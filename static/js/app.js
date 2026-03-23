let tg = window.Telegram ? window.Telegram.WebApp : null;
let currentUserId = null;
let currentBoardId = null;

const AppState = {
    rewards: [],
    spinCost: 50,
    coinBalance: 0,
    freeSpinsLeft: 0,
    secondsUntilNextDay: 0,
    timerInterval: null,
    uzsRate: 100
};

document.addEventListener("DOMContentLoaded", () => {
    if (tg) tg.ready();
    if (tg && tg.expand) tg.expand();

    // Mock user for local testing if tg is not available
    let initDataStr = tg && tg.initData ? tg.initData : '';
    let testTgId = 123456789; // Will be passed or hardcoded if testing browser
    if (tg && tg.initDataUnsafe && tg.initDataUnsafe.user) {
        testTgId = tg.initDataUnsafe.user.id;
    }

    // Auth Check
    fetch('/webapp/api/init/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            initData: initDataStr,
            telegram_id: testTgId // In production, never trust client ID without initData verify
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('loader').classList.add('d-none');
                document.getElementById('app').classList.remove('d-none');

                document.getElementById('user-name').innerText = data.user.username;
                if (data.user.level) {
                    let lvl = document.getElementById('user-level');
                    if (lvl) lvl.innerHTML = `${data.user.level.badge} ${data.user.level.name}`;
                }
                updateBalance(data.user.coin_balance);

                if (data.user.uzs_rate) {
                    AppState.uzsRate = data.user.uzs_rate;
                    updateBalance(data.user.coin_balance); // re-trigger specific to rate
                }

                currentUserId = testTgId;

                if (data.user.is_blocked) {
                    document.getElementById('app').innerHTML = `
                <div class="d-flex flex-column align-items-center justify-content-center h-100 text-center p-4">
                    <i class="fa-solid fa-triangle-exclamation text-danger" style="font-size: 5rem; margin-bottom: 20px;"></i>
                    <h3 class="text-white fw-bold">Siz bloklangansiz!</h3>
                    <p class="text-secondary mt-2">Kechirasiz, siz admin tomonidan bloklangansiz. Dasturdan foydalana olmaysiz.</p>
                </div>`;
                    return;
                }

                if (data.board) {
                    currentBoardId = data.board.id;
                    AppState.spinCost = data.board.spin_cost;
                    AppState.freeSpinsLeft = data.user.free_spins_left;
                    AppState.secondsUntilNextDay = data.user.seconds_until_next_day;

                    // Update referral link
                    let refInput = document.getElementById('ref-link');
                    if (refInput && data.user.referral_code) {
                        refInput.value = `https://t.me/OmadliQutiRoBot?start=${data.user.referral_code}`;
                    }

                    let refCountEl = document.getElementById('ref-count-display');
                    let refCoinsEl = document.getElementById('ref-coins-display');
                    let cardRefCountEl = document.getElementById('card-ref-count');
                    if(refCountEl) refCountEl.innerText = data.user.referral_count || 0;
                    if(refCoinsEl) refCoinsEl.innerText = (data.user.referral_coins || 0).toLocaleString();
                    if(cardRefCountEl) cardRefCountEl.innerText = data.user.referral_count || 0;

                    // Update transactions
                    let txList = document.getElementById('recent-activity-list');
                    if (data.user.transactions && data.user.transactions.length > 0) {
                        txList.innerHTML = '';
                        data.user.transactions.forEach(tx => {
                            let color = tx.amount > 0 ? 'text-success' : 'text-danger';
                            let sign = tx.amount > 0 ? '+' : '';
                            let icon = tx.amount > 0 ? 'fa-arrow-down' : 'fa-arrow-up';
                            txList.innerHTML += `
                            <div class="premium-card p-3 mb-2 d-flex justify-content-between align-items-center text-start">
                                <div>
                                    <h6 class="mb-1 text-white"><i class="fa-solid ${icon} ${color} me-2"></i> ${tx.note}</h6>
                                    <span class="text-secondary small">${tx.date}</span>
                                </div>
                                <h5 class="${color} mb-0 fw-bold">${sign}${tx.amount}</h5>
                            </div>
                        `;
                        });
                    }

                    AppState.spinCost = data.board.spin_cost || 50;
                    updateSpinButtonUI();
                    startCountdownTimer();

                    AppState.rewards = data.board.rewards;
                    renderRewardsCatalog(AppState.rewards);
                    if (typeof initWheel === 'function') {
                        initWheel(AppState.rewards);
                    }
                }

                // Continuous rain in background
                startCoinRain();

                // Show default dash
                navigateTo('dashboard', document.querySelector('.nav-item.active'));
            } else {
                alert('Setup error or user not created in db. Please run telegram bot /start command first.');
            }
        })
        .catch(err => {
            console.error(err);
            alert('Server unreachable or config error');
        });
});

function updateBalance(amount) {
    AppState.coinBalance = amount;
    let els = ['coin-balance', 'wallet-balance-big', 'card-coin-balance'];
    els.forEach(id => {
        let el = document.getElementById(id);
        if(el) el.innerText = amount;
    });
    
    let uzsSum = amount * AppState.uzsRate;
    let uzsEl = document.getElementById('wallet-balance-uzs');
    if(uzsEl) uzsEl.innerText = uzsSum.toLocaleString();
}

function navigateTo(pageId, navElement = null) {
    document.querySelectorAll('.page').forEach(p => p.classList.add('d-none'));
    document.getElementById(`page-${pageId}`).classList.remove('d-none');

    if (navElement) {
        document.querySelectorAll('.bottom-nav .nav-item').forEach(n => n.classList.remove('active'));
        navElement.classList.add('active');
    }

    if (pageId === 'leaders') {
        loadLeaders();
    } else if (pageId === 'tasks') {
        loadTasks();
    } else if (pageId === 'wallet') {
        loadWithdrawalStatuses();
    }
}

function loadWithdrawalStatuses() {
    let container = document.getElementById('withdrawal-status-list');
    let premiumContainer = document.getElementById('premium-rewards-list');
    
    container.innerHTML = '<div class="text-center text-secondary py-3">Yuklanmoqda...</div>';
    premiumContainer.innerHTML = '<div class="text-center text-secondary py-3">Yuklanmoqda...</div>';

    // Load withdrawal statuses
    fetch('/webapp/api/wallet/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegram_id: currentUserId })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                container.innerHTML = '';
                if (data.withdrawals.length === 0) {
                    container.innerHTML = '<div class="premium-card p-3 text-center"><i class="fa-solid fa-hourglass-half text-secondary fs-1 mb-2 opacity-50"></i><p class="text-muted small mb-0">Hozircha so\'rovlar yo\'q</p></div>';
                    return;
                }
                
                data.withdrawals.forEach(w => {
                    const statusColors = {
                        'pending': 'text-warning',
                        'approved': 'text-info', 
                        'rejected': 'text-danger',
                        'fulfilled': 'text-success'
                    };
                    
                    const statusTexts = {
                        'pending': 'Kutilmoqda',
                        'approved': 'Tasdiqlandi',
                        'rejected': 'Rad etildi',
                        'fulfilled': 'Bajarildi'
                    };
                    
                    const statusColor = statusColors[w.status] || 'text-secondary';
                    const statusText = statusTexts[w.status] || w.status;
                    
                    let screenshotHtml = '';
                    if (w.screenshot_url) {
                        screenshotHtml = `
                            <div class="mt-2">
                                <img src="${w.screenshot_url}" alt="Screenshot" style="max-width: 100%; height: auto; border-radius: 8px;" onclick="window.open('${w.screenshot_url}', '_blank')">
                            </div>
                        `;
                    }
                    
                    container.innerHTML += `
                        <div class="premium-card p-3">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <h6 class="mb-1 text-white">${w.amount_coin} Coin</h6>
                                    <span class="small ${statusColor} fw-bold">${statusText}</span>
                                </div>
                                <div class="text-end">
                                    <small class="text-secondary">${w.created_at}</small>
                                </div>
                            </div>
                            <div class="small text-secondary">
                                <div>${w.card_label}: ${w.masked_card}</div>
                                <div>${w.holder_name}</div>
                                ${w.processed_at ? `<div class="text-info mt-1">Qayta ishlandi: ${w.processed_at}</div>` : ''}
                                ${w.admin_comment ? `<div class="text-muted mt-1">Izoh: ${w.admin_comment}</div>` : ''}
                            </div>
                            ${screenshotHtml}
                        </div>
                    `;
                });
            }
        })
        .catch(e => {
            container.innerHTML = '<div class="text-danger text-center py-3">Xatolik yuz berdi</div>';
        });

    // Load Premium rewards
    fetch('/rewards/api/premium-rewards/user/', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify({ telegram_id: currentUserId })
    })
        .then(r => {
            console.log('Response status:', r.status);
            console.log('Response URL:', r.url);
            return r.json();
        })
        .then(data => {
            if (data.success) {
                premiumContainer.innerHTML = '';
                if (data.rewards.length === 0) {
                    premiumContainer.innerHTML = '<div class="premium-card p-3 text-center"><i class="fa-solid fa-crown text-warning fs-1 mb-2 opacity-50"></i><p class="text-muted small mb-0">Hozircha Premium so\'rovlar yo\'q</p></div>';
                    return;
                }
                
                data.rewards.forEach(reward => {
                    const statusColors = {
                        'pending': 'text-warning',
                        'verified': 'text-info',
                        'redeemed': 'text-success',
                        'converted': 'text-warning',
                        'expired': 'text-danger'
                    };
                    
                    const statusTexts = {
                        'pending': 'Kutilmoqda',
                        'verified': 'Tasdiqlangan',
                        'redeemed': 'Yechilgan',
                        'converted': 'Coin ga almashtirilgan',
                        'expired': 'Muddati o\'tgan'
                    };
                    
                    const statusColor = statusColors[reward.status] || 'text-secondary';
                    const statusText = statusTexts[reward.status] || reward.status;
                    
                    let actionButtons = '';
                    if (reward.status === 'verified' && !reward.is_expired) {
                        actionButtons = `
                            <div class="mt-2 d-flex gap-2">
                                <button class="btn btn-sm btn-success" onclick="convertPremiumToCoins('${reward.id}')">
                                    <i class="fa-solid fa-coins me-1"></i> Coin ga almashtirish
                                </button>
                            </div>
                        `;
                    }
                    
                    let verificationCode = '';
                    if (reward.verification_code) {
                        verificationCode = `
                            <div class="mt-2">
                                <small class="text-muted">Tasdiqlash kodi:</small>
                                <div class="code-display">
                                    <code class="text-warning fs-5">${reward.verification_code}</code>
                                </div>
                            </div>
                        `;
                    }
                    
                    let expiryInfo = '';
                    if (reward.expires_at) {
                        const expiredClass = reward.is_expired ? 'text-danger' : 'text-info';
                        expiryInfo = `
                            <div class="mt-1">
                                <small class="${expiredClass}">
                                    ${reward.is_expired ? 'Muddati o\'tgan' : `Amal qiladi: ${reward.expires_at}`}
                                </small>
                            </div>
                        `;
                    }
                    
                    premiumContainer.innerHTML += `
                        <div class="premium-card p-3">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <div>
                                    <h6 class="mb-1 text-white">
                                        <i class="fa-solid fa-crown text-warning me-2"></i>
                                        ${reward.reward_name}
                                    </h6>
                                    <span class="small ${statusColor} fw-bold">${statusText}</span>
                                </div>
                                <div class="text-end">
                                    <small class="text-secondary">${reward.created_at}</small>
                                </div>
                            </div>
                            <div class="small text-secondary">
                                <div>Muddat: ${reward.months} oy</div>
                                <div>Coin qiymati: ${reward.coin_value}</div>
                                ${expiryInfo}
                            </div>
                            ${verificationCode}
                            ${actionButtons}
                        </div>
                    `;
                });
            }
        })
        .catch(e => {
            premiumContainer.innerHTML = '<div class="text-danger text-center py-3">Xatolik yuz berdi</div>';
        });
}

function convertPremiumToCoins(rewardId) {
    if (!confirm('Telegram Premium ni coin ga almashtirishni tasdiqlaysizmi?')) {
        return;
    }

    fetch('/rewards/api/premium-rewards/convert/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            telegram_id: currentUserId,
            reward_id: rewardId
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateBalance(data.new_balance);
                if (tg && tg.showAlert) tg.showAlert(`Muvaffaqiyatli almashtirildi! +${data.new_balance - (data.new_balance - 5000)} Coin`);
                else alert(`Muvaffaqiyatli almashtirildi! Yangi balans: ${data.new_balance} Coin`);
                loadWithdrawalStatuses(); // Refresh the premium rewards list
            } else {
                if (tg && tg.showAlert) tg.showAlert(data.error || "Xatolik yuz berdi");
                else alert(data.error || "Xatolik yuz berdi");
            }
        })
        .catch(e => {
            alert("Xatolik yuz berdi");
        });
}

function toggleNotifications() {
    const dropdown = document.getElementById('notification-dropdown');
    if (dropdown.style.display === 'none' || dropdown.style.display === '') {
        dropdown.style.display = 'block';
        loadNotifications();
    } else {
        dropdown.style.display = 'none';
    }
}

// Close notifications when clicking outside
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('notification-dropdown');
    const button = event.target.closest('button[onclick="toggleNotifications()"]');
    
    if (!dropdown.contains(event.target) && !button) {
        dropdown.style.display = 'none';
    }
});

// Notification System
let notificationCount = 0;
let notifications = [];

function loadNotifications() {
    fetch('/notifications/api/list/', {
        method: 'GET',
        headers: { 'X-CSRFToken': getCookie('csrftoken') }
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                notifications = data.notifications;
                notificationCount = data.unread_count;
                updateNotificationBadge();
                showNotificationPopup();
            }
        })
        .catch(e => console.error('Notifications loading error:', e));
}

function updateNotificationBadge() {
    const badge = document.getElementById('notification-badge');
    if (badge) {
        if (notificationCount > 0) {
            badge.textContent = notificationCount > 99 ? '99+' : notificationCount;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    }
}

function showNotificationPopup() {
    const container = document.getElementById('notification-popup');
    if (!container) return;

    if (notifications.length === 0) {
        container.innerHTML = `
            <div class="notification-item text-center text-muted py-3">
                <i class="fas fa-bell-slash fa-2x mb-2"></i>
                <div>Bildirishnomalar yo'q</div>
            </div>
        `;
        return;
    }

    let html = '';
    notifications.slice(0, 5).forEach(notification => {
        const icon = getNotificationIcon(notification.type);
        const time = formatNotificationTime(notification.created_at);
        const unreadClass = notification.is_read ? '' : 'unread';
        
        html += `
            <div class="notification-item ${unreadClass}" onclick="markNotificationRead(${notification.id})">
                <div class="d-flex align-items-start">
                    <div class="notification-icon me-3">
                        <i class="${icon}"></i>
                    </div>
                    <div class="flex-grow-1">
                        <div class="notification-title">${notification.title}</div>
                        <div class="notification-message">${notification.message}</div>
                        <div class="notification-time">${time}</div>
                    </div>
                    ${!notification.is_read ? '<div class="notification-dot"></div>' : ''}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function getNotificationIcon(type) {
    const iconMap = {
        'withdrawal_approved': 'fas fa-check-circle text-success',
        'withdrawal_rejected': 'fas fa-times-circle text-danger',
        'reward_won': 'fas fa-gift text-warning',
        'premium_won': 'fas fa-crown text-primary',
        'referral_joined': 'fas fa-user-plus text-info',
        'task_completed': 'fas fa-check-square text-success',
        'task_added': 'fas fa-plus-circle text-info',
        'daily_bonus': 'fas fa-coins text-warning',
        'level_up': 'fas fa-arrow-up text-success',
        'system_message': 'fas fa-info-circle text-secondary'
    };
    return iconMap[type] || 'fas fa-bell text-secondary';
}

function formatNotificationTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;
    
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (minutes < 1) return 'hozirgina';
    if (minutes < 60) return `${minutes} daqiqa oldin`;
    if (hours < 24) return `${hours} soat oldin`;
    if (days < 7) return `${days} kun oldin`;
    
    return date.toLocaleDateString('uz-UZ');
}

function markNotificationRead(notificationId) {
    fetch(`/notifications/api/${notificationId}/read/`, {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                notificationCount = data.unread_count;
                updateNotificationBadge();
                loadNotifications();
            }
        })
        .catch(e => console.error('Mark notification read error:', e));
}

function markAllNotificationsRead() {
    fetch('/notifications/api/mark-all-read/', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
        }
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                notificationCount = 0;
                updateNotificationBadge();
                loadNotifications();
                showNotification('Barcha bildirishnomalar o\'qilgan deb belgilandi', 'success');
            }
        })
        .catch(e => console.error('Mark all read error:', e));
}

function showNotification(message, type = 'info') {
    if (tg && tg.showAlert) {
        tg.showAlert(message);
    } else {
        // Create custom notification
        const notification = document.createElement('div');
        notification.className = `custom-notification ${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${getNotificationIconForType(type)} me-2"></i>
                <span>${message}</span>
                <button class="btn-close ms-2" onclick="this.parentElement.parentElement.remove()"></button>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }
}

function getNotificationIconForType(type) {
    const iconMap = {
        'success': 'check-circle',
        'error': 'times-circle',
        'warning': 'exclamation-triangle',
        'info': 'info-circle'
    };
    return iconMap[type] || 'bell';
}

// Auto-refresh notifications every 30 seconds
setInterval(loadNotifications, 30000);

// Initialize notifications on page load
document.addEventListener('DOMContentLoaded', function() {
    loadNotifications();
});

// Utility functions
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function loadLeaders() {
    let list = document.getElementById('leaders-list');
    list.innerHTML = `<li class="list-group-item text-center text-secondary" style="background: transparent; border: none;">Yuklanmoqda...</li>`;
    fetch('/webapp/api/leaders/')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                if (data.leaders.length === 0) {
                    list.innerHTML = `<li class="list-group-item text-center text-secondary" style="background: transparent; border: none;">Reyting bo'sh</li>`;
                    return;
                }
                list.innerHTML = '';
                data.leaders.forEach(l => {
                    let medal = l.rank === 1 ? '🥇' : (l.rank === 2 ? '🥈' : (l.rank === 3 ? '🥉' : `#${l.rank}`));
                    list.innerHTML += `
                        <li class="list-group-item d-flex justify-content-between align-items-center" style="background: transparent; border-color: rgba(255,255,255,0.05); color: #fff;">
                            <div class="d-flex align-items-center">
                                <span class="fw-bold me-3 text-center" style="width: 30px; font-size: 1.2rem; display: inline-block; color: var(--accent-color);">${medal}</span>
                                <span class="fw-bold">${l.name}</span>
                            </div>
                            <span class="text-warning fw-bold">${l.coins} Coin</span>
                        </li>
                    `;
                });
            }
        })
        .catch(err => {
            list.innerHTML = `<li class="list-group-item text-center text-danger" style="background: transparent; border: none;">Xatolik yuz berdi</li>`;
        });
}

function loadTasks() {
    let container = document.getElementById('tasks-list-container');
    container.innerHTML = '<div class="text-center text-secondary py-3">Yuklanmoqda...</div>';

    fetch('/webapp/api/tasks/list/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegram_id: currentUserId })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                container.innerHTML = '';
                if (data.tasks.length === 0) {
                    container.innerHTML = '<div class="text-center text-secondary py-3">Hozircha topshiriqlar yo\'q</div>';
                    return;
                }
                data.tasks.forEach(t => {
                    let icon = t.task_type === 'telegram' ? 'fa-telegram text-info' : (t.task_type === 'youtube' ? 'fa-youtube text-danger' : 'fa-link text-primary');
                    
                    let btnText = 'Bajarish';
                    let btnClass = 'btn-warning';
                    let btnDisabled = '';
                    
                    if (t.is_completed) {
                        btnText = 'Bajarilgan';
                        btnClass = 'btn-secondary';
                        btnDisabled = 'pe-none';
                    } else if (!t.can_verify) {
                        btnText = t.verify_message || 'Kutilmoqda';
                        btnClass = 'btn-secondary';
                        btnDisabled = 'pe-none';
                    }
                    
                    let btn = `<button class="btn btn-sm ${btnClass} rounded-pill fw-bold ${btnDisabled}" onclick="verifyTask(${t.id}, '${t.link}', '${t.task_type}', ${t.can_verify})">${btnText}</button>`;

                    let attemptsInfo = '';
                    if (!t.is_completed && t.verification_attempts > 0) {
                        attemptsInfo = `<div class="text-secondary small mt-1">Urinishlar: ${t.verification_attempts}/${t.max_verification_attempts}</div>`;
                    }
                    
                    let screenshotInfo = '';
                    if (t.requires_screenshot) {
                        screenshotInfo = '<div class="text-warning small mt-1"><i class="fa-solid fa-camera"></i> Skrinshot talab qilinadi</div>';
                    }

                    container.innerHTML += `
                    <div class="premium-card p-3 d-flex justify-content-between align-items-start">
                        <div class="flex-grow-1">
                            <div class="d-flex align-items-start">
                                <i class="fa-brands ${icon} fs-4 me-3 mt-1"></i>
                                <div class="flex-grow-1">
                                    <h6 class="mb-1 text-white fw-bold">${t.title}</h6>
                                    <span class="text-warning small fw-bold">+${t.reward_coin} Coin</span>
                                    ${attemptsInfo}
                                    ${screenshotInfo}
                                </div>
                            </div>
                        </div>
                        <div class="ms-3">
                            ${btn}
                        </div>
                    </div>
                `;
                });
            }
        })
        .catch(e => {
            container.innerHTML = '<div class="text-danger text-center py-3">Xatolik yuz berdi</div>';
        });
}

function verifyTask(taskId, link, taskType, canVerify) {
    if (!canVerify) {
        if (tg && tg.showAlert) tg.showAlert("Bu topshiriq hozircha tekshirib bo'lmaydi. Iltimos, kutib turing.");
        else alert("Bu topshiriq hozircha tekshirib bo'lmaydi. Iltimos, kutib turing.");
        return;
    }

    if (tg && tg.openTelegramLink && taskType === 'telegram') {
        try { tg.openTelegramLink(link); } catch (e) { window.open(link, '_blank'); }
    } else if (tg && tg.openLink) {
        try { tg.openLink(link); } catch (e) { window.open(link, '_blank'); }
    } else {
        window.open(link, '_blank');
    }

    setTimeout(() => {
        let confirmBox = confirm("Topshiriqni bajardingizmi? Tasdiqlaymizmi?");
        if (confirmBox) {
            fetch('/webapp/api/tasks/verify/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ telegram_id: currentUserId, task_id: taskId })
            })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        if (tg && tg.showAlert) tg.showAlert(`Tabriklaymiz! +${data.reward} Coin!`);
                        else alert(`Tabriklaymiz! +${data.reward} Coin!`);
                        updateBalance(data.new_balance);
                        loadTasks();
                    } else {
                        if (tg && tg.showAlert) tg.showAlert(data.error || "Tasdiqlanmadi!");
                        else alert(data.error || "Tasdiqlanmadi!");
                        // Reload tasks to show updated attempt count and cooldown
                        loadTasks();
                    }
                })
                .catch(e => {
                    alert("Xatolik yuz berdi");
                });
        }
    }, 4000);
}

function renderRewardsCatalog(rewards) {
    const container = document.getElementById('reward-catalog');
    container.innerHTML = '';
    rewards.forEach(r => {
        let col = document.createElement('div');
        col.className = 'col-6 col-md-4';
        col.innerHTML = `
            <div class="reward-item-card">
                <div style="font-size: 1.5rem">${r.icon || '🎁'}</div>
                <div class="small fw-bold mt-1 text-truncate">${r.name}</div>
                <div class="small text-warning">🪙 ${r.coin_amount}</div>
            </div>
        `;
        container.appendChild(col);
    });
}

function shuffleBoxes(rewards) {
    const copy = [...rewards];
    for (let i = copy.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
}

function renderBoxGrid(rewards) {
    const grid = document.getElementById('box-grid');
    const btn = document.getElementById('btn-spin-action');
    const info = document.getElementById('box-action-info');

    AppState.boxes = shuffleBoxes(rewards);
    AppState.selectedBoxId = null;
    AppState.selectionDisabled = false;

    grid.innerHTML = '';
    if (!AppState.boxes || AppState.boxes.length === 0) {
        grid.innerHTML = '<div class="col-12 text-center text-secondary">Hozircha sovg‘a qutilari mavjud emas.</div>';
        btn.disabled = true;
        return;
    }

    AppState.boxes.forEach((reward, idx) => {
        const card = document.createElement('div');
        card.className = 'col';
        card.innerHTML = `
            <div class="box-card p-3 text-center rounded shadow-sm" data-reward-id="${reward.id}" onclick="selectBox(${reward.id}, this)">
                <div class="box-emoji" style="font-size:2.2rem;">📦</div>
                <div class="fw-bold mt-2">Quti #${idx + 1}</div>
                <div class="text-secondary small">${reward.name}</div>
                <div class="text-warning small">%${reward.probability_weight || reward.weight || 1} imkoniyat</div>
            </div>
        `;
        grid.appendChild(card);
    });

    btn.disabled = true;
    btn.innerText = 'Quti tanlang';
    btn.onclick = openSelectedBox;
    info.innerText = 'Bir quti tanlang, keyin “Quti ochish” tugmasini bosing.';
}

function selectBox(rewardId, element) {
    if (AppState.selectionDisabled) return;

    document.querySelectorAll('#box-grid .box-card').forEach(card => {
        card.classList.remove('active');
    });

    element.classList.add('active');
    AppState.selectedBoxId = rewardId;

    const btn = document.getElementById('btn-spin-action');
    btn.disabled = false;
    btn.innerText = 'Qutini Ochish';

    const info = document.getElementById('box-action-info');
    info.innerText = `Tanlangan quti: ${AppState.boxes.find(r => r.id === rewardId)?.name || ''} (yutuq foizi oshkora emas).`;
}

function openSelectedBox() {
    if (AppState.selectionDisabled) return;
    if (!AppState.selectedBoxId) {
        if (tg && tg.showAlert) tg.showAlert('Iltimos, bir quti tanlang.');
        else alert('Iltimos, bir quti tanlang.');
        return;
    }

    const cost = AppState.spinCost || 50;
    if (AppState.coinBalance < cost) {
        if (tg && tg.showAlert) tg.showAlert('Coin yetarli emas. Qutini ochish uchun 50 Coin kerak.');
        else alert('Coin yetarli emas. Qutini ochish uchun 50 Coin kerak.');
        return;
    }

    AppState.selectionDisabled = true;
    const btn = document.getElementById('btn-spin-action');
    btn.disabled = true;
    btn.innerText = 'Ochilmoqda...';

    fetch('/webapp/api/spin/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            telegram_id: currentUserId,
            board_id: currentBoardId,
            selected_reward_id: AppState.selectedBoxId,
            paid_open: true
        })
    })
        .then(r => r.json())
        .then(data => {
            AppState.selectionDisabled = false;
            if (data.success) {
                updateBalance(data.new_balance);
                const wasSelected = data.was_selected_box ? 'Tanlangan quti yutdi!' : 'Tasodifiy quti ochildi.';
                const chanceText = data.selected_box_chance ? `(tanlangan likelihood: ${data.selected_box_chance}%)` : '';
                const msg = `🎉 ${wasSelected} ${chanceText} 
Yutuq: ${data.reward_name} (+${data.reward_amount} Coin)`;
                if (tg && tg.showAlert) tg.showAlert(msg);
                else alert(msg);

                // Yangilash: har tanlovdan keyin qutilarni qayta tashkil qilish
                renderBoxGrid(AppState.rewards);
                updateSpinButtonUI();
            } else {
                if (tg && tg.showAlert) tg.showAlert(data.error || 'Xatolik');
                else alert(data.error || 'Xatolik');
                AppState.selectionDisabled = false;
                btn.innerText = 'Qutini Ochish';
            }
        })
        .catch(err => {
            console.error(err);
            AppState.selectionDisabled = false;
            btn.disabled = false;
            btn.innerText = 'Qutini Ochish';
            alert('Aloqa xatosi yuz berdi. Keyinroq qaytadan urinib ko‘ring.');
        });
}

function copyRef() {
    let copyText = document.getElementById("ref-link");
    copyText.select();
    document.execCommand("copy");
    if (tg && tg.showAlert) tg.showAlert("Nusxa olindi!");
    else alert("Nusxa olindi!");
}

/* GAMIFICATION: Button UI, Timer and Coin Rain */

function updateSpinButtonUI() {
    let btn = document.getElementById('btn-spin-action');
    let timerDisplay = document.getElementById('timer-countdown');
    let nextSpinText = document.getElementById('next-spin-timer');
    let cost = AppState.spinCost || 50;

    if (AppState.freeSpinsLeft > 0) {
        btn.innerHTML = `<div>AYLANTIRISH</div><div class="btn-gold-subtext">Bepul: ${AppState.freeSpinsLeft} ta qoldi</div>`;
        btn.disabled = false;
    } else {
        btn.innerHTML = `<div>AYLANTIRISH</div><div class="btn-gold-subtext">${cost} Coin evaziga</div>`;
        btn.disabled = AppState.coinBalance < cost;
    }

    let remaining = AppState.secondsUntilNextDay;
    if (remaining < 0) remaining = 0;
    let hrs = Math.floor(remaining / 3600);
    let mins = Math.floor((remaining % 3600) / 60);
    let secs = Math.floor(remaining % 60);
    let formatted = `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

    if (timerDisplay) {
        timerDisplay.innerText = formatted;
    }

    const timerDisplay2 = document.getElementById('timer-countdown-display');
    if (timerDisplay2) {
        timerDisplay2.innerText = `Keyingi bepul aylantirishgacha: ${formatted}`;
    }
    
    if (nextSpinText) {
        if (AppState.freeSpinsLeft > 0) {
            nextSpinText.innerText = `Bepul aylantirish: ${AppState.freeSpinsLeft} ta qoldi`;
        } else {
            nextSpinText.innerText = `Keyingi bepul aylantirishgacha: ${formatted}`;
        }
    }
}

function startCountdownTimer() {
    if (AppState.timerInterval) clearInterval(AppState.timerInterval);

    // Keep a moving target timestamp for smooth countdown, not just decrement by 1.
    let targetTimestamp = Date.now() + ((AppState.secondsUntilNextDay > 0 ? AppState.secondsUntilNextDay : 24 * 3600) * 1000);

    function updateTimer() {
        let remainingMs = targetTimestamp - Date.now();
        if (remainingMs <= 0) {
            AppState.freeSpinsLeft = 2;
            targetTimestamp = Date.now() + 24 * 3600 * 1000;
            remainingMs = targetTimestamp - Date.now();
        }

        AppState.secondsUntilNextDay = Math.max(0, Math.ceil(remainingMs / 1000));

        let hrs = Math.floor(AppState.secondsUntilNextDay / 3600);
        let mins = Math.floor((AppState.secondsUntilNextDay % 3600) / 60);
        let secs = Math.floor(AppState.secondsUntilNextDay % 60);

        const formatted = `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

        const timerDisplay = document.getElementById('timer-countdown');
        if (timerDisplay) {
            timerDisplay.innerText = formatted;
        }

        updateSpinButtonUI();
    }

    updateTimer();
    AppState.timerInterval = setInterval(updateTimer, 1000);
}

function startCoinRain() {
    const container = document.getElementById('coin-rain-container');
    if (!container) return;

    setInterval(() => {
        // Only spawn 1 coin every 800ms to keep it elegant and not messy
        const drop = document.createElement('div');
        drop.classList.add('coin-drop');
        drop.innerText = '🪙';
        drop.style.left = Math.random() * 100 + 'vw';
        drop.style.animationDuration = (Math.random() * 3 + 4) + 's'; // 4-7s fall
        container.appendChild(drop);

        setTimeout(() => {
            drop.remove();
        }, 7000);
    }, 800);
}

function submitWithdraw(event) {
    event.preventDefault();
    let btn = event.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.innerText = "Yuborilmoqda...";

    let cardType = document.getElementById('cardType').value;
    let cardNumber = document.getElementById('cardNumber').value;
    let cardHolder = document.getElementById('cardHolder').value;

    fetch('/webapp/api/withdraw/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            telegram_id: currentUserId,
            card_label: cardType,
            card_number: cardNumber,
            holder_name: cardHolder
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                updateBalance(data.new_balance);
                if (tg && tg.showAlert) tg.showAlert("So'rov yuborildi! Kutilmoqda...");
                else alert("So'rov yuborildi! Kutilmoqda...");
                navigateTo('wallet', document.querySelector('[data-target="wallet"]'));
            } else {
                if (tg && tg.showAlert) tg.showAlert("Xatolik: " + (data.error || "Noma'lum"));
                else alert("Xatolik: " + (data.error || "Noma'lum"));
            }
        })
        .catch(e => {
            alert("Xatolik yuz berdi");
        })
        .finally(() => {
            btn.disabled = false;
            btn.innerText = "Yuborish";
        });
}
