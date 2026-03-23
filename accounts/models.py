from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    telegram_id = models.BigIntegerField(unique=True, db_index=True, null=True, blank=True)
    language_code = models.CharField(max_length=10, blank=True, null=True)
    is_premium_telegram = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_blocked = models.BooleanField(default=False)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    referral_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    referral_count = models.PositiveIntegerField(default=0)
    is_suspected_fraud = models.BooleanField(default=False)

    # We can use the username from AbstractUser or define dynamic ones based on Telegram id
    
    def __str__(self):
        return f'{self.username} (TG: {self.telegram_id})'
