import logging
import os
import subprocess
import re
import time
from fusionIOUtils import checkFusionIOFirmwareUpgradeSupport
from systemConfiguration import SystemConfiguration
from collectComponentInformation import GetComponentInformation



'''
This class is used to initialize the program before an update is started.
'''
class Initialize:
	def __init__(self, cursesThread):
		self.csurResourceDict = {}
		self.cursesThread = cursesThread

	#End __init__(self):


	'''
	This function prints the initial application header.
	'''
	def __printHeader(self, programVersion):
		version = 'Version ' + programVersion
		versionLength = len(version)
		title = "SAP HANA CSUR Update Application"
		titleLength = len(title)
		author = "Bill Neumann - SAP HANA CoE"
		authorLength = len(author)
		copyright = '(c) Copyright 2016 Hewlett Packard Enterprise Development LP'
		copyrightLength = len(copyright)

		welcomeMessageTop =  "+" + "-"*65 + "+"
		welcomeMessageTitle =  "|" + title + " "*(65-titleLength) + "|"
		welcomeMessageVersion =  "|" + version + " "*(65-versionLength) + "|"
		welcomeMessageAuthor =  "|" + author + " "*(65-authorLength) + "|"
		welcomeMessageCopyright =  "|" + copyright + " "*(65-copyrightLength) + "|"
		welcomeMessageBottom =  "+" + "-"*65 + "+"

		welcomMessageContainer = [welcomeMessageTop, welcomeMessageTitle, welcomeMessageVersion, welcomeMessageAuthor, welcomeMessageCopyright, welcomeMessageBottom]

		#Each line of the welcome message is inserted seperately, since all lines are maintained in an array.
		for line in welcomMessageContainer:
			self.cursesThread.insertMessage(['info', line])

		self.cursesThread.insertMessage(['info', ''])

	#End __printHeader(self):

	
	'''
	This is the main function that is called to do the program initialization for the 
	different components based on the users selection.
	It returns the csurResourceDict which contains all the information gathered during
	initialization that is needed to update the various components.
	'''
	def init(self, csurBasePath, logBaseDir, debug, programVersion, versionInformationLogOnly, updateOSHarddrives):
		#Save the csur base path to the csur resource dict as it will be needed later.
		self.csurResourceDict['csurBasePath'] = csurBasePath

		self.__printHeader(programVersion)

		if versionInformationLogOnly:
			self.cursesThread.insertMessage(['informative', "Phase 1: Collecting system version information report."])
		else:
			self.cursesThread.insertMessage(['informative', "Phase 1: Initializing for the system update."])

		'''
		This section is commented out, since the initialization is for compute nodes only and it is not necessary to prompt.
		#The SystemConfiguration class is used to collect the system configuration from the user.
	        systemConfiguration = SystemConfiguration(self.cursesThread)
        	systemConfigurationDict = systemConfiguration.getConfiguration()

		#Add the system configuration to the csurResourceDict.
		self.csurResourceDict.update(systemConfigurationDict)
		'''

		'''
		The csurAppResourceFile contains information specific to the application and CSUR, e.g. supported OS, etc.
		The file name is hardcoded, since it cannot be set ahead of time.
		'''
		csurAppResourceFile = csurBasePath + '/resourceFiles/csurAppResourceFile'

		#Get csur application's resource file data and save it to a dictionary (hash).
		try:
			with open(csurAppResourceFile) as f:
				for line in f:
					line = line.strip()
					#Remove quotes from resources.
					line = re.sub('[\'"]', '', line)

					#Ignore commented and blank lines.
					if len(line) == 0 or re.match("^#", line):
						continue
					else:
						(key, val) = line.split('=')
						key = re.sub('\s+', '', key)
						self.csurResourceDict[key] = val.lstrip()
		except IOError as err:
			self.__exitOnError("Unable to open the application's resource file (" + csurAppResourceFile + ") for reading; exiting program execution.")

		#Configure logging and clean up old logs during initialization.
		self.csurResourceDict['logBaseDir'] = logBaseDir

		try:
			mainApplicationLog = self.csurResourceDict['mainApplicationLog']
		except KeyError as err:
			self.__exitOnError("The resource key (" + str(err) + ") was not present in the application's resource file " + csurAppResourceFile + "; exiting program execution.")

		mainApplicationLog = logBaseDir + mainApplicationLog
		mainApplicationHandler = logging.FileHandler(mainApplicationLog)

		logger = logging.getLogger('mainApplicationLogger')

		'''
		The log level is saved to the csurResourceDict so that it can be referenced in other modules
		so that they set logging to the same level for their log files.
		'''	
		if debug:
			logger.setLevel(logging.DEBUG)
			self.csurResourceDict['logLevel'] = 'debug'
		else:
			logger.setLevel(logging.INFO)
			self.csurResourceDict['logLevel'] = 'info'

		formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
		mainApplicationHandler.setFormatter(formatter)
		logger.addHandler(mainApplicationHandler)

		'''
		Initialize the version information log file, which holds version information for all
		components being updated.
		'''
		versionInformationLog = logBaseDir + 'versionInformationLog.log'
		versionInformationHandler = logging.FileHandler(versionInformationLog)
		versionInformationLogger = logging.getLogger('versionInformationLog')
		versionInformationLogger.setLevel(logging.INFO)
		versionInformationLogger.addHandler(versionInformationHandler)

		getComponentInformation = GetComponentInformation(self.csurResourceDict, self.cursesThread)
		componentListDict = getComponentInformation.getComponentInformation(versionInformationLogOnly, updateOSHarddrives)

		self.csurResourceDict['componentListDict'] = componentListDict

		return self.csurResourceDict

	#End init(self, csurBasePath):


	'''
	This function is used to display a message for 5 seconds before shutting down curses
	and exiting program execution.
	'''
	def __exitOnError(self, message):
		self.cursesThread.insertMessage(['error', message])
		time.sleep(5.0)
		self.cursesThread.join()
		exit(1)
	#End  __exitOnError(self, message):

#End class Initialize:
