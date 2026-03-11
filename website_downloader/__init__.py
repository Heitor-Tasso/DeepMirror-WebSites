"""
DeepMirror-WebSites - Configurações e Constantes
"""
import os

# Timeouts
BROWSER_TIMEOUT = int(os.getenv('DM_BROWSER_TIMEOUT_MS', '60000'))  # 60s para page.goto()
RESOURCE_TIMEOUT = int(os.getenv('DM_RESOURCE_TIMEOUT_S', '15'))  # 15s por recurso individual
NETWORK_IDLE_TIMEOUT = int(os.getenv('DM_NETWORK_IDLE_TIMEOUT_MS', '30000'))  # 30s esperando rede
NETWORK_IDLE_SILENCE = int(os.getenv('DM_NETWORK_IDLE_SILENCE_MS', '10000'))  # 10s de silêncio
CSS_INJECTION_TIMEOUT = int(os.getenv('DM_CSS_INJECTION_TIMEOUT_MS', '10000'))  # 10s para CSS-in-JS
EXTRA_WAIT_MIN = 5000  # Mínimo 5s após carregamento
EXTRA_WAIT_MAX = 8000  # Máximo 8s após carregamento
INTERACTION_WAIT = 2000  # 2s entre interações simuladas

# Limites
MAX_RESOURCE_SIZE = 100 * 1024 * 1024  # 100MB por recurso
MAX_SCROLL_ITERATIONS = 20  # Máximo de iterações de scroll

# Retry
MAX_RETRIES = 2  # Número de tentativas para downloads
RETRY_BACKOFF = 2  # Multiplicador de delay entre tentativas

# Domínios a ignorar (tracking, analytics, ads)
SKIP_DOMAINS = [
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
    'outseta.com',  # Auth/CRM scripts — concatenated bundle segments that SyntaxError in isolation
]

# Scripts a remover (tracking, analytics)
TRACKING_SCRIPTS = [
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
]

# Smooth scroll libraries a remover
SMOOTH_SCROLL_LIBS = [
    'lenis',
    'locomotive',
    'smooth-scroll',
]

# Browser args
BROWSER_ARGS = [
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
]

# User Agent
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
