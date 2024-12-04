import os
import sys
import subprocess
import time
import getpass
from datetime import datetime
from threading import Thread, Lock
from collections import deque

class EventManager:
	def __init__(self):
		self._handlers = {}
	def register(self, event_name, handler):
		if event_name not in self._handlers:
			self._handlers[event_name] = []
		self._handlers[event_name].append(handler)
	def trigger(self, event_name, *args, **kwargs):
		if event_name in self._handlers:
			for handler in self._handlers[event_name]:
				handler(*args, **kwargs)

class ExecutionThread(Thread):
	def __init__(self, interpreter, script_path, as_user=None):
		super().__init__(target=lambda:self.__threadloop(), daemon=True)
		self._user = as_user if isinstance(as_user, str) else self.__getcurrentuser()
		self._eventManager = EventManager()
		self._interpreter = interpreter
		self._scriptPath = script_path
		self._running = False
		self._interrupted = False
		self._triggerFlag = False
		self._runLock = Lock()
		self._maxBufferSize = 10000
		self._stdout = deque()
		self._stderr = deque()
		self._activeProcess = None
		self._lastExitCode = None
		self._lastExecutedAt = None
		self._lastRunTime = None
	@property
	def needsSudo(self):
		return self._user != self.__getcurrentuser()
	@property
	def user(self):
		return self._user
	@property
	def interpreter(self):
		return self._interpreter
	@property
	def interpreterExists(self):
		return os.path.exists(self._interpreter)
	@property
	def scriptPath(self):
		return self._scriptPath
	@property
	def scriptPathExists(self):
		return os.path.exists(self._scriptPath)
	@property
	def stdout(self):
		return ''.join(self._stdout)
	@property
	def stderr(self):
		return ''.join(self._stderr)
	@property
	def busy(self):
		return self._triggerFlag or self._running
	@property
	def interrupted(self):
		return self._interrupted
	@property
	def lastExecutedAt(self):
		return self._lastExecutedAt
	@property
	def lastRunTime(self):
		return self._lastRunTime
	@property
	def lastExitCode(self):
		return self._lastExitCode
	@property
	def runLock(self):
		return self._runLock
	def __appendBuffer(self, buf, s):
		buf.extend(s)
		while sum(len(chunk) for chunk in buf) > self._maxBufferSize:
			buf.popleft()
	def __appendOut(self, s):
		self.__appendBuffer(self._stdout, s)
	def __appendErr(self, s):
		self.__appendBuffer(self._stderr, s)
	def __getcurrentuser(self):
		return getpass.getuser()
	def __subprocessarguments(self):
		args = []
		if self.needsSudo:
			args.append('sudo')
			args.append('-u')
			args.append(self._user)
		args.append(self._interpreter)
		args.append(self._scriptPath)
		return args
	def __subprocessexecute(self):
		try:
			if self._activeProcess is not None:
				return
			self._eventManager.trigger('before-process')
			process = self._activeProcess = subprocess.Popen(
				self.__subprocessarguments(),
				stdout=subprocess.PIPE,
				stderr=subprocess.PIPE,
				bufsize=1, # Line-buffered
				universal_newlines=True  # Text mode
			)
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
			del self._runtimeStart
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
		def decorator(func):
			self._eventManager.register(event_name, func)
			return func
		return decorator
	def readSourceCode(self):
		try:
			with open(self._scriptPath) as f:
				return f.read()
		except FileNotFoundError:
			return ""
		except Exception as ex:
			print(f'Script source read error: {ex}', file=sys.stderr)
			return ""
	def clearOutputStandard(self):
		self._stdout = b''
	def clearOutputError(self):
		self._stderr = b''
	def clearOutputs(self):
		self.clearOutputStandard()
		self.clearOutputError()
	def execute(self):
		with self._runLock:
			if self.busy: return
			self._runtimeStart = time.time_ns()
			self._lastExecutedAt = datetime.now()
			self._eventManager.trigger('execute')
			self._interrupted = False
			self._triggerFlag = True
	def interrupt(self):
		if not self._triggerFlag:
			return
		elif not self._running:
			self._interrupted = True
			self._triggerFlag = False
			self._eventManager.trigger('interrupted')
			return
		elif self._activeProcess:
			self._interrupted = True
			self._activeProcess.kill()

thread = ExecutionThread(
	os.getenv('EXECUTION_INTEPRETOR','/bin/sh'),
	os.getenv('EXECUTION_SCRIPT',None),
	os.getenv('EXECUTION_USER', None)
)
thread.start()

def init_app(app):
	@app.context_processor
	def globalvariables():
		global thread
		return dict(
			kernel_thread=thread
		)
