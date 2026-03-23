from django.shortcuts import get_object_or_404
from django.http import HttpResponse, Http404
from django.conf import settings
import os
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required

from withdrawals.models import RewardRequest

@require_GET
def serve_withdrawal_screenshot(request, filename):
    """
    Serve withdrawal screenshots with proper authentication
    """
    # Check if user is authenticated
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    
    # Find the reward request with this screenshot
    try:
        reward_request = RewardRequest.objects.get(screenshot=f'withdrawal_screenshots/{filename}')
        
        # Check if user has permission to view this screenshot
        # Allow if user is staff, admin, or the owner of the request
        if not (request.user.is_staff or request.user == reward_request.user):
            return HttpResponse('Forbidden', status=403)
        
        # Check if file exists
        file_path = os.path.join(settings.MEDIA_ROOT, 'withdrawal_screenshots', filename)
        if not os.path.exists(file_path):
            raise Http404("Screenshot not found")
        
        # Serve the file
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='image/jpeg')
            response['Content-Disposition'] = f'inline; filename="{filename}"'
            return response
            
    except RewardRequest.DoesNotExist:
        raise Http404("Screenshot not found")

@require_GET
@login_required
def serve_withdrawal_screenshots_list(request):
    """
    API endpoint to get list of screenshots for authenticated user
    """
    if request.user.is_staff:
        # Admin can see all screenshots
        screenshots = RewardRequest.objects.exclude(screenshot='').exclude(screenshot__isnull=True)
    else:
        # Regular users can only see their own screenshots
        screenshots = RewardRequest.objects.filter(
            user=request.user
        ).exclude(screenshot='').exclude(screenshot__isnull=True)
    
    screenshot_list = []
    for req in screenshots:
        if req.screenshot:
            screenshot_list.append({
                'id': req.id,
                'filename': os.path.basename(req.screenshot.name),
                'url': f"/withdrawal_screenshots/{os.path.basename(req.screenshot.name)}",
                'created_at': req.created_at.isoformat(),
                'status': req.status,
                'amount': req.amount_coin
            })
    
    from django.http import JsonResponse
    return JsonResponse({'success': True, 'screenshots': screenshot_list})
