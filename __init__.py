"""Main entry point module for flask."""

import os
from datetime import date, time, datetime
from pytz import timezone
from flask import Flask, request
from babel import Locale
from babel.dates import format_date, format_datetime, format_time
from babel.numbers import format_number, format_decimal, format_percent

from . import blueprints, kernel
from .extensions import auth, socketio

locale = Locale.parse(os.getenv('LOCALE','en_US'))
tz = timezone(os.getenv('TIMEZONE','US/Eastern'))
app = Flask(__name__)
blueprints.init_app(app)
kernel.init_app(app)
socketio.init_app(app)

@app.template_filter()
def fmtdatetime(value, format='medium'):
	"""Jinja2 template function to format datetime.datetime objects."""
	if not isinstance(value, datetime):
		return '--'
	return format_datetime(value.astimezone(tz), format, locale=locale)

@app.template_filter()
def fmtdate(value, format='medium'):
	"""Jinja2 template function to format datetime.date objects."""
	if not isinstance(value, date):
		return '--'
	return format_date(value, format, locale=locale)

@app.template_filter()
def fmttime(value, format='medium'):
	"""Jinja2 template function to format datetime.time objects."""
	if not isinstance(value, time):
		return '--'
	return format_time(value, format, locale=locale)

@app.template_filter()
def fmtbool(value):
	"""Jinja2 template function to format boolean objects."""
	if not isinstance(value, bool):
		return '--'
	return 'Yes' if value else 'No'

@app.template_filter()
def fmtint(value):
	"""Jinja2 template function to format integer objects."""
	if not isinstance(value, int):
		return '--'
	return format_number(value)

@app.template_filter()
def fmtfloat(value):
	"""Jinja2 template function to format float objects."""
	if not isinstance(value, float):
		return '--'
	return format_decimal(value)

@app.template_filter()
def fmtstr(value):
	"""Jinja2 template function to format string objects."""
	if not isinstance(value, str):
		return '--'
	return value