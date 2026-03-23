# Test ma'lumotlarini yaratish uchun skript
import os
import sys
import django

# Django sozlamalari
sys.path.append(r'C:\Users\Lenovo\Desktop\OmadliQuti')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from accounts.models import User
from rewards.models import Reward, TelegramPremiumReward
from wallet.models import Wallet

# Test user yaratish (agar yo'q bo'lsa)
test_user, created = User.objects.get_or_create(
    telegram_id=123456789,
    defaults={
        'username': 'test_user',
        'first_name': 'Test',
        'last_name': 'User',
        'language_code': 'uz'
    }
)

if created:
    Wallet.objects.create(user=test_user)
    print("Test user va wallet yaratildi")

# Telegram Premium reward yaratish
premium_reward, created = Reward.objects.get_or_create(
    slug='telegram-premium-test',
    defaults={
        'name': 'Telegram Premium 1 oy',
        'reward_type': 'telegram_premium',
        'description': '1 oylik Telegram Premium obunasi',
        'icon': '👑',
        'probability_weight': 5,
        'coin_amount': 0,
        'telegram_premium_months': 1,
        'telegram_premium_coin_value': 5000,
        'display_order': 10,
        'is_active': True,
        'is_visible': True,
        'color_tag': '#0088cc'
    }
)

if created:
    print("Telegram Premium reward yaratildi")

# Test user uchun Premium reward yaratish
test_premium = TelegramPremiumReward.objects.create(
    user=test_user,
    reward=premium_reward,
    status='pending',
    months=1,
    coin_value=5000
)

test_premium.generate_verification_code()
test_premium.mark_as_verified()

print(f"Test Premium reward yaratildi:")
print(f"  ID: {test_premium.id}")
print(f"  User: {test_premium.user.username}")
print(f"  Status: {test_premium.status}")
print(f"  Verification Code: {test_premium.verification_code}")
print(f"  Expires: {test_premium.expires_at}")

# Admin panel URL
print("\nAdmin panelga kirish uchun:")
print("1. Superuser yaratish: python manage.py createsuperuser")
print("2. Admin panel: http://localhost:8000/rewards/admin/dashboard/")
print("3. Default Django admin: http://localhost:8000/admin/")
