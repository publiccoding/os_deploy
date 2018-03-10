import logging
import subprocess
import binascii
import datetime
import os
import signal
import time
import sys
import threading
import re


logger = logging.getLogger("securityPatchLogger")


#Colors used when printing messages to screen.
YELLOW = '\033[1;33m'
RED = '\033[1;31m'
GREEN = '\033[1;32m'
BLUE = '\033[1;34m'
RESETCOLORS = '\033[1;0m'


class TimedProcessThread(threading.Thread):

        def __init__(self, cmd, seconds):
                threading.Thread.__init__(self)
                self.cmd = cmd
                self.seconds = seconds
                self.returncode = 1
                self.done = False
                self.timedOut = False
	'''
	This function runs the cmd passed in to the constructor and times out
	if not completed in the amount of time passed into the constructor.  If
	a time out occcurs killPorcesses will be called in an attempt to end the running
	process.
	'''
        def run(self):
                result = subprocess.Popen(self.cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid, shell=True)
                pid = result.pid
                timer = threading.Timer(self.seconds, self.killProcesses, [pid])
                try:
                        timer.start()
                        result.communicate()
                        self.returncode = result.returncode
                        self.done = True
                finally:
                        timer.cancel()


        '''
        This function is used to try and kill the subprocess process group.  It sets self.done to True so that getCompletionStatus()
        can return the timed out status.
        '''
        def killProcesses(self, pid):
                pgid = os.getpgid(pid)
                os.killpg(pgid, signal.SIGKILL)
                self.timedOut = True
                self.done = True


        '''
        This function is used to get the status of the subprocess.  Whether it timed out or completed.  If it completed before timing out
        then the return code is also returned.
        '''
        def getCompletionStatus(self):

                while not self.timedOut and not self.done:
                        time.sleep(2)

                if self.timedOut:
                        return "timedOut"
                else:
                        return "Completed" + str(self.returncode)

#End TimedProcessThread(threading.Thread):

'''
This function is used to prevent users from interrupting the update process before 
warning them of the consequences.
'''
def signal_handler(signum, frame):
        regex = r"^(y|n)$"

        print spUtils.RED + "\nThe update should not be interrupted once started, since it could put the system in an unknown state.\n" + spUtils.RESETCOLORS

        while True:
                response = raw_input("Do you really want to interrupt the update [y|n]: ")

                if not re.match(regex, response):
                        print "A valid response is y|n.  Please try again."
                        continue
                elif(response == 'y'):
                        exit(1)
                else:
                        return
#End signal_handler(signum, frame):
