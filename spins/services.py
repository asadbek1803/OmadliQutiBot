import random
from django.utils import timezone
from django.db import transaction
from rewards.models import SpinBoard, SpinBoardReward, TelegramPremiumReward
from .models import SpinLog
from wallet.models import Wallet, Ledger
from referrals.models import ReferralTransactionLog

class SpinService:
    @staticmethod
    def calculate_board_expected_value(board: SpinBoard):
        board_rewards = SpinBoardReward.objects.filter(spin_board=board, is_active=True).select_related('reward')
        total_weight = sum(item.weight for item in board_rewards)
        if total_weight == 0:
            return 0
        expected_value = sum((item.reward.coin_amount * item.weight) / total_weight for item in board_rewards)
        return expected_value
    
    @staticmethod
    def get_economy_health(board: SpinBoard):
        expected = SpinService.calculate_board_expected_value(board)
        cost = board.spin_cost
        
        status = "healthy"
        if expected > cost:
            status = "risky_loss"
        elif expected < cost * 0.5:
            status = "risky_scam_like"
        
        return {
            "expected_payout": round(expected, 2),
            "spin_cost": cost,
            "status": status,
        }

    @staticmethod
    @transaction.atomic
    def execute_spin(user, board: SpinBoard, selected_reward_id=None):
        wallet = Wallet.objects.select_for_update().get(user=user)

        now = timezone.now()
        today_free_spins = SpinLog.objects.filter(
            user=user,
            was_free_spin=True,
            created_at__date=now.date()
        ).count()
        free_spins_limit = 2

        is_free_spin = today_free_spins < free_spins_limit
        cost = 0 if is_free_spin else (board.spin_cost if board.spin_cost else 50)

        if not is_free_spin and wallet.coin_balance < cost:
            raise ValueError("Coin yetarli emas. Aylantirish uchun 50 Coin kerak.")

        if not is_free_spin:
            before_balance = wallet.coin_balance
            wallet.coin_balance -= cost
            wallet.spent_coin_total += cost
            Ledger.objects.create(
                user=user,
                type='spin_cost',
                amount=-cost,
                balance_before=before_balance,
                balance_after=wallet.coin_balance,
                reference_type='spin_board',
                reference_id=str(board.id),
                note='Spin charge'
            )

        # 2. Random selection based on weights, with optional selected-box chance path
        board_rewards = list(SpinBoardReward.objects.filter(spin_board=board, is_active=True).select_related('reward'))
        if not board_rewards:
            raise ValueError("No active rewards in this board")

        chosen_item = None
        selected_box_chance = None
        was_selected_box = False

        if selected_reward_id:
            # try map selected id to reward
            selected_item = next((item for item in board_rewards if item.reward.id == int(selected_reward_id)), None)
            total_weight = sum(item.weight for item in board_rewards)
            if selected_item and total_weight > 0:
                selected_box_chance = round((selected_item.weight / total_weight) * 100, 2)
                if random.random() <= (selected_item.weight / total_weight):
                    chosen_item = selected_item
                    was_selected_box = True

        if not chosen_item:
            weights = [item.weight for item in board_rewards]
            chosen_item = random.choices(board_rewards, weights=weights, k=1)[0]

        chosen_reward = chosen_item.reward
        
        # 3. Apply reward logic
        added_coins = chosen_reward.coin_amount
        premium_reward = None
        
        if chosen_reward.reward_type == 'telegram_premium':
            # Create Telegram Premium reward instance
            premium_reward = TelegramPremiumReward.objects.create(
                user=user,
                reward=chosen_reward,
                months=chosen_reward.telegram_premium_months or 1,
                coin_value=chosen_reward.telegram_premium_coin_value or 5000,
                status='pending'
            )
            premium_reward.generate_verification_code()
            
            # Send notification to user about premium reward
            try:
                from bot.handlers import get_or_create_user
                from aiogram import Bot
                from django.conf import settings
                
                def send_premium_notification():
                    try:
                        import asyncio
                        import threading
                        
                        async def async_send():
                            bot = Bot(token=settings.BOT_TOKEN)
                            message = (
                                f"🎉 Tabriklaymiz! Siz {chosen_reward.telegram_premium_months} oylik Telegram Premium yutdingiz!\n\n"
                                f"📋 Tasdiqlash kodi: {premium_reward.verification_code}\n"
                                f"⏰ Kodni 30 kun ichida ishlatishingiz mumkin.\n\n"
                                f"💰 Agar Premium kerak bo'lmasa, {premium_reward.coin_value} coin ga almashtirishingiz mumkin."
                            )
                            await bot.send_message(user.telegram_id, message)
                        
                        # Run async function in thread
                        def run_async():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(async_send())
                            loop.close()
                        
                        thread = threading.Thread(target=run_async)
                        thread.daemon = True
                        thread.start()
                    except Exception as e:
                        print(f"Premium notification error: {e}")
                
                send_premium_notification()
            except Exception as e:
                print(f"Premium notification setup error: {e}")
        
        if added_coins > 0:
            before_balance = wallet.coin_balance
            wallet.coin_balance += added_coins
            wallet.earned_coin_total += added_coins
            
            Ledger.objects.create(
                user=user,
                type='reward',
                amount=added_coins,
                balance_before=before_balance,
                balance_after=wallet.coin_balance,
                reference_type='reward_spin',
                reference_id=str(chosen_reward.id),
                note=f"Won {chosen_reward.name}"
            )
            
        wallet.save()
        
        # Log the spin
        log = SpinLog.objects.create(
            user=user,
            spin_board=board,
            reward=chosen_reward,
            reward_type_snapshot=chosen_reward.reward_type,
            reward_value_snapshot=chosen_reward.coin_amount,
            was_free_spin=is_free_spin,
            cost_snapshot=cost
        )
        # Anti-fraud Referral Activation Check
        if user.referred_by:
            spin_count = SpinLog.objects.filter(user=user).count()
            if spin_count == 1:
                inviter = user.referred_by
                inviter_wallet = Wallet.objects.filter(user=inviter).first()
                if inviter_wallet:
                    bonus_amount = 100
                    before_balance = inviter_wallet.coin_balance
                    inviter_wallet.coin_balance += bonus_amount
                    inviter_wallet.earned_coin_total += bonus_amount
                    inviter_wallet.save()
                    
                    Ledger.objects.create(
                        user=inviter,
                        type='referral_bonus',
                        amount=bonus_amount,
                        balance_before=before_balance,
                        balance_after=inviter_wallet.coin_balance,
                        reference_type='referred_user',
                        reference_id=str(user.id),
                        note=f"Referal aktivatsiyasi: {user.first_name or user.username}"
                    )
                    
                    ReferralTransactionLog.objects.create(
                        inviter=inviter,
                        invited_user=user,
                        amount_to_inviter=bonus_amount,
                        reason='first_spin_activation'
                    )

        return {
            "success": True,
            "reward": chosen_reward,
            "new_balance": wallet.coin_balance,
            "log": log,
            "was_selected_box": was_selected_box,
            "selected_box_chance": selected_box_chance,
            "premium_reward": premium_reward
        }
