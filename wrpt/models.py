# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

import datetime
import re

from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User, UserManager
from django.urls import reverse

def notBlankValidator (value):
  if value.strip() == "": raise ValidationError("This field is required.")

class Schedule (models.Model):
  # A named list of one or more event dates that comprise a Walk&Roll
  # schedule.
  name = models.CharField(max_length=100, unique=True,
    validators=[notBlankValidator],
    help_text="Ex: Monthly, Bi-monthly, Wednesdays 2013-2014, Adams 2013-2014")
  def clean (self):
    self.name = self.name.strip()
  def __str__ (self):
    return self.name
  class Meta:
    # The leading spaces are a cheesy way to order models on the admin page.
    verbose_name_plural = "  Schedules"

class EventDate (models.Model):
  # A Walk&Roll event date belonging to a schedule.
  schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
  date = models.DateField()
  def clean (self):
    if self.pk != None:
      # This event date's schedule can't be changed if any counts
      # refer to this event date, but for simplicity we just disallow
      # all schedule changes.
      if self.schedule != EventDate.objects.get(pk=self.pk).schedule:
        raise ValidationError("Schedule cannot be changed.")
  def __str__ (self):
    return re.sub(r"0(\d)", "\\1", self.date.strftime("%b %d"))
  class Meta:
    unique_together = ("schedule", "date")

class School (models.Model):
  # A school.
  name = models.CharField(max_length=100, unique=True,
    validators=[notBlankValidator],
    help_text="Ex: Adams, Goleta Valley JH, Citywide Walk & Roll Challenge")
  def clean (self):
    self.name = self.name.strip()
  def __str__ (self):
    return self.name
  class Meta:
    # The leading spaces are a cheesy way to order models on the admin page.
    verbose_name_plural = "   Schools"

class WrptUser (User):
  # A user login.  We extend the Django auth User class primarily to
  # associate a user with a school.  Since we otherwise use the Django
  # auth app, the implication is that wherever Users are created
  # (namely, when authenticating and when creating the initial
  # database), we must ensure that WrptUsers are created instead.
  school = models.ForeignKey(School, on_delete=models.CASCADE,
    blank=True, null=True,
    help_text="The school that this user can update.  " +\
    "Set for non-staff users only.")
  hideChangePasswordLink = models.BooleanField("Hide change password link",
    default=False,
    help_text="If checked, hides the 'Change password' link from the user " +\
      "(password can still be changed by staff).")
  def clean (self):
    if self.is_staff and self.school != None:
      raise ValidationError("Check the 'Staff status' box or " +\
        "select a school, not both.")
    if self.hideChangePasswordLink and self.is_staff:
      raise ValidationError({ "hideChangePasswordLink":
        "This box can be checked for non-staff users only." })
  def save (self, *args, **kwargs):
    # We don't distinguish between being staff and being a superuser.
    self.is_superuser = self.is_staff
    super().save(*args, **kwargs)
  def __str__ (self):
    return self.username
  class Meta:
    verbose_name = "user"
    # The leading spaces are a cheesy way to order models on the admin page.
    verbose_name_plural = "     Users"

def schoolYearValidator (value):
  m = re.match("(\d{4})-(\d{4})$", value)
  if not m or int(m.group(2)) != int(m.group(1))+1:
    raise ValidationError("Invalid school year.")

def defaultSchoolYear ():
  t = datetime.date.today()
  # After March, we assume a program is being created for the next
  # school year.
  if t.month <= 3:
    y = t.year-1
  else:
    y = t.year
  return "%d-%d" % (y, y+1)

class Program (models.Model):
  # A Walk&Roll program for a school in a given school year.
  # Classrooms and counts belong to programs.
  school = models.ForeignKey(School, on_delete=models.CASCADE)
  schoolYear = models.CharField(max_length=9, validators=[schoolYearValidator],
    verbose_name="School year", help_text="Ex: 2013-2014",
    default=defaultSchoolYear)
  schedule = models.ForeignKey(Schedule, on_delete=models.CASCADE)
  splitCounts = models.BooleanField(verbose_name="Split counts",
    help_text="Check to split participation counts into two parts, " +\
    "active (walk/bike/scooter/etc) and inactive (carpool/bus)")
  participationGoal = models.IntegerField(blank=True, null=True,
    validators=[MinValueValidator(0), MaxValueValidator(100)],
    verbose_name="Participation goal (percentage; optional)",
    help_text="Ex: 50")
  def clean (self):
    if self.pk != None:
      hasCounts = Count.objects.filter(program=self).exists()
      if self.schedule != Program.objects.get(pk=self.pk).schedule:
        if hasCounts:
          raise ValidationError(
            "Schedule cannot be changed if the program has counts.")
      if self.splitCounts != Program.objects.get(pk=self.pk).splitCounts:
        if hasCounts:
          raise ValidationError(
            "Split counts flag cannot be changed if the program has counts.")
  def isViable (self):
    # A program needs at least one classroom to be considered viable.
    return Classroom.objects.filter(program=self).count() > 0
  def isCurrent (self):
    # After June, a program is no longer considered current.
    t = datetime.date.today()
    return (t.month <= 6 and int(self.schoolYear[:4]) >= t.year-1) or\
      (t.month > 6 and int(self.schoolYear[:4]) >= t.year)
  def get_absolute_url (self):
    return reverse("program", args=(self.pk,))
  def __str__ (self):
    return self.schoolYear + " " + self.school.name
  class Meta:
    unique_together = ("school", "schoolYear")
    # The leading spaces are a cheesy way to order models on the admin page.
    verbose_name_plural = " Programs"

class Classroom (models.Model):
  # A classroom.  By convention, a program not tallying by classroom
  # has a single classroom, "entire school".
  program = models.ForeignKey(Program, on_delete=models.CASCADE)
  name = models.CharField(max_length=100, validators=[notBlankValidator],
    help_text="An identifying name for the classroom.  " +\
    "Ex: 3C, Johnson, 3C Johnson.  If not tallying by classroom, create " +\
    "one classroom named \"entire school\".")
  enrollment = models.IntegerField(validators=[MinValueValidator(1)],
    help_text="Number of students in the classroom")
  def clean (self):
    self.name = self.name.strip()
    if self.pk != None:
      # This classroom's program can't be changed if any counts refer
      # to this classroom, but for simplicity we just disallow all
      # program changes.
      if self.program != Classroom.objects.get(pk=self.pk).program:
        raise ValidationError("Program cannot be changed.")
  def __str__ (self):
    return self.name
  class Meta:
    unique_together = ("program", "name")

class Count (models.Model):
  # A count of students for a classroom on an event date.  Depending
  # on the program configuration, the count may be a single value
  # ('value') or a pair of values (activeValue and inactiveValue); in
  # the latter case, 'value' holds the total.  The sum of 'value' and
  # absentees is not permitted to exceed the classroom enrollment on
  # the event date.
  program = models.ForeignKey(Program, on_delete=models.CASCADE)
  eventDate = models.ForeignKey(EventDate, on_delete=models.CASCADE,
    verbose_name="Event date")
  classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
  # The classroom has a nominal enrollment, but the enrollment often
  # changes slightly over time, so we record the enrollment's value on
  # the event date.
  enrollment = models.IntegerField(validators=[MinValueValidator(1)],
    help_text="Classroom enrollment on the event date")
  value = models.IntegerField(blank=True, null=True,
    validators=[MinValueValidator(0)],
    help_text="Total number of students who took alternative transportation")
  activeValue = models.IntegerField(blank=True, null=True,
    validators=[MinValueValidator(0)], verbose_name="Active value",
    help_text="Number of students who walked/biked/scootered/etc")
  inactiveValue = models.IntegerField(blank=True, null=True,
    validators=[MinValueValidator(0)], verbose_name="Inactive value",
    help_text="Number of students who carpooled/bused")
  absentees = models.IntegerField(validators=[MinValueValidator(0)],
    default=0, help_text="Number of students absent")
  comments = models.CharField(max_length=1000, blank=True)
  def clean (self):
    # In the Django admin, if an event date or classroom is not
    # selected, Django will report the appropriate validation
    # error(s), but at this point in the process the object will not
    # have the corresponding attributes at all, hence the protecting
    # calls to hasattr.
    if hasattr(self, "eventDate") and\
      self.eventDate.schedule != self.program.schedule:
      raise ValidationError("Event date is not in program's schedule.")
    if hasattr(self, "classroom") and self.classroom.program != self.program:
      raise ValidationError("Classroom is not in program.")
    if self.program.splitCounts:
      e = {}
      if self.activeValue == None: e["activeValue"] = "This field is required."
      if self.inactiveValue == None:
        e["inactiveValue"] = "This field is required."
      if len(e) > 0: raise ValidationError(e)
      self.value = self.activeValue + self.inactiveValue
    else:
      e = {}
      if self.value == None: e["value"] = "This field is required."
      if self.activeValue != None:
        e["activeValue"] = "This field must be left empty."
      if self.inactiveValue != None:
        e["inactiveValue"] = "This field must be left empty."
      if len(e) > 0: raise ValidationError(e)
    if self.value+self.absentees > self.enrollment:
      raise ValidationError(
        "Participants plus absentees exceeds classroom enrollment.")
  def __str__ (self):
    return "(%s, %s, %s)" % (self.program, self.eventDate,
      self.classroom)
  def logFormat (self):
    def f (v):
      return str(v) if v != None else ""
    return ("Count(id=%s,program=%s,eventDate=%s,classroom=%s," +\
      "enrollment=%s,value=%s,activeValue=%s,inactiveValue=%s," +\
      "absentees=%s,comments=%s)") %\
      (f(self.id), f(self.program_id), f(self.eventDate_id),
      f(self.classroom_id), f(self.enrollment), f(self.value),
      f(self.activeValue), f(self.inactiveValue), f(self.absentees),
      repr(self.comments))
  class Meta:
    unique_together = ("program", "eventDate", "classroom")
