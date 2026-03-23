# Aiogram scheduler for bot
import asyncio
import logging
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from django.conf import settings
from aiogram import Bot

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None
bot = None

def get_scheduler():
    """Get or create scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler()
    return scheduler

def get_bot():
    """Get bot instance"""
    global bot
    if bot is None and settings.BOT_TOKEN:
        bot = Bot(token=settings.BOT_TOKEN)
    return bot

async def send_daily_reminders():
    """Send daily reminders to users"""
    try:
        bot_instance = get_bot()
        if not bot_instance:
            logger.error("Bot instance not available")
            return
        
        from accounts.models import User
        from notifications.services import NotificationService
        
        # Get all active users
        users = User.objects.filter(is_active=True)
        
        for user in users:
            if user.telegram_id:
                # Create notification
                NotificationService.send_notification(
                    user=user,
                    notification_type='daily_bonus',
                    title='🌅 Kunlik bonus!',
                    message='Har kuni 50 coin bepul bonus olish uchun botga kiring!',
                    data={'bonus_coins': 50}
                )
                
                # Send Telegram message
                try:
                    await bot_instance.send_message(
                        user.telegram_id,
                        '🌅 *Kunlik bonus!*\n\n'
                        'Har kuni 50 coin bepul bonus olish uchun botga kiring!\n'
                        '🎰 Spin orqali ko\'proq coin yuting!',
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Failed to send daily reminder to {user.telegram_id}: {e}")
        
        logger.info(f"Daily reminders sent to {users.count()} users")
        
    except Exception as e:
        logger.error(f"Error in daily reminders: {e}")

async def delete_old_schedules():
    """Clean up old scheduled tasks"""
    try:
        scheduler_instance = get_scheduler()
        
        # Remove completed jobs older than 24 hours
        jobs = scheduler_instance.get_jobs()
        removed_count = 0
        
        for job in jobs:
            if job.name.startswith('temp_') and job.next_run_time and job.next_run_time < datetime.now():
                scheduler_instance.remove_job(job.id)
                removed_count += 1
        
        logger.info(f"Cleaned up {removed_count} old scheduled tasks")
        
    except Exception as e:
        logger.error(f"Error cleaning up schedules: {e}")

def start_scheduler():
    """Start scheduler"""
    try:
        import asyncio
        
        # Check if event loop is running
        try:
            loop = asyncio.get_running_loop()
            # If loop is running, create a new task
            loop.create_task(_start_scheduler_async())
            logger.info("Scheduler task added to existing event loop")
        except RuntimeError:
            # No running loop, create new one
            asyncio.run(_start_scheduler_async())
            logger.info("Scheduler started with new event loop")
        
        return get_scheduler()
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        return None

async def _start_scheduler_async():
    """Async scheduler startup"""
    try:
        scheduler_instance = get_scheduler()
        
        # Add daily reminders job - every day at 9:00 AM
        scheduler_instance.add_job(
            send_daily_reminders,
            CronTrigger(hour=9, minute=0),
            id='daily_reminders',
            name='Daily Reminders',
            replace_existing=True,
            misfire_grace_time=300  # 5 minutes grace period
        )
        
        # Add cleanup job - every day at 3:00 AM
        scheduler_instance.add_job(
            delete_old_schedules,
            CronTrigger(hour=3, minute=0),
            id='delete_old_schedules',
            name='Cleanup Old Schedules',
            replace_existing=True,
            misfire_grace_time=300
        )
        
        # Start scheduler
        scheduler_instance.start()
        
        logger.info("Scheduler started successfully")
        logger.info(f"Daily reminders scheduled for 09:00")
        logger.info(f"Cleanup scheduled for 03:00")
        
        return scheduler_instance
        
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        return None

def stop_scheduler():
    """Stop the scheduler"""
    try:
        scheduler_instance = get_scheduler()
        if scheduler_instance and scheduler_instance.running:
            scheduler_instance.shutdown()
            logger.info("Scheduler stopped")
        
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}")

def add_custom_job(func, trigger, job_id=None, **kwargs):
    """Add a custom job to the scheduler"""
    try:
        scheduler_instance = get_scheduler()
        
        if not scheduler_instance.running:
            scheduler_instance.start()
        
        scheduler_instance.add_job(
            func,
            trigger,
            id=job_id,
            replace_existing=True,
            **kwargs
        )
        
        logger.info(f"Custom job '{job_id}' added to scheduler")
        
    except Exception as e:
        logger.error(f"Failed to add custom job: {e}")

def remove_job(job_id):
    """Remove a job from the scheduler"""
    try:
        scheduler_instance = get_scheduler()
        scheduler_instance.remove_job(job_id)
        logger.info(f"Job '{job_id}' removed from scheduler")
        
    except Exception as e:
        logger.error(f"Failed to remove job: {e}")

def get_jobs():
    """Get all scheduled jobs"""
    try:
        scheduler_instance = get_scheduler()
        return scheduler_instance.get_jobs()
        
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        return []

# For testing
if __name__ == "__main__":
    async def test():
        start_scheduler()
        
        # Keep running for testing
        try:
            while True:
                await asyncio.sleep(60)
        except KeyboardInterrupt:
            stop_scheduler()
    
    asyncio.run(test())
