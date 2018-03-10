import subprocess
import csurUtils
import os
import re
import time
import logging


logger = logging.getLogger("firmwareDriverLogger")


class ComputeNodeUpdate():

	def __init__(self, csurDirectory):
		self.installSoftwareProblemDict = {}
		self.installDriverProblemDict = {}
		self.installFirmwareProblemDict = {}

		self.updateSoftwareDict = {}
		self.updateDriverDict = {}
		self.updateFirmwareDict = {}

		self.csurDirectory = csurDirectory


	def updateSoftware(self, softwareToUpdate, softwareDict, OSDistLevel):
		self.updateSoftwareDict = softwareDict
		softwareDir = self.csurDirectory + 'software/' + OSDistLevel + '/'

		logger.info("Begin Updating software.")
		logger.debug("softwareDict = " + str(softwareDict))

		for software in softwareToUpdate:
			time.sleep(5)			
			logger.info("Updating package " + software)

			#Need to remove hponcfg first on RHEL systems due to package version mis-match causing installtion file conflicts.
			if software == "hponcfg" and re.match("RHEL6.*", OSDistLevel):
				#First make sure it is already installed
				command = "rpm -q hponcfg"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()
				
                                if result.returncode == 0:
					logger.info("Removing hponcfg, since this server is installed with RHEL and updating hponcfg will fail otherwise.")
					command = "rpm -e hponcfg"
					result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
					out, err = result.communicate()

					if result.returncode != 0:
						logger.error(err)
						logger.error("stdout = " + out)
						self.installSoftwareProblemDict[software] = ''
						continue

			#hp-health needs to be stopped first since it has been known to cause installtion problems.
			if software == "hp-health":
				#First make sure it is already installed
				command = "rpm -q hp-health"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()
				
				#This means hp-health is installed.
                                if result.returncode == 0:
					command = "/etc/init.d/hp-health stop"

					#Spend up to two minutes trying to stop hp-health
					timedProcessThread = csurUtils.TimedProcessThread(command, 120)
					timedProcessThread.start()
					status = timedProcessThread.getCompletionStatus()

					if status == "timedOut":
						logger.error("hp-health could not be stopped; will try to kill it now.")

						command = "pgrep -x hpasmlited"
						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()
						
						#The result should be 0 unless it just stopped suddenly.
						if result.returncode == 0:
							hpHealthPID = out.strip()
							command = "kill -9 " + hpHealthPID
							#Spend up to two more minutes trying to stop hp-health
							timedProcessThread = csurUtils.TimedProcessThread(command, 120)
							timedProcessThread.start()
							status = timedProcessThread.getCompletionStatus()

							if status == "timedOut":
								logger.error("hp-health could not be stopped; skipping update of hp-health.")
								self.installSoftwareProblemDict[software] = ''
								continue

			command = "rpm -U --quiet --oldpackage --replacepkgs --nosignature " + softwareDir + softwareDict[software]

			'''
			Need to do this with a thread, since a defunct process causes a hang situation.
			The thread is given two minutes for each rpm, which should be sufficient.
			'''
			timedProcessThread = csurUtils.TimedProcessThread(command, 120)
			timedProcessThread.start()
			status = timedProcessThread.getCompletionStatus()
	
			if status == "timedOut":
				logger.error("Problems were encountered updating " + software)
				self.installSoftwareProblemDict[software] = ''

		if len(self.installSoftwareProblemDict) != 0:
			logger.warn("Sotware update appears to have failed.")
			logger.info("End Updating software.")
		else:
			logger.info("Sotware update completed successfully.")
			logger.info("End Updating software.")
	#End updateSoftware(softwareList)


	def updateDrivers(self, driverDict, OSDistLevel, systemModel):
		self.updateDriverDict = driverDict
		driverDir = self.csurDirectory + 'drivers/' + OSDistLevel + '/'

		logger.info("Begin Updating drivers.")
		logger.debug("driverDict = " + str(driverDict))

		for driverKey in driverDict:
			time.sleep(2)			
			logger.info("Updating driver " + driverKey)
			
			driverRPM = driverDir + driverDict[driverKey]

			command = "rpm -U --oldpackage --replacepkgs --nosignature " + driverRPM
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			logger.debug("out = " + out)

			if result.returncode != 0:
				logger.error(err)
				logger.error("stdout = " + out)
				self.installDriverProblemDict[driverKey] = ''

		if len(self.installDriverProblemDict) != 0:
			logger.warn("Driver update appears to have failed.")
			logger.info("End Updating drivers.")
		else:
			logger.info("Driver update completed successfully.")
			logger.info("End Updating drivers.")
	#End updateDrivers(self, driverDict, OSDistLevel, systemModel)


	def updateFirmware(self, firmwareDict, OSDistLevel):
		self.updateFirmwareDict = firmwareDict

		firmwareDir = self.csurDirectory + 'firmware/'

		#This is for firmware that is installed using a smart component.
		regex = ".*\.scexe"

		#This would be part of the error message if already installed.
		message = "is already installed"

		logger.info("Begin Updating firmware.")
		logger.debug("firmwareDict = " + str(firmwareDict))

		#This may not be necessary if not updating NIC cards, but it won't hurt either.
		self.bringUpNetworks()

		for firmwareKey in firmwareDict:
			time.sleep(2)			

			'''
			If updating DL580Gen8 (CS500)BIOS to 1.6 make required network configuration changes. 
			This applies to CSUR1506.
			'''
			if firmwareKey == "BIOSDL580Gen8" and re.match("SLES.*", OSDistLevel) and re.match(".*p79-1.60", firmwareDict[firmwareKey]):
				command = "updateNetworkCFGFiles.pl"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

                                if err != '':
                                        logger.error(err)

			if re.match(regex, firmwareDict[firmwareKey]):
				os.chdir(firmwareDir)
				command = "./" + firmwareDict[firmwareKey] + " -f -s"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					logger.error(err)
				logger.debug("out = " + out)

				if result.returncode == 3:
					logger.error("stdout = " + out)
					self.installFirmwareProblemDict[firmwareKey] = ''
			else:
				rpm = firmwareDict[firmwareKey]
				command = "rpm -U --oldpackage --nosignature " + firmwareDir + rpm
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()
				
				if err != '' or result.returncode == 1:
					if err == '':
						logger.error("stdout = " + out)
						self.installFirmwareProblemDict[firmwareKey] = ''
						continue
					else:
						if not err.find(message):
							logger.error(err)
							self.installFirmwareProblemDict[firmwareKey] = ''
							continue

				'''
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
                                '''
                                if os.path.isfile(setupFile):
                                        command = "./hpsetup -f -s"
                                else:
                                        command = "./.hpsetup -f -s"

				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if result.returncode == 3:
					logger.error("stdout = " + out)
					self.installFirmwareProblemDict[firmwareKey] = ''

		if len(self.installFirmwareProblemDict) != 0:
			logger.warn("Firmware update appears to have failed.")
			logger.info("End Updating firmware.")
		else:
			logger.info("Firmware update completed successfully.")
			logger.info("End Updating firmware.")
	#End updateFirmware(firmwareDict)


	'''
	We need to bring up all the NIC cards, since the firmware will not update them if they are down.
	'''
	def bringUpNetworks(self):
		count = 1

		command = "ip link show|egrep -i \".*<BROADCAST,MULTICAST>.*DOWN.*\"|awk '{sub(/:$/, \"\", $2);print $2}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		nicList = out.splitlines()

		for nic in nicList:
			command = "ifconfig " + nic + " 10.1.1." + str(count) + "/32  up"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '' or result.returncode  != 0:
				logger.error("stdout = " + out)
				logger.error(err)

			count+=1
	#End bringUpNetworks(self)
#End ComputeNodeUpdate()
