# SQLite optimization middleware
from django.db import connection
from django.utils.deprecation import MiddlewareMixin

class SQLiteOptimizationMiddleware(MiddlewareMixin):
    """
    Middleware to optimize SQLite database performance
    """
    
    def process_request(self, request):
        if 'sqlite' in connection.vendor:
            cursor = connection.cursor()
            # Enable WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            # Set cache size (2MB = -2000KB)
            cursor.execute("PRAGMA cache_size=-2000")
            # Store temp tables in memory
            cursor.execute("PRAGMA temp_store=MEMORY")
            # Enable memory-mapped I/O (256MB)
            cursor.execute("PRAGMA mmap_size=268435456")
            # Optimize for performance
            cursor.execute("PRAGMA synchronous=NORMAL")
            # Optimize foreign key checks
            cursor.execute("PRAGMA foreign_keys=ON")
            # Set busy timeout to 20 seconds
            cursor.execute("PRAGMA busy_timeout=20000")
            cursor.close()
        return None
    
    def process_response(self, request, response):
        # Optional: Add performance headers
        if 'sqlite' in connection.vendor:
            response['X-DB-Engine'] = 'SQLite'
            response['X-DB-Optimized'] = 'True'
        return response

# Custom CSRF exempt middleware for API endpoints
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

class APIRequestMiddleware(MiddlewareMixin):
    """
    Middleware to handle API requests without CSRF
    """
    
    def process_request(self, request):
        # Check if this is an API request
        if request.path.startswith('/rewards/api/') or request.path.startswith('/notifications/api/') or request.path.startswith('/withdrawals/api/'):
            # Mark request as CSRF exempt for API endpoints
            request.csrf_processing_done = True
        return None
