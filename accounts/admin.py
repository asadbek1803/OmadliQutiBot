from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ('username', 'telegram_id', 'is_active', 'is_blocked', 'is_suspected_fraud', 'referral_count', 'date_joined')
    search_fields = ('username', 'telegram_id', 'first_name', 'last_name', 'referral_code')
    list_filter = ('is_active', 'is_blocked', 'is_suspected_fraud', 'is_premium_telegram')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Telegram Info', {'fields': ('telegram_id', 'language_code', 'is_premium_telegram', 'is_blocked', 'is_suspected_fraud')}),
        ('Referrals', {'fields': ('referred_by', 'referral_code', 'referral_count')}),
    )
