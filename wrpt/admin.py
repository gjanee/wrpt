# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Group
from django.core.validators import ValidationError
from django.forms import ModelForm

from wrpt.models import Classroom, Count, EventDate, Program, Schedule,\
  School, WrptUser

class WrptUserAdmin (UserAdmin):
  # Customize the fields displayed in list view (principally, add
  # school).
  list_display = ("username", "first_name", "last_name", "is_staff", "school")
  # Remove the filter sidebar.
  list_filter = ()
  # Customize the fields displayed in change view (remove superuser
  # status [redundant since we equate staff and superusers], groups
  # and user permissions [don't use them], and important dates [ugly],
  # and add school).
  fieldsets = (
    (None, { "fields": ("username", "password") }),
    ("Personal info", { "fields": ("first_name", "last_name", "email") }),
    ("Permissions", { "fields": ("is_active", "is_staff", "school") })
  )
  # The UserAdmin change user template includes a "View on site" link
  # that we don't support but is just impossible to get rid of, so we
  # resort to hiding it via CSS.
  class Media:
    css = { "all": ("wrpt/admin_tweaks_1.css",) }

class SchoolAdmin (admin.ModelAdmin):
  ordering = ["name"]

class EventDateInline (admin.TabularInline):
  model = EventDate
  ordering = ["seq"]
  def get_extra (self, request, obj=None, **kwargs):
    # If creating a schedule, provide 10 blank date forms; if changing
    # an existing schedule, provide none.
    if obj == None:
      return 10
    else:
      return 0
  # Hide the display of the event date, which simply duplicates the
  # date input widget immediately below.
  class Media:
    css = { "all": ("wrpt/admin_tweaks_2.css",) }

class ScheduleAdmin (admin.ModelAdmin):
  ordering = ["name"]
  inlines = [EventDateInline]

class ClassroomInline (admin.TabularInline):
  model = Classroom
  ordering = ["name"]
  def get_extra (self, request, obj=None, **kwargs):
    # If creating a program, provide 10 blank classroom forms; if
    # changing an existing program, provide none.
    if obj == None:
      return 10
    else:
      return 0
  # Hide the display of the classroom, which simply duplicates the
  # name input widget immediately below (N.B.: this actually affects
  # all inlines on the program page).
  class Media:
    css = { "all": ("wrpt/admin_tweaks_2.css",) }

# Note that the following text, due its insertion method, is not
# HTML-escaped by Django.
helpText =\
"""To be listed on the website, a program must have at least one
classroom.  If the program is tallying only school-wide, and not by
classroom, enter one classroom whose name is &ldquo;entire
school&rdquo;."""

class ProgramAdmin (admin.ModelAdmin):
  ordering = ["-schoolYear", "school__name"]
  # Create a fieldset as a hacky way to provide some extra text on the
  # page.
  fieldsets = (
    (None, { "fields": ("schoolYear", "school", "schedule",
      "splitCounts", "participationGoal") }),
    ("CLASSROOM INSTRUCTIONS", { "fields": (), "description": helpText })
  )
  inlines = [ClassroomInline]

class ProgramFilter (admin.SimpleListFilter):
  # The sole purpose of this custom filter, over a simple "program"
  # filter, is to control the listing order.
  title = "program"
  parameter_name = "program"
  def lookups (self, request, model_admin):
    return [(p.id, str(p)) for p in\
      Program.objects.all().order_by("-schoolYear", "school__name")]
  def queryset (self, request, queryset):
    if self.value() != None: queryset = queryset.filter(program=self.value())
    return queryset

class CountForm (ModelForm):
  # For some reason the default Count form doesn't check that a
  # modified count continues to satisfy the uniqueness constraint.
  def clean (self):
    super().clean()
    i = self.instance
    edc = "eventDate" in self.changed_data
    cc = "classroom" in self.changed_data
    if edc or cc:
      ed = self.cleaned_data["eventDate"] if edc else i.eventDate
      c = self.cleaned_data["classroom"] if cc else i.classroom
      if Count.objects.filter(program=i.program, eventDate=ed,
        classroom=c).exists():
        e = {}
        m = "Count with this program, event date, and classroom " +\
          "already exists."
        if edc: e["eventDate"] = m
        if cc: e["classroom"] = m
        raise ValidationError(e)

class CountAdmin (admin.ModelAdmin):
  readonly_fields = ["program"]
  # Making a field readonly messes with the field order, so define a
  # fieldset to restore the order.
  fieldsets = (
    (None, { "fields": ("program", "eventDate", "classroom",
      "value", "activeValue", "inactiveValue", "absentees", "comments") }),
  )
  ordering = ["-program__schoolYear", "program__school__name",
    "-eventDate__seq", "classroom__name"]
  list_display = ["__str__", "comments"]
  list_filter = (ProgramFilter,)
  search_fields = ["program__schoolYear", "program__school__name",
    "eventDate__date", "classroom__name", "comments"]
  form = CountForm
  # To properly support count creation in the admin, we would need to
  # dynamically adjust the event date and classroom menus in response
  # to a change of program, which would require JavaScript.  Easier to
  # just disable creation altogether.
  def has_add_permission (self, request):
    return False
  # The next two functions limit the event date and classroom menu
  # choices according to the count's (fixed) program.
  def get_form (self, request, obj=None, **kwargs):
    if obj != None: self.the_count = obj
    return super().get_form(request, obj, **kwargs)
  def formfield_for_foreignkey (self, db_field, request, **kwargs):
    if db_field.name == "eventDate":
      kwargs["queryset"] = EventDate.objects.filter(
        schedule=self.the_count.program.schedule).order_by("seq")
    elif db_field.name == "classroom":
      kwargs["queryset"] = Classroom.objects.filter(
        program=self.the_count.program).order_by("name")
    return super().formfield_for_foreignkey(db_field, request, **kwargs)

admin.site.unregister(User)
admin.site.unregister(Group)

admin.site.register(WrptUser, WrptUserAdmin)
admin.site.register(School, SchoolAdmin)
admin.site.register(Schedule, ScheduleAdmin)
admin.site.register(Program, ProgramAdmin)
admin.site.register(Count, CountAdmin)
