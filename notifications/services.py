from django.utils import timezone
from django.db.models import signals
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Notification, NotificationPreference

User = get_user_model()

class NotificationService:
    """
    Service for managing notifications
    """
    
    @staticmethod
    def send_notification(user, notification_type, title, message, data=None):
        """
        Send a notification to a user
        """
        # Check user preferences
        preferences = NotificationPreference.get_or_create_preferences(user)
        
        # Check if user wants this type of notification
        if not NotificationService._should_send_notification(preferences, notification_type, 'app'):
            return None
        
        return Notification.create_notification(user, notification_type, title, message, data)
    
    @staticmethod
    def send_bulk_notification(users, notification_type, title, message, data=None):
        """
        Send notifications to multiple users
        """
        notifications = []
        for user in users:
            preferences = NotificationPreference.get_or_create_preferences(user)
            if NotificationService._should_send_notification(preferences, notification_type, 'app'):
                notifications.append(Notification(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    data=data or {}
                ))
        
        if notifications:
            return Notification.objects.bulk_create(notifications)
        return []
    
    @staticmethod
    def _should_send_notification(preferences, notification_type, channel):
        """
        Check if user should receive notification based on preferences
        """
        preference_map = {
            'app': {
                'withdrawal_approved': preferences.app_withdrawal_approved,
                'withdrawal_rejected': preferences.app_withdrawal_rejected,
                'reward_won': preferences.app_reward_won,
                'premium_won': preferences.app_premium_won,
                'referral_joined': preferences.app_referral_joined,
                'task_completed': preferences.app_task_completed,
                'task_added': preferences.app_task_added,
            },
            'email': {
                'withdrawal_approved': preferences.email_withdrawal_approved,
                'withdrawal_rejected': preferences.email_withdrawal_rejected,
                'reward_won': preferences.email_reward_won,
                'premium_won': preferences.email_premium_won,
                'referral_joined': preferences.email_referral_joined,
            }
        }
        
        return preference_map.get(channel, {}).get(notification_type, True)

    @staticmethod
    def mark_all_as_read(user):
        """
        Mark all notifications as read for a user
        """
        unread_notifications = Notification.objects.filter(user=user, is_read=False)
        count = unread_notifications.count()
        unread_notifications.update(is_read=True, read_at=timezone.now())
        return count

    @staticmethod
    def get_notification_stats(user):
        """
        Get notification statistics for a user
        """
        total = Notification.objects.filter(user=user).count()
        unread = Notification.objects.filter(user=user, is_read=False).count()
        
        # Count by type
        type_counts = {}
        for notification_type, _ in Notification.NOTIFICATION_TYPES:
            type_counts[notification_type] = Notification.objects.filter(
                user=user, 
                notification_type=notification_type
            ).count()
        
        return {
            'total': total,
            'unread': unread,
            'type_counts': type_counts
        }

# Event handlers for automatic notifications
@receiver(signals.post_save, sender='withdrawals.RewardRequest')
def withdrawal_status_changed(sender, instance, created, **kwargs):
    """
    Send notification when withdrawal status changes
    """
    if not created:  # Only on status change, not creation
        if instance.status == 'approved':
            NotificationService.send_notification(
                user=instance.user,
                notification_type='withdrawal_approved',
                title='To\'lov tasdiqlandi!',
                message=f"Sizning {instance.amount_coin} coinlik so'rovingiz tasdiqlandi. Pul tez orada o'tkaziladi.",
                data={
                    'amount': instance.amount_coin,
                    'request_id': instance.id,
                    'card_number': instance.masked_card
                }
            )
            # Send notification to all admins
            _send_admin_notification(
                notification_type='withdrawal_approved',
                title=f'🔔 Yangi to\'lov tasdiqlandi',
                message=f'{instance.user.username} foydalanuvchining {instance.amount_coin} coinlik so\'rovi tasdiqlandi.',
                data={
                    'user_id': instance.user.id,
                    'username': instance.user.username,
                    'amount': instance.amount_coin,
                    'request_id': instance.id
                }
            )
        elif instance.status == 'rejected':
            NotificationService.send_notification(
                user=instance.user,
                notification_type='withdrawal_rejected',
                title='To\'lov rad etildi',
                message=f"Sizning {instance.amount_coin} coinlik so'rovingiz rad etildi. Sabab: {instance.admin_comment or 'Noma\'lum'}",
                data={
                    'amount': instance.amount_coin,
                    'request_id': instance.id,
                    'reason': instance.admin_comment
                }
            )
            # Send notification to all admins
            _send_admin_notification(
                notification_type='withdrawal_rejected',
                title=f'❌ To\'lov rad etildi',
                message=f'{instance.user.username} foydalanuvchining {instance.amount_coin} coinlik so\'rovi rad etildi. Sabab: {instance.admin_comment or "Noma\'lum"}',
                data={
                    'user_id': instance.user.id,
                    'username': instance.user.username,
                    'amount': instance.amount_coin,
                    'request_id': instance.id,
                    'reason': instance.admin_comment
                }
            )
        elif instance.status == 'pending' and created:
            # Send notification to admins when new withdrawal request is created
            _send_admin_notification(
                notification_type='new_withdrawal',
                title=f'💰 Yangi pul yechish so\'rovi',
                message=f'{instance.user.username} foydalanuvchi {instance.amount_coin} coin pul yechishni so\'radi.',
                data={
                    'user_id': instance.user.id,
                    'username': instance.user.username,
                    'amount': instance.amount_coin,
                    'request_id': instance.id,
                    'card_type': instance.card_label,
                    'card_number': instance.masked_card
                }
            )

@receiver(signals.post_save, sender='rewards.TelegramPremiumReward')
def premium_reward_updated(sender, instance, created, **kwargs):
    """
    Send notification when Telegram Premium reward is updated
    """
    if created:
        # User won Telegram Premium
        NotificationService.send_notification(
            user=instance.user,
            notification_type='premium_won',
            title='🎉 Tabriklaymiz! Telegram Premium yutdingiz!',
            message=f"Siz {instance.months} oylik Telegram Premium yutdingiz! Tasdiqlash kodi: {instance.verification_code}",
            data={
                'reward_id': instance.id,
                'months': instance.months,
                'verification_code': instance.verification_code,
                'coin_value': instance.coin_value
            }
        )
        # Send notification to all admins
        _send_admin_notification(
            notification_type='premium_won',
            title=f'👑 Foydalanuvchi Telegram Premium yutdi',
            message=f'{instance.user.username} foydalanuvchi {instance.months} oylik Telegram Premium yutdi!',
            data={
                'user_id': instance.user.id,
                'username': instance.user.username,
                'reward_id': instance.id,
                'months': instance.months,
                'coin_value': instance.coin_value
            }
        )
    elif instance.status == 'verified' and instance._status_was_not_verified:
        # Premium reward was verified by admin
        _send_admin_notification(
            notification_type='premium_verified',
            title=f'✅ Telegram Premium tasdiqlandi',
            message=f'{instance.user.username} foydalanuvchining {instance.months} oylik Telegram Premium sovg\'asi tasdiqlandi.',
            data={
                'user_id': instance.user.id,
                'username': instance.user.username,
                'reward_id': instance.id,
                'months': instance.months,
                'verified_by': instance.admin_notes
            }
        )

def _send_admin_notification(notification_type, title, message, data=None):
    """
    Send notification to all admin users
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Get all admin users
    admin_users = User.objects.filter(is_staff=True)
    
    for admin in admin_users:
        NotificationService.send_notification(
            user=admin,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {}
        )

@receiver(signals.post_save, sender='rewards.TelegramPremiumReward')
def premium_reward_updated(sender, instance, created, **kwargs):
    """
    Send notification for premium reward updates
    """
    if created and instance.status == 'pending':
        NotificationService.send_notification(
            user=instance.user,
            notification_type='premium_won',
            title='🎉 Telegram Premium yutdingiz!',
            message=f'Tabriklaymiz! Siz {instance.months} oylik Telegram Premium yutdingiz. Tasdiqlash kodi: {instance.verification_code}',
            data={
                'reward_id': instance.id,
                'months': instance.months,
                'verification_code': instance.verification_code,
                'coin_value': instance.coin_value
            }
        )
        # Send notification to all admins
        _send_admin_notification(
            notification_type='premium_won',
            title=f'👑 Foydalanuvchi Telegram Premium yutdi',
            message=f'{instance.user.username} foydalanuvchi {instance.months} oylik Telegram Premium yutdi!',
            data={
                'user_id': instance.user.id,
                'username': instance.user.username,
                'reward_id': instance.id,
                'months': instance.months,
                'coin_value': instance.coin_value
            }
        )

@receiver(signals.post_save, sender='accounts.User')
def user_joined(sender, instance, created, **kwargs):
    """
    Send notification to referrer when new user joins
    """
    if created and instance.referred_by:
        NotificationService.send_notification(
            user=instance.referred_by,
            notification_type='referral_joined',
            title='👥 Yangi referal!',
            message=f'{instance.first_name or instance.username} sizning referalingiz bo\'lib ro\'yxatdan o\'tdi!',
            data={
                'new_user_id': instance.id,
                'new_user_name': instance.first_name or instance.username,
                'new_user_telegram_id': instance.telegram_id
            }
        )

@receiver(signals.post_save, sender='tasks.UserTask')
def task_completed(sender, instance, created, **kwargs):
    """
    Send notification when task is completed
    """
    if not created and instance.is_completed and not hasattr(instance, '_notification_sent'):
        NotificationService.send_notification(
            user=instance.user,
            notification_type='task_completed',
            title='✅ Topshiriq bajarildi!',
            message=f'"{instance.task.title}" topshirig\'i muvaffaqiyatli bajarildi va {instance.task.reward_coin} coin berildi!',
            data={
                'task_id': instance.task.id,
                'task_title': instance.task.title,
                'reward': instance.task.reward_coin
            }
        )
        # Mark that notification was sent to avoid duplicates
        instance._notification_sent = True
