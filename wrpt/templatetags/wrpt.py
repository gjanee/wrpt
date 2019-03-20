# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django import template

register = template.Library()

def getattr_or_null (object, attr):
  return getattr(object, attr, "null")

register.filter("getattr_or_null", getattr_or_null)
