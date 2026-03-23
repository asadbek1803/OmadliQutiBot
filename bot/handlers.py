from aiogram import Router, types
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asgiref.sync import sync_to_async
from django.conf import settings
from accounts.models import User
from wallet.models import Wallet
from referrals.models import ReferralVisit

router = Router()

@sync_to_async
def get_or_create_user(telegram_user: types.User, referral_code: str = None):
    # Process referral if exists
    if referral_code:
        ReferralVisit.objects.create(code=referral_code, visitor_telegram_id=telegram_user.id)
        
    user, created = User.objects.get_or_create(
        telegram_id=telegram_user.id,
        defaults={
            'username': telegram_user.username or f"tg_{telegram_user.id}",
            'first_name': telegram_user.first_name,
            'last_name': telegram_user.last_name or '',
            'language_code': telegram_user.language_code,
            'is_premium_telegram': telegram_user.is_premium or False,
        }
    )
    if created:
        Wallet.objects.create(user=user)
        if referral_code:
            inviter = User.objects.filter(referral_code=referral_code).first()
            if inviter and inviter != user:
                user.referred_by = inviter
                user.save(update_fields=['referred_by'])
    return user, created

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    ref_code = args[0] if args else None
    
    user, created = await get_or_create_user(message.from_user, ref_code)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🎮 O'yinni Boshlash", web_app=types.WebAppInfo(url=settings.WEBAPP_URL))
    
    welcome_text = (
        f"Assalomu alaykum {message.from_user.first_name}! OmadliQuti loyihasiga xush kelibsiz.\n\n"
        "🎁 Har kuni bepul harakatlar orqali barabanni aylantiring, coinlar to'plang va ularni haqiqiy pullarga (Uzcard/Humo) almashtiring!\n\n"
        "Boshlash uchun pastdagi tugmani bosing 👇"
    )
    await message.answer(welcome_text, reply_markup=builder.as_markup())

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("O'yinni boshlash uchun /start buyrug'idan foydalaning va Omadni sinab ko'ring!")
