from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .models import Organization
from .permissions import IsAdmin, IsOwner
from .serializers import (
    CustomTokenObtainPairSerializer,
    MeUpdateSerializer,
    MemberCreateSerializer,
    MemberUpdateSerializer,
    OrganizationSerializer,
    ProvisionOrgSerializer,
    RegisterSerializer,
    UserCreateSerializer,
    UserDetailSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


def _set_refresh_cookie(response, refresh_token: str) -> None:
    jwt_settings = settings.SIMPLE_JWT
    response.set_cookie(
        key=jwt_settings["AUTH_COOKIE"],
        value=refresh_token,
        httponly=jwt_settings["AUTH_COOKIE_HTTP_ONLY"],
        samesite=jwt_settings["AUTH_COOKIE_SAMESITE"],
        secure=jwt_settings["AUTH_COOKIE_SECURE"],
        max_age=int(jwt_settings["REFRESH_TOKEN_LIFETIME"].total_seconds()),
    )


class RegisterView(generics.CreateAPIView):
    """Admin-only user creation (replaces public registration)."""
    serializer_class = RegisterSerializer
    permission_classes = [IsAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh_token = response.data.pop("refresh", None)
            if refresh_token:
                _set_refresh_cookie(response, refresh_token)
                # Also expose in body so the frontend can store it as a
                # sessionStorage fallback when cross-domain cookies are blocked.
                response.data["refresh_token"] = refresh_token
        return response


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        jwt_settings = settings.SIMPLE_JWT
        cookie_name = jwt_settings["AUTH_COOKIE"]

        # Accept the refresh token from the httpOnly cookie (primary path) or
        # from the request body (fallback for environments where cross-domain
        # cookies are blocked, e.g. Brave Shields, Safari ITP).
        refresh_token = request.COOKIES.get(cookie_name) or request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": "Refresh token not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # request.data is a read-only property in DRF — write to the backing
        # store directly so the parent TokenRefreshView sees the token.
        request._full_data = {"refresh": refresh_token}

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            new_refresh = response.data.pop("refresh", None)
            if new_refresh:
                _set_refresh_cookie(response, new_refresh)
                # Also expose the rotated refresh token in the body so the
                # frontend can update its sessionStorage fallback copy.
                response.data["refresh_token"] = new_refresh
        return response


class LogoutView(APIView):
    def post(self, request):
        jwt_settings = settings.SIMPLE_JWT
        cookie_name = jwt_settings["AUTH_COOKIE"]
        refresh_token = request.COOKIES.get(cookie_name)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie(cookie_name)
        return response


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ("PUT", "PATCH"):
            return MeUpdateSerializer
        return UserSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


# --- Admin ViewSets ---

class AdminUserViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin manages all users."""
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserDetailSerializer

    def get_queryset(self):
        return User.objects.all().select_related("organization").order_by("-date_joined")

    def perform_update(self, serializer):
        if self.get_object().role == User.ROLE_ADMIN:
            raise PermissionDenied("Admin users cannot be modified from this endpoint.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user.role == User.ROLE_ADMIN:
            return Response(
                {"detail": "Admin users cannot be deactivated."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="hard-delete")
    def hard_delete(self, request, *args, **kwargs):
        user = self.get_object()
        if user.pk == request.user.pk:
            return Response(
                {"detail": "You cannot delete your own account."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if user.role == User.ROLE_ADMIN:
            return Response(
                {"detail": "Admin accounts cannot be deleted."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        owned = user.owned_organizations.count()
        if owned:
            return Response(
                {"detail": f"User owns {owned} organization(s). Delete or reassign them first."},
                status=status.HTTP_409_CONFLICT,
            )
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrgViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Admin manages organizations."""
    permission_classes = [IsAdmin]
    serializer_class = OrganizationSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        return Organization.objects.all().select_related("owner").order_by("-created_at")

    def destroy(self, request, *args, **kwargs):
        org = self.get_object()
        active_count = org.members.filter(is_active=True).count()
        if active_count:
            return Response(
                {"detail": f"Organization has {active_count} active member(s). Deactivate or remove them first."},
                status=status.HTTP_409_CONFLICT,
            )
        org.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"])
    def provision(self, request):
        serializer = ProvisionOrgSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        with transaction.atomic():
            org = Organization.objects.create(name=d["name"])
            user = User.objects.create_user(
                email=d["owner_email"],
                username=d["owner_username"],
                password=d["owner_password"],
                role=User.ROLE_OWNER,
                organization=org,
                first_name=d["owner_first_name"],
                last_name=d["owner_last_name"],
            )
            org.owner = user
            org.save(update_fields=["owner"])
        return Response(OrganizationSerializer(org).data, status=status.HTTP_201_CREATED)


# --- Owner ViewSet ---

class OrgMemberViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Owner manages members within their own organization."""
    permission_classes = [IsOwner]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return MemberCreateSerializer
        if self.action in ("update", "partial_update"):
            return MemberUpdateSerializer
        return UserDetailSerializer

    def get_queryset(self):
        return (
            User.objects.filter(
                organization=self.request.user.organization,
                role=User.ROLE_MEMBER,
            )
            .select_related("organization")
            .order_by("email")
        )

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
            role=User.ROLE_MEMBER,
        )

    def perform_update(self, serializer):
        instance = self.get_object()
        if instance.organization_id != self.request.user.organization_id:
            raise PermissionDenied("You can only manage members of your own organization.")
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        member = self.get_object()
        if member.organization_id != request.user.organization_id:
            raise PermissionDenied("You can only manage members of your own organization.")
        member.is_active = False
        member.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)
