from django.db import models
from django.conf import settings

class Reward(models.Model):
    REWARD_TYPES = (
        ('small_coin', 'Small Coin'),
        ('medium_coin', 'Medium Coin'),
        ('big_coin', 'Big Coin'),
        ('extra_spin', 'Extra Spin'),
        ('premium_day', 'Premium Day'),
        ('telegram_premium', 'Telegram Premium'),
        ('jackpot_virtual', 'Virtual Jackpot'),
        ('miss', 'Miss (Try Again)'),
        ('referral_boost', 'Referral Boost'),
        ('custom_bonus', 'Custom Bonus'),
    )

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    reward_type = models.CharField(max_length=30, choices=REWARD_TYPES)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=20, blank=True, null=True, help_text="Emoji")
    image = models.ImageField(upload_to='rewards/', blank=True, null=True)
    probability_weight = models.PositiveIntegerField(default=10)
    coin_amount = models.PositiveIntegerField(default=0)
    premium_days = models.PositiveIntegerField(default=0)
    extra_spins = models.PositiveIntegerField(default=0)
    telegram_premium_months = models.PositiveIntegerField(default=0, help_text="Telegram Premium subscription months")
    telegram_premium_coin_value = models.PositiveIntegerField(default=5000, help_text="Coin value if user chooses to convert to coins")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)
    is_jackpot_like = models.BooleanField(default=False)
    color_tag = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.name} ({self.get_reward_type_display()})"

class TelegramPremiumReward(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('redeemed', 'Redeemed'),
        ('converted', 'Converted to Coins'),
        ('expired', 'Expired'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='telegram_premium_rewards')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE, related_name='premium_instances')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verification_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    months = models.PositiveIntegerField(default=1)
    coin_value = models.PositiveIntegerField(default=5000)
    verified_at = models.DateTimeField(null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track status changes for notifications
        self._status_was_not_verified = self.status != 'verified'

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.months} months Telegram Premium ({self.status})"

    def generate_verification_code(self):
        import random, string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        self.verification_code = code
        self.save()
        return code

    def is_expired(self):
        from django.utils import timezone
        return self.expires_at and self.expires_at < timezone.now()

    def mark_as_verified(self):
        from django.utils import timezone
        from datetime import timedelta
        self.status = 'verified'
        self.verified_at = timezone.now()
        self.expires_at = timezone.now() + timedelta(days=30)  # 30 days to redeem
        self.save()

    def redeem_premium(self):
        from django.utils import timezone
        if self.status == 'verified' and not self.is_expired():
            self.status = 'redeemed'
            self.redeemed_at = timezone.now()
            self.save()
            return True
        return False

    def convert_to_coins(self):
        from django.utils import timezone
        from django.db import transaction
        from wallet.models import Wallet, Ledger
        
        if self.status == 'verified' and not self.is_expired():
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=self.user)
                before_balance = wallet.coin_balance
                wallet.coin_balance += self.coin_value
                wallet.earned_coin_total += self.coin_value
                wallet.save()
                
                Ledger.objects.create(
                    user=self.user,
                    type='premium_conversion',
                    amount=self.coin_value,
                    balance_before=before_balance,
                    balance_after=wallet.coin_balance,
                    reference_type='telegram_premium',
                    reference_id=str(self.id),
                    note=f"Telegram Premium konvertatsiyasi ({self.months} oy)"
                )
                
                self.status = 'converted'
                self.redeemed_at = timezone.now()
                self.save()
                
                return wallet.coin_balance
        return None

class SpinBoard(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    spin_cost = models.PositiveIntegerField(default=50)
    free_spins_per_day = models.PositiveIntegerField(default=1)
    max_rewards_visible = models.PositiveIntegerField(blank=True, null=True, help_text="Limits rewards showing on UI")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class SpinBoardReward(models.Model):
    spin_board = models.ForeignKey(SpinBoard, on_delete=models.CASCADE, related_name='board_rewards')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE, related_name='in_boards')
    board_weight_override = models.PositiveIntegerField(blank=True, null=True, help_text="Overrides default weight")
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['display_order']
        unique_together = ('spin_board', 'reward')

    @property
    def weight(self):
        if self.board_weight_override is not None:
            return self.board_weight_override
        return self.reward.probability_weight

    def __str__(self):
        return f"{self.spin_board.name} -> {self.reward.name}"

class DailyBonusConfig(models.Model):
    is_active = models.BooleanField(default=True)
    coin_amount = models.PositiveIntegerField(default=10)
    extra_spins = models.PositiveIntegerField(default=0)
    streak_enabled = models.BooleanField(default=False)
    streak_rules_json = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"Daily Bonus (coins: {self.coin_amount})"
