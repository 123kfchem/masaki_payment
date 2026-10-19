from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class TransactionManager(models.Manager):
    def daily_totals_for_user(self, user, day=None):
        transactions = self.filter(user=user, status='COMPLETED')
        if day is not None:
            transactions = transactions.filter(created_at__date=day)
        return list(
            transactions
            .values('created_at__date')
            .annotate(total=Sum('amount'))
            .order_by('-created_at__date')
        )


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    phone_number = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    merchant_request_id = models.CharField(max_length=100, blank=True)
    checkout_request_id = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TransactionManager()

    class Meta:
        ordering = ['-created_at']

    @property
    def is_completed(self):
        return self.status == 'COMPLETED'
