"""
Subscription payment views and webhook handlers.
"""
import json
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction as db_transaction
from django.core.cache import cache

from .models import SubscriptionPlan, PaymentTransaction
from .midtrans import midtrans_client, MidtransError
from .pricing_service import format_currency_idr, resolve_effective_plan_pricing
from .reconciliation import mark_paid_and_activate


logger = logging.getLogger(__name__)


def _is_managed_access_user(user) -> bool:
    """
    Users with full-access (staff/superuser) should not go through checkout flow.
    """
    return bool(getattr(user, "has_full_access", False))


def _settlement_payload_is_consistent(status_code, gross_amount, payment_tx) -> bool:
    """Cross-check the SIGNED fields of a Midtrans notification against our record.

    The webhook signature only covers order_id + status_code + gross_amount +
    server_key — NOT transaction_status / fraud_status (audit finding A4). Before
    a 'settlement'/'capture' body is trusted to grant access, confirm the signed
    status_code is Midtrans' success code ('200') and the signed gross_amount
    matches the stored amount. Amounts are compared as Decimal so a formatting
    difference like '300000.00' vs '300000' is not a false mismatch.
    """
    if str(status_code) != "200":
        return False
    try:
        signed_amount = Decimal(str(gross_amount))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return signed_amount == Decimal(payment_tx.amount)


# A6: anti-abuse limit for payment creation. Each call writes a row and hits the
# Midtrans API, so cap per-user attempts. (Webhook rate-limiting is handled at the
# edge/WAF per decision D-2 so legitimate burst notifications aren't dropped.)
CREATE_PAYMENT_MAX_ATTEMPTS = 5
CREATE_PAYMENT_WINDOW_SECONDS = 60


class CreatePaymentView(LoginRequiredMixin, View):
    """
    Create a new payment transaction and get Midtrans Snap token.
    
    POST /subscriptions/payment/create/
    Body: {"plan_id": 1}
    """
    
    def post(self, request):
        try:
            if _is_managed_access_user(request.user):
                return JsonResponse({
                    'success': False,
                    'error': 'Akun admin/staff tidak memerlukan checkout langganan.',
                    'code': 'ADMIN_CHECKOUT_BLOCKED'
                }, status=403)

            # A6: throttle payment creation per user to prevent spam.
            rate_key = f"subs:create_payment:{request.user.id}"
            attempts = cache.get(rate_key, 0)
            if attempts >= CREATE_PAYMENT_MAX_ATTEMPTS:
                return JsonResponse({
                    'success': False,
                    'error': 'Terlalu banyak permintaan pembayaran. Silakan coba lagi sebentar lagi.',
                    'code': 'RATE_LIMIT_EXCEEDED',
                }, status=429)
            cache.set(rate_key, attempts + 1, CREATE_PAYMENT_WINDOW_SECONDS)

            data = json.loads(request.body)
            plan_id = data.get('plan_id')
            
            if not plan_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Plan ID required'
                }, status=400)
            
            # Get the plan
            plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
            pricing = resolve_effective_plan_pricing(plan)

            # A10a: reuse a recent, still-priced pending transaction for this plan
            # instead of piling up new rows (and a redundant Midtrans call) on
            # repeated clicks. Bounded to 30 minutes so the reused Snap token is
            # fresh, and to the current effective amount so a changed promo never
            # reuses a stale price.
            existing = (
                PaymentTransaction.objects.filter(
                    user=request.user,
                    plan=plan,
                    status=PaymentTransaction.STATUS_PENDING,
                    amount=pricing.final_price,
                    created_at__gte=timezone.now() - timedelta(minutes=30),
                )
                .exclude(snap_token="")
                .order_by("-created_at")
                .first()
            )
            if existing:
                return JsonResponse({
                    'success': True,
                    'snap_token': existing.snap_token,
                    'order_id': existing.order_id,
                    'reused': True,
                })

            # Build the transaction with order_id set BEFORE the first save so
            # the row is inserted once, already unique. The previous two-step
            # pattern (create() with empty order_id, then save() again) left a
            # window where concurrent inserts collided on order_id='' and could
            # strand the unique '' slot if the second save never ran.
            transaction = PaymentTransaction(
                user=request.user,
                plan=plan,
                amount=pricing.final_price,
                duration_months_snapshot=plan.duration_months,
                base_amount_snapshot=pricing.base_price,
                discount_amount_snapshot=pricing.discount_amount,
                promotion_id_snapshot=pricing.promotion.id if pricing.promotion else None,
                promotion_name_snapshot=pricing.promotion.name if pricing.promotion else "",
                promotion_discount_type_snapshot=(
                    pricing.promotion.discount_type if pricing.promotion else ""
                ),
                promotion_discount_value_snapshot=(
                    pricing.promotion.discount_value if pricing.promotion else None
                ),
                status=PaymentTransaction.STATUS_PENDING,
            )
            transaction.order_id = transaction.generate_order_id()
            transaction.save()
            
            # Get Midtrans Snap token
            result = midtrans_client.create_snap_token(
                order_id=transaction.order_id,
                amount=int(pricing.final_price),
                user_email=request.user.email,
                user_name=request.user.get_full_name() or request.user.username,
                item_name=f"AHSP Pro - {plan.name}"
            )
            
            # Save snap token
            transaction.snap_token = result['token']
            transaction.save()
            
            return JsonResponse({
                'success': True,
                'snap_token': result['token'],
                'redirect_url': result.get('redirect_url'),
                'order_id': transaction.order_id
            })
            
        except MidtransError as e:
            logger.error(f"Midtrans error: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
        except Exception as e:
            logger.exception(f"Payment creation error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Terjadi kesalahan. Silakan coba lagi.'
            }, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(View):
    """
    Handle Midtrans payment notifications (webhook).
    
    POST /subscriptions/webhook/midtrans/
    
    Called by Midtrans when payment status changes.
    """
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            order_id = data.get('order_id')
            transaction_status = data.get('transaction_status')
            fraud_status = data.get('fraud_status', 'accept')
            status_code = data.get('status_code')
            gross_amount = data.get('gross_amount')
            signature = data.get('signature_key')
            
            # Verify signature
            if not midtrans_client.verify_signature(
                order_id, status_code, gross_amount, signature
            ):
                logger.warning(f"Invalid webhook signature for order {order_id}")
                return HttpResponse(status=403)
            
            # Lock transaction row to ensure webhook idempotency on retries.
            with db_transaction.atomic():
                try:
                    payment_tx = PaymentTransaction.objects.select_for_update().get(order_id=order_id)
                except PaymentTransaction.DoesNotExist:
                    # A8: signature already verified above, so this is a validly
                    # signed notification for an order we don't have. Acknowledge
                    # with 200 so Midtrans stops retrying; log for investigation.
                    logger.warning(
                        "Webhook for unknown order %s (valid signature); acknowledging",
                        order_id,
                    )
                    return HttpResponse(status=200)

                # Update transaction metadata for audit trail
                payment_tx.midtrans_transaction_id = data.get('transaction_id', '')
                payment_tx.payment_type = data.get('payment_type', '')
                payment_tx.midtrans_response = data

                # Process based on status
                if transaction_status in ['capture', 'settlement']:
                    if fraud_status == 'accept':
                        if not _settlement_payload_is_consistent(
                            status_code, gross_amount, payment_tx
                        ):
                            # A4: signed fields don't match our record — do not
                            # trust the (unsigned) settlement status. Leave the
                            # transaction for the authoritative reconcile job.
                            logger.warning(
                                "Webhook settlement cross-check failed for order %s; "
                                "not activating (gross=%s, status_code=%s, amount=%s)",
                                order_id, gross_amount, status_code, payment_tx.amount,
                            )
                        else:
                            already_activated = payment_tx.paid_at is not None
                            if already_activated:
                                logger.info(
                                    "Ignoring already-activated successful webhook for order %s",
                                    order_id
                                )
                            else:
                                self._handle_success(payment_tx)
                elif transaction_status in ['cancel', 'deny']:
                    if payment_tx.paid_at is not None:
                        logger.warning(
                            "Ignoring late %s webhook for already-activated order %s",
                            transaction_status,
                            order_id,
                        )
                    else:
                        payment_tx.status = PaymentTransaction.STATUS_FAILED
                elif transaction_status == 'expire':
                    if payment_tx.paid_at is not None:
                        logger.warning(
                            "Ignoring late expire webhook for already-activated order %s",
                            order_id,
                        )
                    else:
                        payment_tx.status = PaymentTransaction.STATUS_EXPIRED
                elif transaction_status == 'refund':
                    was_activated = payment_tx.paid_at is not None
                    payment_tx.status = PaymentTransaction.STATUS_REFUND
                    if was_activated:
                        # EC-1: revoke only when this was the user's sole paid
                        # transaction. If another non-refunded SUCCESS payment
                        # still justifies access, do not blanket-revoke it.
                        has_other_paid = (
                            PaymentTransaction.objects
                            .filter(
                                user=payment_tx.user,
                                status=PaymentTransaction.STATUS_SUCCESS,
                            )
                            .exclude(pk=payment_tx.pk)
                            .exists()
                        )
                        if not has_other_paid:
                            payment_tx.user.revoke_subscription()
                # pending - keep as pending

                payment_tx.save()
            
            return HttpResponse(status=200)
            
        except json.JSONDecodeError:
            return HttpResponse(status=400)
        except Exception as e:
            logger.exception(f"Webhook error: {e}")
            return HttpResponse(status=500)
    
    def _handle_success(self, transaction: PaymentTransaction):
        """Handle successful payment via the shared, idempotent activation path.

        The ``paid_at`` guard in ``post`` ensures this only runs once; the actual
        state change lives in ``mark_paid_and_activate`` so the webhook and the
        reconciliation job grant access through exactly the same code.
        """
        mark_paid_and_activate(transaction)


class PaymentFinishView(LoginRequiredMixin, View):
    """
    Handle redirect after Midtrans payment (success/failure page).
    
    GET /subscriptions/payment/finish/?order_id=xxx
    """
    
    def get(self, request):
        order_id = request.GET.get('order_id')
        
        if order_id:
            try:
                transaction = PaymentTransaction.objects.get(
                    order_id=order_id,
                    user=request.user
                )
                
                if transaction.status == PaymentTransaction.STATUS_SUCCESS:
                    duration_months = (
                        transaction.duration_months_snapshot
                        or getattr(transaction.plan, "duration_months", 0)
                    )
                    duration_label = (
                        f"{duration_months} bulan" if duration_months > 0 else "sesuai paket"
                    )
                    messages.success(
                        request,
                        f"Pembayaran berhasil! Subscription Anda aktif selama {duration_label}."
                    )
                elif transaction.status == PaymentTransaction.STATUS_PENDING:
                    messages.info(
                        request,
                        "Pembayaran sedang diproses. Anda akan mendapat notifikasi setelah pembayaran dikonfirmasi."
                    )
                else:
                    messages.warning(
                        request,
                        "Pembayaran tidak berhasil. Silakan coba lagi."
                    )
            except PaymentTransaction.DoesNotExist:
                messages.error(request, "Transaksi tidak ditemukan.")
        
        return redirect('dashboard:dashboard')


class PricingPageView(View):
    """
    Display pricing page with available plans.
    
    GET /subscriptions/pricing/
    """
    
    def get(self, request):
        return redirect("pages:pricing")


class CheckoutView(LoginRequiredMixin, View):
    """
    Display checkout page for a specific plan.
    
    GET /subscriptions/checkout/<plan_id>/
    """
    
    def get(self, request, plan_id):
        from django.conf import settings
        
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
        pricing = resolve_effective_plan_pricing(plan)

        if _is_managed_access_user(request.user):
            messages.info(request, 'Akun admin/staff memiliki akses penuh dan tidak memerlukan checkout.')
            return redirect('dashboard:dashboard')
        
        # Check if user already has an active PRO subscription (A10b: a single
        # is_pro_active check; trial-active users are still allowed to upgrade).
        if request.user.is_pro_active:
            messages.info(request, 'Anda sudah memiliki langganan aktif.')
            return redirect('dashboard:dashboard')
        
        return render(request, 'subscriptions/checkout.html', {
            'plan': plan,
            'pricing': pricing,
            'price_display': format_currency_idr(pricing.final_price),
            'base_price_display': format_currency_idr(pricing.base_price),
            'discount_amount_display': format_currency_idr(pricing.discount_amount),
            'midtrans_client_key': getattr(settings, 'MIDTRANS_CLIENT_KEY', ''),
            'midtrans_is_production': getattr(settings, 'MIDTRANS_IS_PRODUCTION', False),
        })
