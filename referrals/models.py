from django.db import models
from django.conf import settings

class ReferralVisit(models.Model):
    code = models.CharField(max_length=20)
    visitor_telegram_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ReferralRelationship(models.Model):
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invited_users')
    invited_user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='invitation')
    inviter_bonus_granted = models.PositiveIntegerField(default=0)
    invited_bonus_granted = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class ReferralTransactionLog(models.Model):
    inviter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referral_gains')
    invited_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referred_rewards')
    amount_to_inviter = models.PositiveIntegerField(default=0)
    amount_to_invited = models.PositiveIntegerField(default=0)
    reason = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
