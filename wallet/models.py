from django.db import models
from django.conf import settings

class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    coin_balance = models.PositiveIntegerField(default=0)
    reserved_coin_balance = models.PositiveIntegerField(default=0)
    earned_coin_total = models.PositiveIntegerField(default=0)
    spent_coin_total = models.PositiveIntegerField(default=0)
    referral_coin_total = models.PositiveIntegerField(default=0)
    daily_bonus_claimed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.username} - Coins: {self.coin_balance}'

class Ledger(models.Model):
    TRANSACTION_TYPES = (
        ('reward', 'Reward'),
        ('referral_bonus', 'Referral Bonus'),
        ('welcome_bonus', 'Welcome Bonus'),
        ('daily_bonus', 'Daily Bonus'),
        ('spin_cost', 'Spin Cost'),
        ('adjustment', 'Adjustment'),
        ('reward_request_reserve', 'Reward Request Reserve'),
        ('reward_request_release', 'Reward Request Release'),
        ('reward_request_approved', 'Reward Request Approved'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ledger_entries')
    type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    amount = models.IntegerField()
    balance_before = models.PositiveIntegerField()
    balance_after = models.PositiveIntegerField()
    reference_type = models.CharField(max_length=50, blank=True, null=True)
    reference_id = models.CharField(max_length=50, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} | {self.type} | {self.amount} | {self.created_at}'
