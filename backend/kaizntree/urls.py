from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.users.urls import auth_urlpatterns, mgmt_urlpatterns


def health(_request):
    """Lightweight liveness probe — no DB query, instant 200."""
    return JsonResponse({"status": "ok"})


def api_root(_request):
    """Minimal root view so GET / returns JSON instead of a Django 404 page."""
    return JsonResponse({
        "service": "kaizntree-api",
        "docs": "/api/schema/swagger-ui/",
        "health": "/health/",
    })


urlpatterns = [
    path("", api_root),
    # health — both with and without trailing slash so Railway's healthcheck
    # probe (/health, no redirect) and named URL reversals (/health/) both work.
    path("health", health),
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include((auth_urlpatterns, "auth"))),
    path("api/v1/", include((mgmt_urlpatterns, "mgmt"))),
    path("api/v1/", include("apps.inventory.urls")),
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.financials.urls")),
    path("api/v1/", include("apps.suppliers.urls")),
    path("api/v1/", include("apps.forecasting.urls")),
    path("api/v1/", include("apps.ai_workflows.urls")),
    path("api/v1/", include("apps.integrations.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
