import os as _os

from .base import *  # noqa: F401, F403

DEBUG = False

SIMPLE_JWT["AUTH_COOKIE_SECURE"] = True  # noqa: F405
# SameSite=None is required when the frontend (Vercel) and backend (Railway)
# are on different domains — browsers only send cross-origin cookies when
# SameSite=None and Secure=True are both set.
SIMPLE_JWT["AUTH_COOKIE_SAMESITE"] = "None"  # noqa: F405

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Explicitly reassign ALLOWED_HOSTS for production.
# Using .append() on the list imported via `*` is unreliable — a full
# reassignment is guaranteed to take effect.
#
#  - ".railway.app"    — wildcard: matches healthcheck.railway.app AND the
#                        public *.railway.app domains Railway assigns
#  - ".up.railway.app" — Railway's newer public URL pattern (*.up.railway.app)
#  - RAILWAY_PUBLIC_DOMAIN is added explicitly in case it's a custom domain
#    that doesn't end in .railway.app
_railway_domain = _os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
ALLOWED_HOSTS = [  # noqa: F405
    "localhost",
    "127.0.0.1",
    "healthcheck.railway.app",
    ".railway.app",
    ".up.railway.app",
]
if _railway_domain:
    ALLOWED_HOSTS.append(_railway_domain)
