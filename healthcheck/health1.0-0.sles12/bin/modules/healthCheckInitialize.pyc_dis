# Embedded file name: ./bin/modules/healthCheckInitialize.py
import logging
import os
import subprocess
import re
import time
from fusionIOUtils import checkFusionIOFirmwareUpgradeSupport
from systemConfiguration import SystemConfiguration
from collectComponentInformation import GetComponentInformation

class Initialize:

    def __init__(self, cursesThread):
        self.healthResourceDict = {}
        self.cursesThread = cursesThread

    def __printHeader(self, programVersion):
        version = 'Version ' + programVersion
        versionLength = len(version)
        title = 'HPE SAP HANA Health Check Application'
        titleLength = len(title)
        author = 'Don Isler, Bill Neumann - SAP HANA CoE'
        authorLength = len(author)
        copyright = '(c) Copyright 2016 Hewlett Packard Enterprise Development LP'
        copyrightLength = len(copyright)
        welcomeMessageTop = '+' + '-' * 65 + '+'
        welcomeMessageTitle = '|' + title + ' ' * (65 - titleLength) + '|'
        welcomeMessageVersion = '|' + version + ' ' * (65 - versionLength) + '|'
        welcomeMessageAuthor = '|' + author + ' ' * (65 - authorLength) + '|'
        welcomeMessageCopyright = '|' + copyright + ' ' * (65 - copyrightLength) + '|'
        welcomeMessageBottom = '+' + '-' * 65 + '+'
        welcomMessageContainer = [welcomeMessageTop,
         welcomeMessageTitle,
         welcomeMessageVersion,
         welcomeMessageAuthor,
         welcomeMessageCopyright,
         welcomeMessageBottom]
        for line in welcomMessageContainer:
            self.cursesThread.insertMessage(['info', line])

        self.cursesThread.insertMessage(['info', ''])

    def init(self, healthBasePath, logBaseDir, debug, programVersion, versionInformationLogOnly, updateOSHarddrives):
        self.healthResourceDict['healthBasePath'] = healthBasePath
        self.healthResourceDict['programVersion'] = programVersion
        self.__printHeader(programVersion)
        if versionInformationLogOnly:
            self.cursesThread.insertMessage(['informative', 'Collecting system component version information.'])
        else:
            self.cursesThread.insertMessage(['informative', 'Phase 1: Initializing for the system update.'])
        systemConfiguration = SystemConfiguration(self.cursesThread)
        systemConfigurationDict = systemConfiguration.getConfiguration(healthBasePath + '/.healthrc')
        self.healthResourceDict.update(systemConfigurationDict)
        healthAppResourceFile = healthBasePath + '/resourceFiles/healthAppResourceFile'
        try:
            with open(healthAppResourceFile) as f:
                for line in f:
                    line = line.strip()
                    line = re.sub('[\'"]', '', line)
                    if len(line) == 0 or re.match('^#', line):
                        continue
                    else:
                        key, val = line.split('=')
                        key = re.sub('\\s+', '', key)
                        self.healthResourceDict[key] = val.lstrip()

        except IOError as err:
            self.__exitOnError("Unable to open the application's resource file (" + healthAppResourceFile + ') for reading; exiting program execution.')

        self.healthResourceDict['logBaseDir'] = logBaseDir
        try:
            mainApplicationLog = self.healthResourceDict['mainApplicationLog']
        except KeyError as err:
            self.__exitOnError('The resource key (' + str(err) + ") was not present in the application's resource file " + healthAppResourceFile + '; exiting program execution.')

        mainApplicationLog = logBaseDir + mainApplicationLog
        mainApplicationHandler = logging.FileHandler(mainApplicationLog)
        logger = logging.getLogger('mainApplicationLogger')
        if debug:
            logger.setLevel(logging.DEBUG)
            self.healthResourceDict['logLevel'] = 'debug'
        else:
            logger.setLevel(logging.INFO)
            self.healthResourceDict['logLevel'] = 'info'
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        mainApplicationHandler.setFormatter(formatter)
        logger.addHandler(mainApplicationHandler)
        if debug:
            logger.debug('systemConfigurationDict: ' + str(systemConfigurationDict))
        versionInformationLog = logBaseDir + 'HealthCheckReport.txt'
        self.healthResourceDict['versionInformationLog'] = versionInformationLog
        if debug:
            logger.debug('healthResourceDict: ' + str(self.healthResourceDict))
        versionInformationHandler = logging.FileHandler(versionInformationLog)
        versionInformationLogger = logging.getLogger('versionInformationLog')
        versionInformationLogger.setLevel(logging.INFO)
        versionInformationLogger.addHandler(versionInformationHandler)
        getComponentInformation = GetComponentInformation(self.healthResourceDict, self.cursesThread)
        componentListDict = getComponentInformation.getComponentInformation(versionInformationLogOnly, updateOSHarddrives)
        self.healthResourceDict['componentListDict'] = componentListDict
        return self.healthResourceDict

    def __exitOnError(self, message):
        self.cursesThread.insertMessage(['error', message])
        time.sleep(5.0)
        self.cursesThread.join()
        exit(1)