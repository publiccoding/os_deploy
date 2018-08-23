# Embedded file name: ./preUpgradeTasks.py
import subprocess
import re
import os
import datetime
import time
import logging
import shutil
import glob
YELLOW = '\x1b[33m'
RED = '\x1b[31m'
GREEN = '\x1b[32m'
RESETCOLORS = '\x1b[0m'

def checkDiskspace(archiveBackup):
    archiveSize = 0
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking to ensure that there is enough disk space for the upgrade.')
    print GREEN + 'Checking to ensure that there is enough disk space for the upgrade.' + RESETCOLORS
    command = 'df /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    if result.returncode != 0:
        debugLogger.error("Unable to get the root file system's usage information.\n" + err + '\n' + out)
        debugLogger.info("The command used to get the root file system's usage information was: " + command + '.')
        print RED + "Unable to get the root file system's usage information; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    try:
        tmpVar = re.match('(.*\\s+){3}([0-9]+)\\s+', out).group(2)
    except AttributeError as err:
        debugLogger.error("There was a match error when getting the root file system size and trying to match against '" + out + "'.\n" + str(err))
        print RED + 'There was a match error when getting the root file system size; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    availableDiskSpace = round(float(tmpVar) / 1048576, 6)
    debugLogger.info('The available disk space on the root filesystem is: ' + str(availableDiskSpace) + 'GB.')
    command = 'tar -czf - ' + ' '.join(archiveBackup) + '|wc -c'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    if re.search('Exiting with failure status due to previous errors', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None or result.returncode != 0:
        debugLogger.error('Unable to get the size of the backup archive.\n' + err + '\n' + out)
        debugLogger.info('The command used to get the size of the archive backup was: ' + command + '.')
        print RED + 'Unable to get the size of the backup archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    try:
        archiveSize = re.match('([0-9]+)$', out, re.MULTILINE | re.DOTALL).group(1)
    except AttributeError as err:
        debugLogger.error('There was a match error when trying to get the size of the backup archive.\n' + out + '\n' + str(err))
        print RED + 'There was a match error when trying to get the size of the backup archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    archiveSize = round(float(archiveSize) / 1073741824, 6) * 2
    debugLogger.info('The calculated archive size (times two) is: ' + str(archiveSize) + 'GB.')
    if availableDiskSpace - archiveSize < 20:
        debugLogger.error('There is not enough disk space on the root filesystem for the upgrade. There needs to be at least 20GB of disk space free after subtracting the calculated archive size from the available disk space.')
        print RED + 'There is not enough disk space on the root filesystem for the upgrade; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done checking to ensure that there is enough disk space for the upgrade.')
    return


def createNetworkInformationFile(upgradeWorkingDir, osDist):
    nicDataFileDir = upgradeWorkingDir + '/nicDataFile'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Creating the NIC MAC address cross reference file that will be used for reference after the upgrade.')
    print GREEN + 'Creating the NIC MAC address cross reference file that will be used for reference after the upgrade.' + RESETCOLORS
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
        debugLogger.info('The command used to get the NIC card information was: ' + command + '.')
        print RED + 'Unable to get NIC card information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    nicDataList = out.splitlines()
    nicDict = {}
    for data in nicDataList:
        if 'HWaddr' in data and 'bond' not in data:
            try:
                nicList = re.match('\\s*([a-z0-9]+)\\s+.*HWaddr\\s+([a-z0-9:]+)', data, re.IGNORECASE).groups()
            except AttributeError as err:
                debugLogger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                print RED + "There was a match error when trying to match against '" + data + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

            nicName = nicList[0]
            nicMACAddress = nicList[1].lower()
            nicDict[nicMACAddress] = nicName

    debugLogger.info('The NIC dictionary was determined to be: ' + str(nicDict) + '.')
    procBondingDir = '/proc/net/bonding'
    if os.path.isdir(procBondingDir):
        command = 'ls ' + procBondingDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to get the network bond information from '" + procBondingDir + "'.\n" + err + '\n' + out)
            debugLogger.info('The command used to get the network bond information was: ' + command + '.')
            print RED + 'Unable to get the network bond information; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        activeBondsList = out.strip().split()
        debugLogger.info('The active bond list was: ' + str(activeBondsList))
        for bondName in activeBondsList:
            command = 'cat ' + procBondingDir + '/' + bondName
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to get network bond information for '" + bondName + "' from proc.\n" + err + '\n' + out)
                debugLogger.info("The command used to get the network bond information for '" + bondName + "' was: " + command + '.')
                print RED + "Unable to get network bond information for '" + bondName + "' from proc; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)
            procBondingData = out.splitlines()
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
        print RED + "Could not write NIC card mac address information to '" + macAddressDataFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

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


def createBackup(archiveBackup, upgradeWorkingDir, osDist):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Creating the backup archive and ISO image.')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    print GREEN + 'Creating the backup archive and ISO image.' + RESETCOLORS
    archiveDir = upgradeWorkingDir + '/archiveBackup'
    try:
        os.mkdir(archiveDir)
    except OSError as err:
        debugLogger.error("Unable to create the archive backup directory '" + archiveDir + "'.\n" + str(err))
        print RED + "Unable to create the archive backup directory '" + archiveDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    hostname = os.uname()[1]
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    tarArchive = archiveDir + '/' + hostname + '_Archive_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.tar'
    command = 'tar -cWf ' + tarArchive + ' ' + ' '.join(archiveBackup) + ' -C /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('A problem was encountered while creating the backup tar archive.\n' + err + '\n' + out)
        debugLogger.info('The command used to create the backup tar archive was: ' + command + '.')
        print RED + 'A problem was encountered while creating the backup tar archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    command = 'gzip ' + tarArchive
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("A problem was encountered while compressing the tar archive '" + tarArchive + "'.\n" + err + '\n' + out)
        debugLogger.info('The command used to compress the tar archive was: ' + command + '.')
        print RED + 'A problem was encountered while compressing the tar archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    backupMd5sumFile = tarArchive[:-4] + '.md5sum'
    command = 'md5sum ' + tarArchive + '.gz' + ' > ' + backupMd5sumFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to get the md5sum of the backup archive '" + tarArchive + '.gz' + "'.\n" + err + '\n' + out)
        debugLogger.info('The command used to get the md5sum of the backup archive was: ' + command + '.')
        print RED + 'Unable to get the md5sum of the backup archive; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    backupISO = upgradeWorkingDir + '/' + hostname + '_ISO_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.iso'
    backupISOMd5sumFile = backupISO[:-4] + '.md5sum'
    command = 'genisoimage -R -m ' + archiveDir + ' -o ' + backupISO + ' ' + upgradeWorkingDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("A problem was encountered while creating the backup '" + backupISO + "' ISO image.\n" + err + '\n' + out)
        debugLogger.info('The command used to create the backup ISO image was: ' + command + '.')
        print RED + 'A problem was encountered while creating the backup ISO image; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    command = 'md5sum ' + backupISO + ' > ' + backupISOMd5sumFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("A problem was encountered while getting the md5sum of the backup '" + backupISO + "' ISO image.\n" + err + '\n' + out)
        debugLogger.info('The command used to get the md5sum of the backup ISO image was: ' + command + '.')
        print RED + 'A problem was encountered while getting the md5sum of the backup ISO image; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done creating the backup archive and ISO image.')
    return (backupISO, tarArchive + '.gz')


def confirmBackupDataList(backupData):
    updatedBackupData = []
    fileRemoved = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking the backup archive to ensure the selected files/directories are present and if not removing them from the backup.')
    for file in backupData:
        if glob.glob(file):
            updatedBackupData.append(file)
        else:
            debugLogger.info('The following was removed from the backup list, since it was not present: ' + file + '.')
            fileRemoved = True

    logger.info('Done checking the backup archive to ensure the selected files/directories are present and if not removing them from the backup.')
    return (updatedBackupData, fileRemoved)


def updateUpgradeCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel, **kwargs):
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%S%b%Y')
    bootFromSAN = False
    autoupgImageFile = programParentDir + '/upgradeCtrlFiles/autoupg.img'
    autoupgImgMountPoint = '/tmp/autoupgImg_' + dateTimestamp
    upgradeCtrlFileDir = upgradeWorkingDir + '/upgradeCtrlFile'
    ctrlFile = upgradeCtrlFileDir + '/autoupg.xml'
    lunID = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Retrieving the upgrade control file and updating it if necessary.')
    if 'bootFromSAN' in kwargs:
        bootFromSAN = True
    if 'mellanoxPresent' in kwargs:
        mellanox = kwargs['mellanoxPresent']
    debugLogger.info('Boot from SAN is: ' + str(bootFromSAN) + '.')
    if 'DL580' in serverModel:
        upgradeCtrlFileTemplate = programParentDir + '/upgradeCtrlFiles/cs500-autoupg.xml'
        ctrlFileImg = upgradeCtrlFileDir + '/cs500_autoupg.img'
    elif serverModel == 'ProLiant DL360 Gen9':
        if bootFromSAN:
            upgradeCtrlFileTemplate = programParentDir + '/upgradeCtrlFiles/sgNFS-autoupg.xml'
            ctrlFileImg = upgradeCtrlFileDir + '/sgNFS_autoupg.img'
        else:
            upgradeCtrlFileTemplate = programParentDir + '/upgradeCtrlFiles/sgQS-autoupg.xml'
            ctrlFileImg = upgradeCtrlFileDir + '/sgQS_autoupg.img'
    elif serverModel == 'ProLiant DL380p Gen8' or serverModel == 'ProLiant DL360p Gen8':
        upgradeCtrlFileTemplate = programParentDir + '/upgradeCtrlFiles/sgNFS-autoupg.xml'
        ctrlFileImg = upgradeCtrlFileDir + '/sgNFS_autoupg.img'
    elif serverModel == 'ProLiant DL320e Gen8 v2':
        upgradeCtrlFileTemplate = programParentDir + '/upgradeCtrlFiles/sgQS-autoupg.xml'
        ctrlFileImg = upgradeCtrlFileDir + '/sgQS_autoupg.img'
    else:
        upgradeCtrlFileTemplate = programParentDir + '/upgradeCtrlFiles/cs900-autoupg.xml'
        ctrlFileImg = upgradeCtrlFileDir + '/cs900_autoupg.img'
    debugLogger.info('The upgrade control file is: ' + upgradeCtrlFileTemplate + '.')
    try:
        os.mkdir(upgradeCtrlFileDir)
        shutil.copy2(upgradeCtrlFileTemplate, ctrlFile)
        shutil.copy2(autoupgImageFile, ctrlFileImg)
    except OSError as err:
        debugLogger.error("Unable to create upgrade control file directory '" + upgradeCtrlFileDir + "'.\n" + str(err))
        print RED + "Unable to create the upgrade control file directory '" + upgradeCtrlFileDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    except IOError as err:
        debugLogger.error("Unable to copy the upgrade control files to '" + ctrlFile + "'.\n" + str(err))
        print RED + "Unable to copy the upgrade control files to '" + ctrlFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    try:
        os.mkdir(autoupgImgMountPoint)
    except OSError as err:
        debugLogger.error("Unable to create mount point '" + autoupgImgMountPoint + "'.\n" + str(err))
        print RED + "Unable to create mount point '" + autoupgImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    command = 'mount -o loop -o rw ' + ctrlFileImg + ' ' + autoupgImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to mount '" + ctrlFileImg + "' on '" + autoupgImgMountPoint + "'.\n" + err + '\n' + out)
        debugLogger.info("The command used to mount '" + ctrlFileImg + "' on '" + autoupgImgMountPoint + "' was: " + command)
        print RED + "Unable to mount '" + ctrlFileImg + "' on '" + autoupgImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    hostname = os.uname()[1]
    command = "sed -ri 's,%%hostname%%," + hostname + ",g' " + ctrlFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to update '" + ctrlFile + "' with the server's hostname '" + hostname + "'.\n" + err + '\n' + out)
        debugLogger.info("The command used to update '" + ctrlFile + "' with the server's hostname '" + hostname + "' was: " + command)
        print RED + 'Unable to update the upgrade control file with the OS LUN device; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if osUpgradeVersion == '12.3':
        command = "sed -i '/<BEGIN LOGROTATE>\\|<END LOGROTATE>/d' " + ctrlFile
    else:
        command = "sed -i '/^[ \t]*<BEGIN LOGROTATE>/,/^[ \t]*<END LOGROTATE>/d' " + ctrlFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to update the '" + ctrlFile + "' logrotate script section.\n" + err + '\n' + out)
        debugLogger.info("The command used to update the '" + ctrlFile + "' logrotate script section was: " + command)
        print RED + 'Unable to update the upgrade control file logrotate script section; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if 'DL580' in serverModel:
        if mellanox:
            command = "sed -i '/<BEGIN MLX4>\\|<END MLX4>/d' " + ctrlFile
        else:
            command = "sed -i '/^[ \t]*<BEGIN MLX4>/,/^[ \t]*<END MLX4>/d' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update the '" + ctrlFile + "' Mellanox script section.\n" + err + '\n' + out)
            debugLogger.info("The command used to update the '" + ctrlFile + "' Mellanox script section was: " + command)
            print RED + 'Unable to update the upgrade control file Mellanox script section; fix the problem and try again; exiting program execution.' + RESETCOLORS
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
            debugLogger.error('Unable to identify the the OS LUN device.')
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
                    if not ('already visited the directory' in err or 'No such' in err):
                        debugLogger.error("Failed to get the files linked to '" + device + "'.\n" + err + '\n' + out)
                        debugLogger.info("The command used to find the files linked to '" + device + "' was: " + command + '.')
                        print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)
                    else:
                        debugLogger.warn('find complained while searching for files linked to ' + device + ': \n' + err + '\n' + out)
                fileList = out.splitlines()
                debugLogger.info("The list of files linked to '" + device + "' is: " + str(fileList))
                for file in fileList:
                    if '360002ac0' in file:
                        try:
                            lunID = re.match('.*(360002ac0+[0-9a-f]+)', file).group(1)
                        except AttributeError as err:
                            debugLogger.error("There was a match error when trying to match against '" + file + "'.\n" + str(err))
                            print RED + 'There was a match error when trying to get the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                            exit(1)

                        break

                if lunID == '':
                    debugLogger.error("Unable to identify the OS LUN ID using the device's (" + device + ') linked file list.')
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
            print RED + 'Unable to update the upgrade control file with the OS LUN device; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if bootFromSAN and serverModel != 'Superdome':
        command = 'sed -i \'s@<start_multipath config:type="boolean">false</start_multipath>@<start_multipath config:type="boolean">true</start_multipath>@\' ' + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' to start multipath.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' to start multipath was: " + command)
            print RED + 'Unable to update the upgrade control file to start multipath; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = 'sed -i \'\\|^[ \\t]*<pre-scripts config:type="list">|,\\|^[ \\t]*</pre-scripts>|d\' ' + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' with the removal of the pre-scripts section.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' with the removal of the pre-scripts section was: " + command)
            print RED + 'Unable to update the upgrade control file with the removal of the pre-scripts section; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        askContents = '    <ask-list config:type="list">\\n      <ask>\\n        <title>OS LUN: ' + osLUNDevice + '</title> \\n        <question>Choose option</question> \\n        <selection config:type="list"> \\n          <entry> \\n            <label>Reboot Server</label> \\n            <value>reboot</value> \\n          </entry> \\n          <entry> \\n            <label>Halt Server</label> \\n            <value>halt</value> \\n          </entry> \\n          <entry> \\n            <label>Continue to overwrite the LUN device.</label> \\n            <value>continue</value> \\n          </entry> \\n        </selection> \\n        <stage>initial</stage> \\n        <script> \\n          <environment config:type="boolean">true</environment> \\n          <feedback config:type="boolean">true</feedback> \\n          <debug config:type="boolean">false</debug> \\n          <rerun_on_error config:type="boolean">true</rerun_on_error> \\n          <source> \\n<![CDATA[ \\n#!/bin/bash \\n \\ncase "$VAL" in \\n    "reboot") \\n        echo b > /proc/sysrq-trigger \\n        exit 0 \\n        ;; \\n    "halt") \\n        echo o > /proc/sysrq-trigger \\n        exit 0 \\n        ;; \\n    "continue") \\n        exit 0 \\n        ;; \\nesac \\n]]> \\n          </source> \\n        </script> \\n      </ask> \\n    </ask-list>'
        command = 'sed -i \'\\|<ask-list config:type="list">|,\\|</ask-list>|c\\' + askContents + "' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to update '" + ctrlFile + "' with the current ask-list section.\n" + err + '\n' + out)
            debugLogger.info("The command used to update '" + ctrlFile + "' with the current ask-list section was: " + command)
            print RED + 'Unable to update the upgrade control file with the current ask-list section; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    try:
        shutil.copy2(ctrlFile, autoupgImgMountPoint)
    except IOError as err:
        debugLogger.error("Unable to copy the upgrade control file '" + ctrlFile + "' to '" + autoupgImgMountPoint + "'.\n" + str(err))
        print RED + "Unable to copy the upgrade control file '" + ctrlFile + "' to '" + autoupgImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    command = 'umount ' + autoupgImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.warn("Unable to unmount '" + ctrlFileImg + "' from '" + autoupgImgMountPoint + "'.\n" + err + '\n' + out)
        print YELLOW + "Unable to unmount '" + ctrlFileImg + "' from '" + autoupgImgMountPoint + "'; ." + RESETCOLORS
    try:
        os.rmdir(autoupgImgMountPoint)
    except OSError as err:
        debugLogger.warn("Unable to delete directory '" + autoupgImgMountPoint + "'.\n" + err + '\n' + out)
        print YELLOW + "Unable to delete directory '" + autoupgImgMountPoint + "'; ." + RESETCOLORS

    logger.info('Done retrieving the upgrade control file and updating it if necessary.')
    return ctrlFileImg


def getOSUpgradeVersion(supportedOSVersions):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    while True:
        count = 0
        choiceNumberDict = {}
        prompt = 'Select the OS version that the server is being upgraded to ('
        for version in supportedOSVersions:
            osVersion = supportedOSVersions[count]
            print str(count + 1) + '. ' + osVersion[:4] + ' ' + osVersion[5:]
            count += 1
            if count == 1:
                prompt = prompt + str(count)
            else:
                prompt = prompt + ',' + str(count)
            choiceNumberDict[str(count)] = None

        debugLogger.info('The choiceNumberDict is: ' + str(choiceNumberDict))
        response = raw_input(prompt + ') [1]: ')
        response = response.strip()
        if response == '':
            response = '1'
        elif response not in choiceNumberDict:
            debugLogger.error('An invalid OS number choice was made: ' + response + '.')
            print 'An invalid selection was made; please try again.\n'
            continue
        osVersion = supportedOSVersions[int(response) - 1]
        while True:
            response = raw_input('The server is going to be upgraded to ' + osVersion[:4] + ' ' + osVersion[5:] + '; is this correct [y|n|q]: ')
            response = response.strip().lower()
            if not (response == 'y' or response == 'n' or response == 'q'):
                debugLogger.error("An invalid entry for the upgrade '[y|n|q]' was made: " + response + '.')
                print 'An invalid entry was provided; please try again.\n'
                continue
            else:
                if response == 'y':
                    validOS = True
                elif response == 'n':
                    validOS = False
                else:
                    debugLogger.info('Upgrade was cancelled while selecting the OS to upgrade to.')
                    exit(0)
                break

        if validOS:
            osUpgradeVersion = osVersion[5:]
            debugLogger.info('The choice to upgrade to ' + osUpgradeVersion + ' was made.')
            break
        else:
            continue

    return osUpgradeVersion


def getOriginalRPMList(upgradeWorkingDir):
    originalRPMListDir = upgradeWorkingDir + '/originalRPMList'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Saving the original RPM list before the server is upgraded.')
    print GREEN + 'Saving the original RPM list before the server is upgraded.' + RESETCOLORS
    try:
        os.mkdir(originalRPMListDir)
    except OSError as err:
        debugLogger.error("Unable to create the original RPM list directory '" + originalRPMListDir + "'.\n" + str(err))
        print RED + "Unable to create the original RPM list directory '" + originalRPMListDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    command = "rpm -qa --queryformat '%{NAME}\n' > " + originalRPMListDir + '/beforeUpgradeRPMList'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Failed to get the server's original RPM list.\n" + err + '\n' + out)
        debugLogger.info("The command used to get the server's original RPM list was: " + command)
        print RED + "Failed to get the server's original RPM list; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    logger.info('Done saving the original RPM list before the server is upgraded.')


def removeRear():
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Removing the rear package, since a new version will be installed during the upgrade.')
    print GREEN + 'Removing the rear package, since a new version will be installed during the upgrade.' + RESETCOLORS
    command = "rpm -qa rear* --queryformat '%{NAME}\n'"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to get the list of rear packages installed.\n' + err + '\n' + out)
        debugLogger.info('The command used to get the list of rear packages installed was: ' + command)
        print RED + 'Failed to get the list of rear packages installed; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    rearPackageList = out.splitlines()
    if len(rearPackageList) != 0:
        for package in rearPackageList:
            command = 'rpm -e yast2-rear ' + package
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Failed to remove the rear package '" + package + "'.\n" + err + '\n' + out)
                debugLogger.info("The command used to remove the rear package '" + package + '\\ was: ' + command)
                print RED + "Failed to remove the rear package '" + package + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

    logger.info('Done removing the rear package, since a new version will be installed during the upgrade.')


def disableMultiversionSupport():
    timestamp = datetime.datetime.now().strftime('%d%H%M%S%b%Y')
    zyppConfigurationFile = '/etc/zypp/zypp.conf'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Disabling kernel multiversion support before the server is upgraded.')
    print GREEN + 'Disabling kernel multiversion support before the server is upgraded.' + RESETCOLORS
    try:
        shutil.copy(zyppConfigurationFile, zyppConfigurationFile + '.SAVED.' + timestamp)
    except IOError as err:
        debugLogger.error("Unable to backup the zypper configuration file to '" + zyppConfigurationFile + '.SAVED.' + timestamp + "'.\n" + str(err))
        print RED + 'Unable to make a backup of the zypper configuration file; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    command = 'egrep -m 1 "^\\s*multiversion\\s*=\\s*" ' + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    debugLogger.info('The output of ' + command + ' was:\n' + out + '\n' + err)
    if result.returncode == 0:
        command = "sed -i 's/^\\s*multiversion\\s*=\\s*.*$/#" + out + "/' " + zyppConfigurationFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Unable to disable kernel multiversion support.\n' + err + '\n' + out)
            debugLogger.info('The command used to disable kernel multiversion support was: ' + command)
            print RED + 'Unable to disable kernel multiversion support; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    command = 'egrep -m 1 "^\\s*multiversion.kernels\\s*=\\s*" ' + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    debugLogger.info('The output of ' + command + ' was:\n' + out + '\n' + err)
    if result.returncode == 0:
        command = "sed -i 's/^\\s*multiversion.kernels\\s*=\\s*.*$/#" + out + "/' " + zyppConfigurationFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Unable to disable kernel multiversion support.\n' + err + '\n' + out)
            debugLogger.info('The command used to disable kernel multiversion support was: ' + command)
            print RED + 'Unable to disable kernel multiversion support; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    logger.info('Done disabling kernel multiversion support before the server is upgraded.')


def checkClusterStatus():
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking the Serviceguard NFS cluster status.')
    print GREEN + 'Checking the Serviceguard NFS cluster status.' + RESETCOLORS
    command = 'cmviewcl -f line -l cluster'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to determine the cluster's status.\n" + err + '\n' + out)
        debugLogger.info("The command used to determine the cluster's status was: " + command)
        print RED + "Unable to determine the cluster's status; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    if re.match('.*status\\s*=\\s*up', out, re.MULTILINE | re.DOTALL) != None:
        debugLogger.error("The cluster's status is up.\n" + out)
        debugLogger.info("The command used to determine the cluster's status was: " + command)
        print RED + "The cluster's status is up; it needs to be shutdown; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    logger.info('Done checking the Serviceguard NFS cluster status.')
    return


def removeServiceguardExtras(extraServiceguardPackages):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Removing Servicguard extras.')
    print GREEN + 'Removing Servicguard extras.' + RESETCOLORS
    serviceguardRPMList = extraServiceguardPackages.split(',')
    for rpm in serviceguardRPMList:
        errorString = 'package ' + rpm + ' is not installed'
        command = 'rpm -q ' + rpm
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0 and out.strip() != errorString:
            debugLogger.error('Unable to determine if ' + rpm + ' is installed.\n' + err + '\n' + out)
            debugLogger.info('The command used to determine if ' + rpm + ' is installed was: ' + command)
            print RED + 'Unable to determine if ' + rpm + ' is installed; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        elif out.strip() == errorString:
            continue
        else:
            serviceguardRPM = out.strip()
            command = 'rpm -e ' + serviceguardRPM
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('Unable to remove ' + serviceguardRPM + '.\n' + err + '\n' + out)
                debugLogger.info('The command used to remove ' + serviceguardRPM + ' was: ' + command)
                print RED + 'Unable to remove ' + serviceguardRPM + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

    logger.info('Done removing Servicguard extras.')


def stageServiceguardRPMS(programParentDir, upgradeWorkingDir, osVersion, serviceguardRPMS):
    rpmCopyList = []
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Getting the Serviceguard RPMs needed for the post-upgrade.')
    print GREEN + 'Getting the Serviceguard RPMs needed for the post-upgrade.' + RESETCOLORS
    serviceguardRPMDict = dict(((x.split(':')[0].strip(), x.split(':')[1].strip()) for x in serviceguardRPMS.split(',')))
    debugLogger.info('The Serviceguard RPM dictionary is: ' + str(serviceguardRPMDict))
    for rpm in serviceguardRPMDict:
        rpmDataList = serviceguardRPMDict[rpm].split('|')
        command = 'rpm -q --queryformat=%{buildtime} ' + rpm
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            if 'is not installed' in out:
                rpmCopyList.append(rpmDataList[1])
            else:
                debugLogger.error('Unable to get the build time for ' + rpm + '.\n' + err + '\n' + out)
                debugLogger.info('The command used to get the build time for ' + rpm + ' was: ' + command)
                print RED + 'Unable to get the build time for ' + rpm + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
        rpmBuildTime = out.strip()
        debugLogger.info('The build time for ' + rpm + ' was determined to be: ' + rpmBuildTime + '.')
        if int(rpmBuildTime) < int(rpmDataList[0]):
            rpmCopyList.append(rpmDataList[1])
        else:
            debugLogger.info('The ' + rpm + ' RPM is not being staged, since the installed RPM is current enough.')

    serviceguardRPMDir = programParentDir + '/serviceguardRPMS/' + osVersion
    serviceguardRPMSDir = upgradeWorkingDir + '/serviceguardRPMS'
    if len(rpmCopyList) > 0:
        try:
            os.mkdir(serviceguardRPMSDir)
        except OSError as err:
            debugLogger.error("Unable to create the Serviceguard RPMs directory '" + serviceguardRPMSDir + "'.\n" + str(err))
            print RED + 'Unable to create the Serviceguard RPMs directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

        for rpm in rpmCopyList:
            command = 'cp ' + serviceguardRPMDir + '/' + rpm + ' ' + serviceguardRPMSDir
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to copy the Serviceguard RPM from '" + serviceguardRPMDir + "' to '" + serviceguardRPMSDir + "'.\n" + err + '\n' + out)
                debugLogger.info("The command used to copy the Serviceguard RPM to the Serviceguard RPMS directory was: '" + command + "'.")
                print RED + 'Unable to copy the Serviceguard RPM to the Serviceguard RPMS directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            time.sleep(0.5)

    else:
        debugLogger.info('There were no Serviceguard packages that needed to be updated.')
    logger.info('Done getting the Serviceguard RPMs needed for the post-upgrade.')


def checkForMellanox(programParentDir, upgradeWorkingDir, osDist, osDistLevel):
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
    command = 'lspci -mvv'
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

    if mellanoxPresent:
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


def prepareFstab(upgradeWorkingDir):
    fstabDir = upgradeWorkingDir + '/fstabFile'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Preparing /etc/fstab for the upgrade.')
    print GREEN + 'Preparing /etc/fstab for the upgrade.' + RESETCOLORS
    try:
        os.mkdir(fstabDir)
        shutil.copy2('/etc/fstab', fstabDir)
    except OSError as err:
        debugLogger.error("Unable to create the fstab backup directory '" + fstabDir + "'.\n" + str(err))
        print RED + "Unable to create the fstab backup directory '" + fstabDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    except IOError as err:
        debugLogger.error("Unable to copy the fstab to '" + fstabDir + "'.\n" + str(err))
        print RED + "Unable to copy the fstab to '" + fstabDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    command = "sed -i '\\@^\\s*[^#].*/hana/@d;\\@^\\s*[^#].*/usr/sap@d' /etc/fstab"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to remove mount points for SAP HANA from /etc/fstab.\n' + err + '\n' + out)
        debugLogger.info("The command used to remove mount points for SAP HANA from /etc/fstab was: '" + command + "'.")
        print RED + 'Failed to remove mount points for SAP HANA from /etc/fstab; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done preparing /etc/fstab for the upgrade.')