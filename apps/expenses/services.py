"""
Service layer for expenses app.
Contains business logic for expense splitting, settlement, and trust score calculation.
"""

from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Sum, Q, F
from decimal import Decimal
from datetime import timedelta
import math
from apps.expenses.models import Expense, Split, Payment, Notification
from apps.groups.models import Group, Membership
from apps.accounts.models import User, TrustScoreAudit
from django.conf import settings

class NotificationService:
    """
    Service for generating lightweight notifications.
    """
    @staticmethod
    def create_notification(user_id, message):
        Notification.objects.create(user_id=user_id, message=message)

class ExpenseService:
    """
    Service for managing expenses and splits.
    """
    
    @staticmethod
    @transaction.atomic
    def create_expense_with_splits(group_id, paid_by, amount, description, 
                                   category, splits_data):
        amount = Decimal(str(amount))
        
        # FRAUD PREVENTION: Limits and invalid states
        if amount <= 0 or amount > Decimal('100000'):
            raise ValidationError("Expense amount must be between 0.01 and 100,000")
            
        total_split = sum(Decimal(str(s['amount'])) for s in splits_data)
        if abs(total_split - amount) > Decimal('0.01'):
            raise ValidationError(f"Splits total ({total_split}) must equal amount ({amount})")
        
        expense = Expense.objects.create(
            group_id=group_id,
            paid_by=paid_by,
            amount=amount,
            description=description,
            category=category,
        )
        
        for split_data in splits_data:
            split_amt = Decimal(str(split_data['amount']))
            if split_amt < 0:
                raise ValidationError("Split amounts cannot be negative")
                
            Split.objects.create(
                expense=expense,
                user_id=split_data['user_id'],
                amount=split_amt
            )
            
            # NOTIFICATION: New Expense
            if split_data['user_id'] != paid_by.id and split_amt > 0:
                NotificationService.create_notification(
                    split_data['user_id'], 
                    f"{paid_by.username} added expense '{description}'. You owe ${split_amt}"
                )
        
        return expense
    
    @staticmethod
    def create_equal_splits(group_id, paid_by, amount, description, 
                           category, participant_ids):
        num_participants = len(participant_ids)
        if num_participants == 0:
            raise ValidationError("At least one participant required")
        
        amount = Decimal(str(amount))
        per_person = amount / num_participants
        per_person = per_person.quantize(Decimal('0.01'))
        
        splits_data = []
        for i, user_id in enumerate(participant_ids):
            if i == num_participants - 1:
                final_amount = amount - (per_person * (num_participants - 1))
            else:
                final_amount = per_person
            
            splits_data.append({
                'user_id': user_id,
                'amount': final_amount
            })
        
        return ExpenseService.create_expense_with_splits(
            group_id=group_id, paid_by=paid_by, amount=amount,
            description=description, category=category, splits_data=splits_data
        )


class SettlementService:
    """
    Service for managing settlements, balance calculations, and debt simplification.
    """
    
    @staticmethod
    def simplify_debts(balances_dict):
        """
        ALGORITHM: Debt Simplification (Min-Cash Flow)
        Instead of A owing B and B owing C, simplifying reduces transactions so A pays C directly.
        
        Args:
            balances_dict: dict of {user_id: net_balance}
        Returns:
            list of dicts: [{'from_user': id, 'to_user': id, 'amount': Decimal}]
        """
        debtors = []
        creditors = []
        
        # Partition into debtors and creditors
        for user_id, balance in balances_dict.items():
            if balance < -Decimal('0.01'):
                debtors.append({'user_id': user_id, 'amount': abs(balance)})
            elif balance > Decimal('0.01'):
                creditors.append({'user_id': user_id, 'amount': balance})
                
        # Sort descending (greedy matching)
        debtors.sort(key=lambda x: x['amount'], reverse=True)
        creditors.sort(key=lambda x: x['amount'], reverse=True)
        
        transactions = []
        i, j = 0, 0
        
        while i < len(debtors) and j < len(creditors):
            debtor = debtors[i]
            creditor = creditors[j]
            
            settle_amount = min(debtor['amount'], creditor['amount'])
            
            transactions.append({
                'from_user': debtor['user_id'],
                'to_user': creditor['user_id'],
                'amount': settle_amount.quantize(Decimal('0.01'))
            })
            
            debtor['amount'] -= settle_amount
            creditor['amount'] -= settle_amount
            
            if debtor['amount'] < Decimal('0.01'):
                i += 1
            if creditor['amount'] < Decimal('0.01'):
                j += 1
                
        return transactions

    @staticmethod
    def calculate_user_balance(user, group):
        total_paid = Expense.objects.filter(group=group, paid_by=user).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        total_owes = Split.objects.filter(user=user, expense__group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        payments_received = Payment.objects.filter(status='COMPLETED', to_user=user, group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        payments_made = Payment.objects.filter(status='COMPLETED', from_user=user, group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        balance = total_paid - total_owes + payments_made - payments_received
        return balance
    
    @staticmethod
    def calculate_balance_between_users(user1, user2, group):
        u1_paid_u2_benefited = Split.objects.filter(user=user2, expense__paid_by=user1, expense__group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        u2_paid_u1_benefited = Split.objects.filter(user=user1, expense__paid_by=user2, expense__group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        u1_paid_u2 = Payment.objects.filter(status='COMPLETED', from_user=user1, to_user=user2, group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        u2_paid_u1 = Payment.objects.filter(status='COMPLETED', from_user=user2, to_user=user1, group=group).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        net = (u1_paid_u2_benefited - u2_paid_u1_benefited) + u1_paid_u2 - u2_paid_u1
        return net
    
    @staticmethod
    @transaction.atomic
    def record_settlement(from_user, to_user, group, amount, description=''):
        amount = Decimal(str(amount))
        
        # FRAUD PREVENTION: Invalid amounts
        if amount <= 0 or amount > Decimal('100000'):
            raise ValidationError("Payment amount must be valid and within limits")
            
        if from_user.id == to_user.id:
            raise ValidationError("Cannot settle payment with yourself")
            
        if not Membership.objects.filter(group=group, user=from_user).exists():
            raise ValidationError("Payer is not in the group")
            
        # FRAUD PREVENTION: Duplicate Transactions
        # Prevent identical payments within 5 minutes
        recent_cutoff = timezone.now() - timedelta(minutes=5)
        is_duplicate = Payment.objects.filter(
            from_user=from_user, to_user=to_user, group=group, 
            amount=amount, status='PENDING', created_at__gte=recent_cutoff
        ).exists()
        
        if is_duplicate:
            raise ValidationError("A similar payment is already pending. Please avoid duplicate clicks.")
            
        actual_balance = SettlementService.calculate_balance_between_users(from_user, to_user, group)
        pending_amount = Payment.objects.filter(from_user=from_user, to_user=to_user, group=group, status='PENDING').aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        if actual_balance < 0:
            max_can_settle = abs(actual_balance) - pending_amount
            if amount > max_can_settle:
                raise ValidationError(f"Cannot overpay. You only owe {abs(actual_balance)} (with {pending_amount} pending)")
        else:
            if amount > 0:
                raise ValidationError("You do not owe this user any money.")
        
        payment = Payment.objects.create(
            from_user=from_user, to_user=to_user, group=group, 
            amount=amount, description=description, status='PENDING'
        )
        
        # NOTIFICATION: Pending payment
        NotificationService.create_notification(
            to_user.id, f"{from_user.username} wants to settle ${amount}. Please confirm."
        )
        
        return payment
    
    @staticmethod
    def get_group_balances(group):
        members = group.memberships.select_related('user').all()
        
        raw_balances = {}
        users_info = {}
        for membership in members:
            user = membership.user
            net_balance = SettlementService.calculate_user_balance(user, group)
            raw_balances[user.id] = net_balance
            users_info[user.id] = {
                'id': user.id, 'username': user.username,
                'email': user.email, 'trust_score': user.trust_score
            }
            
        # Generate optimal simplified transactions
        simplified_debts = SettlementService.simplify_debts(raw_balances)
        
        balances = []
        for uid, net in raw_balances.items():
            balances.append({
                'user': users_info[uid],
                'net_balance': net,
            })
        
        return {
            'balances': balances,
            'simplified_debts': simplified_debts
        }


class TrustScoreService:
    """
    Advanced Trust Score calculation using Time Decay and Weighted Penalties.
    """
    SETTINGS = settings.TRUST_SCORE_SETTINGS
    
    @staticmethod
    def recalculate_score(user):
        """
        Recalculates using Time Decay (recent behavior impacts score more heavily).
        """
        payments = Payment.objects.filter(from_user=user).order_by('-created_at')
        
        score = TrustScoreService.SETTINGS.get('BASE_SCORE', 100)
        
        now = timezone.now()
        late_penalty = 0
        total_payments = payments.count()
        on_time_payments = 0
        
        for payment in payments:
            days_old = (now - payment.created_at).days
            # Exponential decay: weight drops by half roughly every 30 days
            time_weight = math.exp(-0.02 * days_old)
            
            # Simple assumption: if accepted after 7 days, it's late.
            days_to_accept = 0
            if payment.status == 'COMPLETED':
                days_to_accept = (payment.updated_at - payment.created_at).days
            
            if days_to_accept > 7:
                # Weighted penalty (recent delays hurt more)
                late_penalty += 5 * time_weight
            else:
                on_time_payments += 1
                
        # Overdue Penalty for open balances across all groups
        pending_penalty = 0
        groups = Group.objects.filter(memberships__user=user)
        for group in groups:
            bal = SettlementService.calculate_user_balance(user, group)
            if bal < 0:
                # Basic check for how long they've been in debt
                oldest_split = Split.objects.filter(user=user, expense__group=group).order_by('created_at').first()
                if oldest_split:
                    days_overdue = (now - oldest_split.created_at).days
                    if days_overdue > 14:
                        pending_penalty += (days_overdue // 7) * 2
        
        consistency_bonus = 0
        if total_payments >= 5 and on_time_payments == total_payments:
            consistency_bonus = 5
            
        final_score = max(0, min(100, int(score - late_penalty - pending_penalty + consistency_bonus)))
        
        old_score = user.trust_score
        if old_score != final_score:
            user.trust_score = final_score
            user.trust_score_updated_at = now
            user.save(update_fields=['trust_score', 'trust_score_updated_at'])
            
            # NOTIFICATION: Score Change
            if final_score < old_score:
                NotificationService.create_notification(user.id, f"Your trust score decreased to {final_score}.")
            elif final_score > old_score:
                NotificationService.create_notification(user.id, f"Great job! Your trust score increased to {final_score}.")
            
        return final_score
