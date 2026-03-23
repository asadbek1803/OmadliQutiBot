# Combined server and maintenance command
import os
import sys
import django
import subprocess
import threading
import time
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection

# Django sozlamalari
sys.path.append(r'C:\Users\Lenovo\Desktop\OmadliQuti')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

class Command(BaseCommand):
    help = 'Run Django server with daily maintenance'

    def add_arguments(self, parser):
        parser.add_argument(
            '--port',
            type=int,
            default=8000,
            help='Port to run server on (default: 8000)',
        )
        parser.add_argument(
            '--maintenance-time',
            type=str,
            default='00:00',
            help='Daily maintenance time (default: 00:00)',
        )
        parser.add_argument(
            '--backup-only',
            action='store_true',
            help='Only create backup, no cleanup',
        )
        parser.add_argument(
            '--cleanup-only',
            action='store_true',
            help='Only cleanup old logs, no backup',
        )
        parser.add_argument(
            '--no-scheduler',
            action='store_true',
            help='Skip aiogram scheduler',
        )

    def handle(self, *args, **options):
        port = options['port']
        maintenance_time = options['maintenance_time']
        
        self.stdout.write(f'Starting server on port {port}...')
        self.stdout.write(f'Daily maintenance scheduled for {maintenance_time}')
        
        # Start maintenance scheduler in background
        maintenance_thread = threading.Thread(
            target=self.run_maintenance_scheduler,
            args=(maintenance_time, options),
            daemon=True
        )
        maintenance_thread.start()
        
        # Start aiogram scheduler if not disabled
        if not options.get('no_scheduler'):
            scheduler_thread = threading.Thread(
                target=self.start_aiogram_scheduler,
                daemon=True
            )
            scheduler_thread.start()
        
        # Start Django server (this blocks)
        try:
            subprocess.run([
                sys.executable, 'manage.py', 'runserver', f'0.0.0.0:{port}'
            ], check=True)
        except KeyboardInterrupt:
            self.stdout.write('\nServer stopped by user')
        except Exception as e:
            self.stdout.write(f'Error running server: {e}')

    def run_maintenance_scheduler(self, maintenance_time, options):
        """Run daily maintenance at specified time"""
        try:
            while True:
                now = datetime.now()
                target_time = datetime.strptime(maintenance_time, '%H:%M').time()
                
                # Calculate next maintenance time
                next_maintenance = datetime.combine(
                    now.date(), target_time
                )
                
                # If time has passed today, schedule for tomorrow
                if next_maintenance <= now:
                    next_maintenance += timedelta(days=1)
                
                # Sleep until maintenance time
                sleep_seconds = (next_maintenance - now).total_seconds()
                self.stdout.write(f'Next maintenance in {sleep_seconds/3600:.1f} hours')
                
                time.sleep(min(sleep_seconds, 3600))  # Check every hour
                
                # Check if it's maintenance time
                if datetime.now().time().hour == target_time.hour and \
                   datetime.now().time().minute == target_time.minute:
                    self.run_maintenance(options)
                    
        except Exception as e:
            self.stdout.write(f'Maintenance scheduler error: {e}')

    def run_maintenance(self, options):
        """Run maintenance tasks"""
        try:
            self.stdout.write('Running daily maintenance...')
            
            # Create backup
            if not options.get('cleanup_only'):
                self.create_backup()
            
            # Cleanup old logs
            if not options.get('backup_only'):
                self.cleanup_old_logs()
            
            self.stdout.write('Daily maintenance completed!')
            
        except Exception as e:
            self.stdout.write(f'Maintenance failed: {e}')

    def create_backup(self):
        """Create daily database backup"""
        try:
            # Get database path
            db_path = settings.DATABASES['default']['NAME']
            if not db_path:
                self.stdout.write('No database path found')
                return
            
            # Create backup filename
            today = datetime.now().strftime('%Y%m%d')
            backup_dir = os.path.join(settings.BASE_DIR, 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            backup_filename = f'{today}_backup.sqlite3'
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Copy database
            import shutil
            shutil.copy2(db_path, backup_path)
            
            # Compress backup
            compressed_path = f'{backup_path}.gz'
            with open(backup_path, 'rb') as f_in:
                import gzip
                with gzip.open(compressed_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # Remove uncompressed backup
            os.remove(backup_path)
            
            self.stdout.write(f'Backup created: {compressed_path}')
            
            # Keep only last 7 days of backups
            self.cleanup_old_backups(backup_dir)
            
        except Exception as e:
            self.stdout.write(f'Backup failed: {str(e)}')

    def cleanup_old_backups(self, backup_dir):
        """Keep only last 7 days of backups"""
        try:
            backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.sqlite3.gz')]
            
            # Sort by date (filename starts with YYYYMMDD)
            backup_files.sort(reverse=True)
            
            # Keep only first 7 (newest)
            for old_backup in backup_files[7:]:
                old_path = os.path.join(backup_dir, old_backup)
                os.remove(old_path)
                self.stdout.write(f'Removed old backup: {old_backup}')
                
        except Exception as e:
            self.stdout.write(f'Backup cleanup failed: {str(e)}')

    def cleanup_old_logs(self):
        """Clean up old log entries"""
        try:
            from spins.models import SpinLog
            from referrals.models import ReferralTransactionLog
            from wallet.models import Ledger
            from django.utils import timezone
            
            # Delete logs older than 30 days
            cutoff_date = timezone.now() - timedelta(days=30)
            
            # Clean SpinLog
            spin_count = SpinLog.objects.filter(created_at__lt=cutoff_date).delete()[0]
            if spin_count > 0:
                self.stdout.write(f'Cleaned {spin_count} old spin logs')
            
            # Clean ReferralTransactionLog
            referral_count = ReferralTransactionLog.objects.filter(created_at__lt=cutoff_date).delete()[0]
            if referral_count > 0:
                self.stdout.write(f'Cleaned {referral_count} old referral logs')
            
            # Clean Ledger (keep only last 90 days)
            ledger_cutoff = timezone.now() - timedelta(days=90)
            ledger_count = Ledger.objects.filter(created_at__lt=ledger_cutoff).delete()[0]
            if ledger_count > 0:
                self.stdout.write(f'Cleaned {ledger_count} old ledger entries')
            
            # Optimize database
            self.optimize_database()
            
        except Exception as e:
            self.stdout.write(f'Log cleanup failed: {str(e)}')

    def optimize_database(self):
        """Optimize SQLite database"""
        try:
            with connection.cursor() as cursor:
                # Analyze tables
                cursor.execute("ANALYZE")
                
                # Vacuum database
                cursor.execute("VACUUM")
                
                # Rebuild indexes
                cursor.execute("REINDEX")
                
            self.stdout.write('Database optimized')
            
        except Exception as e:
            self.stdout.write(f'Database optimization failed: {str(e)}')

    def start_aiogram_scheduler(self):
        """Start aiogram scheduler"""
        try:
            self.stdout.write('Starting aiogram scheduler...')
            
            # Import and start bot scheduler
            from bot.scheduler import start_scheduler
            start_scheduler()
            
            self.stdout.write('Aiogram scheduler started')
            
        except Exception as e:
            self.stdout.write(f'Failed to start scheduler: {str(e)}')

if __name__ == '__main__':
    # Run directly for testing
    command = Command()
    command.handle()
