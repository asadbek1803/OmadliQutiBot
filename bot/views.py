import json
import logging
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from aiogram import Bot, Dispatcher, types
from bot.handlers import router

logger = logging.getLogger(__name__)

dp = Dispatcher()
dp.include_router(router)

@method_decorator(csrf_exempt, name='dispatch')
class BotWebhookView(View):
    async def post(self, request, *args, **kwargs):
        try:
            update_data = json.loads(request.body.decode('utf-8'))
            update = types.Update(**update_data)
            
            # Using context manager for Bot automatically handles session closing and
            # prevents "Event loop is closed" errors while preserving performance.
            async with Bot(token=settings.BOT_TOKEN) as bot:
                await dp.feed_update(bot, update)
                
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            error_msg = str(e)
            # Handle specific Telegram bot errors gracefully
            if "Forbidden: bot was blocked by the user" in error_msg:
                logger.warning(f"User blocked the bot: {error_msg}")
                # Mark user as blocked in database if possible
                try:
                    update_data = json.loads(request.body.decode('utf-8'))
                    update = types.Update(**update_data)
                    if update.message and update.message.from_user:
                        from accounts.models import User
                        User.objects.filter(telegram_id=update.message.from_user.id).update(is_blocked=True)
                except:
                    pass  # Ignore errors in user blocking logic
                return JsonResponse({'status': 'user_blocked'}, status=200)
            else:
                logger.error(f"Error handling webhook: {e}")
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
