# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django.contrib.auth.backends import ModelBackend

from wrpt.models import WrptUser

class WrptUserModelBackend (ModelBackend):
  def authenticate (self, request, username=None, password=None):
    try:
      user = WrptUser.objects.get(username=username)
      if user.check_password(password):
        return user
      else:
        return None
    except WrptUser.DoesNotExist:
      return None
  def get_user (self, user_id):
    try:
      return WrptUser.objects.get(pk=user_id)
    except WrptUser.DoesNotExist:
      return None
