from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Wallet, Ledger

@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = ('user', 'coin_balance', 'reserved_coin_balance', 'earned_coin_total', 'updated_at')
    search_fields = ('user__username', 'user__telegram_id')

@admin.register(Ledger)
class LedgerAdmin(ModelAdmin):
    list_display = ('user', 'type', 'amount', 'balance_after', 'created_at')
    list_filter = ('type', 'created_at')
    search_fields = ('user__username', 'user__telegram_id', 'note', 'reference_id')
    readonly_fields = ('user', 'type', 'amount', 'balance_before', 'balance_after', 'reference_type', 'reference_id', 'created_at')
