import os as _os

from .base import *  # noqa: F401, F403

DEBUG = False

SIMPLE_JWT["AUTH_COOKIE_SECURE"] = True  # noqa: F405
# SameSite=None is required when the frontend (Vercel) and backend (Railway)
# are on different domains. The cookie is a secondary/best-effort mechanism;
# the primary session-persistence path uses the refresh token in the response
# body stored in sessionStorage (see authRefresh.ts). Browsers that block
# third-party cookies (Brave Shields, Safari ITP) fall back to that path.
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

# ── CORS ─────────────────────────────────────────────────────────────────────
import urllib.parse as _up  # noqa: E402


def _parse_cors_origins(raw: str) -> list:
    """
    Parse a comma-separated CORS origins string defensively:
      - Strips path components  (e.g. /login, /register)
      - Defaults scheme to https when none is given
      - Deduplicates, preserves order
    This means typos like http://example.vercel.app (should be https) or
    https://example.vercel.app/login are auto-corrected.
    """
    results = []
    for entry in raw.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            p = _up.urlparse(entry)
            scheme = p.scheme or "https"
            netloc = p.netloc or p.path  # handle bare "example.com" without scheme
            if netloc:
                results.append(f"{scheme}://{netloc}")
        except Exception:
            pass
    return list(dict.fromkeys(results))  # deduplicate, preserve insertion order


# Reads CORS_ALLOWED_ORIGINS env var first; falls back to FRONTEND_URL.
# Set CORS_ALLOWED_ORIGINS=https://your-app.vercel.app in Railway Variables.
_cors_raw = (
    _os.environ.get("CORS_ALLOWED_ORIGINS", "")
    or _os.environ.get("FRONTEND_URL", "")
)
CORS_ALLOWED_ORIGINS = _parse_cors_origins(_cors_raw)  # noqa: F405
