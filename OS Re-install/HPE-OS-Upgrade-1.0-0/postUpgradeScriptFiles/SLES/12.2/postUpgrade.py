# Embedded file name: ./postUpgrade.py
import re
import os
import sys
import logging
import traceback
import optparse
from modules.computeNode import getServerModel, getOSDistribution
from modules.postUpgradeTasks import configureSnapper, checkSAPHANAConfiguration, enableMultiversionSupport, cleanupGrubCfg, checkServices, updateServiceguardPackages, configureMellanox, disableServices
from modules.sapHANANodeSpec import updateBIOS, restoreFstab, updateSysctl, configureNofile
RED = '\x1b[31m'
YELLOW = '\x1b[33m'
GREEN = '\x1b[32m'
RESETCOLORS = '\x1b[0m'

def main():
    programVersion = '1.0-0'
    programName = os.path.basename(sys.argv[0]).split('.')[0]
    errorsEncountered = False
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS
        exit(1)
    usage = 'usage: %prog [-h] [-p] [-v]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-p', action='store_true', default=False, help='This option is used after an upgrade to check services and SAP Note settings.')
    parser.add_option('-v', action='store_true', default=False, help="This option is used to display the application's version.")
    options, args = parser.parse_args()
    if options.v:
        print programName + ' ' + programVersion
        exit(0)
    osDist, osDistLevel = getOSDistribution()
    logDir = '/var/log/CoESapHANA_' + osDist + '_UpgradeLogDir'
    if not os.path.isdir(logDir):
        try:
            os.mkdir(logDir)
        except OSError as err:
            print RED + "Unable to create the post upgrade log directory '" + logDir + "'; fix the problem and try again; exiting program execution.\n" + str(err) + RESETCOLORS
            exit(1)

    statusLogFile = logDir + '/status.log'
    debugLogFile = logDir + '/debug.log'
    statusHandler = logging.FileHandler(statusLogFile)
    debugHandler = logging.FileHandler(debugLogFile)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    statusHandler.setFormatter(formatter)
    debugHandler.setFormatter(formatter)
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.setLevel(logging.INFO)
    logger.addHandler(statusHandler)
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    debugLogger.setLevel(logging.INFO)
    debugLogger.addHandler(debugHandler)
    debugLogger.info("The program's version is: " + programVersion + '.')
    serverModel = getServerModel()
    try:
        programParentDir = ''
        cwd = os.getcwd()
        programParentDir = os.path.dirname(os.path.realpath(__file__))
        if cwd != programParentDir:
            os.chdir(programParentDir)
    except OSError as err:
        debugLogger.error("Unable to change into the programs parent directory '" + programParentDir + "'.\n" + str(err))
        print RED + "Unable to change into the programs parent directory '" + programParentDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    upgradeResourceDict = {}
    try:
        with open('upgradeResourceFile') as f:
            for line in f:
                line = line.strip()
                if len(line) == 0 or re.match('^\\s*#', line) or re.match('^\\s+$', line):
                    continue
                else:
                    line = re.sub('[\'"]', '', line)
                    key, val = line.split('=')
                    key = key.strip()
                    upgradeResourceDict[key] = re.sub('\\s*,\\s*', ',', val).strip()

    except IOError as err:
        debugLogger.error("Unable to access the application's resource file 'upgradeResourceFile'.\n" + str(err))
        print RED + "Unable to access the application's resource file 'upgradeResourceFile'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    if options.p:
        if serverModel == 'Superdome' or 'DL580' in serverModel:
            if serverModel == 'Superdome':
                errors = checkSAPHANAConfiguration(serverModel, osDist)
            elif osDist == 'SLES':
                errors = checkSAPHANAConfiguration(serverModel, osDist, upgradeResourceDict['slesKernelParameters'])
            else:
                errors = checkSAPHANAConfiguration(serverModel, osDist, upgradeResourceDict['rhelKernelParameters'])
            if errors:
                if not errorsEncountered:
                    errorsEncountered = True
        errors = checkServices()
        if errors:
            if not errorsEncountered:
                errorsEncountered = True
    else:
        progressStatusFile = logDir + '/.restorationProgress'
        try:
            if os.path.isfile(progressStatusFile):
                with open(progressStatusFile) as f:
                    progressDict = dict.fromkeys((x.strip() for x in f))
            else:
                progressDict = {}
            if os.path.isfile(progressStatusFile):
                f = open(progressStatusFile, 'a')
            else:
                f = open(progressStatusFile, 'w')
            if serverModel == 'ProLiant DL360 Gen9' or serverModel == 'ProLiant DL380p Gen8' or serverModel == 'ProLiant DL360p Gen8' or serverModel == 'ProLiant DL320e Gen8 v2':
                serviceguardRPMDir = programParentDir + '/serviceguardRPMS'
                if os.path.isdir(serviceguardRPMDir):
                    if 'updateServiceguardPackages' not in progressDict:
                        errors = updateServiceguardPackages(serviceguardRPMDir)
                        if errors:
                            if not errorsEncountered:
                                errorsEncountered = True
                        else:
                            f.write('updateServiceguardPackages\n')
                    else:
                        print YELLOW + 'The Serviceguard packages were not updated, since they were already updated.' + RESETCOLORS
            fstabFile = programParentDir + '/fstabFile/fstab'
            if os.path.isfile(fstabFile):
                if 'restoreFstab' not in progressDict:
                    errors = restoreFstab(fstabFile)
                    if errors:
                        if not errorsEncountered:
                            errorsEncountered = True
                    else:
                        f.write('restoreFstab\n')
                else:
                    print YELLOW + 'The fstab file was not restored, since it was already restored.' + RESETCOLORS
            if osDist == 'SLES':
                limitsFile = programParentDir + '/limitsFile/limits.conf'
                if os.path.isfile(limitsFile):
                    if 'configureNofile' not in progressDict:
                        errors = configureNofile(limitsFile, upgradeResourceDict['sapsysNofileValue'])
                        if errors:
                            if not errorsEncountered:
                                errorsEncountered = True
                        else:
                            f.write('configureNofile\n')
                    else:
                        print YELLOW + 'hard/soft nofile limits for @sapsys, were not configured, since they were already configured.' + RESETCOLORS
            if 'DL580' in serverModel:
                if 'updateBIOS' not in progressDict:
                    errors = updateBIOS(programParentDir)
                    if errors:
                        if not errorsEncountered:
                            errorsEncountered = True
                    else:
                        f.write('updateBIOS\n')
                else:
                    print YELLOW + 'The BIOS was not updated, since it was already updated.' + RESETCOLORS
                if os.path.isdir(programParentDir + '/mellanoxDriver'):
                    if 'configureMellanox' not in progressDict:
                        errors = configureMellanox(programParentDir)
                        if errors:
                            if not errorsEncountered:
                                errorsEncountered = True
                        else:
                            f.write('configureMellanox\n')
                    else:
                        print YELLOW + 'The Mellanox driver was not installed, since it was already installed.' + RESETCOLORS
                if os.path.isfile('/etc/sysctl.conf'):
                    if 'updateSysctl' not in progressDict:
                        if osDist == 'SLES':
                            errors = updateSysctl(upgradeResourceDict['slesKernelParameters'])
                        else:
                            errors = updateSysctl(upgradeResourceDict['rhelKernelParameters'])
                        if errors:
                            if not errorsEncountered:
                                errorsEncountered = True
                        else:
                            f.write('updateSysctl\n')
                    else:
                        print YELLOW + '/etc/sysctl.conf was not updated, since an attempt to update it was already made.' + RESETCOLORS
            if osDist == 'SLES':
                if 'configureSnapper' not in progressDict:
                    errors = configureSnapper()
                    if errors:
                        errorsEncountered = True
                    else:
                        f.write('configureSnapper\n')
                else:
                    print YELLOW + 'The snapper configuration was not updated, since it was already updated.' + RESETCOLORS
                if 'enableMultiversionSupport' not in progressDict:
                    errors = enableMultiversionSupport()
                    if errors:
                        if not errorsEncountered:
                            errorsEncountered = True
                    else:
                        f.write('enableMultiversionSupport\n')
                else:
                    print YELLOW + 'Kernel multiversion support was not enabled, since it was already enabled.' + RESETCOLORS
                if 'cleanupGrubCfg' not in progressDict:
                    errors = cleanupGrubCfg()
                    if errors:
                        if not errorsEncountered:
                            errorsEncountered = True
                    else:
                        f.write('cleanupGrubCfg\n')
                else:
                    print YELLOW + '/etc/default/grub was not configured, since it was already configured.' + RESETCOLORS
                if 'disableServices' not in progressDict:
                    disableServiceList = dict(((x.split(':')[0].strip(), re.sub('\\s+', '', x.split(':')[1])) for x in upgradeResourceDict['slesServices'].split(',')))['SLES ' + osDistLevel].split('|')
                    errors = disableServices(disableServiceList)
                    if errors:
                        if not errorsEncountered:
                            errorsEncountered = True
                    else:
                        f.write('disableServices\n')
                else:
                    print YELLOW + 'Systemd services were not disabled, since they were already disabled.' + RESETCOLORS
        except IOError as err:
            debugLogger.error('Could not access ' + progressStatusFile + '.\n' + str(err))
            print RED + "Could not access '" + progressStatusFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        finally:
            f.close()

    if errorsEncountered:
        print RED + 'Errors were encountered while performing post upgrade tasks; check the debug log file for additional information before continuing.' + RESETCOLORS
    else:
        print GREEN + 'The post upgrade tasks have completed; continue with the next step in the upgrade process.' + RESETCOLORS


try:
    main()
except Exception as err:
    try:
        debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
        debugLogger.error('An unexpected error was encountered:\n' + traceback.format_exc())
        print RED + "An unexpected error was encountered; collect the application's log file and report the error back to the SAP HANA CoE DevOps team." + RESETCOLORS
        print RED + 'Error: ' + str(err) + RESETCOLORS
        exit(1)
    except NameError:
        print RED + "An unexpected error was encountered; collect the application's log file as well as the error message and report the error back to the SAP HANA CoE DevOps team." + RESETCOLORS
        print RED + 'Error: ' + str(err) + RESETCOLORS
        exit(1)