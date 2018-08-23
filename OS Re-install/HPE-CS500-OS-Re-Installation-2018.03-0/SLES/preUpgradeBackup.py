# Embedded file name: ./preUpgradeBackup.py
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
from modules.sapHANANodeSpec import getSapInitBackupList, getSAPUserLoginData, getHANAFstabData, getGlobalIniFiles, checkSAPHANA, getConrepFile
from modules.computeNode import getServerModel, getOSDistribution, getProcessorType, getHostname, getLocalTimeLink
from modules.upgradeMisc import checkDiskspace, createNetworkInformationFile, createBackup, stageAddOnRPMS, checkForMellanox, updateInstallCtrlFile, updateSGInstallCtrlFile, copyRepositoryTemplate, getOSUpgradeVersion
from modules.serviceGuardNodeSpec import checkForQSRPMPresence
RED = '\x1b[31m'
PURPLE = '\x1b[35m'
GREEN = '\x1b[32m'
BOLD = '\x1b[1m'
RESETCOLORS = '\x1b[0m'

def backupPreparation(upgradeWorkingDir, programParentDir, osDist, osDistLevel):
    logger = logging.getLogger('coeOSUpgradeLogger')
    resourceFile = 'upgradeResourceFile'
    ctrlFileImg = ''
    hanaSharedWithSID = False
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
        logger.error("Unable to access the application's resource file '" + resourceFile + "'.\n" + str(err))
        print RED + "Unable to access the application's resource file '" + resourceFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    try:
        shutil.copy2(resourceFile, upgradeWorkingDir)
    except OSError as err:
        print RED + "Unable to copy the upgrade resource file to '" + upgradeWorkingDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    serverModel = getServerModel()
    if serverModel not in upgradeResourceDict['supportedServerList']:
        logger.error('The ' + serverModel + ' is not supported. Supported models are: ' + upgradeResourceDict['supportedServerList'] + '.')
        print RED + 'The ' + serverModel + ' is not supported; exiting program execution.' + RESETCOLORS
        exit(1)
    if serverModel == 'ProLiant DL360 Gen9':
        command = 'rpm -q serviceguard-qs-*'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0 and 'package servicguard-qs-* is not installed' not in out:
            logger.error('Unable to determine if the server is a Serviceguard quorum server or Serviceguard NFS server:\n' + err + '\n' + out)
            print RED + 'Unable to determine if the server is a Serviceguard quorum server or Serviceguard NFS server; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        elif 'package servicguard-qs-* is not installed' in out:
            logger.error('The ' + serverModel + ' is not supported, since it is not a Serviceguard Quorum server.\n' + out)
            print RED + 'The ' + serverModel + ' is not supported, since it is not a Serviceguard Quorum server; exiting program execution.' + RESETCOLORS
            exit(1)
    try:
        if osDist == 'RHEL':
            supportedOSVersions = upgradeResourceDict['supportedRHELOSVersions'].split(',')
        else:
            supportedOSVersions = upgradeResourceDict['supportedSLESOSVersions'].split(',')
        osUpgradeVersion = getOSUpgradeVersion(supportedOSVersions)
    except KeyError as err:
        logger.error('The resource key ' + str(err) + " was not present in the application's resource file.")
        print RED + 'The resource key ' + str(err) + " was not present in the application's resource file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    if osUpgradeVersion == '11.4':
        if serverModel == 'ProLiant DL320e Gen8 v2' or not serverModel == 'ProLiant DL360 Gen9':
            logger.error('The ' + serverModel + ' is not supported for a SLES 11.4 wipe and replace upgrade.')
            print RED + 'The ' + serverModel + ' is not supported for a SLES 11.4 wipe and replace upgrade; exiting program execution.' + RESETCOLORS
            exit(1)
        if serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9':
            checkForQSRPMPresence(upgradeWorkingDir, osDist, osUpgradeVersion)
        if osDist == 'SLES':
            postUpgradeScripts = programParentDir + '/postUpgradeScriptFiles/SLES/' + osUpgradeVersion + '/*'
        else:
            postUpgradeScripts = programParentDir + '/postUpgradeScriptFiles/RHEL/' + osUpgradeVersion + '/*'
        command = 'cp -r ' + postUpgradeScripts + ' ' + upgradeWorkingDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to copy the post-upgrade script files from '" + postUpgradeScripts + "' to '" + upgradeWorkingDir + ':\n' + err + '\n' + out)
            print RED + 'Unable to copy the post-upgrade script files to the upgrade working directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        if not osUpgradeVersion == '11.4':
            getHostname(upgradeWorkingDir)
        getLocalTimeLink(upgradeWorkingDir)
        processor = ('DL580' in serverModel or serverModel == 'Superdome') and getProcessorType()
    try:
        if 'DL380p' in serverModel or 'DL360p' in serverModel:
            archiveBackup = re.split(',', upgradeResourceDict['osArchiveBackup']) + re.split(',', upgradeResourceDict['sglxArchiveBackup'])
            if osDist == 'SLES':
                restorationBackup = re.split(',', upgradeResourceDict['slesOSRestorationBackup']) + re.split(',', upgradeResourceDict['sglxRestorationBackup'])
            else:
                restorationBackup = re.split(',', upgradeResourceDict['rhelOSRestorationBackup']) + re.split(',', upgradeResourceDict['sglxRestorationBackup'])
        elif serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9':
            archiveBackup = re.split(',', upgradeResourceDict['osArchiveBackup']) + re.split(',', upgradeResourceDict['sgQsArchiveBackup'])
            if osDist == 'SLES':
                restorationBackup = re.split(',', upgradeResourceDict['slesOSRestorationBackup']) + re.split(',', upgradeResourceDict['sgQsRestorationBackup'])
            else:
                restorationBackup = re.split(',', upgradeResourceDict['rhelOSRestorationBackup']) + re.split(',', upgradeResourceDict['sgQsRestorationBackup'])
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
        logger.error('The resource key ' + str(err) + " was not present in the application's resource file.")
        print RED + 'The resource key ' + str(err) + " was not present in the application's resource file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    stageAddOnRPMS(programParentDir, upgradeWorkingDir, osDist, osUpgradeVersion)
    if not serverModel == 'Superdome':
        if not 'DL580' in serverModel:
            ctrlFileImg = updateSGInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel)
        if 'DL580' in serverModel or serverModel == 'Superdome':
            if re.match('.*/$', addOnFileArchive) == None:
                addOnFileArchiveDir = upgradeWorkingDir + '/addOnFileArchive'
                try:
                    os.mkdir(addOnFileArchiveDir)
                    shutil.copy2(addOnFileArchive, addOnFileArchiveDir)
                except (OSError, IOError) as err:
                    logger.error("Unable to copy the add on files archive '" + addOnFileArchive + "' to '" + addOnFileArchiveDir + "'.\n" + str(err))
                    print RED + "Unable to copy the add on files archive '" + addOnFileArchive + "' to '" + addOnFileArchiveDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)

            if serverModel == 'Superdome' and processor != 'ivybridge':
                logger.info('The system is a Superdome with the SID as part of /hana/shared in the mount point.')
                hanaSharedWithSID = True
            getHANAFstabData(upgradeWorkingDir, fstabHANAEntries)
            sidList, tenantUserDict = checkSAPHANA(upgradeWorkingDir, hanaSharedWithSID)
            if len(tenantUserDict) != 0:
                homeDirList = getSAPUserLoginData(upgradeWorkingDir, sidList, tenantUserDict=tenantUserDict)
            else:
                homeDirList = getSAPUserLoginData(upgradeWorkingDir, sidList)
            restorationBackup += homeDirList
            restorationBackup += getSapInitBackupList()
            if 'DL580' in serverModel:
                conrepDir = upgradeWorkingDir + '/conrepFile'
                getConrepFile(programParentDir, conrepDir)
            if (serverModel == 'Superdome' or 'DL580' in serverModel) and osDist == 'SLES':
                if serverModel == 'Superdome':
                    ctrlFileImg = updateInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion)
                else:
                    command = 'lsblk -l'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        logger.error('Unable to get the partition information for the root file system.\n' + err + '\n' + out)
                        print RED + 'Unable to get the partition information for the root file system; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)
                    if re.match('.*(360002ac0+.*)[_-]part.*/boot/efi.*$', out, re.DOTALL | re.MULTILINE):
                        ctrlFileImg = updateInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel='DL580', cs500ScaleOut='cs500ScaleOut')
                    else:
                        ctrlFileImg = updateInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel='DL580')
        if 'DL580' in serverModel or serverModel == 'Superdome':
            backupItems = ' '.join(restorationBackup) + ' ' + ' '.join(archiveBackup) + ' ' + ' '.join(sapRestorationBackup)
            backupItems = [restorationBackup, sapRestorationBackup, archiveBackup]
        else:
            backupItems = ' '.join(restorationBackup) + ' ' + ' '.join(archiveBackup)
            backupItems = [restorationBackup, archiveBackup]
        checkDiskspace(backupItems)
        createNetworkInformationFile(upgradeWorkingDir, osDist)
        if 'DL580' in serverModel and processor != 'ivybridge':
            checkForMellanox(programParentDir, upgradeWorkingDir, osDist, osUpgradeVersion)
        return ('DL580' in serverModel or serverModel == 'Superdome') and ([restorationBackup, archiveBackup, sapRestorationBackup], ctrlFileImg)
    else:
        return ([restorationBackup, archiveBackup], ctrlFileImg)
        return


def main():
    programVersion = '2018.03-0'
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
    if osDist == 'SLES':
        if not osDistLevel == '11.4':
            print osDistLevel == '11.3' or RED + "The server's OS distribution level (" + osDistLevel + ') is not supported for a wipe and replace upgrade; exiting program execution.\n' + out + RESETCOLORS
            exit(1)
    elif not osDistLevel == '6.7':
        print osDistLevel == '6.6' or RED + "The server's OS distribution level (" + osDistLevel + ') is not supported for a wipe and replace upgrade; exiting program execution.\n' + out + RESETCOLORS
        exit(1)
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    upgradeWorkingDir = '/tmp/CoE_SAP_HANA_' + osDist + '_Upgrade_Working_Dir_' + dateTimestamp
    try:
        if os.path.exists(upgradeWorkingDir):
            shutil.rmtree(upgradeWorkingDir)
            time.sleep(0.1)
            os.mkdir(upgradeWorkingDir)
        else:
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

    logFile = logDir + '/' + osDist + '_Pre-Upgrade.log'
    handler = logging.FileHandler(logFile)
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("The program's version is: " + programVersion + '.')
    backupList, ctrlFileImg = backupPreparation(upgradeWorkingDir, programParentDir, osDist, osDistLevel)
    backupISO, archiveImage = createBackup(backupList, upgradeWorkingDir, osDist)
    print GREEN + 'The pre-upgrade backup successfully completed.\n\nSave the following files and their md5sum files if applicable to another system:\n\t- ' + backupISO + '\n\t- ' + archiveImage + '\n\t- ' + ctrlFileImg + BOLD + PURPLE + '\n\n**** Finally, make sure to copy the files in binary format to avoid corrupting the files; you should also double check the files and their contents before continuing with the upgrade. ****' + RESETCOLORS


try:
    main()
except Exception as err:
    try:
        logger = logging.getLogger('coeOSUpgradeLogger')
        logger.error('An unexpected error was encountered:\n' + traceback.format_exc())
        print RED + "An unexpected error was encountered; collect the application's log file and report the error back to the SAP HANA CoE DevOps team." + RESETCOLORS
        print RED + 'Error: ' + str(err) + RESETCOLORS
        exit(1)
    except NameError:
        print RED + "An unexpected error was encountered; collect the application's log file as well as the error message and report the error back to the SAP HANA CoE DevOps team." + RESETCOLORS
        print RED + 'Error: ' + str(err) + RESETCOLORS
        exit(1)