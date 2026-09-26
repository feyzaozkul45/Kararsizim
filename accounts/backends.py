from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailOrUsernameBackend(ModelBackend):
    """Authenticate with either the username or the e-mail address."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if not username or password is None:
            return None

        identifier = username.strip()
        user = User.objects.filter(username=identifier).first()
        if user is None:
            user = User.objects.filter(email=identifier.lower()).first()

        if user is None:
            # Run the hasher once to reduce timing differences.
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
