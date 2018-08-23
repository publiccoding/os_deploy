# Embedded file name: /hp/support/health/bin/modules/networkSwitch.py
import pexpect
import re
import logging
from healthCheckUtils import InvalidPasswordError

class NetworkSwitch():
    """
    The constructor sets up instance variables and initiates logging.
    """

    def __init__(self, generation, ip, logBaseDir, logLevel):
        self.ip = ip
        self.loggerName = ip + 'Logger'
        self.username = None
        self.password = None
        self.softwareImage = None
        self.switchSlotsToUpgrade = []
        self.slotSoftwareVersionDict = {}
        self.upgradeStatus = None
        if generation == 'Gen1.0':
            self.switchType = 'ProCurve'
        else:
            self.switchType = '3Com'
        switchLog = logBaseDir + 'networkSwitch_' + ip + '.log'
        handler = logging.FileHandler(switchLog)
        self.logger = logging.getLogger(self.loggerName)
        if logLevel == 'debug':
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.versionInformationLogger = logging.getLogger('versionInformationLog')
        return

    def initializeSwitch(self, networkSwitchResources, **kwargs):
        self.logger.info('Initializing for a Network switch update.')
        resultDict = {'updateNeeded': False,
         'errorMessages': []}
        threeComPrompt = re.compile('<[a-zA-Z0-9-]+>')
        if len(kwargs) != 0:
            self.username = kwargs['username']
            self.password = kwargs['password']
        elif self.switchType == '3Com':
            self.username = 'admin'
            self.password = 'HP1nv3nt'
        self.switchSlotsToUpgrade = []
        cmd = 'ssh -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + self.username + '@' + self.ip
        if self.switchType == '3Com':
            try:
                child = pexpect.spawn(cmd, timeout=60)
                i = child.expect(['(?i)password:\\s*', threeComPrompt])
                if i == 0:
                    child.sendline(self.password)
                    i = child.expect(['(?i)password:\\s*', threeComPrompt])
                    if i == 0:
                        self.logger.error('An invalid password was provided for user ' + self.username + '.')
                        resultDict['errorMessages'].append('An invalid password was provided.')
                        raise InvalidPasswordError('An invalid password was provided for user ' + self.username + '.')
                child.sendline('screen-length disable')
                child.expect(threeComPrompt)
                cmd = 'display device verbose | include "^Slot[ ]+[0-9]{1,}|^Type|^Software Ver"'
                child.sendline(cmd)
                child.expect(threeComPrompt)
                deviceInformation = child.before
                self.logger.debug('The output of the command (' + cmd + ") used to check the switch's slot, model, and software version was: " + deviceInformation)
                switchTupleList = re.findall('Slot\\s+(\\d+)\\s+info:|Type\\s+:\\s+([A-Z0-9- ]+)|Software Ver\\s+:\\s+([0-9A-Z]+)', deviceInformation)
                self.logger.debug('The switch tuple list was determined to be: ' + str(switchTupleList) + '.')
                if len(switchTupleList) != 6:
                    self.logger.error("The network switch's (" + self.ip + ') slot, model, and software version could not be determined:\n' + deviceInformation)
                    resultDict['errorMessages'].append("The network switch's slot, model, and software version could not be determined.")
                    self.logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
                    return resultDict
                switchList = [ filter(None, i) for i in switchTupleList ]
                self.logger.debug('The switch device list was determined to be: ' + str(switchList) + '.')
                switchModel = switchList[1][0]
                switchResourceList = self.__getSwitchResources(switchModel, networkSwitchResources[:])
                if switchResourceList[0]:
                    errorsEncountered = True
                    resultDict['errorMessages'].append("An error occurred while getting the switch's resources.")
                    self.logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
                    return resultDict
                switchResourceDict = switchResourceList[1]
                try:
                    self.softwareImage = re.sub('[\'"]', '', switchResourceDict['softwareImage']).strip()
                    csurSoftwareVersion = re.sub('[\'"]', '', switchResourceDict['softwareVersion']).strip()
                    softwareImageSize = re.sub('[\'"]', '', switchResourceDict['softwareImageSize']).strip()
                except KeyError as err:
                    resultDict['errorMessages'].append('A resource key error was encountered.')
                    self.logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                    self.logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
                    return resultDict

                count = 0
                for i in range(0, 2):
                    availableSpace = None
                    switchSlot = switchList[i + count][0]
                    count += 2
                    installedSoftwareVersion = switchList[i + count][0]
                    self.slotSoftwareVersionDict[switchSlot] = installedSoftwareVersion
                    if installedSoftwareVersion != csurSoftwareVersion:
                        self.switchSlotsToUpgrade.append(switchSlot)
                        if not resultDict['updateNeeded']:
                            resultDict['updateNeeded'] = True
                        cmd = 'dir slot' + switchSlot + '#flash:/ | include "KB[ ]+free)$"'
                        child.sendline(cmd)
                        child.expect(threeComPrompt)
                        spaceInformation = child.before
                        self.logger.debug('The output of the command (' + cmd + ") used to check the switch's available space was: " + spaceInformation)
                        spaceInformationList = spaceInformation.splitlines()
                        for line in spaceInformationList:
                            if re.match('.*\\((\\d+)\\s+KB\\s+free', line) != None:
                                availableSpace = re.match('.*\\((\\d+)\\s+KB\\s+free', line).group(1)
                                self.logger.debug("The switch's available space in slot " + switchSlot + ' was determined to be: ' + availableSpace + ' KB.')

                        if availableSpace != None:
                            if int(availableSpace) < int(softwareImageSize):
                                self.logger.error("The switch's available space in slot " + switchSlot + ' was determined to be: ' + availableSpace + ' KB.')
                                resultDict['errorMessages'].append('There is insufficient space on the switch for the update.')
                                self.logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
                                return resultDict
                        else:
                            self.logger.error("The switch's available space could not be determined: " + spaceInformation)
                            resultDict['errorMessages'].append("The switch's available space could not be determined")
                            self.logger.info("Done checking the switch's connnectivity, model, software version, and setting up its ftp server if necessary.")
                            return resultDict

                if len(self.switchSlotsToUpgrade) > 0:
                    child.sendline('display ftp-server')
                    child.expect(threeComPrompt)
                    ftpServerInformation = child.before
                    if 'FTP server is running' not in ftpServerInformation:
                        systemViewPrompt = re.compile('\\[[a-zA-Z0-9-]+\\]')
                        child.sendline('system-view')
                        child.expect(systemViewPrompt)
                        child.sendline('ftp server enable')
                        child.expect(systemViewPrompt)
                        child.sendline('display ftp-server')
                        child.expect(systemViewPrompt)
                        ftpServerInformation = child.before
                        child.sendline('quit')
                        if 'FTP server is running' not in ftpServerInformation:
                            resultDict['errorMessages'].append("The switch's ftp server could not be enabled.")
                child.sendline('quit')
            except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as e:
                resultDict['errorMessages'].append('The session with the switch was aborted.')
                self.logger.error('Problems were encountered while checking the switch; session aborted: ' + str(e))
            except InvalidPasswordError as e:
                self.logger.error(e.message)

        self.__logVersionInformation(csurSoftwareVersion)
        self.logger.info('Done initializing for a Network switch update.')
        return resultDict

    def __logVersionInformation(self, csurSoftwareVersion):
        for i in range(1, 3):
            installedSoftwareVersion = self.slotSoftwareVersionDict[str(i)]
            if i == 1:
                self.versionInformationLogger.info('Software information for network switch at ' + self.ip + ':')
                componentHeader = 'Switch Slot'
                componentUnderLine = '------------'
                csurVersionHeader = 'CSUR Version'
                csurVersionUnderLine = '------------'
                currentVersionHeader = 'Current Version'
                currentVersionUnderLine = '---------------'
                statusHeader = 'Status'
                statusUnderLine = '------'
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))
            if installedSoftwareVersion != csurSoftwareVersion:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(str(i), csurSoftwareVersion, installedSoftwareVersion, 'FAIL'))
            else:
                self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(str(i), csurSoftwareVersion, installedSoftwareVersion, 'PASS'))

    def getSwitchIP(self):
        return self.ip

    def __getSwitchResources(self, switchModel, networkSwitchResources):
        errorsEncountered = False
        started = False
        switchResourceDict = {}
        self.logger.info("Getting the resources for switch model '" + switchModel + "'.")
        for data in networkSwitchResources:
            data = data.strip()
            if not re.match(switchModel, data) and not started:
                continue
            elif re.match(switchModel, data):
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                resourceList = [ x.strip() for x in data.split('=') ]
                try:
                    switchResourceDict[resourceList[0]] = resourceList[1]
                except IndexError as err:
                    errorsEncountered = True
                    self.logger.error('An index out of range error occured for switch resource list: ' + str(resourceList))

        if not started:
            errorsEncountered = True
            self.logger.error("The switch's model (" + switchModel + ') was not found in the network switch resource file.')
        self.logger.info("Done getting the resources for switch model '" + switchModel + "'.")
        return [errorsEncountered, switchResourceDict]


if __name__ == '__main__':
    ip = '10.41.0.9'
    username = 'admin'
    password = 'HP1nv3nt'
    switchType = '3Com'
    switchSoftwareVersion = '2422P01'
    model = 'FF 5930-4Slot Switch'
    imageSize = 100000
    networkSwitch = NetworkSwitch(ip, username, password)
    resultDict = networkSwitch.checkSwitch(switchType, model, switchSoftwareVersion, imageSize)
    print resultDict