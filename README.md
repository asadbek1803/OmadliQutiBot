# OmadliQuti Gamified Reward Platform

A complete Django + Aiogram 3 based platform including a Telegram Bot, a Telegram Mini App, and a sophisticated Django Admin Panel.

## Project Features
- **Telegram Bot Integration:** Built with Aiogram 3 and running via Webhooks entirely within Django.
- **Telegram Web App:** Beautiful frontend using HTML5 Canvas for the dynamic spin wheel, Bootstrap 5, and custom dark mode CSS.
- **Dynamic Reward System:** Admin can add 8, 9, 10 or however many rewards they want. Both the backend and the UI wheel mathematically adapt to the amount of rewards.
- **Economy & Wallets:** Bulletproof core ledger system logging all transactions. Prevent race conditions with atomic requests.
- **Referrals:** Referral tracking, bonus assignment logic with abuse protection basics built-in.
- **Reward Requests:** Manual cash-out workflow handled securely without full card numbers using a reserve-release system.

## Setup Instructions

```bash
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# 2. Install requirements
pip install -r requirements.txt

# 3. Create .env file based on .env.example
# Put your bot token and your ngrok url (for local testing) in .env

# 4. Run migrations
python manage.py makemigrations accounts wallet rewards spins referrals withdrawals bot webapp
python manage.py migrate

# 5. Setup Demo Rewards & Create Admin
python manage.py create_demo_rewards

# 6. Run the server
python manage.py runserver
```

### To bind Telegram Webhook (Local Testing)
If you're using Ngrok, make sure to update your `WEBHOOK_HOST` in your `.env` to your Ngrok HTTPS URL. Then run:
```bash
python manage.py sync_webhook
```
Your bot is now live!
