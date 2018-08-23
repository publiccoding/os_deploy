# File: c (Python 2.7)

import re
import os
import subprocess
import logging
import datetime

class ComputeNodeInventory:
    
    def __init__(self, computeNodeDict, noPMCFirmwareUpdateModels, computeNodeResources, healthResourceDict):
        self.computeNodeResources = computeNodeResources
        self.CSURDesc = 'HPE Converged Systems Upgrade Release'
        self.noPMCFirmwareUpdateModels = noPMCFirmwareUpdateModels
        self.osDistListDict = {
            'SLES11.3': 'SLES4SAP 11 SP3',
            'SLES11.4': 'SLES4SAP 11 SP4',
            'SLES12.1': 'SLES4SAP 12 SP1',
            'RHEL6.7': 'RHEL4SAP 6 SP7',
            'RHEL7.2': 'RHEL4SAP 7 SP2' }
        systemListDict = {
            'DL580Gen8': 'CS500 Ivy Bridge',
            'DL580Gen9': 'CS500',
            'DL580G7': 'Gen1.0',
            'DL980G7': 'Gen1.0' }
        processorListDict = {
            'E7-8890v3': 'Haswell',
            'E7-8890v4': 'Broadwell',
            'E7-8880v3': 'Haswell',
            'E7-8880Lv3': 'Haswell' }
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
        except KeyError:
            err = None
            raise KeyError('Missing key from health App resource file: ' + str(err))

        
        try:
            self.osDistLevel = computeNodeDict['osDistLevel']
            self.processorVersion = computeNodeDict['processorVersion']
            self.systemModel = computeNodeDict['systemModel']
        except KeyError:
            err = None
            raise KeyError('Missing key from compute Node resource file: ' + str(err))

        
        try:
            self.CSURRelease = re.search('Version:\\s*([a-z0-9._-]+)', healthResourceDict['releaseNotes'], re.IGNORECASE).group(1)
        except (AttributeError, KeyError):
            err = None
            self.logger.error("Missing key 'releaseNotes' or match key error from healthApp Resource file." + str(err))
            self.CSURRelease = 'Unknown'

        
        try:
            self.osPatchUpdateRelease = re.search('Version:\\s*([a-z0-9._-]+)', healthResourceDict['osPatchUpdateReleaseNotes'], re.IGNORECASE).group(1)
        except (AttributeError, KeyError):
            err = None
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
        self.firmwareDict = { }
        self.unsupportedUpgradableDist = False
        self.componentUpdateDict = {
            'Firmware': { },
            'Drivers': { },
            'Software': { },
            'CSUR': { },
            'osPatchBundle': { } }
        self.componentWARNDict = {
            'Firmware': 0,
            'Drivers': 0,
            'Software': 0,
            'CSUR': 0,
            'osPatchBundle': 0 }
        self.notVersionMatchMessage = 'FAIL'
        self.versionMatchMessage = 'PASS'
        self.versionMatchWarningMessage = 'WARNING'

    
    def _ComputeNodeInventory__getFirmwareDict(self):
        started = False
        self.logger.info('Getting the firmware dictionary.')
        for data in self.computeNodeResources:
            if not re.match('^Firmware:\\s*$', data) and not started:
                continue
                continue
            if re.match('^Firmware:\\s*$', data):
                started = True
                continue
                continue
            if re.match('\\s*$', data):
                break
                continue
            data2 = data.replace(' ', '')
            firmwareList = data.split('|')
            firmwareList2 = data2.split('|')
            self.firmwareDict[firmwareList[0]] = [
                firmwareList2[1],
                firmwareList2[2],
                firmwareList[-1].strip()]
        
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
        self._ComputeNodeInventory__getCSURInventory()
        self._getComputeNodeSpecificCSURInventory()
        if self.osDistLevel in self.unsupportedUpgradableDistLevels:
            self.versionInformationLogger.info('\nThe ' + self.osDistLevel + ' is not supported, but is upgradable to a supported release.\n')
            self.unsupportedUpgradableDi