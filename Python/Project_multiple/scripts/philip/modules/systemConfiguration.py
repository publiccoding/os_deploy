#!/usr/bin/python


import re
import time


'''
This class is used to gather the system configuration information from the user.
'''
class SystemConfiguration:
        def __init__(self, cursesThread):
                self.cursesThread = cursesThread

        #End __init__(self, cursesThread):


        '''
        This function prompts the user for the type of update that is to be performed.
	Tabs are a 4 character indent.
        '''
        def getConfiguration(self):
		systemConfigurationDict = {}

                while(1):
			startOver = False

			self.cursesThread.insertMessage(['info', ' '])
			self.cursesThread.insertMessage(['info', 'Select the system type to be updated: '])
			self.cursesThread.insertMessage(['info', '    1. Scale-up'])
			self.cursesThread.insertMessage(['info', '    2. Scale-out'])
			self.cursesThread.getUserInput(['info', ' '])

			#Wait till the user presses enter to collect their response.
			while not self.cursesThread.isUserInputReady():
			        time.sleep(0.1)

			selection = self.cursesThread.getUserResponse().strip()

                        if selection == '1':
				while 1:
					self.cursesThread.insertMessage(['info', "Select the configuration to be updated or 'q' to quit; 'x' to start over: "])
					self.cursesThread.insertMessage(['info', '    1. CS500 Scale-up'])
					self.cursesThread.insertMessage(['info', '    2. CS900 Scale-up'])
					self.cursesThread.insertMessage(['info', '    3. Gen1.0 Scale-up'])

					self.cursesThread.getUserInput(['info', ' '])

					while not self.cursesThread.isUserInputReady():
						time.sleep(0.1)

					selection = self.cursesThread.getUserResponse().strip()

                                        if selection == '1':
                                                scaleUpType = 'CS500'
                                        elif selection == '2':
						self.cursesThread.getUserInput(['info', ' '])
						self.cursesThread.insertMessage(['error', 'The CS900 Scale-up is not supported at this time; please try again.'])
						continue
                                                scaleUpType = 'CS900'
                                        elif selection == '3':
                                                scaleUpType = 'Gen1.0'
                                        elif selection == 'q':
						#Shut down curses mode before exiting.
						self.cursesThread.join()
                               			exit(0)
                                        elif selection == 'x':
                               			startOver = True                 
                                        else:
						self.cursesThread.getUserInput(['info', ' '])
						self.cursesThread.insertMessage(['error', 'An invalid selection was made; please try again. '])
                                                continue

					if startOver:
						break

					if self.__confirmSelection({'Scale-up' : scaleUpType}):
						systemConfigurationDict['systemType'] = {'Scale-up' : scaleUpType}
						break
					else:
                               			startOver = True                 
						break

				if startOver:
					continue
                        elif selection == '2':
				self.cursesThread.getUserInput(['info', ' '])
				self.cursesThread.insertMessage(['error', 'Scale-out systems are not supported at this time; please try again.'])
				continue

                                while 1:
					reselect = False

					self.cursesThread.insertMessage(['info', "Select the configuration to be updated or 'q' to quit; 'x' to start over: "])
					self.cursesThread.insertMessage(['info', '    1. CS500 Scale-out'])
					self.cursesThread.insertMessage(['info', '    2. CS900 Scale-out'])
					self.cursesThread.insertMessage(['info', '    3. Gen1.0 Scale-out'])
					self.cursesThread.insertMessage(['info', '    4. Gen1.2 Scale-out'])

					self.cursesThread.getUserInput(['info', ' '])

					while not self.cursesThread.isUserInputReady():
						time.sleep(0.1)

					selection = self.cursesThread.getUserResponse().strip()

                                        if selection == '1':
						self.cursesThread.insertMessage(['error', 'The CS500 Scale-out is not supported at this time; please try again.'])
						continue
                                                scaleOutType = 'CS500'

						while 1:
							self.cursesThread.getUserInput(['info', ' '])
							self.cursesThread.insertMessage(['info', "Select the configuration to be updated or 'r' to reselect the configuration: "])
							self.cursesThread.insertMessage(['info', '    1. CS500 Ivy Bridge'])
							self.cursesThread.insertMessage(['info', '    2. CS500 Haswell'])
							self.cursesThread.insertMessage(['info', '    3. CS500 Broadwell'])

							self.cursesThread.getUserInput(['info', ' '])

							while not self.cursesThread.isUserInputReady():
								time.sleep(0.1)

							selection = self.cursesThread.getUserResponse().strip()

							if selection == '1' or selection == '2':
								if selection == '1':
									generation = 'Ivy Bridge'
								else:
									generation = 'Haswell'

								componentList = self.__getCS500ComponentList()
								if self.__confirmSelection({'Scale-out' : [scaleOutType, componentList]}):
									systemConfigurationDict['systemType'] = {'Scale-out' : {'scaleOutType' : 'CS500', 'generation' : generation, 'componentList' : componentList}}
									break
								else:
									startOver = True                 
									break
							elif selection == '3':
								self.cursesThread.getUserInput(['info', ' '])
								self.cursesThread.insertMessage(['error', 'The Broadwell Scale-out is not supported at this time; please try again.'])
								continue
								generation = 'Haswell'
							elif selection == 'r':
								reselect = True
							else:
								self.cursesThread.insertMessage(['error', 'An invalid selection was made; please try again. '])
								continue

							if reselect:
								break
                                        elif selection == '2':
						self.cursesThread.insertMessage(['error', 'The CS900 Scale-out is not supported at this time; please try again.'])
						continue
                                                scaleOutType = 'CS900'
                                        elif selection == '3':
						self.cursesThread.insertMessage(['error', 'The Gen1.0 Scale-out is not supported at this time; please try again.'])
						continue
                                                scaleOutType = 'Gen1.0'
                                        elif selection == '4':
						self.cursesThread.insertMessage(['error', 'The Gen1.2 Scale-out is not supported at this time; please try again.'])
						continue
                                                scaleOutType = 'Gen1.2'
                                        elif selection == 'q':
						#Shut down curses mode before exiting.
						self.cursesThread.join()
                               			exit(0)
                                        elif selection == 'x':
                               			startOver = True                 
                                        else:
						self.cursesThread.insertMessage(['error', 'An invalid selection was made; please try again. '])
                                                continue

					if reselect:
						continue
					else:
						break

				if startOver:
					continue
                        else:
				self.cursesThread.insertMessage(['error', 'An invalid selection was made; please try again. '])
                                continue

                        break

		return systemConfigurationDict

        #End getConfiguration():


	def __confirmSelection(self, selection):
		validInput = False

		self.cursesThread.insertMessage(['info', 'Is the following system update information correct [y|n]:'])

		if 'Scale-up' in selection:
			self.cursesThread.insertMessage(['info', '    ' + selection['Scale-up'] + ' Scale-up'])
		else:
			ScaleOutList = selection['Scale-out']

			self.cursesThread.insertMessage(['info', '    ' + ScaleOutList[0] + ' Scale-out:'])
			self.cursesThread.insertMessage(['info', ' '])
			self.cursesThread.insertMessage(['info', '    Components that have been selected to update:'])

			for component in ScaleOutList[1]:
				self.cursesThread.insertMessage(['info', '        ' + component])

		while 1:
			self.cursesThread.getUserInput(['info', ' '])

			while not self.cursesThread.isUserInputReady():
				time.sleep(0.1)

			response = self.cursesThread.getUserResponse().strip().lower()

			if len(response) != 1:
				self.cursesThread.insertMessage(['error', '    A valid response is y|n. Please try again. '])
				continue

			if not re.match('y|n', response):
				self.cursesThread.insertMessage(['error', '    A valid response is y|n. Please try again. '])
				continue
			else:
				break

		if response == 'y':
			validInput = True

		return validInput

	#End __confirmInput(self, selection):


	def __getCS500ComponentList(self):
		componentDict = {'1' : 'Compute Node', '2' : '3PAR StoreServ', '3' : 'SAN Switch', '4' : 'Network Switch'}
		componentList = []

		while 1:
			invalidResponse = False

			self.cursesThread.insertMessage(['info', ' '])
			self.cursesThread.insertMessage(['info', 'Enter a comma separated list of the Components to be updated or press enter for everything:'])
			self.cursesThread.insertMessage(['info', '    1. Compute Nodes'])
			self.cursesThread.insertMessage(['info', '    2. 3PAR StoreServ'])
			self.cursesThread.insertMessage(['info', '    3. SAN Switches'])
			self.cursesThread.insertMessage(['info', '    4. Network Switches'])

			self.cursesThread.getUserInput(['info', ' '])

			while not self.cursesThread.isUserInputReady():
				time.sleep(0.1)

			selection = self.cursesThread.getUserResponse().strip()

			if ',' in selection:
				selection = re.sub('\s+', '', selection)
				componentSelectionList = selection.split(',')
				componentSelectionList.sort()

				for selection in componentSelectionList:
					try:
						selection = int(selection)
					except ValueError:
						self.cursesThread.insertMessage(['error', 'An invalid response was provided, please try again. '])
						invalidResponse = True
						break

					if selection < 1 or selection > 4:
						self.cursesThread.insertMessage(['error', 'An invalid response was provided, please try again. '])
						invalidResponse = True
						break

				if not invalidResponse:
					for selection in componentSelectionList:
						componentList.append(componentDict[selection])
			else:
				if len(selection) == 0:
					componentList = ['Compute Node', '3PAR StoreServ', 'SAN Switch', 'Network Switch']
				else:
					try:
						var = int(selection)
					except ValueError:
						self.cursesThread.insertMessage(['error', 'An invalid response was provided, please try again. '])
						invalidResponse = True
						break

					if var < 1 or var > 4:
						self.cursesThread.insertMessage(['error', 'An invalid response was provided, please try again. '])
						invalidResponse = True
					else:
						componentList.append(componentDict[selection])

			if not invalidResponse:
				break

		return componentList

	#End __getCS500ComponentList(self):

	
#This section is for running the module standalone for debugging purposes.
if __name__ == '__main__':
	systemConfiguration = SystemConfiguration()

	dict = systemConfiguration.getConfiguration()

	print dict
