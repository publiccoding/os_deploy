import time
import sys
import threading
import logging
import subprocess
import signal
import os
import re


#Colors available to use when printing messages to screen.
YELLOW = '\033[33m'
RED = '\033[31m'
GREEN = '\033[32m'
BLUE = '\033[34m'
PURPLE = '\033[35m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'
RESETCOLORS = '\033[0m'


'''
This is a custom class for handling the signals we want to catch (SIGINT, SIGQUIT).
'''
class SignalHandler:

        def __init__(self, cursesThread):
                self.response = ''
		self.cursesThread = cursesThread
        #End __init__(self):


        '''
        This function is used to warn users of the consequences of interrupting the update process.
        '''
        def signal_handler(self, signum, frame):
	       	regex = r"^(y|n)$"

		self.cursesThread.insertMessage(['error', 'The update should not be interrupted once started, since it could put the system in an unknown state.'])

                while 1:
			self.cursesThread.insertMessage(['info', '    Do you really want to interrupt the update [y|n]: '])

			self.cursesThread.getUserInput(['info', ' '])

			while not self.cursesThread.isUserInputReady():
				time.sleep(0.1)

			self.response = self.cursesThread.getUserResponse().strip()
			self.response = self.response.lower()

                        if not re.match(regex, self.response):
				self.cursesThread.insertMessage(['error', '    A valid response is y|n.  Please try again.'])
                                continue

			break

        #End signal_handler(self, signum, frame):


        '''
        This function is used to get the users response to interrupting the update process.
        '''
        def getResponse(self):
                return self.response
        #End getResponse(self):

#End class SignalHandler:


'''
This class is used to provide feedback in time expired during long running tasks.
The componentValue is the component being updated and componentMessage is the
message that one wants to be displayed.
It also takes a thread event when a timer thread is involved for a process that should 
not be interrupted.
'''
class TimeFeedbackThread(threading.Thread):

        def __init__(self, **kwargs):
                threading.Thread.__init__(self)

                if 'componentMessage' in kwargs:
                        self.componentMessage = kwargs['componentMessage']
                else:
                        self.componentMessage = ''

                if 'componentValue' in kwargs:
                        self.componentValue = kwargs['componentValue']
                else:
                        self.componentValue = ''

                if 'event' in kwargs:
                        self.event = kwargs['event']
                else:
                        self.event = ''

                self.stop = False

        #End __init__(self, **kwargs):

	
	'''
	This fuction prints out the timer message when the thread is in a run state.
	'''
        def run(self):
                i = 0

                if self.event != '':
                        self.event.set()

                while self.stop != True:
                        if self.event != '':
                                self.event.wait()
                        timeStamp = time.strftime("%H:%M:%S", time.gmtime(i))

                        if self.componentValue != '':
                                feedbackMessage = self.componentMessage + " " +  self.componentValue + " .... " + timeStamp
                        else:
                                feedbackMessage = self.componentMessage + " .... " + timeStamp
			
			sys.stdout.write('\r' + feedbackMessage)

                        sys.stdout.flush()

                        time.sleep(1.0)

                        i+=1

        #End run(self):


	'''
	This function cancels the timer.
	'''
        def stopTimer(self):
                self.stop = True
        #End stopTimer(self):


	'''
	This function is used to pause the timer during the time a signal is being handled.
	'''
        def pauseTimer(self):
                self.event.clear()
        #End pauseTimer(self):


	'''
	This function is used to resume the timer after a signal has been handled.
	'''
        def resumeTimer(self):
                self.event.set()
        #End resumeTimer(self):


	'''
	This function is used to update the component message of the current thread.
	'''
	def updateComponentMessage(self, message):
		self.componentMessage = message
	#End updateComponentMessage(self, message)

#End class TimeFeedbackThread(threading.Thread):


class TimedProcessThread(threading.Thread):

        def __init__(self, cmd, seconds, loggerName):
                threading.Thread.__init__(self)
                self.cmd = cmd
                self.seconds = seconds

		'''
		Since a TimedProcessThread can be used for different components we pass in
		a reference to the loggerName that would be associated with the component
		being updated, e.g. computeNodeLogger, sanSwitchLogger, etc.
		'''
		self.loggerName = loggerName

		self.logger = logging.getLogger(self.loggerName)

                self.returncode = 1
                self.done = False
                self.timedOut = False
                self.err = ''
                self.out = ''

		self.pid = 0

        #End  __init__(self, cmd, seconds, loggerName):


        '''
        This function runs the cmd passed in to the constructor and times out
        if not completed in the amount of time passed into the constructor.  If
        a time out occcurs killPorcesses will be called in an attempt to end the running
        process.
        '''
        def run(self):
                result = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, shell=True)
                self.pid = result.pid
                timer = threading.Timer(self.seconds, self.killProcesses, [self.pid])
                try:
                        timer.start()
                        self.out, self.err = result.communicate()
                        self.returncode = result.returncode
                        self.done = True
                finally:
                        timer.cancel()

        #End run(self):


        '''
        This function is used to try and kill the subprocess process group.  It sets self.done to True so that getCompletionStatus()
        can return the timed out status.
        '''
        def killProcesses(self, pid):
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGKILL)
                self.timedOut = True
                self.done = True

        #End killProcesses(self, pid):


        '''
        This function is used to get the status of the subprocess.  Whether it timed out or completed.
        '''
        def getCompletionStatus(self):
                while not self.timedOut and not self.done:
                        time.sleep(2)

		self.logger.debug("The output of the timed process command (" + self.cmd + ") was: " + self.out.strip())

                if self.timedOut:
                        return ["timedOut"]
                elif self.returncode == 0:
                        return ["Succeeded"]
		else:
			return ["Failed", self.err]

        #End getCompletionStatus(self):


	'''
	This function is used to get the process's PID.  It can then be used to kill the process 
	when one selects to exit the program and the process is not yet done.
	'''
	def getProcessPID(self):
		return self.pid
	#End getProcessPID(self):

#End class TimedProcessThread(threading.Thread):


'''
This class is used to handle an exception when an invalid password 
has been provided.
'''
class InvalidPasswordError(Exception):
	def __init__(self, message):
		self.message = message

'''
This class is used to handle an exception when one tries to log into the 
3PAR Service Processor and a session already exists.
'''
class InUseError(Exception):
        def __init__(self, message):
                self.message = message


'''
This class is used to handle an exception when one a specific 
value is being looked for, e.g. when looking for a version, etc.
'''
class CouldNotDetermineError(Exception):
        def __init__(self, message):
                self.message = message


'''
This class is used to handle an exception when one a file  
upload fails.
'''
class FileUploadError(Exception):
        def __init__(self, message):
                self.message = message


class TimerThread(threading.Thread):

        def __init__(self, message):
                threading.Thread.__init__(self)

                self.stop = False
		self.timeStampe = None
		self.message = message

        #End __init__(self):

	
	'''
	This fuction prints out the timer message when the thread is in a run state.
	'''
        def run(self):
                i = 0

                while self.stop != True:
                        self.timeStamp = time.strftime("%H:%M:%S", time.gmtime(i))

                        time.sleep(1.0)
                        i+=1

        #End run(self):


	'''
	This function cancels the timer.
	'''
        def stopTimer(self):
                self.stop = True
        #End stopTimer(self):


	'''
	This function is used to get the current time stamp.
	'''
	def getTimeStamp(self):
		return self.timeStamp
	#End getTimeStamp(self):

	
	'''
	This function is used to get the message associated with the thread. 
	'''
	def getMessage(self):
		return self.message
	#End getMessage(self):


#End class TimerThread(threading.Thread):
