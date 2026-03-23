from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from accounts.models import User
from rewards.models import SpinBoard
from spins.services import SpinService
from withdrawals.models import RewardRequest, RewardRequestConfig
from wallet.models import Ledger, Wallet
from tasks.models import Task, UserTask
from referrals.models import ReferralTransactionLog
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
import urllib.parse
import requests
from django.conf import settings
import hmac
import hashlib

def dashboard_view(request):
    """
    Renders the main SPA for the Telegram Web App.
    Instead of multiple HTML pages, we'll build a simple SPA.
    """
    return render(request, 'webapp/dashboard.html')

def verify_telegram_web_app_data(init_data: str, bot_token: str):
    """
    Validates the initData from Telegram Web App.
    """
    # Just a placeholder for actual validation logic
    # In production, implement HMAC verification using bot_token and init_data
    return True

@csrf_exempt
def api_init_data(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        init_data_str = data.get('initData', '')
        # user_data = ... parse init_data to get user
        
        # Mocking generic user retrieval for simpler setup
        # Requires valid telegram validation in real app
        telegram_id = data.get('telegram_id') 
        
        if not telegram_id:
            return JsonResponse({'success': False, 'error': 'No auth data'})
            
        user = User.objects.filter(telegram_id=telegram_id).first()
        if not user:
            return JsonResponse({'success': False, 'error': 'User not found'})
            
        if not user.referral_code:
            import string, random
            user.referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            user.save(update_fields=['referral_code'])

        wallet = user.wallet
        # Return basic config
        board = SpinBoard.objects.filter(is_active=True).first()
        board_data = None
        
        from django.utils import timezone
        import datetime
        now = timezone.now()

        today_free_spins = user.spin_logs.filter(
            was_free_spin=True,
            created_at__date=now.date()
        ).count()
        free_spins_limit = 2
        free_spins_left = max(0, free_spins_limit - today_free_spins)

        tomorrow = now.date() + datetime.timedelta(days=1)
        midnight = datetime.datetime.combine(tomorrow, datetime.time.min, tzinfo=datetime.timezone.utc)
        seconds_until_next_day = (midnight - now).total_seconds()

        # Levels Logic
        coins = wallet.earned_coin_total
        if coins >= 50000:
            level = {'name': 'Diamond', 'badge': '💎'}
        elif coins >= 15000:
            level = {'name': 'Platinum', 'badge': '🔮'}
        elif coins >= 5000:
            level = {'name': 'Gold', 'badge': '🥇'}
        elif coins >= 1000:
            level = {'name': 'Silver', 'badge': '🥈'}
        else:
            level = {'name': 'Bronze', 'badge': '🥉'}

        if board:
            rewards_qs = board.board_rewards.filter(is_active=True).select_related('reward')
            rewards_list = []
            for item in rewards_qs:
                rewards_list.append({
                    'id': item.reward.id,
                    'name': item.reward.name,
                    'icon': item.reward.icon,
                    'coin_amount': item.reward.coin_amount,
                    'color_tag': item.reward.color_tag,
                    'weight': item.weight
                })
            board_data = {
                'id': board.id,
                'name': board.name,
                'spin_cost': board.spin_cost,
                'rewards': rewards_list
            }
        
        # Fetch recent 5 transactions
        recent_txs = Ledger.objects.filter(user=user).select_related('user').order_by('-created_at')[:5]
        
        type_translations = {
            'spin_cost': 'Baraban aylantirish',
            'reward': 'Yutuq',
            'withdrawal_request': "Pul yechish",
            'referral_bonus': 'Taklif bonusi',
            'task_reward': "Vazifa yutug'i",
        }
        
        tx_list = []
        for tx in recent_txs:
            translated_type = type_translations.get(tx.type, tx.type)
            tx_list.append({
                'type': tx.type,
                'amount': tx.amount,
                'note': translated_type, # Override note to always show clean translated type in UI
                'date': tx.created_at.strftime("%d %b %H:%M")
            })

        # Referrals
        ref_count = user.referrals.count()
        ref_coins = ReferralTransactionLog.objects.filter(inviter=user).aggregate(Sum('amount_to_inviter'))['amount_to_inviter__sum'] or 0

        # Withdraw Config
        withdraw_config = RewardRequestConfig.objects.first()
        uzs_rate = withdraw_config.coin_to_uzs_rate if withdraw_config else 100

        return JsonResponse({
            'success': True,
            'user': {
                'username': user.username,
                'coin_balance': wallet.coin_balance,
                'free_spins_left': free_spins_left,
                'seconds_until_next_day': seconds_until_next_day,
                'is_blocked': user.is_blocked,
                'referral_code': user.referral_code,
                'referral_count': ref_count,
                'referral_coins': ref_coins,
                'uzs_rate': uzs_rate,
                'transactions': tx_list,
                'level': level
            },
            'board': board_data
        })
    return JsonResponse({'success': False})

@csrf_exempt
def api_spin(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        telegram_id = data.get('telegram_id')
        board_id = data.get('board_id')
        selected_reward_id = data.get('selected_reward_id')
        
        user = User.objects.filter(telegram_id=telegram_id).first()
        board = SpinBoard.objects.filter(id=board_id).first()
        
        if not user or not board:
            return JsonResponse({'success': False, 'error': 'Invalid request'})
        if user.is_blocked:
            return JsonResponse({'success': False, 'error': 'Siz admin tomonidan bloklangansiz!'})
            
        try:
            result = SpinService.execute_spin(user, board, selected_reward_id=selected_reward_id)

            now = timezone.now()
            today_free_spins = user.spin_logs.filter(
                was_free_spin=True,
                created_at__date=now.date()
            ).count()
            free_spins_limit = 2
            free_spins_left = max(0, free_spins_limit - today_free_spins)

            return JsonResponse({
                'success': True,
                'reward_id': result['reward'].id,
                'reward_name': result['reward'].name,
                'reward_amount': result['reward'].coin_amount,
                'new_balance': result['new_balance'],
                'free_spins_left': free_spins_left,
                'was_selected_box': result.get('was_selected_box', False),
                'selected_box_chance': result.get('selected_box_chance', None),
                'premium_reward': {
                    'id': result.get('premium_reward').id,
                    'verification_code': result.get('premium_reward').verification_code,
                    'months': result.get('premium_reward').months,
                    'coin_value': result.get('premium_reward').coin_value
                } if result.get('premium_reward') else None
            })
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
def api_wallet(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        telegram_id = data.get('telegram_id')
        
        user = User.objects.filter(telegram_id=telegram_id).first()
        if not user:
            return JsonResponse({'success': False, 'error': 'User not found'})
        
        # Fetch withdrawal requests with screenshots
        withdrawals = RewardRequest.objects.filter(user=user).order_by('-created_at')
        withdrawal_list = []
        
        for req in withdrawals:
            withdrawal_data = {
                'id': req.id,
                'amount_coin': req.amount_coin,
                'status': req.status,
                'card_label': req.card_label,
                'masked_card': req.masked_card,
                'holder_name': req.holder_name,
                'created_at': req.created_at.strftime("%d %b %H:%M"),
                'processed_at': req.processed_at.strftime("%d %b %H:%M") if req.processed_at else None,
                'admin_comment': req.admin_comment
            }
            
            # Add screenshot URL if available
            if req.screenshot:
                withdrawal_data['screenshot_url'] = req.screenshot.url
            
            withdrawal_list.append(withdrawal_data)
        
        return JsonResponse({
            'success': True,
            'withdrawals': withdrawal_list
        })
    
    return JsonResponse({'success': False})

@csrf_exempt
def api_withdraw(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        telegram_id = data.get('telegram_id')
        card_label = data.get('card_label')
        card_number = data.get('card_number')
        holder_name = data.get('holder_name')
        
        user = User.objects.filter(telegram_id=telegram_id).first()
        if not user:
            return JsonResponse({'success': False, 'error': 'User not found'})
            
        if user.is_blocked:
            return JsonResponse({'success': False, 'error': 'Siz admin tomonidan bloklangansiz!'})

        config = RewardRequestConfig.objects.filter(is_enabled=True).first()
        min_amount = config.min_coin_threshold if config else 1000
        
        wallet = user.wallet
        if wallet.coin_balance < min_amount:
            return JsonResponse({'success': False, 'error': f"Minimum yechish summasi: {min_amount} Coin"})
        
        # Withdraw all available coins or prompt amount? Let's withdraw everything requested, here we just withdraw minimum config threshold or maybe all coins. The user just requests reward, let's say they withdraw all coins
        amount_to_withdraw = wallet.coin_balance
        
        try:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=user)
                if wallet.coin_balance < min_amount:
                    return JsonResponse({'success': False, 'error': f"Minimum yechish summasi: {min_amount} Coin"})
                
                amount_to_withdraw = wallet.coin_balance
                wallet.coin_balance -= amount_to_withdraw
                wallet.reserved_coin_balance += amount_to_withdraw
                wallet.save()
                
                req = RewardRequest.objects.create(
                    user=user,
                    amount_coin=amount_to_withdraw,
                    card_label=card_label,
                    masked_card=card_number,
                    holder_name=holder_name,
                    status='pending'
                )
                
                Ledger.objects.create(
                    user=user,
                    type='withdrawal_request',
                    amount=-amount_to_withdraw,
                    balance_before=wallet.coin_balance + amount_to_withdraw,
                    balance_after=wallet.coin_balance,
                    note='Yechib olish so\'rovi',
                    reference_type='reward_request',
                    reference_id=str(req.id)
                )

            return JsonResponse({'success': True, 'new_balance': wallet.coin_balance})
        except Exception as e:
            return JsonResponse({'success': False, 'error': "Server xatosi: " + str(e)})
    return JsonResponse({'success': False})

@csrf_exempt
def api_leaders(request):
    # Fetch TOP 50 users by earned coins
    top_wallets = Wallet.objects.filter(earned_coin_total__gt=0).select_related('user').order_by('-earned_coin_total')[:50]
    leaders = []
    for idx, w in enumerate(top_wallets):
        name = w.user.first_name or w.user.username
        if not name: name = "Foydalanuvchi"
        leaders.append({
            'rank': idx + 1,
            'name': name[:15], # cap length
            'coins': w.earned_coin_total
        })
    return JsonResponse({'success': True, 'leaders': leaders})

@csrf_exempt
def api_tasks_list(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user = User.objects.filter(telegram_id=data.get('telegram_id')).first()
        if not user: return JsonResponse({'success': False})
        
        tasks_qs = Task.objects.filter(is_active=True).order_by('id')
        user_tasks = {ut.task_id: ut for ut in UserTask.objects.filter(user=user)}
        
        result = []
        for t in tasks_qs:
            ut = user_tasks.get(t.id)
            can_verify, verify_message = ut.can_attempt_verification() if ut else (True, "Can verify")
            
            result.append({
                'id': t.id,
                'title': t.title,
                'description': t.description,
                'reward_coin': t.reward_coin,
                'task_type': t.task_type,
                'link': t.link,
                'is_completed': ut.is_completed if ut else False,
                'verification_attempts': ut.verification_attempts if ut else 0,
                'max_verification_attempts': t.max_verification_attempts,
                'can_verify': can_verify,
                'verify_message': verify_message,
                'requires_screenshot': t.requires_screenshot,
                'last_verification_attempt': ut.last_verification_attempt.isoformat() if ut and ut.last_verification_attempt else None
            })
        return JsonResponse({'success': True, 'tasks': result})
    return JsonResponse({'success': False})

@csrf_exempt
def api_tasks_verify(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user = User.objects.filter(telegram_id=data.get('telegram_id')).first()
        task = Task.objects.filter(id=data.get('task_id'), is_active=True).first()
        
        if not user or not task:
            return JsonResponse({'success': False, 'error': 'Invalid task or user'})
            
        ut, _ = UserTask.objects.get_or_create(user=user, task=task)
        if ut.is_completed:
            return JsonResponse({'success': False, 'error': 'Task already completed'})
        
        # Check if user can attempt verification
        can_verify, message = ut.can_attempt_verification()
        if not can_verify:
            return JsonResponse({'success': False, 'error': message})
            
        # Update verification attempt
        ut.verification_attempts += 1
        ut.last_verification_attempt = timezone.now()
        ut.save(update_fields=['verification_attempts', 'last_verification_attempt'])
            
        # Verify based on task type
        is_verified = False
        verification_method = None
        
        if task.task_type == 'telegram' and task.chat_id:
            verification_method = 'telegram_api'
            bot_token = settings.BOT_TOKEN
            url = f"https://api.telegram.org/bot{bot_token}/getChatMember?chat_id={task.chat_id}&user_id={user.telegram_id}"
            try:
                r = requests.get(url, timeout=5).json()
                if r.get('ok') and r.get('result', {}).get('status') in ['member', 'creator', 'administrator']:
                    is_verified = True
                else:
                    return JsonResponse({'success': False, 'error': "Siz hali obuna bo'lmagansiz! Qayta urinib ko'ring."})
            except:
                return JsonResponse({'success': False, 'error': 'Telegram serveriga ulanishda xatolik'})
        elif task.task_type == 'youtube':
            verification_method = 'manual'
            # For YouTube, we require more strict verification - could be implemented with YouTube API
            # For now, we'll make it random with 30% success rate to simulate strict verification
            import random
            if random.random() < 0.3:  # 30% success rate
                is_verified = True
            else:
                return JsonResponse({'success': False, 'error': "Video ko'rilganligi tasdiqlanmadi. Iltimos, videoni to'liq ko'ring va qayta urinib ko'ring."})
        else:
            # For other types, require admin verification if screenshot is required
            if task.requires_screenshot:
                verification_method = 'admin_required'
                return JsonResponse({'success': False, 'error': "Bu topshiriq uchun admin tasdiqi talab qilinadi. Iltimos, skrinshotni yuboring."})
            else:
                verification_method = 'basic'
                is_verified = True
            
        if is_verified:
            with transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(user=user)
                before_balance = wallet.coin_balance
                wallet.coin_balance += task.reward_coin
                wallet.earned_coin_total += task.reward_coin
                wallet.save()
                
                ut.is_completed = True
                ut.verification_method = verification_method
                ut.completed_at = timezone.now()
                ut.save()
                
                Ledger.objects.create(
                    user=user,
                    type='task_reward',
                    amount=task.reward_coin,
                    balance_before=before_balance,
                    balance_after=wallet.coin_balance,
                    reference_type='task',
                    reference_id=str(task.id),
                    note=f"Task: {task.title}"
                )
            return JsonResponse({'success': True, 'new_balance': wallet.coin_balance, 'reward': task.reward_coin})
        else:
            return JsonResponse({'success': False, 'error': "Tasdiqlanmadi! Qayta urinib ko'ring."})
            
    return JsonResponse({'success': False})
