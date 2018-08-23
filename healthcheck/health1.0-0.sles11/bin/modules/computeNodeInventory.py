# Embedded file name: /hp/support/health/bin/modules/computeNodeInventory.py
import re
import os
import subprocess
import logging
import datetime

class ComputeNodeInventory():

    def __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources, healthResourceDict):
        self.computeNodeResources = computeNodeResources
        self.CSURDesc = 'HPE Converged Systems Upgrade Release'
        self.noPMCFirmwareUpdateModels = noPMCFirmwareUpdateModels
        self.osDistListDict = {'SLES11.3': 'SLES4SAP 11 SP3',
         'SLES11.4': 'SLES4SAP 11 SP4',
         'SLES12.1': 'SLES4SAP 12 SP1',
         'RHEL6.7': 'RHEL4SAP 6 SP7',
         'RHEL7.2': 'RHEL4SAP 7 SP2'}
        systemListDict = {'DL580Gen8': 'CS500 Ivy Bridge',
         'DL580Gen9': 'CS500',
         'DL580G7': 'Gen1.0',
         'DL980G7': 'Gen1.0'}
        processorListDict = {'E7-8890v3': 'Haswell',
         'E7-8890v4': 'Broadwell',
         'E7-8880v3': 'Haswell',
         'E7-8880Lv3': 'Haswell'}
        self.externalStoragePresent = False
        loggerName = computeNodeDict['loggerName']
        hostname = computeNodeDict['hostname']
        self.logger = logging.getLogger(loggerName)
        try:
            self.csurVersionReleaseFile = healthResourceDict['versionInformationFile']
            self.osPatchUpdateReleaseFile = healthResourceDict['osPatchUpdateReleaseFile']
            self.hbaDrivers = healthResourceDict['hbaDrivers']
            self.hbaSoftware = healthResourceDict['hbaSoftware']
            self.localStorageDrivers = healthResourceDict['localStorageDrivers']
            self.localStorageSoftware = healthResourceDict['localStorageSoftware']
            self.pciIdsFile = healthResourceDict['healthBasePath'] + '/resourceFiles/' + healthResourceDict['pciIdsFile']
            self.programVersion = healthResourceDict['programVersion']
            self.systemType = healthResourceDict['systemType']
            self.unsupportedUpgradableDistLevels = healthResourceDict['unsupportedUpgradableDistLevels']
        except KeyError as err:
            raise KeyError('Missing key from health App resource file: ' + str(err))

        try:
            self.osDistLevel = computeNodeDict['osDistLevel']
            self.processorVersion = computeNodeDict['processorVersion']
            self.systemModel = computeNodeDict['systemModel']
        except KeyError as err:
            raise KeyError('Missing key from compute Node resource file: ' + str(err))

        try:
            self.CSURRelease = re.search('Version:\\s*([a-z0-9._-]+)', healthResourceDict['releaseNotes'], re.IGNORECASE).group(1)
        except (AttributeError, KeyError) as err:
            self.logger.error("Missing key 'releaseNotes' or match key error from healthApp Resource file." + str(err))
            self.CSURRelease = 'Unknown'

        try:
            self.osPatchUpdateRelease = re.search('Version:\\s*([a-z0-9._-]+)', healthResourceDict['osPatchUpdateReleaseNotes'], re.IGNORECASE).group(1)
        except (AttributeError, KeyError) as err:
            self.logger.error("Missing key 'osPatchReleaseNotes' or match key error from healthApp Resource file." + str(err))
            self.osPatchUpdateRelease = 'Unknown'

        self.logger.debug('OS Patch Update Release File: ' + self.osPatchUpdateReleaseFile + '.')
        self.versionInformationLogger = logging.getLogger('versionInformationLog')
        self.versionInformationLogger.info('-' * 100)
        Date = datetime.datetime.now().strftime('%d %b %Y_%H:%M:%S')
        self.versionInformationLogger.info('\n' + '{0:40}'.format('HPE SAP HANA Health Check Report ') + '{0:30} {1}'.format(' ', Date) + '\n')
        system = systemListDict[self.systemModel]
        if self.systemModel == 'DL580Gen9':
            system = system + ' ' + processorListDict[self.processorVersion]
        if 'Scale-up' in healthResourceDict['systemType']:
            system = system + ' Scale-up'
        else:
            system = system + ' Scale-out'
        self.versionInformationLogger.info('{0:40}'.format('System: \t' + system))
        self.versionInformationLogger.info('{0:40}'.format('System Name: \t' + hostname))
        self.versionInformationLogger.info('{0:40}'.format('System Model: \t' + self.systemModel))
        if self.osDistLevel in self.osDistListDict:
            self.versionInformationLogger.info('{0:40}'.format('Installed OS Dist. Level: \t' + self.osDistListDict[self.osDistLevel]))
        else:
            self.versionInformationLogger.info('{0:40}'.format('Installed OS Dist. Level: \t' + self.osDistLevel))
        self.versionInformationLogger.info('{0:40}'.format('CSUR Release Baseline:\t' + self.CSURRelease))
        self.versionInformationLogger.info('{0:40}'.format('OS Patch Update Baseline:\t' + self.osPatchUpdateRelease))
        self.versionInformationLogger.info('{0:40}'.format('healthCheck version:\t' + self.programVersion))
        self.versionInformationLogger.info('\n' + '-' * 100 + '\n')
        self.inventoryError = False
        self.firmwareDict = {}
        self.unsupportedUpgradableDist = False
        self.componentUpdateDict = {'Firmware': {},
         'Drivers': {},
         'Software': {},
         'CSUR': {},
         'osPatchBundle': {}}
        self.componentWARNDict = {'Firmware': 0,
         'Drivers': 0,
         'Software': 0,
         'CSUR': 0,
         'osPatchBundle': 0}
        self.notVersionMatchMessage = 'FAIL'
        self.versionMatchMessage = 'PASS'
        self.versionMatchWarningMessage = 'WARNING'

    def __getFirmwareDict(self):
        started = False
        self.logger.info('Getting the firmware dictionary.')
        for data in self.computeNodeResources:
            if not re.match('^Firmware:\\s*$', data) and not started:
                continue
            elif re.match('^Firmware:\\s*$', data):
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                data2 = data.replace(' ', '')
                firmwareList = data.split('|')
                firmwareList2 = data2.split('|')
                self.firmwareDict[firmwareList[0]] = [firmwareList2[1], firmwareList2[2], firmwareList[-1].strip()]

        self.logger.debug('The firmware dictionary contents was determined to be: ' + str(self.firmwareDict) + '.')
        self.logger.info('Done getting the firmware dictionary.')

    def getComponentUpdateInventory(self):
        self.localStoragePresent = False
        componentHeader = 'Component'
        componentUnderLine = '---------'
        CSURVersionHeader = 'CSUR Version'
        CSURVersionUnderLine = '------------'
        currentVersionHeader = 'Current Version'
        currentVersionUnderLine = '---------------'
        statusHeader = 'Status'
        statusUnderLine = '------'
        descriptionHeader = 'Description'
        descriptionUnderLine = '-----------'
        patchBundleVersionHeader = 'Patch Bundle Version'
        patchBundleVersionUnderLine = '--------------------'
        self.versionInformationLogger.info('\n' + '{0:40}'.format('CSUR Version:') + '\n')
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentHeader, CSURVersionHeader, currentVersionHeader, statusHeader, descriptionHeader))
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentUnderLine, CSURVersionUnderLine, currentVersionUnderLine, statusUnderLine, descriptionUnderLine))
        self.__getCSURInventory()
        self._getComputeNodeSpecificCSURInventory()
        if self.osDistLevel in self.unsupportedUpgradableDistLevels:
            self.versionInformationLogger.info('\nThe ' + self.osDistLevel + ' is not supported, but is upgradable to a supported release.\n')
            self.unsupportedUpgradableDist = True
            self.__makeSummaryRecommendaitons()
            return 1
        self.__getFirmwareDict()
        self.versionInformationLogger.info('\n' + '{0:40}'.format('Firmware Versions:') + '\n')
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentHeader, CSURVersionHeader, currentVersionHeader, statusHeader, descriptionHeader))
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentUnderLine, CSURVersionUnderLine, currentVersionUnderLine, statusUnderLine, descriptionUnderLine))
        if self.__getLocalStorage() == 'Present':
            self.localStoragePresent = True
            self.__getStorageFirmwareInventory()
        self.__getNICFirmwareInventory()
        self.__getCommonFirmwareInventory()
        self._getComputeNodeSpecificFirmwareInventory()
        self.versionInformationLogger.info('\n' + '{0:40}'.format('Driver Versions:') + '\n')
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentHeader, CSURVersionHeader, currentVersionHeader, statusHeader, descriptionHeader))
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentUnderLine, CSURVersionUnderLine, currentVersionUnderLine, statusUnderLine, descriptionUnderLine))
        self.__getDriverInventory()
        self._getComputeNodeSpecificDriverInventory()
        self.versionInformationLogger.info('\n' + '{0:40}'.format('Managed Software Versions:') + '\n')
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentHeader, CSURVersionHeader, currentVersionHeader, statusHeader, descriptionHeader))
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentUnderLine, CSURVersionUnderLine, currentVersionUnderLine, statusUnderLine, descriptionUnderLine))
        self.__getSoftwareInventory()
        self._getComputeNodeSpecificSoftwareInventory()
        self.versionInformationLogger.info('\n' + '{0:40}'.format('OS Patch Bundle Version:') + '\n')
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentHeader, patchBundleVersionHeader, currentVersionHeader, statusHeader, descriptionHeader))
        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(componentUnderLine, patchBundleVersionUnderLine, currentVersionUnderLine, statusUnderLine, descriptionUnderLine))
        self.__getPatchBundleInventory()
        self._getComputeNodeSpecificPatchBundleInventory()
        self.__makeSummaryRecommendaitons()

    def __makeSummaryRecommendaitons(self):
        self.logger.debug('Update Dict:' + str(self.componentUpdateDict) + '.')
        self.logger.debug('WARNing Dict:' + str(self.componentWARNDict) + '.')
        self.versionInformationLogger.info('\n\n' + '=' * 100 + '\n')
        self.versionInformationLogger.info('SUMMARY:')
        if self.inventoryError:
            self.versionInformationLogger.info("\tWARNING: Unable to read some of the system's inventory. Check compute node log for details. \n\tFindings are incomplete until corrected! If not H/W error(s), or disk model missing from the resource file,\n\tthen a CSUR upgrade is recommended.")
        if self.unsupportedUpgradableDist:
            self.versionInformationLogger.info('\nRecommendation: \n\tPlease contact your HPE account team to request the following lifecycle event services:')
            self.versionInformationLogger.info('\tOS Upgrade Service')
            self.versionInformationLogger.info('\tCSUR Update Service')
            return 1
        updateNeeded = False
        osPatchUpdSet = False
        componentDictSizes = [ len(dict) for dict in self.componentUpdateDict.values() ]
        if any((x != 0 for x in componentDictSizes)):
            updateNeeded = True
            self.versionInformationLogger.info('\nFollowing sections need updating:')
            for key in self.componentUpdateDict.keys():
                x = len(self.componentUpdateDict[key])
                if x > 0:
                    self.versionInformationLogger.info('\t' + key + '\t' + str(x))

            if any((self.componentWARNDict[x] != 0 for x in self.componentWARNDict.keys())):
                self.versionInformationLogger.info('\nWarnings/Needs Installation:')
                for key in self.componentWARNDict.keys():
                    x = self.componentWARNDict[key]
                    if x > 0:
                        self.versionInformationLogger.info('\t' + key + '\t' + str(x))

            self.versionInformationLogger.info('\nRecommendation(s): \n\tPlease contact your HPE account team to request the following lifecycle event services:')
            if len(self.componentUpdateDict['CSUR']) > 0:
                self.versionInformationLogger.info('\tCSUR Update Service')
                csurUpdSet = True
            if len(self.componentUpdateDict['osPatchBundle']) > 0 or len(self.componentUpdateDict['Software']) > 0:
                if 'osPatchKernel' in self.componentUpdateDict['osPatchBundle'].keys() and len(self.componentUpdateDict['osPatchBundle']['osPatchKernel']) > 0:
                    self.versionInformationLogger.info('\tOS Upgrade Service')
                if 'osPatchOS' in self.componentUpdateDict['osPatchBundle'].keys() and len(self.componentUpdateDict['osPatchBundle']['osPatchOS']) > 0:
                    self.versionInformationLogger.info('\tOS Patch Update Service')
                    osPatchUpdSet = True
            if len(self.componentUpdateDict['Software']) > 0:
                if not osPatchUpdSet:
                    self.versionInformationLogger.info('\tOS Patch Update Service')
                    osPatchUpdSet = True
            if len(self.componentUpdateDict['Firmware']) > 0 or len(self.componentUpdateDict['Drivers']) > 0:
                if len(self.componentUpdateDict['Firmware']) < 3 and len(self.componentUpdateDict['Drivers']) < 3:
                    if not osPatchUpdSet:
                        self.versionInformationLogger.info('\tOS Patch Update Service')
                        osPatchUpdSet = True
                elif not csurUpdSet:
                    self.versionInformationLogger.info('\tCSUR Update Service')
                    csurUpdSet = True
        else:
            self.versionInformationLogger.info('\nRecommendation: \n\tCongratuations! No Updates are needed at this time.\n')

    def getLocalHardDriveFirmwareInventory(self):
        self.__getFirmwareDict()
        if self.__getLocalStorage() == 'Present':
            self.localStoragePresent = True
            self.__getLocalOSHardDriveFirmwareInventory()
        else:
            self.logger.error('There are no local hard drives to update.')
            self.inventoryError = True

    def __getStorageFirmwareInventory(self):
        self.logger.info('Getting the storage firmware inventory.')
        controllerReportedList = []
        if os.path.isfile('/usr/sbin/ssacli'):
            arrayCfgUtilFile = '/usr/sbin/ssacli'
        elif os.path.isfile('/usr/sbin/hpssacli'):
            arrayCfgUtilFile = '/usr/sbin/hpssacli'
        elif os.path.isfile('/usr/sbin/hpacucli'):
            arrayCfgUtilFile = '/usr/sbin/hpacucli'
        else:
            arrayCfgUtilFile = '/usr/sbin/ssacli'
            self.logger.error('No array configuration utility found. A CSUR upgrade is needed.')
            self.inventoryError = True
            return
        command = arrayCfgUtilFile + ' ctrl all show'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ') used to get the list of storage controllers was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get the list of storage controllers.\n' + err)
            self.inventoryError = True
            return
        controllerList = re.findall('P\\d{3}i*\\s+in\\s+Slot\\s+\\d{1}', out, re.MULTILINE | re.DOTALL)
        self.logger.debug('The controller list was determined to be: ' + str(controllerList) + '.')
        hardDriveList = []
        for controller in controllerList:
            controllerModel = controller.split()[0]
            controllerSlot = controller.split()[-1]
            CSURControllerFirmwareVersion = self.firmwareDict[controllerModel][0]
            CSURControllerFirmwareDesc = self.firmwareDict[controllerModel][-1]
            command = arrayCfgUtilFile + ' ctrl slot=' + controllerSlot + ' show'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.debug('The output of the command (' + command + ') used to get the storage controllers firmware version was: ' + out.strip())
            if result.returncode != 0:
                self.logger.error('Failed to get the list of storage controllers.\n' + err)
                self.inventoryError = True
                return
            installedControllerFirmwareVersion = re.match('.*Firmware Version:\\s+(\\d+\\.\\d+).*', out, re.MULTILINE | re.DOTALL).group(1)
            self.logger.debug("The controller's firmware version was determined to be: " + installedControllerFirmwareVersion + '.')
            item = 'Model:' + controllerModel + ' FW:' + installedControllerFirmwareVersion
            if item not in controllerReportedList:
                controllerReportedList.append(item)
                if installedControllerFirmwareVersion != CSURControllerFirmwareVersion:
                    self.componentUpdateDict['Firmware'][controllerModel] = self.firmwareDict[controllerModel][1]
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(controllerModel, CSURControllerFirmwareVersion, installedControllerFirmwareVersion, self.notVersionMatchMessage, CSURControllerFirmwareDesc))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(controllerModel, CSURControllerFirmwareVersion, installedControllerFirmwareVersion, self.versionMatchMessage, CSURControllerFirmwareDesc))
            if controllerModel == 'P812' or controllerModel == 'P431':
                if self.systemModel != 'DL580Gen9':
                    CSUREnclosureFirmwareVersion = self.firmwareDict['D2700'][0]
                    CSUREnclosureFirmwareDesc = self.firmwareDict['D2700'][-1]
                    enclosure = 'D2700'
                else:
                    CSUREnclosureFirmwareVersion = self.firmwareDict['D3700'][0]
                    CSUREnclosureFirmwareDesc = self.firmwareDict['D3700'][-1]
                    enclosure = 'D3700'
                self.externalStoragePresent = True
                command = arrayCfgUtilFile + ' ctrl slot=' + controllerSlot + ' enclosure all show detail'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.debug('The output of the command (' + command + ') used to get the storage controllers enclosure firmware version was: ' + out.strip())
                if result.returncode != 0:
                    self.logger.error("Failed to get the storage contoller's details.\n" + err)
                    self.inventoryError = True
                    return
                installedEnclosureFirmwareVersion = re.match('.*Firmware Version:\\s+(\\d+\\.\\d+|\\d+).*', out, re.MULTILINE | re.DOTALL).group(1)
                self.logger.debug("The controller's enclosure firmware version was determined to be: " + installedEnclosureFirmwareVersion + '.')
                item = 'enclosure:' + enclosure + ' FW:' + installedEnclosureFirmwareVersion
                if item not in controllerReportedList:
                    controllerReportedList.append(item)
                    if installedEnclosureFirmwareVersion != CSUREnclosureFirmwareVersion:
                        self.componentUpdateDict['Firmware'][enclosure] = self.firmwareDict[enclosure][1]
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(enclosure, CSUREnclosureFirmwareVersion, installedEnclosureFirmwareVersion, self.notVersionMatchMessage, CSUREnclosureFirmwareDesc))
                    else:
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(enclosure, CSUREnclosureFirmwareVersion, installedEnclosureFirmwareVersion, self.versionMatchMessage, CSUREnclosureFirmwareDesc))
            command = arrayCfgUtilFile + ' ctrl slot=' + controllerSlot + ' pd all show detail'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.debug('The output of the command (' + command + ') used to get the hard drive list and their firmware version was: ' + out.strip())
            if result.returncode != 0:
                self.logger.error('Failed to get hard drive versions.\n' + err)
                self.inventoryError = True
                return
            hardDriveDataList = re.findall('Firmware\\s+Revision:\\s+[0-9,A-Z]{4}\\s+Serial\\s+Number:\\s+[0-9,A-Z]+\\s+WWID:\\s+[0-9,A-Z]+\\s+Model:\\s+HP\\s+[0-9,A-Z]+', out, re.MULTILINE | re.DOTALL)
            self.logger.debug('The hard drive data list was determined to be: ' + str(hardDriveDataList) + '.')
            for hardDrive in hardDriveDataList:
                hardDriveData = hardDrive.split()
                hardDriveVersion = hardDriveData[-1] + ' ' + hardDriveData[2]
                hardDriveList.append(hardDriveVersion)

        hardDriveList.sort()
        self.logger.debug('The hard drive list was determined to be: ' + str(hardDriveList) + '.')
        hardDriveModels = []
        count = 0
        for hd in hardDriveList:
            hardDriveData = hd.split()
            if count == 0:
                hardDriveModels.append(hardDriveData[0])
                tmpHardDriveModel = hardDriveData[0]
                count += 1
            elif hardDriveData[0] != tmpHardDriveModel:
                hardDriveModels.append(hardDriveData[0])
                tmpHardDriveModel = hardDriveData[0]

        self.logger.debug('The hard drive models were determined to be: ' + str(hardDriveModels))
        for hardDriveModel in hardDriveModels:
            hardDriveVersionMismatch = False
            try:
                CSURHardDriveFirmwareVersion = self.firmwareDict[hardDriveModel][0]
                CSURHardDriveFirmwareDesc = self.firmwareDict[hardDriveModel][-1]
            except KeyError:
                self.logger.error('Firmware for the hard drive model ' + hardDriveModel + ' is missing from the CSUR bundle.')
                self.inventoryError = True
                continue

            for hd in hardDriveList:
                hardDriveData = hd.split()
                if hardDriveData[0] == hardDriveModel:
                    installedHardDriveFirmwareVersion = hardDriveData[1]
                    self.logger.debug("The hard drive's firmware version was determined to be: " + installedHardDriveFirmwareVersion + '.')
                    if installedHardDriveFirmwareVersion != CSURHardDriveFirmwareVersion and self.firmwareDict[hardDriveModel][1] != 'None':
                        self.componentUpdateDict['Firmware'][hardDriveModel] = self.firmwareDict[hardDriveModel][1]
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(hardDriveModel, CSURHardDriveFirmwareVersion, installedHardDriveFirmwareVersion, self.notVersionMatchMessage, CSURHardDriveFirmwareDesc))
                        hardDriveVersionMismatch = True
                        break

            if not hardDriveVersionMismatch:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(hardDriveModel, CSURHardDriveFirmwareVersion, installedHardDriveFirmwareVersion, self.versionMatchMessage, CSURHardDriveFirmwareDesc))

        self.logger.info('Done getting the storage firmware inventory.')

    def __getLocalOSHardDriveFirmwareInventory(self):
        self.logger.info('Getting the local OS hard drive firmware inventory.')
        if os.path.isfile('/usr/sbin/hpssacli'):
            arrayCfgUtilFile = '/usr/sbin/hpssacli'
        else:
            arrayCfgUtilFile = '/usr/sbin/hpacucli'
        command = arrayCfgUtilFile + ' ctrl all show'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ') used to get the list of attached storage controllers was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get the list of attached storage controllers.\n' + err)
            self.inventoryError = True
            return
        if re.match('\\s*Smart\\s+Array\\s+P\\d{3}i\\s+in\\s+Slot\\s+\\d{1}', out, re.MULTILINE | re.DOTALL):
            controllerModel = re.match('\\s*Smart\\s+Array\\s+(P\\d{3}i)\\s+in\\s+Slot\\s+\\d{1}', out, re.MULTILINE | re.DOTALL).group(1)
            controllerSlot = re.match('\\s*Smart\\s+Array\\s+P\\d{3}i\\s+in\\s+Slot\\s+(\\d{1})', out, re.MULTILINE | re.DOTALL).group(1)
        else:
            self.logger.error("Failed to get the internal storage controller's information.")
            self.inventoryError = True
            return
        self.logger.debug('The controller was determined to be: ' + controllerModel + ' in slot ' + controllerSlot + '.')
        hardDriveList = []
        command = arrayCfgUtilFile + ' ctrl slot=' + controllerSlot + ' pd all show detail'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ') used to get the hard drive list and their firmware version was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get hard drive versions.\n' + err)
            self.inventoryError = True
            return
        hardDriveDataList = re.findall('Firmware\\s+Revision:\\s+[0-9,A-Z]{4}\\s+Serial\\s+Number:\\s+[0-9,A-Z]+\\s+Model:\\s+HP\\s+[0-9,A-Z]+', out, re.MULTILINE | re.DOTALL)
        self.logger.debug('The hard drive data list was determined to be: ' + str(hardDriveDataList) + '.')
        for hardDrive in hardDriveDataList:
            hardDriveData = hardDrive.split()
            hardDriveVersion = hardDriveData[-1] + ' ' + hardDriveData[2]
            hardDriveList.append(hardDriveVersion)

        hardDriveList.sort()
        self.logger.debug('The hard drive list was determined to be: ' + str(hardDriveList) + '.')
        hardDriveModels = []
        count = 0
        for hd in hardDriveList:
            hardDriveData = hd.split()
            if count == 0:
                hardDriveModels.append(hardDriveData[0])
                tmpHardDriveModel = hardDriveData[0]
                count += 1
            elif hardDriveData[0] != tmpHardDriveModel:
                hardDriveModels.append(hardDriveData[0])
                tmpHardDriveModel = hardDriveData[0]

        self.logger.debug('The hard drive models were determined to be: ' + str(hardDriveModels))
        for hardDriveModel in hardDriveModels:
            hardDriveVersionMismatch = False
            try:
                CSURHardDriveFirmwareVersion = self.firmwareDict[hardDriveModel][0]
                CSURHardDriveFirmwareDesc = self.firmwareDict[hardDriveModel][-1]
            except KeyError:
                self.logger.error('Firmware for the hard drive model ' + hardDriveModel + ' is missing from the CSUR bundle.')
                self.inventoryError = True
                continue

            for hd in hardDriveList:
                hardDriveData = hd.split()
                if hardDriveData[0] == hardDriveModel:
                    installedHardDriveFirmwareVersion = hardDriveData[1]
                    self.logger.debug("The hard drive's firmware version was determined to be: " + installedHardDriveFirmwareVersion + '.')
                    if installedHardDriveFirmwareVersion != CSURHardDriveFirmwareVersion and self.firmwareDict[hardDriveModel][1] != 'None':
                        self.componentUpdateDict['Firmware'][hardDriveModel] = self.firmwareDict[hardDriveModel][1]
                        hardDriveVersionMismatch = True
                        break

        self.logger.info('Done getting the local OS hard drive firmware inventory.')

    def __getNICFirmwareInventory(self):
        nicCardModels = []
        count = 0
        self.logger.info('Getting the NIC card firmware inventory.')
        nicBusList = self.__getNicBusList()
        if nicBusList == 'NICBusFailure':
            return
        for nd in nicBusList:
            nicCardData = nd.split()
            if count == 0:
                nicCardModels.append(nicCardData[-1])
                tmpNicCardModel = nicCardData[-1]
                count += 1
            elif nicCardData[-1] != tmpNicCardModel:
                nicCardModels.append(nicCardData[-1])
                tmpNicCardModel = nicCardData[-1]

        self.logger.debug('The NIC card models were determined to be: ' + str(nicCardModels) + '.')
        command = 'ifconfig -a'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ') used to get the NIC card list was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error("Failed to get the Compute Node's NIC card list.\n" + err)
            self.inventoryError = True
            return
        nicCardList = re.findall('^[empth0-9]{3,}', out, re.MULTILINE | re.DOTALL)
        self.logger.debug('The NIC card list was determined to be: ' + str(nicCardList) + '.')
        for nicCardModel in nicCardModels:
            nicCardVersionMismatch = False
            count = 0
            try:
                CSURNicCardFirmwareVersion = self.firmwareDict[nicCardModel][0]
                CSURNicCardFirmwareDesc = self.firmwareDict[nicCardModel][-1]
            except KeyError as err:
                self.logger.error('Firmware for the NIC card model ' + nicCardModel + ' is missing from the CSUR bundle. ' + str(err))
                self.logger.debug('FW Dict;' + str(self.firmwareDict) + '.')
                self.inventoryError = True
                continue

            for data in nicBusList:
                nicCardData = data.split()
                nicBus = nicCardData[0]
                installedNicCardModel = nicCardData[1]
                if installedNicCardModel == nicCardModel:
                    for nic in nicCardList:
                        command = 'ethtool -i ' + nic
                        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                        out, err = result.communicate()
                        self.logger.debug('The output of the command (' + command + ') used to check the NIC card firmware was: ' + out.strip())
                        if result.returncode != 0:
                            self.logger.error('Failed to get the NIC card information for (' + nic + ').\n' + err)
                            self.inventoryError = True
                            continue
                        if nicBus in out:
                            nicDevice = nic
                        else:
                            continue
                        versionList = out.splitlines()
                        for line in versionList:
                            if 'firmware-version' in line:
                                firmwareList = line.split()
                                if '5719-v' in line or '5720-v' in line:
                                    installedNicCardFirmwareVersion = re.match('\\d{4}-(.*)', firmwareList[1]).group(1)
                                else:
                                    installedNicCardFirmwareVersion = firmwareList[-1]

                        self.logger.debug('The NIC card firmware version was determined to be: ' + str(installedNicCardFirmwareVersion) + '.')
                        if installedNicCardFirmwareVersion != CSURNicCardFirmwareVersion and count == 0:
                            self.componentUpdateDict['Firmware'][nicCardModel] = self.firmwareDict[nicCardModel][1]
                            count += 1
                            nicCardVersionMismatch = True
                            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(nicCardModel, CSURNicCardFirmwareVersion, installedNicCardFirmwareVersion, self.notVersionMatchMessage, CSURNicCardFirmwareDesc))
                        break

                else:
                    continue
                if count == 1:
                    break

            if not nicCardVersionMismatch:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(nicCardModel, CSURNicCardFirmwareVersion, installedNicCardFirmwareVersion, self.versionMatchMessage, CSURNicCardFirmwareDesc))

        self.logger.info('Done getting the NIC card firmware inventory.')

    def __getNicBusList(self):
        nicBusList = []
        busDict = {}
        modelCrossRefDict = {'NetXtreme BCM5719': '331FLR',
         'Intel Corporation 82599': '560SFP+',
         'Mellanox Technologies MT27520': '544+QSFP',
         '331FLR': '331FLR',
         '560SFP+': '560SFP+',
         '544+QSFP': '544+QSFP'}
        self.logger.info('Getting the NIC bus list.')
        command = 'lspci -i ' + self.pciIdsFile + ' -mvv'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            self.logger.error("Failed to get the Compute Node's NIC bus list.\n" + err)
            self.inventoryError = True
            return 'NICBusFailure'
        self.logger.info('The output of the command (' + command + ') used to get the NIC card bus information was: ' + out.strip())
        out = re.sub('\n{2,}', '####', out)
        deviceList = out.split('####')
        for device in deviceList:
            if 'Ethernet controller' in device or 'Network controller' in device:
                bus = re.match('\\s*[a-zA-Z]+:\\s+([0-9a-f]{2}:[0-9a-f]{2}\\.[0-9]).*(NC375T|NC375i|NC550SFP|331FLR|331T|544\\+QSFP|560SFP\\+|331T|561T|332i|332T)\\s+Adapter.*', device, re.MULTILINE | re.DOTALL)
                try:
                    if not bus:
                        self.logger.error('A match error was encountered while getting nic bus information for device: ' + device[0:200])
                        self.inventoryError = True
                        continue
                    self.logger.info('The bus information for device:\n' + device[0:200] + '\nwas determined to be: ' + bus.group(1) + '.  ' + bus.group(2) + '.\n')
                    busPrefix = bus.group(1)[:-2]
                    if busPrefix not in busDict:
                        busDict[busPrefix] = ''
                        if self.systemModel == 'DL580Gen8':
                            nicBusList.append(bus.group(1) + ' ' + modelCrossRefDict[bus.group(2)])
                        elif self.systemModel == 'DL380pGen8':
                            if bus.group(2) == 'NC552SFP':
                                nicBusList.append(bus.group(1) + ' ' + bus.group(2))
                            else:
                                nicBusList.append(bus.group(1) + ' ' + modelCrossRefDict[bus.group(2)])
                        else:
                            nicBusList.append(bus.group(1) + ' ' + bus.group(2))
                except AttributeError as err:
                    self.logger.error('An AttributeError was encountered while getting nic bus information: ' + str(err) + '\n' + device[0:200])
                    self.inventoryError = True
                    continue

        nicBusList.sort(key=lambda n: n.split()[1])
        self.logger.info('The NIC card bus list was determined to be: ' + str(nicBusList) + '.')
        self.logger.info('Done getting the NIC bus list.')
        return nicBusList

    def __getCommonFirmwareInventory(self):
        biosFirmwareType = 'BIOS' + self.systemModel
        self.logger.info('Getting the compute node common firmware inventory.')
        command = 'dmidecode -s bios-release-date'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ") used to get the compute node's BIOS information was: " + out.strip())
        if result.returncode != 0:
            self.logger.error("Failed to get the compute node's BIOS firmware version.\n" + err)
            self.inventoryError = True
        else:
            biosFirmwareDate = out.strip()
            biosFirmwareDateList = biosFirmwareDate.split('/')
            installedBiosFirmwareVersion = biosFirmwareDateList[2] + '.' + biosFirmwareDateList[0] + '.' + biosFirmwareDateList[1]
            self.logger.debug("The compute node's bios version was determined to be: " + installedBiosFirmwareVersion + '.')
            CSURBiosFirmwareVersion = self.firmwareDict[biosFirmwareType][0]
            CSURBiosFirmwareDesc = self.firmwareDict[biosFirmwareType][-1]
            if installedBiosFirmwareVersion != CSURBiosFirmwareVersion:
                self.componentUpdateDict['Firmware'][biosFirmwareType] = self.firmwareDict[biosFirmwareType][1]
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('BIOS', CSURBiosFirmwareVersion, installedBiosFirmwareVersion, self.notVersionMatchMessage, CSURBiosFirmwareDesc))
            else:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('BIOS', CSURBiosFirmwareVersion, installedBiosFirmwareVersion, self.versionMatchMessage, CSURBiosFirmwareDesc))
        command = 'hponcfg -g'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ") used to get the compute node's iLO information was: " + out.strip())
        if result.returncode != 0:
            self.logger.error("Failed to get the Compute Node's iLO firmware version.\n" + err)
            self.inventoryError = True
        else:
            installedILOFirmwareVersion = re.match('.*Firmware Revision\\s+=\\s+(\\d+\\.\\d+).*', out, re.MULTILINE | re.DOTALL).group(1)
            self.logger.debug("The compute node's iLO version was determined to be: " + installedILOFirmwareVersion + '.')
            CSURILOFirmwareVersion = self.firmwareDict['iLO'][0]
            CSURILOFirmwareDesc = self.firmwareDict['iLO'][-1]
            if installedILOFirmwareVersion != CSURILOFirmwareVersion:
                self.componentUpdateDict['Firmware']['iLO'] = self.firmwareDict['iLO'][1]
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('iLO', CSURILOFirmwareVersion, installedILOFirmwareVersion, self.notVersionMatchMessage, CSURILOFirmwareDesc))
            else:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('iLO', CSURILOFirmwareVersion, installedILOFirmwareVersion, self.versionMatchMessage, CSURILOFirmwareDesc))
        command = 'systool -c scsi_host -v'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ") used to get the compute node's HBA information was: " + out.strip())
        if result.returncode != 0:
            self.logger.error("Failed to get compute node's HBA information.\n" + err)
            self.inventoryError = True
        else:
            PreviousHBAFirmwareVersion = ''
            PreviousHBAModel = ''
            if re.search('HBA', out, re.MULTILINE | re.DOTALL) != None:
                hostList = out.split('Device = "')
                for host in hostList:
                    if re.search('HBA', host, re.MULTILINE | re.DOTALL) != None:
                        installedHBAFirmwareVersion = ''
                        hbaModel = ''
                        hostDataList = host.splitlines()
                        for data in hostDataList:
                            if re.match('\\s+fw_version', data) != None:
                                installedHBAFirmwareVersion = re.match('\\s*fw_version\\s+=\\s+"(.*)\\s+\\(', data).group(1)
                                self.logger.debug("The HBA's firmware version was determined to be: " + installedHBAFirmwareVersion + '.')
                            if re.match('\\s*model_name', data) != None:
                                hbaModel = re.match('\\s*model_name\\s+=\\s+"(.*)"', data).group(1)
                                self.logger.debug("The HBA's model was determined to be: " + hbaModel + '.')
                            if installedHBAFirmwareVersion != '' and hbaModel != '':
                                if installedHBAFirmwareVersion == PreviousHBAFirmwareVersion and hbaModel == PreviousHBAModel:
                                    break
                                else:
                                    PreviousHBAFirmwareVersion = installedHBAFirmwareVersion
                                    PreviousHBAModel = hbaModel
                                try:
                                    CSURHBAFirmwareVersion = self.firmwareDict[hbaModel][0]
                                    CSURHBAFirmwareDesc = self.firmwareDict[hbaModel][-1]
                                except KeyError:
                                    self.logger.error('Firmware for the HBA model ' + hbaModel + ' is missing from the CSUR bundle.')
                                    self.inventoryError = True
                                    break

                                if installedHBAFirmwareVersion != CSURHBAFirmwareVersion:
                                    if hbaModel not in self.componentUpdateDict['Firmware']:
                                        self.componentUpdateDict['Firmware'][hbaModel] = self.firmwareDict[hbaModel][1]
                                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(hbaModel, CSURHBAFirmwareVersion, installedHBAFirmwareVersion, self.notVersionMatchMessage, CSURHBAFirmwareDesc))
                                else:
                                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(hbaModel, CSURHBAFirmwareVersion, installedHBAFirmwareVersion, self.versionMatchMessage, CSURHBAFirmwareDesc))
                                break

        if self.systemModel not in self.noPMCFirmwareUpdateModels:
            installedPMCFirmwareVersion = ''
            command = 'dmidecode'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            self.logger.debug('The output of the command (' + command + ") used to get the compute node's dmidecode information was: " + out.strip())
            if result.returncode != 0:
                self.logger.error("Failed to get compute node's dmidecode information needed to determine the Power Management Contoller's firmware version.\n" + err)
                self.inventoryError = True
            else:
                dmidecodeList = out.splitlines()
                found = False
                for data in dmidecodeList:
                    if not found and re.match('^\\s*Power Management Controller Firmware\\s*$', data) != None:
                        found = True
                        continue
                    elif found:
                        installedPMCFirmwareVersion = data.strip()
                        self.logger.debug("The Power Management Controller's firmware version was determined to be: " + installedPMCFirmwareVersion + '.')
                        break
                    else:
                        continue

                if installedPMCFirmwareVersion != '':
                    pmcCSURReference = 'PMC' + self.systemModel
                    try:
                        CSURPMCFirmwareVersion = self.firmwareDict[pmcCSURReference][0]
                        CSURPMCFirmwareDesc = self.firmwareDict[pmcCSURReference][-1]
                    except KeyError:
                        self.logger.error('Firmware for the Power Management Controller is missing from the CSUR bundle.')
                        self.inventoryError = True
                    else:
                        if installedPMCFirmwareVersion != CSURPMCFirmwareVersion:
                            self.componentUpdateDict['Firmware'][pmcCSURReference] = self.firmwareDict[pmcCSURReference][1]
                            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('PMC', CSURPMCFirmwareVersion, installedPMCFirmwareVersion, self.notVersionMatchMessage, CSURPMCFirmwareDesc))
                        else:
                            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('PMC', CSURPMCFirmwareVersion, installedPMCFirmwareVersion, self.versionMatchMessage, CSURPMCFirmwareDesc))
                else:
                    self.logger.error("The Power Management Controller's firmware version was not found in the output of dmidecode.")
                    self.inventoryError = True
        self.logger.info('Done getting the compute node common firmware inventory.')
        return

    def __getDriverInventory(self):
        started = False
        driversFound = False
        updateDriverList = []
        mlnxCount = 0
        self.logger.info('Getting the driver inventory.')
        for data in self.computeNodeResources:
            if not re.match('^Drivers:\\s*$', data) and not driversFound:
                continue
            elif 'Drivers:' in data:
                driversFound = True
                continue
            elif re.match('^#', data):
                continue
            elif self.osDistLevel in data and not self.systemModel in data and not started:
                continue
            elif self.osDistLevel in data and self.systemModel in data:
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                data2 = data
                data = data.replace(' ', '')
                CSURDriverList = data.split('|')
                CSURDriverList2 = data2.split('|')
                CSURDriver = CSURDriverList[0]
                CSURDriverVersion = CSURDriverList[1]
                CSURDriverDesc = CSURDriverList2[3].strip()
                if CSURDriver in self.localStorageDrivers and not self.localStoragePresent:
                    break
                if CSURDriver in self.hbaDrivers and 'Scale-up' in self.systemType:
                    break
                command = 'modinfo ' + CSURDriver
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.debug('The output of the command (' + command + ') used to get the driver information was: ' + out.strip())
                if result.returncode != 0:
                    if (CSURDriver == 'mlx4_en' or CSURDriver == 'mlnx') and mlnxCount == 0:
                        self.logger.warn('The first Mellanox driver checked (' + CSURDriver + ') appears not to be the driver being used.\n' + err)
                        mlnxCount += 1
                        continue
                    else:
                        self.logger.error("Failed to get the Compute Node's driver version for driver " + CSURDriver + '.\n' + err)
                        self.inventoryError = True
                driverDataList = out.splitlines()
                for data in driverDataList:
                    if re.match('version:\\s+.*', data) != None:
                        versionList = data.split()
                        installedDriverVersion = versionList[1]
                        break

                self.logger.debug('The driver version was determined to be: ' + installedDriverVersion + '.')
                if installedDriverVersion != CSURDriverVersion:
                    self.componentUpdateDict['Drivers'][CSURDriver] = CSURDriverList[2]
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(CSURDriver, CSURDriverVersion, installedDriverVersion, self.notVersionMatchMessage, CSURDriverDesc))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(CSURDriver, CSURDriverVersion, installedDriverVersion, self.versionMatchMessage, CSURDriverDesc))

        self.logger.info('Done getting the driver inventory.')
        return

    def __getSoftwareInventory(self):
        started = False
        softwareFound = False
        updateSoftwareList = []
        self.logger.info('Getting the software inventory.')
        for data in self.computeNodeResources:
            if not re.match('^Software:\\s*$', data) and not softwareFound:
                continue
            elif 'Software:' in data:
                softwareFound = True
                continue
            elif re.match('^#', data):
                continue
            elif self.osDistLevel in data and not self.systemModel in data and not started:
                continue
            elif self.osDistLevel in data and self.systemModel in data:
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                data2 = data
                data = data.replace(' ', '')
                CSURSoftwareList = data.split('|')
                CSURSoftwareList2 = data2.split('|')
                CSURSoftware = CSURSoftwareList[0]
                CSURSoftwareEpoch = CSURSoftwareList[1]
                CSURSoftwareVersion = CSURSoftwareList[2]
                CSURSoftwareDesc = CSURSoftwareList2[4].strip()
                if CSURSoftware in self.localStorageSoftware and not self.localStoragePresent:
                    break
                if CSURSoftware in self.hbaSoftware and 'Scale-up' in self.systemType:
                    break
                command = "rpm -q --queryformat=%{buildtime}':'%{version}'-'%{release} " + CSURSoftware
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.debug('The output of the command (' + command + ') used to get the software epoch and version information was: ' + out.strip())
                if result.returncode != 0:
                    if 'is not installed' in out:
                        self.componentUpdateDict['Software'][CSURSoftware] = CSURSoftwareList[3]
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(CSURSoftware, CSURSoftwareVersion, 'Not Installed', self.versionMatchWarningMessage, CSURSoftwareDesc))
                        self.componentWARNDict['Software'] += 1
                        continue
                    else:
                        self.logger.error("Failed to get the Compute Node's software version for software " + CSURSoftware + '.\n' + err)
                        self.inventoryError = True
                        continue
                rpmInformationList = out.strip().split(':')
                installedSoftwareEpoch = rpmInformationList[0]
                installedSoftwareVersion = rpmInformationList[1]
                self.logger.debug('The software epoch date was determined to be: ' + installedSoftwareEpoch + '.')
                if installedSoftwareEpoch < CSURSoftwareEpoch:
                    self.componentUpdateDict['Software'][CSURSoftware] = CSURSoftwareList[3]
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(CSURSoftware, CSURSoftwareVersion, installedSoftwareVersion, self.notVersionMatchMessage, CSURSoftwareDesc))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(CSURSoftware, CSURSoftwareVersion, installedSoftwareVersion, self.versionMatchMessage, CSURSoftwareDesc))

        self.logger.info('Done getting the software inventory.')

    def __getCSURInventory(self):
        if not os.path.isfile(self.csurVersionReleaseFile):
            self.logger.debug('The CSUR Version Release File does not exist. A CSUR upgrade has never been performed on this system.')
            csurInstalledVersion = 'Not Installed'
        else:
            try:
                with open(self.csurVersionReleaseFile) as f:
                    for line in f:
                        line = line.strip()
                        line = re.sub('[\'"]', '', line)
                        if len(line) == 0 or re.match('^#', line):
                            continue
                        elif 'CSUR Bundle|' in line:
                            x = re.search('Version:\\s*([a-zA-Z0-9._-]+)', line)
                            if x != None:
                                csurInstalledVersion = x.group(1)
                            else:
                                csurInstalledVersion = 'Not Installed'

            except IOError as err:
                self.logger.error('I/O Errors with file (' + self.csurVersionReleaseFile + ') for reading.' + str(err))
                csurInstalledVersion = 'I/O Error'

        self.logger.debug('The CSUR Installed version is ' + csurInstalledVersion + '. CSUR Release is ' + self.CSURRelease + '.')
        if csurInstalledVersion < self.CSURRelease or csurInstalledVersion == 'Not Installed' or csurInstalledVersion == 'I/O Error':
            self.componentUpdateDict['CSUR'] = {'CSUR': self.CSURRelease}
            if csurInstalledVersion == 'Not Installed':
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(self.CSURDesc, self.CSURRelease, csurInstalledVersion, self.versionMatchWarningMessage, ' '))
                self.componentWARNDict['CSUR'] += 1
            else:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(self.CSURDesc, self.CSURRelease, csurInstalledVersion, self.notVersionMatchMessage, ' '))
        else:
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(self.CSURDesc, self.CSURRelease, csurInstalledVersion, self.versionMatchMessage, ' '))
        self.logger.info('Done getting the CSUR Version inventory.')
        return

    def __getPatchBundleInventory(self):
        started = False
        patchBundleFound = False
        patchBundleText = 'HPE CS for SAP HANA Patch Bundle'
        self.patchBundleResourceDict = {}
        patchBundleDesc = ''
        self.logger.info('Getting the patch bundle inventory.')
        for data in self.computeNodeResources:
            if not re.match('^patchBundle:\\s*$', data) and not patchBundleFound:
                continue
            elif 'patchBundle:' in data:
                patchBundleFound = True
                continue
            elif re.match('^#', data):
                continue
            elif self.osDistLevel in data:
                if not self.systemModel in data and not started and re.match('^\\S+:\\s*$', data):
                    break
                continue
            elif self.osDistLevel in data and self.systemModel in data:
                started = True
                continue
            elif re.match('^\\s*$', data):
                break
            else:
                key, val = data.split('=')
                key = key.strip()
                val = val.strip()
                self.patchBundleResourceDict[key] = val

        self.logger.debug('OS Patch Update resource dict: ' + str(self.patchBundleResourceDict))
        try:
            osPatchUpdateReleaseNotes = self.patchBundleResourceDict['osPatchUpdateReleaseNotes']
            patchBundleList = osPatchUpdateReleaseNotes.split('|')
            patchBundleDesc = patchBundleList[0].strip().replace("'", '')
            for data in patchBundleList:
                if re.match('Version:\\s*.*', data) != None:
                    patchBundleReleasedVersion = data.split(':')[1].strip()

        except KeyError as err:
            osPatchUpdateReleaseNotes = 'Not Released'
            patchBundleReleasedVersion = 'Not Released'

        self.logger.debug('Patch Bundle Released version: ' + patchBundleReleasedVersion + '. Description: ' + patchBundleDesc + '.')
        patchBundleDict = {'kernel': {},
         'os': {}}
        patchBundleInstalledVersion = 'Not Found'
        if not os.path.isfile(self.osPatchUpdateReleaseFile):
            osPatchUpdateReleaseFileExist = False
            if osPatchUpdateReleaseNotes != 'Not Released':
                self.logger.debug('The OS Patch Update Release File does not exists ' + self.osPatchUpdateReleaseFile + '. This maybe OK if a patch bundle has never been installed.')
        else:
            osPatchUpdateReleaseFileExist = True
            try:
                with open(self.osPatchUpdateReleaseFile) as f:
                    for line in f:
                        line = line.strip()
                        line = re.sub('[\'"]', '', line)
                        if len(line) == 0 or re.match('^#', line):
                            continue
                        else:
                            patchBundleList = line.split('|')
                            for data in patchBundleList:
                                if re.match('Version:\\s*.*', data) != None:
                                    patchBundleInstalledVersion = data.split(':')[1].lstrip()
                                    patchBundleDesc = patchBundleList[-1].strip().lower()
                                    if 'kernel ' in patchBundleDesc:
                                        patchBundleDict['kernel'] = patchBundleInstalledVersion
                                    if ' os ' in patchBundleDesc:
                                        patchBundleDict['os'] = patchBundleInstalledVersion

                            self.logger.debug('The Patch Bundle Installed version is ' + patchBundleInstalledVersion + ', Desc:' + patchBundleDesc + ', patchBundleDict: ' + str(patchBundleDict))

            except IOError as err:
                self.logger.error('I/O Errors with file (' + self.osPatchUpdateReleaseFile + ') for reading.' + str(err))
                patchBundleInstalledVersion = 'I/O Error'

            if patchBundleDict['kernel'] == patchBundleInstalledVersion and patchBundleDict['os'] == patchBundleInstalledVersion:
                patchBundleDesc = 'Both kernel and os patches.'
            elif patchBundleDict['kernel'] == patchBundleInstalledVersion:
                patchBundleDesc = 'Kernel patches only.'
            elif patchBundleDict['os'] == patchBundleInstalledVersion:
                patchBundleDesc = 'OS patches only.'
            else:
                patchBundleDesc = ' '
            self.logger.debug('The Patch Bundle Installed version is ' + patchBundleInstalledVersion + ', Desc:' + patchBundleDesc + '.')
        if osPatchUpdateReleaseNotes == 'Not Released':
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(patchBundleText, patchBundleReleasedVersion, patchBundleInstalledVersion, self.versionMatchMessage, ' '))
        elif not osPatchUpdateReleaseFileExist:
            self.componentUpdateDict['osPatchBundle']['osPatchOS'] = patchBundleReleasedVersion
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(patchBundleText, patchBundleReleasedVersion, patchBundleInstalledVersion, self.notVersionMatchMessage, ' '))
        else:
            if patchBundleDict['kernel'] < patchBundleReleasedVersion:
                self.componentUpdateDict['osPatchBundle']['osPatchKernel'] = patchBundleReleasedVersion
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(patchBundleText + ':kernel', patchBundleReleasedVersion, patchBundleDict['kernel'], self.notVersionMatchMessage, patchBundleDesc))
            else:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(patchBundleText + ':kernel', patchBundleReleasedVersion, patchBundleDict['kernel'], self.versionMatchMessage, patchBundleDesc))
            if patchBundleDict['os'] < patchBundleReleasedVersion:
                self.componentUpdateDict['osPatchBundle']['osPatchOS'] = patchBundleReleasedVersion
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(patchBundleText + ':OS', patchBundleReleasedVersion, patchBundleDict['os'], self.notVersionMatchMessage, patchBundleDesc))
            else:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(patchBundleText + ':OS', patchBundleReleasedVersion, patchBundleDict['os'], self.versionMatchMessage, patchBundleDesc))
        self.logger.info('Done getting the Patch Bundle inventory.')
        return

    def __getLocalStorage(self):
        self.logger.info('Checking to see if there is any local storage.')
        if os.path.isfile('/usr/sbin/ssacli'):
            arrayCfgUtilFile = '/usr/sbin/ssacli'
        elif os.path.isfile('/usr/sbin/hpssacli'):
            arrayCfgUtilFile = '/usr/sbin/hpssacli'
        elif os.path.isfile('/usr/sbin/hpacucli'):
            arrayCfgUtilFile = '/usr/sbin/hpacucli'
        else:
            arrayCfgUtilFile = '/usr/sbin/ssacli'
            self.logger.error('No array configuration utility found. A CSUR upgrade is needed.')
            self.inventoryError = True
            return 'Absent'
        command = arrayCfgUtilFile + ' ctrl all show'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ') used to check if storage is local was: ' + out.strip())
        if result.returncode != 0:
            if 'No controllers detected' in out:
                return 'Absent'
            else:
                self.logger.error('Failed to get the list of storage controllers.\n' + err)
                self.inventoryError = True
                return 'Absent'
        else:
            return 'Present'
        self.logger.info('Done checking to see if there is any local storage.')

    def getComponentUpdateDict(self):
        return self.componentUpdateDict

    def getInventoryStatus(self):
        return self.inventoryError

    def _getComputeNodeSpecificFirmwareInventory(self):
        pass

    def _getComputeNodeSpecificDriverInventory(self):
        pass

    def _getComputeNodeSpecificSoftwareInventory(self):
        pass

    def _getComputeNodeSpecificCSURInventory(self):
        pass

    def _getComputeNodeSpecificPatchBundleInventory(self):
        pass

    def isExternalStoragePresent(self):
        return self.externalStoragePresent


class Gen1ScaleUpComputeNodeInventory(ComputeNodeInventory):

    def __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources, healthResourceDict):
        ComputeNodeInventory.__init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources, healthResourceDict)
        self.busList = []
        self.fusionIOSoftwareInstallPackageList = healthResourceDict['fusionIOSoftwareInstallPackageList']

    def _getComputeNodeSpecificFirmwareInventory(self):
        self.logger.info("Getting the compute node's FusionIO firmware inventory.")
        command = 'fio-status'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        self.logger.debug('The output of the command (' + command + ') used to get the FusionIO firmware information was: ' + out.strip())
        if result.returncode != 0:
            self.logger.error('Failed to get the FusionIO status information needed to determine the FusionIO firmware version information.\n' + err)
            self.inventoryError = True
            return
        fioStatusList = out.splitlines()
        count = 0
        ioDIMMStatusDict = {}
        firmwareUpdateRequired = 'no'
        CSURFusionIOFirmwareVersion = self.firmwareDict['FusionIO'][0]
        CSURFusionIOFirmwareDesc = self.firmwareDict['FusionIO'][-1]
        for line in fioStatusList:
            line = line.strip()
            if 'Firmware' in line or re.search('PCI:[0-9a-f]{2}:[0-9]{2}\\.[0-9]{1}', line):
                if 'Firmware' in line:
                    ioDIMMStatusDict['Firmware'] = re.match('Firmware\\s+(v([0-9]\\.){2}[0-9]{1,2})', line).group(1)
                    self.logger.debug('The ioDIMM firmware version was determined to be: ' + ioDIMMStatusDict['Firmware'] + '.')
                else:
                    ioDIMMStatusDict['bus'] = re.match('.*([0-9a-f]{2}:[0-9]{2}\\.[0-9]{1})', line).group(1)
                    self.logger.debug('The ioDIMM bus was determined to be: ' + ioDIMMStatusDict['bus'] + '.')
                count += 1
            if count == 2:
                if ioDIMMStatusDict['Firmware'] != CSURFusionIOFirmwareVersion:
                    self.busList.append(ioDIMMStatusDict['bus'])
                    if firmwareUpdateRequired == 'no':
                        self.componentUpdateDict['Firmware']['FusionIO'] = self.firmwareDict['FusionIO'][1]
                        firmwareUpdateRequired = 'yes'
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('FusionIOBus: ' + ioDIMMStatusDict['bus'], CSURFusionIOFirmwareVersion, ioDIMMStatusDict['Firmware'], self.notVersionMatchMessage, CSURFusionIOFirmwareDesc))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('FusionIOBus: ' + ioDIMMStatusDict['bus'], CSURFusionIOFirmwareVersion, ioDIMMStatusDict['Firmware'], self.versionMatchMessage, CSURFusionIOFirmwareDesc))
                ioDIMMStatusDict.clear()
                count = 0

        self.logger.info("Done getting the compute node's FusionIO firmware inventory.")

    def _getComputeNodeSpecificDriverInventory(self):
        started = False
        updateDriverList = []
        self.logger.info("Getting the compute node's FusionIO driver inventory.")
        for data in self.computeNodeResources:
            if not re.match('FusionIODriver', data) and not started:
                continue
            elif re.match('FusionIODriver', data):
                started = True
                continue
            else:
                data2 = data
                data = data.replace(' ', '')
                CSURDriverList = data.split('|')
                CSURDriverList2 = data2.split('|')
                CSURDriverVersion = CSURDriverList[1]
                CSURDriverDesc = CSURDriverList2[-1]
                command = 'modinfo iomemory_vsl'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.debug('The output of the command (' + command + ') used to get the FusionIO driver information was: ' + out.strip())
                if result.returncode != 0:
                    self.logger.error('Failed to get the FusionIO driver information.\n' + err)
                    self.inventoryError = True
                else:
                    installedDriverVersion = re.match('.*srcversion:\\s+([1-3][^\\s]+)', out, re.MULTILINE | re.DOTALL).group(1)
                    self.logger.debug('The FusionIO driver version was determined to be: ' + installedDriverVersion + '.')
                    if installedDriverVersion != CSURDriverVersion:
                        self.componentUpdateDict['Drivers']['iomemory_vsl'] = CSURDriverList[2]
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('iomemory_vsl', CSURDriverVersion, installedDriverVersion, self.notVersionMatchMessage, CSURDriverDesc))
                    else:
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format('iomemory_vsl', CSURDriverVersion, installedDriverVersion, self.versionMatchMessage, CSURDriverDesc))
                break

        self.logger.info("Done getting the compute node's FusionIO driver inventory.")

    def _getComputeNodeSpecificSoftwareInventory(self):
        softwareFound = False
        updateRequired = False
        self.logger.info("Getting the compute node's FusionIO software inventory.")
        for data in self.computeNodeResources:
            if not re.match('^FusionIOSoftware:\\s*$', data) and not softwareFound:
                continue
            elif re.match('^FusionIOSoftware:', data):
                softwareFound = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                data2 = data
                data = data.replace(' ', '')
                CSURSoftwareList = data.split('|')
                CSURSoftwareList2 = data2.split('|')
                CSURSoftware = CSURSoftwareList[0]
                if len(CSURSoftwareList) < 4:
                    self.logger.error('CSURSoftwareList length < 4 :' + str(CSURSoftwareList))
                CSURSoftwareEpoch = CSURSoftwareList[1]
                CSURSoftwareVersion = CSURSoftwareList[2]
                CSURSoftwareDesc = CSURSoftwareList2[-1]
                command = "rpm -q --queryformat=%{buildtime}':'%{version}'-'%{release} " + CSURSoftware
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.debug('The output of the command (' + command + ') used to get the software epoch information was: ' + out.strip())
                if result.returncode != 0:
                    if 'is not installed' in err or 'is not installed' in out:
                        if not updateRequired:
                            updateRequired = True
                        self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(CSURSoftware, CSURSoftwareVersion, 'Not Installed', self.versionMatchWarningMessage, CSURSoftwareDesc))
                        self.componentWARNDict['Software'] += 1
                        continue
                    else:
                        self.logger.error("Failed to get the Compute Node's software version for software " + CSURSoftware + '.\n' + err)
                        self.inventoryError = True
                        continue
                rpmInformationList = out.strip().split(':')
                installedSoftwareEpoch = rpmInformationList[0]
                installedSoftwareVersion = rpmInformationList[1]
                self.logger.debug('The software epoch date was determined to be: ' + installedSoftwareEpoch + '.')
                if installedSoftwareEpoch < CSURSoftwareEpoch:
                    if not updateRequired:
                        updateRequired = True
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(CSURSoftware, CSURSoftwareVersion, installedSoftwareVersion, self.notVersionMatchMessage, CSURSoftwareDesc))
                else:
                    self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3:10} {4}'.format(CSURSoftware, CSURSoftwareVersion, installedSoftwareVersion, self.versionMatchMessage, CSURSoftwareDesc))

        if updateRequired:
            updateSoftwareList = re.sub(',\\s*', ' ', self.fusionIOSoftwareInstallPackageList)
            self.componentUpdateDict['Software']['FusionIO'] = updateSoftwareList
        self.logger.info("Done getting the compute node's FusionIO software inventory.")

    def getFusionIOBusList(self):
        return self.busList