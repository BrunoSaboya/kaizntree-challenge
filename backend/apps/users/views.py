from django.conf import settings
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import CustomTokenObtainPairSerializer, RegisterSerializer, UserSerializer


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
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        response = Response(
            {
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )
        _set_refresh_cookie(response, str(refresh))
        return response


class LoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == status.HTTP_200_OK:
            refresh_token = response.data.pop("refresh", None)
            if refresh_token:
                _set_refresh_cookie(response, refresh_token)
        return response


class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        jwt_settings = settings.SIMPLE_JWT
        cookie_name = jwt_settings["AUTH_COOKIE"]
        refresh_token = request.COOKIES.get(cookie_name)

        if not refresh_token:
            return Response(
                {"detail": "Refresh token not found in cookie."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        request.data._mutable = True if hasattr(request.data, "_mutable") else None
        try:
            request.data["refresh"] = refresh_token
        except AttributeError:
            request.data = {"refresh": refresh_token}

        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            new_refresh = response.data.pop("refresh", None)
            if new_refresh:
                _set_refresh_cookie(response, new_refresh)
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


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
