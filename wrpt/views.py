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

def percentage (n, d):
  # Returns n/d as an integer percentage, safely.
  if d > 0:
    return round((n/d)*100)
  else:
    return 0

class ClassroomStats (object):
  # This class is more complex than would seem to be necessary because
  # of the need to accommodate three cases: a date for which there is
  # a count; a date for which no count was recorded (in which case
  # percentages are not displayed in the table, but cumulative counts
  # and percentages are still computed and displayed in the graph);
  # and a date in the future (which holds no data and serves only as a
  # placeholder).  Note that the supplied count is stored and may be
  # modified.
  def __init__ (self, date, count=None, prev=None,
    computeEventDatePercentages=True):
    self.date = date
    if count == None: return
    self.count = count
    if count.activeValue == None:
      count.activeValue = count.value
      count.inactiveValue = 0
    present = count.enrollment - count.absentees
    self.presentSum = present
    self.activeSum = count.activeValue
    self.inactiveSum = count.inactiveValue
    if prev != None:
      self.presentSum += prev.presentSum
      self.activeSum += prev.activeSum
      self.inactiveSum += prev.inactiveSum
    self.combinedCumPct = percentage(self.activeSum+self.inactiveSum,
      self.presentSum)
    self.activeCumPct = percentage(self.activeSum, self.presentSum)
    self.inactiveCumPct = percentage(self.inactiveSum, self.presentSum)
    if computeEventDatePercentages:
      self.combinedPct = percentage(count.value, present)
      self.activePct = percentage(count.activeValue, present)
      self.inactivePct = percentage(count.inactiveValue, present)

class ProgramStats (object):
  # Simpler than the preceding, there are only two cases: a date for
  # which there are percentages (for the event day and cumulative);
  # and a date in the future (which holds no data and serves only as a
  # placeholder).
  def __init__ (self, date, combinedPct=None, activePct=None,
    inactivePct=None, combinedCumPct=None, activeCumPct=None,
    inactiveCumPct=None):
    self.date = date
    if combinedPct != None:
      self.combinedPct = combinedPct
      self.activePct = activePct
      self.inactivePct = inactivePct
      self.combinedCumPct = combinedCumPct
      self.activeCumPct = activeCumPct
      self.inactiveCumPct = inactiveCumPct

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

def computeClassroomData (dates, map, classroom, today):
  # Returns ([ClassroomStats, ...], lastIndex).  A ClassroomStats
  # object is returned for each date; those after `today` are empty
  # placeholders.  `lastIndex` is the index of the last non-empty
  # ClassroomStats, or -1 if they're all empty.
  stats = []
  lastEnrollment = classroom.enrollment
  i = -1
  for d in dates:
    if d.date <= today:
      i += 1
      # If the classroom has no count recorded for the event date, it
      # is penalized by being given zero participation relative to its
      # most recently observed enrollment.
      if (classroom.pk, d.pk) in map:
        c = map[(classroom.pk, d.pk)]
        lastEnrollment = c.enrollment
        countFound = True
      else:
        c = Count(enrollment=lastEnrollment, value=0)
        countFound = False
      s = ClassroomStats(d, c, stats[-1] if len(stats) > 0 else None,
        computeEventDatePercentages=countFound)
    else:
      s = ClassroomStats(d)
    stats.append(s)
  return stats, i

def addClassroomData (context, classroom):
  dates = EventDate.objects.filter(
    schedule=classroom.program.schedule).order_by("date")
  map = dict(((classroom.pk, c.eventDate.pk), c)\
    for c in Count.objects.filter(classroom=classroom)\
    .select_related("eventDate"))
  context["hasData"] = (len(map) > 0)
  if context["hasData"]:
    context["data"], i =\
      computeClassroomData(dates, map, classroom, datetime.date.today())
    context["lastStats"] = context["data"][i] if i >= 0 else None
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
    context["label"] = "school"
  else:
    context["label"] = "classroom"
  addClassroomData(context, classroom)
  if context["hasData"]:
    # Because we don't allow users to enter counts for dates that are
    # in the future, if hasData is true then there must be a
    # last ClassroomStats, but out of an abundance of caution...
    if context["lastStats"] != None:
      ls = context["lastStats"]
      if classroom.program.splitCounts:
        context["graphSeries"] = [
          ("Overall", "combinedCumPct", ls.combinedCumPct),
          ("Walk/bike", "activeCumPct", ls.activeCumPct),
          ("Carpool/bus", "inactiveCumPct", ls.inactiveCumPct)]
      else:
        context["graphSeries"] = [
          ("Participation", "combinedCumPct", ls.combinedCumPct)]
      # Sort the series in decreasing order of total to date
      # percentage.
      context["graphSeries"].sort(key=lambda t: -t[2])
    else:
      context["graphSeries"] = []
  return render(request, "wrpt/classroom.html", context)

def addProgramData (context, program, classrooms):
  dates = EventDate.objects.filter(
    schedule=program.schedule).order_by("date")
  map = dict(((c.classroom.pk, c.eventDate.pk), c)\
    for c in Count.objects.filter(program=program)\
    .select_related("classroom", "eventDate"))
  context["hasData"] = (len(map) > 0)
  if context["hasData"]:
    today = datetime.date.today()
    cdata = []
    for c in classrooms:
      # N.B.: the last index will be the same for every classroom and
      # the program generally.
      l, lastIndex = computeClassroomData(dates, map, c, today)
      cdata.append((c, l[lastIndex] if lastIndex >= 0 else None, l))
    context["classroomData"] = cdata
    data = []
    for i, d in enumerate(dates):
      if i <= lastIndex:
        asum = isum = psum = acsum = icsum = pcsum = 0
        for _, _, l in cdata:
          asum += l[i].count.activeValue
          isum += l[i].count.inactiveValue
          psum += l[i].count.enrollment - l[i].count.absentees
          acsum += l[i].activeSum
          icsum += l[i].inactiveSum
          pcsum += l[i].presentSum
        data.append(ProgramStats(d, percentage(asum+isum, psum),
          percentage(asum, psum), percentage(isum, psum),
          percentage(acsum+icsum, pcsum),
          percentage(acsum, pcsum), percentage(icsum, pcsum)))
      else:
        data.append(ProgramStats(d))
    context["data"] = data
    if lastIndex >= 0:
      context["lastStats"] = context["data"][lastIndex]
    else:
      context["lastStats"] = None
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
    totalEnrollment = sum(c.enrollment for c in classrooms)
    context = { "program": program, "classrooms": classrooms,
      "totalEnrollment": totalEnrollment }
    addProgramData(context, program, classrooms)
    if context["hasData"]:
      # Because we don't allow users to enter counts for dates that
      # are in the future, if hasData is true then there must be a
      # last ProgramStats, but out of an abundance of caution...
      if context["lastStats"] != None:
        context["graphSeries"] = [("Participation", "combinedCumPct")]
      else:
        context["graphSeries"] = []
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
