# Embedded file name: ./bin/modules/systemConfiguration.py
import re
import subprocess
import time
import os

class SystemConfiguration():

    def __init__(self, cursesThread):
        self.cursesThread = cursesThread

    def getConfiguration(self, healthUserInputsFile):
        self.healthUserInputsFile = healthUserInputsFile
        userInputsUpdates = ''
        systemConfigurationDict = {}
        systemHWInfo = self.__getHWInfo()
        while 1:
            startOver = False
            if 'Scale-' in systemHWInfo:
                if 'Scale-up' in systemHWInfo:
                    selection = '1'
                else:
                    selection = '2'
            else:
                self.cursesThread.insertMessage(['info', ' '])
                self.cursesThread.insertMessage(['info', 'Select the system type: '])
                self.cursesThread.insertMessage(['info', '    1. Scale-up'])
                self.cursesThread.insertMessage(['info', '    2. Scale-out'])
                self.cursesThread.getUserInput(['info', ''])
                while not self.cursesThread.isUserInputReady():
                    time.sleep(0.1)

                selection = self.cursesThread.getUserResponse().strip()
            if selection == '1':
                while 1:
                    if 'CS500' in systemHWInfo:
                        selection = '1'
                    elif 'Gen1' in systemHWInfo:
                        selection = '3'
                    else:
                        self.cursesThread.insertMessage(['info', "Select the configuration or 'q' to quit; 'x' to start over: "])
                        self.cursesThread.insertMessage(['info', '    1. CS500 Scale-up'])
                        self.cursesThread.insertMessage(['info', '    2. CS900 Scale-up'])
                        self.cursesThread.insertMessage(['info', '    3. Gen1.0 Scale-up'])
                        self.cursesThread.getUserInput(['info', ''])
                        while not self.cursesThread.isUserInputReady():
                            time.sleep(0.1)

                        selection = self.cursesThread.getUserResponse().strip()
                    if selection == '1':
                        scaleUpType = 'CS500'
                    elif selection == '2':
                        self.cursesThread.insertMessage(['error', 'The CS900 Scale-up is not supported at this time; please try again.'])
                        startOver = True
                        continue
                        scaleUpType = 'CS900'
                    elif selection == '3':
                        scaleUpType = 'Gen1.0'
                    elif selection == 'q':
                        self.cursesThread.join()
                        exit(0)
                    elif selection == 'x':
                        startOver = True
                    else:
                        self.cursesThread.insertMessage(['error', 'An invalid selection was made; please try again.'])
                        continue
                    if startOver:
                        break
                    if not ('Scale-up' in systemHWInfo and scaleUpType in systemHWInfo):
                        if self.__confirmSelection({'Scale-up': systemHWInfo}):
                            systemConfigurationDict['systemType'] = {'Scale-up': systemHWInfo}
                            if userInputsUpdates == None:
                                userInputsUpdates == systemHWInfo
                            if 'Scale-up' not in systemHWInfo:
                                userInputsUpdates = userInputsUpdates + ' ' + 'Scale-up'
                            else:
                                userInputsUpdates = userInputsUpdates + ' ' + scaleUpType
                            break
                        else:
                            startOver = True
                            break
                    else:
                        systemConfigurationDict['systemType'] = {'Scale-up': scaleUpType}
                        break

                if startOver:
                    continue
            elif selection == '2':
                self.cursesThread.insertMessage(['error', 'The Scale-out systems are not supported at this time; please try again.'])
                startOver = True
                continue
                while 1:
                    reselect = False
                    self.cursesThread.insertMessage(['info', "Select the configuration or 'q' to quit; 'x' to start over:"])
                    self.cursesThread.insertMessage(['info', '    1. CS500 Scale-out'])
                    self.cursesThread.insertMessage(['info', '    2. CS900 Scale-out'])
                    self.cursesThread.insertMessage(['info', '    3. Gen1.0 Scale-out'])
                    self.cursesThread.insertMessage(['info', '    4. Gen1.2 Scale-out'])
                    self.cursesThread.getUserInput(['info', ''])
                    while not self.cursesThread.isUserInputReady():
                        time.sleep(0.1)

                    selection = self.cursesThread.getUserResponse().strip()
                    if selection == '1':
                        scaleOutType = 'CS500'
                        while 1:
                            self.cursesThread.getUserInput(['info', ' '])
                            self.cursesThread.insertMessage(['info', "Select the configuration or 'r' to reselect the configuration: "])
                            self.cursesThread.insertMessage(['info', '    1. CS500 Ivy Bridge'])
                            self.cursesThread.insertMessage(['info', '    2. CS500 Haswell'])
                            self.cursesThread.insertMessage(['info', '    3. CS500 Broadwell'])
                            self.cursesThread.getUserInput(['info', ''])
                            while not self.cursesThread.isUserInputReady():
                                time.sleep(0.1)

                            selection = self.cursesThread.getUserResponse().strip()
                            if selection == '1' or selection == '2':
                                if selection == '1':
                                    generation = 'Ivy Bridge'
                                else:
                                    generation = 'Haswell'
                                componentList = self.__getCS500ComponentList()
                                if self.__confirmSelection({'Scale-out': [scaleOutType, componentList, generation]}):
                                    systemConfigurationDict['systemType'] = {'Scale-out': {'scaleOutType': 'CS500',
                                                   'generation': generation,
                                                   'componentList': componentList}}
                                    break
                                else:
                                    startOver = True
                                    break
                            elif selection == '3':
                                self.cursesThread.insertMessage(['error', 'The Broadwell Scale-out is not supported at this time; please try again.'])
                                continue
                                generation = 'Haswell'
                            elif selection == 'r':
                                reselect = True
                            else:
                                self.cursesThread.insertMessage(['error', 'An invalid selection was made; please try again.'])
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
                        self.cursesThread.join()
                        exit(0)
                    elif selection == 'x':
                        startOver = True
                    else:
                        self.cursesThread.insertMessage(['error', 'An invalid selection was made; please try again.'])
                        continue
                    if reselect:
                        continue
                    else:
                        break

                if startOver:
                    continue
            else:
                self.cursesThread.insertMessage(['error', 'An invalid selection was made; please try again.'])
                continue
            break

        if len(userInputsUpdates) > 0:
            self.__putUserInputsUpdate(systemHWInfo + userInputsUpdates)
        return systemConfigurationDict

    def __confirmSelection(self, selection):
        validInput = False
        self.cursesThread.insertMessage(['info', 'Is the following system information correct [y|n]:'])
        if 'Scale-up' in selection:
            self.cursesThread.insertMessage(['info', '    ' + selection['Scale-up'] + ' Scale-up'])
        else:
            ScaleOutList = selection['Scale-out']
            self.cursesThread.insertMessage(['info', '    ' + ScaleOutList[0] + ' ' + ScaleOutList[2] + ' Scale-out:'])
            self.cursesThread.insertMessage(['info', ' '])
            self.cursesThread.insertMessage(['info', '    Components that have been selected to update:'])
            for component in ScaleOutList[1]:
                self.cursesThread.insertMessage(['info', '        ' + component])

        while 1:
            self.cursesThread.getUserInput(['info', ''])
            while not self.cursesThread.isUserInputReady():
                time.sleep(0.1)

            response = self.cursesThread.getUserResponse().strip().lower()
            if len(response) != 1:
                self.cursesThread.insertMessage(['error', '    A valid response is y|n. Please try again.'])
                continue
            if not re.match('y|n', response):
                self.cursesThread.insertMessage(['error', '    A valid response is y|n. Please try again.'])
                continue
            else:
                break

        if response == 'y':
            validInput = True
        return validInput

    def __getHWInfo(self):
        systemListDict = {'DL580Gen8': 'CS500 IvyBridge',
         'DL580Gen9': 'CS500',
         'DL580G7': 'Gen1.0',
         'DL980G7': 'Gen1.0',
         '': ''}
        processorListDict = {'E7-8890v3': 'Haswell',
         'E7-8890v4': 'Broadwell',
         'E7-8880v3': 'Haswell',
         'E7-8880Lv3': 'Haswell',
         'Unkn': ''}
        command = 'dmidecode -s system-product-name'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            self.cursesThread.insertMessage(['warn', ' Unable to get the system model using (' + command + '). error: ' + err])
        else:
            out = out.strip()
            try:
                systemModel = re.match('[a-z,0-9]+\\s+(.*)', out, re.IGNORECASE).group(1).replace(' ', '')
            except AttributeError as err:
                self.cursesThread.insertMessage(['warn', ' There was a system model match error when trying to match against ' + out + ':\n' + str(err) + '.'])
                systemModel = ''

        command = 'dmidecode -s processor-version'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            self.cursesThread.insertMessage(['warn', ' Unable to get the processor version using (' + command + '). error: ' + err])
        else:
            out = out.strip()
            try:
                processorVersion = re.search('CPU (E\\d-\\s*\\d{4}\\w* v\\d)', out).group(1).replace(' ', '')
            except AttributeError as err:
                self.cursesThread.insertMessage(['warn', ' There was a processor version match error when trying to match against ' + out + ':\n' + str(err) + '.'])
                processorVersion = ''

        system = systemListDict[systemModel]
        if systemModel == 'DL580Gen9':
            system = system + ' ' + processorListDict[processorVersion]
        errors = False
        if os.path.isfile(self.healthUserInputsFile):
            try:
                with open(self.healthUserInputsFile) as f:
                    resources = f.read()
            except IOError as err:
                self.cursesThread.insertMessage(['warn', "Unable to open User's Inputs file (" + self.healthUserInputsFile + ') for reading.\n' + str(err) + '.'])
                errors = True

            if not errors:
                if system in resources:
                    system = resources
        self.cursesThread.insertMessage(['info', ' System Model: ' + system + '.'])
        return system

    def __putUserInputsUpdate(self, newInputsRecord):
        try:
            with open(self.healthUserInputsFile, 'w') as f:
                f.write(newInputsRecord)
        except IOError as err:
            self.cursesThread.insertMessage(['warn', "Unable to write to User's Inputs file (" + self.healthUserInputsFile + ') ' + str(err) + '.'])

    def __getCS500ComponentList(self):
        componentDict = {'1': 'Compute Node',
         '2': '3PAR StoreServ',
         '3': 'SAN Switch',
         '4': 'Network Switch'}
        componentList = []
        count = len(componentDict)
        while 1:
            self.cursesThread.insertMessage(['info', ' '])
            self.cursesThread.insertMessage(['info', 'Enter a comma separated list of the Components or press enter for everything:'])
            self.cursesThread.insertMessage(['info', '    1. Compute Nodes'])
            self.cursesThread.insertMessage(['info', '    2. 3PAR StoreServ'])
            self.cursesThread.insertMessage(['info', '    3. SAN Switches'])
            self.cursesThread.insertMessage(['info', '    4. Network Switches'])
            self.cursesThread.getUserInput(['info', ''])
            while not self.cursesThread.isUserInputReady():
                time.sleep(0.1)

            selection = self.cursesThread.getUserResponse().strip()
            if len(selection) == 0:
                componentList = ['Compute Node',
                 '3PAR StoreServ',
                 'SAN Switch',
                 'Network Switch']
                break
            elif self.__checkSelection(selection, count):
                selection = re.sub('\\s+', '', selection)
                componentSelectionList = selection.split(',')
                componentSelectionList.sort()
                for selection in componentSelectionList:
                    componentList.append(componentDict[selection])

                break
            else:
                self.cursesThread.insertMessage(['error', 'An invalid response was provided, please try again.'])
                continue

        return componentList

    def __checkSelection(self, selection, count):
        lengthFailure = False
        allowedCharacters = ',' + ''.join((str(i) for i in range(1, count + 1)))
        selection = re.sub('\\s+', '', selection)
        if all((chr in allowedCharacters for chr in selection)):
            selectionList = selection.split(',')
            for i in selectionList:
                if len(i) > 1:
                    lengthFailure = True
                    break

            if lengthFailure:
                return False
            else:
                return True
        else:
            return False


if __name__ == '__main__':
    systemConfiguration = SystemConfiguration()
    dict = systemConfiguration.getConfiguration()
    print dict