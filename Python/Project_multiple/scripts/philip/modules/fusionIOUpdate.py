import subprocess
import logging
import re
import os
from threading import Thread


'''
This class is used for updating the FusionIO driver on Gen1.0 Scale-up compute nodes.
'''
class FusionIODriverUpdate:
	def __init__(self):
		self.pid = 0
	#End __init__(self):

	'''
	This function is used to build and install the FusionIO driver.
	It also will install libvsl as well, since it had a dependency on the driver.
	'''
	def buildInstallFusionIODriver(self, csurResourceDict, driverDir, computeNodeLogger):
		#updateStatus is the return variable as well as a control variable for what steps are performed.
		updateStatus = True

		#Ensure self.pid is set to 0 before any work begins.
		self.pid = 0

		logger = logging.getLogger(computeNodeLogger)
		logger.info("Building and installing the FusionIO driver.")
		
		try:
			computeNodeDict = csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()
			fusionIODriverSrcRPM = csurResourceDict['fusionIODriverSrcRPM']
		except KeyError as err:
			logger.error("The resource key (" + str(err) + ") was not present in the csurResourceDict.")
			updateStatus = False

		if updateStatus:
			kernel = computeNodeDict['kernel']
			processorType = computeNodeDict['processorType']

			fusionIODriverSrcRPMPath = driverDir + "src/" + fusionIODriverSrcRPM

			#Build the driver for the new kernel.
			command = "rpmbuild --rebuild " + fusionIODriverSrcRPMPath
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)

			#We get the processes PID in case the process is cancelled and we need to kill the process.
			self.pid = result.pid

			out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used to build the FusionIO driver was: " + out.strip())

			if result.returncode != 0:
				logger.error("Failed to build the FusionIO driver:\n" + err)
				updateStatus = False

		if updateStatus:
			out = out.strip()

			'''
			This strips off iomemory from RPM name, since it will not be needed in the regex match.
			Additionally, the source RPM is renamed to the driver RPM's name, which includes the current 
			kernel and processor type in its name.
			'''
			fusionIODriverRPM = (fusionIODriverSrcRPM.replace('iomemory-vsl', '-vsl-' + kernel)).replace('src', processorType)

			#Compile the regex that will be used to get the driver RPM location.
			fusionIODriverPattern = re.compile('.*Wrote:\s+((/[0-9,a-z,A-Z,_]+)+' + fusionIODriverRPM +')', re.DOTALL)

			logger.debug("The regex used to get the FusionIO driver RPM location was: " + fusionIODriverPattern.pattern)

			driverRPM = re.match(fusionIODriverPattern, out).group(1)

			logger.debug("The FuionIO driver was determined to be: " + driverRPM)

			#Install the FusionIO software and driver.
			command = "rpm -ivh " + driverRPM + ' ' + driverDir + "libvsl-*.rpm"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)

			#We get the processes PID in case the process is cancelled and we need to kill the process.
			self.pid = result.pid

			out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used to install the FusionIO driver was: " + out.strip())

			if result.returncode != 0:
				logger.error("Failed to install the FusionIO driver:\n" + err)
				updateStatus = False

		logger.info("Done building and installing the FusionIO driver.")

		return updateStatus

	#End buildInstallFusionIODriver(self, csurResourceDict, driverDir):


	'''
	This function is used to retrieve the PID of the currently running update.
	'''
	def getUpdatePID(self):
		return self.pid
	#End getUpdatePID(self):

#End class FusionIODriverUpdate:


'''
This class is used for updating the FusionIO firmware on Gen1.0 Scale-up compute nodes.
'''
class FusionIOFirmwareUpdate(Thread):
        def __init__(self, bus, firmwareImage, updateFailureList, computeNodeLogger):
                Thread.__init__(self)

		self.logger = logging.getLogger(computeNodeLogger)

		self.bus = bus
		self.firmwareImage = firmwareImage

		'''
		The thread will append a reference to an IODIMM to the updateFailureList only
		if it fails to update.
		'''
		self.updateFailureList = updateFailureList

		self.pid = 0

        #End __init__(self, bus, firmwareImage, statusDict, computeNodeLogger):


        def run(self):
		self.logger.info("Updating the FusionIO firmware for IODIMM " + self.bus + '.')

		command = "fio-update-iodrive -y -f -s " + self.bus + ' ' + self.firmwareImage
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)

		#We get the processes PID in case the process is cancelled and we need to kill the process.
		self.pid = result.pid

		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to update the FusionIO firmware for IODIMM " + self.bus + " was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Failed to upgrade the FusionIO firmware for IODIMM " + self.bus + ':\n' + err)
			self.updateFailureList.append(self.bus)

		self.logger.info("Done updating the FusionIO firmware for IODIMM " + self.bus + '.')
        #End run(self):


	'''
	This function is used to get the process's PID.  It can then be used to kill the process 
	when one selects to exit the program and the process is not yet done.
	'''
	def getUpdatePID(self):
		return self.pid
	#End getUpdatePID(self):

#End class FusionIOFirmwareUpdate(Thread):
