# Test script for daily maintenance with scheduler
import os
import sys
import django

# Setup Django
sys.path.append(r'C:\Users\Lenovo\Desktop\OmadliQuti')
os.chdir(r'C:\Users\Lenovo\Desktop\OmadliQuti')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

def test_scheduler():
    """Test scheduler functionality"""
    print("Testing aiogram scheduler...")
    
    try:
        from bot.scheduler import start_scheduler, get_scheduler
        
        # Start scheduler
        scheduler = start_scheduler()
        
        if scheduler and scheduler.running:
            print("Scheduler started successfully!")
            
            # Show jobs
            jobs = scheduler.get_jobs()
            print(f"Active jobs: {len(jobs)}")
            
            for job in jobs:
                print(f"  - {job.name}: {job.next_run_time}")
            
            return True
        else:
            print("Scheduler failed to start")
            return False
            
    except Exception as e:
        print(f"Error testing scheduler: {e}")
        return False

def test_maintenance():
    """Test daily maintenance"""
    print("\nTesting daily maintenance...")
    
    try:
        from django.core.management import call_command
        
        # Test backup only
        call_command('daily_maintenance', '--backup-only')
        print("Backup test completed!")
        
        # Test cleanup only
        call_command('daily_maintenance', '--cleanup-only')
        print("Cleanup test completed!")
        
        return True
        
    except Exception as e:
        print(f"Error testing maintenance: {e}")
        # Try alternative command
        try:
            print("Trying alternative command...")
            call_command('daily_maintenance_with_scheduler', '--backup-only')
            print("Alternative backup test completed!")
            return True
        except Exception as e2:
            print(f"Alternative also failed: {e2}")
            return False

def test_combined():
    """Test combined maintenance with scheduler"""
    print("\nTesting combined maintenance with scheduler...")
    
    try:
        from django.core.management import call_command
        
        # Test combined command
        call_command('daily_maintenance_with_scheduler')
        print("Combined test completed!")
        
        return True
        
    except Exception as e:
        print(f"Error testing combined: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING DAILY MAINTENANCE WITH SCHEDULER")
    print("=" * 60)
    
    # Test individual components
    scheduler_ok = test_scheduler()
    maintenance_ok = test_maintenance()
    
    # Test combined
    if scheduler_ok and maintenance_ok:
        combined_ok = test_combined()
        
        if combined_ok:
            print("\nAll tests passed!")
            print("\nSetup complete! You can now:")
            print("1. Run: python manage.py daily_maintenance_with_scheduler")
            print("2. Set up Windows Task Scheduler")
            print("3. Check backup folder: backups/")
            print("4. Monitor scheduler logs")
        else:
            print("\nCombined test failed")
    else:
        print("\nSome tests failed. Check the errors above.")
    
    print("\n" + "=" * 60)
