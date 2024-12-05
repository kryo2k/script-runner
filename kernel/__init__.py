"""Module containing objects and classes related to core Kernel logic."""
import os
import sys
import subprocess
import time
import getpass
from datetime import datetime
from threading import Thread, Lock
from collections import deque

class EventManager:
	"""Holds subscribers of specific event behavior."""
	def __init__(self):
		"""Initializes class"""
		self._handlers = {}
	def register(self, event_name, handler):
		"""Registers a new event handler."""
		if event_name not in self._handlers:
			self._handlers[event_name] = []
		self._handlers[event_name].append(handler)
	def trigger(self, event_name, *args, **kwargs):
		"""Calls all handlers subcribed to an event."""
		if event_name in self._handlers:
			for handler in self._handlers[event_name]:
				handler(*args, **kwargs)

class ExecutionThread(Thread):
	"""Thread object responsible for execution logic."""
	def __init__(self, interpreter, script_path, as_user=None):
		"""Initializes class"""
		super().__init__(target=self.__threadloop, daemon=True)
		self._user = as_user if isinstance(as_user, str) else self.__getcurrentuser()
		self._eventManager = EventManager()
		self._interpreter = interpreter
		self._scriptPath = script_path
		self._running = False
		self._interrupted = False
		self._triggerFlag = False
		self._runLock = Lock()
		self._runtimeStart = None
		self._maxBufferSize = 10000
		self._stdout = deque()
		self._stderr = deque()
		self._activeProcess = None
		self._lastExitCode = None
		self._lastExecutedAt = None
		self._lastRunTime = None
	@property
	def needsSudo(self):
		"""Virtual property which determines if SUDO should be used or not."""
		return self._user != self.__getcurrentuser()
	@property
	def user(self):
		"""User whom task should be executed as."""
		return self._user
	@property
	def interpreter(self):
		"""Interpreter that should be used to execute configured script."""
		return self._interpreter
	@property
	def interpreterExists(self):
		"""Virtual property which determines if interpreter exists or not."""
		return os.path.exists(self._interpreter)
	@property
	def scriptPath(self):
		"""Script path that should be used for execution."""
		return self._scriptPath
	@property
	def scriptPathExists(self):
		"""Virtual property which determines if script path exists or not."""
		return os.path.exists(self._scriptPath)
	@property
	def stdout(self):
		"""Dumps the stdout buffer as a string."""
		return ''.join(self._stdout)
	@property
	def stderr(self):
		"""Dumps the stderr buffer as a string."""
		return ''.join(self._stderr)
	@property
	def busy(self):
		"""Virtual property which determines if kernel thread is busy or not."""
		return self._triggerFlag or self._running
	@property
	def interrupted(self):
		"""Provides access to internal interrupted state."""
		return self._interrupted
	@property
	def lastExecutedAt(self):
		"""Provides access to internal last executed at state."""
		return self._lastExecutedAt
	@property
	def lastRunTime(self):
		"""Provides access to internal last runtime state."""
		return self._lastRunTime
	@property
	def lastExitCode(self):
		"""Provides access to internal last exit code state."""
		return self._lastExitCode
	@property
	def runLock(self):
		"""Provides access to lock used for run flow control."""
		return self._runLock
	def __appendBuffer(self, buf, s):
		"""Internal method for appending to a provided buffer."""
		buf.extend(s)
		while sum(len(chunk) for chunk in buf) > self._maxBufferSize:
			buf.popleft()
	def __appendOut(self, s):
		"""Internal method for appending stdout buffer."""
		self.__appendBuffer(self._stdout, s)
	def __appendErr(self, s):
		"""Internal method for appending stderr buffer."""
		self.__appendBuffer(self._stderr, s)
	def __getcurrentuser(self):
		"""Internal method to get current logged in user."""
		return getpass.getuser()
	def __subprocessarguments(self):
		"""Internal method to generate arguments needed for current settings."""
		args = []
		if self.needsSudo:
			args.append('sudo')
			args.append('-u')
			args.append(self._user)
		args.append(self._interpreter)
		args.append(self._scriptPath)
		return args
	def __subprocessexecute(self):
		"""Internal method execute with current settings."""
		try:
			if self._activeProcess is not None:
				return
			self._eventManager.trigger('before-process')
			with subprocess.Popen(
				self.__subprocessarguments(),
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				bufsize=1, # Line-buffered
				universal_newlines=True  # Text mode
			) as process:
				self._activeProcess = process
				def append_output(pipe, buffer):
					try:
						for line in iter(pipe.readline, ''):
							if buffer == 1:
								self.__appendOut(line)
							elif buffer == 2:
								self.__appendErr(line)
							else: raise KeyError(f'Invalid buffer key ({buffer})')
							self._eventManager.trigger('buffer-line', buffer, line)
					except ValueError:
						pass
					finally:
						pipe.close()
				stdout_thread = Thread(target=append_output, args=(process.stdout, 1))
				stderr_thread = Thread(target=append_output, args=(process.stderr, 2))
				stdout_thread.start()
				stderr_thread.start()
				stdout_thread.join()
				stderr_thread.join()
				self._lastExitCode = process.wait()
		except Exception as ex:
			self._eventManager.trigger('exception', ex)
		finally:
			self._lastRunTime = (time.time_ns() - self._runtimeStart) / (10 ** 9)
			self._runtimeStart = None
			if self._interrupted:
				self._eventManager.trigger('interrupted')
			self._eventManager.trigger('after-process')
			self._activeProcess = None
	def __threadloop(self):
		while True:
			with self._runLock:
				if self._triggerFlag:
					try:
						self._running = True
						self.__subprocessexecute()
					finally:
						self._running = False
						self._triggerFlag = False
			time.sleep(0.1)
	def on(self, event_name):
		"""Decorator function to get access to kernel events."""
		def decorator(func):
			self._eventManager.register(event_name, func)
			return func
		return decorator
	def readSourceCode(self):
		"""Method to dump the configured script's source code."""
		try:
			with open(self._scriptPath, encoding="utf-8") as f:
				return f.read()
		except FileNotFoundError:
			return ""
		except Exception as ex:
			print(f'Script source read error: {ex}', file=sys.stderr)
			return ""
	def clearOutputStandard(self):
		"""Clears the stdout buffer."""
		self._stdout = b''
	def clearOutputError(self):
		"""Clears the stderr buffer."""
		self._stderr = b''
	def clearOutputs(self):
		"""Clears both stderr and stdout buffers."""
		self.clearOutputStandard()
		self.clearOutputError()
	def execute(self):
		"""Signals the thread to execute with current settings."""
		with self._runLock:
			if self.busy:
				return
			self._runtimeStart = time.time_ns()
			self._lastExecutedAt = datetime.now()
			self._eventManager.trigger('execute')
			self._interrupted = False
			self._triggerFlag = True
	def interrupt(self):
		"""Signals the thread to interrupt the current process."""
		if not self._triggerFlag:
			return
		if not self._running:
			self._interrupted = True
			self._triggerFlag = False
			self._eventManager.trigger('interrupted')
			return
		if self._activeProcess:
			self._interrupted = True
			self._activeProcess.kill()

thread = ExecutionThread(
	os.getenv('EXECUTION_INTEPRETOR','/bin/sh'),
	os.getenv('EXECUTION_SCRIPT',None),
	os.getenv('EXECUTION_USER', None)
)
thread.start()

def init_app(app):
	"""Bootstraps the kernel with current flask application."""
	@app.context_processor
	def globalvariables():
		return {
			'kernel_thread' : thread
		}
