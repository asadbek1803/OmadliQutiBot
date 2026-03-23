from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
import json

User = get_user_model()

def is_staff_user(user):
    """Check if user is staff"""
    return user.is_authenticated and user.is_staff

@user_passes_test(is_staff_user)
def admin_management_view(request):
    """Admin management page"""
    context = {
        'total_admins': User.objects.filter(is_staff=True).count(),
        'total_users': User.objects.count(),
        'recent_users': User.objects.order_by('-date_joined')[:10],
    }
    return render(request, 'admin/admin_management.html', context)

@csrf_exempt
@user_passes_test(is_staff_user)
def api_admin_list(request):
    """Get list of all admin users"""
    admins = User.objects.filter(is_staff=True).order_by('-date_joined')
    
    data = []
    for admin in admins:
        data.append({
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'first_name': admin.first_name,
            'last_name': admin.last_name,
            'is_superuser': admin.is_superuser,
            'is_active': admin.is_active,
            'date_joined': admin.date_joined.strftime('%d %b %Y %H:%M'),
            'last_login': admin.last_login.strftime('%d %b %Y %H:%M') if admin.last_login else None,
            'telegram_id': getattr(admin, 'telegram_id', None),
        })
    
    return JsonResponse({'success': True, 'admins': data})

@csrf_exempt
@user_passes_test(is_staff_user)
def api_admin_create(request):
    """Create new admin user"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        required_fields = ['username', 'password', 'email']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'success': False, 'error': f'{field} is required'}, status=400)
        
        # Check if username already exists
        if User.objects.filter(username=data['username']).exists():
            return JsonResponse({'success': False, 'error': 'Username already exists'}, status=400)
        
        # Check if email already exists
        if User.objects.filter(email=data['email']).exists():
            return JsonResponse({'success': False, 'error': 'Email already exists'}, status=400)
        
        # Create admin user
        admin = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data.get('first_name', ''),
            last_name=data.get('last_name', ''),
            is_staff=True,
            is_superuser=data.get('is_superuser', False),
            is_active=True
        )
        
        # Add telegram_id if provided
        if data.get('telegram_id'):
            admin.telegram_id = data['telegram_id']
            admin.save()
        
        return JsonResponse({
            'success': True,
            'admin': {
                'id': admin.id,
                'username': admin.username,
                'email': admin.email,
                'first_name': admin.first_name,
                'last_name': admin.last_name,
                'is_superuser': admin.is_superuser,
                'is_active': admin.is_active,
                'telegram_id': getattr(admin, 'telegram_id', None),
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@user_passes_test(is_staff_user)
def api_admin_update(request, admin_id):
    """Update admin user"""
    if request.method not in ['POST', 'PUT']:
        return JsonResponse({'success': False, 'error': 'POST/PUT required'}, status=405)
    
    try:
        admin = get_object_or_404(User, id=admin_id, is_staff=True)
        data = json.loads(request.body)
        
        # Update fields
        updatable_fields = ['email', 'first_name', 'last_name', 'telegram_id', 'is_superuser', 'is_active']
        for field in updatable_fields:
            if field in data:
                setattr(admin, field, data[field])
        
        # Update password if provided
        if data.get('password'):
            admin.set_password(data['password'])
        
        admin.save()
        
        return JsonResponse({'success': True, 'admin': {
            'id': admin.id,
            'username': admin.username,
            'email': admin.email,
            'first_name': admin.first_name,
            'last_name': admin.last_name,
            'is_superuser': admin.is_superuser,
            'is_active': admin.is_active,
            'telegram_id': getattr(admin, 'telegram_id', None),
        }})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Admin not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@user_passes_test(is_staff_user)
def api_admin_delete(request, admin_id):
    """Delete admin user"""
    if request.method != 'DELETE':
        return JsonResponse({'success': False, 'error': 'DELETE required'}, status=405)
    
    try:
        admin = get_object_or_404(User, id=admin_id, is_staff=True)
        
        # Don't allow deleting the last superuser
        if admin.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
            return JsonResponse({'success': False, 'error': 'Cannot delete the last superuser'}, status=400)
        
        # Don't allow self-deletion
        if admin.id == request.user.id:
            return JsonResponse({'success': False, 'error': 'Cannot delete yourself'}, status=400)
        
        username = admin.username
        admin.delete()
        
        return JsonResponse({'success': True, 'message': f'Admin {username} deleted successfully'})
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Admin not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@user_passes_test(is_staff_user)
def api_admin_stats(request):
    """Get admin statistics"""
    try:
        # Basic counts
        stats = {
            'total_admins': User.objects.filter(is_staff=True).count(),
            'active_admins': User.objects.filter(is_staff=True, is_active=True).count(),
            'superusers': User.objects.filter(is_staff=True, is_superuser=True).count(),
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
        }
        
        # Recent activity
        last_7_days = timezone.now() - timedelta(days=7)
        stats['new_users_7_days'] = User.objects.filter(date_joined__gte=last_7_days).count()
        stats['new_admins_7_days'] = User.objects.filter(date_joined__gte=last_7_days, is_staff=True).count()
        
        # Admin login activity
        stats['recent_logins'] = User.objects.filter(
            is_staff=True,
            last_login__gte=last_7_days
        ).count()
        
        return JsonResponse({'success': True, 'stats': stats})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@user_passes_test(is_staff_user)
def api_admin_toggle_status(request, admin_id):
    """Toggle admin active status"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        admin = get_object_or_404(User, id=admin_id, is_staff=True)
        
        # Don't allow deactivating yourself
        if admin.id == request.user.id:
            return JsonResponse({'success': False, 'error': 'Cannot deactivate yourself'}, status=400)
        
        admin.is_active = not admin.is_active
        admin.save()
        
        status_text = 'activated' if admin.is_active else 'deactivated'
        return JsonResponse({
            'success': True, 
            'message': f'Admin {admin.username} {status_text}',
            'is_active': admin.is_active
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Admin not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@user_passes_test(is_staff_user)
def api_admin_reset_password(request, admin_id):
    """Reset admin password"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=405)
    
    try:
        admin = get_object_or_404(User, id=admin_id, is_staff=True)
        data = json.loads(request.body)
        new_password = data.get('password')
        
        if not new_password or len(new_password) < 8:
            return JsonResponse({'success': False, 'error': 'Password must be at least 8 characters'}, status=400)
        
        admin.set_password(new_password)
        admin.save()
        
        return JsonResponse({'success': True, 'message': f'Password reset for {admin.username}'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Admin not found'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
