"""
Models for groups app.
Defines Group and Membership models for managing user groups and expense sharing.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Group(models.Model):
    """
    A group represents a collection of users who share expenses together.
    
    Examples:
    - Apartment/Roommates
    - Trip/Vacation
    - Family
    - Sports team
    
    Design notes:
    - Immutable: Groups are never deleted (audit trail)
    - No "owner" field: ownership is managed via Membership with 'admin' role
    - Accessible only to members (enforced in views)
    """
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the group (e.g., 'Summer Vacation 2025')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what the group is for"
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='groups_created',
        help_text="User who created the group"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = '"group"'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by']),
        ]
    
    def __str__(self):
        return self.name
    
    def add_member(self, user, role='member'):
        """
        Add a user to the group.
        
        Args:
            user: User instance to add
            role: 'admin' or 'member' (default: 'member')
            
        Raises:
            ValidationError: If user is already a member
        """
        if Membership.objects.filter(group=self, user=user).exists():
            raise ValidationError(f"{user.username} is already a member of {self.name}")
        
        Membership.objects.create(group=self, user=user, role=role)
    
    def remove_member(self, user):
        """
        Remove a user from the group.
        
        Args:
            user: User instance to remove
            
        Raises:
            ValidationError: If user is not a member
        """
        membership = Membership.objects.filter(group=self, user=user).first()
        if not membership:
            raise ValidationError(f"{user.username} is not a member of {self.name}")
        membership.delete()
    
    def get_members(self):
        """
        Get all members of the group.
        
        Returns:
            QuerySet of User objects
        """
        return User.objects.filter(membership__group=self)
    
    def get_member_count(self):
        """Get count of members."""
        return Membership.objects.filter(group=self).count()


class Membership(models.Model):
    """
    Represents association between User and Group.
    
    Design rationale:
    - Separates group from membership concerns
    - Allows role-based access control (admin vs member)
    - Tracks when user joined the group
    - Can be extended with permissions in future
    
    Unique constraint: A user can appear in a group only once.
    """
    
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('member', 'Member'),
    )
    
    group = models.ForeignKey(
        Group,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='memberships'
    )
    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default='member'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'membership'
        unique_together = ('group', 'user')
        indexes = [
            models.Index(fields=['group', 'user']),
            models.Index(fields=['user']),
            models.Index(fields=['group']),
        ]
    
    def __str__(self):
        return f"{self.user.username} → {self.group.name} ({self.role})"
    
    def is_admin(self):
        """Check if member is an admin of the group."""
        return self.role == 'admin'
