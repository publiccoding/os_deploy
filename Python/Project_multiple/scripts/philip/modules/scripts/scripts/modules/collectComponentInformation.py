import re
import getpass
import logging
import time
import os
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
	def getComponentInformation(self, versionInformationLogOnly, updateOSHarddrives):
		'''
		Commented out to change to compute nodes only.	
		systemTypeDict = self.csurResourceDict['systemType']
		'''
		logBaseDir = self.csurResourceDict['logBaseDir']
		logLevel = self.csurResourceDict['logLevel']
		csurBasePath = self.csurResourceDict['csurBasePath']

		self.csurResourceDict['multipleUpgradesRequiredDict'] = {'SAN Switches' : [], '3PAR' : []}

		'''
		This is a dictionary that holds a reference to timer thread's and their
		location based on IP address of the component being updated.
		A Scale-up system does not need to use the dictionary, since it is only one system/thread.
		'''
		timerThreadLocationDict = {}
		
		componentListDict = {'computeNodeList' : [], 'networkSwitchList' : [], 'sanSwitchList' : [], 'storeServList' : []}

		logger = logging.getLogger('mainApplicationLogger')

		'''
		Commented out to change to compute nodes only.	
		if 'Scale-up' in systemTypeDict:
		'''
		systemType = 'Scale-up'	
		
		#Get the compute node's resources from its resource file.
		componentResourceList = self.__getComponentResources(['Compute Node'], csurBasePath)

		#If an error occurred while getting resources then componentResourceList[0] will be set to 'True'.
		if componentResourceList[0]:
			self.__exitOnError("An error occurred while collecting component resources; check the application's log file for errors; exiting program execution.")
		'''
		Commented out to change to compute nodes only.	
		else:
			systemType = 'Scale-out'	
			
			#This is an example of the scaleOutDict contents: 
			#systemConfigurationDict['systemType'] = {'Scale-out' : {'scaleOutType' : 'CS500', 'generation' : generation, 'componentList' : componentList}}
			scaleOutDict = systemTypeDict['Scale-out']
			generation = scaleOutDict['generation']
			componentList = scaleOutDict['componentList']
			scaleOutConfiguration = scaleOutDict['scaleOutType']

			#Get the component resources from the respective resource files for the components that were selected for an update.
			componentResourceList = self.__getComponentResources(componentList, csurBasePath)

			if componentResourceList[0]:
				self.__exitOnError("An error occurred while collecting component resources; check the application's log file for errors; exiting program execution.")
		'''

		if systemType == 'Scale-up':
			try:
				computeNode = ComputeNode(self.csurResourceDict.copy(), '127.0.0.1')
				computeNodeDict = computeNode.getComputeNodeDict()
				hostname = computeNodeDict['hostname']
				self.csurResourceDict['hostname'] = hostname
			except KeyError as err:
				logger.error("The resource key (" + str(err) + ") was not present in the application's resource file.")
				self.__exitOnError("A resource key was not present in the application's resource file; check the application's log file for errors; exiting program execution.")

			#Run timer thread for feedback during initialization.
			if versionInformationLogOnly:
				timerThread = TimerThread("Getting compute node " + hostname + "'s version report ... ")
			elif updateOSHarddrives:
				timerThread = TimerThread('Initializing compute node ' + hostname + ' for an OS hard drive update ... ')
			else:
				timerThread = TimerThread('Initializing compute node ' + hostname + ' ... ')
			timerThread.daemon = True
			timerThread.start()

			#Add the compute node's timer thread location to the timerThreadLocationDict if it is not already saved.
			if not '127.0.0.1' in timerThreadLocationDict:
				self.cursesThread.insertTimerThread(['', timerThread])
				timerThreadLocationDict['127.0.0.1'] = self.cursesThread.getTimerThreadLocation()
			else:
				self.cursesThread.insertTimerThread(['', timerThread], timerThreadLocationDict['127.0.0.1'])

			resultDict = computeNode.computeNodeInitialize(componentResourceList[1]['ComputeNodeResources'][:], versionInformationLogOnly, updateOSHarddrives)

			timerThread.stopTimer()
			timerThread.join()

			if len(resultDict['errorMessages']) != 0:
				if versionInformationLogOnly:
					self.__exitOnError("Error(s) were encountered while generating compute node " + hostname + "'s version report; check the compute node's log file for additional information; exiting program execution.")
				elif updateOSHarddrives:
					if not 'There are no local hard drives to update' in resultDict['errorMessages'][-1]: 
						self.__exitOnError("Error(s) were encountered while initializing compute node " + hostname + " for an OS hard drive update; check the compute node's log file for additional information; exiting program execution.")
					else:
						self.cursesThread.updateTimerThread("Compute node " + hostname + " does not have any local hard drives to update.", timerThreadLocationDict['127.0.0.1'])
						self.__exitOnError("Compute node " + hostname + " does not have any local hard drives to update; exiting program execution.")
				else:
					self.__exitOnError("Error(s) were encountered while initializing compute node " + hostname + "; check the compute node's log file for additional information; exiting program execution.")
			else:
				if versionInformationLogOnly:
					self.cursesThread.updateTimerThread("Done generating compute node " + hostname + "'s version report.", timerThreadLocationDict['127.0.0.1'])
				        logger.info("Compute node " + hostname + " was skipped, since it was already up to date.")
				elif resultDict['updateNeeded']:
					if updateOSHarddrives:
						self.cursesThread.updateTimerThread("Done initializing compute node " + hostname + " for an OS hard drive update.", timerThreadLocationDict['127.0.0.1'])
					else:
						self.cursesThread.updateTimerThread("Done initializing compute node " + hostname + ".", timerThreadLocationDict['127.0.0.1'])

					componentListDict['computeNodeList'].append(computeNode)
				else:
					self.cursesThread.updateTimerThread("Compute node " + hostname + " was skipped, since it was already up to date.", timerThreadLocationDict['127.0.0.1'])
				        logger.info("Compute node " + hostname + " was skipped, since it was already up to date.")
		else:
			#When compute nodes are being updated we check to see if the local host is included to be updated.
			if componentList[0] == 'Compute Node':
				try:
					computeNodeLogDir = logBaseDir + 'computeNodeLogs/'
					os.mkdir(computeNodeLogDir)
				except OSError as err:
					logger.error('Unable to create the log directory ' + computeNodeLogDir + '.\n' + str(err))
					self.__exitOnError("Unable to create the log directory ' + computeNodeLogDir + '; fix the problem and try again; exiting program execution.")

				while 1:
					skipUpdate = False

                                        self.cursesThread.getUserInput(['info', 'Is the local host being updated [y|n]: '])

                                        while not self.cursesThread.isUserInputReady():
                                                time.sleep(0.1)

                                        response = self.cursesThread.getUserResponse().strip().lower()

					if len(response) != 1:
                                                self.cursesThread.insertMessage(['error', '    A valid response is y|n; please try again.'])
                                                continue

					if not re.match('y|n', response):
                                                self.cursesThread.insertMessage(['error', '    A valid response is y|n; please try again.'])
                                                continue

					if response == 'y':
                                                try:
                                                        computeNode = ComputeNode(self.csurResourceDict.copy(), '127.0.0.1')
							computeNodeDict = computeNode.getComputeNodeDict()
							hostname = computeNodeDict['hostname']
						except KeyError as err:
							logger.error("The resource key (" + str(err) + ") was not present in the application's resource file.")
							self.__exitOnError("A resource key was not present in the application's resource file; check the application's log file for errors; exiting program execution.")

						#Run timer thread for feedback during initialization.
						timerThread = TimerThread('Initializing compute node ' + hostname + ' ... ')
						timerThread.daemon = True
						timerThread.start()

						if not '127.0.0.1' in timerThreadLocationDict:
							self.cursesThread.insertTimerThread(['', timerThread])
							timerThreadLocationDict['127.0.0.1'] = self.cursesThread.getTimerThreadLocation()
						else:
							self.cursesThread.insertTimerThread(['', timerThread], timerThreadLocationDict['127.0.0.1'])

                                                resultDict = computeNode.computeNodeInitialize(componentResourceList[1]['ComputeNodeResources'][:])

						timerThread.stopTimer()
						timerThread.join()

                                                if len(resultDict['errorMessages']) != 0:
                                                        if self.__tryAgainQuery('Compute Node', resultDict['errorMessages']):
                                                                continue
							else:
								self.cursesThread.updateTimerThread("Compute node " + hostname + " was skipped due to initialization errors.", timerThreadLocationDict['127.0.0.1'])
                                                else:
                                                        if resultDict['updateNeeded']:
								self.cursesThread.updateTimerThread("Done initializing compute node " + hostname + ".", timerThreadLocationDict['127.0.0.1'])
                                                                componentListDict['computeNodeList'].append(computeNode)
                                                        else:
								self.cursesThread.updateTimerThread("Compute node " + hostname + " was skipped, since it was already up to date.", timerThreadLocationDict['127.0.0.1'])
                                                                logger.info("Compute node " + hostname + " was skipped, since it was already up to date.")
                                        break

			#Now go through the list of components that were selected to be updated and initialize them for the update.
			for component in componentList:
				while 1:
					invalidResponse = False
					tryAgain = False

					self.cursesThread.getUserInput(['info', 'Enter the IP address of the ' + component + ' to be updated or enter to continue: '])

                                        while not self.cursesThread.isUserInputReady():
                                                time.sleep(0.1)

                                        ip = self.cursesThread.getUserResponse().strip()

					'''
					An empty string indicates the current component selection is done.
					Otherwise do some basic checking of the IP to see that its format is valid.
					'''
					if ip != '':
						#This just does a simple check of the IP.
						if not self.__checkIP(ip):
							continue

						if component == 'Compute Node':
							pass
						elif component == 'Network Switch':
							networkSwitchLogDir = logBaseDir + 'networkSwitchLogs/'

							if not os.path.exists(networkSwitchLogDir):
								try:
									os.mkdir(networkSwitchLogDir)
								except OSError as err:
									logger.error('Unable to create the log directory ' + networkSwitchLogDir + '.\n' + str(err))
									self.__exitOnError("Unable to create the log directory ' + networkSwitchLogDir + '; fix the problem and try again; exiting program execution.")

							skipNetworkSwitch = False

							'''
							Give a chance to confirm the input before moving on to test/update.
							'''
							if not self.__confirmInput(component, ip):
								continue

							networkSwitch = NetworkSwitch(generation, ip, networkSwitchLogDir, logLevel)

							'''
							count is used to determine if default credentials are used or in the case
							of a login password failure with default credentials the end user is prompted
							for the necessary credentials.
							'''
							count = 0

							while 1:	
								timerThread = TimerThread('Initializing network switch ' + ip + ' ... ')
								timerThread.daemon = True
								timerThread.start()

								if not ip in timerThreadLocationDict:
									self.cursesThread.insertTimerThread(['', timerThread])
									timerThreadLocationDict[ip] = self.cursesThread.getTimerThreadLocation()
								else:
									self.cursesThread.insertTimerThread(['', timerThread], timerThreadLocationDict[ip])

								if count == 0:							
									resultDict = networkSwitch.initializeSwitch(componentResourceList[1]['NetworkSwitchResources'][:])
								else:
									resultDict = networkSwitch.initializeSwitch(componentResourceList[1]['NetworkSwitchResources'][:], username=username, password=password)

								timerThread.stopTimer()
								timerThread.join()

								if len(resultDict['errorMessages']) != 0:
									errorMessage =  resultDict['errorMessages'][0]

									self.cursesThread.updateTimerThread('Initialization of network switch ' + ip + ' was interrupted due to errors.', timerThreadLocationDict[ip])

									if 'invalid password' in errorMessage:
										'''
										Give another chance to verify the IP address that was originally provided,
										since an invalid password can be caused by trying to log into the wrong system.
										'''
										if count == 0:
											if self.__confirmInput(component, ip, passwordFailure='passwordFailure'):
												(username, password) = self.__getCredentials(component, ip)
											else:
												tryAgain = True
												break

											count += 1
										else:
											if self.__tryAgainQuery(component, resultDict['errorMessages']):
												(username, password) = self.__getCredentials(component, ip)
											else:
												skipNetworkSwitch = True
												self.cursesThread.updateTimerThread('Skipping the update of network switch ' + ip + '.', timerThreadLocationDict[ip])
												logger.warn("An update for the network switch at '" + ip + "' was skipped.")
												break
									else:
										break
								else:
									self.cursesThread.updateTimerThread('Done initializing network switch ' + ip + '.', timerThreadLocationDict[ip])
									break

							if len(resultDict['errorMessages']) != 0 and not skipNetworkSwitch and not tryAgain:
								if self.__tryAgainQuery(component, resultDict['errorMessages']):
									continue
								else:
									self.cursesThread.updateTimerThread('Skipping the update of network switch ' + ip + '.', timerThreadLocationDict[ip])
									logger.warn("An update for the network switch at '" + ip + "' was skipped.")

							if len(resultDict['errorMessages']) == 0:
								if resultDict['updateNeeded']:
									componentListDict['networkSwitchList'].append(networkSwitch)
								else:
									logger.info("An update for network switch at '" + ip + "' was not needed, since it is already up to date.")
						elif component == 'SAN Switch':
							sanSwitchLogDir = logBaseDir + 'sanSwitchLogs/'

							if not os.path.exists(sanSwitchLogDir):
								try:
									os.mkdir(sanSwitchLogDir)
								except OSError as err:
									logger.error('Unable to create the log directory ' + sanSwitchLogDir + '.\n' + str(err))
									self.__exitOnError("Unable to create the log directory ' + sanSwitchLogDir + '; fix the problem and try again; exiting program execution.")

							skipSANSwitch = False

							count = 0

							while 1:
								self.cursesThread.getUserInput(['info', 'Enter the management IP address of the local system: '])

								while not self.cursesThread.isUserInputReady():
									time.sleep(0.1)

								localhostMgmtIP = self.cursesThread.getUserResponse().strip()

								if not self.__checkIP(localhostMgmtIP):
									continue
								else:
									break
							
							self.cursesThread.getUserInput(['info', 'Enter the user name of a user that can scp to/from this system: '])

							while not self.cursesThread.isUserInputReady():
								time.sleep(0.1)

							scpUsername = self.cursesThread.getUserResponse().strip()

							self.cursesThread.getUserInput(['info', 'Enter the password for ' + scpUsername + ': '], 'password')

							while not self.cursesThread.isUserInputReady():
								time.sleep(0.1)

							scpPassword = self.cursesThread.getUserPassword()

							if not self.__confirmInput(component, ip, localhostMgmtIP=localhostMgmtIP, scpUsername=scpUsername):
								continue
							
							sanSwitch = SANSwitch(ip, localhostMgmtIP, scpUsername, scpPassword, sanSwitchLogDir, logLevel)

							while 1:
								timerThread = TimerThread('Initializing SAN switch ' + ip + ' ... ')
								timerThread.daemon = True
								timerThread.start()

								if not ip in timerThreadLocationDict:
									self.cursesThread.insertTimerThread(['', timerThread])
									timerThreadLocationDict[ip] = self.cursesThread.getTimerThreadLocation()
								else:
									self.cursesThread.insertTimerThread(['', timerThread], timerThreadLocationDict[ip])

								if count == 0:							
									resultDict = sanSwitch.initializeSwitch(componentResourceList[1]['SANSwitchResources'][:])
								else:
									resultDict = sanSwitch.initializeSwitch(componentResourceList[1]['SANSwitchResources'][:], password=password)

								timerThread.stopTimer()
                                                                timerThread.join()

								if len(resultDict['errorMessages']) != 0:
                                                                        errorMessage =  resultDict['errorMessages'][0]

                                                                        self.cursesThread.updateTimerThread('Initialization of SAN switch ' + ip + ' was interrupted due to errors.', timerThreadLocationDict[ip])

                                                                        if 'invalid password' in errorMessage:
                                                                                if count == 0:
                                                                                        if self.__confirmInput(component, ip, passwordFailure='passwordFailure'):
                                                                                                (username, password) = self.__getCredentials(component, ip)
                                                                                        else:
                                                                                                tryAgain = True
                                                                                                break

                                                                                        count += 1
                                                                                else:
                                                                                        if self.__tryAgainQuery(component, resultDict['errorMessages']):
                                                                                                (username, password) = self.__getCredentials(component, ip)
                                                                                        else:
                                                                                                skipSANSwitch = True
												self.cursesThread.updateTimerThread('Skipping the update of SAN switch ' + ip + '.', timerThreadLocationDict[ip])
												logger.warn("An update for the SAN switch at '" + ip + "' was skipped.")
                                                                                                break
                                                                        else:
                                                                                break
                                                                else:
                                                                        self.cursesThread.updateTimerThread('Done initializing SAN switch ' + ip + '.', timerThreadLocationDict[ip])
                                                                        break

                                                        if len(resultDict['errorMessages']) != 0 and not skipSANSwitch and not tryAgain:
                                                                if self.__tryAgainQuery(component, resultDict['errorMessages']):
                                                                        continue
								else:
									self.cursesThread.updateTimerThread('Skipping the update of SAN switch ' + ip + '.', timerThreadLocationDict[ip])
									logger.warn("An update for the SAN switch at '" + ip + "' was skipped.")

                                                        if len(resultDict['errorMessages']) == 0:
                                                                if resultDict['updateNeeded']:
                                                                        componentListDict['sanSwitchList'].append(sanSwitch)

									if resultDict['multipleUpgradesRequired']:
										self.csurResourceDict['multipleUpgradesRequiredDict']['SAN Switches'].append(ip)
                                                                else:
                                                                        logger.info("An update for SAN switch at '" + ip + "' was not needed, since it is already up to date.")
						elif component == '3PAR StoreServ':
							threePARLogDir = logBaseDir + 'threePARLogs/'

							if not os.path.exists(threePARLogDir):
								try:
									os.mkdir(threePARLogDir)
								except OSError as err:
									logger.error('Unable to create the log directory ' + threePARLogDir + '.\n' + str(err))
									self.__exitOnError("Unable to create the log directory ' + threePARLogDir + '; fix the problem and try again; exiting program execution.")

							skipThreePAR = False

							'''
							Give a chance to confirm the input before moving on to test/update.
							'''
							if not self.__confirmInput(component, ip):
								continue

							count = 0

							threePAR = ThreePAR(ip, threePARLogDir, logLevel)

							while 1:
								timerThread = TimerThread('Initializing 3PAR ' + ip + ' ... ')
								timerThread.daemon = True
								timerThread.start()

								if not ip in timerThreadLocationDict:
									self.cursesThread.insertTimerThread(['', timerThread])
									timerThreadLocationDict[ip] = self.cursesThread.getTimerThreadLocation()
								else:
									self.cursesThread.insertTimerThread(['', timerThread], timerThreadLocationDict[ip])

								if count == 0:							
									resultDict = threePAR.initialize3PAR(generation, componentResourceList[1]['3PARStoreServResources'][:])
								else:
									resultDict = threePAR.initialize3PAR(generation, componentResourceList[1]['3PARStoreServResources'][:], username=username, password=password)

								timerThread.stopTimer()
								timerThread.join()

								if len(resultDict['errorMessages']) != 0:
									errorMessage =  resultDict['errorMessages'][0]

									self.cursesThread.updateTimerThread('Initialization of 3PAR ' + ip + ' was interrupted due to errors.', timerThreadLocationDict[ip])

									if 'invalid password' in errorMessage or 'spvar password resource key error' in errorMessage:
										'''
										Give another chance to verify the IP address that was originally provided,
										since an invalid password can be caused by trying to log into the wrong system
										if the password failure is not spvar.
										'''
										if count == 0 and not 'spvar password resource key error' in errorMessage:
											if self.__confirmInput(component, ip, passwordFailure='passwordFailure'):
												(username, password) = self.__getCredentials(component, ip)
											else:
												tryAgain = True
												break

											count += 1
										else:
											if self.__tryAgainQuery(component, resultDict['errorMessages']):
												(username, password) = self.__getCredentials(component, ip)
					
												if count == 0:
													count += 1
											else:
												skipThreePAR = True
												self.cursesThread.updateTimerThread('Skipping the update of 3PAR ' + ip + '.', timerThreadLocationDict[ip])
												logger.info("An update for the 3PAR at '" + ip + "' was skipped.")
												break
									else:
										break
								else:
									self.cursesThread.updateTimerThread('Done initializing 3PAR ' + ip + '.', timerThreadLocationDict[ip])
									break

							if len(resultDict['errorMessages']) != 0 and not skipThreePAR and not tryAgain:
								if self.__tryAgainQuery(component, resultDict['errorMessages']):
									continue
								else:
									self.cursesThread.updateTimerThread('Skipping the update of 3PAR ' + ip + '.', timerThreadLocationDict[ip])
									logger.info("An update for the 3PAR at '" + ip + "' was skipped.")

							if len(resultDict['errorMessages']) == 0:
								if resultDict['spUpdateNeeded'] or resultDict['storeServUpdateNeeded']:
									componentListDict['storeServList'].append(threePAR)
								else:
									logger.info("An update for 3PAR at '" + ip + "' was not needed, since it is already up to date.")
					else:
						break

		#Save the timerThreadLocationDict, since it will be referred to again during the actual component updates.
		self.csurResourceDict['timerThreadLocationDict'] = timerThreadLocationDict

		'''
		If any components require multiple upgrades then write out the component information (type, ip) so the person 
		doing the upgrades can keep track of the components.
		'''
		if any(len(self.csurResourceDict['multipleUpgradesRequiredDict'][i]) != 0 for i in self.csurResourceDict['multipleUpgradesRequiredDict']):
			try:
				multipleUpgradesRequiredLog = open(logBaseDir + 'multipleUpgradesRequired.log', w)

				iteration = 0

				for i in self.csurResourceDict['multipleUpgradesRequiredDict']:
					if len(self.csurResourceDict['multipleUpgradesRequiredDict'][i]) != 0:
						#This will add a blank line between sections; skipping the first time through.
						if iteration == 0:
							iteration += 1
						else:
							multipleUpgradesRequiredLog.write('\n')
						
						count = len(self.csurResourceDict['multipleUpgradesRequiredDict'][i])
						multipleUpgradesRequiredLog.write(i + '\n')

						for j in range(0, count):
							multipleUpgradesRequiredLog.write(self.csurResourceDict['multipleUpgradesRequiredDict'][i][j] + '\n')

			except IOError as err:
				pass

		#Return the dictionary containing the list of components that need to be updated.
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
			self.cursesThread.insertMessage(['error', 'An invalid IP was provided, please try again.'])
			return False

		for number in ipList:
			try:
				number = int(number)
			except ValueError:
				self.cursesThread.insertMessage(['error', 'An invalid IP was provided, please try again.'])
				return False

			if number < 0 or number > 255: 
				self.cursesThread.insertMessage(['error', 'An invalid IP was provided, please try again.'])
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
			if 'resource' in errorMessage and not 'spvar password resource key error' in errorMessage:
				self.__exitOnError(errorMessage + " Fix the problem and try again; exiting program execution.")

		self.cursesThread.insertMessage(['error', 'The following error(s) was encountered while checking the ' + component + ':'])

		for errorMessage in errorMessages:
			self.cursesThread.insertMessage(['error', '    ' + errorMessage])

		while 1:
			self.cursesThread.getUserInput(['info', 'Do you want to fix the problem and try again [y|n]: '])

			while not self.cursesThread.isUserInputReady():
				time.sleep(0.1)

			response = self.cursesThread.getUserResponse().strip().lower()

			if len(response) != 1:
				self.cursesThread.insertMessage(['error', 'A valid response is y|n.  Please try again.'])
				continue

			if not re.match('y|n', response):
				self.cursesThread.insertMessage(['error', 'A valid response is y|n.  Please try again.'])
				continue

			if response == 'y':
				tryAgain = True						

			break

		return tryAgain

	#End __tryAgainQuery(self, component, errorMessages):


	def __confirmInput(self, component, ip, **kwargs):
		validInput = False

		if 'passwordFailure' in kwargs:
			self.cursesThread.insertMessage(['error', 'A login attempt to the ' + component + ' at ' + ip + ' failed using default credentials.'])
			self.cursesThread.insertMessage(['info', ' '])

		self.cursesThread.insertMessage(['info', 'The following information was provided for the ' + component + ' to be updated:'])
		self.cursesThread.insertMessage(['info', '    IP: ' + ip])

		if 'username' in kwargs:
			self.cursesThread.insertMessage(['info', '    User Name: ' + kwargs['username']])

		if 'localhostMgmtIP' in kwargs:
			self.cursesThread.insertMessage(['info', '    Local Host Management IP: ' + kwargs['localhostMgmtIP']])

		if 'scpUsername' in kwargs:
			self.cursesThread.insertMessage(['info', '    Local Host scp User Name: ' + kwargs['scpUsername']])

		while 1:
			self.cursesThread.insertMessage(['info', ' '])
			self.cursesThread.getUserInput(['info', 'Is the above information correct [y|n]: '])

			while not self.cursesThread.isUserInputReady():
				time.sleep(0.1)

			response = self.cursesThread.getUserResponse().strip().lower()

			if len(response) != 1:
				self.cursesThread.insertMessage(['error', 'A valid response is y|n.  Please try again.'])
				continue

			if not re.match('y|n', response):
				self.cursesThread.insertMessage(['error', 'A valid response is y|n.  Please try again.'])
				continue
			else:
				break

		if response == 'y':
			validInput = True						

		return validInput
		
	#End __confirmInput(self, component, ip, username):


	'''
	This function is used to get the username and password for a component 
	if the defaults do not work.
	'''
	def __getCredentials(self, component, ip):
		self.cursesThread.insertMessage(['info', ' '])

		#The SAN switch username is just a place holder, since it is set by default.
		if component != 'SAN Switch':
			self.cursesThread.getUserInput(['info', 'Enter the admin user name for the ' + component + ' at ' + ip + ': '])

			while not self.cursesThread.isUserInputReady():
				time.sleep(0.1)

			username = self.cursesThread.getUserResponse().strip()
		else:
			username = 'admin'

		self.cursesThread.insertMessage(['info', ' '])
		self.cursesThread.getUserInput(['info', 'Enter the password for ' + username + ': '], 'password')

		while not self.cursesThread.isUserInputReady():
			time.sleep(0.1)
		
		password = self.cursesThread.getUserPassword()

		return (username, password)

	#End __getCredentials(self, component, ip):


        def __exitOnError(self, message):
                self.cursesThread.insertMessage(['error', message])
                time.sleep(10.0)
                self.cursesThread.join()
                exit(1)
        #End  __exitOnError(self, message):

#End class GetComponentInformation:
