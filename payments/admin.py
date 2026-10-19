from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('phone_number', 'checkout_request_id', 'receipt_number')
