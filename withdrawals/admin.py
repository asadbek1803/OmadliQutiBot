from django.contrib import admin
from unfold.admin import ModelAdmin
from django.utils import timezone
from .models import RewardRequest, RewardRequestConfig
from wallet.models import Wallet, Ledger

@admin.action(description='Approve selected requests (Releases reserve)')
def approve_requests(modeladmin, request, queryset):
    for obj in queryset.filter(status='pending'):
        wallet = obj.user.wallet
        # Release from reserved and deduct
        if wallet.reserved_coin_balance >= obj.amount_coin:
            wallet.reserved_coin_balance -= obj.amount_coin
            wallet.save()
            obj.status = 'approved'
            obj.processed_at = timezone.now()
            obj.processed_by = request.user
            obj.save()
            
            Ledger.objects.create(
                user=obj.user,
                type='reward_request_approved',
                amount=0,
                balance_before=wallet.coin_balance, # already deducted from main balance during reserve
                balance_after=wallet.coin_balance,
                note=f"Approved req #{obj.id}"
            )

@admin.action(description='Reject selected requests (Refunds reserve)')
def reject_requests(modeladmin, request, queryset):
    for obj in queryset.filter(status='pending'):
        wallet = obj.user.wallet
        # Refund to main balance
        if wallet.reserved_coin_balance >= obj.amount_coin:
            before_balance = wallet.coin_balance
            wallet.reserved_coin_balance -= obj.amount_coin
            wallet.coin_balance += obj.amount_coin
            wallet.save()
            obj.status = 'rejected'
            obj.processed_at = timezone.now()
            obj.processed_by = request.user
            obj.save()
            
            Ledger.objects.create(
                user=obj.user,
                type='reward_request_release',
                amount=obj.amount_coin,
                balance_before=before_balance,
                balance_after=wallet.coin_balance,
                note=f"Rejected req #{obj.id}, refunded."
            )

@admin.register(RewardRequest)
class RewardRequestAdmin(ModelAdmin):
    list_display = ('user', 'amount_coin', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'card_label', 'holder_name')
    actions = [approve_requests, reject_requests]

@admin.register(RewardRequestConfig)
class RewardRequestConfigAdmin(ModelAdmin):
    list_display = ('__str__', 'min_coin_threshold', 'is_enabled')
