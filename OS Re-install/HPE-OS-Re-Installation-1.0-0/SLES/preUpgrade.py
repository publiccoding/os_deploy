# Embedded file name: ./preUpgrade.py
import re
import os
import sys
import shutil
import datetime
import logging
import time
import optparse
import subprocess
import traceback
from modules.sapHANANodeSpec import getSapInitBackupList, getSAPUserLoginData, getHANAFstabData, getGlobalIniFiles, checkSAPHANA, getConrepFile, backupLimitsFile
from modules.computeNode import getServerModel, getOSDistribution, getProcessorType, getHostname, getLocalTimeLink
from modules.preUpgradeTasks import checkDiskSpace, createNetworkInformationFile, createBackup, stageAddOnRPMS, copyRepositoryTemplate, checkForMellanox, updateInstallCtrlFile, updateRHELInstallCtrlFile, updateSGInstallCtrlFile, getOSUpgradeVersion
RED = '\x1b[31m'
PURPLE = '\x1b[35m'
GREEN = '\x1b[32m'
BOLD = '\x1b[1m'
RESETCOLORS = '\x1b[0m'

def backupPreparation(upgradeWorkingDir, programParentDir, osDistVersion):
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    resourceFile = 'upgradeResourceFile'
    ctrlFileImg = ''
    osDist = osDistVersion[:4]
    mellanoxPresent = False
    upgradeResourceDict = {}
    try:
        with open(resourceFile) as f:
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
        print RED + "Unable to access the application's resource file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    try:
        shutil.copy2(resourceFile, upgradeWorkingDir)
    except OSError as err:
        debugLogger.error("Unable to copy the upgrade resource file to '" + upgradeWorkingDir + "'.\n" + str(err))
        print RED + 'Unable to copy the upgrade resource file to the upgrade working directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    if osDist == 'SLES':
        initialOSDict = dict.fromkeys((x for x in upgradeResourceDict['initialSLESOSVersions'].split(',')))
        debugLogger.info('The initial OS version dictionary is: ' + str(initialOSDict))
        if osDistVersion not in initialOSDict:
            debugLogger.error("The server's OS distribution (" + osDistVersion + ') is not supported for a wipe and replace upgrade.')
            print RED + "The server's OS distribution is not supported for a wipe and replace upgrade; exiting program execution." + RESETCOLORS
            exit(1)
    else:
        initialOSDict = dict.fromkeys((x for x in upgradeResourceDict['initialRHELOSVersions'].split(',')))
        debugLogger.info('The initial OS version dictionary is: ' + str(initialOSDict))
        if osDistVersion not in initialOSDict:
            debugLogger.error("The server's OS version (" + osDistVersion + ') is not supported for a wipe and replace upgrade.')
            print RED + "The server's OS version is not supported for a wipe and replace upgrade; exiting program execution." + RESETCOLORS
            exit(1)
    serverModel = getServerModel()
    if 'DL580' in serverModel or serverModel == 'Superdome':
        processor = getProcessorType()
    if osDist == 'RHEL' and serverModel == 'Superdome' and processor == 'ivybridge':
        debugLogger.error('The ' + serverModel + ' is not supported, since it is a CS900 Ivy Bridge configuration.')
        print RED + 'The server is not supported; exiting program execution.' + RESETCOLORS
        exit(1)
    if osDist == 'SLES':
        supportedServerList = upgradeResourceDict['slesSupportedServerList']
    else:
        supportedServerList = upgradeResourceDict['rhelSupportedServerList']
    if serverModel not in supportedServerList:
        debugLogger.error('The ' + serverModel + ' is not supported. Supported models are: ' + supportedServerList + '.')
        print RED + 'The server is not supported; exiting program execution.' + RESETCOLORS
        exit(1)
    if serverModel == 'ProLiant DL360 Gen9':
        command = 'rpm -q serviceguard-qs-*'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0 and 'package servicguard-qs-* is not installed' not in out:
            debugLogger.error('Unable to determine if the server is a Serviceguard quorum server or Serviceguard NFS server:\n' + err + '\n' + out)
            print RED + 'Unable to determine if the server is a Serviceguard quorum server or Serviceguard NFS server; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        elif 'package servicguard-qs-* is not installed' in out:
            debugLogger.error('The ' + serverModel + ' is not supported, since it is not a Serviceguard Quorum server.\n' + out)
            print RED + 'The ' + serverModel + ' is not supported, since it is not a Serviceguard Quorum server; exiting program execution.' + RESETCOLORS
            exit(1)
    if serverModel == 'Superdome':
        systemType = 'CS900'
    elif serverModel == 'ProLiant DL360 Gen9' or serverModel == 'ProLiant DL320e Gen8 v2':
        systemType = 'SGQS'
    elif serverModel == 'ProLiant DL380p Gen8' or serverModel == 'ProLiant DL360p Gen8':
        systemType = 'SGLX'
    else:
        systemType = 'CS500'
    try:
        if osDist == 'RHEL':
            supportedOSVersions = upgradeResourceDict['supportedRHELOSVersions'].split(',')
        else:
            supportedOSVersions = upgradeResourceDict['supportedSLESOSVersions'].split(',')
    except KeyError as err:
        debugLogger.error('The resource key ' + str(err) + " was not present in the application's resource file.")
        print RED + 'The resource ' + str(err) + " was not present in the application's resource file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    debugLogger.info('The supported OS Versions to upgrade to are: ' + str(supportedOSVersions))
    if len(supportedOSVersions) > 1:
        osUpgradeVersion = getOSUpgradeVersion(supportedOSVersions, serverModel, upgradeResourceDict.copy())
    else:
        osUpgradeVersion = supportedOSVersions[0][5:]
    debugLogger.info('The server is being upgraded to ' + osUpgradeVersion + '.')
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
    if not osUpgradeVersion == '11.4':
        getHostname(upgradeWorkingDir)
    getLocalTimeLink(upgradeWorkingDir)
    try:
        if serverModel == 'ProLiant DL380p Gen8' or serverModel == 'ProLiant DL360p Gen8':
            archiveBackup = re.split(',', upgradeResourceDict['osArchiveBackup']) + re.split(',', upgradeResourceDict['sglxArchiveBackup'])
            if osDist == 'SLES':
                restorationBackup = re.split(',', upgradeResourceDict['slesOSRestorationBackup']) + re.split(',', upgradeResourceDict['sglxRestorationBackup'])
            else:
                restorationBackup = re.split(',', upgradeResourceDict['rhelOSRestorationBackup']) + re.split(',', upgradeResourceDict['sglxRestorationBackup'])
        elif serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9':
            archiveBackup = re.split(',', upgradeResourceDict['osArchiveBackup']) + re.split(',', upgradeResourceDict['sgQsArchiveBackup'])
            restorationBackup = re.split(',', upgradeResourceDict['slesOSRestorationBackup']) + re.split(',', upgradeResourceDict['sgQsRestorationBackup'])
        else:
            archiveBackup = re.split(',', upgradeResourceDict['osArchiveBackup'])
            sapRestorationBackup = re.split(',', upgradeResourceDict['sapRestorationBackup'])
            if osDist == 'SLES':
                restorationBackup = re.split(',', upgradeResourceDict['slesOSRestorationBackup'])
                if 'DL580' in serverModel:
                    if processor == 'ivybridge':
                        addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['ivyBridgeSLESAddOnFileArchive']
                    else:
                        addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['haswellSLESAddOnFileArchive']
                else:
                    addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['cs900SLESAddOnFileArchive']
            else:
                restorationBackup = re.split(',', upgradeResourceDict['rhelOSRestorationBackup'])
                if 'DL580' in serverModel:
                    if processor == 'ivybridge':
                        addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['ivyBridgeRHELAddOnFileArchive']
                    else:
                        addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['haswellRHELAddOnFileArchive']
                else:
                    addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['cs900RHELAddOnFileArchive']
            fstabHANAEntries = upgradeResourceDict['fstabHANAEntries'].split(',')
    except KeyError as err:
        debugLogger.error('The resource key ' + str(err) + " was not present in the application's resource file.")
        print RED + 'The resource ' + str(err) + " was not present in the application's resource file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    stageAddOnRPMS(programParentDir, upgradeWorkingDir, osDist, osUpgradeVersion, systemType)
    if osDist == 'RHEL':
        copyRepositoryTemplate(programParentDir, upgradeWorkingDir)
    if not serverModel == 'Superdome':
        if not 'DL580' in serverModel and osDist == 'SLES':
            ctrlFileImg = updateSGInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel)
        elif not serverModel == 'Superdome':
            sgNFSCtrlFileImg = not 'DL580' in serverModel and osDist == 'RHEL' and programParentDir + '/installCtrlFiles/sgNFS_ks.img'
            installCtrlFileDir = upgradeWorkingDir + '/installCtrlFile'
            ctrlFileImg = installCtrlFileDir + '/sgNFS_ks.img'
            try:
                os.mkdir(installCtrlFileDir)
                shutil.copy2(sgNFSCtrlFileImg, ctrlFileImg)
            except OSError as err:
                debugLogger.error("Unable to create install control file directory '" + installCtrlFileDir + "'.\n" + str(err))
                print RED + 'Unable to create the install control file directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            except IOError as err:
                debugLogger.error('Unable to copy the NFS Serviceguard control image file (' + sgNFSCtrlFileImg + ") to '" + ctrlFileImg + "'.\n" + str(err))
                print RED + 'Unable to copy the NFS Serviceguard control image file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

        if 'DL580' in serverModel or serverModel == 'Superdome':
            if re.match('.*/$', addOnFileArchive) == None:
                addOnFileArchiveDir = upgradeWorkingDir + '/addOnFileArchive'
                try:
                    os.mkdir(addOnFileArchiveDir)
                    shutil.copy2(addOnFileArchive, addOnFileArchiveDir)
                except (OSError, IOError) as err:
                    debugLogger.error("Unable to copy the add on files archive '" + addOnFileArchive + "' to '" + addOnFileArchiveDir + "'.\n" + str(err))
                    print RED + 'Unable to copy the add on files archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

            getHANAFstabData(upgradeWorkingDir, fstabHANAEntries)
            backupLimitsFile(upgradeWorkingDir)
            if osDist == 'RHEL':
                supportedSAPHANARevisionList = dict(((x.split(':')[0].strip(), re.sub('\\s+', '', x.split(':')[1])) for x in upgradeResourceDict['rhelSupportedSAPHANARevision'].split(',')))['RHEL ' + osUpgradeVersion].split('|')
            else:
                supportedSAPHANARevisionList = dict(((x.split(':')[0].strip(), re.sub('\\s+', '', x.split(':')[1])) for x in upgradeResourceDict['slesSupportedSAPHANARevision'].split(',')))['SLES ' + osUpgradeVersion].split('|')
            debugLogger.info('The supported SAP HANA revision list was: ' + str(supportedSAPHANARevisionList))
            sidList, tenantUserDict = checkSAPHANA(upgradeWorkingDir, serverModel, supportedSAPHANARevisionList)
            if len(tenantUserDict) != 0:
                homeDirList = getSAPUserLoginData(upgradeWorkingDir, sidList, tenantUserDict=tenantUserDict)
            else:
                homeDirList = getSAPUserLoginData(upgradeWorkingDir, sidList)
            restorationBackup += homeDirList
            restorationBackup += getSapInitBackupList()
            if 'DL580' in serverModel:
                conrepDir = upgradeWorkingDir + '/conrepFile'
                getConrepFile(programParentDir, conrepDir)
            if 'DL580' in serverModel and processor != 'ivybridge':
                mellanoxPresent = checkForMellanox(programParentDir, upgradeWorkingDir, osDist, osUpgradeVersion)
            if osDist == 'SLES':
                if serverModel == 'Superdome':
                    ctrlFileImg = updateInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion)
                else:
                    command = 'lsblk -l'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        debugLogger.error('Unable to get the partition information for the root file system.\n' + err + '\n' + out)
                        print RED + 'Unable to get the partition information for the root file system; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)
                    if re.match('.*(360002ac0+.*)[_-]part.*/boot/efi.*$', out, re.DOTALL | re.MULTILINE):
                        ctrlFileImg = updateInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, mellanoxPresent=mellanoxPresent, serverModel='DL580', bootFromSAN='bootFromSAN')
                    else:
                        ctrlFileImg = updateInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, mellanoxPresent=mellanoxPresent, serverModel='DL580')
            elif serverModel == 'Superdome':
                ctrlFileImg = updateRHELInstallCtrlFile(programParentDir, upgradeWorkingDir)
            else:
                cs500CtrlFileImg = programParentDir + '/installCtrlFiles/cs500_ks.img'
                installCtrlFileDir = upgradeWorkingDir + '/installCtrlFile'
                ctrlFileImg = installCtrlFileDir + '/cs500_ks.img'
                try:
                    os.mkdir(installCtrlFileDir)
                    shutil.copy2(cs500CtrlFileImg, ctrlFileImg)
                except OSError as err:
                    debugLogger.error("Unable to create install control file directory '" + installCtrlFileDir + "'.\n" + str(err))
                    print RED + 'Unable to create the install control file directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)
                except IOError as err:
                    debugLogger.error('Unable to copy the CS500 control image file (' + cs500CtrlFileImg + ") to '" + ctrlFileImg + "'.\n" + str(err))
                    print RED + 'Unable to copy the CS500 control image file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

            if osDist == 'RHEL':
                if os.path.isfile('/etc/sudoers'):
                    command = "sed -i 's/\\s*Defaults requiretty/#Defaults requiretty/g' /etc/sudoers"
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        debugLogger.error('There was a problem updating /etc/sudoers.\n' + err + '\n' + out)
                        debugLogger.info('The command used to update /etc/sudoers was: ' + command)
                        print RED + 'There was a problem updating /etc/sudoers; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)
                if serverModel != 'Superdome':
                    print GREEN + "Changing the server's boot mode from Legacy to UEFI." + RESETCOLORS
                    command = 'conrep -l -f ' + programParentDir + '/conrepFile/conrepBootMode.dat'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        debugLogger.error("An error was encountered while updating the server's BIOS from Legacy mode to UEFI mode.\n" + err + '\n' + out)
                        debugLogger.info("The command used to update the server's BIOS from Legacy mode to UEFI mode was: " + command)
                        print RED + "There was a problem updating the server's BIOS from Legacy mode to UEFI mode; fix the problem and try again; exiting program execution." + RESETCOLORS
                        exit(1)
        if 'DL580' in serverModel or serverModel == 'Superdome':
            backupItems = [restorationBackup, sapRestorationBackup, archiveBackup]
        else:
            backupItems = [restorationBackup, archiveBackup]
        checkDiskSpace(backupItems, upgradeWorkingDir)
        createNetworkInformationFile(upgradeWorkingDir, osDist)
        return ('DL580' in serverModel or serverModel == 'Superdome') and ([restorationBackup, archiveBackup, sapRestorationBackup], ctrlFileImg)
    else:
        return ([restorationBackup, archiveBackup], ctrlFileImg)
        return


def main():
    programVersion = '1.0-0'
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS
        exit(1)
    parser = optparse.OptionParser(version=programVersion)
    options, args = parser.parse_args()
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
    backupList, ctrlFileImg = backupPreparation(upgradeWorkingDir, programParentDir, osDistVersion)
    backupISO, archiveImage = createBackup(backupList, upgradeWorkingDir, osDist)
    print GREEN + 'The pre-upgrade backup successfully completed.\n\nSave the following files and their md5sum files if applicable to another system:\n\t- ' + backupISO + '\n\t- ' + archiveImage + '\n\t- ' + ctrlFileImg + BOLD + PURPLE + '\n\n**** Finally, make sure to copy the files in binary format to avoid corrupting the files; you should also double check the files and their contents before continuing with the upgrade. ****' + RESETCOLORS


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