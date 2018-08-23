# Embedded file name: ./bin/modules/threePar.py
import pexpect
import re
import logging
import subprocess
import time
from healthCheckUtils import CouldNotDetermineError, InvalidPasswordError, InUseError

class ThreePAR():

    def __init__(self, ip, logBaseDir, logLevel):
        self.ip = ip
        self.username = None
        self.password = None
        self.storeServUpdateNeeded = False
        self.spUpdateNeeded = False
        self.spvarPasswordKeyError = False
        loggerName = ip + 'Logger'
        threePARLog = logBaseDir + 'threePAR_' + ip + '.log'
        handler = logging.FileHandler(threePARLog)
        self.logger = logging.getLogger(loggerName)
        if logLevel == 'debug':
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        return

    def initialize3PAR(self, generation, threePARResources, **kwargs):
        self.logger.info('Initializing for a 3PAR update.')
        installedSPVersion = None
        installedStoreServVersion = None
        errorsEncountered = False
        if len(kwargs) != 0:
            self.username = kwargs['username']
            self.password = kwargs['password']
        else:
            self.username = '3parcust'
            self.password = '3parInServ'
        resultDict = {'errorMessages': [],
         'storeServUpdateNeeded': False,
         'spUpdateNeeded': False}
        threePARResourceList = self.__get3PARResources(generation, threePARResources[:])
        if threePARResourceList[0]:
            errorsEncountered = True
            resultDict['errorMessages'].append('An error occurred while getting the 3PAR resources.')
            self.logger.error('Errors were encountered while initializing for a 3PAR update.')
            return resultDict
        else:
            threePARResourceDict = threePARResourceList[1]
            try:
                csurSPVersion = re.sub('[\'" ]', '', threePARResourceDict['spVersion'])
                csurStoreServVersion = re.sub('[\'" ]', '', threePARResourceDict['storeServVersion'])
                spPasswordCrossReference = dict((x.split(':') for x in re.sub('[\'" ]', '', threePARResourceDict['spPasswordCrossReference']).split(',')))
            except KeyError as err:
                resultDict['errorMessages'].append('A resource key error was encountered.')
                self.logger.error('The resource key (' + str(err) + ') was not present in the 3PAR resource file.')
                self.logger.error('Errors were encountered while initializing for a 3PAR update.')
                return resultDict

            cmd = 'ssh -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + self.username + '@' + self.ip
            try:
                child = pexpect.spawn(cmd, timeout=60)
                child.expect('(?i)password:\\s*')
                child.sendline(self.password)
                i = child.expect(['(?i)password:\\s*', 'Another copy of spmaint is already running', 'X\\s+Exit'])
                if i == 0:
                    raise InvalidPasswordError('An invalid password was provided for ' + self.username + '.')
                if i == 1:
                    raise InUseError('Another copy of spmaint is already running.')
                child.sendline('1')
                child.expect('X\\s+Return to previous menu')
                child.sendline('1')
                child.expect('Press <enter/return> to continue')
                versionInformation = child.before
                self.logger.debug("The output of the Service Processor's menu selection '1  ==>  Display SP Version' was: " + versionInformation)
                versionInformationList = versionInformation.splitlines()
                for line in versionInformationList:
                    line = line.strip()
                    if re.match('SP Version:', line) != None:
                        installedSPVersion = re.match('SP Version:\\s+(.*)', line).group(1)
                        self.logger.debug("The Service Processor's current software version was determined to be: " + installedSPVersion + '.')
                        break

                if installedSPVersion == None:
                    child.sendline('')
                    child.expect('X\\s+Return to previous menu')
                    child.sendline('x')
                    child.expect('X\\s+Exit')
                    child.sendline('x')
                    child.expect('Press <enter/return> to continue')
                    child.sendline('')
                    raise CouldNotDetermineError("Could not determine the Service Processor's software version.")
                if installedSPVersion != csurSPVersion:
                    resultDict['spUpdateNeeded'] = True
                    self.spUpdateNeeded = True
                try:
                    self.password = spPasswordCrossReference[installedSPVersion]
                except KeyError as err:
                    if not self.spvarPasswordKeyError:
                        self.spvarPasswordKeyError = True
                        child.sendline('')
                        child.expect('X\\s+Return to previous menu')
                        child.sendline('x')
                        child.expect('X\\s+Exit')
                        child.sendline('x')
                        child.expect('Press <enter/return> to continue')
                        child.sendline('')
                        resultDict['errorMessages'].append('A spvar password resource key error was encountered.')
                        self.logger.error('The spvar password resource key (' + str(err) + ') was not present in the 3PAR resource file.')
                        self.logger.error('Errors were encountered while initializing for a 3PAR update.')
                        return resultDict

                child.sendline('')
                child.expect('X\\s+Return to previous menu')
                child.sendline('x')
                child.expect('X\\s+Exit')
                child.sendline('3')
                child.expect('X\\s+Return to the previous menu')
                child.sendline('1')
                child.expect('Please select a StoreServ to operate on')
                child.sendline('1')
                child.expect('Press <enter/return> to continue')
                versionInformation = child.before
                child.sendline('')
                child.expect('X\\s+Return to the previous menu')
                child.sendline('x')
                child.expect('X\\s+Exit')
                child.sendline('x')
                child.expect('Press <enter/return> to continue')
                child.sendline('')
                self.logger.debug("The output of the Service Processor's menu selection '1  ==>  Display StoreServ information' was: " + versionInformation)
                versionInformationList = versionInformation.splitlines()
                for line in versionInformationList:
                    line = line.strip()
                    if re.match('InForm OS Level:', line) != None:
                        installedStoreServVersion = re.match('InForm OS Level:\\s+(.*)', line).group(1)
                        self.logger.debug("The StoreServ's current software version was determined to be: " + installedStoreServVersion + '.')
                        break

                if installedStoreServVersion == None:
                    raise CouldNotDetermineError("Could not determine the StoreServ's software version.")
                if installedStoreServVersion != csurStoreServVersion:
                    resultDict['storeServUpdateNeeded'] = True
                    self.storeServUpdateNeeded = True
                while child.isalive():
                    time.sleep(1.0)

                self.username = 'spvar'
                cmd = 'ssh -o PubkeyAuthentication=no -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ' + self.username + '@' + self.ip
                child = pexpect.spawn(cmd, timeout=60)
                child.expect('(?i)password:\\s*')
                child.sendline(self.password)
                i = child.expect(['(?i)password:\\s*', 'Another copy of spmaint is already running', 'X\\s+Exit'])
                if i == 0:
                    raise InvalidPasswordError('An invalid password was provided for ' + self.username + '.')
                if i == 1:
                    raise InUseError('Another copy of spmaint is already running.')
                child.sendline('x')
                child.expect('Press <enter/return> to continue')
                child.sendline('')
            except (pexpect.TIMEOUT, pexpect.EOF, pexpect.ExceptionPexpect) as e:
                resultDict['errorMessages'].append('The session was aborted while initializing 3PAR.')
                self.logger.error('Problems were encountered while checking the 3PAR Service Processor and StoreServ; session aborted: ' + str(e))
                errorsEncountered = True
            except InvalidPasswordError as e:
                self.logger.error(e.message)
                resultDict['errorMessages'].append(e.message)
                errorsEncountered = True
            except InUseError as e:
                self.logger.error(e.message)
                resultDict['errorMessages'].append(e.message)
                errorsEncountered = True
            except CouldNotDetermineError as e:
                self.logger.error(e.message)
                resultDict['errorMessages'].append(e.message)
                errorsEncountered = True

            if errorsEncountered:
                self.logger.error('Errors were encountered while initializing for a 3PAR update.')
            else:
                self.__logVersionInformation(installedSPVersion, csurSPVersion, installedStoreServVersion, csurStoreServVersion)
                self.logger.info('Done initializing for a 3PAR update.')
            return resultDict

    def __get3PARResources(self, generation, threePARResources):
        errorsEncountered = False
        started = False
        threePARResourceDict = {}
        self.logger.info('Getting the 3PAR resources for a ' + generation + ' system.')
        for data in threePARResources:
            data = data.strip()
            if generation not in data and not started:
                continue
            elif generation in data:
                started = True
                continue
            elif re.match('\\s*$', data):
                break
            else:
                resourceList = [ x.strip() for x in data.split('=') ]
                try:
                    threePARResourceDict[resourceList[0]] = resourceList[1]
                except IndexError as err:
                    errorsEncountered = True
                    self.logger.error('An index out of range error occured for 3PAR resource list: ' + str(resourceList))

        if not started:
            errorsEncountered = True
            self.logger.error('The system generation (' + generation + ') was not found in the 3PAR resource file.')
        self.logger.info('Done getting the 3PAR resources for a ' + generation + ' system.')
        return [errorsEncountered, threePARResourceDict]

    def __logVersionInformation(self, installedSPVersion, csurSPVersion, installedStoreServVersion, csurStoreServVersion):
        if i == 1:
            self.versionInformationLogger.info('Software information for 3PAR components at ' + self.ip + ':')
            componentHeader = 'Component'
            componentUnderLine = '---------'
            csurVersionHeader = 'CSUR Version'
            csurVersionUnderLine = '------------'
            currentVersionHeader = 'Current Version'
            currentVersionUnderLine = '---------------'
            statusHeader = 'Status'
            statusUnderLine = '------'
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentHeader, csurVersionHeader, currentVersionHeader, statusHeader))
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format(componentUnderLine, csurVersionUnderLine, currentVersionUnderLine, statusUnderLine))
        if installedSPVersion != csurSPVersion:
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('Service Processor', csurSPVersion, installedSPVersion, 'FAIL'))
        else:
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('Service Processor', csurSPVersion, installedSPVersion, 'PASS'))
        if installedStoreServVersion != csurStoreServVersion:
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('StoreServ', csurStoreServVersion, installedStoreServVersion, 'FAIL'))
        else:
            self.versionInformationLogger.info('{0:40} {1:25} {2:25} {3}'.format('StoreServ', csurStoreServVersion, installedStoreServVersion, 'PASS'))


if __name__ == '__main__':
    ip = '10.41.0.28'
    csurSPVersion = '4.4.0'
    csurStoreServVersion = '3.3.2'
    threePAR = ThreePAR(ip, '/tmp/', 'debug')
    resultDict = threePAR.initialize3PAR()
    print resultDict