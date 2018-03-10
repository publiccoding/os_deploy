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


logger = logging.getLogger("firmwareDriverLogger")


#Colors used when printing messages to screen.
YELLOW = '\033[1;33m'
RED = '\033[1;31m'
GREEN = '\033[1;32m'
BLUE = '\033[1;34m'
RESETCOLORS = '\033[1;0m'


def getPackageDict(updateList, csurData, type, *args):
        updateImageDict = {}
	packageDict = {}
 	started = False
	found = False
	OSDistLevel = 'None'
	systemModel = 'None'
	
	if len(args) != 0:
		OSDistLevel = args[0]
		systemModel = args[1]

        logger.info("Begin Getting Package List")
        logger.debug("updateList = " + ":".join(updateList))

	regex1 = '^' + type + '\s*'
	regex2 = ".*" + OSDistLevel + ".*" + systemModel + ".*"

	for data in csurData:
		if not re.match(regex1, data) and not started:
			continue
		elif re.match(regex1, data):
			started = True
			continue
		elif not re.match(regex2, data) and not found and (type != "Firmware"):
			continue
		elif re.match(regex2, data):
			found = True
			continue
		elif re.match(r'\s*$', data):
			break
		else:
			packageList = data.split('|')
			if type != "Software":
				if packageList[0].strip() != "FusionIO":
					packageDict[packageList[0].strip()] = packageList[2].strip()
			else:
				packageDict[packageList[0].strip()] = packageList[3].strip()

        for name in updateList:
		if packageDict.has_key(name):
			#We don't add duplicate update images, since some components use the same image for updating.
			dictValues = '-'.join(updateImageDict.values())
			if not packageDict[name] in dictValues:
                		updateImageDict[name] = packageDict[name]

        logger.debug("updateImageDict = " + str(updateImageDict))
        logger.info("End Getting Package List")

        return updateImageDict
#End getPackageDict(updateList, csurData, type, *args)


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
