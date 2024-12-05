"""All extensions required for application functionality."""

import os
from flask import render_template
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO

class SimpleAuthFile:
	"""Object representing a file used for authentication checks."""
	def __init__(self, path):
		self._path = path
	@property
	def path(self):
		"""Returns configured path of file."""
		return self._path
	def authenticate(self, username, password):
		"""Attempts to authenticate username and password against file."""
		try:
			with open(self._path, 'r', encoding="utf-8") as f:
				for line in f:
					stored_username, stored_password = line.strip().split(':')
					if stored_username == username and stored_password == password:
						return True
				return False
		except FileNotFoundError:
			pass
		return False

auth = HTTPBasicAuth()
auth_enabled = int(os.getenv('AUTH_ENABLED','1')) == 1
auth_file = SimpleAuthFile(os.getenv('AUTH_FILE','.script-runner-auth'))
socketio = SocketIO(cors_allowed_origins='*')

@auth.verify_password
def verify_password(username, password):
	"""Method  to check a username and password for validity."""
	if not auth_enabled or auth_file.authenticate(username, password):
		return (username, password)
	return None

@auth.error_handler
def unauthorized():
	"""Endpoint to send users which are unauthorized to."""
	return render_template('unauthorized.html')
