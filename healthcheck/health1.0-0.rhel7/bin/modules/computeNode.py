# Embedded file name: ./bin/modules/computeNode.py
import logging
import os
import subprocess
import re
import shutil
from fusionIOUtils import checkFusionIOFirmwareUpgradeSupport
from computeNodeInventory import ComputeNodeInventory, Gen1ScaleUpComputeNodeInventory

class ComputeNode:

    def __init__(self, healthResourceDict, ip):
        self.healthResourceDict = healthResourceDict
        self.computeNodeDict = {}
        try:
            self.healthBasePath = self.healthResourceDict['healthBasePath']
            logLevel = self.healthResourceDict['logLevel']
            logBaseDir = self.healthResourceDict['logBaseDir']
            self.versionInformationLog = self.healthResourceDict['versionInformationLog']
        except KeyError as err:
            raise KeyError(str(err))

        self.computeNodeDict['ip'] = ip
        hostname = os.uname()[1]
        self.computeNodeDict['hostname'] = hostname
        computeNodeLog = logBaseDir + 'computeNode_' + hostname + '.log'
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

    def computeNodeInitialize(self, computeNodeResources, versionInformationLogOnly, updateOSHarddrives):
        logger = logging.getLogger(self.loggerName)
        resultDict = {'updateNeeded': False,
         'errorMessages': []}
        command = 'dmidecode -s system-product-name'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        out = out.strip()
        logger.debug('The output of the command (' + command + ") used to get the system's model was: " + out)
        if result.returncode != 0:
            logger.error("Unable to get the system's model information.\n" + err)
            resultDict['errorMessages'].append("Unable to get the system's model information.")
            return resultDict
        else:
            try:
                systemModel = re.match('[a-z,0-9]+\\s+(.*)', out, re.IGNORECASE).group(1).replace(' ', '')
            except AttributeError as err:
                logger.error("There was a system model match error when trying to match against '" + out + "':\n" + str(err) + '.')
                resultDict['errorMessages'].append('There was a system model match error.')
                return resultDict

            try:
                if systemModel not in self.healthResourceDict['supportedComputeNodeModels']:
                    logger.error("The system's model (" + systemModel + ') is not supported by this CSUR bundle.')
                    resultDict['errorMessages'].append("The system's model is not supported by this CSUR bundle.")
                    return resultDict
            except KeyError as err:
                logger.error('The resource key (' + str(err) + ") was not present in the application's esource file.")
                resultDict['errorMessages'].append('A resource key error was encountered.')
                return resultDict

            logger.debug("The system's model was determined to be: " + systemModel + '.')
            self.computeNodeDict['systemModel'] = systemModel
            command = 'dmidecode -s processor-version'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            out = out.strip()
            logger.debug('The output of the command (' + command + ') used to get the processor version was: ' + out)
            if result.returncode != 0:
                logger.error('Unable to get the processor version.\n' + err)
                resultDict['errorMessages'].append('Unable to get the processor version information.')
                return resultDict
            try:
                processorVersion = re.search('CPU (E\\d-\\s*\\d{4}\\w* v\\d)', out).group(1).replace(' ', '')
            except AttributeError as err:
                logger.error("There was a processor match error when trying to match against '" + out + "':\n" + str(err) + '.')
                resultDict['errorMessages'].append('There was a processor match error.')
                return resultDict

            logger.debug("The processor's version was determined to be: " + processorVersion + '.')
            self.computeNodeDict['processorVersion'] = processorVersion
            command = 'cat /proc/version'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.debug('The output of the command (' + command + ') used to get the OS distribution information was: ' + out.strip())
            if result.returncode != 0:
                logger.error("Unable to get the system's OS distribution version information.\n" + err)
                resultDict['errorMessages'].append("Unable to get the system's OS distribution version information.")
                return resultDict
            versionInfo = out.lower()
            if 'suse' in versionInfo:
                OSDist = 'SLES'
                command = 'cat /etc/SuSE-release'
            else:
                OSDist = 'RHEL'
                command = 'cat /etc/redhat-release'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Unable to get the system's OS distribution level.\n" + err)
                resultDict['errorMessages'].append("Unable to get the system's OS distribution level.")
                return resultDict
            releaseInfo = out.replace('\n', ' ')
            if OSDist == 'SLES':
                try:
                    slesVersion = re.match('.*version\\s*=\\s*([1-4]{2})', releaseInfo, re.IGNORECASE).group(1)
                except AttributeError as err:
                    logger.error("There was SLES OS version match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.')
                    resultDict['errorMessages'].append('There was a SLES OS version match error.')
                    return resultDict

                try:
                    slesPatchLevel = re.match('.*patchlevel\\s*=\\s*([1-4]{1})', releaseInfo, re.IGNORECASE).group(1)
                except AttributeError as err:
                    logger.error("There was SLES patch level match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.')
                    resultDict['errorMessages'].append('There was a SLES patch level match error.')
                    return resultDict

                osDistLevel = OSDist + slesVersion + '.' + slesPatchLevel
            else:
                try:
                    rhelVersion = re.match('.*release\\s+([6-7]{1}.[0-9]{1}).*', releaseInfo, re.IGNORECASE).group(1)
                except AttributeError as err:
                    logger.error("There was RHEL OS version match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.')
                    resultDict['errorMessages'].append('There was a RHEL OS version match error.')
                    return resultDict

                osDistLevel = OSDist + rhelVersion
            try:
                if osDistLevel not in self.healthResourceDict['supportedDistributionLevels']:
                    if osDistLevel not in self.healthResourceDict['unsupportedUpgradableDistLevels']:
                        logger.error("The system's OS distribution level (" + osDistLevel + ') is not supported by this CSUR bundle.')
                        resultDict['errorMessages'].append("The system's OS distribution level is not supported by this CSUR bundle.")
                        return resultDict
            except KeyError as err:
                logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                resultDict['errorMessages'].append('A resource key error was encountered.')
                return resultDict

            logger.debug("The system's OS distribution level was determined to be: " + osDistLevel + '.')
            self.computeNodeDict['osDistLevel'] = osDistLevel
            if not versionInformationLogOnly:
                if 'DL380' in systemModel:
                    command = '/opt/cmcluster/bin/cmviewcl -f line'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    logger.debug('The output of the command (' + command + ') used to check if the cluster is running was: ' + out.strip())
                    if result.returncode != 0:
                        logger.warn('Unable to check if the cluster is running.\n' + err)
                        resultDict['errorMessages'].append('Unable to check if the cluster is running.')
                    clusterView = out.splitlines()
                    for line in clusterView:
                        if re.search('^status=', line):
                            if re.match('status=up', line):
                                logger.warn('It appears that the cluster is still running.\n' + out)
                                resultDict['errorMessages'].append('It appears that the cluster is still running.')

                if not ('DL380' in systemModel or 'DL320' in systemModel):
                    command = 'ps -C hdbnameserver,hdbcompileserver,hdbindexserver,hdbpreprocessor,hdbxsengine,hdbwebdispatcher'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    logger.debug('The output of the command (' + command + ') used to check if SAP is running was: ' + out.strip())
                    if result.returncode == 0:
                        logger.warn('It appears that SAP HANA is still running.\n' + out)
                        resultDict['errorMessages'].append('It appears that SAP HANA is still running.')
                if systemModel == 'DL580G7' or systemModel == 'DL980G7':
                    command = 'mount'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    logger.debug('The output of the command (' + command + ') used to check if the log partition is mounted was: ' + out.strip())
                    if result.returncode != 0:
                        logger.error('Unable to check if the log partition is mounted.\n' + err)
                        resultDict['errorMessages'].append('Unable to check if the log partition is mounted.')
                        return resultDict
                    if re.search('/hana/log|/HANA/IMDB-log', out, re.MULTILINE | re.DOTALL) != None:
                        logger.error('The log partition is still mounted.')
                        resultDict['errorMessages'].append('The log partition needs to be unmounted before the system is updated.')
                        return resultDict
                    command = 'uname -r'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    kernel = out.strip()
                    logger.debug('The output of the command (' + command + ') used to get the currently used kernel was: ' + kernel)
                    if result.returncode != 0:
                        logger.error("Unable to get the system's current kernel information.\n" + err)
                        resultDict['errorMessages'].append("Unable to get the system's current kernel information.")
                        return resultDict
                    logger.debug('The currently used kernel was determined to be: ' + kernel + '.')
                    self.computeNodeDict['kernel'] = kernel
                    command = 'uname -p'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    processorType = out.strip()
                    logger.debug('The output of the command (' + command + ") used to get the compute node's processor type was: " + processorType)
                    if result.returncode != 0:
                        logger.error("Unable to get the system's processor type.\n" + err)
                        resultDict['errorMessages'].append("Unable to get the system's processor type.")
                        return resultDict
                    logger.debug("The compute node's processor type was determined to be: " + processorType + '.')
                    self.computeNodeDict['processorType'] = processorType
                    try:
                        if not checkFusionIOFirmwareUpgradeSupport(self.healthResourceDict['fusionIOFirmwareVersionList'], self.loggerName):
                            resultDict['errorMessages'].append('The fusionIO firmware is not at a supported version for an automatic upgrade.')
                            return resultDict
                    except KeyError as err:
                        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                        resultDict['errorMessages'].append('A resource key error was encountered.')
                        return resultDict

            if not updateOSHarddrives:
                result = self.__checkDrivers(computeNodeResources, systemModel, osDistLevel)
                if result != '':
                    resultDict['errorMessages'].append(result)
                    return resultDict
            try:
                if systemModel == 'DL580G7' or systemModel == 'DL980G7':
                    computeNodeInventory = Gen1ScaleUpComputeNodeInventory(self.computeNodeDict.copy(), self.healthResourceDict['noPMCFirmwareUpdateModels'], computeNodeResources, self.healthResourceDict.copy())
                else:
                    computeNodeInventory = ComputeNodeInventory(self.computeNodeDict.copy(), self.healthResourceDict['noPMCFirmwareUpdateModels'], computeNodeResources, self.healthResourceDict.copy())
            except KeyError as err:
                logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                resultDict['errorMessages'].append('A resource key error was encountered.')
                return resultDict

            if not updateOSHarddrives:
                computeNodeInventory.getComponentUpdateInventory()
            else:
                computeNodeInventory.getLocalHardDriveFirmwareInventory()
            if computeNodeInventory.getInventoryStatus():
                resultDict['errorMessages'].append("Errors were encountered during the compute node's inventory.")
                return resultDict
            if versionInformationLogOnly:
                if os.path.isfile(self.versionInformationLog):
                    try:
                        shutil.copy(self.versionInformationLog, self.healthBasePath)
                    except IOError as err:
                        self.logger.error('I/O Error while copy of ' + self.versionInformationLog + ' to ' + self.healthBasePath)

                return resultDict
            componentUpdateDict = computeNodeInventory.getComponentUpdateDict()
            if updateOSHarddrives:
                if len(componentUpdateDict['Firmware']) != 0:
                    self.computeNodeDict['componentUpdateDict'] = componentUpdateDict
                    resultDict['updateNeeded'] = True
            else:
                componentDictSizes = [ len(dict) for dict in componentUpdateDict.values() ]
                if any((x != 0 for x in componentDictSizes)):
                    self.computeNodeDict['componentUpdateDict'] = componentUpdateDict
                    resultDict['updateNeeded'] = True
                    if 'FusionIO' in componentUpdateDict['Firmware']:
                        self.computeNodeDict['busList'] = computeNodeInventory.getFusionIOBusList()
                    self.computeNodeDict['externalStoragePresent'] = computeNodeInventory.isExternalStoragePresent()
            return resultDict

    def __checkDrivers(self, computeNodeResources, systemModel, osDistLevel):
        errorMessage = ''
        logger = logging.getLogger(self.loggerName)
        driversFound = False
        started = False
        mlnxDriverFound = False
        for data in computeNodeResources:
            data = data.replace(' ', '')
            if re.match('^#', data):
                continue
            if not re.match('^Drivers:\\s*$', data) and not driversFound:
                continue
            elif 'Drivers' in data:
                driversFound = True
                continue
            elif not (osDistLevel in data and systemModel in data) and not started:
                continue
            elif osDistLevel in data and systemModel in data:
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                computeNodeDriverList = data.split('|')
                computeNodeDriver = computeNodeDriverList[0]
                command = 'modinfo ' + computeNodeDriver
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                logger.debug('The output of the command (' + command + ') used to check if the ' + computeNodeDriver + ' driver is loaded was: ' + out.strip())
                if result.returncode != 0:
                    if (computeNodeDriver == 'mlx4_en' or computeNodeDriver == 'mlnx') and not mlnxDriverFound:
                        mlnxDriverFound = True
                        continue
                    logger.error('The ' + computeNodeDriver + ' driver does not appear to be loaded.\n' + err)
                    errorMesssage = 'The ' + computeNodeDriver + ' driver does not appear to be loaded.'
                    return errorMessage

        if systemModel == 'DL580G7' or systemModel == 'DL980G7':
            command = 'modinfo iomemory_vsl'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.debug('The output of the command (' + command + ') used to check if the iomemory_vsl driver is loaded was: ' + out.strip())
            if result.returncode != 0:
                logger.error('The iomemory_vsl driver does not appear to be loaded.\n' + err)
                errorMessage = 'The iomemory_vsl driver does not appear to be loaded.'
        return errorMessage

    def getComputeNodeDict(self):
        return self.computeNodeDict