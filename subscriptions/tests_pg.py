"""
PostgreSQL-only integration tests for backend behaviour the SQLite suite cannot
prove: A13 (`NULLS NOT DISTINCT` unique constraint) and A12 (row locking via
`select_for_update`).

Run with:
    python manage.py test subscriptions.tests_pg --settings=config.settings.test_pg

Skipped on non-PostgreSQL backends so the default SQLite suite stays green.
"""
import threading
from datetime import timedelta
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from subscriptions.models import PlanFeatureEntitlement, SubscriptionFeature


_IS_POSTGRES = connection.vendor == "postgresql"


@skipUnless(_IS_POSTGRES, "NULLS NOT DISTINCT is PostgreSQL-specific (A13)")
class EntitlementNullPlanUniquePgTests(TestCase):
    """A13: the status-level default matrix (plan IS NULL) must be unique per
    (feature, subscription_status) on PostgreSQL."""

    def test_duplicate_null_plan_default_is_rejected(self):
        feature = SubscriptionFeature.objects.create(
            code="pg_a13_feature", name="A13", is_active=True
        )
        PlanFeatureEntitlement.objects.create(
            feature=feature, plan=None, subscription_status="PRO", access_level="allow"
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                PlanFeatureEntitlement.objects.create(
                    feature=feature,
                    plan=None,
                    subscription_status="PRO",
                    access_level="deny",
                )

    def test_distinct_status_null_plan_still_allowed(self):
        feature = SubscriptionFeature.objects.create(
            code="pg_a13_feature_2", name="A13b", is_active=True
        )
        PlanFeatureEntitlement.objects.create(
            feature=feature, plan=None, subscription_status="PRO", access_level="allow"
        )
        # A different status is a different constraint tuple → still allowed.
        PlanFeatureEntitlement.objects.create(
            feature=feature, plan=None, subscription_status="TRIAL", access_level="allow"
        )

        self.assertEqual(
            PlanFeatureEntitlement.objects.filter(
                feature=feature, plan__isnull=True
            ).count(),
            2,
        )


@skipUnless(_IS_POSTGRES, "row locking (select_for_update) requires PostgreSQL (A12)")
class ActivateSubscriptionConcurrencyPgTests(TransactionTestCase):
    """A12: two concurrent activations for the same user must stack (the row lock
    serialises them) instead of one update overwriting the other."""

    def test_concurrent_activations_stack_under_row_lock(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(
            username="pg_concurrent_user",
            email="pg-concurrent@example.com",
            password="Secret123!",
            subscription_status="EXPIRED",
        )

        barrier = threading.Barrier(2)
        errors = []

        def worker():
            try:
                barrier.wait(timeout=10)
                handle = user_model.objects.get(pk=user.pk)
                handle.activate_subscription(months=1)
            except Exception as exc:  # noqa: BLE001 - surfaced via errors list
                errors.append(repr(exc))
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=20)

        self.assertEqual(errors, [])
        user.refresh_from_db()
        expected_end = timezone.now() + timedelta(days=60)
        self.assertLessEqual(
            abs((user.subscription_end_date - expected_end).days), 1
        )
        self.assertEqual(user.subscription_status, "PRO")
