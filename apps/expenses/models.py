"""
Models for expenses app.
Defines Expense, Split (individual shares), and Payment (settlement) models.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal

User = get_user_model()


class Expense(models.Model):
    """
    Represents a shared expense within a group.
    
    Design rationale:
    - No "settled" field: settlement recorded in Payment model instead
    - paid_by tracks who paid (not necessarily who created expense)
    - Splits store individual shares (not stored on Expense)
    - Immutable: expenses are never modified/deleted (audit trail)
    
    Example workflow:
    1. Alice creates expense: pays $300 for hotel
    2. System creates 3 Split records (one for each participant)
    3. Over time, participants settle their shares via Payment records
    4. Balance calculated: total_paid - total_split - total_paid_to=user
    """
    
    CATEGORY_CHOICES = (
        ('accommodation', 'Accommodation'),
        ('food', 'Food & Dining'),
        ('transport', 'Transportation'),
        ('entertainment', 'Entertainment'),
        ('utilities', 'Utilities'),
        ('shopping', 'Shopping'),
        ('other', 'Other'),
    )
    
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    paid_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expenses_paid'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total expense amount in group's currency"
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        help_text="What was the expense for?"
    )
    category = models.CharField(
        max_length=100,
        choices=CATEGORY_CHOICES,
        default='other'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'expense'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['group']),
            models.Index(fields=['paid_by']),
            models.Index(fields=['created_at']),
            models.Index(fields=['group', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.description} - {self.amount} (paid by {self.paid_by.username})"
    
    def get_total_split(self):
        """
        Get sum of all splits for this expense.
        
        Should equal self.amount, but we compute to verify consistency.
        """
        return self.splits.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
    
    def is_fully_split(self):
        """Check if splits sum to total amount (for validation)."""
        return self.get_total_split() == self.amount


class Split(models.Model):
    """
    Individual share of an expense for a user.
    
    Design rationale:
    - Separate model from Expense allows flexible splitting
    - Supports equal splits, manual splits, or complex allocations
    - Each split is immutable (audit trail)
    - Amount must be >= 0 (not strictly > 0, in case of edge cases)
    
    Key invariant (enforced in service layer):
    For each expense: SUM(split.amount) == expense.amount
    
    Example:
    Expense "Pizza" = $30
    Splits:
      - Alice: $15
      - Bob: $10
      - Charlie: $5
    """
    
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='splits'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='expense_splits'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount this user owes for this expense"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'split'
        unique_together = ('expense', 'user')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['expense']),
            models.Index(fields=['user', 'expense']),
        ]
    
    def __str__(self):
        return f"{self.user.username} owes {self.amount} for {self.expense.description}"


class Payment(models.Model):
    """
    Settlement payment: actual money transfer between two users.
    
    Design rationale:
    - Directional: from_user → to_user (clear who paid whom)
    - Immutable: payments are never deleted/modified (audit trail)
    - Used for:
      1. Calculating balances (with Splits)
      2. Updating trust scores (payment timing)
      3. Proving settlement history
    
    Invariant (enforced in application):
    from_user_id != to_user_id (can't pay yourself)
    
    Example:
    Alice pays Bob $75 for hotel split
    Payment:
      from_user: Alice
      to_user: Bob
      amount: $75
      group: Summer Trip
      status: pending -> accepted
    """
    
    STATUS_CHOICES = (
        ('pending', 'Pending Confirmation'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    )
    
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments_made'
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments_received'
    )
    group = models.ForeignKey(
        'groups.Group',
        on_delete=models.CASCADE,
        related_name='payments'
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Settlement amount"
    )
    description = models.CharField(
        max_length=500,
        blank=True,
        help_text="Payment description (e.g., 'Settled for split dinner')"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text="Settlement confirmation status"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'payment'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['from_user']),
            models.Index(fields=['to_user']),
            models.Index(fields=['group']),
            models.Index(fields=['created_at']),
            models.Index(fields=['from_user', 'to_user', 'group']),
        ]
    
    def __str__(self):
        return f"{self.from_user.username} → {self.to_user.username}: {self.amount}"
    
    def clean(self):
        """Validate that payment is not to/from same user."""
        if self.from_user_id == self.to_user_id:
            raise ValidationError("Cannot settle payment with yourself.")
    
    def save(self, *args, **kwargs):
        """Run full_clean() before saving."""
        self.full_clean()
        super().save(*args, **kwargs)
