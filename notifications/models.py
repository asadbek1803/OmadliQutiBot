from django.db import models
from django.conf import settings
from django.utils import timezone

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('withdrawal_approved', 'To\'lov tasdiqlandi'),
        ('withdrawal_rejected', 'To\'lov rad etildi'),
        ('reward_won', 'Yutuq qo\'lga kiritildi'),
        ('premium_won', 'Telegram Premium yutildi'),
        ('referral_joined', 'Referal ro\'yxatdan o\'tdi'),
        ('task_completed', 'Topshiriq bajarildi'),
        ('task_added', 'Yangi topshiriq qo\'shildi'),
        ('daily_bonus', 'Kunlik bonus'),
        ('level_up', 'Daraja ko\'tarildi'),
        ('system_message', 'Tizim xabari'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True, help_text="Additional notification data")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    @classmethod
    def create_notification(cls, user, notification_type, title, message, data=None):
        """
        Create a new notification for a user
        """
        return cls.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {}
        )

    @classmethod
    def create_bulk_notification(cls, users, notification_type, title, message, data=None):
        """
        Create notifications for multiple users at once
        """
        notifications = []
        for user in users:
            notifications.append(cls(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data or {}
            ))
        return cls.objects.bulk_create(notifications)

    @classmethod
    def get_unread_count(cls, user):
        """
        Get unread notification count for a user
        """
        return cls.objects.filter(user=user, is_read=False).count()

    @classmethod
    def get_recent_notifications(cls, user, limit=10):
        """
        Get recent notifications for a user
        """
        return cls.objects.filter(user=user).order_by('-created_at')[:limit]

class NotificationPreference(models.Model):
    """
    User notification preferences
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Email notifications
    email_withdrawal_approved = models.BooleanField(default=True)
    email_withdrawal_rejected = models.BooleanField(default=True)
    email_reward_won = models.BooleanField(default=True)
    email_premium_won = models.BooleanField(default=True)
    email_referral_joined = models.BooleanField(default=True)
    
    # Push notifications (for future implementation)
    push_withdrawal_approved = models.BooleanField(default=True)
    push_withdrawal_rejected = models.BooleanField(default=True)
    push_reward_won = models.BooleanField(default=True)
    push_premium_won = models.BooleanField(default=True)
    push_referral_joined = models.BooleanField(default=True)
    
    # In-app notifications
    app_withdrawal_approved = models.BooleanField(default=True)
    app_withdrawal_rejected = models.BooleanField(default=True)
    app_reward_won = models.BooleanField(default=True)
    app_premium_won = models.BooleanField(default=True)
    app_referral_joined = models.BooleanField(default=True)
    app_task_completed = models.BooleanField(default=True)
    app_task_added = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} Preferences"

    @classmethod
    def get_or_create_preferences(cls, user):
        """
        Get or create notification preferences for a user
        """
        preferences, created = cls.objects.get_or_create(user=user)
        return preferences
