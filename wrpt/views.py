# =============================================================================
# Walk&Roll Performance Tracking
# Copyright (c) 2014, Greg Janee <gregjanee@gmail.com>
# License: http://www.gnu.org/licenses/gpl-2.0.html
# -----------------------------------------------------------------------------

from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.gzip import gzip_page
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db.models import Sum

import csv
import datetime
import io
import time

from wrpt.models import Classroom, Count, EventDate, Program
from wrpt.forms import CountForm

maximumTableWidth = 20 # columns

def dateIsInPast (date):
  try:
    st = time.strptime(date, "%m/%d/%Y")
    return (datetime.date(st.tm_year, st.tm_mon, st.tm_mday) <=\
      datetime.date.today())
  except:
    return False

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

def home (request):
  current = []
  past = []
  for p in Program.objects.all().order_by("school__name", "-schoolYear"):
    if p.isViable():
      if p.isCurrent():
        current.append(p)
      else:
        past.append(p)
  return render(request, "wrpt/home.html", { "currentPrograms": current,
    "pastPrograms": past })

def addClassroomData (context, classroom, dataKey):
  dates = EventDate.objects.filter(
    schedule=classroom.program.schedule).order_by("seq")
  map = dict((c.eventDate.pk, (c.value, c.absentees))\
    for c in Count.objects.filter(classroom=classroom))
  context["hasData"] = (len(map) > 0)
  if context["hasData"]:
    data = []
    overall = [0, 0] # numerator, denominator
    for date in dates:
      if date.pk in map:
        data.append({ "date": date, "count": map[date.pk][0],
          "absentees": map[date.pk][1],
          "percentage": percentage(map[date.pk][0], classroom.enrollment,
          map[date.pk][1]) })
      else:
        data.append({ "date": date, "count": None, "absentees": None,
          "percentage": None })
      if dateIsInPast(date.date):
        if date.pk in map:
          d = max(classroom.enrollment-map[date.pk][1], 0)
          overall[0] += min(map[date.pk][0], d)
          overall[1] += d
        else:
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
  classroom = get_object_or_404(Classroom, pk=id)
  canSubmit = formCanBeSubmitted(request.user, classroom)
  if request.method == "POST":
    # Should never happen.
    if not canSubmit: raise PermissionDenied
    form = CountForm(request.POST, classroom=classroom, canSubmit=canSubmit)
    if form.is_valid():
      try:
        c = Count.objects.get(program=classroom.program,
          eventDate=form.cleaned_data["eventDate"], classroom=classroom)
        if form.cleaned_data["absentees"] != None:
          c.absentees = min(form.cleaned_data["absentees"],
            classroom.enrollment)
        else:
          c.absentees = 0
        c.comments = form.cleaned_data["comments"]
        if classroom.program.splitCounts:
          if form.cleaned_data["activeValue"] != None or\
            form.cleaned_data["inactiveValue"] != None:
            c.activeValue = min(form.cleaned_data["activeValue"] or 0,
              classroom.enrollment-c.absentees)
            c.inactiveValue = min(form.cleaned_data["inactiveValue"] or 0,
              classroom.enrollment-c.absentees)
            c.value = min(c.activeValue+c.inactiveValue,
              classroom.enrollment-c.absentees)
            c.save()
            messages.success(request, "Count updated.")
          else:
            c.delete()
            messages.success(request, "Count deleted.")
        else:
          if form.cleaned_data["value"] != None:
            c.value = min(form.cleaned_data["value"],
              classroom.enrollment-c.absentees)
            c.save()
            messages.success(request, "Count updated.")
          else:
            c.delete()
            messages.success(request, "Count deleted.")
      except Count.DoesNotExist:
        if form.cleaned_data["absentees"] != None:
          absentees = min(form.cleaned_data["absentees"],
            classroom.enrollment)
        else:
          absentees = 0
        if classroom.program.splitCounts:
          if form.cleaned_data["activeValue"] != None or\
            form.cleaned_data["inactiveValue"] != None:
            activeValue = min(form.cleaned_data["activeValue"] or 0,
              classroom.enrollment-absentees)
            inactiveValue = min(form.cleaned_data["inactiveValue"] or 0,
              classroom.enrollment-absentees)
            c = Count(program=classroom.program,
              eventDate=form.cleaned_data["eventDate"], classroom=classroom,
              value=min(activeValue+inactiveValue,
              classroom.enrollment-absentees),
              activeValue=activeValue, inactiveValue=inactiveValue,
              absentees=absentees,
              comments=form.cleaned_data["comments"])
            c.save()
            messages.success(request, "Count saved.")
          else:
            messages.success(request, "Did you mean to supply a count?")
        else:
          if form.cleaned_data["value"] != None:
            c = Count(program=classroom.program,
              eventDate=form.cleaned_data["eventDate"], classroom=classroom,
              value=min(form.cleaned_data["value"],
              classroom.enrollment-absentees),
              activeValue=None, inactiveValue=None,
              absentees=absentees,
              comments=form.cleaned_data["comments"])
            c.save()
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

def addProgramData (context, program, classrooms, totalEnrollment):
  dates = EventDate.objects.filter(
    schedule=program.schedule).order_by("seq")
  map = dict(((c.classroom.pk, c.eventDate.pk), (c.value, c.absentees))\
    for c in Count.objects.filter(program=program))
  context["hasData"] = (len(map) > 0)
  if context["hasData"]:
    context["dates"] = dates
    # Note that in computing overall counts and percentages we're
    # careful to distinguish 0 from None (i.e., no data).
    overall = dict((d.pk, None) for d in dates)
    classroomData = []
    for c in classrooms:
      data = []
      classroomOverall = [0, 0] # numerator, denominator
      for d in dates:
        if (c.pk, d.pk) in map:
          data.append({ "date": d, "count": map[(c.pk, d.pk)][0],
            "percentage": percentage(map[(c.pk, d.pk)][0], c.enrollment,
            map[(c.pk, d.pk)][1]) })
          if overall[d.pk] == None:
            overall[d.pk] = map[(c.pk, d.pk)]
          else:
            overall[d.pk] = (overall[d.pk][0]+map[(c.pk, d.pk)][0],
              overall[d.pk][1]+map[(c.pk, d.pk)][1])
        else:
          data.append({ "date": d, "count": None, "percentage": None })
        if dateIsInPast(d.date):
          if (c.pk, d.pk) in map:
            e = max(c.enrollment-map[(c.pk, d.pk)][1], 0)
            classroomOverall[0] += min(map[(c.pk, d.pk)][0], e)
            classroomOverall[1] += e
          else:
            classroomOverall[1] += c.enrollment
      classroomData.append({ "classroom": c, "data": data,
        "overall": percentage(classroomOverall[0], classroomOverall[1], 0) })
    context["classroomData"] = classroomData
    data = []
    for d in dates:
      if overall[d.pk] != None:
        data.append({ "date": d, "count": overall[d.pk][0],
          "percentage": percentage(overall[d.pk][0], totalEnrollment,
          overall[d.pk][1]) })
      else:
        data.append({ "date": d, "count": None, "percentage": None })
    context["schoolData"] = data
    # It's a pain to do slicing inside templates, so compute the table
    # slices here.
    slices = []
    for i in range((len(dates)-1)//maximumTableWidth+1):
      slices.append("%d:%d" % (i*maximumTableWidth,
        min((i+1)*maximumTableWidth, len(dates))))
    context["tableSlices"] = slices

def program (request, id):
  program = get_object_or_404(Program, pk=id)
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
    addProgramData(context, program, classrooms, totalEnrollment)
    return render(request, "wrpt/program-n.html", context)

@staff_member_required
@gzip_page
def dumpCounts (request):
  s = io.StringIO()
  w = csv.writer(s)
  w.writerow(["program", "eventDate", "classroom", "enrollment", "value",
    "activeValue", "inactiveValue", "absentees", "comments"])
  last_id = -1
  while True:
    counts = list(Count.objects.filter(id__gt=last_id).order_by("id")[:100])
    if len(counts) == 0: break
    for c in counts:
      w.writerow([c.program, c.eventDate.date, c.classroom.name,
        c.classroom.enrollment, c.value, c.activeValue, c.inactiveValue,
        c.absentees, c.comments])
    last_id = counts[-1].id
  return HttpResponse(s.getvalue(), content_type="text/plain; charset=UTF-8")
