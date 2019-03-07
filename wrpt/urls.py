# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django.contrib.auth.views import LoginView, LogoutView,\
  PasswordChangeView, PasswordChangeDoneView
from django.urls import path

from wrpt import views

urlpatterns = [
  path("", views.home),
  path("program/<int:id>", views.program, name="program"),
  path("classroom/<int:id>", views.classroom, name="classroom"),
  path("dump_counts", views.dumpCounts, name="dump_counts"),
  path("login", LoginView.as_view(template_name="wrpt/login.html"),
    name="login"),
  path("logout", LogoutView.as_view(), name="logout"),
  path("change_password", PasswordChangeView.as_view(
    template_name="wrpt/password_change_form.html",
    success_url="/password_changed"), name="change_password"),
  path("password_changed", PasswordChangeDoneView.as_view(
    template_name="wrpt/password_change_done.html"),
    name="password_changed")
]
