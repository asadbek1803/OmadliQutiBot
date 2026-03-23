from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ReferralRelationship, ReferralTransactionLog, ReferralVisit

@admin.register(ReferralRelationship)
class ReferralRelationshipAdmin(ModelAdmin):
    list_display = ('inviter', 'invited_user', 'inviter_bonus_granted', 'created_at')
    search_fields = ('inviter__username', 'invited_user__username')

@admin.register(ReferralTransactionLog)
class ReferralTransactionLogAdmin(ModelAdmin):
    list_display = ('inviter', 'invited_user', 'amount_to_inviter', 'reason', 'created_at')
    
@admin.register(ReferralVisit)
class ReferralVisitAdmin(ModelAdmin):
    list_display = ('code', 'visitor_telegram_id', 'created_at')
