# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

# The way our custom user model is implemented (i.e., as a subclass of
# the built-in user model) is a bit of a hack, and there are now
# better ways of doing it.  The price paid is that users need to use
# this command, which forces the correct model, and not the built-in
# createsuperuser command.

from django.contrib.auth.management.commands import createsuperuser

from wrpt.models import WrptUser

class Command (createsuperuser.Command):
  def __init__ (self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.UserModel = WrptUser
