from django.db import models
from django.conf import settings

class RewardRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('fulfilled', 'Fulfilled'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reward_requests')
    amount_coin = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    card_label = models.CharField(max_length=50, blank=True, null=True, help_text="e.g Uzcard, Humo, Visa")
    masked_card = models.CharField(max_length=20, blank=True, null=True, help_text="e.g **** 1234")
    holder_name = models.CharField(max_length=100, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    admin_comment = models.TextField(blank=True, null=True)
    screenshot = models.ImageField(upload_to='withdrawal_screenshots/', blank=True, null=True, help_text="Screenshot of deposited money")
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='processed_requests')

    def __str__(self):
        return f"{self.user.username} - {self.amount_coin} coins ({self.status})"

class RewardRequestConfig(models.Model):
    min_coin_threshold = models.PositiveIntegerField(default=1000)
    max_pending_per_user = models.PositiveIntegerField(default=1)
    coin_to_uzs_rate = models.PositiveIntegerField(default=100, help_text="1 Coin necha so'mligini belgilaydi")
    is_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"Config: Min {self.min_coin_threshold} coins"
