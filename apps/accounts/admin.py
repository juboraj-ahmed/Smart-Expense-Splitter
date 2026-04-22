"""
Django admin configuration for accounts app.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from apps.accounts.models import User, TrustScoreAudit


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User admin with trust score visibility.
    """
    list_display = ('username', 'email', 'first_name', 'trust_score', 'created_at', 'is_active')
    list_filter = ('trust_score', 'created_at', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    readonly_fields = ('trust_score', 'trust_score_updated_at', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Credentials', {'fields': ('username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Profile', {'fields': ('bio', 'phone', 'avatar_url')}),
        ('Trust', {'fields': ('trust_score', 'trust_score_updated_at')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
    )


@admin.register(TrustScoreAudit)
class TrustScoreAuditAdmin(admin.ModelAdmin):
    """
    Audit log for trust score changes.
    """
    list_display = ('user', 'old_score', 'new_score', 'reason', 'computed_at')
    list_filter = ('reason', 'computed_at')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'old_score', 'new_score', 'metrics', 'computed_at')
    ordering = ('-computed_at',)
