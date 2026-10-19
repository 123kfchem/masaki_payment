from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .models import Transaction


class DailyTotalsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='tester',
            email='tester@example.com',
            password='StrongPass123',
        )

    def test_daily_totals_aggregate_completed_transactions(self):
        Transaction.objects.create(
            user=self.user,
            phone_number='+254700000001',
            amount=Decimal('100.00'),
            status='COMPLETED',
            created_at=timezone.now() - timedelta(days=1),
        )
        Transaction.objects.create(
            user=self.user,
            phone_number='+254700000002',
            amount=Decimal('50.00'),
            status='COMPLETED',
            created_at=timezone.now(),
        )

        totals = Transaction.objects.daily_totals_for_user(self.user)

        self.assertEqual(len(totals), 2)
        self.assertEqual(totals[0]['total'], Decimal('50.00'))
        self.assertEqual(totals[1]['total'], Decimal('100.00'))

    def test_dashboard_only_shows_transactions_from_today(self):
        Transaction.objects.create(
            user=self.user,
            phone_number='+254700000001',
            amount=Decimal('100.00'),
            status='COMPLETED',
            created_at=timezone.now() - timedelta(days=1),
        )
        Transaction.objects.create(
            user=self.user,
            phone_number='+254700000002',
            amount=Decimal('50.00'),
            status='COMPLETED',
            created_at=timezone.now(),
        )
        self.client.force_login(self.user)

        response = self.client.get('/')

        self.assertEqual(response.context['transaction_count'], 1)
        self.assertEqual(response.context['completed_total'], Decimal('50.00'))
        self.assertEqual(len(response.context['daily_totals']), 1)
        self.assertContains(response, '+254700000002')
        self.assertNotContains(response, '+254700000001')
