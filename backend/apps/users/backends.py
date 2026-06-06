from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class OrgAwareBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email:
            return None
        # Null-org admins are globally unique — try first
        try:
            user = User.objects.get(email=email, organization__isnull=True)
            return user if user.check_password(password) and self.user_can_authenticate(user) else None
        except User.DoesNotExist:
            pass
        # Org-scoped: works if exactly one org has this email
        matches = list(User.objects.filter(email=email, organization__isnull=False))
        if len(matches) == 1:
            u = matches[0]
            return u if u.check_password(password) and self.user_can_authenticate(u) else None
        return None
