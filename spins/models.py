from django.db import models
from django.conf import settings
from rewards.models import SpinBoard, Reward

class SpinLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='spin_logs')
    spin_board = models.ForeignKey(SpinBoard, on_delete=models.SET_NULL, null=True, related_name='spin_logs')
    reward = models.ForeignKey(Reward, on_delete=models.SET_NULL, null=True, related_name='spin_logs')
    reward_type_snapshot = models.CharField(max_length=50)
    reward_value_snapshot = models.PositiveIntegerField(default=0)
    was_free_spin = models.BooleanField(default=False)
    cost_snapshot = models.PositiveIntegerField(default=0)
    seed_reference = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} spun on {self.spin_board.name} -> {self.reward.name if self.reward else 'Unknown'}"
