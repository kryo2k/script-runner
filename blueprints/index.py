"""Main blueprint for interacting with application kernel."""

import os
from flask import Blueprint, render_template
from flask_socketio import emit
from ..extensions import auth, socketio
from ..kernel import thread as kernel_thread

bp = Blueprint("app_index", __name__)

@bp.route("/")
@auth.login_required
def index():
	"""Main UI."""
	return render_template('index.html', page_title=os.getenv('INDEX_TITLE', 'Home'))

@kernel_thread.on('execute')
def kernelExecute():
	"""Event called when kernel execute is triggered."""
	socketio.emit('disable_action', 'execute')
	socketio.emit('enable_action', 'interrupt')

@kernel_thread.on('after-process')
@kernel_thread.on('interrupted')
def kernelAfterProcess():
	"""Event called after kernel execute is finished or interrupted."""
	socketio.emit('enable_action', 'execute')
	socketio.emit('disable_action', 'interrupt')

@kernel_thread.on('buffer-line')
def kernelBufferLine(buffer, line):
	"""Event called after a line is added to stdout or stderr."""
	if buffer == 1:
		socketio.emit('stdout_write', line)
	elif buffer == 2:
		socketio.emit('stderr_write', line)

@kernel_thread.on('exception')
def kernelException(ex):
	"""Event called when an exception happens."""
	print(f'Exception: {ex}')

@socketio.on('connect')
def client_connect(_auth):
	"""Event called when client connects via socket.io"""
	# TODO: work in some kind of authentication.
	emit('stdout_reset')
	emit('stdout_write', kernel_thread.stdout)
	emit('stderr_reset')
	emit('stderr_write', kernel_thread.stderr)
	emit('update_actions', [
		['execute',   {
			'caption': 'Execute',
			'disabled': kernel_thread.busy,
			'style': 'success',
			'icon' : 'bolt'
		} ],
		['interrupt', {
			'caption': 'Interrupt',
			'disabled': not kernel_thread.busy,
			'style': 'danger',
			'icon' : 'hand'
		} ]
	])

# @socketio.on('disconnect')
# def client_disconnect():
# 	pass

@socketio.on('button_click')
def client_button_click(action_code):
	"""Event called when button_click message is received."""
	if action_code == 'execute':
		kernel_thread.execute()
	elif action_code == 'interrupt':
		kernel_thread.interrupt()