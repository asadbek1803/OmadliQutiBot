"""
URL configuration for admin dashboard + withdrawal management.

Include this file in your project's main urls.py:

    from django.urls import path, include

    urlpatterns = [
        ...
        path('admin-panel/', include('your_app.urls')),
        ...
    ]
"""

from django.urls import path
from . import views

# ── Admin dashboard ───────────────────────────────────────────
dashboard_patterns = [
    path('', views.AdminDashboardView.as_view(), name='admin_dashboard'),
]

# ── Premium rewards API ───────────────────────────────────────
premium_patterns = [
    path('list/',    views.api_premium_rewards_list,   name='api_premium_rewards_list'),
    path('verify/',  views.api_premium_reward_verify,  name='api_premium_reward_verify'),
    path('convert/', views.api_premium_reward_convert, name='api_premium_reward_convert'),
    path('user/',    views.api_user_premium_rewards,   name='api_user_premium_rewards'),
]

# ── Withdrawal API ────────────────────────────────────────────
withdrawal_patterns = [
    # List & stats
    path('list/',   views.api_withdrawals_list,   name='api_withdrawals_list'),
    path('stats/',  views.api_withdrawal_stats,   name='api_withdrawal_stats'),
    path('config/', views.api_withdrawal_config,  name='api_withdrawal_config'),

    # Single-item actions
    path('action/',          views.api_withdrawal_action,   name='api_withdrawal_action'),
    path('bulk/',            views.api_withdrawal_bulk_action, name='api_withdrawal_bulk_action'),
    path('<int:request_id>/', views.api_withdrawal_detail,  name='api_withdrawal_detail'),

    # Screenshot serving
    path(
        'screenshots/<str:filename>',
        views.serve_withdrawal_screenshot,
        name='serve_withdrawal_screenshot',
    ),
    path(
        'screenshots/',
        views.serve_withdrawal_screenshots_list,
        name='serve_withdrawal_screenshots_list',
    ),
]

# ── Unified admin-stats endpoint ──────────────────────────────
# ── Admin Management ───────────────────────────────────────
admin_patterns = [
    path('management/', views.admin_management_view, name='admin_management'),
    path('api/admins/list/', views.api_admin_list, name='api_admin_list'),
    path('api/admins/create/', views.api_admin_create, name='api_admin_create'),
    path('api/admins/<int:admin_id>/', views.api_admin_update, name='api_admin_update'),
    path('api/admins/<int:admin_id>/delete/', views.api_admin_delete, name='api_admin_delete'),
    path('api/admins/<int:admin_id>/toggle/', views.api_admin_toggle_status, name='api_admin_toggle_status'),
    path('api/admins/<int:admin_id>/reset-password/', views.api_admin_reset_password, name='api_admin_reset_password'),
    path('api/admins/stats/', views.api_admin_stats, name='api_admin_stats'),
]

urlpatterns = [
    # Dashboard page
    *[path('dashboard/' + p.pattern._route, p.callback, name=p.name) for p in dashboard_patterns],

    # API namespaces
    *[path('rewards/api/premium-rewards/' + p.pattern._route, p.callback, name=p.name) for p in premium_patterns],
    *[path('withdrawals/api/' + p.pattern._route, p.callback, name=p.name) for p in withdrawal_patterns],
    *[path('admin/' + p.pattern._route, p.callback, name=p.name) for p in admin_patterns],

    # Direct API patterns for debugging
    path('api/premium-rewards/user/', views.api_user_premium_rewards, name='api_user_premium_rewards_direct'),
    path('api/premium-rewards/list/', views.api_premium_rewards_list, name='api_premium_rewards_list_direct'),

    # Shared admin stats (used by dashboard JS)
    path('rewards/api/admin/stats/', views.api_admin_stats, name='api_admin_stats'),
]