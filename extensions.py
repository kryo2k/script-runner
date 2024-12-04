import os
from flask import render_template
from flask_httpauth import HTTPBasicAuth
from flask_socketio import SocketIO

class SimpleAuthFile:
	def __init__(self, path):
		self._path = path
	@property
	def path(self):
		return self._path
	def authenticate(self, username, password):
		try:
			with open(self._path, 'r') as f:
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
	if not auth_enabled or auth_file.authenticate(username, password):
		return (username, password)
	return None

@auth.error_handler
def unauthorized():
	return render_template('unauthorized.html')