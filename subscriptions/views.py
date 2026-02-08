"""
Subscription payment views and webhook handlers.
"""
import json
import logging
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

from .models import SubscriptionPlan, PaymentTransaction
from .midtrans import midtrans_client, MidtransError


logger = logging.getLogger(__name__)


def _is_managed_access_user(user) -> bool:
    """
    Users with full-access (staff/superuser) should not go through checkout flow.
    """
    return bool(getattr(user, "has_full_access", False))


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

            data = json.loads(request.body)
            plan_id = data.get('plan_id')
            
            if not plan_id:
                return JsonResponse({
                    'success': False,
                    'error': 'Plan ID required'
                }, status=400)
            
            # Get the plan
            plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
            
            # Create transaction record
            transaction = PaymentTransaction.objects.create(
                user=request.user,
                plan=plan,
                amount=plan.price,
                status=PaymentTransaction.STATUS_PENDING
            )
            transaction.order_id = transaction.generate_order_id()
            transaction.save()
            
            # Get Midtrans Snap token
            result = midtrans_client.create_snap_token(
                order_id=transaction.order_id,
                amount=int(plan.price),
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
                    logger.warning(f"Transaction not found: {order_id}")
                    return HttpResponse(status=404)

                # Update transaction metadata for audit trail
                payment_tx.midtrans_transaction_id = data.get('transaction_id', '')
                payment_tx.payment_type = data.get('payment_type', '')
                payment_tx.midtrans_response = data

                # Process based on status
                if transaction_status in ['capture', 'settlement']:
                    if fraud_status == 'accept':
                        already_success = (
                            payment_tx.status == PaymentTransaction.STATUS_SUCCESS and
                            payment_tx.paid_at is not None
                        )
                        if already_success:
                            logger.info(
                                "Ignoring duplicate successful webhook for order %s",
                                order_id
                            )
                        else:
                            self._handle_success(payment_tx)
                elif transaction_status in ['cancel', 'deny']:
                    payment_tx.status = PaymentTransaction.STATUS_FAILED
                elif transaction_status == 'expire':
                    payment_tx.status = PaymentTransaction.STATUS_EXPIRED
                elif transaction_status == 'refund':
                    payment_tx.status = PaymentTransaction.STATUS_REFUND
                # pending - keep as pending

                payment_tx.save()
            
            return HttpResponse(status=200)
            
        except json.JSONDecodeError:
            return HttpResponse(status=400)
        except Exception as e:
            logger.exception(f"Webhook error: {e}")
            return HttpResponse(status=500)
    
    def _handle_success(self, transaction: PaymentTransaction):
        """Handle successful payment."""
        transaction.status = PaymentTransaction.STATUS_SUCCESS
        transaction.paid_at = timezone.now()
        
        # Activate user subscription
        if transaction.plan:
            transaction.user.activate_subscription(
                months=transaction.plan.duration_months
            )
            logger.info(
                f"Subscription activated for {transaction.user.email}: "
                f"{transaction.plan.duration_months} months"
            )


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
                    messages.success(
                        request,
                        f"Pembayaran berhasil! Subscription Anda aktif selama {transaction.plan.duration_months} bulan."
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
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return render(request, 'subscriptions/pricing.html', {
            'plans': plans
        })


class CheckoutView(LoginRequiredMixin, View):
    """
    Display checkout page for a specific plan.
    
    GET /subscriptions/checkout/<plan_id>/
    """
    
    def get(self, request, plan_id):
        from django.conf import settings
        
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)

        if _is_managed_access_user(request.user):
            messages.info(request, 'Akun admin/staff memiliki akses penuh dan tidak memerlukan checkout.')
            return redirect('dashboard:dashboard')
        
        # Check if user already has active subscription
        if request.user.subscription_status == 'PRO' and request.user.is_subscription_active:
            messages.info(request, 'Anda sudah memiliki langganan aktif.')
            return redirect('dashboard:dashboard')
        
        return render(request, 'subscriptions/checkout.html', {
            'plan': plan,
            'midtrans_client_key': getattr(settings, 'MIDTRANS_CLIENT_KEY', ''),
        })

