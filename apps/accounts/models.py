"""
Models for accounts app.
Defines User model with authentication and trust score functionality.
"""

from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model extending Django's AbstractUser.
    
    Adds financial-specific fields:
    - trust_score: Behavioral metric for payment reliability (0-100)
    - bio: Optional user biography
    - phone: Optional phone number
    
    Rationale for extending AbstractUser:
    - Allows future customization of authentication
    - Cleaner than using a Profile model
    - Recommended by Django best practices
    """
    
    # Financial metrics
    trust_score = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Payment reliability score (0-100, higher is better)"
    )
    trust_score_updated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When trust score was last recalculated"
    )
    
    # User profile fields
    bio = models.TextField(
        blank=True,
        help_text="User biography"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="User's phone number"
    )
    age = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text="User's age"
    )
    location = models.CharField(
        max_length=100,
        blank=True,
        help_text="Where the user lives"
    )
    occupation = models.CharField(
        max_length=100,
        blank=True,
        help_text="User's occupation"
    )
    university = models.CharField(
        max_length=100,
        blank=True,
        help_text="University name if student"
    )
    avatar_url = models.URLField(
        blank=True,
        help_text="URL to user's profile picture"
    )
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = '"user"'  # Use lowercase 'user' in database
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['trust_score'], name='idx_user_trust_score'),
        ]
    
    def __str__(self):
        return f"{self.username} (Trust: {self.trust_score})"
    
    @property
    def trust_level(self):
        """
        Human-readable trust level based on score.
        
        Returns:
            str: One of 'Excellent', 'Good', 'Fair', 'Poor', 'Very Poor'
        """
        if self.trust_score >= 90:
            return "Excellent"
        elif self.trust_score >= 75:
            return "Good"
        elif self.trust_score >= 50:
            return "Fair"
        elif self.trust_score >= 25:
            return "Poor"
        else:
            return "Very Poor"
    
    @property
    def full_name(self):
        """
        Returns user's full name or username as fallback.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        return self.username


class TrustScoreAudit(models.Model):
    """
    Audit log for trust score changes.
    
    Why maintain an audit log?
    - Transparency: Users can see why their score changed
    - Debugging: System operators can track score computation
    - Compliance: Financial regulations require audit trails
    
    Immutable record of every score update.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='trust_score_history'
    )
    
    old_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    new_score = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    reason = models.CharField(
        max_length=255,
        help_text="Why the score changed (e.g., 'payment_recorded', 'overdue_detected')"
    )
    
    # Detailed metrics snapshot at time of calculation
    metrics = models.JSONField(
        default=dict,
        help_text="Snapshot of metrics used in calculation"
    )
    
    computed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'trust_score_audit'
        ordering = ['-computed_at']
        indexes = [
            models.Index(fields=['user', '-computed_at']),
        ]
    
    def __str__(self):
        return f"{self.user.username}: {self.old_score} → {self.new_score} ({self.reason})"
