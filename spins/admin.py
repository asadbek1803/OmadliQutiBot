from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import SpinLog

@admin.register(SpinLog)
class SpinLogAdmin(ModelAdmin):
    list_display = ('user', 'spin_board', 'reward_type_snapshot', 'reward_value_snapshot', 'was_free_spin', 'created_at')
    list_filter = ('was_free_spin', 'spin_board', 'reward_type_snapshot', 'created_at')
    search_fields = ('user__username', 'user__telegram_id')
    readonly_fields = [f.name for f in SpinLog._meta.fields]
    fields = readonly_fields
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
