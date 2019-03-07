# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django import forms
from django.core.validators import ValidationError

from wrpt.models import EventDate

class CountForm (forms.Form):
  eventDate = forms.ModelChoiceField(queryset=EventDate.objects.all())
  # Without 'localize=True' below, Django uses a bizarro widget that
  # doesn't check for valid integers?!
  value = forms.IntegerField(min_value=0, required=False, localize=True)
  activeValue = forms.IntegerField(min_value=0, required=False, localize=True)
  inactiveValue =\
    forms.IntegerField(min_value=0, required=False, localize=True)
  absentees = forms.IntegerField(min_value=0, required=False, localize=True,
    initial=0)
  comments = forms.CharField(max_length=1000, required=False,
    widget=forms.TextInput(attrs={ "size": "100" }))
  def __init__ (self, *args, **kwargs):
    self.classroom = kwargs.pop("classroom")
    canSubmit = kwargs.pop("canSubmit")
    super().__init__(*args, **kwargs)
    self.fields["eventDate"].queryset = EventDate.objects.filter(
      schedule=self.classroom.program.schedule).order_by("seq")
    if not canSubmit:
      self.fields["eventDate"].widget.attrs["disabled"] = "disabled"
      self.fields["value"].widget.attrs["disabled"] = "disabled"
      self.fields["activeValue"].widget.attrs["disabled"] = "disabled"
      self.fields["inactiveValue"].widget.attrs["disabled"] = "disabled"
      self.fields["absentees"].widget.attrs["disabled"] = "disabled"
      self.fields["comments"].widget.attrs["disabled"] = "disabled"
  def clean (self):
    cleaned_data = super().clean()
    if not self.classroom.program.isCurrent():
      raise ValidationError("The program has concluded.")
    return cleaned_data
