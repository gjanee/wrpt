# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django import template

register = template.Library()

@register.simple_tag
def getattr_or_null (objectList, index, attr):
  return getattr(objectList[index], attr, "null")
