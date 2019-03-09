# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django import forms
from django.core.validators import ValidationError

from wrpt.models import Count, EventDate

class CountForm (forms.Form):
  eventDate = forms.ModelChoiceField(queryset=EventDate.objects.all())
  # Without 'localize=True' below, Django uses a bizarro widget that
  # doesn't check for valid integers?!
  # Enrollment is required, but will receive an initial value below.
  enrollment = forms.IntegerField(min_value=1, required=True, localize=True)
  # Note that the value fields are allowed to be blank: blank values
  # are treated as a command to delete an existing count.
  value = forms.IntegerField(min_value=0, required=False, localize=True)
  activeValue = forms.IntegerField(min_value=0, required=False, localize=True)
  inactiveValue =\
    forms.IntegerField(min_value=0, required=False, localize=True)
  absentees = forms.IntegerField(min_value=0, required=True, localize=True,
    initial=0)
  comments = forms.CharField(max_length=1000, required=False,
    widget=forms.TextInput(attrs={ "size": "100" }))
  def __init__ (self, *args, **kwargs):
    self.classroom = kwargs.pop("classroom")
    canSubmit = kwargs.pop("canSubmit")
    super().__init__(*args, **kwargs)
    if self.is_bound: return
    self.fields["eventDate"].queryset = EventDate.objects.filter(
      schedule=self.classroom.program.schedule).order_by("date")
    # The initial enrollment value is either the value supplied by the
    # most recent count for this classroom, or the classroom's nominal
    # value.
    counts = list(Count.objects.filter(program=self.classroom.program,
      classroom=self.classroom).select_related("eventDate")\
      .order_by("eventDate__date"))
    if len(counts) > 0:
      self.fields["enrollment"].initial = counts[-1].enrollment
    else:
      self.fields["enrollment"].initial = self.classroom.enrollment
    if self.classroom.program.splitCounts:
      self.fields["value"].disabled = True
    else:
      self.fields["activeValue"].disabled = True
      self.fields["inactiveValue"].disabled = True
    if not canSubmit:
      self.fields["eventDate"].disabled = True
      self.fields["enrollment"].disabled = True
      self.fields["value"].disabled = True
      self.fields["activeValue"].disabled = True
      self.fields["inactiveValue"].disabled = True
      self.fields["absentees"].disabled = True
      self.fields["comments"].disabled = True
  def clean (self):
    cleaned_data = super().clean()
    # Bail out if there are already individual field errors.
    if len(self.errors.as_data()) > 0: return cleaned_data
    if not self.classroom.program.isCurrent():
      raise ValidationError("The program has concluded.")
    d = cleaned_data
    if self.classroom.program.splitCounts:
      countSubmitted = (d["activeValue"] != None or d["inactiveValue"] != None)
      if countSubmitted:
        d["activeValue"] = d["activeValue"] or 0
        d["inactiveValue"] = d["inactiveValue"] or 0
        d["value"] = d["activeValue"] + d["inactiveValue"]
    else:
      countSubmitted = (d["value"] != None)
    if countSubmitted and d["value"]+d["absentees"] > d["enrollment"]:
      raise ValidationError(
        "Participants plus absentees exceeds classroom enrollment.")
    d["comments"] = d["comments"].strip()
    return d
