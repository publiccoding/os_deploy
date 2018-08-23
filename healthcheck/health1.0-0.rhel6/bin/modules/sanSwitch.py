# Embedded file name: /hp/support/health/bin/modules/sanSwitch.py
import pexpect
import re
import os
import shutil
import pwd
import logging
import subprocess
from healthCheckUtils import CouldNotDetermineError, InvalidPasswordError

class SANSwitch():

    def __init__(self, ip, serverIP, scpUsername, scpPassword, logBaseDir, logLevel):
        self.ip = ip
        self.password = None
        self.serverIP = serverIP
        self.scpUsername = scpUsername
        self.scpPassword = scpPassword
        self.logBaseDir = logBaseDir
        self.firmwareImage = None
        self.loggerName = ip + 'Logger'
        switchLog = self.logBaseDir + 'sanSwitch_' + ip + '.log'
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
        self.versionInformationLogger.info('\n')
        self.versionInformationLogger.info('Firmware information for SAN switch at ' + ip + ':')
        return

    def initializeSwitch(self, sanSwitchResources, **kwargs):
        self.logger.info('Initializing for a SAN switch update.')
        resultDict = {'multipleUpgradesRequired': False,
         'updateNeeded': False,
         'errorMessages': []}
        prompt = re.compile('.*:admin>\\s*')
        firmwareHeaderRegex = 'Appl\\s+Primary/Secondary\\s+Versions'
        if len(kwargs) != 0:
            self.password = kwargs['password']
        else:
            self.password = 'HP1nv3nt'
        for line in sanSwitchResources:
            if 'sanSwitchCrossReference' in line:
                sanSwitchCrossReferenceList = line.split('=')
                sanSwitchCrossReference = sanSwitchCrossReferenceList[1]
                sanSwitchCrossReference = re.sub('[\'"]', '', sanSwitchCrossReference).strip()

        sanSwitchCrossReferenceDict = dict((x.split(':') for x in re.sub('\\s+:\\s+', ':', re.sub(',\\s*', ',', sanSwitchCrossReference)).split(',')))
        self.logger.info('The SAN switch cross reference dictionary was determined to be: ' + str(sanSwitchCrossReferenceDict))
        cmd = 'ssh -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + 'admin@' + self.ip
        try:
            child = pexpect.spawn(cmd, timeout=60)
            child.expect('(?i)password:\\s*')
            child.sendline(self.password)
            i = child.expect(['(?i)password:\\s*', 'Please change passwords', prompt])
            if i == 0:
                raise InvalidPasswordError('An invalid password was provided for admin.')
            if i == 1:
                child.sendcontrol('c')
                child.expect(prompt)
            child.sendline('firmwareshow')
            child.expect(prompt)
            firmwareInformation = child.before
            self.logger.debug("The output of the command (firmwareshow) used to check the switch's firmware version was: " + firmwareInformation)
            child.sendline('switchshow')
            child.expect(prompt)
            switchInformation = child.before
            self.logger.debug("The output of the command (switchshow) used to check the switch's type was: " + firmwareInformation)
            if re.search(firmwareHeaderRegex, firmwareInformation, re.DOTALL | re.MULTILINE | re.IGNORECASE) == None:
                resultDict['errorMessages'].append("The component at '" + self.ip + "' is not a SAN switch.")
                self.logger.error("The component at '" + self.ip + "' is not a SAN switch: " + firmwareInformation)
                self.logger.info("Done checking the SAN switch's connnectivity, firmware version, and setting up ssh keys.")
                return resultDict
            try:
                installedFirmwareVersion = re.search('(v(\\d\\.){2}\\d[a-z]{1})', firmwareInformation).group(1)
                self.logger.debug("The switch's current firmware version was determined to be: " + installedFirmwareVersion + '.')
            except AttributeError:
                resultDict['errorMessages'].append("Could not determine the switch's firmware version.")
                self.logger.error("Could not determine the switch's firmware version: " + firmwareInformation)
                self.logger.info("Done checking the SAN switch's connnectivity, firmware version, and setting up ssh keys.")
                return resultDict

            try:
                switchType = re.search('switchType:\\s+(\\d+)\\.\\d+', switchInformation).group(1)
                try:
                    switchModel = sanSwitchCrossReferenceDict[switchType]
                    self.logger.debug("The switch's model was determined to be: " + switchModel + '.')
                except KeyError as err:
                    resultDict['errorMessages'].append('A resource key error was encountered.')
                    self.logger.error('The resource key (' + str(err) + ") was not present in the application's resource file.")
                    self.logger.info("Done checking the SAN switch's connnectivity, firmware version, and setting up ssh keys.")
                    return resultDict

            except AttributeError:
                resultDict['errorMessages'].append("Could not determine the switch's type.")
                self.logger.error("Could not determine the switch's type: " + switchInformation)
                self.logger.info("Done checking the SAN switch's connnectivity, firmware version, and setting up ssh keys.")
                return resultDict

            switchResourceList = self.__getSwitchResources(switchModel, sanSwitchResources[:])
            if switchResourceList[0]:
                errorsEncountered = True
                resultDict['errorMessages'].append("An error occurred while getting the switch's resources.")
                self.logger.info("Done checking the SAN switch's connnectivity, firmware version, and setting up ssh keys.")
                return resultDict
            switchResourceDict = switchResourceList[1]
            try:
                csurFirmwareVersion = switchResourceDict['currentFirmwareVersion']
                if installedFirmwareVersion != csurFirmwareVersion:
                    installedFirmwareVersion = re.sub('\\d[a-z]$', 'x', installedFirmwareVersion)
                    supportedDirectMigrationVersions = switchResourceDict['supportedDirectMigrationVersions']
                    if installedFirmwareVersion not in installedFirmwareVersion:
                        resultDict['multipleUpgradesRequired'] = True
                    for key in switchResourceDict:
                        if installedFirmwareVersion in key:
                            self.firmwareImage = switchResourceDict[key]

                    if self.firmwareImage == None:
                        raise CouldNotDetermineError('Could not determine firmware image information for firmware version ' + installedFirmwareVersion + '.')
                    resultDict['updateNeeded'] = True
                else:
                    child.sendline('exit')
                    self.__logVersionInformation(switchModel, installedSoftwareVersion, csurSoftwareVersion)
                    self.logger.info('Done initializing for a SAN switch update; an update was not needed.')
                    return resultDict
            except KeyError as err:
                resultDict['errorMessages'].append('A resource key error was encountered.')
                self.logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
                self.logger.error('Errors were encountered while initializing for a SAN switch update.')
                child.sendline('exit')
                return resultDict
            except CouldNotDetermineError as err:
                self.logger.error(err.message)
                resultDict['errorMessages'].append(err.message)
                child.sendline('exit')
                return resultDict

            child.sendline('sshutil delprivkey')
            child.expect(prompt)
            child.sendline('sshutil genkey')
            child.expect('Enter passphrase.*:\\s*')
            child.sendline('')
            child.expect('Enter same passphrase again:\\s*')
            child.sendline('')
            child.expect(prompt)
            keyGenerationResult = child.before
            if 'generated successfully' not in keyGenerationResult:
                resultDict['errorMessages'].append('Problems were encountered while generating a new key pair.')
                self.logger.error('Problems were encountered while generating a new key pair: ' + keyGenerationResult)
                self.logger.error('Errors were encountered while initializing for a SAN switch update.')
                return resultDict
            child.sendline('sshutil exportpubkey')
            child.expect('Enter IP address:\\s*')
            child.sendline(self.serverIP)
            child.expect('Enter remote directory:\\s*')
            child.sendline('/tmp')
            child.expect('Enter login name:\\s*')
            child.sendline(self.scpUsername)
            child.expect('(?i)password:\\s*')
            child.sendline(self.scpPassword)
            child.expect(prompt)
            keyExportResult = child.before
            if 'is exported successfully' not in keyExportResult:
                resultDict['errorMessages'].append("There was a problem exporting the SAN switch's public key.")
                self.logger.error("There was a problem exporting the SAN switch's public key to this system (" + self.serverIP + ').')
            else:
                scpUserUid = pwd.getpwnam(self.scpUsername).pw_uid
                scpUserGid = pwd.getpwnam(self.scpUsername).pw_gid
                scpUserHomeDir = pwd.getpwnam(self.scpUsername).pw_dir
                scpUserSSHDir = scpUserHomeDir + '/.ssh'
                scpUserAuthorizedKeysFile = scpUserSSHDir + '/authorized_keys'
                try:
                    if not os.path.isdir(scpUserSSHDir):
                        os.mkdir(scpUserSSHDir, 493)
                        os.chown(scpUserSSHDir, scpUserUid, scpUserGid)
                except KeyError as err:
                    resultDict['errorMessages'].append("A resource key error was encountered while getting the scp user's account information.")
                    self.logger.error('The resource key (' + str(err) + ") was not present in the application's resource file.")
                    self.logger.info("Done checking the SAN switch's connnectivity, firmware version, and setting up ssh keys.")
                    return resultDict
                except OSError as err:
                    resultDict['errorMessages'].append("An OS error was encountered while setting up the scp user's .ssh directory.")
                    self.logger.error("An OS error was encountered while setting up the scp user's .ssh directory: \n" + str(err))
                    self.logger.info("Done checking the SAN switch's connnectivity, firmware version, and setting up ssh keys.")
                    return resultDict

                command = 'cat /tmp/out_going_Brocade6510.pub >> ' + scpUserAuthorizedKeysFile
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                self.logger.debug('The output of the command (' + command + ') used to update ' + self.scpUsername + "'s authorized_keys file with the SAN switch's public key was: " + out.strip())
                if result.returncode != 0:
                    resultDict['errorMessages'].append("There was a problem importing the SAN switch's public key.")
                    self.logger.error("There was a problem importing the SAN switch's public key into " + self.scpUsername + "'s authorized_keys file.\n" + err)
                else:
                    os.chown(scpUserAuthorizedKeysFile, scpUserUid, scpUserGid)
            configurationFileName = 'sanSwitch_' + self.ip + '_ConfigurationFile.txt'
            configurationFile = '/tmp/' + configurationFileName
            child.sendline('configupload')
            child.expect('Protocol.*:\\s*')
            child.sendline('scp')
            child.expect('Server Name or IP Address.*:\\s*')
            child.sendline(self.serverIP)
            child.expect('User Name.*:\\s*')
            child.sendline(self.scpUsername)
            child.expect('Path/Filename.*:\\s*')
            child.sendline(configurationFile)
            child.expect('Section.*:\\s*')
            child.sendline(' ')
            child.expect(prompt)
            configurationFileUploadResult = child.before
            if 'All selected config parameters are uploaded' not in configurationFileUploadResult:
                child.sendline('exit')
                raise FileUploadError("The SAN switch's configuration file failed to successfully upload to the local server.")
            child.sendline('exit')
            try:
                destination = self.logBaseDir + configurationFileName
                shutil.move(configurationFile, destination)
            except (OSError, IOError, Error) as e:
                resultDict['errorMessages'].append("There was a problem moving the SAN switch's configuration file.")
                self.logger.error("There was a problem moving the SAN switch's configuration file to " + destination + '\n' + str(e))

        except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as err:
            resultDict['errorMessages'].append('The session with the switch was aborted.')
            self.logger.error('Problems were encountered while checking the switch; session aborted: ' + str(err))
        except InvalidPasswordError as err:
            resultDict['errorMessages'].append(err.message)
            self.logger.error(err.message)
        except FileUploadError as err:
            resultDict['errorMessages'].append(err.message)
            self.logger.error(err.message)

        self.__logVersionInformation(switchModel, installedSoftwareVersion, csurSoftwareVersion)
        self.logger.info('Done initializing for a SAN switch update.')
        return resultDict

    def __getSwitchResources(self, switchModel, sanSwitchResources):
        errorsEncountered = False
        started = False
        switchResourceDict = {}
        self.logger.info("Getting the resources for switch model '" + switchModel + "'.")
        for data in sanSwitchResources:
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
                    self.logger.error('An index out of range error occured for switch resource list: ' + resourceList)

        if not started:
            errorsEncountered = True
            self.logger.error("The switch's model (" + switchModel + ') was not found in the SAN switch resource file.')
        self.logger.info("Done getting the resources for switch model '" + switchModel + "'.")
        return [errorsEncountered, switchResourceDict]

    def __logVersionInformation(self, switchModel, installedSoftwareVersion, csurSoftwareVersion):
        componentHeader = 'Switch Model'
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
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(switchModel, csurSoftwareVersion, installedSoftwareVersion, 'FAIL'))
        else:
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(switchModel, csurSoftwareVersion, installedSoftwareVersion, 'PASS'))


if __name__ == '__main__':
    ip = '10.41.0.10'
    serverIP = '10.41.0.15'
    scpUsername = 'root'
    scpPassword = 'x3r7ds5Q'
    password = 'password'
    switchSoftwareVersion = 'v7.2.2d'
    sanSwitch = SANSwitch(ip, password, serverIP, scpUsername, scpPassword)
    resultDict = sanSwitch.checkSwitch(switchSoftwareVersion)
    print resultDict