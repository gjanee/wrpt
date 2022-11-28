# Walk & Roll Performance Tracking (WRPT)

WRPT is a web tool for hosting and tracking [Safe Routes to
School](http://www.saferoutesinfo.org) "Walk & Roll" competitions:
friendly events in which grade school classrooms vie, over a series of
event dates, to see which can achieve the highest participation rate
of using alternative/sustainable transportation getting to school.

Using WRPT, an administrator creates a "program" that gives a name to
a competition and enumerates the participating classrooms and event
dates.  An enrollment count is recorded for each classroom so that
participation percentages can be computed.  Then, on each event date,
teachers log in to WRPT and enter the numbers of their children
getting to school actively (walk/bike/scooter/etc), inactively yet
sustainably (carpool/bus), and absent.  The tool tracks classroom
cumulative participation as a percentage of children present (i.e.,
enrollment less absentees).

Such counts could of course be entered on paper forms, or using an
online spreadsheet.  But using this tool is a little more convenient
and structured and makes the competition seem more formal, and it
provides some graphs that show a classroom how it ranks in relation to
others.

A running instance of WRPT can be found at
~~http://<span>ww</span><span>w.coast-walknroll.o</span><span>rg</span>~~,
sponsored by and for the benefit of the Coalition for Sustainable
Transportation (COAST) in Santa Barbara, California.

WRPT is a [Django](https://www.djangoproject.com) application
configured to be run under [Gunicorn](https://gunicorn.org) and hosted
by [Heroku](https://www.heroku.com).  The majority of the
functionality is encapsulated in a reusable Django app; site-specific
details (logos, custom text, etc.) are located in a thin wrapper
around the app.  Resource usage is low enough that the tool can run in
Heroku's free tier.

## Prerequisites

* [Git](https://git-scm.com/)
* [Python](https://www.python.org), version 3.7.2+
* A database, [SQLite](https://www.sqlite.org) or
  [PostgreSQL](https://www.postgresql.org)
* [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli), if
  deploying to Heroku

## Installation

Get the software:

* `git clone <repository-url>` this repository
* `cd wrpt`

Set up a virtual environment:

* `python -m venv venv`
* `source venv/bin/activate` (if using Bash)
* `source venv/bin/activate.csh` (if using Csh)

It will be necessary to activate the virtual environment every time
logging in.  Next, install software dependencies (note the comment in
`requirements.txt` if not using PostgreSQL):

* `pip install -r requirements.txt`

## Files

* `.env` Heroku environment variables (development only)
* `.env.example` example environment variables
* `Procfile` the command Heroku runs
* `coast_wrpt/` site-specific wrapper (and actual Django application)
* `db.sqlite3` if using SQLite, the database
* `manage.py` Django management tool
* `requirements.txt` software dependencies for pip
* `runtime.txt` Python version to run (Heroku production only)
* `staticfiles/` static files delivery directory
* `tools/` handy scripts
* `venv/` virtual environment
* `wrpt/` the main Django app

## Setting up

Set environment variables:

* `cp .env.example .env`

The default environment variables use SQLite and turn debugging on.

Django management commands (e.g., `manage.py migrate`) can be run
directly or they can be run using `heroku local:run` as shown below.
The advantage of the latter is that the environment variables in
`.env` are automatically picked up.  If running directly, environment
variables will need to be set using shell mechanisms.

Create database tables:

* `heroku local:run manage.py migrate`

Create an administrator user:

* `heroku local:run manage.py createadmin`

Populate the `staticfiles` directory:

* `heroku local:run manage.py collectstatic`

Static files will need to be re-collected whenever they change.

## Running locally

The server will appear at http://localhost:5000.

* `heroku local`
* or, `gunicorn -b localhost:5000 coast_wrpt.wsgi` (need to set
  environment variables)

After starting the server, log in as the administator, navigate to the
admin site, and complete the administrator's user record.

## Deploying to Heroku

The procedure for deploying to Heroku is well-described in the Heroku
documentation, and mirrors the preceding.  But for the record the
steps are generally as follows.

Create a Heroku app and attached database:

* `heroku create`
* `heroku addons:create heroku-postgresql:hobby-dev`

Set the application's secret key:

* `heroku config:set SECRET_KEY="$(tools/generate-secret-key)"` (if
  using Bash)

Creating a Heroku app also creates a "heroku" git remote.  Push the
code to Heroku:

* `git push heroku master`

Upon every push Heroku creates or updates the virtual environment (if
necessary), runs the collectstatic command, and attempts to (re)start
the server.  The server will not run initially because the application
configuration is incomplete, but there's no other way to order the
steps; code must be pushed first.  To quiet Heroku, temporarily turn
the dyno off:

* `heroku ps:scale web=0`

Complete the setup similarly as before:

* `heroku run python manage.py migrate`
* `heroku run python manage.py createadmin`

Turn the dyno back on:

* `heroku ps:scale web=1`

## License

This software is distributed under the [GNU General Public
License](http://www.gnu.org/licenses/gpl-2.0.html).
