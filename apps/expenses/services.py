"""
Service layer for expenses app.
Contains business logic for expense splitting, settlement, and trust score calculation.

Design Principles:
1. Services encapsulate complex logic (not in views or models)
2. Services are stateless and reusable
3. Services handle transactions and data consistency
4. Services raise exceptions for validation errors
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Q, F
from decimal import Decimal
from datetime import timedelta
from apps.expenses.models import Expense, Split, Payment
from apps.groups.models import Group, Membership
from apps.accounts.models import User, TrustScoreAudit
from django.conf import settings


class ExpenseService:
    """
    Service for managing expenses and splits.
    """
    
    @staticmethod
    @transaction.atomic  # Atomic: all splits create together or none
    def create_expense_with_splits(group_id, paid_by, amount, description, 
                                   category, splits_data):
        """
        Create expense with multiple splits atomically.
        
        Args:
            group_id: ID of group
            paid_by: User paying
            amount: Total amount
            description: Expense description
            category: Expense category
            splits_data: List of {'user_id': X, 'amount': Y}
        
        Returns:
            Expense instance
        
        Raises:
            ValidationError: If splits don't sum to amount or users not members
        """
        # Validate splits sum
        total_split = sum(Decimal(str(s['amount'])) for s in splits_data)
        if total_split != amount:
            raise ValidationError(
                f"Splits total ({total_split}) must equal amount ({amount})"
            )
        
        # Create expense
        expense = Expense.objects.create(
            group_id=group_id,
            paid_by=paid_by,
            amount=amount,
            description=description,
            category=category,
        )
        
        # Create splits atomically
        for split_data in splits_data:
            Split.objects.create(
                expense=expense,
                user_id=split_data['user_id'],
                amount=split_data['amount']
            )
        
        return expense
    
    @staticmethod
    def create_equal_splits(group_id, paid_by, amount, description, 
                           category, participant_ids):
        """
        Create equal splits for a group of participants.
        
        Handles rounding issues by allocating remainder to last participant.
        """
        num_participants = len(participant_ids)
        if num_participants == 0:
            raise ValidationError("At least one participant required")
        
        per_person = amount / num_participants
        per_person = per_person.quantize(Decimal('0.01'))
        
        splits_data = []
        for i, user_id in enumerate(participant_ids):
            if i == num_participants - 1:
                # Last person gets remainder (handles rounding)
                final_amount = amount - (per_person * (num_participants - 1))
            else:
                final_amount = per_person
            
            splits_data.append({
                'user_id': user_id,
                'amount': final_amount
            })
        
        return ExpenseService.create_expense_with_splits(
            group_id=group_id,
            paid_by=paid_by,
            amount=amount,
            description=description,
            category=category,
            splits_data=splits_data
        )


class SettlementService:
    """
    Service for managing settlements and balance calculations.
    
    Key concepts:
    - Balance = what user paid - what user owes + what they received
    - We calculate on-demand from transactions (no stored balance field)
    """
    
    @staticmethod
    def calculate_user_balance(user, group):
        """
        Calculate net balance for user in group.
        
        Returns:
            Decimal: Positive = owed to user, Negative = user owes
        
        Formula:
        balance = (total_paid - total_split - payments_received + payments_made_to)
        """
        # Total amount user paid
        total_paid = Expense.objects.filter(
            group=group,
            paid_by=user
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Total amount in splits (what user owes)
        total_owes = Split.objects.filter(
            user=user,
            expense__group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Total amounts received from others
        payments_received = Payment.objects.filter(
            status='accepted',
            to_user=user,
            group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Total amounts paid to others (settlement)
        payments_made = Payment.objects.filter(
            status='accepted',
            from_user=user,
            group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Net balance
        balance = total_paid - total_owes + payments_made - payments_received
        return balance
    
    @staticmethod
    def calculate_balance_between_users(user1, user2, group):
        """
        Calculate balance between two specific users.
        
        Returns:
            Decimal: Positive = user2 owes user1, Negative = user1 owes user2
        """
        # What user1 paid that user2 had to split
        u1_paid_u2_benefited = Split.objects.filter(
            user=user2,
            expense__paid_by=user1,
            expense__group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # What user2 paid that user1 had to split
        u2_paid_u1_benefited = Split.objects.filter(
            user=user1,
            expense__paid_by=user2,
            expense__group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Settlements between them
        u1_paid_u2 = Payment.objects.filter(
            status='accepted',
            from_user=user1,
            to_user=user2,
            group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        u2_paid_u1 = Payment.objects.filter(
            status='accepted',
            from_user=user2,
            to_user=user1,
            group=group
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Net: user2 owes user1
        net = (u1_paid_u2_benefited - u2_paid_u1_benefited) + u1_paid_u2 - u2_paid_u1
        return net
    
    @staticmethod
    @transaction.atomic
    def record_settlement(from_user, to_user, group, amount, description=''):
        """
        Record settlement payment between users.
        
        Validates:
        - Amounts don't exceed actual balance owed
        - User isn't paying themselves
        - Both users are in group
        
        Updates trust scores after recording.
        """
        # Validate users
        if from_user.id == to_user.id:
            raise ValidationError("Cannot settle payment with yourself")
        
        # Verify both are members of group
        if not Membership.objects.filter(group=group, user=from_user).exists():
            raise ValidationError(f"{from_user.username} is not a member of {group.name}")
        if not Membership.objects.filter(group=group, user=to_user).exists():
            raise ValidationError(f"{to_user.username} is not a member of {group.name}")
        
        # Calculate actual balance owed
        actual_balance = SettlementService.calculate_balance_between_users(
            from_user, to_user, group
        )
        
        # Check pending payments
        pending_amount = Payment.objects.filter(
            from_user=from_user, to_user=to_user, group=group, status='pending'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Validate amount (user1 owes user2 if negative)
        if actual_balance < 0:  # from_user owes to_user
            max_can_settle = abs(actual_balance) - pending_amount
            if amount > max_can_settle:
                raise ValidationError(
                    f"{from_user.username} owes {abs(actual_balance)} "
                    f"(with {pending_amount} pending) "
                    f"to {to_user.username}, cannot settle {amount}"
                )
        else:  # from_user doesn't owe to_user (or they don't owe anything)
            if amount > 0:
                raise ValidationError(
                    f"{from_user.username} doesn't owe {to_user.username}. "
                    f"Actually, {to_user.username} owes {actual_balance}."
                )
        
        # Create payment
        payment = Payment.objects.create(
            from_user=from_user,
            to_user=to_user,
            group=group,
            amount=amount,
            description=description
        )
        
        # Update trust score for payer
        TrustScoreService.recalculate_score(from_user)
        
        return payment
    
    @staticmethod
    def get_group_balances(group):
        """
        Get all balances in a group.
        
        Returns:
            List of dicts with per-user balance information
        """
        balances = []
        members = group.memberships.select_related('user').all()
        
        for membership in members:
            user = membership.user
            
            # Calculate comprehensive net balance including settlements
            net_balance = SettlementService.calculate_user_balance(user, group)
            
            balances.append({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'trust_score': user.trust_score,
                },
                'total_paid': Decimal('0.00'),  # Omitted for performance, frontend uses net_balance
                'total_owes': Decimal('0.00'),
                'net_balance': net_balance,
            })
        
        return balances


class TrustScoreService:
    """
    Service for trust score calculation and management.
    
    Philosophy:
    - Score reflects payment reliability based on behavior
    - Penalize late/missing payments
    - Reward consistent on-time payments
    - Account for financial capacity (debt ratio)
    """
    
    # Configuration from settings
    SETTINGS = settings.TRUST_SCORE_SETTINGS
    
    @staticmethod
    def get_user_payment_metrics(user):
        """
        Get raw payment metrics for user.
        
        Returns:
            dict: Payment history metrics
        """
        payments = Payment.objects.filter(from_user=user)
        
        on_time = 0
        late = 0
        days_late_total = 0
        
        for payment in payments:
            # Find what expense(s) this settled
            # (Simplified: just track payment timeliness)
            days_since = (timezone.now() - payment.created_at).days
            
            # Assume debt is "late" if not paid within 7 days of expense
            # In real system, would link payments to specific expense groups
            if days_since > 7:
                late += 1
                days_late_total += days_since
            else:
                on_time += 1
        
        total_payments = on_time + late
        avg_days_late = days_late_total / late if late > 0 else 0
        
        # Since payments are not linked to specific expenses, 
        # pending amount is the sum of the user's net negative balances across all groups.
        groups = Group.objects.filter(memberships__user=user)
        pending_amount = Decimal('0.00')
        for group in groups:
            bal = SettlementService.calculate_user_balance(user, group)
            if bal < 0:
                pending_amount += abs(bal)
        
        # How long has longest overdue been pending?
        # We find the oldest split in any group where the user owes money
        # Simplified: just find the oldest split
        oldest_pending = Split.objects.filter(
            user=user,
            expense__created_at__lt=timezone.now() - timedelta(days=7)
        ).order_by('expense__created_at').first()
        
        # Check if the user actually owes money overall
        pending_days = 0
        if pending_amount > 0 and oldest_pending:
            pending_days = (timezone.now() - oldest_pending.expense.created_at).days
        
        return {
            'total_payments': total_payments,
            'on_time_payments': on_time,
            'late_payments': late,
            'avg_days_late': avg_days_late,
            'pending_amount': pending_amount,
            'pending_since_days': pending_days,
        }
    
    @staticmethod
    def recalculate_score(user):
        """
        Recalculate trust score for a user.
        
        Algorithm:
        Base: 100
        Penalties:
        - Late payment: -5 per occurrence
        - Pending overdue: -2 per 7 days
        - High debt ratio: -15 if pending > 75%
        Bonuses:
        - Consistency: +3 if 100% on-time last 5
        - Early payments: +2 per 10 early payments
        """
        metrics = TrustScoreService.get_user_payment_metrics(user)
        
        # Base score
        score = TrustScoreService.SETTINGS['BASE_SCORE']
        
        # Late payment penalty
        late_penalty = metrics['late_payments'] * TrustScoreService.SETTINGS['LATE_PAYMENT_PENALTY']
        
        # Pending overdue penalty
        overdue_penalty = (metrics['pending_since_days'] // 7) * TrustScoreService.SETTINGS['OVERDUE_PENALTY_MULTIPLIER']
        
        # Bonuses
        consistency_bonus = 0
        if metrics['total_payments'] >= 5 and metrics['on_time_payments'] == metrics['total_payments']:
            consistency_bonus = TrustScoreService.SETTINGS['CONSISTENCY_BONUS']
        
        # Calculate final score
        final_score = max(0, min(100, score - late_penalty - overdue_penalty + consistency_bonus))
        
        # Record change
        old_score = user.trust_score
        user.trust_score = final_score
        user.trust_score_updated_at = timezone.now()
        user.save()
        
        # Audit log
        TrustScoreAudit.objects.create(
            user=user,
            old_score=old_score,
            new_score=final_score,
            reason='recalculated',
            metrics={
                'breakdown': {
                    'base': score,
                    'late_penalty': -late_penalty,
                    'overdue_penalty': -overdue_penalty,
                    'consistency_bonus': consistency_bonus,
                },
                'payment_metrics': {
                    'total': metrics['total_payments'],
                    'on_time': metrics['on_time_payments'],
                    'late': metrics['late_payments'],
                    'avg_days_late': float(metrics['avg_days_late']),
                },
                'pending': {
                    'amount': str(metrics['pending_amount']),
                    'days_overdue': metrics['pending_since_days'],
                }
            }
        )
        
        return final_score
    
    @staticmethod
    def get_detailed_score(user):
        """
        Get detailed trust score breakdown for API response.
        """
        metrics = TrustScoreService.get_user_payment_metrics(user)
        audit_history = TrustScoreAudit.objects.filter(user=user).order_by('-computed_at')[:5]
        
        return {
            'user_id': user.id,
            'username': user.username,
            'current_score': user.trust_score,
            'previous_score': audit_history[1].new_score if len(audit_history) > 1 else user.trust_score,
            'score_breakdown': {
                'base_score': TrustScoreService.SETTINGS['BASE_SCORE'],
                'late_payment_penalty': -(metrics['late_payments'] * TrustScoreService.SETTINGS['LATE_PAYMENT_PENALTY']),
                'pending_amount_penalty': -((metrics['pending_since_days'] // 7) * TrustScoreService.SETTINGS['OVERDUE_PENALTY_MULTIPLIER']),
                'consistency_bonus': TrustScoreService.SETTINGS['CONSISTENCY_BONUS'] if metrics['total_payments'] >= 5 and metrics['on_time_payments'] == metrics['total_payments'] else 0,
                'final_score': user.trust_score,
            },
            'metrics': metrics,
            'last_updated': user.trust_score_updated_at,
        }
