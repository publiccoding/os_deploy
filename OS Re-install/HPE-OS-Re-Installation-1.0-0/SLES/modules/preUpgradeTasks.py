# Embedded file name: ./preUpgradeTasks.py
import math
import subprocess
import re
import os
import datetime
import time
import logging
import shutil
import glob
from ast import literal_eval
RED = '\x1b[31m'
GREEN = '\x1b[32m'
YELLOW = '\x1b[33m'
RESETCOLORS = '\x1b[0m'

def checkDiskSpace(backupItemsList, upgradeWorkingDir):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking to ensure that there is enough disk space for the backup and that the backup ISO image data does not exceed 3GB.')
    print GREEN + 'Checking to ensure that there is enough disk space for the backup and that the backup ISO image data does not exceed 3GB.' + RESETCOLORS
    command = 'df /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    if result.returncode != 0:
        debugLogger.error("Unable to get the root file system's usage information.\n" + err + '\n' + out)
        debugLogger.info("The command used to get the root file system's usage information was: " + command)
        print RED + "Unable to get the root file system's usage information; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    try:
        tmpVar = re.match('(.*\\s+){3}([0-9]+)\\s+', out).group(2)
    except AttributeError as err:
        debugLogger.error("There was a match error when getting the root file system size and trying to match against '" + out + "'.\n" + str(err))
        print RED + 'There was an error when getting the root file system size; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    availableDiskSpace = round(float(tmpVar) / 1048576, 6)
    debugLogger.info('The available disk space on the root filesystem is: ' + str(availableDiskSpace) + 'GB.')
    if len(backupItemsList) == 3:
        backupItems = ' '.join(backupItemsList[2])
        restorationItems = ' '.join(backupItemsList[0]) + ' ' + ' '.join(backupItemsList[1])
    else:
        backupItems = ' ' + ' '.join(backupItemsList[1])
        restorationItems = ' '.join(backupItemsList[0])
    backupList = [backupItems, restorationItems]
    totalArchiveSize = 0
    for items in backupList:
        command = 'tar -czf - ' + items + '|wc -c'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        out = out.strip()
        if re.search('Exiting with failure status due to previous errors', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None or result.returncode != 0:
            debugLogger.error('Unable to get the size of the backup archive.\n' + err + '\n' + out)
            debugLogger.info('The command used to get the size of the backup archive was: ' + command)
            print RED + 'Unable to get the size of the backup archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        try:
            archiveSize = re.match('([0-9]+)$', out, re.MULTILINE | re.DOTALL).group(1)
        except AttributeError as err:
            debugLogger.error('There was a match error when trying to get the size of the backup archive.\n' + out + '\n' + str(err))
            debugLogger.info('The command used to get the size of the backup archive was: ' + command)
            print RED + 'There was an error when trying to get the size of the backup archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

        archiveSize = round(float(archiveSize) / 1000000000, 6)
        debugLogger.info('The command was: ' + command)
        debugLogger.info('The archiveSize is: ' + str(archiveSize))
        totalArchiveSize = totalArchiveSize + archiveSize

    command = 'du -BKB -sc ' + upgradeWorkingDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get the size of the upgrade working directory (' + upgradeWorkingDir + ').\n' + err + '\n' + out)
        debugLogger.info('The command used to get the size of the upgrade working directory was: ' + command)
        print RED + 'Unable to get the size of the upgrade working directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    try:
        upgradeWorkingDirSize = float(re.match('\\s*([0-9]+)kb\\s+', out, re.DOTALL | re.IGNORECASE | re.MULTILINE).group(1)) / 1048576
    except AttributeError as err:
        debugLogger.error('There was a match error when trying to get the size of the upgrade working directory.\n' + out + '\n' + str(err))
        debugLogger.info('The command used to get the size of the upgrade working directory was: ' + command)
        print RED + 'There was an error when trying to get the size of the upgrade working directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    debugLogger.info('The command was: ' + command)
    debugLogger.info('The upgrade working directory size is: ' + str(archiveSize))
    debugLogger.info('The total calculated size of all the archives (backup and restoration) is: ' + str(totalArchiveSize) + 'GB.')
    debugLogger.info('The calculated restoration archive size is: ' + str(archiveSize) + 'GB.')
    debugLogger.info('The calculated upgrade working directory size is: ' + str(upgradeWorkingDirSize) + 'GB.')
    debugLogger.info('The calculated ISO estimated size (restoration archive size + upgrade working directory size) is: ' + str(archiveSize + upgradeWorkingDirSize) + 'GB.')
    if availableDiskSpace - (totalArchiveSize + archiveSize + upgradeWorkingDirSize) < 3:
        debugLogger.error('There is not enough disk space on the root filesystem for the upgrade. There needs to be at least 3GB of disk space (availableDiskSpace - (totalArchiveSize + restorationArchiveSize + upgradeWorkingDirSize))).')
        print RED + 'There is not enough disk space on the root filesystem for the upgrade; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if archiveSize + upgradeWorkingDirSize > 2.8:
        debugLogger.error('The data to be stored on the ISO exceeds 2.8GB (restoration archive size + upgrade working directory size).')
        print RED + 'The data to be stored on the ISO exceeds 2.8GB; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done checking to ensure that there is enough disk space for the backup and that the backup ISO image data does not exceed 3GB.')
    return


def createNetworkInformationFile(upgradeWorkingDir, osDist):
    nicDataFileDir = upgradeWorkingDir + '/nicDataFile'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Creating the NIC MAC address cross reference file that will be used for reference after the upgrade.')
    print GREEN + 'Creating the NIC MAC address cross reference file that will be used for reference after the upgrade.' + RESETCOLORS
    if not os.path.exists(nicDataFileDir):
        try:
            os.mkdir(nicDataFileDir)
        except OSError as err:
            debugLogger.error("Unable to create the NIC MAC address cross reference data directory '" + nicDataFileDir + "'.\n" + str(err))
            print RED + 'Unable to create the NIC MAC address cross reference data directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

    command = 'ifconfig -a'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get NIC card information.\n' + err + '\n' + out)
        debugLogger.info('The command used to get NIC card information was: ' + command)
        print RED + 'Unable to get NIC card information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    nicDataList = out.splitlines()
    debugLogger.info('The NIC data list was:\n' + str(nicDataList))
    nicDict = {}
    for data in nicDataList:
        if 'HWaddr' in data and 'bond' not in data:
            try:
                nicList = re.match('\\s*([a-z0-9]+)\\s+.*HWaddr\\s+([a-z0-9:]+)', data, re.IGNORECASE).groups()
            except AttributeError as err:
                debugLogger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                print RED + "There was an error when trying to match against '" + data + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

            nicName = nicList[0]
            nicMACAddress = nicList[1].lower()
            nicDict[nicMACAddress] = nicName

    debugLogger.info('The NIC dictionary mapping MAC addresses to NIC card names was:\n' + str(nicDict))
    procBondingDir = '/proc/net/bonding'
    if os.path.isdir(procBondingDir):
        command = 'ls ' + procBondingDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to get the network bond information from '" + procBondingDir + "'.\n" + err + '\n' + out)
            debugLogger.info('The command used to get the network bond information was: ' + command)
            print RED + 'Unable to get the network bond information; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        activeBondsList = out.strip().split()
        debugLogger.info('The bond list from proc was:\n' + str(activeBondsList))
        for bondName in activeBondsList:
            command = 'cat ' + procBondingDir + '/' + bondName
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to get the network bond information for '" + bondName + "' from proc.\n" + err + '\n' + out)
                debugLogger.info("The command used to get the network bond information for '" + bondName + "' was: " + command)
                print RED + "Unable to get the network bond information for '" + bondName + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)
            procBondingData = out.splitlines()
            debugLogger.info("The the network bond information for '" + bondName + "' was:\n" + str(procBondingData))
            for data in procBondingData:
                if 'Slave Interface' in data:
                    slaveInterface = re.match('.*:\\s+([a-z0-9]+)', data).group(1)
                    continue
                if 'Permanent HW addr' in data:
                    macAddress = re.match('.*:\\s+([a-z0-9:]+)', data).group(1)
                    nicDict[macAddress] = slaveInterface

        debugLogger.info('The updated NIC dictionary was determined to be: ' + str(nicDict) + '.')
        if osDist == 'RHEL':
            updateNICCfgFiles(nicDict)
    else:
        debugLogger.info("It was determined that there were no active network bonds, since '" + procBondingDir + "' did not exist.")
    try:
        macAddressDataFile = nicDataFileDir + '/macAddressData.dat'
        f = open(macAddressDataFile, 'w')
        for macAddress in nicDict:
            f.write(nicDict[macAddress] + '|' + macAddress + '\n')

    except IOError as err:
        debugLogger.error("Could not write NIC card mac address information to '" + macAddressDataFile + "'.\n" + str(err))
        print RED + 'Could not write NIC card mac address information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    finally:
        f.close()

    logger.info('Done creating the NIC MAC address cross reference file that will be used for reference after the upgrade.')


def updateNICCfgFiles(nicDict):
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    for macAddress in nicDict:
        nicCFGFile = '/etc/sysconfig/network-scripts/ifcfg-' + nicDict[macAddress]
        if os.path.exists(nicCFGFile):
            command = 'egrep "^\\s*HWADDR" ' + nicCFGFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            debugLogger.info("The output of the command '" + command + "' used to get the NIC's MAC address variable 'HWADDR' from '" + nicCFGFile + "' was: " + out.strip() + '.')
            if result.returncode != 0:
                debugLogger.info("Updating '" + nicCFGFile + "' with the NIC's MAC address, since it was not present.")
                command = "echo 'HWADDR=" + macAddress + "' >> " + nicCFGFile
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    debugLogger.error("Problems were encountered while updating '" + nicCFGFile + "' with the NIC's MAC address information.\n" + err + '\n' + out)
                    debugLogger.info("The command used to update '" + nicCFGFile + "' with the NIC's MAC address information was: " + command)
                    print RED + "Problems were encountered while updating '" + nicCFGFile + "' with the NIC's MAC address information; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)


def createBackup(backupList, upgradeWorkingDir, osDist):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Creating the backup archive ISO image.')
    print GREEN + 'Creating the backup archive ISO image.' + RESETCOLORS
    archiveDir = upgradeWorkingDir + '/archiveImages'
    if not os.path.isdir(archiveDir):
        try:
            os.mkdir(archiveDir)
        except OSError as err:
            debugLogger.error("Unable to create the pre-upgrade archive directory '" + archiveDir + "'.\n" + str(err))
            print RED + "Unable to create the pre-upgrade archive directory '" + archiveDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    else:
        try:
            archiveList = os.listdir(archiveDir)
            for archive in archiveList:
                os.remove(archiveDir + '/' + archive)

        except OSError as err:
            debugLogger.error("Unable to remove old archives in '" + archiveDir + "'.\n" + str(err))
            print RED + "Unable to remove old archives in '" + archiveDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    hostname = os.uname()[1]
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    restorationBackupList = [archiveDir + '/' + hostname + '_OS_Restoration_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.tar',
     archiveDir + '/' + hostname + '_OS_Restoration_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.tar.gz',
     archiveDir + '/' + hostname + '_OS_Restoration_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp,
     'OS restoration']
    archiveBackupList = [archiveDir + '/' + hostname + '_OS_Archive_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.tar',
     archiveDir + '/' + hostname + '_OS_Archive_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.tar.gz',
     archiveDir + '/' + hostname + '_OS_Archive_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp,
     'OS backup']
    if len(backupList) == 3:
        sapRestorationBackupList = [archiveDir + '/' + hostname + '_SAP_Restoration_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.tar',
         archiveDir + '/' + hostname + '_SAP_Restoration_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.tar.gz',
         archiveDir + '/' + hostname + '_SAP_Restoration_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp,
         'SAP restoration']
    count = 0
    for backupData in backupList:
        fileRemoved = False
        if count == 0:
            backupReferenceList = restorationBackupList
        elif count == 1:
            backupReferenceList = archiveBackupList
        else:
            backupReferenceList = sapRestorationBackupList
        backupData, fileRemoved = confirmBackupDataList(backupData)
        if fileRemoved:
            print YELLOW + 'File(s) were removed from the backup, since they were not present; review the log file for additional information.' + RESETCOLORS
        command = 'tar -cWf ' + backupReferenceList[0] + ' ' + ' '.join(backupData) + ' -C /'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('A problem was encountered while creating the pre-upgrade ' + backupReferenceList[3] + " backup '" + backupReferenceList[0] + "' archive.\n" + err + '\n' + out)
            debugLogger.info('The command used to create the pre-upgrade ' + backupReferenceList[3] + " backup '" + backupReferenceList[0] + "' archive was: " + command)
            print RED + 'A problem was encountered while creating the pre-upgrade archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = 'gzip ' + backupReferenceList[0]
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('A problem was encountered while compressing the pre-upgrade ' + backupReferenceList[3] + " backup '" + backupReferenceList[0] + "' archive.\n" + err + '\n' + out)
            debugLogger.info('The command used to compress the pre-upgrade ' + backupReferenceList[3] + " backup '" + backupReferenceList[0] + "' archive was: " + command)
            print RED + 'A problem was encountered while compressing the pre-upgrade archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        count += 1

    count = 0
    for i in range(len(backupList)):
        if count == 0:
            backupReferenceList = restorationBackupList
        elif count == 1:
            backupReferenceList = archiveBackupList
        else:
            backupReferenceList = sapRestorationBackupList
        backupMd5sumFile = backupReferenceList[2] + '.md5sum'
        command = 'md5sum ' + backupReferenceList[1] + '> ' + backupMd5sumFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to get the md5sum of the backup archive '" + backupReferenceList[1] + "'.\n" + err + '\n' + out)
            debugLogger.info("The command used to get the md5sum of the backup archive '" + backupReferenceList[1] + "' was: " + command)
            print RED + 'Unable to get the md5sum of the backup archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        count += 1

    backupISO = upgradeWorkingDir + '/' + hostname + '_Archive_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.iso'
    backupISOMd5sumFile = upgradeWorkingDir + '/' + hostname + '_Archive_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.md5sum'
    command = 'genisoimage -R -m *_OS_Archive_Backup_For*.* -o ' + backupISO + ' ' + upgradeWorkingDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("A problem was encountered while creating the pre-upgrade backup '" + backupISO + "' ISO image.\n" + err + '\n' + out)
        debugLogger.info("The command used to create the pre-upgrade backup '" + backupISO + "' ISO image was: " + command)
        print RED + "A problem was encountered while creating the pre-upgrade backup  '" + backupISO + "' ISO image; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    command = 'md5sum ' + backupISO + ' > ' + backupISOMd5sumFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("A problem was encountered while getting the md5sum of the pre-upgrade backup '" + backupISO + "' ISO image.\n" + err + '\n' + out)
        debugLogger.info("The command used to get the md5sum of the pre-upgrade backup '" + backupISO + "' ISO image was: " + command)
        print RED + 'A problem was encountered while getting the md5sum of the pre-upgrade backup ISO image; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done creating the backup archive ISO image.')
    return (backupISO, archiveBackupList[1])


def confirmBackupDataList(backupData):
    updatedBackupData = []
    fileRemoved = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking the backup data list to ensure the selected files/directories are present and if not removing them from the list.')
    for file in backupData:
        if glob.glob(file):
            updatedBackupData.append(file)
        else:
            debugLogger.info('The following was removed from the backup list, since it was not present: ' + file + '.')
            fileRemoved = True

    logger.info('Done checking the backup data list to ensure the selected files/directories are present and if not removing them from the list.')
    return (updatedBackupData, fileRemoved)


def stageAddOnRPMS(programParentDir, upgradeWorkingDir, osDist, osUpgradeVersion, systemType):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Copying the additional RPMs needed for the post-upgrade to the pre-upgrade working directory.')
    addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/' + systemType + '/' + osDist + '/' + osUpgradeVersion
    addOnSoftwareRPMSDir = upgradeWorkingDir + '/addOnSoftwareRPMS'
    try:
        if os.listdir(addOnSoftwareRPMDir):
            try:
                os.mkdir(addOnSoftwareRPMSDir)
            except OSError as err:
                debugLogger.error("Unable to create the additional RPMs directory '" + addOnSoftwareRPMSDir + "'.\n" + str(err))
                print RED + 'Unable to create the additional RPMs directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

            command = 'cp ' + addOnSoftwareRPMDir + '/* ' + addOnSoftwareRPMSDir
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            debugLogger.info("The command used to copy the additional RPMs into place for the post-upgrade installation was: '" + command)
            if result.returncode != 0:
                debugLogger.error("Unable to copy the additional RPMs from '" + addOnSoftwareRPMDir + "' to '" + addOnSoftwareRPMSDir + "'.\n" + err + '\n' + out)
                print RED + 'Unable to copy the additional RPMs into place for the post-upgrade installation; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
        else:
            debugLogger.info('There were no additional RPMs present for the post-upgrade.')
    except OSError as err:
        debugLogger.error("Unable to get a listing of the additional RPMs needed for the post-upgrade from '" + addOnSoftwareRPMDir + "'.\n" + str(err))
        print RED + 'Unable to get a listing of the additional RPMs needed for the post-upgrade; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    logger.info('Done copying the additional RPMs needed for the post-upgrade to the pre-upgrade working directory.')


def updateInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, **kwargs):
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    bootFromSAN = False
    serverModel = 'Superdome'
    autoinstImageFile = programParentDir + '/installCtrlFiles/autoinst.img'
    autoinstImgMountPoint = '/tmp/autoinstImg_' + dateTimestamp
    installCtrlFileDir = upgradeWorkingDir + '/installCtrlFile'
    ctrlFile = installCtrlFileDir + '/autoinst.xml'
    lunID = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Updating the install control file with the partition ID that will have the OS installed on it.')
    if 'bootFromSAN' in kwargs:
        bootFromSAN = True
    if 'mellanoxPresent' in kwargs:
        mellanox = kwargs['mellanoxPresent']
    if 'serverModel' in kwargs:
        serverModel = kwargs['serverModel']
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/cs500-autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/cs500_autoinst.img'
    else:
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/cs900-autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/cs900_autoinst.img'
    try:
        os.mkdir(installCtrlFileDir)
        shutil.copy2(installCtrlFileTemplate, ctrlFile)
        shutil.copy2(autoinstImageFile, ctrlFileImg)
    except OSError as err:
        debugLogger.error("Unable to create install control file directory '" + installCtrlFileDir + "'.\n" + str(err))
        print RED + 'Unable to create the install control file directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    except IOError as err:
        debugLogger.error("Unable to copy the install control files to '" + ctrlFile + "'.\n" + str(err))
        print RED + 'Unable to get a copy of the install control files; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    if not os.path.isdir(autoinstImgMountPoint):
        try:
            os.mkdir(autoinstImgMountPoint)
        except OSError as err:
            debugLogger.error("Unable to create mount point '" + autoinstImgMountPoint + "'.\n" + str(err))
            print RED + "Unable to create mount point '" + autoinstImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    command = 'mount -o loop -o rw ' + ctrlFileImg + ' ' + autoinstImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to mount '" + ctrlFileImg + "' on '" + autoinstImgMountPoint + "'.\n" + err + '\n' + out)
        debugLogger.info('The command used to mount the control image file was: ' + command)
        print RED + 'Unable to mount the control image file; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if serverModel == 'Superdome' or bootFromSAN:
        command = 'df /boot/efi'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Unable to get the partition information for the root file system.\n' + err + '\n' + out)
            debugLogger.info('The command used to get the partition information for the root file system was: ' + command)
            print RED + 'Unable to get the partition information for the root file system; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        out = out.strip()
        debugLogger.info('df shows that the /boot/efi partition is mounted on:\n' + out)
        if '/dev' not in out:
            debugLogger.error("Unable to identify the the OS LUN device, since '/dev' was not present in its path.")
            print RED + 'Unable to identify the OS LUN device; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        try:
            if '360002ac0' in out:
                lunID = re.match('.*(360002ac0+[0-9a-f]+)[_-]part', out, re.DOTALL | re.MULTILINE).group(1)
            else:
                device = re.match('.*(/dev/[0-9a-z/_-]*)\\s+', out, re.DOTALL | re.MULTILINE).group(1)
                command = 'find -L /dev -samefile ' + device
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    if not 'already visited the directory' in err:
                        if not 'No such' in err:
                            debugLogger.error("Failed to get the files linked to '" + device + "'.\n" + err + '\n' + out)
                            debugLogger.info("The command used to get the files linked to '" + device + "' was: " + command)
                            print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                            exit(1)
                        else:
                            debugLogger.warn('find complained while searching for files linked to ' + device + ': \n' + err + '\n' + out)
                    fileList = out.splitlines()
                    for file in fileList:
                        if '360002ac0' in file:
                            try:
                                lunID = re.match('.*(360002ac0+[0-9a-f]+)', file).group(1)
                            except AttributeError as err:
                                debugLogger.error("There was a match error when trying to match against '" + file + "'.\n" + str(err))
                                print RED + 'There was a match error when trying to get the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                                exit(1)

                            break

                    lunID == '' and debugLogger.error("Unable to identify the OS LUN ID using the device's (" + device + ') linked file list: ' + str(fileList))
                    print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)
        except AttributeError as err:
            debugLogger.error("There was a match error when trying to match against '" + out + "'.\n" + str(err))
            print RED + 'There was a match error when trying to get the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

        debugLogger.info("The OS LUN ID was determined to be '" + lunID + "'.")
        osLUNDevice = '/dev/mapper/' + lunID
        command = "sed -ri 's,%%bootDisk%%," + osLUNDevice + ",g' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' with the OS LUN device '" + osLUNDevice + "'.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' with the OS LUN device '" + osLUNDevice + "' was: " + command)
            print RED + 'Unable to update the install control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if serverModel == 'DL580':
        if mellanox:
            command = "sed -i '/<BEGIN MLX4>\\|<END MLX4>/d' " + ctrlFile
        else:
            command = "sed -i '/^[ \t]*<BEGIN MLX4>/,/^[ \t]*<END MLX4>/d' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update the '" + ctrlFile + "' Mellanox script section.\n" + err + '\n' + out)
            debugLogger.info("The command used to update the '" + ctrlFile + "' Mellanox script section was: " + command)
            print RED + 'Unable to update the install control file Mellanox script section; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if 'bootFromSAN' in kwargs:
        command = 'sed -i \'s@<start_multipath config:type="boolean">false</start_multipath>@<start_multipath config:type="boolean">true</start_multipath>@\' ' + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' to have multipath start.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' to have multipath start was: " + command)
            print RED + 'Unable to update the install control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = 'sed -i \'\\|^[ \\t]*<pre-scripts config:type="list">|,\\|^[ \\t]*</pre-scripts>|d\' ' + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' with the removal of the pre-scripts section.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' with the removal of the pre-scripts section was: " + command)
            print RED + 'Unable to update the install control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        askContents = '    <ask-list config:type="list">\\n      <ask>\\n        <title>OS LUN: ' + osLUNDevice + '</title> \\n        <question>Choose option</question> \\n        <selection config:type="list"> \\n          <entry> \\n            <label>Reboot Server</label> \\n            <value>reboot</value> \\n          </entry> \\n          <entry> \\n            <label>Halt Server</label> \\n            <value>halt</value> \\n          </entry> \\n          <entry> \\n            <label>Continue to overwrite the LUN device.</label> \\n            <value>continue</value> \\n          </entry> \\n        </selection> \\n        <stage>initial</stage> \\n        <script> \\n          <environment config:type="boolean">true</environment> \\n          <feedback config:type="boolean">true</feedback> \\n          <debug config:type="boolean">false</debug> \\n          <rerun_on_error config:type="boolean">true</rerun_on_error> \\n          <source> \\n<![CDATA[ \\n#!/bin/bash \\n \\ncase "$VAL" in \\n    "reboot") \\n        echo b > /proc/sysrq-trigger \\n        exit 0 \\n        ;; \\n    "halt") \\n        echo o > /proc/sysrq-trigger \\n        exit 0 \\n        ;; \\n    "continue") \\n        exit 0 \\n        ;; \\nesac \\n]]> \\n          </source> \\n        </script> \\n      </ask> \\n    </ask-list>'
        command = 'sed -i \'\\|<ask-list config:type="list">|,\\|</ask-list>|c\\' + askContents + "' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' with the current ask-list section.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' with the current ask-list section was: " + command)
            print RED + 'Unable to update the install control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if osUpgradeVersion == '12.1':
        slesSP1PackageDict = {'sapconf': 'saptune',
         'rear116': 'rear118a'}
        for package in slesSP1PackageDict:
            command = "sed -i 's,<package>" + slesSP1PackageDict[package] + '</package>,<package>' + package + "</package>,' " + ctrlFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to update '" + ctrlFile + "' with the HPE SAP HANA specific package (" + package + ') for SLES for SAP 12 SP1.\n' + err + '\n' + out)
                debugLogger.info("The command used to update '" + ctrlFile + "' with the HPE SAP HANA specific package (" + package + ') for SLES for SAP 12 SP1 was: ' + command)
                print RED + 'Unable to update the install control file with the HPE SAP HANA specific package for SLES for SAP 12 SP1; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            time.sleep(1.0)

    if serverModel == 'DL580' and osUpgradeVersion == '12.1':
        hpeTune = "mkdir -p /mnt/etc/tuned/sap-hpe-hana\\ncat<<EOF > /mnt/etc/tuned/sap-hpe-hana/tuned.conf\\n######################################################\\n# START: tuned profile sap-hpe-hana settings\\n######################################################\\n#\\n# tuned configuration for HPE SAP HANA.\\n# Inherited from SuSE/SAP 'sap-hana' profile\\n#\\n# Allows HPE SAP HANA specific tunings\\n#\\n[main]\\ninclude = sap-hana\\n"
        command = "sed -i '\\|<START HPE TUNE>|,\\|<END HPE TUNE>|c\\" + hpeTune + "' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' with the HPE SAP HANA specific tuning for SLES for SAP 12 SP1.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' with the HPE SAP HANA specific tuning for SLES for SAP 12 SP1 was: " + command)
            print RED + 'Unable to update the install control file with the HPE SAP HANA specific tuning for SLES for SAP 12 SP1; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if osUpgradeVersion == '12.1':
        command = "sed -i '\\|^[ \t]*<START HPE TUNE TWO>|,\\|^[ \t]*<END HPE TUNE TWO>|d' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' with the HPE SAP HANA specific tuning for SLES for SAP 12 SP1.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' with the HPE SAP HANA specific tuning for SLES for SAP 12 SP1 was: " + command)
            print RED + 'Unable to update the install control file with the HPE SAP HANA specific tuning for SLES for SAP 12 SP1; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    else:
        command = "sed -i '/<START HPE TUNE>\\|<END HPE TUNE>\\|<START HPE TUNE TWO>\\|<END HPE TUNE TWO>/d' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to remove the tuning boundaries from '" + ctrlFile + "'.\n" + err + '\n' + out)
            debugLogger.error("The command used to remove the tuning boundaries from '" + ctrlFile + "' was: " + command)
            print RED + 'Unable to remove the tuning boundaries from the install control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    try:
        shutil.copy2(ctrlFile, autoinstImgMountPoint)
    except IOError as err:
        debugLogger.error("Unable to copy the install control file '" + ctrlFile + "' to '" + autoinstImgMountPoint + "'.\n" + str(err))
        print RED + 'Unable to copy the install control file onto the control file image; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    command = 'umount ' + autoinstImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.warn("Unable to unmount '" + autoinstImgMountPoint + "'.\n" + err + '\n' + out)
        print YELLOW + "Unable to unmount '" + autoinstImgMountPoint + "'; ." + RESETCOLORS
        exit(1)
    logger.info('Done updating the install control file with the partition ID that will have the OS installed on it.')
    return ctrlFileImg


def updateSGInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel):
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    autoinstImageFile = programParentDir + '/installCtrlFiles/autoinst.img'
    autoinstImgMountPoint = '/tmp/autoinstImg_' + dateTimestamp
    installCtrlFileDir = upgradeWorkingDir + '/installCtrlFile'
    ctrlFile = installCtrlFileDir + '/autoinst.xml'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Updating the install control file for the Serviceguard node.')
    if serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9':
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/sgQS-autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/sgQS_autoinst.img'
    else:
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/sgNFS-autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/sgNFS_autoinst.img'
    try:
        os.mkdir(installCtrlFileDir)
        shutil.copy2(installCtrlFileTemplate, ctrlFile)
        shutil.copy2(autoinstImageFile, ctrlFileImg)
    except OSError as err:
        debugLogger.error("Unable to create install control file directory '" + installCtrlFileDir + "'.\n" + str(err))
        print RED + "Unable to create the install control file directory '" + installCtrlFileDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    except IOError as err:
        debugLogger.error("Unable to copy the install control files to '" + ctrlFile + "'.\n" + str(err))
        print RED + "Unable to copy the install control files to '" + ctrlFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    if not os.path.isdir(autoinstImgMountPoint):
        try:
            os.mkdir(autoinstImgMountPoint)
        except OSError as err:
            debugLogger.error("Unable to create mount point '" + autoinstImgMountPoint + "'.\n" + str(err))
            print RED + "Unable to create mount point '" + autoinstImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    command = 'mount -o loop -o rw ' + ctrlFileImg + ' ' + autoinstImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to mount '" + ctrlFileImg + "' on '" + autoinstImgMountPoint + "'.\n" + err + '\n' + out)
        debugLogger.info('The command used to mount the control image file was: ' + command)
        print RED + 'Unable to mount the control image file; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if serverModel == 'ProLiant DL360 Gen9':
        command = "sed -i 's/B120i/P440ar/g' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' with the DL360's controller model (P440ar).\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' with the DL360's controller model (P440ar) was: " + command)
            print RED + "Unable to update the install control file with the DL360's controller model (P440ar); fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
    if osUpgradeVersion == '12.1':
        slesSP1PackageDict = {'sapconf': 'saptune',
         'rear116': 'rear118a'}
        for package in slesSP1PackageDict:
            command = "sed -i 's,<package>" + slesSP1PackageDict[package] + '</package>,<package>' + package + "</package>,' " + ctrlFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to update '" + ctrlFile + "' with the HPE SAP HANA specific package (" + package + ') for SLES for SAP 12 SP1.\n' + err + '\n' + out)
                debugLogger.info("The command used to update '" + ctrlFile + "' with the HPE SAP HANA specific package (" + package + ') for SLES for SAP 12 SP1 was: ' + command)
                print RED + 'Unable to update the install control file with the HPE SAP HANA specific package for SLES for SAP 12 SP1; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            time.sleep(1.0)

    if osUpgradeVersion == '11.4':
        slesPackageDict = {'sapconf': 'saptune',
         'rear': 'rear118a',
         'microcode_ctl': 'ucode-intel'}
        for package in slesPackageDict:
            command = "sed -i 's,<package>" + slesPackageDict[package] + '</package>,<package>' + package + "</package>,' " + ctrlFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to update '" + ctrlFile + "' with the HPE SAP HANA specific package (" + package + ') for SLES for SAP 11 SP4.\n' + err + '\n' + out)
                debugLogger.info("The command used to update '" + ctrlFile + "' with the HPE SAP HANA specific package (" + package + ') for SLES for SAP 11 SP4 was: ' + command)
                print RED + 'Unable to update the install control file with the HPE SAP HANA specific package for SLES for SAP 11 SP4; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            time.sleep(1.0)

        removalPackageList = ['perl-Bootloader-YAML',
         'git-core',
         'perl-Error',
         'tuned',
         'open-lldp',
         'uuidd',
         'libcgroup-tools',
         'libts-1_0-0',
         'lcms2',
         'libgif6',
         'java-1_7_0-openjdk',
         'java-1_7_0-openjdk-headless',
         'python-libxml2']
        sles11Services = '  <runlevel>\\n    <default>3</default>\\n    <services config:type="list">\\n      <service>\\n        <service_name>ntp</service_name>\\n        <service_start>3</service_start>\\n      </service>\\n    </services>\\n  </runlevel>'
        for package in removalPackageList:
            command = "sed -i '/<package>" + package + "<\\/package>/d' " + ctrlFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to remove the packages from the control file '" + ctrlFile + "' that are not present for SLES 11.4.\n" + err + '\n' + out + '\n' + str(removalPackageList))
                debugLogger.info("The command used to remove the packages from the control file '" + ctrlFile + "' that are not present for SLES 11.4 was: " + command)
                print RED + 'Unable to remove the packages from the control file that are not present for SLES 11.4; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            time.sleep(0.1)

        command = "sed -i 's@<loader_type>grub2</loader_type>@<loader_type>grub</loader_type>@' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to change the loader type in the control file '" + ctrlFile + "' from grub2 to grub.\n" + err + '\n' + out)
            debugLogger.info("The command used to change the loader type in the control file '" + ctrlFile + "' from grub2 to grub was: " + command)
            print RED + 'Unable to change the loader type in the control file from grub2 to grub; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = "sed -i '\\|<services-manager>|,\\|</services-manager>|c\\" + sles11Services + "' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Unable to change the "services-manager" section in the control file \'' + ctrlFile + "'.\n" + err + '\n' + out)
            debugLogger.info('The command used to change the "services-manager" section in the control file \'' + ctrlFile + "' was: " + command)
            print RED + 'Unable to change the "services-manager" section in the control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = "sed -i 's@<package>quota-nfs</package>@&\\n      <package>net-snmp</package>\\n      <package>biosdevname</package>@' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to add the net-snmp package to the control file '" + ctrlFile + "'.\n" + err + '\n' + out)
            debugLogger.info("The command used to add the net-snmp package to the control file '" + ctrlFile + "' was: " + command)
            print RED + 'Unable to add the net-snmp package to the control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = "sed -i '\\@<listentry>boot/grub2/i386-pc</listentry>\\|<listentry>boot/grub2/x86_64-efi</listentry>@d' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to remove boot subvolumes from the control file '" + ctrlFile + "'.\n" + err + '\n' + out)
            debugLogger.info("The command used to remove boot subvolumes from the control file '" + ctrlFile + "' was: " + command)
            print RED + 'Unable to remove boot subvolumes from the control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        bootPartition = '       <partition>\\n          <create config:type="boolean">true</create>\\n          <crypt_fs config:type="boolean">false</crypt_fs>\\n          <filesystem config:type="symbol">ext3</filesystem>\\n          <format config:type="boolean">true</format>\\n          <fstopt>defaults</fstopt>\\n          <loop_fs config:type="boolean">false</loop_fs>\\n          <mount>/boot</mount>\\n          <mountby config:type="symbol">uuid</mountby>\\n          <partition_id config:type="integer">131</partition_id>\\n          <partition_nr config:type="integer">1</partition_nr>\\n          <resize config:type="boolean">false</resize>\\n          <size>200M</size>\\n        </partition>'
        command = 'sed -i \'/<partitions config:type="list">/a \\ ' + bootPartition + "' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to add the boot partition to the control file '" + ctrlFile + "'.\n" + err + '\n' + out)
            debugLogger.info("The command used to add the boot partition to the control file '" + ctrlFile + "' was: " + command)
            print RED + 'Unable to add the boot partition to the control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    try:
        shutil.copy2(ctrlFile, autoinstImgMountPoint)
    except IOError as err:
        debugLogger.error("Unable to copy the install control file '" + ctrlFile + "' to '" + autoinstImgMountPoint + "'.\n" + str(err))
        print RED + 'Unable to copy the install control file onto the control file image; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    command = 'umount ' + autoinstImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.warn("Unable to unmount '" + autoinstImgMountPoint + "'.\n" + err + '\n' + out)
        print YELLOW + "Unable to unmount '" + autoinstImgMountPoint + "'; ." + RESETCOLORS
        exit(1)
    logger.info('Done updating the install control file the Serviceguard node.')
    return ctrlFileImg


def checkForMellanox(programParentDir, upgradeWorkingDir, osDist, osDistLevel):
    pciIdsFile = programParentDir + '/mellanoxFiles/pci.ids'
    mellanoxPresent = False
    if osDist == 'SLES':
        mellanoxDriverRPMS = glob.glob(programParentDir + '/mellanoxFiles/SLES/' + osDistLevel + '/*.rpm')
    else:
        mellanoxDriverRPMS = glob.glob(programParentDir + '/mellanoxFiles/RHEL/' + osDistLevel + '/*.rpm')
    mellanoxDriverDir = upgradeWorkingDir + '/mellanoxDriver'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking to see if Mellanox NIC cards are present.')
    print GREEN + 'Checking to see if Mellanox NIC cards are present.' + RESETCOLORS
    command = 'lspci -i ' + pciIdsFile + ' -mvv'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to get the lspci output which is used to check if Mellanox NIC cards are present.\n' + err + '\n' + out)
        debugLogger.info("The command used to get the lspci output which is used to check if Mellanox NIC cards are present was: '" + command + "'.")
        print RED + 'Failed to get the lspci output which is used to check if Mellanox NIC cards are present; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    out = re.sub('\n{2,}', '####', out)
    deviceList = out.split('####')
    debugLogger.info('The lspci device list was:\n' + str(deviceList))
    for device in deviceList:
        if ('Ethernet controller' in device or 'Network controller' in device) and 'Mellanox' in device:
            mellanoxPresent = True
            break

    if mellanoxPresent and osDistLevel != '12.1':
        try:
            os.mkdir(mellanoxDriverDir)
            for file in mellanoxDriverRPMS:
                shutil.copy2(file, mellanoxDriverDir)
                time.sleep(1.0)

        except OSError as err:
            debugLogger.error("Unable to create the Mellanox driver directory '" + mellanoxDriverDir + "'.\n" + str(err))
            print RED + "Unable to create the Mellanox driver directory '" + mellanoxDriverDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        except IOError as err:
            debugLogger.error("Unable to copy the Mellanox driver to '" + mellanoxDriverDir + "'.\n" + str(err))
            print RED + "Unable to copy the Mellanox driver to '" + mellanoxDriverDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    logger.info('Done checking to see if Mellanox NIC cards are present.')
    return mellanoxPresent


def copyRepositoryTemplate(programParentDir, upgradeWorkingDir):
    repositoryTemplate = programParentDir + '/repositoryTemplate/local.repo'
    repoDir = upgradeWorkingDir + '/repositoryTemplate'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Copying the yum repository template needed for the post-upgrade.')
    try:
        if not os.path.isdir(repoDir):
            os.mkdir(repoDir)
        shutil.copy(repositoryTemplate, repoDir)
    except OSError as err:
        debugLogger.error("Unable to create the yum repository directory '" + repoDir + "'.\n" + str(err))
        print RED + "Unable to create the yum repository directory '" + repoDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    except IOError as err:
        debugLogger.error("Unable to copy the yum repository template from '" + repositoryTemplate + "' to '" + repoDir + "'.\n" + str(err))
        print RED + 'Unable to copy the yum repository template into place for the post-upgrade installation; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    logger.info('Done copying the yum repository template needed for the post-upgrade.')


def getOSUpgradeVersion(supportedOSVersions, serverModel, upgradeResourceDict):
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    while True:
        count = 0
        choiceNumberDict = {}
        prompt = 'Select the OS version that the server is being upgraded to ('
        for version in supportedOSVersions:
            osVersion = supportedOSVersions[count]
            if count == 0:
                print ''
            if osVersion[5:] == '11.4':
                print str(count + 1) + '. ' + osVersion[:4] + ' ' + osVersion[5:] + ' (Serviceguard Quorum Servers Only)'
            else:
                print str(count + 1) + '. ' + osVersion[:4] + ' ' + osVersion[5:]
            count += 1
            if count == 1:
                prompt = prompt + str(count)
            else:
                prompt = prompt + ',' + str(count)
            choiceNumberDict[str(count)] = None

        response = raw_input(prompt + ') [1]: ')
        response = response.strip()
        if response == '':
            response = '1'
        elif response not in choiceNumberDict:
            print 'An invalid selection was made; please try again.\n'
            continue
        osVersion = supportedOSVersions[int(response) - 1]
        if osVersion[5:] == '11.4':
            if serverModel == 'ProLiant DL320e Gen8 v2' or not serverModel == 'ProLiant DL360 Gen9':
                print 'An invalid selection was made; please try again.'
                continue
            if osVersion[5:] != '11.4' and (serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9'):
                try:
                    if serverModel == 'ProLiant DL320e Gen8 v2':
                        if not literal_eval(upgradeResourceDict['dl320eSLES12Supported']):
                            while True:
                                response = raw_input('An invalid selection was made, SLES 12.x is not supported for a QS upgrade, do you want to continue [y|n]: ')
                                response = response.strip().lower()
                                if not response == 'y':
                                    print response == 'n' or 'An invalid entry was provided; please try again.'
                                    continue
                                else:
                                    if response == 'y':
                                        break
                                    else:
                                        debugLogger.info('The upgrade was cancelled while selecting the OS to upgrade to.')
                                        exit(0)
                                    break

                            continue
                    elif not literal_eval(upgradeResourceDict['dl360SLES12Supported']):
                        while True:
                            response = raw_input('An invalid selection was made, SLES 12.x is not supported for a QS upgrade, do you want to continue [y|n]: ')
                            response = response.strip().lower()
                            if not response == 'y':
                                print response == 'n' or 'An invalid entry was provided; please try again.\n'
                                continue
                            else:
                                if response == 'y':
                                    break
                                else:
                                    debugLogger.info('The upgrade was cancelled while selecting the OS to upgrade to.')
                                    exit(0)
                                break

                        continue
                except ValueError as err:
                    debugLogger.error('There was an invalid entry for the Quorum server ...SLES12Supported resource.\n' + str(err))
                    print RED + 'There was an invalid entry for the Quorum server ...SLES12Supported resource; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

            while True:
                response = raw_input('The server is going to be upgraded to ' + osVersion[:4] + ' ' + osVersion[5:] + '; is this correct [y|n|q]: ')
                response = response.strip().lower()
                if not response == 'y':
                    print response == 'n' or response == 'q' or 'An invalid entry was provided; please try again.\n'
                    continue
                else:
                    if response == 'y':
                        validOS = True
                    elif response == 'n':
                        validOS = False
                    else:
                        debugLogger.info('The upgrade was cancelled while selecting the OS to upgrade to.')
                        exit(0)
                    break

            osUpgradeVersion = validOS and osVersion[5:]
            break
        else:
            continue

    return osUpgradeVersion


def updateRHELInstallCtrlFile(programParentDir, upgradeWorkingDir):
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    ksImageFile = programParentDir + '/installCtrlFiles/ks.img'
    ksImgMountPoint = '/tmp/ksImg_' + dateTimestamp
    installCtrlFileDir = upgradeWorkingDir + '/installCtrlFile'
    ctrlFile = installCtrlFileDir + '/ks.cfg'
    lunID = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Updating the install control file with the partition ID that will have the OS installed on it.')
    installCtrlFileTemplate = programParentDir + '/installCtrlFiles/cs900-ks.cfg'
    ctrlFileImg = installCtrlFileDir + '/cs900_ks.img'
    try:
        os.mkdir(installCtrlFileDir)
        shutil.copy2(installCtrlFileTemplate, ctrlFile)
        shutil.copy2(ksImageFile, ctrlFileImg)
    except OSError as err:
        debugLogger.error("Unable to create install control file directory '" + installCtrlFileDir + "'.\n" + str(err))
        print RED + 'Unable to create the install control file directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    except IOError as err:
        debugLogger.error("Unable to copy the install control files to '" + ctrlFile + "'.\n" + str(err))
        print RED + 'Unable to get a copy of the install control files; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    if not os.path.isdir(ksImgMountPoint):
        try:
            os.mkdir(ksImgMountPoint)
        except OSError as err:
            debugLogger.error("Unable to create mount point '" + ksImgMountPoint + "'.\n" + str(err))
            print RED + "Unable to create mount point '" + ksImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    command = 'mount -o loop -o rw ' + ctrlFileImg + ' ' + ksImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to mount '" + ctrlFileImg + "' on '" + ksImgMountPoint + "'.\n" + err + '\n' + out)
        debugLogger.info('The command used to mount the control image file was: ' + command)
        print RED + 'Unable to mount the control image file; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    command = 'df /boot/efi'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get the partition information for the root file system.\n' + err + '\n' + out)
        debugLogger.info('The command used to get the partition information for the root file system was: ' + command)
        print RED + 'Unable to get the partition information for the root file system; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    out = out.strip()
    debugLogger.info('df shows that the /boot/efi partition is mounted on:\n' + out)
    if '/dev' not in out:
        debugLogger.error("Unable to identify the the OS LUN device, since '/dev' was not present in its path.")
        print RED + 'Unable to identify the OS LUN device; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    try:
        if '360002ac0' in out:
            lunID = re.match('.*(360002ac0+[0-9a-f]+)[_-]part', out, re.DOTALL | re.MULTILINE).group(1)
        else:
            device = re.match('.*(/dev/[0-9a-z/_-]*)\\s+', out, re.DOTALL | re.MULTILINE).group(1)
            command = 'find -L /dev -samefile ' + device
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                if not 'already visited the directory' in err:
                    if not 'No such' in err:
                        debugLogger.error("Failed to get the files linked to '" + device + "'.\n" + err + '\n' + out)
                        debugLogger.info("The command used to get the files linked to '" + device + "' was: " + command)
                        print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)
                    else:
                        debugLogger.warn('find complained while searching for files linked to ' + device + ': \n' + err + '\n' + out)
                fileList = out.splitlines()
                for file in fileList:
                    if '360002ac0' in file:
                        try:
                            lunID = re.match('.*(360002ac0+[0-9a-f]+)', file).group(1)
                        except AttributeError as err:
                            debugLogger.error("There was a match error when trying to match against '" + file + "'.\n" + str(err))
                            print RED + 'There was a match error when trying to get the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                            exit(1)

                        break

                lunID == '' and debugLogger.error("Unable to identify the OS LUN ID using the device's (" + device + ') linked file list: ' + str(fileList))
                print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
    except AttributeError as err:
        debugLogger.error("There was a match error when trying to match against '" + out + "'.\n" + str(err))
        print RED + 'There was a match error when trying to get the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    debugLogger.info("The OS LUN ID was determined to be '" + lunID + "'.")
    osLUNDevice = '"disk/by-id/dm-uuid-mpath-' + lunID + '"'
    command = "sed -ri 's,os_device=OS_DEVICE,os_device=" + osLUNDevice + ",g' " + ctrlFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to update '" + ctrlFile + "' with the OS LUN device '" + osLUNDevice + "'.\n" + err + '\n' + out)
        debugLogger.info("The command used to update '" + ctrlFile + "' with the OS LUN device '" + osLUNDevice + "' was: " + command)
        print RED + 'Unable to update the install control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    try:
        shutil.copy2(ctrlFile, ksImgMountPoint)
    except IOError as err:
        debugLogger.error("Unable to copy the install control file '" + ctrlFile + "' to '" + ksImgMountPoint + "'.\n" + str(err))
        print RED + 'Unable to copy the install control file onto the control file image; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    command = 'umount ' + ksImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.warn("Unable to unmount '" + ksImgMountPoint + "'.\n" + err + '\n' + out)
        print YELLOW + "Unable to unmount '" + ksImgMountPoint + "'; ." + RESETCOLORS
        exit(1)
    logger.info('Done updating the install control file with the partition ID that will have the OS installed on it.')
    return ctrlFileImg