import logging
import os
import subprocess
import re
from fusionIOUtils import checkFusionIOFirmwareUpgradeSupport
from computeNodeInventory import (ComputeNodeInventory, Gen1ScaleUpComputeNodeInventory)


class ComputeNode:
	def __init__(self, csurResourceDict, ip):
		self.csurResourceDict = csurResourceDict

		'''
		This dictionary holds compute node specific information: systemModel, osDistLevel, kernel, processorType
		which is passed to other objects.
		'''
		self.computeNodeDict = {}

		try:
			csurBasePath = self.csurResourceDict['csurBasePath']
                        logLevel = self.csurResourceDict['logLevel']
			logBaseDir = self.csurResourceDict['logBaseDir']
		except KeyError as err:
			raise KeyError(str(err))

		self.computeNodeDict['ip'] = ip

		hostname = os.uname()[1]
		self.computeNodeDict['hostname'] = hostname

                computeNodeLog = logBaseDir + 'computeNode_' + hostname + '.log'

                #Configure logging
                handler = logging.FileHandler(computeNodeLog)

		self.loggerName = ip + 'Logger'
		self.computeNodeDict['loggerName'] = self.loggerName

                logger = logging.getLogger(self.loggerName)

                if logLevel == 'debug':
                        logger.setLevel(logging.DEBUG)
                else:
                        logger.setLevel(logging.INFO)

                formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
                handler.setFormatter(formatter)
                logger.addHandler(handler)

	#End __init__(self, csurResourceDict, ip):


	'''
	This function is used to initialize for a compute node update.
	versionInformationLogOnly is used to indicate that only a version information log will be created, which
	means some initialization steps can be skipped.  
	updateOSHarddrives is used to indicate that only the OS hard drive firmware has been requested to update,
	which means some initialization steps can be skipped.
	'''
	def computeNodeInitialize(self, computeNodeResources, versionInformationLogOnly, updateOSHarddrives): 
		logger = logging.getLogger(self.loggerName)

		'''
		This is returned with any error messages that are encountered along with whether or not the 
		compute node needs to be updated.
		'''
                resultDict = {'updateNeeded' : False, 'errorMessages' : []}

                #Get system model.
                command = "dmidecode -s system-product-name"
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
		out = out.strip()

                logger.debug("The output of the command (" + command + ") used to get the system's model was: " + out)

                if result.returncode != 0:
                        logger.error("Unable to get the system's model information.\n" + err)
                        resultDict['errorMessages'].append("Unable to get the system's model information.")
                        return resultDict

		try:
                	systemModel = (re.match('[a-z,0-9]+\s+(.*)', out, re.IGNORECASE).group(1)).replace(' ', '')
		except AttributeError as err:
			logger.error("There was a system model match error when trying to match against '" + out + "':\n" + str(err) + ".")
			resultDict['errorMessages'].append("There was a system model match error.")
			return resultDict

                try:
			if systemModel not in self.csurResourceDict['supportedComputeNodeModels']:
				logger.error("The system's model (" + systemModel + ") is not supported by this CSUR bundle.")
                                resultDict['errorMessages'].append("The system's model is not supported by this CSUR bundle.")
                                return resultDict
                except KeyError as err:
                        logger.error("The resource key (" + str(err) + ") was not present in the application's esource file.")
                        resultDict['errorMessages'].append("A resource key error was encountered.")
                        return resultDict

                logger.debug("The system's model was determined to be: " + systemModel + ".")

		self.computeNodeDict['systemModel'] = systemModel

		#Get the system's OS distribution version information.
		command = "cat /proc/version"
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to get the OS distribution information was: " + out.strip())

		if result.returncode != 0:
			logger.error("Unable to get the system's OS distribution version information.\n" + err)
                        resultDict['errorMessages'].append("Unable to get the system's OS distribution version information.")
                        return resultDict

		#Change version information to lowercase before checking for OS type.
		versionInfo = out.lower()

		if 'suse' in versionInfo:
			OSDist = 'SLES'
			command = "cat /etc/SuSE-release"
		else:
			OSDist = 'RHEL'
			command = "cat /etc/redhat-release"

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error("Unable to get the system's OS distribution level.\n" + err)
                        resultDict['errorMessages'].append("Unable to get the system's OS distribution level.")
                        return resultDict
		else:
			releaseInfo = out.replace('\n', ' ')

			if OSDist == 'SLES':
				try:
					slesVersion = re.match('.*version\s*=\s*([1-4]{2})', releaseInfo, re.IGNORECASE).group(1)
				except AttributeError as err:
					logger.error("There was SLES OS version match error when trying to match against '" + releaseInfo + "':\n" + str(err) + ".")
					resultDict['errorMessages'].append("There was a SLES OS version match error.")
					return resultDict

				try:
					slesPatchLevel = re.match('.*patchlevel\s*=\s*([1-4]{1})', releaseInfo, re.IGNORECASE).group(1)
				except AttributeError as err:
					logger.error("There was SLES patch level match error when trying to match against '" + releaseInfo + "':\n" + str(err) + ".")
					resultDict['errorMessages'].append("There was a SLES patch level match error.")
					return resultDict

				osDistLevel = OSDist + slesVersion + '.' + slesPatchLevel
			else:
				try:
					rhelVersion = re.match('.*release\s+([6-7]{1}.[0-9]{1}).*', releaseInfo, re.IGNORECASE).group(1)
				except AttributeError as err:
					logger.error("There was RHEL OS version match error when trying to match against '" + releaseInfo + "':\n" + str(err) + ".")
					resultDict['errorMessages'].append("There was a RHEL OS version match error.")
					return resultDict

				osDistLevel = OSDist + rhelVersion

		try:
			if osDistLevel not in self.csurResourceDict['supportedDistributionLevels']:
				logger.error("The system's OS distribution level (" + osDistLevel + ") is not supported by this CSUR bundle.")
                                resultDict['errorMessages'].append("The system's OS distribution level is not supported by this CSUR bundle.")
                                return resultDict
                except KeyError as err:
                        logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
                        resultDict['errorMessages'].append("A resource key error was encountered.")
                        return resultDict

		logger.debug("The system's OS distribution level was determined to be: " + osDistLevel + ".")

		self.computeNodeDict['osDistLevel'] = osDistLevel

		'''
		Whenever any type of update is being performed we ensure certain prerequisites are met, e.g. the HANA application
		is not running.
		'''
		if not versionInformationLogOnly:
			#On NFS servers we want to check and notify if the cluster is still running.
			if 'DL380' in systemModel:
				command = '/opt/cmcluster/bin/cmviewcl -f line'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				logger.debug("The output of the command (" + command + ") used to check if the cluster is running was: " + out.strip())

				if result.returncode != 0:
					logger.warn("Unable to check if the cluster is running.\n" + err)
					resultDict['errorMessages'].append("Unable to check if the cluster is running.")

				clusterView = out.splitlines()

				for line in clusterView:
					if re.search('^status=', line):
						if re.match('status=up', line):
							logger.warn("It appears that the cluster is still running.\n" + out)
							resultDict['errorMessages'].append("It appears that the cluster is still running.")

			'''
			On servers that are not Serviceguard we check if SAP HANA is running and notify if it is running.
			We can assume that processes are not running is we get a return code of 1.
			'''
			if not ('DL380' in systemModel or 'DL320' in systemModel):
				command = 'ps -C hdbnameserver,hdbcompileserver,hdbindexserver,hdbpreprocessor,hdbxsengine,hdbwebdispatcher'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				logger.debug("The output of the command (" + command + ") used to check if SAP is running was: " + out.strip())

				if result.returncode == 0:
					logger.warn("It appears that SAP HANA is still running.\n" + out)
					resultDict['errorMessages'].append("It appears that SAP HANA is still running.")
		
			'''
			Additional kernel version and processorType is needed for FusionIO systems when the driver is rebuilt.	
			Also, need to confirm the system is already at a supported firmware version for automatic upgrades.
			'''
			if systemModel == 'DL580G7' or systemModel == 'DL980G7':
				#Check if /hana/log or /HANA/IMDB-log is mounted.
				command = 'mount'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()

				logger.debug("The output of the command (" + command + ") used to check if the log partition is mounted was: " + out.strip())

				if result.returncode != 0:
					logger.error("Unable to check if the log partition is mounted.\n" + err)
					resultDict['errorMessages'].append("Unable to check if the log partition is mounted.")
					return resultDict

				if re.search('/hana/log|/HANA/IMDB-log', out, re.MULTILINE|re.DOTALL) != None:
					logger.error("The log partition is still mounted.")
					resultDict['errorMessages'].append("The log partition needs to be unmounted before the system is updated.")
					return resultDict

				#Get the currently used kernel and processor type, which is used as part of the FusionIO driver RPM name.
				command = 'uname -r'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()
				kernel = out.strip()

				logger.debug("The output of the command (" + command + ") used to get the currently used kernel was: " + kernel)

				if result.returncode != 0:
					logger.error("Unable to get the system's current kernel information.\n" + err)
					resultDict['errorMessages'].append("Unable to get the system's current kernel information.")
					return resultDict

				logger.debug("The currently used kernel was determined to be: " + kernel + ".")

				self.computeNodeDict['kernel'] = kernel
				
				command = 'uname -p'
				result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				out, err = result.communicate()
				processorType = out.strip()

				logger.debug("The output of the command (" + command + ") used to get the compute node's processor type was: " + processorType)

				if result.returncode != 0:
					logger.error("Unable to get the system's processor type.\n" + err)
					resultDict['errorMessages'].append("Unable to get the system's processor type.")
					return resultDict

				logger.debug("The compute node's processor type was determined to be: " + processorType + ".")

				self.computeNodeDict['processorType'] = processorType

				try:
					if not checkFusionIOFirmwareUpgradeSupport(self.csurResourceDict['fusionIOFirmwareVersionList'], self.loggerName):
						resultDict['errorMessages'].append("The fusionIO firmware is not at a supported version for an automatic upgrade.")
						return resultDict
				except KeyError as err:
					logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
					resultDict['errorMessages'].append("A resource key error was encountered.")
					return resultDict

		#Don't need to check drivers if only doing an OS hard drive firmware update.
		if not updateOSHarddrives:
			#Confirm that the drivers for the system being updated are loaded.
			result = self.__checkDrivers(computeNodeResources, systemModel, osDistLevel)

			if result != '':
				resultDict['errorMessages'].append(result)
				return resultDict
			
		#Instantiate the compute node inventory class which is used to get a list of compute node components that need to be updated.
		try:
			if (systemModel == 'DL580G7' or systemModel == 'DL980G7'):
				computeNodeInventory = Gen1ScaleUpComputeNodeInventory(self.computeNodeDict.copy(), self.csurResourceDict['noPMCFirmwareUpdateModels'], computeNodeResources, self.csurResourceDict['fusionIOSoftwareInstallPackageList'])
			elif systemModel == 'DL380pGen8' and 'systemGeneration' in self.csurResourceDict and self.csurResourceDict['systemGeneration'] == 'Gen1.x':
				computeNodeInventory = ComputeNodeInventory(self.computeNodeDict.copy(), self.csurResourceDict['noPMCFirmwareUpdateModels'], computeNodeResources, systemGeneration='Gen1.x')
			else:
				computeNodeInventory = ComputeNodeInventory(self.computeNodeDict.copy(), self.csurResourceDict['noPMCFirmwareUpdateModels'], computeNodeResources)
		except KeyError as err:
			logger.error("The resource key (" + str(err) + ") was not present in the resource file.")
			resultDict['errorMessages'].append("A resource key error was encountered.")
			return resultDict

		#Inventory the compute node to determine which components need to be updated.
		if not updateOSHarddrives:
			computeNodeInventory.getComponentUpdateInventory()
		else:
			hardDrivesLocal = computeNodeInventory.getLocalHardDriveFirmwareInventory()

			if hardDrivesLocal != None and not hardDrivesLocal:
				resultDict['errorMessages'].append("There are no local hard drives to update, since there were no controllers detected.")
				return resultDict

                if computeNodeInventory.getInventoryStatus():
			resultDict['errorMessages'].append("Errors were encountered during the compute node's inventory.")
			return resultDict

		#The resultDict will not be used, but the inventory is done which generated the version report.
		if versionInformationLogOnly:
			return resultDict

                componentUpdateDict = computeNodeInventory.getComponentUpdateDict()

                '''
                This gets a list of the dictionary sizes (Software, Drivers, Firmwware) so that
                it can be determined whether or not an update is needed.
                '''
		if updateOSHarddrives:
			if len(componentUpdateDict['Firmware']) != 0:
				self.computeNodeDict['componentUpdateDict'] = componentUpdateDict
				resultDict['updateNeeded'] = True
		else:
			componentDictSizes = [len(dict) for dict in componentUpdateDict.values()]

			if any(x != 0 for x in componentDictSizes):
				self.computeNodeDict['componentUpdateDict'] = componentUpdateDict
				resultDict['updateNeeded'] = True
				
				if 'FusionIO' in componentUpdateDict['Firmware']:
					self.computeNodeDict['busList'] = computeNodeInventory.getFusionIOBusList()

				self.computeNodeDict['externalStoragePresent'] = computeNodeInventory.isExternalStoragePresent()
	
		return resultDict

	#End computeNodeInitialize(self): 


	'''
	This function is used to confirm that the drivers to be checked for an update are loaded.
	'''
	def __checkDrivers(self, computeNodeResources, systemModel, osDistLevel):
		errorMessage = ''

		logger = logging.getLogger(self.loggerName)

		driversFound = False
		started = False

		#Need to check twice for the Mellonex driver, since it can have two different names (mlx4_en or mlnx).
		mlnxDriverFound = False

                for data in computeNodeResources:
                        #Remove spaces if any are present.
                        data = data.replace(' ', '')

                        if not 'Drivers' in data and not driversFound:
                                continue
                        elif 'Drivers' in data:
                                driversFound = True
                                continue
                        elif not ((osDistLevel in data) and (systemModel in data)) and not started:
                                continue
                        elif (osDistLevel in data) and (systemModel in data):
                                started = True
                                continue
                        elif re.match(r'\s*$', data):
                                break
                        else:
                                computeNodeDriverList = data.split('|')
                                computeNodeDriver = computeNodeDriverList[0]

                                command = "modinfo " + computeNodeDriver
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()

                                logger.debug("The output of the command (" + command + ") used to check if the " + computeNodeDriver + " driver is loaded was: " + out.strip())

                                if result.returncode != 0:
					if (computeNodeDriver == 'mlx4_en' or computeNodeDriver == 'mlnx') and not mlnxDriverFound:
						mlnxDriverFound = True
						continue
					logger.error("The " + computeNodeDriver + " driver does not appear to be loaded.\n" + err)
					errorMesssage = "The " + computeNodeDriver + " driver does not appear to be loaded."
					return errorMessage

		if (systemModel == 'DL580G7' or systemModel == 'DL980G7'):
			command = "modinfo iomemory_vsl"
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			logger.debug("The output of the command (" + command + ") used to check if the iomemory_vsl driver is loaded was: " + out.strip())

			if result.returncode != 0:
				logger.error("The iomemory_vsl driver does not appear to be loaded.\n" + err)
				errorMessage = "The iomemory_vsl driver does not appear to be loaded."

		return errorMessage

	#End __checkDrivers(self, resultDict):

	
	'''
	This function is used to get the dictionary of a compute node which
	contains information about the compute node.
	'''
	def getComputeNodeDict(self):
		return self.computeNodeDict
	#End getComputeNodeDict(self):

#End class ComputeNode:
