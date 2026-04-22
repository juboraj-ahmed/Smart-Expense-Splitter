"""
Django admin configuration for groups app.
"""

from django.contrib import admin
from apps.groups.models import Group, Membership


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """
    Group administration.
    """
    list_display = ('name', 'created_by', 'member_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    
    def member_count(self, obj):
        """Show member count."""
        return obj.get_member_count()
    member_count.short_description = 'Members'


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """
    Group membership administration.
    """
    list_display = ('user', 'group', 'role', 'joined_at')
    list_filter = ('role', 'joined_at', 'group')
    search_fields = ('user__username', 'group__name')
    readonly_fields = ('joined_at',)
