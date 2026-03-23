from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Task, UserTask

@admin.register(Task)
class TaskAdmin(ModelAdmin):
    list_display = ('title', 'task_type', 'reward_coin', 'is_active', 'created_at')
    list_filter = ('task_type', 'is_active')
    search_fields = ('title', 'chat_id')

@admin.register(UserTask)
class UserTaskAdmin(ModelAdmin):
    list_display = ('user', 'task', 'is_completed', 'completed_at')
    list_filter = ('is_completed',)
    search_fields = ('user__username', 'task__title')
