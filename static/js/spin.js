let currentRotationConfig = 0;

function getRewardColor(r, index) {
    let name = r.name.toLowerCase();
    if (name.includes('oops') || name.includes('kelmadi')) return '#EF4444'; // Soft Red
    if (r.coin_amount >= 100 || name.includes('premium')) return '#D4A017'; // Gold
    if (name.includes('spin') || name.includes('qo\'shimcha')) return '#14B8A6'; // Muted Teal

    // Default alternating dark blues
    const darkBlues = ['#0F1B2E', '#1E293B'];
    return darkBlues[index % 2];
}

function initWheel(rewards) {
    const canvas = document.getElementById('spin-wheel');
    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;
    const center = width / 2;

    const sliceAngle = (2 * Math.PI) / rewards.length;
    ctx.clearRect(0, 0, width, height);

    for (let i = 0; i < rewards.length; i++) {
        let angle = i * sliceAngle;

        ctx.beginPath();
        ctx.fillStyle = getRewardColor(rewards[i], i);
        ctx.moveTo(center, center);
        ctx.arc(center, center, center, angle, angle + sliceAngle);
        ctx.fill();

        ctx.lineWidth = 1;
        ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        ctx.stroke();

        ctx.save();
        ctx.translate(center, center);
        ctx.rotate(angle + sliceAngle / 2);

        ctx.textAlign = 'right';
        // Force Gold or White text depending on background
        ctx.fillStyle = ctx.fillStyle === '#D4A017' ? '#081120' : '#F8FAFC';
        ctx.font = 'bold 13px Inter, sans-serif';

        let textLabel = rewards[i].coin_amount > 0 ? `+${rewards[i].coin_amount} coin` : rewards[i].name;
        if (textLabel.toLowerCase().includes('oops')) textLabel = 'Omad kelmadi';
        if (textLabel.toLowerCase().includes('free spin')) textLabel = 'Qo‘shimcha spin';

        ctx.fillText(rewards[i].icon || '🎁', center - 15, 4);
        ctx.fillText(textLabel, center - 40, 4);
        ctx.restore();
    }
}

function spinWheel() {
    if (!currentBoardId || !currentUserId) return;

    let btn = document.getElementById('btn-spin-action');
    btn.disabled = true;

    if (AppState.freeSpinsLeft <= 0 && AppState.spinCost > AppState.coinBalance) {
        if (tg && tg.showAlert) tg.showAlert('Not enough coins!');
        else alert('Not enough coins!');
        btn.disabled = false;
        return;
    }

    // Call API First
    fetch('/webapp/api/spin/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            telegram_id: currentUserId,
            board_id: currentBoardId
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                // Find the reward index to land on
                const rewardId = data.reward_id;
                const index = AppState.rewards.findIndex(r => r.id === rewardId);

                if (index === -1) {
                    // Should not happen, but safe fallback
                    updateBalance(data.new_balance);
                    alert(`Won: ${data.reward_name}!`);
                    btn.disabled = false;
                    return;
                }

                // Animation mathematics
                const slices = AppState.rewards.length;
                const sliceAngleDeg = 360 / slices;

                // The pointer is at the TOP (270 degrees in standard canvas, but visually standard top)
                // Due to drawing starting at 0 rightwards, we need to calculate offset relative to 270 deg.

                // Base config
                const selectedAngleCenter = (index * sliceAngleDeg) + (sliceAngleDeg / 2);

                // We want selectedAngleCenter to land near top (270 degrees)
                // Amount to rotate to bring it top
                const targetRotationOffset = 270 - selectedAngleCenter;

                // Add spins (e.g. 5 full spins = 1800 deg)
                const spins = 10;
                const offsetVariation = Math.floor(Math.random() * (sliceAngleDeg * 0.7)) - (sliceAngleDeg * 0.35); // Randomize within slice

                let finalRotation = (targetRotationOffset - (spins * 360) + offsetVariation);

                // To ensure it always rotates forward (adding degrees since transition expects continuous value changes)
                // We accumulate rotation config
                currentRotationConfig = currentRotationConfig - (spins * 360) - (currentRotationConfig % 360) + targetRotationOffset + offsetVariation;
                // Subtracting because CSS rotate uses clockwise, while canvas draws index clockwise. Wait. 
                // Better simpler math: We just rotate clockwise (add 360).

                const totalRotationDeg = currentRotationConfig + (spins * 360) + (360 - selectedAngleCenter) + 270 + offsetVariation;
                currentRotationConfig = totalRotationDeg;

                const canvas = document.getElementById('spin-wheel');
                canvas.style.transform = `rotate(${totalRotationDeg}deg)`;

                // Wait for transition end (4s)
                setTimeout(() => {
                    let wonName = data.reward_name;
                    if (wonName.toLowerCase().includes('oops')) wonName = 'Omad kelmadi';
                    if (wonName.toLowerCase().includes('free spin')) wonName = 'Qo‘shimcha spin';
                    if (wonName.toLowerCase().includes('premium')) wonName = 'Telegram Premium';

                    let msg = '';
                    if (data.premium_reward) {
                        msg = `🎉 Tabriklaymiz! Siz ${data.premium_reward.months} oylik Telegram Premium yutdingiz!\n\n` +
                              `📋 Tasdiqlash kodi: ${data.premium_reward.verification_code}\n` +
                              `⏰ Kodni 30 kun ichida ishlatishingiz mumkin.\n` +
                              `💰 Agar Premium kerak bo'lmasa, ${data.premium_reward.coin_value} coin ga almashtirishingiz mumkin.`;
                    } else if (wonName === 'Omad kelmadi') {
                        msg = `Afus, bu safar ${wonName} 😢`;
                    } else {
                        msg = `🎉 Tabriklaymiz! Yutug'ingiz: ${wonName}`;
                    }

                    if (tg && tg.showAlert) {
                        tg.showAlert(msg);
                    } else {
                        alert(msg);
                    }
                    updateBalance(data.new_balance);

                    // If it was a free spin, deduct 1 from left and update button
                    if (typeof data.free_spins_left !== 'undefined') {
                        AppState.freeSpinsLeft = data.free_spins_left;
                    } else if (AppState.freeSpinsLeft > 0) {
                        AppState.freeSpinsLeft--;
                    }
                    if (typeof updateSpinButtonUI === 'function') {
                        updateSpinButtonUI();
                    }
                    
                    // Refresh wallet if premium reward was won
                    if (data.premium_reward) {
                        if (typeof loadWithdrawalStatuses === 'function') {
                            loadWithdrawalStatuses();
                        }
                    }
                    
                    btn.disabled = false;
                }, 4100);

            } else {
                if (tg && tg.showAlert) tg.showAlert(data.error);
                else alert(data.error);
                btn.disabled = false;
            }
        })
        .catch(err => {
            console.error(err);
            btn.disabled = false;
        });
}
