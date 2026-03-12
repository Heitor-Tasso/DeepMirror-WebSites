"""
DeepMirror-WebSites - Configurações e Constantes
"""
import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / '.env')


def _get_str(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


def _get_int(name, default):
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def _get_float(name, default):
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_bool(name, default):
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _get_csv(name, default):
    value = os.getenv(name)
    if value is None or not value.strip():
        return list(default)
    return [item.strip() for item in value.split(',') if item.strip()]


def _get_optional_float(name):
    value = os.getenv(name, '').strip()
    if not value:
        return None, None
    try:
        return float(value), None
    except ValueError:
        return None, value


APP_HOST = _get_str('DM_APP_HOST', '0.0.0.0')
APP_PORT = _get_int('DM_APP_PORT', 5001)
APP_DEBUG = _get_bool('DM_APP_DEBUG', True)
APP_THREADED = _get_bool('DM_APP_THREADED', True)
APP_SECRET_KEY = _get_str('DM_APP_SECRET_KEY', 'deepmirror-local-dev-secret')
LOGIN_USERNAME = _get_str('DM_LOGIN_USERNAME', 'asimov')
LOGIN_PASSWORD = _get_str('DM_LOGIN_PASSWORD', 'aidesign')
DOWNLOAD_FOLDER = _get_str('DM_DOWNLOAD_FOLDER', 'downloads')
STARTUP_CLEAN_DOWNLOADS = _get_bool('DM_STARTUP_CLEAN_DOWNLOADS', True)
SESSION_CLEANUP_INTERVAL_S = _get_int('DM_SESSION_CLEANUP_INTERVAL_S', 300)
SESSION_MAX_AGE_S = _get_int('DM_SESSION_MAX_AGE_S', 1800)
SSE_MESSAGE_TIMEOUT_S = _get_int('DM_SSE_MESSAGE_TIMEOUT_S', 60)
DOWNLOAD_CLEANUP_DELAY_S = _get_float('DM_DOWNLOAD_CLEANUP_DELAY_S', 1.0)

BROWSER_TIMEOUT = _get_int('DM_BROWSER_TIMEOUT_MS', 60000)
RESOURCE_TIMEOUT = _get_int('DM_RESOURCE_TIMEOUT_S', 15)
NETWORK_IDLE_TIMEOUT = _get_int('DM_NETWORK_IDLE_TIMEOUT_MS', 30000)
NETWORK_IDLE_SILENCE = _get_int('DM_NETWORK_IDLE_SILENCE_MS', 10000)
CSS_INJECTION_TIMEOUT = _get_int('DM_CSS_INJECTION_TIMEOUT_MS', 10000)
EXTRA_WAIT_MIN = _get_int('DM_EXTRA_WAIT_MIN_MS', 5000)
EXTRA_WAIT_MAX = _get_int('DM_EXTRA_WAIT_MAX_MS', 8000)
INTERACTION_WAIT = _get_int('DM_INTERACTION_WAIT_MS', 2000)
MAX_RESOURCE_SIZE = int(_get_float('DM_MAX_RESOURCE_SIZE_MB', 100.0) * 1024 * 1024)
MAX_SCROLL_ITERATIONS = _get_int('DM_MAX_SCROLL_ITERATIONS', 20)
MAX_RETRIES = _get_int('DM_MAX_RETRIES', 2)
RETRY_BACKOFF = _get_float('DM_RETRY_BACKOFF', 2.0)
RESOURCE_MAP_INLINE_LIMIT = _get_int('DM_RESOURCE_MAP_INLINE_LIMIT', 500)
CLEAN_MODE = _get_str('DM_CLEAN_MODE', 'full').lower()
CLEAN_MAX_SIZE_MB, CLEAN_MAX_SIZE_MB_INVALID = _get_optional_float('DM_CLEAN_MAX_SIZE_MB')

DEFAULT_SKIP_DOMAINS = (
    'google-analytics.com',
    'googletagmanager.com',
    'doubleclick.net',
    'facebook.com',
    'facebook.net',
    'connect.facebook.net',
    'analytics.google.com',
    'stats.g.doubleclick.net',
    'pagead2.googlesyndication.com',
    'adservice.google.com',
    'googlesyndication.com',
    'googleadservices.com',
    'hotjar.com',
    'clarity.ms',
    'segment.com',
    'segment.io',
    'mixpanel.com',
    'amplitude.com',
    'intercom.io',
    'drift.com',
    'crisp.chat',
    'zendesk.com',
    'tawk.to',
    'livechatinc.com',
    'freshchat.com',
    'outseta.com',
)
SKIP_DOMAINS = _get_csv('DM_SKIP_DOMAINS', DEFAULT_SKIP_DOMAINS)

DEFAULT_TRACKING_SCRIPTS = (
    'google-analytics',
    'googletagmanager',
    'gtm.js',
    'gtag',
    'analytics.js',
    'facebook.net',
    'fbevents.js',
    'pixel',
    'hotjar',
    'clarity',
    'segment',
    'mixpanel',
    'amplitude',
    'intercom',
    'drift',
    'crisp',
    'zendesk',
    'tawk',
    'livechat',
    'freshchat',
    'klaviyo',
    'cookiebot',
    'consentcdn',
    'monorail',
    'web-pixels',
    'webpixels',
)
TRACKING_SCRIPTS = _get_csv('DM_TRACKING_SCRIPTS', DEFAULT_TRACKING_SCRIPTS)

DEFAULT_SMOOTH_SCROLL_LIBS = (
    'lenis',
    'locomotive',
    'smooth-scroll',
)
SMOOTH_SCROLL_LIBS = _get_csv('DM_SMOOTH_SCROLL_LIBS', DEFAULT_SMOOTH_SCROLL_LIBS)

DEFAULT_BROWSER_ARGS = (
    '--disable-dev-shm-usage',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-gpu',
    '--disable-extensions',
    '--disable-background-networking',
    '--disable-default-apps',
    '--disable-sync',
    '--disable-translate',
    '--metrics-recording-only',
    '--mute-audio',
    '--no-first-run',
    '--safebrowsing-disable-auto-update',
)
BROWSER_ARGS = _get_csv('DM_BROWSER_ARGS', DEFAULT_BROWSER_ARGS)

USER_AGENT = _get_str(
    'DM_USER_AGENT',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
)
