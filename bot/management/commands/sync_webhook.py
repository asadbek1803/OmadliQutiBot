import os
from django.core.management.base import BaseCommand
from aiogram import Bot
from django.conf import settings
import asyncio

class Command(BaseCommand):
    help = 'Sync bot webhook with Telegram'

    def handle(self, *args, **kwargs):
        asyncio.run(self.set_webhook())

    async def set_webhook(self):
        bot = Bot(token=settings.BOT_TOKEN)
        url = f"{settings.WEBHOOK_HOST}{settings.WEBHOOK_PATH}"
        await bot.set_webhook(url=url)
        self.stdout.write(self.style.SUCCESS(f'Successfully set webhook to {url}'))
        await bot.session.close()
