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

# Railway automatically injects RAILWAY_PUBLIC_DOMAIN — add it to ALLOWED_HOSTS
# so Django doesn't reject requests before they reach the app.
_railway_domain = _os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
if _railway_domain:
    ALLOWED_HOSTS.append(_railway_domain)  # noqa: F405
