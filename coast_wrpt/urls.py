# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

admin.autodiscover()

urlpatterns = [
  path("robots.txt", lambda request: redirect("/static/robots.txt")),
  path("", include("wrpt.urls")),
  path("admin/", admin.site.urls)
]
