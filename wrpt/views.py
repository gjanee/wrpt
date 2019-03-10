# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.gzip import gzip_page
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Sum

from collections import namedtuple
import csv
import datetime
import io
import logging

from wrpt.models import Classroom, Count, EventDate, Program
from wrpt.forms import CountForm

maximumTableWidth = 20 # columns

def percentage (m, n, a):
  # Returns m/(n-a) as an integer percentage, safely.
  d = n-a
  if d > 0:
    return min(round((m/d)*100), 100)
  else:
    return 0

def formCanBeSubmitted (user, classroom):
  return user.is_authenticated and\
    (user.is_staff or user.school == classroom.program.school)

def log (request, operation, count1, count2=None):
  logging.getLogger("wrpt").info(
    "[WRPT] %s %s %s %s%s%s" % (request.META.get("REMOTE_ADDR", "unknown"),
    request.user.username, operation,
    "FROM=" if operation == "update" else "", count1,
    " TO="+count2 if operation == "update" else ""))

def home (request):
  current = []
  past = []
  for p in Program.objects.all().select_related("school")\
    .order_by("-schoolYear", "school__name"):
    if p.isViable():
      if p.isCurrent():
        current.append(p)
      else:
        past.append(p)
  return render(request, "wrpt/home.html", { "currentPrograms": current,
    "pastPrograms": past })

def addClassroomData (context, classroom, dataKey):
  Datum = namedtuple("Datum", ["enrollment", "value", "absentees"])
  dates = EventDate.objects.filter(
    schedule=classroom.program.schedule).order_by("date")
  map = dict((c.eventDate.pk, Datum(c.enrollment, c.value, c.absentees))\
    for c in Count.objects.filter(classroom=classroom)\
    .select_related("eventDate"))
  context["hasData"] = (len(map) > 0)
  if context["hasData"]:
    data = []
    overall = [0, 0] # numerator, denominator
    for date in dates:
      if date.pk in map:
        d = map[date.pk]
        data.append({ "date": date, "count": d.value, "absentees": d.absentees,
          "percentage": percentage(d.value, d.enrollment, d.absentees) })
        if date.date <= datetime.date.today():
          overall[0] += d.value
          overall[1] += d.enrollment - d.absentees
      else:
        data.append({ "date": date, "count": None, "absentees": None,
          "percentage": None })
        if date.date <= datetime.date.today():
          overall[1] += classroom.enrollment
    context[dataKey] = data
    context["overall"] = percentage(overall[0], overall[1], 0)
    # It's a pain to do slicing inside templates, so compute the table
    # slices here.
    slices = []
    for i in range((len(dates)-1)//maximumTableWidth+1):
      slices.append("%d:%d" % (i*maximumTableWidth,
        min((i+1)*maximumTableWidth, len(dates))))
    context["tableSlices"] = slices

def classroom (request, id):
  try:
    classroom = Classroom.objects.select_related("program",
      "program__school", "program__schedule").get(pk=id)
  except Classroom.DoesNotExist:
    raise Http404
  canSubmit = formCanBeSubmitted(request.user, classroom)
  if request.method == "POST":
    # Should never happen.
    if not canSubmit: raise PermissionDenied
    form = CountForm(request.POST, classroom=classroom, canSubmit=canSubmit)
    if form.is_valid():
      try:
        c = Count.objects.get(program=classroom.program,
          eventDate=form.cleaned_data["eventDate"], classroom=classroom)
        if form.cleaned_data["value"] != None:
          before = c.logFormat()
          c.enrollment = form.cleaned_data["enrollment"]
          c.value = form.cleaned_data["value"]
          c.activeValue = form.cleaned_data["activeValue"]
          c.inactiveValue = form.cleaned_data["inactiveValue"]
          c.absentees = form.cleaned_data["absentees"]
          c.comments = form.cleaned_data["comments"]
          c.save()
          log(request, "update", before, c.logFormat())
          messages.success(request, "Count updated.")
        else:
          c.delete()
          log(request, "delete", c.logFormat())
          messages.success(request, "Count deleted.")
      except Count.DoesNotExist:
        if form.cleaned_data["value"] != None:
          c = Count(program=classroom.program,
            eventDate=form.cleaned_data["eventDate"], classroom=classroom,
            enrollment=form.cleaned_data["enrollment"],
            value=form.cleaned_data["value"],
            activeValue=form.cleaned_data["activeValue"],
            inactiveValue=form.cleaned_data["inactiveValue"],
            absentees=form.cleaned_data["absentees"],
            comments=form.cleaned_data["comments"])
          c.save()
          log(request, "create", c.logFormat())
          messages.success(request, "Count saved.")
        else:
          messages.success(request, "Did you mean to supply a count?")
      return HttpResponseRedirect(request.path)
  else:
    form = CountForm(classroom=classroom, canSubmit=canSubmit)
  context = { "form": form, "classroom": classroom,
    "program": classroom.program, "canSubmit": canSubmit }
  # This view is also used to view one-classroom programs.
  if classroom.name == "entire school" and\
    classroom.program.classroom_set.count() == 1:
    context["label"] = "School"
  else:
    context["label"] = "Classroom"
  addClassroomData(context, classroom, "data")
  return render(request, "wrpt/classroom.html", context)

def addProgramData (context, program, classrooms):
  Datum = namedtuple("Datum", ["enrollment", "value", "absentees"])
  dates = EventDate.objects.filter(
    schedule=program.schedule).order_by("date")
  map = dict(((c.classroom.pk, c.eventDate.pk), Datum(c.enrollment,
    c.value, c.absentees)) for c in Count.objects.filter(program=program)\
    .select_related("classroom", "eventDate"))
  context["hasData"] = (len(map) > 0)
  if context["hasData"]:
    context["dates"] = dates
    # Note that in computing overall counts and percentages we're
    # careful to distinguish 0 from None (i.e., no data).
    overall = dict((d.pk, Datum(0, 0, 0)) for d in dates)
    classroomData = []
    for c in classrooms:
      data = []
      classroomOverall = [0, 0] # numerator, denominator
      for date in dates:
        if (c.pk, date.pk) in map:
          d = map[(c.pk, date.pk)]
          data.append({ "date": date,
            "percentage": percentage(d.value, d.enrollment, d.absentees) })
          if date.date <= datetime.date.today():
            classroomOverall[0] += d.value
            classroomOverall[1] += d.enrollment - d.absentees
            overall[date.pk] = Datum(overall[date.pk][0]+d[0],
              overall[date.pk][1]+d[1], overall[date.pk][2]+d[2])
        else:
          data.append({ "date": date, "percentage": None })
          if date.date <= datetime.date.today():
            classroomOverall[1] += c.enrollment
            overall[date.pk] = Datum(overall[date.pk][0]+c.enrollment,
              overall[date.pk][1], overall[date.pk][2])
      classroomData.append({ "classroom": c, "data": data,
        "overall": percentage(classroomOverall[0], classroomOverall[1], 0) })
    context["classroomData"] = classroomData
    data = []
    for d in dates:
      if d.date <= datetime.date.today():
        data.append({ "date": d,
          "percentage": percentage(overall[d.pk].value,
          overall[d.pk].enrollment, overall[d.pk].absentees) })
      else:
        data.append({ "date": d, "percentage": None })
    context["schoolData"] = data
    # It's a pain to do slicing inside templates, so compute the table
    # slices here.
    slices = []
    for i in range((len(dates)-1)//maximumTableWidth+1):
      slices.append("%d:%d" % (i*maximumTableWidth,
        min((i+1)*maximumTableWidth, len(dates))))
    context["tableSlices"] = slices

def program (request, id):
  try:
    program = Program.objects.select_related("school", "schedule").get(pk=id)
  except Program.DoesNotExist:
    raise Http404
  classrooms = Classroom.objects.filter(program=program).order_by("name")
  if len(classrooms) == 0:
    raise Http404
  elif len(classrooms) == 1 and classrooms[0].name == "entire school":
    return redirect("classroom", id=classrooms[0].pk)
  else:
    totalEnrollment =\
      classrooms.aggregate(Sum("enrollment"))["enrollment__sum"]
    context = { "program": program, "classrooms": classrooms,
      "totalEnrollment": totalEnrollment }
    addProgramData(context, program, classrooms)
    return render(request, "wrpt/program-n.html", context)

@staff_member_required
@gzip_page
def dumpCounts (request):
  s = io.StringIO()
  w = csv.writer(s)
  w.writerow(["program", "eventDate", "classroom", "enrollment", "value",
    "activeValue", "inactiveValue", "absentees", "comments"])
  for c in Count.objects.all().select_related("program", "program__school",
    "eventDate", "classroom"):
    w.writerow([c.program, c.eventDate.date, c.classroom.name,
      c.enrollment, c.value, c.activeValue, c.inactiveValue,
      c.absentees, c.comments])
  return HttpResponse(s.getvalue(), content_type="text/plain; charset=UTF-8")
