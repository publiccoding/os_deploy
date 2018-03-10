import re
import socket
import os
import subprocess
import datetime
import csurUtils
import logging


logger = logging.getLogger("firmwareDriverLogger")

#This is the main compute node class from which other compute nodes can be instantiated as necessary.
class ComputeNode():

	def __init__(self, systemModel, OSDistLevel):
		self.systemModel = systemModel
		self.OSDistLevel = OSDistLevel

		#Variables used to determine status of gap analysis stage data collection.
		self.firmwareError = False
		self.driverError = False
		self.softwareError = False
	#End __init__(self, systemModel, OSDistLevel)


	'''
	This function retrieves firmware versions from the CSUR data that was 
	supplied by the CSUR file during program initialization.
	'''
	def getFirmwareDict(self, csurData):
		started = False
		firmwareDict = {}

		logger.info("Begin Getting Firmware Dictionary")

		for data in csurData:
			if not re.match(r'Firmware.*', data) and not started:
				continue
			elif re.match(r'Firmware.*', data):
				started = True
				continue
			elif re.match(r'\s*$', data):
				break
			else:
				firmwareList = data.split('|')
				firmwareDict[firmwareList[0].strip()] = firmwareList[1].strip()

		logger.debug("firmwareDict = " + str(firmwareDict))
		logger.info("End Getting Firmware Dictionary")
		return firmwareDict
	#End getFirmwareDict(csurData)


	'''
	This function updates the firmwareToUpdate array with any storage components that need updating
	based on a comparison to the firmware versions within the firmwareDict.
	'''
	def getStorageFirmwareInventory(self, firmwareDict, updateList):

		logger.info("Begin Getting Storage Firmware Inventory")
		logger.debug("firmwareDict = " + str(firmwareDict))
		logger.debug("updateList = " + ":".join(updateList))

		arrayCfgUtilFile = '/usr/sbin/hpssacli'

		logger.debug("arrayCfgUtilFile = " + arrayCfgUtilFile)

		#Get list of storage controllers.
		command = arrayCfgUtilFile + " ctrl all show status|egrep -o \"P.*Slot\s*[0-9]{1,2}\"|awk '{print $1\":\"$NF}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			logger.error(err)
			self.firmwareError = True
		logger.debug("out = " + out)

		controllerList = out.splitlines()

		hardDriveList = [] #This is a complete list of hard drives from all controllers combined.

		for controller in controllerList:
			controllerModel = controller[0:controller.index(':')]
			controllerSlot = controller[controller.index(':')+1:len(controller)]

			csurFirmwareVersion = firmwareDict.get(controllerModel)

			command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " show |grep \"Firmware Version\"|awk '{print $3}'"

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				logger.error(err)
				self.firmwareError = True
			logger.debug("out = " + out)

			installedFirmwareVersion = out.strip()

			if installedFirmwareVersion != csurFirmwareVersion:
				updateList.append(controllerModel)

			if (controllerModel == 'P812') or (controllerModel == 'P431'):
				csurFirmwareVersion = firmwareDict.get('D2700')
				command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " enclosure all show  detail|grep -m 1  \"Firmware Version\"|awk '{print $3}'"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					logger.error(err)
					self.firmwareError = True
				logger.debug("out = " + out)

				installedFirmwareVersion = out.strip()

				if installedFirmwareVersion != csurFirmwareVersion:
					updateList.append('D2700')

			#Get a list of all hard drives and thier firmware version.
			command = arrayCfgUtilFile + " ctrl slot=" + controllerSlot + " pd all show detail|grep -A 2 --no-group-separator \"Firmware Revision\"|grep -v Serial|sed -e '$!N;s/\\n/ /'|awk '{print $6, $3}'|sort -k1"

			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				logger.error(err)
				self.firmwareError = True
			logger.debug("out = " + out)

			hardDriveList.extend(out.splitlines()) #out is an array of hard drives and their firmware version, e.g. 'EG0600FBVFP HPDC'

		#Sort the hard drive list since it may not be sorted due to multiple controllers.
		hardDriveList.sort()

		#Get a unique list of hard drives managed by the controllers.
		hardDriveModels = []
		count = 0
		
		for hd in hardDriveList:
			hardDriveData = hd.split()

			if count == 0:
				hardDriveModels.append(hardDriveData[0].strip())
				tmpHardDriveModel = hardDriveData[0]
				count += 1
			elif hardDriveData[0] != tmpHardDriveModel:
				hardDriveModels.append(hardDriveData[0].strip())
				tmpHardDriveModel = hardDriveData[0]

		#Now check each hard drive's firmware version.
		for hardDriveModel in hardDriveModels:
			count = 0

			csurFirmwareVersion = firmwareDict.get(hardDriveModel)

			#This accounts for the cases where the CSUR did not include a hard drive's firmware.
			if csurFirmwareVersion is None:
				logger.warn("There was no firmware in the CSUR for hard drive model" + hardDriveModel +".")
				continue

			#Now check every hard drive's firmware version that matches the current hardDriveModel.
			for hd in hardDriveList:
				hardDriveData = hd.split()

				if hardDriveData[0].strip() == hardDriveModel:
					hardDriveFirmwareVersion = hardDriveData[1].strip()

					'''
					If the hard drive version does not match the CSUR version then add it to the updateList.
					We only care about a one time occurance of a firmware mis-match.
					'''
					if hardDriveFirmwareVersion != csurFirmwareVersion:
						updateList.append(hardDriveModel)
						count += 1
						break

		logger.info("End Getting Storage Firmware Inventory")
	#End getStorageFirmwareInventory(firmwareDict, updateList)


	'''
	This function updates the firmwareToUpdate array with any NIC cards that need updating
	based on a comparison to the firmware versions within the firmwareDict.
	'''
	def getNICFirmwareInventory(self, firmwareDict, updateList):
		nicCardModels = []
		count = 0

		logger.info("Begin Getting NIC Firmware Inventory")
		logger.debug("firmwareDict = " + str(firmwareDict))
		logger.debug("updateList = " + ":".join(updateList))

		nicBusList = self.getNicBusList()

		#Get a unique list of nic card models.
		for nd in nicBusList: #['03:00.0 HP331FLR', '44:00.0 HP560SFP', '47:00.0 HP560SFP']
			nicCardData = nd.split()

			if count == 0:
				nicCardModels.append(nicCardData[1].strip())
				tmpNicCardModel = nicCardData[1]
				count += 1
			elif nicCardData[1] != tmpNicCardModel:
				nicCardModels.append(nicCardData[1].strip())
				tmpNicCardModel = nicCardData[1]

		#Get nic card list which will be used to map nic card bus to nic device.
		command = "ifconfig -a|egrep -v \"^\s+|^bond|^lo|^\s*$\"|awk '{print $1}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			logger.error(err)
			self.firmwareError = True
		logger.debug("out = " + out)

		nicCardList = out.splitlines() #['em0', 'em1', 'em2', 'em3', 'p4p1', 'p4p2', 'p5p1', 'p5p2', 'p7p1', 'p7p2', 'p8p1', 'p8p2']

		#Loop through all nic cards to check thier firmware.  Only record one occcurance of a mismatch.
		for nicCardModel in nicCardModels: #['HP331FLR', 'HP560SFP']
			count = 0
			csurNicCardFirmwareVersion = firmwareDict.get(nicCardModel)

			for data in nicBusList:
				nicCardData = data.split()

				nicBus = nicCardData[0].strip()
				installedNicCardModel = nicCardData[1].strip()

				if installedNicCardModel == nicCardModel:
					for nic in nicCardList:
						logger.debug("NIC card = " + nic)
						command = "ethtool -i " + nic + "|grep " + nicBus
						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()

						if err != '':
							logger.error(err)
							self.firmwareError = True
						logger.debug("out = " + out)

						if result.returncode != 0:
							continue
						else:
							nicDevice = nic

						command = "ethtool -i " + nicDevice + "|grep firmware-version|awk '{print $NF}'"
						result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
						out, err = result.communicate()

						if err != '':
							logger.error(err)
							self.firmwareError = True
						logger.debug("out = " + out)

						installedFirmwareVersion = out.strip()

						if installedFirmwareVersion != csurNicCardFirmwareVersion and count == 0:
							updateList.append(nicCardModel)
							count += 1
						break #We only get here if a nic card matched the nicBus we are looking at.
				else:
					continue
	
				if count == 1:
					break
		logger.info("End Getting NIC Firmware Inventory")
	#End getNICFirmwareInventory(firmwareDict, updateList)

	
	'''
	This function is used to get the NIC bus list using lscpi and return the list to the getNICFirmwareInventory function.
	'''
	def getNicBusList(self):
		nicBusList = []
		commands = []
		count = 0

		if self.systemModel == 'DL580G7' or self.systemModel =='DL980G7' or self.systemModel =='BL680cG7':
			commands.append("lspci -v|grep -B1 NC --no-group-separator|sed -e '$!N;s/\\n/ /'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}|NC[0-9]+[a-z]{1,3}\"|sed -e '$!N;s/\\n/ /'| sort -k2")
		elif self.systemModel == 'DL580Gen8':
			commands.append("lspci -v|grep 'NetXtreme BCM5719'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}\"") #HP 331FLR
			commands.append("HP331FLR")
			commands.append("lspci -v|grep 'Intel Corporation 82599'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}\"") #HP 560SFP+
			commands.append("HP560SFP")
		elif self.systemModel == 'DL380pGen8':
			commands.append("lspci -v|grep -B1 NC --no-group-separator|sed -e '$!N;s/\\n/ /'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}|NC[0-9]+[a-z]{1,3}\"|sed -e '$!N;s/\\n/ /'| sort -k2") #NC552SFP
			commands.append("lspci -v|grep 'NetXtreme BCM5719'|uniq -w 2|egrep -io \".{2}:.{2}\.[0-9]{1}\"") #HP 331FLR
			commands.append("HP331FLR")

		while count < len(commands):
			command = commands[count]
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if err != '':
				logger.error(err)
				self.firmwareError = True
			logger.debug("out = " + out)

			if len(commands) == 1:
				nicBusList = out.splitlines()
			else:
				tmpList = out.splitlines()
				nicBusList.extend(x + ' ' + commands[count + 1] for x in tmpList)

			count += 2

		return nicBusList
	#End getNicBusList():


	'''
	This function updates the firmwareToUpdate array with any common components that need updating
	based on a comparison to the firmware versions within the firmwareDict.
	'''
	def getCommonFirmwareInventory(self, firmwareDict, updateList):
		biosFirmwareType = "BIOS" + self.systemModel
			
		logger.info("Begin Getting Compute Node Common Firmware Inventory")
		logger.debug("firmwareDict = " + str(firmwareDict))
		logger.debug("updateList = " + ":".join(updateList))

		#BIOS
		logger.info("Getting BIOS firmware information.")
		command = "dmidecode -s bios-release-date"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			logger.error(err)
			self.firmwareError = True
		logger.debug("out = " + out)

		biosFirmwareDate = out.strip()
		biosFirmwareDateList = biosFirmwareDate.split('/')
		installedFirmwareVersion = biosFirmwareDateList[2] + '.' + biosFirmwareDateList[0] + '.' + biosFirmwareDateList[1]

		csurFirmwareVersion = firmwareDict.get(biosFirmwareType)

		if installedFirmwareVersion != csurFirmwareVersion:
			updateList.append(biosFirmwareType)

		#iLO
		logger.info("Getting iLO firmware information.")
		command = "hponcfg -g|grep \"Firmware Revision\"|awk '{print $4}'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			logger.error(err)
			self.firmwareError = True
		logger.debug("out = " + out)

		installedFirmwareVersion = out.strip()

		if installedFirmwareVersion != firmwareDict.get('iLO'):
			updateList.append('iLO')

		logger.info("End Getting Compute Node Common Firmware Inventory")
	#End getCommonFirmwareInventory(firmwareDict, updateList)


	'''
	This function is stubbed for future use.
	'''
	def getComputeNodeSpecificFirmwareInventory(self, firmwareDict, updateList):
		pass
	#End getComputeNodeSpecificFirmwareInventory(self, firmwareDict, updateList)


	'''
	This function updates the driversToUpdate array with any drivers that need updating
	based on a comparison to the driver list found in the CSUR data.
	'''
	def getDriverInventory(self, csurData):
		started = False
		updateDriverList = []

		logger.info("Begin Getting Driver Inventory")
		logger.debug("csurData = " + ":".join(csurData))

		regex = self.OSDistLevel + ".*" + self.systemModel + ".*"
	
		for data in csurData:
			if not re.match(regex, data) and not started:
				continue
			elif re.match(regex, data):
				started = True
				continue
			elif re.match(r'\s*$', data):
				break
			else:
				csurDriverList = data.split('|')
				csurDriver = csurDriverList[0].strip()
				csurDriverVersion = csurDriverList[1].strip()

				command = "modinfo " + csurDriver + "|grep -i ^version|awk '{print $2}'"
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				if err != '':
					logger.error(err)
					self.driverError = True
				logger.debug("driver = " + csurDriver)
				logger.debug("out = " + out)

				installedDriverVersion = out.strip()

				if installedDriverVersion != csurDriverVersion:
					updateDriverList.append(csurDriver)

		logger.debug("updateDriverList = " + ":".join(updateDriverList))
		logger.info("End Getting Driver Inventory")
		return updateDriverList
	#End getDriverInventory(csurData)


	'''
	This function updates the softwareToUpdate array with any software that need updating
	based on a comparison to the software list found in the CSUR data.
	'''
        def getSoftwareInventory(self, csurData):
                started = False
                softwareFound = False
                updateSoftwareList = []

                logger.info("Begin Getting Software Inventory")
                logger.debug("csurData = " + ":".join(csurData))

		regex = ".*" + self.OSDistLevel + ".*" + self.systemModel + ".*"

                for data in csurData:
                        if not re.match('Software.*', data) and not softwareFound:
                                continue
                        elif re.match('Software.*', data):
                                softwareFound = True
                                continue
                        elif not re.match(regex, data) and not started:
                                continue
                        elif re.match(regex, data):
                                started = True
                                continue
                        elif re.match(r'\s*$', data):
                                break
                        else:
                                csurSoftwareList = data.split('|')
                                csurSoftware = csurSoftwareList[0].strip()
                                csurSoftwareEpoch = csurSoftwareList[1].strip()
                                csurSoftwareVersion = csurSoftwareList[2].strip()

                                command = "rpm -q --queryformat=\"%{buildtime} %{version}-%{release}\" " + csurSoftware + " 2> /dev/null"
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

                                if err != '':
                                        csurUtils.log(err, "error")
					self.softwareError = True
                                logger.debug("software = " + csurSoftware)
                                logger.debug("out = " + out)

                                if result.returncode != 0:
                                        updateSoftwareList.append(csurSoftware)
                                        continue

                                installedSoftware = out.strip()
                                installedSoftwareList = installedSoftware.split()
                                installedSoftwareEpoch = installedSoftwareList[0]
                                installedSoftwareVersion = installedSoftwareList[1]

                                if re.match(regex, csurSoftware):
                                        continue

                                if installedSoftwareEpoch < csurSoftwareEpoch:
                                        updateSoftwareList.append(csurSoftware)

                logger.debug("updateSoftwareList = " + ":".join(updateSoftwareList))
                logger.info("End Getting Software Inventory")
                return updateSoftwareList
        #End getSoftwareInventory(csurData)


	'''
	This function is used to determine if getting the firmware inventory was sucessful or not.
	'''
	def getFirmwareStatus(self):
		return self.firmwareError
	#End getFirmwareStatus():


	'''
	This function is used to determine if getting the driver inventory was sucessful or not.
	'''
	def getDriverStatus(self):
		return self.driverError
	#End getDriverStatus():


	'''
	This function is used to determine if getting the software inventory was sucessful or not.
	'''
	def getSoftwareStatus(self):
		return self.softwareError
	#End getSoftwareStatus():
#End ComputeNode()


'''
This class is a subclass of ComputeNode and its purpose is for getting model specific information.
'''
class DL580Gen8ComputeNode(ComputeNode):

	def getComputeNodeSpecificFirmwareInventory(self, firmwareDict, updateList):

		logger.info("Begin Getting Compute Node Specific Firmware Inventory")
		logger.debug("firmwareDict = " + str(firmwareDict))
		logger.debug("updateList = " + ":".join(updateList))

		#Power Management Controller
		fh = open("dmidecode.log", 'w')
		subprocess.call(["dmidecode"], stdout=fh)
		fh.close()

		command = "egrep -A 1 \"^\s*Power Management Controller Firmware\s*$\" dmidecode.log |grep -v Power |sed -e 's/^[ \t]*//'"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if err != '':
			logger.error(err)
			self.firmwareError = True
		logger.debug("out = " + out)

		installedFirmwareVersion = out.strip()

		os.remove("dmidecode.log")
		logger.info("End Getting Compute Node Specific Firmware Inventory")
	#End getComputeNodeSpecificFirmwareInventory(firmwareDict, updateList)
#End DL580Gen8ComputeNode(ComputeNode)
