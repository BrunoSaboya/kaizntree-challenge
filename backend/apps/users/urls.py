from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AdminUserViewSet,
    LoginView,
    LogoutView,
    MeView,
    OrgMemberViewSet,
    OrgViewSet,
    RefreshView,
    RegisterView,
)

# Mounted at /api/v1/auth/
auth_urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("refresh/", RefreshView.as_view(), name="auth-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
]

# Mounted at /api/v1/
router = DefaultRouter()
router.register("users", AdminUserViewSet, basename="admin-users")
router.register("organizations", OrgViewSet, basename="organizations")
router.register("org/members", OrgMemberViewSet, basename="org-members")

mgmt_urlpatterns = router.urls
