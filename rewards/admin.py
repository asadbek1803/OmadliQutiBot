from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import Reward, SpinBoard, SpinBoardReward, DailyBonusConfig

@admin.register(Reward)
class RewardAdmin(ModelAdmin):
    list_display = ('name', 'reward_type', 'coin_amount', 'probability_weight', 'is_active', 'is_visible')
    list_filter = ('reward_type', 'is_active', 'is_visible')
    search_fields = ('name', 'description')

class SpinBoardRewardInline(TabularInline):
    model = SpinBoardReward
    extra = 1

@admin.register(SpinBoard)
class SpinBoardAdmin(ModelAdmin):
    list_display = ('name', 'is_active', 'spin_cost', 'free_spins_per_day')
    inlines = [SpinBoardRewardInline]
    prepopulated_fields = {'slug': ('name',)}

@admin.register(DailyBonusConfig)
class DailyBonusConfigAdmin(ModelAdmin):
    list_display = ('__str__', 'is_active', 'coin_amount', 'extra_spins', 'streak_enabled')
