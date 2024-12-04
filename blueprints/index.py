import os
from flask import Blueprint, request, send_file, render_template
from flask_socketio import emit
from ..extensions import auth, socketio
from ..kernel import thread as kernel_thread

bp = Blueprint("app_index", __name__)

@bp.route("/")
@auth.login_required
def index():
	return render_template('index.html', page_title=os.getenv('INDEX_TITLE', 'Home'))

@kernel_thread.on('execute')
def kernelExecute():
	socketio.emit('disable_action', 'execute')
	socketio.emit('enable_action', 'interrupt')

@kernel_thread.on('before-process')
def kernelBeforeProcess():
	pass

@kernel_thread.on('after-process')
@kernel_thread.on('interrupted')
def kernelAfterProcess():
	socketio.emit('enable_action', 'execute')
	socketio.emit('disable_action', 'interrupt')

@kernel_thread.on('buffer-line')
def kernelBufferLine(buffer, line):
	if buffer == 1:
		socketio.emit('stdout_write', line)
	elif buffer == 2:
		socketio.emit('stderr_write', line)

@kernel_thread.on('exception')
def kernelException(ex):
	print(f'Exception', ex)

@socketio.on('connect')
def client_connect(auth):
	# TODO: work in some kind of authentication.
	emit('stdout_reset')
	emit('stdout_write', kernel_thread.stdout)
	emit('stderr_reset')
	emit('stderr_write', kernel_thread.stderr)
	emit('update_actions', [
		['execute',   { 'caption': 'Execute', 'disabled': kernel_thread.busy, 'style': 'success', 'icon' : 'bolt' } ],
		['interrupt', { 'caption': 'Interrupt', 'disabled': not kernel_thread.busy, 'style': 'danger', 'icon' : 'hand' } ]
	])

@socketio.on('disconnect')
def client_disconnect():
	pass

@socketio.on('button_click')
def client_button_click(action_code):
	if action_code == 'execute':
		kernel_thread.execute()
	elif action_code == 'interrupt':
		kernel_thread.interrupt()