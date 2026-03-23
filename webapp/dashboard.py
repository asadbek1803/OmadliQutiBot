from django.db.models import Sum
from accounts.models import User
from wallet.models import Wallet
from withdrawals.models import RewardRequest

def dashboard_callback(request, context):
    total_users = User.objects.count()
    total_coins = Wallet.objects.aggregate(Sum('coin_balance'))['coin_balance__sum'] or 0
    pending_withdraws = RewardRequest.objects.filter(status='pending').count()
    total_paid = RewardRequest.objects.filter(status='fulfilled').count()
    
    context.update({
        "kpi": [
            {
                "title": "Jami Foydalanuvchilar",
                "metric": total_users,
                "footer": "Barcha tizimga kirganlar",
            },
            {
                "title": "Foydalanuvchilardagi Coinlar",
                "metric": f"{total_coins:,}",
                "footer": "Tizimdagi jami aylanma tangalar",
            },
            {
                "title": "Kutilayotgan To'lovlar",
                "metric": pending_withdraws,
                "footer": "Yechib olish uchun so'rovlar",
            },
            {
                "title": "To'lab Berildi",
                "metric": total_paid,
                "footer": "Muvaffaqiyatli to'lovlar",
            },
        ],
    })
    return context
