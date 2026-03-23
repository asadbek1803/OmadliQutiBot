import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY', default='django-insecure-xyz')
DEBUG = env('DEBUG', default=True)
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['*'])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Core app (for management commands)
    'core',
    # Custom apps
    'accounts.apps.AccountsConfig',
    'wallet.apps.WalletConfig',
    'rewards.apps.RewardsConfig',
    'spins.apps.SpinsConfig',
    'referrals.apps.ReferralsConfig',
    'withdrawals.apps.WithdrawalsConfig',
    'bot.apps.BotConfig',
    'webapp.apps.WebappConfig',
    'tasks',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'core.middleware.APIRequestMiddleware',
    'core.middleware.SQLiteOptimizationMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'
AUTH_USER_MODEL = 'accounts.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# SQLite Optimization Settings
if 'sqlite' in DATABASES['default']['ENGINE']:
    DATABASES['default']['OPTIONS'] = {
        'timeout': 20,  # 20 seconds timeout
        'check_same_thread': False,
    }

BOT_TOKEN = env('BOT_TOKEN', default='')
WEBHOOK_HOST = env('WEBHOOK_HOST', default='')
WEBHOOK_PATH = env('WEBHOOK_PATH', default='/bot/webhook/')
WEBAPP_URL = env('WEBAPP_URL', default='')

CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok.app',
    'https://*.ngrok.io'
]
if WEBHOOK_HOST and WEBHOOK_HOST.startswith('http'):
    CSRF_TRUSTED_ORIGINS.append(WEBHOOK_HOST)

UNFOLD = {
    "SITE_TITLE": "OmadliQuti Admin",
    "SITE_HEADER": "OmadliQuti Boshqaruv",
    "SITE_URL": "/",
    "DASHBOARD_CALLBACK": "webapp.dashboard.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "250 245 255",
            "100": "243 232 255",
            "200": "233 213 255",
            "300": "216 180 254",
            "400": "192 132 252",
            "500": "168 85 247",
            "600": "147 51 234",
            "700": "126 34 206",
            "800": "107 33 168",
            "900": "88 28 135",
        },
    },
}
