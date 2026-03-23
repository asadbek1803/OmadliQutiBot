from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.core.paginator import Paginator
import json

from .models import Notification, NotificationPreference
from .services import NotificationService

class NotificationListView(LoginRequiredMixin, ListView):
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['unread_count'] = Notification.get_unread_count(self.request.user)
        context['stats'] = NotificationService.get_notification_stats(self.request.user)
        return context

@require_GET
@login_required
def api_notifications_list(request):
    """Get user's notifications with pagination"""
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    unread_only = request.GET.get('unread_only', 'false').lower() == 'true'
    
    notifications = Notification.objects.filter(user=request.user)
    
    if unread_only:
        notifications = notifications.filter(is_read=False)
    
    notifications = notifications.order_by('-created_at')
    
    paginator = Paginator(notifications, per_page)
    page_obj = paginator.get_page(page)
    
    data = []
    for notification in page_obj:
        data.append({
            'id': notification.id,
            'type': notification.notification_type,
            'title': notification.title,
            'message': notification.message,
            'data': notification.data,
            'is_read': notification.is_read,
            'created_at': notification.created_at.isoformat(),
            'read_at': notification.read_at.isoformat() if notification.read_at else None,
        })
    
    return JsonResponse({
        'success': True,
        'notifications': data,
        'pagination': {
            'current_page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous(),
        },
        'unread_count': Notification.get_unread_count(request.user)
    })

@require_POST
@login_required
@csrf_exempt
def api_mark_notification_read(request, notification_id):
    """Mark a specific notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()
        return JsonResponse({
            'success': True,
            'unread_count': Notification.get_unread_count(request.user)
        })
    except Notification.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Notification not found'}, status=404)

@require_POST
@login_required
@csrf_exempt
def api_mark_all_notifications_read(request):
    """Mark all notifications as read for the user"""
    try:
        count = NotificationService.mark_all_as_read(request.user)
        return JsonResponse({
            'success': True,
            'marked_count': count,
            'unread_count': 0
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_GET
@login_required
def api_notification_stats(request):
    """Get notification statistics for the user"""
    stats = NotificationService.get_notification_stats(request.user)
    return JsonResponse({
        'success': True,
        'stats': stats
    })

@require_GET
@login_required
def api_notification_preferences(request):
    """Get user's notification preferences"""
    preferences = NotificationPreference.get_or_create_preferences(request.user)
    
    preference_data = {
        'email': {
            'withdrawal_approved': preferences.email_withdrawal_approved,
            'withdrawal_rejected': preferences.email_withdrawal_rejected,
            'reward_won': preferences.email_reward_won,
            'premium_won': preferences.email_premium_won,
            'referral_joined': preferences.email_referral_joined,
        },
        'push': {
            'withdrawal_approved': preferences.push_withdrawal_approved,
            'withdrawal_rejected': preferences.push_withdrawal_rejected,
            'reward_won': preferences.push_reward_won,
            'premium_won': preferences.push_premium_won,
            'referral_joined': preferences.push_referral_joined,
        },
        'app': {
            'withdrawal_approved': preferences.app_withdrawal_approved,
            'withdrawal_rejected': preferences.app_withdrawal_rejected,
            'reward_won': preferences.app_reward_won,
            'premium_won': preferences.app_premium_won,
            'referral_joined': preferences.app_referral_joined,
            'task_completed': preferences.app_task_completed,
            'task_added': preferences.app_task_added,
        }
    }
    
    return JsonResponse({
        'success': True,
        'preferences': preference_data
    })

@require_POST
@login_required
@csrf_exempt
def api_update_notification_preferences(request):
    """Update user's notification preferences"""
    try:
        data = json.loads(request.body)
        preferences = NotificationPreference.get_or_create_preferences(request.user)
        
        # Update email preferences
        email_prefs = data.get('email', {})
        preferences.email_withdrawal_approved = email_prefs.get('withdrawal_approved', True)
        preferences.email_withdrawal_rejected = email_prefs.get('withdrawal_rejected', True)
        preferences.email_reward_won = email_prefs.get('reward_won', True)
        preferences.email_premium_won = email_prefs.get('premium_won', True)
        preferences.email_referral_joined = email_prefs.get('referral_joined', True)
        
        # Update push preferences
        push_prefs = data.get('push', {})
        preferences.push_withdrawal_approved = push_prefs.get('withdrawal_approved', True)
        preferences.push_withdrawal_rejected = push_prefs.get('withdrawal_rejected', True)
        preferences.push_reward_won = push_prefs.get('reward_won', True)
        preferences.push_premium_won = push_prefs.get('premium_won', True)
        preferences.push_referral_joined = push_prefs.get('referral_joined', True)
        
        # Update app preferences
        app_prefs = data.get('app', {})
        preferences.app_withdrawal_approved = app_prefs.get('withdrawal_approved', True)
        preferences.app_withdrawal_rejected = app_prefs.get('withdrawal_rejected', True)
        preferences.app_reward_won = app_prefs.get('reward_won', True)
        preferences.app_premium_won = app_prefs.get('premium_won', True)
        preferences.app_referral_joined = app_prefs.get('referral_joined', True)
        preferences.app_task_completed = app_prefs.get('task_completed', True)
        preferences.app_task_added = app_prefs.get('task_added', True)
        
        preferences.save()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@require_POST
@login_required
@csrf_exempt
def api_send_test_notification(request):
    """Send a test notification to the user"""
    try:
        data = json.loads(request.body)
        notification_type = data.get('type', 'system_message')
        title = data.get('title', 'Test Notification')
        message = data.get('message', 'This is a test notification')
        
        notification = NotificationService.send_notification(
            user=request.user,
            notification_type=notification_type,
            title=title,
            message=message,
            data={'test': True}
        )
        
        return JsonResponse({
            'success': True,
            'notification_id': notification.id
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
