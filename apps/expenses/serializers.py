"""
Serializers for expenses app.
Handles expense, split, and payment data validation.
"""

from rest_framework import serializers
from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.expenses.models import Expense, Split, Payment
from apps.accounts.serializers import UserSerializer

User = get_user_model()


class SplitSerializer(serializers.ModelSerializer):
    """
    Serializer for individual expense splits.
    Shows who owes what in an expense.
    """
    
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = Split
        fields = ['id', 'user', 'user_id', 'amount', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate_amount(self, value):
        """Amount must be non-negative."""
        if value < 0:
            raise serializers.ValidationError("Amount cannot be negative.")
        return value


class ExpenseSerializer(serializers.ModelSerializer):
    """
    Serializer for Expense.
    Read/write expense information with splits.
    """
    
    paid_by = UserSerializer(read_only=True)
    splits = SplitSerializer(many=True, read_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Expense
        fields = [
            'id',
            'transaction_id',
            'group',
            'paid_by',
            'user_id',
            'amount',
            'description',
            'category',
            'splits',
            'created_at',
        ]
        read_only_fields = ['id', 'transaction_id', 'paid_by', 'created_at']
    
    def validate_amount(self, value):
        """Amount must be positive."""
        if value <= 0:
            raise serializers.ValidationError("Expense amount must be greater than 0.")
        return value
    
    def validate(self, data):
        """
        Validate expense data:
        - Group must exist
        - User must be member of group
        - Splits must sum to amount
        """
        from apps.groups.models import Membership
        
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError("User not authenticated.")
        
        group_id = data.get('group')
        if not group_id:
            raise serializers.ValidationError("Group is required.")
        
        # Check if user is member of group
        is_member = Membership.objects.filter(
            group_id=group_id,
            user=request.user
        ).exists()
        
        if not is_member:
            raise serializers.ValidationError(
                "You must be a member of the group to create expenses."
            )
        
        return data


class CreateExpenseWithSplitsSerializer(serializers.Serializer):
    """
    Serializer for creating expense with splits in one request.
    
    Request format:
    {
      "group_id": 1,
      "amount": "100.00",
      "description": "Pizza",
      "category": "food",
      "splits": [
        {"user_id": 1, "amount": "50.00"},
        {"user_id": 2, "amount": "50.00"}
      ]
    }
    """
    
    group_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.ChoiceField(
        choices=Expense.CATEGORY_CHOICES,
        default='other'
    )
    splits = SplitSerializer(many=True)
    
    def validate_amount(self, value):
        """Amount must be positive."""
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value
    
    def validate(self, data):
        """
        Validate:
        - Group exists
        - User is member
        - Splits sum equals amount
        """
        from apps.groups.models import Membership, Group
        
        request = self.context.get('request')
        group_id = data.get('group_id')
        amount = data.get('amount')
        splits = data.get('splits', [])
        
        # Check group exists
        try:
            group = Group.objects.get(id=group_id)
        except Group.DoesNotExist:
            raise serializers.ValidationError("Group does not exist.")
        
        # Check user is member
        is_member = Membership.objects.filter(
            group_id=group_id,
            user=request.user
        ).exists()
        
        if not is_member:
            raise serializers.ValidationError(
                "You must be a member of the group."
            )
        
        # Validate splits
        if not splits:
            raise serializers.ValidationError("At least one split is required.")
        
        total_split = sum(Decimal(str(s['amount'])) for s in splits)
        
        if total_split != amount:
            raise serializers.ValidationError(
                f"Splits total ({total_split}) must equal expense amount ({amount})."
            )
        
        # Check all users in splits are group members
        split_user_ids = [s['user_id'] for s in splits]
        group_member_ids = set(
            Membership.objects.filter(group_id=group_id).values_list(
                'user_id', flat=True
            )
        )
        
        for user_id in split_user_ids:
            if user_id not in group_member_ids:
                raise serializers.ValidationError(
                    f"User {user_id} is not a member of the group."
                )
        
        data['group'] = group
        return data


class CreateEqualSplitSerializer(serializers.Serializer):
    """
    Convenience serializer for equal expense splits.
    
    Request:
    {
      "group_id": 1,
      "amount": "120.00",
      "description": "Pizza",
      "participant_ids": [1, 2, 3, 4]
    }
    """
    
    group_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.ChoiceField(
        choices=Expense.CATEGORY_CHOICES,
        default='other'
    )
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="User IDs to split expense among"
    )
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0.")
        return value
    
    def validate_participant_ids(self, value):
        if not value:
            raise serializers.ValidationError("At least one participant required.")
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate user IDs in participants.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for payment settlement.
    """
    
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    to_user_id = serializers.IntegerField(write_only=True, required=False)
    group_id = serializers.IntegerField(write_only=True)
    group = serializers.PrimaryKeyRelatedField(read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'transaction_id',
            'from_user',
            'to_user',
            'to_user_id',
            'group',
            'group_id',
            'amount',
            'description',
            'status',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'transaction_id', 'from_user', 'group', 'status', 'created_at', 'updated_at']
    
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than 0.")
        return value
    
    def validate(self, data):
        """
        Validate settlement:
        - User cannot settle with themselves
        - Settlement amount cannot exceed actual balance owed
        """
        request = self.context.get('request')
        to_user_id = data.get('to_user_id')
        
        if request.user.id == to_user_id:
            raise serializers.ValidationError(
                "You cannot settle payment with yourself."
            )
        
        return data


class BalanceBetweenUsersSerializer(serializers.Serializer):
    """
    Serializer for balance between two users in a group.
    """
    
    from_user_id = serializers.IntegerField()
    to_user_id = serializers.IntegerField()
    group_id = serializers.IntegerField()
    net_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    details = serializers.DictField()


class GroupBalancesSerializer(serializers.Serializer):
    """
    Serializer for all balances in a group.
    """
    
    group_id = serializers.IntegerField()
    total_expenses = serializers.DecimalField(max_digits=12, decimal_places=2)
    balances = serializers.ListField(
        child=serializers.DictField(),
        help_text="Balance breakdown per user"
    )
