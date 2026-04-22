"""
Django signals for expense app.
Trigger automatic actions when models are saved.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.expenses.models import Payment
from apps.expenses.services import TrustScoreService


@receiver(post_save, sender=Payment)
def update_trust_score_on_settlement(sender, instance, created, **kwargs):
    """
    Update payer's trust score when payment is recorded.
    
    This is called every time a Payment is saved.
    Only recalculate if it's a new payment (created=True).
    """
    if created:
        # Recalculate trust score for the payer
        TrustScoreService.recalculate_score(instance.from_user)
