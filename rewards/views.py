from django.shortcuts import render
from django.http import JsonResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import UserPassesTestMixin
import json
import os
from django.utils import timezone
from django.db.models import Q, F, Sum, Count
from django.views.generic import TemplateView
from django.test.utils import override_settings
from django.conf import settings

from accounts.models import User
from rewards.models import TelegramPremiumReward, Reward
from wallet.models import Wallet, Ledger
from withdrawals.models import RewardRequest, RewardRequestConfig
from tasks.models import Task, UserTask
from spins.models import SpinLog
from referrals.models import ReferralTransactionLog

# Import admin management views
from .admin_views import (
    admin_management_view,
    api_admin_list,
    api_admin_create,
    api_admin_update,
    api_admin_delete,
    api_admin_stats,
    api_admin_toggle_status,
    api_admin_reset_password,
)


# ─────────────────────────────────────────────────────────────
# MIXINS & BASE VIEWS
# ─────────────────────────────────────────────────────────────

class IsAdminMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_staff


class AdminDashboardView(IsAdminMixin, TemplateView):
    template_name = 'admin/unfold_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Basic stats
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(
            wallet__earned_coin_total__gt=0
        ).count()
        context['total_coins_earned'] = Wallet.objects.aggregate(
            total=Sum('earned_coin_total')
        )['total'] or 0
        context['total_coins_spent'] = Wallet.objects.aggregate(
            total=Sum('spent_coin_total')
        )['total'] or 0

        # Today's stats
        today = timezone.now().date()
        context['today_spins'] = SpinLog.objects.filter(
            created_at__date=today
        ).count()
        context['today_withdrawals'] = RewardRequest.objects.filter(
            created_at__date=today
        ).count()
        context['today_new_users'] = User.objects.filter(
            date_joined__date=today
        ).count()

        # Premium rewards stats
        context['premium_rewards_pending'] = TelegramPremiumReward.objects.filter(
            status='pending'
        ).count()
        context['premium_rewards_verified'] = TelegramPremiumReward.objects.filter(
            status='verified'
        ).count()
        context['premium_rewards_redeemed'] = TelegramPremiumReward.objects.filter(
            status='redeemed'
        ).count()

        # Withdrawal stats
        context['withdrawals_pending'] = RewardRequest.objects.filter(
            status='pending'
        ).count()
        context['withdrawals_approved'] = RewardRequest.objects.filter(
            status='approved'
        ).count()
        context['withdrawals_fulfilled'] = RewardRequest.objects.filter(
            status='fulfilled'
        ).count()
        context['withdrawals_rejected'] = RewardRequest.objects.filter(
            status='rejected'
        ).count()
        context['withdrawals_total_coins'] = RewardRequest.objects.aggregate(
            total=Sum('amount_coin')
        )['total'] or 0

        # Recent activities
        context['recent_spins'] = SpinLog.objects.select_related(
            'user', 'reward'
        ).order_by('-created_at')[:10]
        context['recent_withdrawals'] = RewardRequest.objects.select_related(
            'user', 'processed_by'
        ).order_by('-created_at')[:10]
        context['recent_premium_rewards'] = TelegramPremiumReward.objects.select_related(
            'user', 'reward'
        ).order_by('-created_at')[:10]

        return context


# ─────────────────────────────────────────────────────────────
# HELPER
# ─────────────────────────────────────────────────────────────

def _is_admin(request):
    return request.user.is_authenticated and request.user.is_staff


def _serialize_withdrawal(req):
    """Return a JSON-serializable dict for a RewardRequest instance."""
    config = RewardRequestConfig.objects.first()
    rate = config.coin_to_uzs_rate if config else 100

    return {
        'id': req.id,
        'user': req.user.username,
        'user_telegram_id': getattr(req.user, 'telegram_id', None),
        'amount_coin': req.amount_coin,
        'amount_uzs': req.amount_coin * rate,
        'coin_to_uzs_rate': rate,
        'status': req.status,
        'card_label': req.card_label,
        'masked_card': req.masked_card,
        'holder_name': req.holder_name,
        'note': req.note,
        'admin_comment': req.admin_comment,
        'screenshot': req.screenshot.url if req.screenshot else None,
        'created_at': req.created_at.strftime('%d %b %Y %H:%M'),
        'processed_at': req.processed_at.strftime('%d %b %Y %H:%M') if req.processed_at else None,
        'processed_by': req.processed_by.username if req.processed_by else None,
    }


# ─────────────────────────────────────────────────────────────
# PREMIUM REWARDS  (existing endpoints — unchanged)
# ─────────────────────────────────────────────────────────────

@csrf_exempt
def api_premium_rewards_list(request):
    """List all Telegram Premium rewards for admin."""
    # TODO: enable auth check in production:
    # if not _is_admin(request):
    #     return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    rewards = TelegramPremiumReward.objects.select_related(
        'user', 'reward'
    ).order_by('-created_at')

    data = []
    for reward in rewards:
        data.append({
            'id': reward.id,
            'user': reward.user.username,
            'user_telegram_id': reward.user.telegram_id,
            'reward_name': reward.reward.name,
            'months': reward.months,
            'coin_value': reward.coin_value,
            'status': reward.status,
            'verification_code': reward.verification_code,
            'created_at': reward.created_at.strftime('%d %b %Y %H:%M'),
            'verified_at': reward.verified_at.strftime('%d %b %Y %H:%M') if reward.verified_at else None,
            'expires_at': reward.expires_at.strftime('%d %b %Y %H:%M') if reward.expires_at else None,
            'admin_notes': reward.admin_notes,
            'is_expired': reward.is_expired(),
        })

    return JsonResponse({'success': True, 'rewards': data})


@csrf_exempt
def api_premium_reward_verify(request):
    """Verify / redeem / convert / reject a Telegram Premium reward."""
    # TODO: enable auth check in production:
    # if not _is_admin(request):
    #     return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    body = json.loads(request.body)
    reward_id = body.get('reward_id')
    action = body.get('action')   # 'verify' | 'redeem' | 'convert' | 'reject'
    notes = body.get('notes', '')

    try:
        reward = TelegramPremiumReward.objects.get(id=reward_id)
    except TelegramPremiumReward.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Reward not found'}, status=404)

    if action == 'verify':
        if reward.status != 'pending':
            return JsonResponse({'success': False, 'error': 'Reward is not pending'})
        reward.mark_as_verified()
        reward.admin_notes = notes
        reward.save()

    elif action == 'redeem':
        if reward.status != 'verified':
            return JsonResponse({'success': False, 'error': 'Reward is not verified'})
        if reward.is_expired():
            return JsonResponse({'success': False, 'error': 'Reward has expired'})
        if not reward.redeem_premium():
            return JsonResponse({'success': False, 'error': 'Cannot redeem reward'})
        reward.admin_notes = notes
        reward.save()

    elif action == 'convert':
        if reward.status != 'verified':
            return JsonResponse({'success': False, 'error': 'Reward is not verified'})
        if reward.is_expired():
            return JsonResponse({'success': False, 'error': 'Reward has expired'})
        new_balance = reward.convert_to_coins()
        if new_balance is None:
            return JsonResponse({'success': False, 'error': 'Cannot convert to coins'})
        reward.admin_notes = notes
        reward.save()
        return JsonResponse({'success': True, 'new_balance': new_balance})

    elif action == 'reject':
        reward.status = 'expired'
        reward.admin_notes = notes
        reward.save()

    else:
        return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)

    return JsonResponse({'success': True})


@csrf_exempt
def api_user_premium_rewards(request):
    """Get a single user's Telegram Premium rewards (user-facing)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    body = json.loads(request.body)
    telegram_id = body.get('telegram_id')

    user = User.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

    rewards = TelegramPremiumReward.objects.filter(user=user).order_by('-created_at')
    data = []
    for reward in rewards:
        data.append({
            'id': reward.id,
            'reward_name': reward.reward.name,
            'months': reward.months,
            'coin_value': reward.coin_value,
            'status': reward.status,
            'verification_code': (
                reward.verification_code
                if reward.status in ['verified', 'pending'] else None
            ),
            'created_at': reward.created_at.strftime('%d %b %Y %H:%M'),
            'verified_at': reward.verified_at.strftime('%d %b %Y %H:%M') if reward.verified_at else None,
            'expires_at': reward.expires_at.strftime('%d %b %Y %H:%M') if reward.expires_at else None,
            'is_expired': reward.is_expired(),
        })

    return JsonResponse({'success': True, 'rewards': data})


@csrf_exempt
def api_premium_reward_convert(request):
    """Convert a verified Premium reward to coins (user-facing action)."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    body = json.loads(request.body)
    telegram_id = body.get('telegram_id')
    reward_id = body.get('reward_id')

    user = User.objects.filter(telegram_id=telegram_id).first()
    if not user:
        return JsonResponse({'success': False, 'error': 'User not found'}, status=404)

    try:
        reward = TelegramPremiumReward.objects.get(id=reward_id, user=user)
    except TelegramPremiumReward.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Reward not found'}, status=404)

    if reward.status != 'verified':
        return JsonResponse({'success': False, 'error': 'Reward is not verified'})
    if reward.is_expired():
        return JsonResponse({'success': False, 'error': 'Reward has expired'})

    new_balance = reward.convert_to_coins()
    if new_balance is None:
        return JsonResponse({'success': False, 'error': 'Cannot convert to coins'})

    return JsonResponse({'success': True, 'new_balance': new_balance})


# ─────────────────────────────────────────────────────────────
# ADMIN STATS
# ─────────────────────────────────────────────────────────────

@csrf_exempt
def api_admin_stats(request):
    """Dashboard summary statistics for admin panel."""
    if not _is_admin(request):
        return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    from datetime import timedelta

    config = RewardRequestConfig.objects.first()

    stats = {
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(wallet__earned_coin_total__gt=0).count(),
        'total_coins_earned': Wallet.objects.aggregate(total=Sum('earned_coin_total'))['total'] or 0,
        'total_coins_spent': Wallet.objects.aggregate(total=Sum('spent_coin_total'))['total'] or 0,
        # Withdrawal stats
        'total_withdrawals': RewardRequest.objects.count(),
        'pending_withdrawals': RewardRequest.objects.filter(status='pending').count(),
        'approved_withdrawals': RewardRequest.objects.filter(status='approved').count(),
        'fulfilled_withdrawals': RewardRequest.objects.filter(status='fulfilled').count(),
        'rejected_withdrawals': RewardRequest.objects.filter(status='rejected').count(),
        'total_withdrawn_coins': RewardRequest.objects.filter(
            status='fulfilled'
        ).aggregate(total=Sum('amount_coin'))['total'] or 0,
        # Other stats
        'total_spins': SpinLog.objects.count(),
        'total_tasks_completed': UserTask.objects.filter(is_completed=True).count(),
        'total_referrals': User.objects.filter(referred_by__isnull=False).count(),
        # Premium rewards
        'premium_rewards_pending': TelegramPremiumReward.objects.filter(status='pending').count(),
        # Config
        'coin_to_uzs_rate': config.coin_to_uzs_rate if config else 100,
        'withdrawals_enabled': config.is_enabled if config else True,
    }

    # Chart data — last 7 days
    dates, spins_data, users_data, withdrawals_data = [], [], [], []
    for i in range(7):
        date = (timezone.now() - timedelta(days=i)).date()
        dates.append(date.strftime('%d %b'))
        spins_data.append(SpinLog.objects.filter(created_at__date=date).count())
        users_data.append(User.objects.filter(date_joined__date=date).count())
        withdrawals_data.append(
            RewardRequest.objects.filter(created_at__date=date).count()
        )

    stats['chart_data'] = {
        'dates': list(reversed(dates)),
        'spins': list(reversed(spins_data)),
        'users': list(reversed(users_data)),
        'withdrawals': list(reversed(withdrawals_data)),
    }

    return JsonResponse({'success': True, 'stats': stats})


# ─────────────────────────────────────────────────────────────
# WITHDRAWAL MANAGEMENT  (new endpoints)
# ─────────────────────────────────────────────────────────────

@csrf_exempt
def api_withdrawals_list(request):
    """
    GET  /withdrawals/api/list/
    Returns all RewardRequests for the admin panel.
    Supports optional query params:
      ?status=pending|approved|fulfilled|rejected
      ?search=<username or telegram_id>
    """
    if not _is_admin(request):
        return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    qs = RewardRequest.objects.select_related('user', 'processed_by').order_by('-created_at')

    status_filter = request.GET.get('status')
    if status_filter and status_filter != 'all':
        qs = qs.filter(status=status_filter)

    search = request.GET.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(user__username__icontains=search) |
            Q(user__telegram_id__icontains=search) |
            Q(holder_name__icontains=search)
        )

    data = [_serialize_withdrawal(r) for r in qs]
    return JsonResponse({'success': True, 'requests': data, 'count': len(data)})


@csrf_exempt
def api_withdrawal_action(request):
    """
    POST /withdrawals/api/action/
    Body (multipart/form-data OR JSON):
      request_id    – ID of the RewardRequest
      action        – 'approve' | 'reject' | 'fulfill'
      admin_comment – optional text
      screenshot    – optional image file (for 'fulfill')

    Transitions:
      pending  → approve  → approved
      pending  → reject   → rejected
      approved → fulfill  → fulfilled  (+ optional screenshot upload)
    """
    if not _is_admin(request):
        return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    # Support both JSON and multipart
    if request.content_type and 'application/json' in request.content_type:
        body = json.loads(request.body)
        request_id = body.get('request_id')
        action = body.get('action')
        admin_comment = body.get('admin_comment', '')
        screenshot_file = None
    else:
        request_id = request.POST.get('request_id')
        action = request.POST.get('action')
        admin_comment = request.POST.get('admin_comment', '')
        screenshot_file = request.FILES.get('screenshot')

    if not request_id or not action:
        return JsonResponse({'success': False, 'error': 'request_id and action are required'}, status=400)

    try:
        req = RewardRequest.objects.select_related('user').get(id=request_id)
    except RewardRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'RewardRequest not found'}, status=404)

    # ── approve ───────────────────────────────────────────────
    if action == 'approve':
        if req.status != 'pending':
            return JsonResponse(
                {'success': False, 'error': f"Cannot approve: current status is '{req.status}'"}
            )
        req.status = 'approved'
        req.admin_comment = admin_comment
        req.processed_at = timezone.now()
        req.processed_by = request.user
        req.save()
        return JsonResponse({'success': True, 'new_status': 'approved', 'request': _serialize_withdrawal(req)})

    # ── reject ────────────────────────────────────────────────
    elif action == 'reject':
        if req.status not in ('pending', 'approved'):
            return JsonResponse(
                {'success': False, 'error': f"Cannot reject: current status is '{req.status}'"}
            )
        req.status = 'rejected'
        req.admin_comment = admin_comment
        req.processed_at = timezone.now()
        req.processed_by = request.user
        req.save()
        return JsonResponse({'success': True, 'new_status': 'rejected', 'request': _serialize_withdrawal(req)})

    # ── fulfill ───────────────────────────────────────────────
    elif action == 'fulfill':
        if req.status != 'approved':
            return JsonResponse(
                {'success': False, 'error': f"Cannot fulfill: current status is '{req.status}'"}
            )
        req.status = 'fulfilled'
        req.admin_comment = admin_comment
        req.processed_at = timezone.now()
        req.processed_by = request.user
        if screenshot_file:
            req.screenshot = screenshot_file
        req.save()
        return JsonResponse({'success': True, 'new_status': 'fulfilled', 'request': _serialize_withdrawal(req)})

    else:
        return JsonResponse({'success': False, 'error': f"Unknown action: '{action}'"}, status=400)


@csrf_exempt
def api_withdrawal_detail(request, request_id):
    """
    GET /withdrawals/api/<int:request_id>/
    Returns full details of a single RewardRequest.
    """
    if not _is_admin(request):
        return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    try:
        req = RewardRequest.objects.select_related('user', 'processed_by').get(id=request_id)
    except RewardRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)

    return JsonResponse({'success': True, 'request': _serialize_withdrawal(req)})


@csrf_exempt
def api_withdrawal_bulk_action(request):
    """
    POST /withdrawals/api/bulk/
    Body JSON:
      ids    – list of RewardRequest IDs
      action – 'approve' | 'reject'
    Useful for batch-processing multiple pending requests at once.
    """
    if not _is_admin(request):
        return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)

    body = json.loads(request.body)
    ids = body.get('ids', [])
    action = body.get('action')
    admin_comment = body.get('admin_comment', '')

    if not ids or action not in ('approve', 'reject'):
        return JsonResponse({'success': False, 'error': 'ids and valid action required'}, status=400)

    new_status = 'approved' if action == 'approve' else 'rejected'
    allowed_current = 'pending' if action == 'approve' else ('pending', 'approved')

    qs = RewardRequest.objects.filter(id__in=ids, status__in=allowed_current)
    updated = qs.update(
        status=new_status,
        admin_comment=admin_comment,
        processed_at=timezone.now(),
        processed_by=request.user,
    )

    return JsonResponse({
        'success': True,
        'updated': updated,
        'skipped': len(ids) - updated,
        'new_status': new_status,
    })


@csrf_exempt
def api_withdrawal_stats(request):
    """
    GET /withdrawals/api/stats/
    Returns aggregated statistics for the withdrawal dashboard.
    """
    if not _is_admin(request):
        return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    from datetime import timedelta

    config = RewardRequestConfig.objects.first()
    rate = config.coin_to_uzs_rate if config else 100

    today = timezone.now().date()

    stats = {
        'total': RewardRequest.objects.count(),
        'pending': RewardRequest.objects.filter(status='pending').count(),
        'approved': RewardRequest.objects.filter(status='approved').count(),
        'fulfilled': RewardRequest.objects.filter(status='fulfilled').count(),
        'rejected': RewardRequest.objects.filter(status='rejected').count(),
        'today_count': RewardRequest.objects.filter(created_at__date=today).count(),
        'today_coins': RewardRequest.objects.filter(
            created_at__date=today
        ).aggregate(total=Sum('amount_coin'))['total'] or 0,
        'total_coins_requested': RewardRequest.objects.aggregate(
            total=Sum('amount_coin')
        )['total'] or 0,
        'total_coins_fulfilled': RewardRequest.objects.filter(
            status='fulfilled'
        ).aggregate(total=Sum('amount_coin'))['total'] or 0,
        'coin_to_uzs_rate': rate,
        'withdrawals_enabled': config.is_enabled if config else True,
        'min_coin_threshold': config.min_coin_threshold if config else 1000,
    }

    # Add UZS equivalents
    stats['total_uzs_requested'] = stats['total_coins_requested'] * rate
    stats['total_uzs_fulfilled'] = stats['total_coins_fulfilled'] * rate

    # Last 7 days chart data
    dates, counts, coins = [], [], []
    for i in range(7):
        date = (timezone.now() - timedelta(days=i)).date()
        dates.append(date.strftime('%d %b'))
        counts.append(RewardRequest.objects.filter(created_at__date=date).count())
        coins.append(
            RewardRequest.objects.filter(
                created_at__date=date
            ).aggregate(total=Sum('amount_coin'))['total'] or 0
        )

    stats['chart_data'] = {
        'dates': list(reversed(dates)),
        'counts': list(reversed(counts)),
        'coins': list(reversed(coins)),
    }

    return JsonResponse({'success': True, 'stats': stats})


@csrf_exempt
def api_withdrawal_config(request):
    """
    GET  /withdrawals/api/config/         – return current config
    POST /withdrawals/api/config/         – update config (admin only)
    Body JSON:
      min_coin_threshold   – int
      max_pending_per_user – int
      coin_to_uzs_rate     – int
      is_enabled           – bool
    """
    if not _is_admin(request):
        return JsonResponse({'success': False, 'error': 'Admin required'}, status=403)

    config, _ = RewardRequestConfig.objects.get_or_create(pk=1)

    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'config': {
                'min_coin_threshold': config.min_coin_threshold,
                'max_pending_per_user': config.max_pending_per_user,
                'coin_to_uzs_rate': config.coin_to_uzs_rate,
                'is_enabled': config.is_enabled,
            }
        })

    if request.method == 'POST':
        body = json.loads(request.body)
        if 'min_coin_threshold' in body:
            config.min_coin_threshold = int(body['min_coin_threshold'])
        if 'max_pending_per_user' in body:
            config.max_pending_per_user = int(body['max_pending_per_user'])
        if 'coin_to_uzs_rate' in body:
            config.coin_to_uzs_rate = int(body['coin_to_uzs_rate'])
        if 'is_enabled' in body:
            config.is_enabled = bool(body['is_enabled'])
        config.save()
        return JsonResponse({
            'success': True,
            'config': {
                'min_coin_threshold': config.min_coin_threshold,
                'max_pending_per_user': config.max_pending_per_user,
                'coin_to_uzs_rate': config.coin_to_uzs_rate,
                'is_enabled': config.is_enabled,
            }
        })

    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


# ─────────────────────────────────────────────────────────────
# SCREENSHOT SERVING  (existing + enhanced)
# ─────────────────────────────────────────────────────────────

@require_GET
def serve_withdrawal_screenshot(request, filename):
    """
    Serve a withdrawal screenshot with proper auth/permission checks.
    Staff can view any screenshot; regular users can only view their own.
    """
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    try:
        reward_request = RewardRequest.objects.get(
            screenshot=f'withdrawal_screenshots/{filename}'
        )
    except RewardRequest.DoesNotExist:
        raise Http404('Screenshot not found')

    if not (request.user.is_staff or request.user == reward_request.user):
        return HttpResponse('Forbidden', status=403)

    file_path = os.path.join(settings.MEDIA_ROOT, 'withdrawal_screenshots', filename)
    if not os.path.exists(file_path):
        raise Http404('Screenshot file not found on disk')

    # Detect content type from extension
    ext = os.path.splitext(filename)[1].lower()
    content_type_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                        '.png': 'image/png', '.gif': 'image/gif',
                        '.webp': 'image/webp'}
    content_type = content_type_map.get(ext, 'application/octet-stream')

    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        response['Cache-Control'] = 'private, max-age=3600'
        return response


@require_GET
@login_required
def serve_withdrawal_screenshots_list(request):
    """
    Returns a list of screenshot URLs accessible to the requesting user.
    Staff sees all; regular users see only their own.
    """
    if request.user.is_staff:
        qs = RewardRequest.objects.exclude(
            screenshot=''
        ).exclude(screenshot__isnull=True)
    else:
        qs = RewardRequest.objects.filter(
            user=request.user
        ).exclude(screenshot='').exclude(screenshot__isnull=True)

    screenshot_list = []
    for req in qs:
        if req.screenshot:
            fname = os.path.basename(req.screenshot.name)
            screenshot_list.append({
                'id': req.id,
                'filename': fname,
                'url': req.screenshot.url,
                'created_at': req.created_at.isoformat(),
                'status': req.status,
                'amount_coin': req.amount_coin,
                'user': req.user.username,
            })

    return JsonResponse({'success': True, 'screenshots': screenshot_list})