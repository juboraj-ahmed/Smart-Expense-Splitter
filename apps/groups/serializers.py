"""
Serializers for groups app.
Handles group and membership data validation.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.groups.models import Group, Membership
from apps.accounts.serializers import UserSerializer

User = get_user_model()


class MembershipSerializer(serializers.ModelSerializer):
    """
    Serializer for group membership.
    Shows user info within a group context.
    """
    
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Membership
        fields = ['id', 'user', 'role', 'joined_at']
        read_only_fields = ['id', 'joined_at']


class GroupSerializer(serializers.ModelSerializer):
    """
    Serializer for Group data.
    
    Includes:
    - Basic info (name, description)
    - Member count
    - Creator info
    - User's balance in group (for their own response)
    """
    
    created_by = UserSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    members_count = serializers.SerializerMethodField()
    your_balance = serializers.SerializerMethodField()
    total_expenses = serializers.SerializerMethodField()
    
    class Meta:
        model = Group
        fields = [
            'id',
            'name',
            'description',
            'created_by',
            'members',
            'members_count',
            'your_balance',
            'total_expenses',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'created_by']
    
    def get_members(self, obj):
        """Get all members with their roles."""
        memberships = obj.memberships.select_related('user')
        # Only include if viewing from authenticated user (optional filtering)
        return [{
            'id': m.user.id,
            'username': m.user.username,
            'email': m.user.email,
            'role': m.role,
            'trust_score': m.user.trust_score,
        } for m in memberships]
    
    def get_members_count(self, obj):
        """Count total members."""
        return obj.get_member_count()
    
    def get_your_balance(self, obj):
        """
        Calculate current user's net balance in group.
        
        Only available if user is viewing their own group data.
        Returns:
            Decimal or None: Positive = owed to user, Negative = user owes
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        
        # Import here to avoid circular imports
        from apps.expenses.services import SettlementService
        
        try:
            balance = SettlementService.calculate_user_balance(
                request.user,
                obj
            )
            return str(balance)
        except Exception:
            return None
    
    def get_total_expenses(self, obj):
        """Get total amount of all expenses in group."""
        from django.db.models import Sum
        from apps.expenses.models import Expense
        
        total = Expense.objects.filter(group=obj).aggregate(
            total=Sum('amount')
        )['total']
        return str(total or 0.0)


class GroupCreateSerializer(serializers.ModelSerializer):
    """
    Simplified serializer for creating a new group.
    """
    
    class Meta:
        model = Group
        fields = ['name', 'description']


class AddMemberSerializer(serializers.Serializer):
    """
    Serializer for adding member to group.
    """
    
    user_id = serializers.IntegerField(
        help_text="ID of user to add"
    )
    role = serializers.ChoiceField(
        choices=['member', 'admin'],
        default='member',
        help_text="Role in group"
    )
    
    def validate_user_id(self, value):
        """Ensure user exists."""
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User does not exist.")
        return value
