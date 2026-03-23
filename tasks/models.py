from django.db import models
from django.conf import settings
from django.utils import timezone

class Task(models.Model):
    TASK_TYPES = (
        ('telegram', 'Telegram Channel'),
        ('youtube', 'YouTube Video'),
        ('twitter', 'Twitter Follow'),
        ('other', 'Sponsor Link')
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    reward_coin = models.PositiveIntegerField(default=100)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, default='telegram')
    link = models.URLField()
    chat_id = models.CharField(max_length=100, blank=True, null=True, help_text='Only for telegram (e.g. @channelusername or -100...)')
    is_active = models.BooleanField(default=True)
    verification_cooldown_minutes = models.PositiveIntegerField(default=5, help_text="Minimum time between verification attempts")
    max_verification_attempts = models.PositiveIntegerField(default=3, help_text="Maximum verification attempts per user")
    requires_screenshot = models.BooleanField(default=False, help_text="Whether task requires screenshot verification")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.get_task_type_display()}] {self.title}"

class UserTask(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='completed_tasks')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='user_completions')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    verification_attempts = models.PositiveIntegerField(default=0, help_text="Number of verification attempts made")
    last_verification_attempt = models.DateTimeField(null=True, blank=True, help_text="Last time user tried to verify this task")
    verification_method = models.CharField(max_length=20, blank=True, null=True, help_text="How the task was verified")
    screenshot = models.ImageField(upload_to='task_screenshots/', blank=True, null=True, help_text="Screenshot for task verification")
    admin_verified = models.BooleanField(default=False, help_text="Whether admin has manually verified this task")
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin notes about verification")

    class Meta:
        unique_together = ('user', 'task')
        
    def __str__(self):
        return f"{self.user.username} - {self.task.title}"
    
    def can_attempt_verification(self):
        """Check if user can attempt verification based on cooldown and attempts limit"""
        if self.is_completed:
            return False, "Task already completed"
        
        if self.verification_attempts >= self.task.max_verification_attempts:
            return False, "Maximum verification attempts reached"
        
        if self.last_verification_attempt:
            time_since_last = timezone.now() - self.last_verification_attempt
            cooldown_minutes = self.task.verification_cooldown_minutes
            if time_since_last.total_seconds() < cooldown_minutes * 60:
                remaining_minutes = int((cooldown_minutes * 60 - time_since_last.total_seconds()) / 60)
                return False, f"Please wait {remaining_minutes} minutes before next attempt"
        
        return True, "Verification allowed"
