"""
Django admin configuration for expenses app.
"""

from django.contrib import admin
from apps.expenses.models import Expense, Split, Payment


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    """
    Expense administration.
    """
    list_display = ('description', 'group', 'paid_by', 'amount', 'category', 'created_at')
    list_filter = ('category', 'created_at', 'group')
    search_fields = ('description', 'group__name', 'paid_by__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'


@admin.register(Split)
class SplitAdmin(admin.ModelAdmin):
    """
    Expense split administration.
    """
    list_display = ('user', 'expense', 'amount', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'expense__description')
    readonly_fields = ('created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Payment/Settlement administration.
    """
    list_display = ('from_user', 'to_user', 'group', 'amount', 'created_at')
    list_filter = ('created_at', 'group')
    search_fields = ('from_user__username', 'to_user__username', 'group__name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
