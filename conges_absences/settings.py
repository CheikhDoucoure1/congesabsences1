import os
from pathlib import Path
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Environment variables -------------------------------------------------
# Load a local .env file if present (no external dependency required).
# Real deployments should instead set these as actual environment variables.
_env_path = BASE_DIR / '.env'
if _env_path.exists():
    for _line in _env_path.read_text(encoding='utf-8').splitlines():
        _line = _line.strip()
        if not _line or _line.startswith('#') or '=' not in _line:
            continue
        _key, _, _value = _line.partition('=')
        os.environ.setdefault(_key.strip(), _value.strip().strip('"').strip("'"))


def _env_bool(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('1', 'true', 'yes', 'on')


# DEBUG defaults to False (secure by default). Set DJANGO_DEBUG=True in a
# local .env file (see .env.example) while developing to get full error
# pages. NEVER enable it on a server reachable by anyone but you.
DEBUG = _env_bool('DJANGO_DEBUG', False)

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        # Auto-generated per run so local development still works without a
        # .env file. Sessions/CSRF tokens won't survive a server restart.
        SECRET_KEY = get_random_secret_key()
    else:
        raise RuntimeError(
            "DJANGO_SECRET_KEY is not set. Define it in the environment "
            "(or in a .env file next to manage.py) before running with "
            "DEBUG=False."
        )

_allowed_hosts = os.environ.get(
    'DJANGO_ALLOWED_HOSTS',
    '127.0.0.1,localhost,conges-absences.petrosen.sn',
)
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',') if h.strip()]

_csrf_trusted_origins = os.environ.get(
    'DJANGO_CSRF_TRUSTED_ORIGINS',
    'https://conges-absences.petrosen.sn',
)
CSRF_TRUSTED_ORIGINS = [
    origin.strip() for origin in _csrf_trusted_origins.split(',') if origin.strip()
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'conges',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'conges_absences.urls'

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

WSGI_APPLICATION = 'conges_absences.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'conges_absences'),
        'USER': os.environ.get('DB_USER', 'conges_absences'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
    }
}

# File-based, not Django's default in-memory cache: the login throttle
# (see conges.views.connexion) reads/writes this cache, and an in-memory
# one is private to a single process — with Gunicorn running several
# worker processes, each would keep its own separate attempt counter,
# so the throttle would trigger inconsistently depending on which worker
# handles a given request. A shared file store fixes that with no extra
# service (Redis/Memcached) to install or run.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': str(BASE_DIR / 'django_cache'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Dakar'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Sensitive uploads (leave justificatifs) are NOT served from here — see
# conges.views.voir_justificatif and conges_absences/urls.py, which only
# expose the public 'avatars/' subfolder through Django's static() helper
# (itself a no-op unless DEBUG=True; use a real web server / storage
# backend with its own access control in production).

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'conges.Employe'

LOGIN_URL = '/connexion/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/connexion/'

# Base URL used to build absolute links inside notification emails (a
# relative /approbations/12/ means nothing in an inbox). No trailing slash.
SITE_URL = os.environ.get('DJANGO_SITE_URL', 'http://127.0.0.1:8001').rstrip('/')

# --- Email notifications -----------------------------------------------------
# Disabled by default — the app works fine without it (in-app notifications
# still work regardless). Set DJANGO_EMAIL_ENABLED=True once real SMTP
# credentials are filled in in .env. See conges/email_utils.py for what
# actually triggers an email (a deliberately small subset of all in-app
# notifications — only "needs your action" and "final decision on your own
# request", to avoid flooding inboxes with every intermediate step).
EMAIL_ENABLED = _env_bool('DJANGO_EMAIL_ENABLED', False)

if EMAIL_ENABLED:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    # Defaults match Office 365 / Exchange Online. That tenant needs
    # "Authenticated SMTP" explicitly enabled for the sending mailbox
    # (Microsoft disables it by default) — ask IT, or Exchange admin center
    # → the mailbox → Manage email apps → Authenticated SMTP.
    EMAIL_HOST = os.environ.get('DJANGO_EMAIL_HOST', 'smtp.office365.com')
    EMAIL_PORT = int(os.environ.get('DJANGO_EMAIL_PORT', '587'))
    EMAIL_USE_TLS = _env_bool('DJANGO_EMAIL_USE_TLS', True)
    EMAIL_HOST_USER = os.environ.get('DJANGO_EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('DJANGO_EMAIL_HOST_PASSWORD', '')
    if not EMAIL_HOST_USER or not EMAIL_HOST_PASSWORD:
        raise RuntimeError(
            "DJANGO_EMAIL_ENABLED is True but DJANGO_EMAIL_HOST_USER/"
            "DJANGO_EMAIL_HOST_PASSWORD are not set. Fill them in in .env."
        )
    DEFAULT_FROM_EMAIL = os.environ.get('DJANGO_EMAIL_FROM') or EMAIL_HOST_USER
elif DEBUG:
    # Prints emails to the console instead of sending them — lets you see
    # what would go out while developing, with no SMTP setup needed.
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    # Silently discards — safe no-op for a production instance that hasn't
    # been given SMTP credentials yet.
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# --- Hardening --------------------------------------------------------------
# Reasonable per-request upload ceiling (also enforced per-field in
# conges/validators.py for avatars/justificatifs specifically).
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # the CSRF cookie must stay readable by the JS that sends it
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True

# HTTPS-only cookie/redirect settings — only turned on when DEBUG is off,
# so local http://127.0.0.1 development keeps working. Set
# DJANGO_BEHIND_HTTPS=True once the app is actually served over HTTPS.
_behind_https = _env_bool('DJANGO_BEHIND_HTTPS', not DEBUG)
SESSION_COOKIE_SECURE = _behind_https
CSRF_COOKIE_SECURE = _behind_https
SECURE_SSL_REDIRECT = _behind_https
if _behind_https:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# --- LDAP / Active Directory authentication ---------------------------------
# Disabled by default so the app keeps working with local-only accounts
# (including this instance's demo logins) if .env has no LDAP settings yet.
# Set DJANGO_LDAP_ENABLED=True once DJANGO_LDAP_BIND_PASSWORD (and the rest)
# are filled in in .env — see .env.example for every variable.
AUTH_LDAP_ENABLED = _env_bool('DJANGO_LDAP_ENABLED', False)

if AUTH_LDAP_ENABLED:
    import ldap
    from django_auth_ldap.config import LDAPSearch

    # Plain LDAP on 389 — this DC doesn't have LDAPS (636) available/open.
    # Credentials travel unencrypted on this connection unless
    # DJANGO_LDAP_START_TLS=True and the DC actually supports STARTTLS on
    # 389 (worth asking IT to check — it upgrades this same connection to
    # TLS without needing a separate 636 listener). Until then this is a
    # known, accepted risk on the internal network this runs on.
    AUTH_LDAP_SERVER_URI = os.environ.get(
        'DJANGO_LDAP_SERVER_URI', 'ldap://PETROSEN-SRV-DC1.PETROSEN.SN:389'
    )
    # Use the UPN form (user@domain), not DOMAIN\user — the backslash form
    # gets silently corrupted when systemd's EnvironmentFile= loads .env
    # (it applies C-style backslash escaping, so \a becomes a control
    # character instead of staying literal). Confirmed the hard way: this
    # cost real debugging time before someone thought to check the actual
    # process environment (/proc/<pid>/environ) rather than the .env file
    # or a manually-run shell, which don't go through systemd's parser and
    # so don't show the corruption.
    AUTH_LDAP_BIND_DN = os.environ.get('DJANGO_LDAP_BIND_DN', 'adminclb@petrosen.sn')
    AUTH_LDAP_BIND_PASSWORD = os.environ.get('DJANGO_LDAP_BIND_PASSWORD', '')
    if not AUTH_LDAP_BIND_PASSWORD:
        raise RuntimeError(
            "DJANGO_LDAP_ENABLED is True but DJANGO_LDAP_BIND_PASSWORD is not "
            "set. Fill it in in .env (never commit it)."
        )

    # Exposed as a real setting (not just a local var feeding
    # AUTH_LDAP_USER_SEARCH below) so other code — conges/management/
    # commands/sync_ldap_employes.py — can reuse the same base DN for its
    # own standalone directory search.
    AUTH_LDAP_BASE_DN = os.environ.get('DJANGO_LDAP_BASE_DN', 'DC=PETROSEN,DC=SN')
    _ldap_base_dn = AUTH_LDAP_BASE_DN
    # Subtree search from the domain root: the employees are spread across
    # several OUs under this base, so this recurses into all of them rather
    # than requiring one fixed OU. Matches on either the AD login
    # (sAMAccountName) or the UPN (userPrincipalName, the "user@domain"
    # form AD itself uses for login) — covers both what IT expects and what
    # the app's own login form asks for (an email-shaped identifier), since
    # UPN commonly equals the mail address without depending on it being
    # in sync with the `mail` attribute specifically.
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        _ldap_base_dn, ldap.SCOPE_SUBTREE,
        '(|(sAMAccountName=%(user)s)(userPrincipalName=%(user)s)(mail=%(user)s))',
    )

    # AD attributes -> Employe fields, refreshed on every successful login
    # (name changes in AD are picked up automatically). Role, department,
    # manager, matricule etc. are NOT sourced from AD — a newly auto-created
    # account gets the model's defaults (role='employe') and an RH/admin
    # assigns the rest afterwards from /administration/.
    AUTH_LDAP_USER_ATTR_MAP = {
        'first_name': 'givenName',
        'last_name': 'sn',
        'email': 'mail',
    }
    AUTH_LDAP_ALWAYS_UPDATE_USER = True

    # Opt-in: upgrades the plain-389 connection above to TLS via the
    # STARTTLS extension, if the DC supports it — encrypts credentials
    # without needing a separate LDAPS/636 listener. Off by default since
    # it hasn't been confirmed available; test it in a maintenance window
    # before flipping it on (a DC that doesn't support it will just make
    # every login fail again).
    AUTH_LDAP_START_TLS = _env_bool('DJANGO_LDAP_START_TLS', False)

    AUTH_LDAP_CONNECTION_OPTIONS = {
        ldap.OPT_REFERRALS: 0,        # required against Active Directory
        ldap.OPT_NETWORK_TIMEOUT: 10,  # seconds — fail fast if the DC is unreachable
        ldap.OPT_TIMEOUT: 10,
    }

    # If the DC's TLS certificate is issued by an internal/enterprise CA not
    # in the system trust store, point this at that CA's PEM file instead of
    # disabling validation (never set OPT_X_TLS_REQUIRE_CERT to "never").
    _ldap_ca_cert = os.environ.get('DJANGO_LDAP_CA_CERT_FILE')
    if _ldap_ca_cert:
        AUTH_LDAP_CONNECTION_OPTIONS[ldap.OPT_X_TLS_CACERTFILE] = _ldap_ca_cert
        AUTH_LDAP_CONNECTION_OPTIONS[ldap.OPT_X_TLS_NEWCTX] = 0

    AUTHENTICATION_BACKENDS = [
        'django_auth_ldap.backend.LDAPBackend',
        'django.contrib.auth.backends.ModelBackend',
    ]

    # Set DJANGO_LDAP_DEBUG=True temporarily to see exactly what
    # django-auth-ldap is doing on each login attempt (connect, search,
    # bind, attribute population) in the server's own stdout/journalctl —
    # invaluable when a login silently fails with no other clue why.
    # Turn it back off once diagnosed: at DEBUG level this can log bind
    # attempts, which you don't want piling up in production logs forever.
    if _env_bool('DJANGO_LDAP_DEBUG', False):
        LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'handlers': {'console': {'class': 'logging.StreamHandler'}},
            'loggers': {
                'django_auth_ldap': {'handlers': ['console'], 'level': 'DEBUG'},
            },
        }
else:
    AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend']
