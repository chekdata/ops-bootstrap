from accounts.models import User
from django.contrib.auth.backends import ModelBackend

class UserIDAuthBackend(ModelBackend):
    def authenticate(self, request, user_id=None):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
