import subprocess
import os
import re
import time
import logging
import threading
import datetime
import shutil
import signal
from csurUpdateUtils import (TimedProcessThread, TimerThread)
from fusionIOUtils import removeFusionIOPackages
from fusionIOUpdate import (FusionIODriverUpdate, FusionIOFirmwareUpdate)


'''
This class is used to update computeNodes as well as other nodes, e.g. NFS nodes.
'''
class ComputeNodeUpdate:

	def __init__(self, cursesThread, csurResourceDict, timerThreadLocation):
		self.cursesThread = cursesThread

		self.timerThreadLocation = timerThreadLocation

		self.csurResourceDict = csurResourceDict
		self.computeNodeDict = self.csurResourceDict['componentListDict']['computeNodeList'][0].getComputeNodeDict()
		self.componentUpdateDict = self.computeNodeDict['componentUpdateDict']

		self.updateComponentProblemDict = {'Firmware' : {}, 'Drivers' : {}, 'Software' : {}}

		self.csurBasePath = self.csurResourceDict['csurBasePath']

		self.logger = logging.getLogger(self.computeNodeDict['loggerName'])

		self.timedProcessThread = ''

                self.pid = 0

		self.wait = False
		self.cancel = False

		'''
		These are used to check first if a FusionIO dirver or firmware update is taking place.
		If so we get the current update PID from the fusionIODriverUpdate or fusionIOFirmareUpdate instance.
		'''	
		self.fusionIODriverUpdateStarted = False
		self.fusionIOFirmwareUpdateStarted = False

		#This is the update instance used when a FusionIO driver update is needed.
		self.fusionIODriverUpdate = ''

		#This is the list that holds the threads used when a FusionIO firmware update is needed.
		self.fusionIOFirmwareUpdateThreadList = []


	#End __init__(self, computeNodeDict, componentUpdateDict, csurResourceDict):


	'''
	This function updates the system components that were identified as needing to be updated.
	The software update is done last because it has some dependencies on software installed
	with the drivers, e.g. fio-snmp-agentx software depends on fio-common, which is part of 
	the driver software.
	Also, drivers are updated before firmware due to dependencies.
	'''
	def updateComputeNodeComponents(self):
		#Run timer thread for feedback during the update.
		timerThread = TimerThread('Updating compute node ' + self.computeNodeDict['ip'] + ' ... ')
		timerThread.daemon = True
		timerThread.start()
		self.cursesThread.insertTimerThread(['', timerThread])

		#We instantiate a class to update the FusionIO components.
		if 'iomemory_vsl' in self.componentUpdateDict['Drivers']:
			self.fusionIODriverUpdate = FusionIODriverUpdate()

		if len(self.componentUpdateDict['Drivers']) != 0:
			self.__updateDrivers()

		if len(self.componentUpdateDict['Firmware']) != 0 and not self.cancel:
			self.__updateFirmware()

		if len(self.componentUpdateDict['Software']) != 0 and not self.cancel:
			self.__updateSoftware()

		timerThread.stopTimer()
		timerThread.join()
		self.cursesThread.updateTimerThread('Done updating compute node ' + self.computeNodeDict['ip'] + '.', self.timerThreadLocation)

	#End updateComputeNodeComponents(self):


	def __updateSoftware(self):
		softwareDir = self.csurBasePath + '/software/computeNode/'
		softwareDict = self.componentUpdateDict['Software']
		osDistLevel = self.computeNodeDict['osDistLevel']

		self.logger.info("Updating the software that was identified as needing to be updated.")

		for software in softwareDict:
			#A second pause between each package update to help avoid any timing issues which may arise.
			time.sleep(2)			

			#This pauses the updates during a keyboard interruption.
			while(self.wait):
				time.sleep(1)

			#Cancel the update if the user requested to end the program.
			if self.cancel:
				return

			'''
			Need to remove hponcfg first on RHEL systems if it is installed due to a package
			version mis-match causing a conflict during installation and subsequently an installation failure.
			'''
			if software == "hponcfg" and re.match("RHEL6.*", osDistLevel):
				#First make sure it is already installed before trying to remove it.
				command = "rpm -q hponcfg"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to check if hponcfg is installed was: " + out.strip())
				
                                if result.returncode == 0:
					#Found multiple instances of hponcfg installed; thus converting the returned results to a string for removal.
					out = out.splitlines()
					command = "rpm -e " + ' '.join(out)
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					self.logger.debug("The output of the command (" + command + ") used to remove hponcfg was: " + out.strip())

					if result.returncode != 0:
						self.logger.error("Problems were encountered while trying to remove hponcfg; skipping update.\n" + err)
						self.updateComponentProblemDict['Software'][software] = ''
						continue

			#hp-health needs to be stopped first since it has been known to cause installation problems.
			if software == "hp-health":
				#First make sure it is already installed before trying to stop it.
				command = "rpm -q hp-health"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()
				
				self.logger.debug("The output of the command (" + command + ") used to check if hp-health is installed was: " + out.strip())

				#This means hp-health is installed.
                                if result.returncode == 0:
					command = "/etc/init.d/hp-health stop"

					#Spend up to two minutes trying to stop hp-health
					self.timedProcessThread = TimedProcessThread(command, 120, self.computeNodeDict['loggerName'])
					self.timedProcessThread.start()
					self.pid = self.timedProcessThread.getProcessPID()
				
					statusList = self.timedProcessThread.getCompletionStatus()

					status = statusList[0]

					#Reset self.pid back to zero, since an active process is not running.
					self.pid = 0

					if status == 'timedOut':
						self.logger.error("hp-health could not be stopped; will try to kill it now.")

						#This will return the process ID of hpasmlited.
						command = "pgrep -x hpasmlited"
						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()

						self.logger.debug("The output of the command (" + command + ") used to get the PID of hp-health was: " + out.strip())
						
						#The result should be 0 unless it just stopped suddenly.
						if result.returncode == 0:
							hpHealthPID = out.strip()
							command = "kill -9 " + hpHealthPID
							#Spend up to two more minutes trying to stop hp-health
							self.timedProcessThread = TimedProcessThread(command, 120, self.computeNodeDict['loggerName'])
							self.timedProcessThread.start()
							self.pid = self.timedProcessThread.getProcessPID()
							status = self.timedProcessThread.getCompletionStatus()

							self.pid = 0

							if status == "timedOut":
								self.logger.error("A second attempt to stop hp-health timed out; skipping update of hp-health.")
								self.updateComponentProblemDict['Software'][software] = ''
								continue
					elif status == 'Failed':
						self.logger.error("An error was encountered while trying to stop hp-health; skipping update of hp-health.\n" + statusList[1])
						self.updateComponentProblemDict['Software'][software] = ''
						continue

			'''
			Before FusionIO software is updated the old packages are removed.  Also, since there are a set of packages to 
			install we need to add the softwareDir to each package.
			'''
			if software == 'FusionIO':
				if not removeFusionIOPackages(self.csurResourceDict['fusionIOSoftwareRemovalPackageList'], 'software', self.computeNodeDict['loggerName']):
					self.logger.error("The FusionIO software could not be removed before updating/re-installing; skipping update of FusionIO software.")
					self.updateComponentProblemDict['Software'][software] = ''
					continue

				softwarePackage = softwareDir + re.sub(' ', ' ' + softwareDir, softwareDict[software])
			else:
				softwarePackage = softwareDir + softwareDict[software]

			#This command will update/install the software RPM and set its version to the CSUR version.
			command = "rpm -U --quiet --oldpackage --replacepkgs --nosignature " + softwarePackage

                        '''
                        Need to do this with a thread, since a defunct process causes a hang situation.
                        The thread is given two minutes for each rpm, which should be sufficient.
                        Also, we set the thread to be a daemon thread so that the program can still exit
                        at which time the thread should exit and it appears that the RPM defunct processes
                        also go away as well.
			'''

                        self.timedProcessThread = TimedProcessThread(command, 120, self.computeNodeDict['loggerName'])
			self.timedProcessThread.setDaemon(True)
                        self.timedProcessThread.start()
			self.pid = self.timedProcessThread.getProcessPID()

                        status = self.timedProcessThread.getCompletionStatus()

			self.pid = 0

			'''
			This transforms the variable software from FusionIO to a list of the of FusionIO package names 
			for verification purposes, since FusionIO is not a recognized package name when running rpm -V.	
			'''
			if software == 'FusionIO':
				fusionIOSoftwarePkgList = softwareDict[software].split()
	
				packageNames = ''

				for package in fusionIOSoftwarePkgList:
					packageNames += re.sub('-[0-9]{1}.*', '', package) + " "
					
				packageNames = packageNames.strip()

                        if status[0] == 'timedOut':
                                '''
                                Let's verify whether or not the RPM was successfully installed, since it appears that
                                a defunct RPM process will cause a timeout to occur, yet the RPM installed successfully.
                                '''

				if software == 'FusionIO':
                                	self.logger.info("Verifying the installation status of " + packageNames + ", since it appears it may not of installed correctly." )
                                	command = "rpm -V --nomtime " + packageNames
				else:
                                	self.logger.info("Verifying the installation status of " + software + ", since it appears it may not of installed correctly." )
                                	command = "rpm -V --nomtime " + software

                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

				if software == 'FusionIO':
					self.logger.debug("The output of the command (" + command + ") used to verify the installation status of " + packageNames + "  was: " + out.strip())
				else:
					self.logger.debug("The output of the command (" + command + ") used to verify the installation status of " + software + "  was: " + out.strip())

                                if result.returncode != 0:
					if software == 'FusionIO':
                                        	self.logger.error("Problems were encountered while updating " + packageNames + ".\n" + err)
					else:
                                        	self.logger.error("Problems were encountered while updating " + software + ".\n" + err)

					self.updateComponentProblemDict['Software'][software] = ''
                        elif status[0] != "Succeeded":
				if software == 'FusionIO':
					self.logger.error("Problems were encountered while updating " + packageNames + ".\n" + err)
				else:
                                	self.logger.error("Problems were encountered while updating " + software + ".\n" + status[1])

				self.updateComponentProblemDict['Software'][software] = ''

		self.logger.info("Done updating the software that was identified as needing to be updated.")

	#End __updateSoftware(self)


	'''
	This function is used to update the drivers that were identified as needing to be updated.
	'''
	def __updateDrivers(self):
		driverDir = self.csurBasePath + '/drivers/computeNode/'
		driverDict = self.componentUpdateDict['Drivers']
		systemModel = self.computeNodeDict['systemModel']
		osDistLevel = self.computeNodeDict['osDistLevel']

		self.logger.info("Updating the drivers that were identified as needing to be updated.")

		for driver in driverDict:
			time.sleep(2)			

			#This pauses the updates during a keyboard interruption.
			while(self.wait):
				time.sleep(1)

			#Cancel the update if the user requested to end the program.
			if self.cancel:
				return

			#Make sure self.pid is set to 0 for each iteration.
			self.pid = 0

			'''
			nx_nic and be2net driver has to be removed first if it is an old driver, since the packages have been renamed.
			Thus, we first check to see if new version is installed and if not this implies the old driver is present,
			which we then remove.
			'''
			if driver == "nx_nic" and ((systemModel == 'DL580G7') or (systemModel == 'DL980G7')):
				command = "rpm -qa|grep ^hpqlgc-nx"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to check if the new nx_nic driver is installed was: " + out.strip())

				if result.returncode != 0:
					command = "rpm -e hp-nx_nic-kmp-default hp-nx_nic-tools"
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					self.logger.debug("The output of the command (" + command + ") used to remove the nx_nic driver was: " + out.strip())

					if result.returncode != 0:
						self.logger.error("Problems were encountered while trying to remove hp-nx_nic-kmp-default and hp-nx_nic-tools; skipping update.\n" + err)
						self.updateComponentProblemDict['Drivers'][driver] = ''
						continue

			if driver == "be2net":
				command = "rpm -q hp-be2net-kmp-default"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to check if the old be2net driver is installed was: " + out.strip())

				if result.returncode == 0:
					command = "rpm -e hp-be2net-kmp-default"
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					self.logger.debug("The output of the command (" + command + ") used to remove the be2net driver was: " + out.strip())

					if result.returncode != 0:
						self.logger.error("Problems were encountered while trying to remove hp-be2net-kmp-default; skipping update.\n" + err)
						self.updateComponentProblemDict['Drivers'][driver] = ''
						continue

                        '''
			This was added for CS500 Haswell.
                        Before the Mellanox driver can be updated we need to remove some RPMs that conflict with the change.
                        '''
                        if driver == 'mlx4_en':
				mellanoxPackageList = ['mlnx-en-kmp-default', 'mlnx-en-utils', 'libmlx4-rdmav2', 'libmlx4', 'libibverbs', 'libibverbs1', 'librdmacm', 'libmthca-rdmav2', 'libibcm']
                                mellanoxRemovalList = []

                                #Before trying to remove a package we need to see if it is present.
                                for package in mellanoxPackageList:
                                        command = "rpm -q " + package + " > /dev/null 2>&1"
                                        result = subprocess.call(command, shell=True)

                                        if result == 0:
                                                mellanoxRemovalList.append(package)

                                #Now remove any of the packages that were present.
                                if len(mellanoxRemovalList) > 0:
                                        packages = " ".join(mellanoxRemovalList)

                                        command = "rpm -e " + packages

                                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                        out, err = result.communicate()

					self.logger.debug("The output of the command (" + command + ") used to remove the Mellanox conflicting RPMs was: " + out.strip())

                                        if result.returncode != 0:
						self.logger.error("Problems were encountered while trying to remove the Mellanox conflicting RPMs; skipping update.\n" + err)
						self.updateComponentProblemDict['Drivers'][driver] = ''
						continue

			if driver == 'iomemory_vsl':
				#Make a backup of /etc/sysconfig/iomemory-vsl, which will be restored during the post update.
				dateTimestamp = (datetime.datetime.now()).strftime('%Y%m%d%H%M%S')

				iomemoryCfgBackup = '/etc/sysconfig/iomemory-vsl.' + dateTimestamp

				try:
					shutil.copy2('/etc/sysconfig/iomemory-vsl', iomemoryCfgBackup)
				except IOError as err:
					self.logger.error("Unable to make a backup of the system's iomemory-vsl configuration file.\n" + str(err))
					self.updateComponentProblemDict['Drivers'][driver] = ''

				if not removeFusionIOPackages(self.csurResourceDict['fusionIODriverRemovalPackageList'], 'driver', self.computeNodeDict['loggerName'], kernel=self.computeNodeDict['kernel']):
					self.logger.error("The FusionIO driver packages could not be removed before building/re-installing the FusionIO driver; skipping update of FusionIO driver.")
					self.updateComponentProblemDict['Drivers'][driver] = ''
					continue
			
			#Driver dependencies are seperated by a ':'.
			if ':' not in driverDict[driver]:
				driverRPMList = driverDir + driverDict[driver]
			else:
				driverRPMsString = driverDict[driver]
				tmpDriverRPMList = driverRPMsString.replace(':', ' ' + driverDir)
				driverRPMList = driverDir + tmpDriverRPMList

			command = "rpm -U --oldpackage --replacepkgs --nosignature " + driverRPMList
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
			self.pid = result.pid
			out, err = result.communicate()

			self.logger.debug("The output of the command (" + command + ") used to update the '" + driver + "' driver was: " + out.strip())

			if result.returncode != 0:
                                self.logger.error("Problems were encountered while updating driver '" + driver + "'.\n" + err)
				self.updateComponentProblemDict['Drivers'][driver] = ''
				continue

			if driver == 'iomemory_vsl':
				self.fusionIODriverUpdateStarted = True

				if not self.fusionIODriverUpdate.buildInstallFusionIODriver(self.csurResourceDict.copy(), driverDir, self.computeNodeDict['loggerName']):
					self.logger.error("Problems were encountered while building and installing the FusionIO driver.")
					self.updateComponentProblemDict['Drivers'][driver] = ''
			
				self.fusionIODriverUpdateStarted = False

				#Restore the original FusionIO configuration file.
				try:
					shutil.copy2(iomemoryCfgBackup, '/etc/sysconfig/iomemory-vsl')
				except IOError as err:
					self.logger.error("Failed to restore the system's iomemory-vsl configuration file.\n" + str(err))
					self.updateComponentProblemDict['Drivers'][driver] = ''

		self.logger.info("Done updating the drivers that were identified as needing to be updated.")

	#End __updateDrivers(self)


	'''
        This function is used to update the firmware that were identified as needing to be updated.
        '''
	def __updateFirmware(self):
                firmwareDir = self.csurBasePath + '/firmware/computeNode/'
                firmwareDict = self.componentUpdateDict['Firmware']

		osDistLevel = self.computeNodeDict['osDistLevel']

		#This reference is used when updating the bios on DL580 Gen8 systems, since the NIC interface names may change.
		biosReference = 'BIOSDL580Gen8'

		#This is for firmware that is installed using a smart component.
		regex = ".*\.scexe"

		#This is for checking NIC cards whose name changes due to a compute node BIOS upgrade to 1.6 or higher.
		nicRegex = 'em49|em50|em51|em52'

                self.logger.info("Updating the firmware that were identified as needing to be updated.")

		#This may not be necessary if not updating NIC cards, but it won't hurt either.
		self.__bringUpNetworks()

		for firmware in firmwareDict:
			time.sleep(2)			

			#This pauses the updates during a keyboard interruption.
			while(self.wait):
				time.sleep(1)

			#Cancel the update if the user requested to end the program.
			if self.cancel:
				return

			#Make sure self.pid is set to 0 for each iteration.
			self.pid = 0

                        if firmware == 'FusionIO':
				'''
				Make sure to stop/unload the driver first if it is running.
				Will still try to continue if the check errors out.
				'''
				command = '/etc/init.d/iomemory-vsl status'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to check if the FusionIO driver is running was: " + out.strip())

				if result.returncode != 0:
					self.logger.error("Problems were detected while checking if the FusionIO driver is running:\n" + err)

				if 'is running' in out:
					command = '/etc/init.d/iomemory-vsl stop'
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
					out, err = result.communicate()

					self.logger.debug("The output of the command (" + command + ") used to stop the FusionIO driver from running was: " + out.strip())

					if result.returncode != 0:
						self.logger.error("Problems were detected while stopping the FusionIO driver from running:\n" + err)

				firmwareImage = firmwareDir + firmwareDict[firmware]

				busList = self.computeNodeDict['busList']

				#This contains a reference to each IODIMM who's update failed.
				fusionIOFirmwareUpdateFailureList = []
	
				'''
				This hold each FusionIOFirmwareUpdate instance so that we can reference the instance to see if it is still
				running and to get the update process PID in case it needs to be killed.
				'''

				self.fusionIOFirmwareUpdateStarted = True
				
				#Create and start the FusionIOFirmwareUpdate threads.
				for bus in busList:
					self.fusionIOFirmwareUpdateThreadList.append(FusionIOFirmwareUpdate(bus, firmwareImage, fusionIOFirmwareUpdateFailureList, self.computeNodeDict['loggerName']))
					self.fusionIOFirmwareUpdateThreadList[-1].start()

				#Wait for threads to finish before continuing.
				while 1:
					time.sleep(1.0)
					for i in range(0, len(self.fusionIOFirmwareUpdateThreadList)):
						#If a thread is no longer alive it is removed from the list.
						if not self.fusionIOFirmwareUpdateThreadList[i].isAlive():
							del self.fusionIOFirmwareUpdateThreadList[i]
							#Break out of the loop if a thread is removed to avoid any side affects due to the list changing.
							break
					
					#Exit the loop once the thread list is empty.
					if len(self.fusionIOFirmwareUpdateThreadList) == 0:
						break

				if len(fusionIOFirmwareUpdateFailureList) > 0:
					self.logger.error("Problems were encountered while updating the FusionIO firmware for the IODIMMS: " + ' '.join(fusionIOFirmwareUpdateFailureList))
					self.updateComponentProblemDict['Firmware'][firmware] = ''

				self.fusionIOFirmwareUpdateStarted = False
			else:
				if re.match(regex, firmwareDict[firmware]):
					os.chdir(firmwareDir)
					command = "./" + firmwareDict[firmware] + " -f -s"
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
					self.pid = result.pid
					out, err = result.communicate()

					self.logger.debug("The output of the command (" + command + ") used to update the firmware " + firmware + " was: " + out.strip())

					self.logger.debug("The return code from the smart component update was: " + str(result.returncode))

					if result.returncode == 3:
						self.logger.error("Problems were encountered while updating firmware " + firmware + ".\n" + err)
						self.updateComponentProblemDict['Firmware'][firmware] = ''
						continue
				else:
					rpm = firmwareDict[firmware]
					command = "rpm -U --oldpackage --replacepkgs --nosignature " + firmwareDir + rpm
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
					self.pid = result.pid
					out, err = result.communicate()
					
					self.logger.debug("The output of the command (" + command + ") used to update the firmware " + firmware + " was: " + out.strip())

					if result.returncode != 0:
						self.logger.error("Problems were encountered while updating firmware " + firmware + ".\n" + err)
						self.updateComponentProblemDict['Firmware'][firmware] = ''
						continue

					'''
					Remove the extension portion of the RPM name.
					Currently firmware RPMs end with x86_64.rpm or i386.rpm.
					'''
					if rpm.endswith("x86_64.rpm"):	
						firmwareRPMDir = '/usr/lib/x86_64-linux-gnu/'
						setupDir = firmwareRPMDir + rpm[0:rpm.index('.x86_64.rpm')]
					else:
						firmwareRPMDir = '/usr/lib/i386-linux-gnu/'
						setupDir = firmwareRPMDir + rpm[0:rpm.index('.i386.rpm')]

					os.chdir(setupDir)
					setupFile = setupDir + "/hpsetup"

					'''
					Need to check setup file, since there is no consistency between RPM images.
					Also, the options seem not to be consistent.  Thus, for Mellanox firmware we 
					do not use the '-f' option.
					hp-firmware-hca-mellanox-vpi-eth-ib-1.0.3-1.1.1.x86_64.rpm
					'''
					if os.path.isfile(setupFile):
						if 'mellanox' in setupDir:
							command = "./hpsetup -s"
						else:
							command = "./hpsetup -f -s"
					else:
						if 'mellanox' in setupDir:
							command = "./.hpsetup -s"
						else:
							command = "./.hpsetup -f -s"

					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setpgrp, shell=True)
					self.pid = result.pid
					out, err = result.communicate()

					self.logger.debug("The output of the command (" + command + ") used to update the firmware " + firmware + " was: " + out.strip())

					self.logger.debug("The return code from the smart component update was: " + str(result.returncode))

					'''
					Linux smart component return codes

					1. Single target servers

					Error level     Meaning

					0               The Smart Component installed successfully.
					1               The Smart Component installed successfully,
							but the system must be restarted.
					2               The installation was not attempted because the required
							hardware was not present, the software was current, or
							there was nothing to install.
					3               The Smart Component failed to install.
							Refer to the log file for more details.
					
					It seems that the return codes are not consistent, since return code 3 was reported for:
					"All selected devices are either up-to-date or have newer versions installed."
					Thus, for return code of 3 we will double check to the reason.
					'''

					if result.returncode == 3:
						if re.search('All selected devices are either up-to-date or have newer versions installed', out, re.MULTILINE|re.DOTALL) == None:
							self.logger.error("Problems were encountered while updating firmware " + firmware + ".\n" + err)
							self.updateComponentProblemDict['Firmware'][firmware] = ''
							continue

			'''
			If updating DL580Gen8 (CS500) BIOS to 1.6 then make the required network configuration changes. 
			This applies to CSUR1506 and above, since em names are changed, e.g. em49 to em0.
			'''
			if firmware == biosReference and re.match("SLES.*", osDistLevel):
				command = "ifconfig -a"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				self.logger.debug("The output of the command (" + command + ") used to get the list of NIC interfaces for checking if renaming is needed as a result of a bios update was: " + out.strip())

				if result.returncode != 0:
					self.logger.error("Problems were encountered while getting the list of NIC interfaces for checking if renaming is needed as a result of a bios update.\n" + err)
					self.updateComponentProblemDict['Firmware'][biosReference] = 'Network name update failure.'
				else:
					if re.search(nicRegex, out, re.MULTILINE|re.DOTALL) != None:
						self.__updateNICConfiguration(biosReference)

                self.logger.info("Done updating the firmware that were identified as needing to be updated.")

	#End __updateFirmware(self)


	'''
	We need to bring up all the NIC cards, since the firmware will not update them if they are down.
	'''
	def __bringUpNetworks(self):
		count = 1
		nicDownList = []

		command = "ip link show"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the information for the NIC cards that are down was: " + out.strip())

		if result.returncode != 0:
			self.logger.error("Problems were encountered while getting the information for the NIC cards that are down.\n" + err)
			return 

		nicDataList = out.splitlines()

		'''
		Get the list of NIC interfaces that are down.  We only look for NICs with biosdevnames, e.g. em, p#p#, since eth 
		naming is no longer used.
		'''
		for data in nicDataList:
			if re.search('DOWN', data):
				match = re.match('[0-9]{1,2}:\s+([e,m,p,[0-9]{1,})', data)
		
				if match != None:
					nicDownList.append(match.group(1))

		#Now bring up the NICs that were down on their own private (single node) network.
		for nic in nicDownList:
			command = "ifconfig " + nic + " 10.1.1." + str(count) + "/32  up"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			self.logger.debug("The output of the command (" + command + ") used to bring up NIC card " + nic + " was: " + out.strip())

			if result.returncode != 0:
				self.logger.error("Problems were encountered while bringing up NIC card " + nic + ".\n" + err)

			count+=1

	#End __bringUpNetworks(self):


	'''
	This function is used to update/rename NIC configuration files on DL580Gen8 systems after a bios update.
	'''
	def __updateNICConfiguration(self, biosReference):
		emDict = {'em49' : 'em0', 'em50' : 'em1', 'em51' : 'em2', 'em52' : 'em3'}

		regex = 'em49|em50|em51|em52'

		#This gets the list of files to check for updating.
		command = 'ls /etc/sysconfig/network/ifcfg-{bond*,em*}'
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		self.logger.debug("The output of the command (" + command + ") used to get the list of network configuration files to update was: " + out.strip())

		if result.returncode != 0:
			self.updateComponentProblemDict['Firmware'][biosReference] = 'Network configuration file update failure.'
			return

		out = out.splitlines()

		for file in out:
			try:
				with open(file) as f:
					nicData = f.read()
			except IOError as err:
				self.logger.error("Problems were encountered while reading network configuration file " + file + ".\n" + str(err))
				self.updateComponentProblemDict['Firmware'][biosReference] = 'Network configuration file update failure.'
				return

			if 'em' in file:
				tmpList = file.split('-')
				newFile = tmpList[0] + '-' + emDict[tmpList[1]]

				command = 'mv ' + file + ' ' + newFile
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if result.returncode != 0:
					self.logger.error("Problems were encountered while updating (moving) the network configuration file " + file + ".\n" + err)
					self.updateComponentProblemDict['Firmware'][biosReference] = 'Network configuration file update failure.'
					return

				continue
			elif re.search(regex, nicData, re.MULTILINE|re.DOTALL) != None:
				nicDataList = nicData.splitlines()

				for em in emDict:
					count = 0

					for data in nicDataList:
						if em in data:
							data = re.sub(em, emDict[em], data)
							nicDataList[count] = data

						count += 1

				try:
					f = open(file, 'w')
					f.write("\n".join(nicDataList))
				except IOError as err:
					self.logger.error("Problems were encountered while writing out the updated network configuration file " + file + ".\n" + str(err))
					self.updateComponentProblemDict['Firmware'][biosReference] = 'Network configuration file update failure.'
					return

				f.close()

	#End __updateNICConfiguration(self, biosReference):


	'''
	This function will attempt to kill the running processes as requested by the user.
	'''
        def endTask(self):
		self.logger.info("The CSUR update was cancelled by the user.")

		if self.fusionIODriverUpdateStarted:
			self.pid = self.fusionIODriverUpdate.getUpdatePID()

		if self.fusionIOFirmwareUpdateStarted:
			for i in range(0, len(self.fusionIOFirmwareUpdateThreadList)):
				pid = self.fusionIOFirmwareUpdateThreadList[i].getUpdatePID()

				try:
					pgid = os.getpgid(pid)
					os.killpg(pgid, signal.SIGKILL)
				except OSError:
					pass
		else:
			if self.pid != 0:
				try:
					pgid = os.getpgid(self.pid)
					os.killpg(pgid, signal.SIGKILL)
				except OSError:
					pass

		#Set self.cancel to True so that the program knows to exit and does not try to continue.
		self.cancel = True

		#Set self.wait back to False so that the program can proceed again (exit wait while loop).
		self.wait = False

        #End endTask(self):


	'''
	This function is used to get the problem dictionary to determine if there were any issues during the update.
	'''
	def getUpdateComponentProblemDict(self):
                return self.updateComponentProblemDict
        #End getUpdateComponentProblemDict(self):

#End class ComputeNodeUpdate:
