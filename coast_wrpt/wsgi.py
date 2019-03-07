# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "coast_wrpt.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
