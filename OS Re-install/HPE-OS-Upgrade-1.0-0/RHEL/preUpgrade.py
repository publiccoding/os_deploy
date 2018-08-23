# Embedded file name: ./preUpgrade.py
import re
import os
import sys
import glob
import shutil
import datetime
import logging
import time
import optparse
import subprocess
import traceback
from modules.sapHANANodeSpec import checkSAPHANA, getConrepFile, backupLimitsFile
from modules.computeNode import getServerModel, getOSDistribution, getProcessorType
from modules.preUpgradeTasks import checkDiskspace, createNetworkInformationFile, confirmBackupDataList, createBackup, getOriginalRPMList, removeRear, disableMultiversionSupport, updateUpgradeCtrlFile, checkClusterStatus, removeServiceguardExtras, stageServiceguardRPMS, checkForMellanox, prepareFstab, getOSUpgradeVersion
RED = '\x1b[31m'
PURPLE = '\x1b[35m'
GREEN = '\x1b[32m'
YELLOW = '\x1b[33m'
BOLD = '\x1b[1m'
RESETCOLORS = '\x1b[0m'

def backupPreparation(upgradeWorkingDir, programParentDir, osDistVersion):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    resourceFile = 'upgradeResourceFile'
    ctrlFileImg = ''
    hanaSharedWithSID = False
    osDist = osDistVersion[:4]
    dl360NFSNode = True
    mellanoxPresent = False
    bootFromSAN = False
    if osDist == 'SLES':
        previousUpgradeDir = '/var/log/CoESapHANA_SLES_UpgradeLogDir'
    else:
        previousUpgradeDir = '/var/log/CoESapHANA_RHEL_UpgradeLogDir'
    upgradeResourceDict = {}
    try:
        with open(resourceFile, 'r') as f:
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
        debugLogger.error("Unable to access the application's resource file '" + resourceFile + "'.\n" + str(err))
        print RED + "Unable to access the application's resource file '" + resourceFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    try:
        shutil.copy2(resourceFile, upgradeWorkingDir)
    except OSError as err:
        debugLogger.error("Unable to copy the upgrade resource file to '" + upgradeWorkingDir + "'.\n" + str(err))
        print RED + "Unable to copy the upgrade resource file to '" + upgradeWorkingDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    if osDist == 'SLES':
        initialOSDict = dict.fromkeys((x for x in upgradeResourceDict['initialSLESOSVersions'].split(',')))
    else:
        initialOSDict = dict.fromkeys((x for x in upgradeResourceDict['initialRHELOSVersions'].split(',')))
    debugLogger.info('The initial OS version dictionary is: ' + str(initialOSDict))
    if osDistVersion not in initialOSDict:
        debugLogger.error("The server's OS distribution (" + osDistVersion + ') is not supported for an upgrade.')
        print RED + "The server's OS distribution (" + osDistVersion + ') is not supported for an upgrade; exiting program execution.' + RESETCOLORS
        exit(1)
    serverModel = getServerModel()
    if 'DL580' in serverModel:
        serverProcessor = getProcessorType()
    if osDist == 'SLES':
        if serverModel not in upgradeResourceDict['slesSupportedServerList']:
            debugLogger.error('The ' + serverModel + ' is not supported. Supported models are: ' + upgradeResourceDict['supportedServerList'] + '.')
            print RED + 'The ' + serverModel + ' is not supported; exiting program execution.' + RESETCOLORS
            exit(1)
    elif serverModel not in upgradeResourceDict['rhelSupportedServerList']:
        debugLogger.error('The ' + serverModel + ' is not supported. Supported models are: ' + upgradeResourceDict['supportedServerList'] + '.')
        print RED + 'The ' + serverModel + ' is not supported; exiting program execution.' + RESETCOLORS
        exit(1)
    if serverModel == 'ProLiant DL360 Gen9':
        command = 'rpm -q serviceguard-A.*'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0 and 'package serviceguard-A.* is not installed' not in out:
            debugLogger.error('Unable to determine if the server is a Serviceguard quorum server or Serviceguard NFS server:\n' + err + '\n' + out)
            print RED + 'Unable to determine if the server is a Serviceguard quorum server or Serviceguard NFS server; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        elif 'package servicguard-A.* is not installed' in out:
            debugLogger.error('The ' + serverModel + ' is not supported, since it is not a NFS Serviceguard server.\n' + out)
            print RED + 'The ' + serverModel + ' is not supported, since it is not a NFS Serviceguard server; exiting program execution.' + RESETCOLORS
            exit(1)
    try:
        if osDist == 'SLES':
            supportedOSVersions = dict((re.sub('\\s*:\\s*', ':', x).split(':') for x in upgradeResourceDict['supportedSLESOSVersions'].split(',')))
        else:
            supportedOSVersions = dict((re.sub('\\s*:\\s*', ':', x).split(':') for x in upgradeResourceDict['supportedRHELOSVersions'].split(',')))
    except KeyError as err:
        debugLogger.error('The resource key ' + str(err) + " was not present in the application's resource file.")
        print RED + 'The resource key ' + str(err) + " was not present in the application's resource file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    osUpgradeVersion = supportedOSVersions[osDistVersion][5:]
    debugLogger.info('The server is being upgraded to ' + osUpgradeVersion + '.')
    if osDist == 'RHEL':
        logDir = '/var/log/CoESapHANA_' + osDist + '_UpgradeLogDir'
        if not os.path.isdir(logDir):
            try:
                os.mkdir(logDir)
            except OSError as err:
                debugLogger.error("Unable to create the upgrade log directory '" + logDir + "'.\n" + str(err))
                print RED + 'Unable to create the upgrade log directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

        else:
            fileList = glob.glob(logDir + '/*')
            for file in fileList:
                try:
                    os.remove(logDir + '/' + file)
                except OSError as err:
                    debugLogger.error("Unable to remove the file '" + logDir + '/' + file + "'.\n" + str(err))
                    print RED + "Unable to remove the file '" + logDir + '/' + file + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)

                time.sleep(1.0)

        try:
            with open(logDir + '/upgradeVersionReference.log', 'w') as f:
                f.write(osUpgradeVersion)
        except OSError as err:
            debugLogger.error('Could not access ' + logDir + '/upgradeVersionReference.log to write out the OS upgrade version.\n' + str(err))
            print RED + 'Could not access ' + logDir + '/upgradeVersionReference.log to write out the OS upgrade version; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

    if osDist == 'SLES':
        osVersion = osDist + osUpgradeVersion[:2]
    else:
        osVersion = osDist + osUpgradeVersion[:1]
    if os.path.isdir(previousUpgradeDir):
        try:
            shutil.rmtree(previousUpgradeDir)
        except OSError as err:
            debugLogger.error("Problems were encountered while removing a previous upgrade directory '" + previousUpgradeDir + "'.\n" + str(err))
            print RED + 'Problems were encountered while removing a previous upgrade directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

    if 'DL580' in serverModel or serverModel == 'Superdome':
        if osDist == 'RHEL':
            supportedSAPHANARevisionList = dict(((x.split(':')[0].strip(), re.sub('\\s+', '', x.split(':')[1])) for x in upgradeResourceDict['rhelSupportedSAPHANARevision'].split(',')))['RHEL ' + osUpgradeVersion].split('|')
        else:
            supportedSAPHANARevisionList = dict(((x.split(':')[0].strip(), re.sub('\\s+', '', x.split(':')[1])) for x in upgradeResourceDict['slesSupportedSAPHANARevision'].split(',')))['SLES ' + osUpgradeVersion].split('|')
        debugLogger.info('The supported SAP HANA revision list was: ' + str(supportedSAPHANARevisionList))
        checkSAPHANA(upgradeWorkingDir, serverModel, supportedSAPHANARevisionList)
    if serverModel == 'ProLiant DL360 Gen9' and dl360NFSNode or serverModel == 'ProLiant DL380p Gen8' or serverModel == 'ProLiant DL360p Gen8':
        checkClusterStatus()
        removeServiceguardExtras(upgradeResourceDict['extraServiceguardPackages'])
        stageServiceguardRPMS(programParentDir, upgradeWorkingDir, osVersion, upgradeResourceDict[osVersion.lower() + 'NFSServiceguardRPMS'])
    if serverModel == 'ProLiant DL360 Gen9' and not dl360NFSNode or serverModel == 'ProLiant DL320e Gen8 v2':
        stageServiceguardRPMS(programParentDir, upgradeWorkingDir, osVersion, upgradeResourceDict[osVersion.lower() + 'QSServiceguardRPMS'])
    if osDist == 'SLES':
        postUpgradeScripts = programParentDir + '/postUpgradeScriptFiles/SLES/' + osUpgradeVersion + '/*'
    else:
        postUpgradeScripts = programParentDir + '/postUpgradeScriptFiles/RHEL/' + osUpgradeVersion + '/*'
    command = 'cp -r ' + postUpgradeScripts + ' ' + upgradeWorkingDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to copy the post-upgrade script files from '" + postUpgradeScripts + "' to '" + upgradeWorkingDir + ':\n' + err + '\n' + out)
        print RED + 'Unable to copy the post-upgrade script files to the upgrade working directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if osDist == 'RHEL':
        command = 'cp ' + programParentDir + '/rhelRPMReferenceList/* ' + upgradeWorkingDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to copy the RPM reference file from '" + programParentDir + "/rhelRPMReferenceList' to '" + upgradeWorkingDir + ':\n' + err + '\n' + out)
            print RED + 'Unable to copy the the RPM reference file to the upgrade working directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        filesystemRPMDir = '/tmp/rhelFilesystemRPM'
        if not os.path.isdir(filesystemRPMDir):
            try:
                os.mkdir(filesystemRPMDir)
            except OSError as err:
                print RED + "Unable to create the directory '" + filesystemRPMDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

        else:
            filesystemRPMS = glob.glob(filesystemRPMDir + '/filesystem*.rpm')
            for file in filesystemRPMS:
                try:
                    os.remove(filesystemRPMDir + '/' + file)
                except OSError as err:
                    print RED + "Unable to remove the file '" + filesystemRPMDir + '/' + file + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)

                time.sleep(1.0)

        command = 'cp ' + programParentDir + '/rhelFilesystemRPM/filesystem*.rpm ' + filesystemRPMDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to copy the filesystem RPM from '" + programParentDir + "/rhelFilesystemRPM' to '" + filesystemRPMDir + ':\n' + err + '\n' + out)
            print RED + "Unable to copy the the filesystem RPM to '" + filesystemRPMDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
    if 'DL580' in serverModel:
        conrepDir = upgradeWorkingDir + '/conrepFile'
        getConrepFile(programParentDir, conrepDir)
    if osDist == 'SLES':
        if 'DL580' in serverModel or serverModel == 'ProLiant DL360 Gen9' and dl360NFSNode:
            command = 'lsblk -l'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('Unable to get the partition information for the root file system.\n' + err + '\n' + out)
                print RED + 'Unable to get the partition information for the root file system; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            if re.match('.*(360002ac0+.*)[_-]part.*/boot/efi.*$', out, re.DOTALL | re.MULTILINE):
                debugLogger.info('The ' + serverModel + "'s boot from SAN partition information was: " + out.strip() + '.')
                bootFromSAN = True
        if 'DL580' in serverModel and serverProcessor == 'broadwell' or serverModel == 'Superdome':
            prepareFstab(upgradeWorkingDir)
        if 'DL580' in serverModel or serverModel == 'Superdome':
            backupLimitsFile(upgradeWorkingDir)
    if 'DL580' in serverModel and serverProcessor != 'ivybridge':
        mellanoxPresent = checkForMellanox(programParentDir, upgradeWorkingDir, osDist, osUpgradeVersion)
    try:
        if serverModel == 'ProLiant DL360 Gen9' and dl360NFSNode or serverModel == 'ProLiant DL380p Gen8' or serverModel == 'ProLiant DL360p Gen8':
            archiveBackup = re.split(',', upgradeResourceDict['osArchiveBackup']) + re.split(',', upgradeResourceDict['sglxArchiveBackup'])
        else:
            archiveBackup = re.split(',', upgradeResourceDict['osArchiveBackup']) + re.split(',', upgradeResourceDict['sapArchiveBackup'])
    except KeyError as err:
        debugLogger.error('The resource key ' + str(err) + " was not present in the application's resource file.")
        print RED + 'The resource key ' + str(err) + " was not present in the application's resource file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    debugLogger.info('The archive backup list is: ' + str(archiveBackup) + '.')
    getOriginalRPMList(upgradeWorkingDir)
    archiveBackup, fileRemoved = confirmBackupDataList(archiveBackup)
    if fileRemoved:
        print YELLOW + 'File(s) were removed from the backup, since they were not present; review the log file for additional information.' + RESETCOLORS
    checkDiskspace(archiveBackup)
    if osDist == 'SLES':
        removeRear()
        disableMultiversionSupport()
        if serverModel == 'Superdome' or serverModel == 'ProLiant DL380p Gen8' or serverModel == 'ProLiant DL360p Gen8':
            ctrlFileImg = updateUpgradeCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel)
        elif bootFromSAN:
            ctrlFileImg = updateUpgradeCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel, bootFromSAN='bootFromSAN', mellanoxPresent=mellanoxPresent)
        else:
            ctrlFileImg = updateUpgradeCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel, mellanoxPresent=mellanoxPresent)
    createNetworkInformationFile(upgradeWorkingDir, osDist)
    return (archiveBackup, ctrlFileImg)


def main():
    programName = os.path.basename(sys.argv[0]).split('.')[0]
    programVersion = '1.0-0'
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS
        exit(1)
    usage = 'usage: %prog [-h] [-v]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-v', action='store_true', default=False, help="This option is used to display the application's version.")
    options, args = parser.parse_args()
    if options.v:
        print programName + ' ' + programVersion
        exit(0)
    try:
        programParentDir = ''
        cwd = os.getcwd()
        programDir = os.path.dirname(os.path.realpath(__file__))
        programParentDir = '/'.join(programDir.split('/')[:-1])
        if cwd != programParentDir:
            os.chdir(programParentDir)
    except OSError as err:
        print RED + "Unable to change into the programs parent directory '" + programParentDir + "'; fix the problem and try again; exiting program execution.\n" + str(err) + RESETCOLORS
        exit(1)

    osDist, osDistLevel = getOSDistribution()
    osDistVersion = osDist + ' ' + osDistLevel
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%S%b%Y')
    upgradeWorkingDir = '/tmp/CoE_SAP_HANA_' + osDist + '_Upgrade_Working_Dir_' + dateTimestamp
    try:
        os.mkdir(upgradeWorkingDir)
    except OSError as err:
        print RED + "Unable to create '" + upgradeWorkingDir + "' in preparation for the upgrade; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    logDir = upgradeWorkingDir + '/log'
    try:
        os.mkdir(logDir)
    except OSError as err:
        print RED + "Unable to create the pre-upgrade log directory '" + logDir + "'; fix the problem and try again; exiting program execution.\n" + str(err) + RESETCOLORS
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
    debugLogger.info("The server's OS distribution Version is: " + osDistVersion + '.')
    archiveBackup, ctrlFileImg = backupPreparation(upgradeWorkingDir, programParentDir, osDistVersion)
    backupISO, archiveImage = createBackup(archiveBackup, upgradeWorkingDir, osDist)
    if osDist == 'SLES':
        print GREEN + 'The pre-upgrade backup successfully completed.\n\nSave the following files and their md5sum files if applicable to another system:\n\t- ' + backupISO + '\n\t- ' + archiveImage + '\n\t- ' + ctrlFileImg + BOLD + PURPLE + '\n\n**** Finally, make sure to copy the files in binary format to avoid corrupting the files; you should also double check the files and their contents before continuing with the upgrade. ****' + RESETCOLORS
    else:
        print GREEN + 'The pre-upgrade backup successfully completed.\n\nSave the following files and their md5sum files if applicable to another system:\n\t- ' + backupISO + '\n\t- ' + archiveImage + BOLD + PURPLE + '\n\n**** Finally, make sure to copy the files in binary format to avoid corrupting the files; you should also double check the files and their contents before continuing with the upgrade. ****' + RESETCOLORS


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