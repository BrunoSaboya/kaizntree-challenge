from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Organization

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name",
                  "role", "organization_id", "organization_name", "date_joined"]
        read_only_fields = fields

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization_id else None


class OrganizationSerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source="owner.email", read_only=True)

    class Meta:
        model = Organization
        fields = ["id", "name", "owner", "owner_email", "created_at"]
        read_only_fields = ["id", "owner_email", "created_at"]


class ProvisionOrgSerializer(serializers.Serializer):
    """Admin provisions a new org + its owner in one atomic call."""
    name = serializers.CharField(max_length=255)
    owner_email = serializers.EmailField()
    owner_username = serializers.CharField(max_length=150)
    owner_password = serializers.CharField(write_only=True, validators=[validate_password])
    owner_first_name = serializers.CharField(max_length=150, required=False, default="")
    owner_last_name = serializers.CharField(max_length=150, required=False, default="")

    def validate_owner_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_owner_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this username already exists.")
        return value


class RegisterSerializer(serializers.ModelSerializer):
    """Admin-only user creation."""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name",
                  "role", "organization", "password", "password_confirm"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        role = attrs.get("role", User.ROLE_OWNER)
        org = attrs.get("organization")
        if role != User.ROLE_ADMIN and org is None:
            raise serializers.ValidationError(
                {"organization": "Non-admin users must belong to an organization."}
            )
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return User.objects.create_user(**validated_data)


class UserCreateSerializer(serializers.ModelSerializer):
    """Admin creates any user; owner creates members (role/org enforced in the view)."""
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name",
                  "role", "organization", "password"]

    def validate(self, attrs):
        role = attrs.get("role", User.ROLE_MEMBER)
        org = attrs.get("organization")
        if role != User.ROLE_ADMIN and org is None:
            raise serializers.ValidationError(
                {"organization": "Non-admin users must belong to an organization."}
            )
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserDetailSerializer(serializers.ModelSerializer):
    organization_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "username", "first_name", "last_name",
                  "role", "organization", "organization_name",
                  "is_active", "date_joined"]
        read_only_fields = ["id", "email", "organization_name", "date_joined"]

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization_id else None


class UserUpdateSerializer(serializers.ModelSerializer):
    """Admin updates any user's role, org, active status."""

    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "organization", "is_active"]


class MemberCreateSerializer(serializers.ModelSerializer):
    """Owner creates a member — role is forced to 'member' in the view."""
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "password"]

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class MemberUpdateSerializer(serializers.ModelSerializer):
    """Owner updates a member's name or password."""
    password = serializers.CharField(write_only=True, required=False,
                                     validators=[validate_password])

    class Meta:
        model = User
        fields = ["first_name", "last_name", "password"]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class MeUpdateSerializer(serializers.ModelSerializer):
    """Users update their own profile."""
    password = serializers.CharField(write_only=True, required=False,
                                     validators=[validate_password])

    class Meta:
        model = User
        fields = ["first_name", "last_name", "password"]

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["user"] = UserSerializer(self.user).data
        return data
