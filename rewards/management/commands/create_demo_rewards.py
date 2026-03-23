import os
from django.core.management.base import BaseCommand
from accounts.models import User
from rewards.models import Reward, SpinBoard, SpinBoardReward, DailyBonusConfig

class Command(BaseCommand):
    help = 'Create demo rewards and default spin board'

    def handle(self, *args, **kwargs):
        # 1. Create Rewards
        rewards_data = [
            {'name': '10 Coins', 'icon': '🪙', 'type': 'small_coin', 'amount': 10, 'weight': 40, 'color': '#f1c40f'},
            {'name': '50 Coins', 'icon': '💰', 'type': 'medium_coin', 'amount': 50, 'weight': 20, 'color': '#e67e22'},
            {'name': '100 Coins', 'icon': '💎', 'type': 'big_coin', 'amount': 100, 'weight': 10, 'color': '#3498db'},
            {'name': 'Extra Spin', 'icon': '🔄', 'type': 'extra_spin', 'amount': 0, 'weight': 15, 'color': '#2ecc71'},
            {'name': 'Oops!', 'icon': '❌', 'type': 'miss', 'amount': 0, 'weight': 10, 'color': '#e74c3c'},
            {'name': 'Premium 1D', 'icon': '👑', 'type': 'premium_day', 'amount': 0, 'weight': 2, 'color': '#9b59b6'},
            {'name': '500 Coins', 'icon': '🎁', 'type': 'big_coin', 'amount': 500, 'weight': 2, 'color': '#1abc9c'},
            {'name': 'Jackpot', 'icon': '🎰', 'type': 'jackpot_virtual', 'amount': 5000, 'weight': 1, 'color': '#ff0000'},
            {'name': '5 Coins', 'icon': '🪙', 'type': 'small_coin', 'amount': 5, 'weight': 50, 'color': '#f39c12'},
        ]
        
        self.stdout.write("Checking rewards...")
        created_rewards = []
        for rd in rewards_data:
            obj, created = Reward.objects.get_or_create(
                slug=rd['name'].lower().replace(' ', '-').replace('!', ''),
                defaults={
                    'name': rd['name'],
                    'reward_type': rd['type'],
                    'icon': rd['icon'],
                    'coin_amount': rd['amount'],
                    'probability_weight': rd['weight'],
                    'color_tag': rd['color']
                }
            )
            created_rewards.append(obj)
            
        # 2. Create Board
        board, created = SpinBoard.objects.get_or_create(
            slug='main-board',
            defaults={
                'name': 'Main Spin Board',
                'description': 'The default wheel for users.',
                'spin_cost': 50,
                'free_spins_per_day': 1
            }
        )
        
        # 3. Map rewards to board (using first 8/9 rewards dynamically)
        self.stdout.write("Mapping rewards to board...")
        for i, r in enumerate(created_rewards):
            SpinBoardReward.objects.get_or_create(
                spin_board=board,
                reward=r,
                defaults={
                    'display_order': i
                }
            )

        # 4. Create Daily Bonus Config
        DailyBonusConfig.objects.get_or_create(
            id=1,
            defaults={
                'is_active': True,
                'coin_amount': 20,
            }
        )
        
        # 5. Admin user (optional check)
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser('admin', 'admin@asadbek.uz', 'admin')
            self.stdout.write(self.style.SUCCESS('Created default superuser admin/admin'))

        self.stdout.write(self.style.SUCCESS(f'Successfully setup {len(created_rewards)} demo rewards and board config.'))
