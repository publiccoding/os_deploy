import re
import getpass
import logging
import time
#from networkSwitch import NetworkSwitch
#from sanSwitch import SANSwitch
#from threePar import ThreePAR
from computeNode import ComputeNode
from csurUpdateUtils import (RED, RESETCOLORS, TimerThread)



'''
This class is used to get component information for the various components to determine
what needs to be updated.
'''
class GetComponentInformation:
	def __init__(self, csurResourceDict, cursesThread):
		self.csurResourceDict = csurResourceDict
		self.cursesThread = cursesThread
	#End __init__(self, csurResourceDict):


	'''
	This function does the actual work of getting component information based
	on whether the system is a Scale-up or Scale-out.
	'''
	def getComponentInformation(self):
		systemTypeDict = self.csurResourceDict['systemType']
		logBaseDir = self.csurResourceDict['logBaseDir']
		logLevel = self.csurResourceDict['logLevel']
		csurBasePath = self.csurResourceDict['csurBasePath']

		'''
		This is a dictionary that holds a reference to timer thread's and their
		location based on IP address of the component being updated.
		A Scale-up system does not need to use the dictionary, since it is only one system/thread.
		'''
		timerThreadLocationDict = {}
		
		componentListDict = {'computeNodeList' : [], 'networkSwitchList' : [], 'sanSwitchList' : [], 'storeServList' : []}

		logger = logging.getLogger('mainApplicationLogger')

		if 'Scale-up' in systemTypeDict:
			systemType = 'Scale-up'	
			scaleUpConfiguration = systemTypeDict['Scale-up']
			
			#Get the compute node's resources from its resource file.
			componentResourceList = self.__getComponentResources(['Compute Node'], csurBasePath)

			if componentResourceList[0]:
				self.__exitOnError("An error occurred while collecting component resources; check the application's log file for errors; exiting program execution.")
		else:
			systemType = 'Scale-out'	
			
			'''
			This is an example of the scaleOutDict contents: 
			systemConfigurationDict['systemType'] = {'Scale-out' : {'scaleOutType' : 'CS500', 'generation' : generation, 'componentList' : componentList}}
			'''
			scaleOutDict = systemTypeDict['Scale-out']
			generation = scaleOutDict['generation']
			componentList = scaleOutDict['componentList']
			scaleOutConfiguration = scaleOutDict['scaleOutType']

			#Get the component resources from the respective resource files for the components that were selected for an update.
			componentResourceList = self.__getComponentResources(componentList, csurBasePath)

			if componentResourceList[0]:
				print RED + "\nAn error occurred while collecting component resources; check the application's log file for errors; exiting program execution." +  RESETCOLORS
				exit(1)

		if systemType == 'Scale-up':
			try:
				computeNode = ComputeNode(self.csurResourceDict.copy(), '127.0.0.1')
			except KeyError as err:
				logger.error("The resource key (" + str(err) + ") was not present in the application's resource file.")
				self.__exitOnError("A resource key was not present in the application's resource file; check the application's log file for errors; exiting program execution.")

			#Run timer thread for feedback during initialization.
			timerThread = TimerThread('Initializing compute node 127.0.0.1 ... ')
			timerThread.daemon = True
			timerThread.start()
			timerThreadLocation = 0
			self.cursesThread.insertTimerThread(['', timerThread])

			resultDict = computeNode.computeNodeInitialize(componentResourceList[1]['ComputeNodeResources'][:])

			timerThread.stopTimer()
			timerThread.join()
			self.cursesThread.updateTimerThread("Done initializing compute node 127.0.0.1.", timerThreadLocation)

			if len(resultDict['errorMessages']) != 0:
				self.__exitOnError("Error(s) were encountered while initializing the compute node; check the compute node's log file for additional information; exiting program execution.\n" + '\n'.join(resultDict['errorMessages']))
			else:
				if resultDict['updateNeeded']:
					componentListDict['computeNodeList'].append(computeNode)
				else:
					logger.info("An update for local compute node was not needed, since it is already up to date.")
		else:
			#When compute nodes are being updated we check to see if the local host is included to be updated.
			if componentList[0] == 'Compute Node':
				while 1:
					skipUpdate = False

					response = raw_input("Is the local host being updated [y|n]: ")
					response = response.strip().lower()

					if len(response) != 1:
						print "\tA valid response is y|n.  Please try again."
						continue

					if not re.match('y|n', response):
						print "\tA valid response is y|n.  Please try again."
						continue

					if response == 'y':
                                                try:
                                                        computeNode = ComputeNode(self.csurResourceDict.copy(), '127.0.0.1')
                                                except KeyError as err:
                                                        logger.error("The resource key (" + str(err) + ") was not present in the application's resource file.")
                                                        print RED + "\nA resource key was not present in the application's resource file; check the application's log file for errors; exiting program execution." +  RESETCOLORS
                                                        exit(1)

                                                resultDict = computeNode.computeNodeInitialize(componentResourceList[1]['ComputeNodeResources'][:])

                                                if len(resultDict['errorMessages']) != 0:
                                                        if self.__tryAgainQuery('Compute Node', resultDict['errorMessages']):
                                                                continue
                                                else:
                                                        if resultDict['updateNeeded']:
                                                                componentListDict['computeNodeList'].append(computeNode)
                                                        else:
                                                                logger.info("An update for local compute node was not needed, since it is already up to date.")
                                        break

			#Now go through the list of components that were selected to be updated and initialize them for the update.
			for component in componentList:
				while 1:
					invalidResponse = False
					tryAgain = False

					ip = raw_input("Enter the IP address of the " + component + " to be updated or enter to continue: ")

					ip = ip.strip()

					'''
					An empty string indicates the current component selection is done.
					Otherwise do some basic checking of the IP to see that its format is valid.
					'''
					if ip != '':
						if not self.__checkIP(ip):
							continue

						username = raw_input("Enter the admin user name for the " + component + ": ")
						username = username.strip()

						password = getpass.getpass(prompt = 'Enter the password for ' + username + ':')

						'''
						Give a chance to confirm the input before moving on to test/update.
						Since the SAN switch requires additional inputs we will check it later.
						'''
						if component != 'SAN Switch':
							if not self.__confirmInput(component, ip, username=username):
								continue

						if component == 'Compute Node':
							pass
						elif component == 'Network Switch':
							networkSwitch = NetworkSwitch(ip, username, password, logBaseDir, logLevel)

							resultDict = networkSwitch.checkSwitch(generation, componentResourceList[1]['NetworkSwitchResources'][:])

							if len(resultDict['errorMessages']) != 0:
								if self.__tryAgainQuery(component, resultDict['errorMessages']):
									continue
							else:
								if resultDict['updateNeeded']:
									componentListDict['networkSwitchList'].append(networkSwitch)
								else:
									logger.info("An update for network switch at '" + ip + "' was not needed, since it is already up to date.")
						elif component == 'SAN Switch':
							while 1:
								localhostIP = raw_input("Enter the management IP address of the local system: ")
								localhostIP = localhostIP.strip()

								if self.__checkIP(localhostIP):
									break
							
							scpUsername = raw_input("Enter the user name of a user that can scp to/from this system: ")
							scpUsername = scpUsername.strip()

							scpPassword = getpass.getpass(prompt = 'Enter the password for ' + scpUsername + ':')

							if not self.__confirmInput(component, ip, localhostIP=localhostIP, scpUsername=scpUsername):
								continue
							
							sanSwitch = SANSwitch(ip, password, localhostIP, scpUsername, scpPassword, logBaseDir, logLevel)

							resultDict = sanSwitch.checkSwitch(componentResourceList[1]['SANSwitchResources'][:], self.csurResourceDict['sanSwitchCrossReference'])

							if len(resultDict['errorMessage']) != 0:
								if self.__tryAgainQuery(component, resultDict['errorMessages']):
									continue
							else:
								if resultDict['updateNeeded']:
									componentListDict['sanSwitchList'].append(sanSwitch)
								else:
									logger.info("An update for SAN switch at '" + ip + "' was not needed, since it is already up to date.")
						elif component == '3PAR StoreServ':
							threePAR = ThreePAR(ip, username, password)

							resultDict = threePAR.check3PAR(componentResourceList[1]['3PARStoreServResources'][:])

							if len(resultDict['errorMessages']) != 0:
								if self.__tryAgainQuery(component, resultDict['errorMessages']):
									continue
							else:
								if resultDict['updateNeeded']:
									componentListDict['storeServList'].append(threePAR)
								else:
									logger.info("An update for the Service Processor at '" + ip + "' and its StoreServ was not needed, since they are already up to date.")
					else:
						break

		return componentListDict

	#End getComponentInformation(self):


	'''
	This function is used to get component resource data, e.g. model, software, firmware, drivers, etc.
	from is respective resource file.
	If a resource file key is missing or a resource file cannot be read then the errorMessage variable 
	will be set and the function returns immediately.
	'''
	def __getComponentResources(self, componentList, csurBasePath):
		componentResourceDict = {}
		errors = False

		logger = logging.getLogger('mainApplicationLogger')

		logger.info("Getting component resource data for " + ', '.join(componentList) + ".")

		for component in componentList:
			try:
				if component == 'Compute Node':
					resourceFile = csurBasePath + '/resourceFiles/' + self.csurResourceDict['computeNodeResourceFile']
				elif component == 'Network Switch':
					resourceFile = csurBasePath + '/resourceFiles/' + self.csurResourceDict['networkSwitchResourceFile']
				elif component == 'SAN Switch':
					resourceFile = csurBasePath + '/resourceFiles/' + self.csurResourceDict['sanSwitchResourceFile']
				elif component == '3PAR StoreServ':
					resourceFile = csurBasePath + '/resourceFiles/' + self.csurResourceDict['threePARResourceFile']
			except KeyError as err:
				errors = True
				logger.error("The resource key (" + str(err) + ") was not present in the application's resource file.")
				break

			try:
				with open(resourceFile) as f:
					resources = f.read().splitlines()
			except IOError as err:
				errors = True
				logger.error("Unable to open the " + component + "'s resource file (" + resourceFile + ") for reading.\n" + str(err))
				break

			if not errors:
				componentResourceKey = re.sub('\s+', '', component) + 'Resources'
				componentResourceDict[componentResourceKey] = resources

		logger.info("Done getting component resource data for " + ', '.join(componentList) + ".")

		return [errors, componentResourceDict]

	#End __getComponentResources(self, componentList):	


	'''
	This function does a basic check of an IP address.
	It is still up to the end user to provide a valid IP 
	for connection purposes.
	'''
	def __checkIP(self, ip):
		ipList = ip.split('.')

		if len(ipList) != 4:
			print "An invalid IP was provided, please try again."
			return False

		for number in ipList:
			try:
				number = int(number)
			except ValueError:
				print "An invalid IP was provided, please try again."
				return False

			if number < 0 or number > 255: 
				print "An invalid IP was provided, please try again."
				return False

		return True

	#End __checkIP(self, ip):

	
	'''
	This function gives the user a chance to to fix an issue and try again.  However, some issues
	may require the program to be restarted in order for the fix to be recognized.  An example 
	would be a resource missing from the main application resource file, since it is read in during
	program initialization.
	'''
	def __tryAgainQuery(self, component, errorMessages):
		tryAgain = False

		'''
		A resource KeyError is the only reason we exit immediately, since it indicates a program bug.
		Since the resource files should not have resources missing from them.
		'''
		for errorMessage in errorMessages:
			if 'resource' in errorMessage:
				print RED + errorMessage + " Fix the problem and try again; exiting program execution." + RESETCOLORS
				exit(1)

		print "The following error(s) was encountered while checking the " + component + ":"

		for errorMessage in errorMessages:
			print "\t" + errorMessage


		while 1:
			response = raw_input("Do you want to fix the problem and try again [y|n]: ")
			response = response.strip().lower()

			if len(response) != 1:
				print "\tA valid response is y|n.  Please try again."
				continue

			if not re.match('y|n', response):
				print "\tA valid response is y|n.  Please try again."
				continue

			if response == 'y':
				tryAgain = True						

			break

		return tryAgain

	#End __tryAgainQuery(self, component, error):


	def __confirmInput(self, component, ip, **kwargs):
		validInput = False

		print "The following information was provided for the component to be updated:"
		print "\t" + component + "IP: " + ip

		if 'username' in kwargs:
			print "\t" + component + "user name: " + kwargs['username']

		if 'localhostIP' in kwargs:
			print "\tlocal host managememt IP: " + kwargs['localhostIP']

		if 'scpUsername' in kwargs:
			print "\tlocal host scp user name: " + kwargs['scpUsername']

		while 1:
			response = raw_input("Is the above information correct [y|n]: ")
			response = response.strip().lower()

			if len(response) != 1:
				print "\tA valid response is y|n.  Please try again."
				continue

			if not re.match('y|n', response):
				print "\tA valid response is y|n.  Please try again."
				continue
			else:
				break

		if response == 'y':
			validInput = True						

		return validInput
		
	#End __confirmInput(self, component, ip, username):


        def __exitOnError(self, message):
                self.cursesThread.insertMessage(['error', message])
                time.sleep(10.0)
                self.cursesThread.join()
                exit(1)
        #End  __exitOnError(self, message):

#End class GetComponentInformation:
