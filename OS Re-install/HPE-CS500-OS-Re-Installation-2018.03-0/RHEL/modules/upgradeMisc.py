# Embedded file name: ./modules/upgradeMisc.py
import math
import subprocess
import re
import os
import datetime
import time
import logging
import shutil
import glob
RED = '\x1b[31m'
GREEN = '\x1b[32m'
YELLOW = '\x1b[33m'
RESETCOLORS = '\x1b[0m'

def checkDiskspace(backupItemsList):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking to ensure that there is enough disk space for the backup and the backup ISO image and that the overall restoration backup does not exceed 3GB.')
    print GREEN + 'Checking to ensure that there is enough disk space for the backup and the backup ISO image and that the overall backup archive does not exceed 3GB.' + RESETCOLORS
    command = 'df /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    if result.returncode != 0:
        logger.error("Unable to get the root file system's usage information.\n" + err + '\n' + out)
        print RED + "Unable to get the root file system's usage information; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    try:
        tmpVar = re.match('(.*\\s+){3}([0-9]+)\\s+', out).group(2)
    except AttributeError as err:
        logger.error("There was a match error when trying to match against '" + out + "'.\n" + str(err))
        print RED + "There was a match error when trying to match against '" + out + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    availableDiskSpace = int(math.floor(float(tmpVar) / float(1048576)))
    if len(backupItemsList) == 3:
        backupItems = ' '.join(backupItemsList[0]) + ' ' + ' '.join(backupItemsList[1]) + ' ' + ' '.join(backupItemsList[2])
        restorationItems = ' '.join(backupItemsList[0]) + ' ' + ' '.join(backupItemsList[1])
    else:
        backupItems = ' '.join(backupItemsList[0]) + ' ' + ' '.join(backupItemsList[1])
        restorationItems = ' '.join(backupItemsList[0])
    backupList = [backupItems, restorationItems]
    count = 0
    for items in backupList:
        command = 'du -BG -sc ' + items
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            if re.search('No such file or directory', err, re.MULTILINE | re.DOTALL) == None:
                logger.error("Could not get the total disk space used by '" + items + "'.\n" + err + '\n' + out)
                print RED + 'Could not get the total disk space used by the directories/files being backed up; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
        if re.match('.*\\s+([0-9]+)G\\s+total', out, re.DOTALL | re.IGNORECASE | re.MULTILINE) != None:
            try:
                if count == 0:
                    totalUsed = int(re.match('.*\\s+([0-9]+)G\\s+total', out, re.DOTALL | re.IGNORECASE | re.MULTILINE).group(1)) * 2 + 0.2
                else:
                    totalUsed = int(re.match('.*\\s+([0-9]+)G\\s+total', out, re.DOTALL | re.IGNORECASE | re.MULTILINE).group(1))
            except AttributeError as err:
                logger.error("There was a match error when trying to match against '" + out + "'.\n" + str(err))
                print RED + "There was a match error when trying to match against '" + out + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

        else:
            logger.error("Could not get the total disk space used by '" + items + "'.\n" + out)
            print RED + 'Could not get the total disk space used by the directories/files being backed up; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        if count == 0:
            if availableDiskSpace - totalUsed < 3:
                logger.error("There is not enough disk space to make a backup of '" + items + "'; available disk space '" + str(availableDiskSpace) + "' minus backup total '" + str(totalUsed) + "' used is less than 3GB.")
                print RED + 'There is not enough disk space to make a backup of the directories/files being backed up; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
        elif totalUsed > 3:
            logger.error("The current size '" + str(totalUsed) + "'GB of the restoration backup of '" + items + "' exceeds 3GB.")
            print RED + 'The current size of the restoration backup to be saved to the restoration ISO exceeds 3GB; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        count += 1

    logger.info('Done checking to ensure that there is enough disk space for the backup and the backup ISO image and that the overall restoration backup does not exceed 3GB.')
    return


def createNetworkInformationFile(upgradeWorkingDir, osDist):
    nicDataFileDir = upgradeWorkingDir + '/nicDataFile'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Creating the NIC MAC address cross reference file that will be used for reference after the upgrade.')
    print GREEN + 'Creating the NIC MAC address cross reference file that will be used for reference after the upgrade.' + RESETCOLORS
    if not os.path.exists(nicDataFileDir):
        try:
            os.mkdir(nicDataFileDir)
        except OSError as err:
            logger.error("Unable to create the NIC MAC address cross reference data directory '" + nicDataFileDir + "'.\n" + str(err))
            print RED + "Unable to create the NIC MAC address cross reference data directory '" + nicDataFileDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    command = 'ifconfig -a'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Unable to get NIC card information.\n' + err + '\n' + out)
        print RED + 'Unable to get NIC card information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    nicDataList = out.splitlines()
    nicDict = {}
    for data in nicDataList:
        if 'HWaddr' in data and 'bond' not in data:
            try:
                nicList = re.match('\\s*([a-z0-9]+)\\s+.*HWaddr\\s+([a-z0-9:]+)', data, re.IGNORECASE).groups()
            except AttributeError as err:
                logger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                print RED + "There was a match error when trying to match against '" + data + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

            nicName = nicList[0]
            nicMACAddress = nicList[1].lower()
            nicDict[nicMACAddress] = nicName

    logger.info('The NIC dictionary was determined to be: ' + str(nicDict) + '.')
    procBondingDir = '/proc/net/bonding'
    if os.path.isdir(procBondingDir):
        command = 'ls ' + procBondingDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to get the network bond information from '" + procBondingDir + "'.\n" + err + '\n' + out)
            print RED + "Unable to get the network bond information from '" + procBondingDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        activeBondsList = out.strip().split()
        for bondName in activeBondsList:
            command = 'cat ' + procBondingDir + '/' + bondName
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Unable to get network bond information for '" + bondName + "' from proc.\n" + err + '\n' + out)
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

        logger.info('The updated NIC dictionary was determined to be: ' + str(nicDict) + '.')
        if osDist == 'RHEL':
            updateNICCfgFiles(nicDict)
    else:
        logger.info("It was determined that there were no active network bonds, since '" + procBondingDir + "' did not exist.")
    try:
        macAddressDataFile = nicDataFileDir + '/macAddressData.dat'
        f = open(macAddressDataFile, 'w')
        for macAddress in nicDict:
            f.write(nicDict[macAddress] + '|' + macAddress + '\n')

    except IOError as err:
        logger.error("Could not write NIC card mac address information to '" + macAddressDataFile + "'.\n" + str(err))
        print RED + "Could not write NIC card mac address information to '" + macAddressDataFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    f.close()
    logger.info('Done creating the NIC MAC address cross reference file that will be used for reference after the upgrade.')


def updateNICCfgFiles(nicDict):
    logger = logging.getLogger('coeOSUpgradeLogger')
    for macAddress in nicDict:
        nicCFGFile = '/etc/sysconfig/network-scripts/ifcfg-' + nicDict[macAddress]
        if os.path.exists(nicCFGFile):
            command = 'egrep "^\\s*HWADDR" ' + nicCFGFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.info("The output of the command '" + command + "' used to get the NIC's MAC address variable 'HWADDR' from '" + nicCFGFile + "' was: " + out.strip() + '.')
            if result.returncode != 0:
                logger.info("Updating '" + nicCFGFile + "' with the NIC's MAC address, since it was not present.")
                command = "echo 'HWADDR=" + macAddress + "' >> " + nicCFGFile
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    logger.error("Problems were encountered while updating '" + nicCFGFile + "' with the NIC's MAC address information.\n" + err + '\n' + out)
                    print RED + "Problems were encountered while updating '" + nicCFGFile + "' with the NIC's MAC address information; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)


def checkRHELNetworkConfiguration(programParentDir, osDist, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking the network configuration.')
    cursesThread.insertMessage(['informative', 'Checking the network configuration.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'systemctl stop network'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while shutting down the network.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while shutting down the network; thus the network configuration was not confirmed.'
        return errorMessage
    time.sleep(15.0)
    if os.path.isfile(programParentDir + '/nicDataFile/pci.ids'):
        errorMessage = configureMellanox(programParentDir)
        if len(errorMessage) != 0:
            return errorMessage
    command = 'modprobe -r tg3'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while unloading the tg3 driver.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while unloading the tg3 driver; thus the network configuration was not confirmed.'
        return errorMessage
    time.sleep(2.0)
    command = 'modprobe tg3'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while reloading the tg3 driver.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while reloading the tg3 driver; thus the network configuration was not confirmed.'
        return errorMessage
    time.sleep(2.0)
    command = 'ifconfig -a'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Unable to get NIC card information.\n' + err + '\n' + out)
        errorMessage = 'Unable to get NIC card information; thus the network configuration was not confirmed.'
        return errorMessage
    nicDataList = out.splitlines()
    nicDict = {}
    count = 0
    skip = False
    for data in nicDataList:
        if 'flags=' in data:
            if 'lo:' in data or not 'bond' in data:
                try:
                    nicName = re.match('\\s*([a-z0-9]+):', data, re.IGNORECASE).group(1)
                    count += 1
                except AttributeError as err:
                    logger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                    errorMessage = "There was a match error when trying to match against '" + data + "'; thus the network configuration was not confirmed."
                    return errorMessage

            elif 'flags=' in data and 'bond' in data:
                skip = True
            elif 'ether' in data and 'txqueuelen' in data and not skip:
                try:
                    nicMACAddress = re.match('\\s*ether\\s+([a-z0-9:]+)', data, re.IGNORECASE).group(1)
                    count += 1
                except AttributeError as err:
                    logger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                    errorMessage = "There was a match error when trying to match against '" + data + "'; thus the network configuration was not confirmed."
                    return errorMessage

            elif 'ether' in data and 'txqueuelen' in data:
                skip = False
            else:
                continue
            nicDict[nicMACAddress] = count == 2 and nicName
            count = 0

    logger.info('The NIC dictionary was determined to be: ' + str(nicDict) + '.')
    try:
        macAddressDataFile = programParentDir + '/nicDataFile/macAddressData.dat'
        with open(macAddressDataFile) as f:
            macAddressData = f.readlines()
    except IOError as err:
        logger.error("Unable to get the MAC address list from '" + macAddressDataFile + "'.\n" + str(err))
        errorMessage = "Unable to get the MAC address list from '" + macAddressDataFile + "'; thus the network configuration was not confirmed."
        return errorMessage

    macAddressDict = dict((x.strip().split('|') for x in macAddressData))
    macAddressDict = dict(map(reversed, macAddressDict.items()))
    logger.info('The MAC address dictionary (previous NIC mapping) was determined to be: ' + str(macAddressDict) + '.')
    changedNicDict = {}
    for macAddress in macAddressDict:
        currentNicName = macAddressDict[macAddress]
        try:
            previousNicName = nicDict[macAddress]
        except KeyError as err:
            logger.error('The resource key (' + str(err) + ') was not present in the previous NIC dictionary.')
            errorMessage = 'The resource key (' + str(err) + ') was not present in the previous NIC dictionary; thus the network configuration was not confirmed.'
            return errorMessage

        if currentNicName != previousNicName:
            changedNicDict[previousNicName] = currentNicName

    if len(changedNicDict) != 0:
        errorMessage = updateNICNames(changedNicDict, osDist, cursesThread)
    logger.info('Done checking the network configuration.')
    return errorMessage


def checkSLESNetworkConfiguration(programParentDir, osDist, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking the network configuration.')
    cursesThread.insertMessage(['informative', 'Checking the network configuration.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'systemctl stop network'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while shutting down the network.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while shutting down the network; thus the network configuration was not confirmed.'
        return errorMessage
    time.sleep(15.0)
    if os.path.isfile(programParentDir + '/nicDataFile/pci.ids'):
        errorMessage = configureMellanox(programParentDir)
        if len(errorMessage) != 0:
            return errorMessage
    command = 'ifconfig -a'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Unable to get NIC card information.\n' + err + '\n' + out)
        errorMessage = 'Unable to get NIC card information; thus the network configuration was not confirmed.'
        return errorMessage
    nicDataList = out.splitlines()
    nicDict = {}
    for data in nicDataList:
        if 'HWaddr' in data:
            try:
                nicList = re.match('\\s*([a-z0-9]+)\\s+.*HWaddr\\s+([a-z0-9:]+)', data, re.IGNORECASE).groups()
            except AttributeError as err:
                logger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                errorMessage = "There was a match error when trying to match against '" + data + "'; thus the network configuration was not confirmed."
                return errorMessage

            nicDict[nicList[1].lower()] = nicList[0]

    logger.info('The NIC dictionary was determined to be: ' + str(nicDict) + '.')
    try:
        macAddressDataFile = programParentDir + '/nicDataFile/macAddressData.dat'
        with open(macAddressDataFile) as f:
            macAddressData = f.readlines()
    except IOError as err:
        logger.error("Unable to get the MAC address list from '" + macAddressDataFile + "'.\n" + str(err))
        errorMessage = "Unable to get the MAC address list from '" + macAddressDataFile + "'; thus the network configuration was not confirmed."
        return errorMessage

    macAddressDict = dict((x.strip().split('|') for x in macAddressData))
    macAddressDict = dict(map(reversed, macAddressDict.items()))
    logger.info('The MAC address dictionary (previous NIC mapping) was determined to be: ' + str(macAddressDict) + '.')
    changedNicDict = {}
    for macAddress in macAddressDict:
        currentNicName = macAddressDict[macAddress]
        previousNicName = nicDict[macAddress]
        if currentNicName != previousNicName:
            changedNicDict[previousNicName] = currentNicName

    if len(changedNicDict) != 0:
        errorMessage = updateNICNames(changedNicDict, osDist, cursesThread)
    logger.info('Done checking the network configuration.')
    return errorMessage


def updateNICNames(changedNicDict, osDist, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Updating the network configuration, since the NIC names changed.')
    cursesThread.insertMessage(['informative', 'Updating the network configuration, since the NIC names changed.'])
    cursesThread.insertMessage(['informative', ''])
    logger.info('The changed NIC dictionary was determined to be: ' + str(changedNicDict) + '.')
    networkCfgFileList = []
    if osDist == 'SLES':
        networkDir = '/etc/sysconfig/network'
    else:
        networkDir = '/etc/sysconfig/network-scripts'
    try:
        os.chdir(networkDir)
    except OSError as err:
        logger.error("Unable to change into the network directory '" + networkDir + "'.\n" + str(err))
        errorMessage = "Unable to change into the network directory '" + networkDir + "'; thus the network configuration was not confirmed."
        return errorMessage

    command = 'ls ifcfg-*'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while getting a listing of the NIC configuration files.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while getting a listing of the NIC configuration files; thus the network configuration was not confirmed.'
        return errorMessage
    nicCfgFileList = out.splitlines()
    logger.info('The NIC configuration files were determined to be: ' + str(nicCfgFileList) + '.')
    tmpNicNameDict = dict(((nic.strip().replace('ifcfg-', ''), nic.strip()) for nic in nicCfgFileList))
    nicNameDict = {}
    for key in tmpNicNameDict:
        if '.' not in key and key != 'lo':
            nicNameDict[key] = tmpNicNameDict[key]
            networkCfgFileList.append(tmpNicNameDict[key])

    logger.info('The NIC name dictionary was determined to be: ' + str(nicNameDict) + '.')
    logger.info('The NIC configuration file list was determined to be: ' + str(networkCfgFileList) + '.')
    command = ''
    if osDist == 'SLES':
        if glob.glob('ifroute-*'):
            command = 'ls ifroute-*'
    elif glob.glob('route-*'):
        command = 'ls route-*'
    routeNicNameDict = {}
    if not command == '':
        logger.info("The command used to get the list of NIC specific route configuration files was: '" + command + "'.")
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Problems were encountered while getting a listing of the NIC specific route configuration files.\n' + err + '\n' + out)
            errorMessage = 'Problems were encountered while getting a listing of the NIC specific route configuration files; thus the network configuration was not confirmed.'
            return errorMessage
        routeCfgFileList = out.splitlines()
        logger.info('The route configuration file list was determined to be: ' + str(routeCfgFileList) + '.')
        if osDist == 'SLES':
            tmpRouteNicNameDict = dict(((route.strip().replace('ifroute-', ''), route.strip()) for route in routeCfgFileList))
        else:
            tmpRouteNicNameDict = dict(((route.strip().replace('route-', ''), route.strip()) for route in routeCfgFileList))
        for key in tmpRouteNicNameDict:
            if '.' not in key and key != 'lo':
                routeNicNameDict[key] = tmpRouteNicNameDict[key]
                networkCfgFileList.append(tmpRouteNicNameDict[key])

    if len(routeNicNameDict) > 0:
        logger.info('The route name dictionary was determined to be: ' + str(routeNicNameDict) + '.')
    for nicName in changedNicDict:
        previousNICName = changedNicDict[nicName]
        command = "sed -i 's/" + previousNICName + '/' + nicName + "/g' " + ' '.join(networkCfgFileList)
        logger.info("The command used to update the NIC configuration files with the new NIC name was: '" + command + "'.")
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Problems were encountered while updating the configuration files with the new NIC name '" + nicName + "'.\n" + err + '\n' + out)
            errorMessage = "Problems were encountered while updating the configuration files with the new NIC name '" + nicName + "'; thus the network configuration was not confirmed."
            return errorMessage
        if previousNICName in nicNameDict:
            command = 'mv ' + nicNameDict[previousNICName] + ' ifcfg-' + nicName
            logger.info("The command used to move the NIC configuration file '" + nicNameDict[previousNICName] + "' to its new name was: '" + command + "'.")
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Problems were encountered while moving '" + nicNameDict[previousNICName] + "' to 'ifcfg-" + nicName + "'.\n" + err + '\n' + out)
                errorMessage = "Problems were encountered while moving '" + nicNameDict[previousNICName] + "' to 'ifcfg-" + nicName + "'; thus the network configuration was not confirmed."
                return errorMessage
            networkCfgFileList.remove(nicNameDict[previousNICName])
        if previousNICName in routeNicNameDict:
            if osDist == 'SLES':
                newRouteFileName = 'ifroute-' + nicName
            else:
                newRouteFileName = 'route-' + nicName
            command = 'mv ' + routeNicNameDict[previousNICName] + ' ' + newRouteFileName
            logger.info('The command used to move the NIC route configuration file ' + routeNicNameDict[previousNICName] + "' to its new name was: '" + command + "'.")
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Problems were encountered while moving '" + routeNicNameDict[previousNICName] + "' to '" + newRouteFileName + "'.\n" + err + '\n' + out)
                errorMessage = "Problems were encountered while moving '" + routeNicNameDict[previousNICName] + "' to '" + newRouteFileName + "'; thus the network configuration was not confirmed."
                return errorMessage
            networkCfgFileList.remove(routeNicNameDict[previousNICName])

    logger.info('Done updating the network configuration, since the NIC names changed.')
    return errorMessage


def setHostname(programParentDir, cursesThread):
    errorMessage = ''
    hostnameFile = programParentDir + '/hostnameData/hostname'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Setting the server's hostname.")
    cursesThread.insertMessage(['informative', "Setting the server's hostname."])
    cursesThread.insertMessage(['informative', ''])
    try:
        f = open(hostnameFile, 'r')
        hostname = f.readline()
    except IOError as err:
        logger.error("Problems were encountered while reading the server's hostname from '" + hostnameFile + "'.\n" + str(err))
        errorMessage = "Problems were encountered while reading the server's hostname from '" + hostnameFile + "'; thus the server's hostname was not set."
        return errorMessage

    command = 'hostnamectl set-hostname ' + hostname
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Problems were encountered while setting the server's hostname '" + hostname + "'.\n" + err + '\n' + out)
        errorMessage = "Problems were encountered while setting the server's hostname '" + hostname + "'; thus the server's hostname was not set."
        return errorMessage
    logger.info("Done setting the server's hostname.")
    return errorMessage


def updateNTPConf(cursesThread):
    errorMessage = ''
    ntpConfigurationFile = '/etc/ntp.conf'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Checking and updating ntp's controlkey setting if necessary.")
    cursesThread.insertMessage(['informative', "Checking and updating ntp's controlkey setting if necessary."])
    cursesThread.insertMessage(['informative', ''])
    command = 'egrep "^\\s*keys" ' + ntpConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to get the keys resource from ' + ntpConfigurationFile + ' was: ' + out.strip() + '.')
    if result.returncode == 0:
        command = 'egrep "^\\s*controlkey\\s+[0-9]+\\s*.*" ' + ntpConfigurationFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to get the controlkey resource from ' + ntpConfigurationFile + ' was: ' + out.strip() + '.')
        if result.returncode == 0:
            command = "sed -ri '0,/^\\s*controlkey\\s+[0-9]+\\s*.*/s//controlkey 1/' " + ntpConfigurationFile
        else:
            command = "sed -i 's/^\\s*keys.*/&\\ncontrolkey 1/' " + ntpConfigurationFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Problems were encountered while setting ntp's controlkey variable.\n" + err + '\n' + out)
            errorMessage = "Problems were encountered while setting ntp's controlkey variable; thus the server's ntp server was not configured."
            return errorMessage
    logger.info("Done checking and updating ntp's controlkey setting if necessary.")
    return errorMessage


def createBackup(backupList, upgradeWorkingDir, osDist):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Creating the backup archive ISO image.')
    print GREEN + 'Creating the backup archive ISO image.' + RESETCOLORS
    archiveDir = upgradeWorkingDir + '/archiveImages'
    if not os.path.isdir(archiveDir):
        try:
            os.mkdir(archiveDir)
        except OSError as err:
            logger.error("Unable to create the pre-upgrade archive directory '" + archiveDir + "'.\n" + str(err))
            print RED + "Unable to create the pre-upgrade archive directory '" + archiveDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    else:
        try:
            archiveList = os.listdir(archiveDir)
            for archive in archiveList:
                os.remove(archiveDir + '/' + archive)

        except OSError as err:
            logger.error("Unable to remove old archives in '" + archiveDir + "'.\n" + str(err))
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
        logger.info("The command used to create the '" + backupReferenceList[3] + "' tar archive was: " + command + '.')
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('A problem was encountered while creating the pre-upgrade ' + backupReferenceList[3] + " backup '" + backupReferenceList[0] + "' archive.\n" + err + '\n' + out)
            print RED + 'A problem was encountered while creating the pre-upgrade ' + backupReferenceList[3] + " backup '" + backupReferenceList[0] + "' archive; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        command = 'gzip ' + backupReferenceList[0]
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('A problem was encountered while compressing the pre-upgrade ' + backupReferenceList[3] + " backup '" + backupReferenceList[0] + "' archive.\n" + err + '\n' + out)
            print RED + 'A problem was encountered while compressing the pre-upgrade ' + backupReferenceList[3] + " backup '" + backupReferenceList[0] + "' archive; fix the problem and try again; exiting program execution." + RESETCOLORS
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
            logger.error("Unable to get the md5sum of the backup archive '" + backupReferenceList[1] + "'.\n" + err + '\n' + out)
            print RED + "Unable to get the md5sum of the backup archive '" + backupReferenceList[1] + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        count += 1

    backupISO = upgradeWorkingDir + '/' + hostname + '_Archive_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.iso'
    backupISOMd5sumFile = upgradeWorkingDir + '/' + hostname + '_Archive_Backup_For_' + osDist + '_Upgrade_' + dateTimestamp + '.md5sum'
    command = 'genisoimage -R -m *_OS_Archive_Backup_For*.* -o ' + backupISO + ' ' + upgradeWorkingDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("A problem was encountered while creating the pre-upgrade backup '" + backupISO + "' ISO image.\n" + err + '\n' + out)
        print RED + "A problem was encountered while creating the pre-upgrade backup  '" + backupISO + "' ISO image; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    command = 'md5sum ' + backupISO + ' > ' + backupISOMd5sumFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("A problem was encountered while getting the md5sum of the pre-upgrade backup '" + backupISO + "' ISO image.\n" + err + '\n' + out)
        print RED + "A problem was encountered while getting the md5sum of the pre-upgrade backup '" + backupISO + "' ISO image; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    logger.info('Done creating the backup archive ISO image.')
    return (backupISO, archiveBackupList[1])


def confirmBackupDataList(backupData):
    updatedBackupData = []
    fileRemoved = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking the backup data list to ensure the selected files/directories are present and if not removing them from the list.')
    for file in backupData:
        if glob.glob(file):
            updatedBackupData.append(file)
        else:
            logger.info('The following was removed from the backup list, since it was not present: ' + file + '.')
            fileRemoved = True

    logger.info('Done checking the backup data list to ensure the selected files/directories are present and if not removing them from the list.')
    return (updatedBackupData, fileRemoved)


def installSLESAddOnSoftware(programParentDir, cursesThread):
    errorMessage = ''
    addOnSoftwareInstalled = True
    addOnSoftwareDir = programParentDir + '/addOnSoftwareRPMS'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Installing the additional software RPMs needed for the upgrade.')
    cursesThread.insertMessage(['informative', 'Installing the additional software RPMs needed for the upgrade.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'zypper ar -G -t plaindir ' + addOnSoftwareDir + ' addOnSoftwareRPMS'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while installing the additional software RPMs.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while installing the additional software RPMs; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    command = 'zypper in -y addOnSoftwareRPMS:*'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while installing the additional software RPMs.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while installing the additional software RPMs; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    command = 'zypper rr addOnSoftwareRPMS'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while removing the additional software RPMs repository.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while removing the additional software RPMs repository; the repository will need to be removed manually.'
    logger.info('Done installing the additional software RPMs needed for the upgrade.')
    return (errorMessage, addOnSoftwareInstalled)


def installRHELAddOnSoftware(programParentDir, cursesThread):
    errorMessage = ''
    addOnSoftwareInstalled = True
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    repoDir = '/tmp/addOnSoftware_' + dateTimestamp
    addOnSoftware = programParentDir + '/addOnSoftwareRPMS'
    baseURL = 'baseurl=file://' + repoDir
    repositoryTemplate = programParentDir + '/repositoryTemplate/local.repo'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Installing the additional software RPMs needed for the upgrade.')
    cursesThread.insertMessage(['informative', 'Installing the additional software RPMs needed for the upgrade.'])
    cursesThread.insertMessage(['informative', ''])
    try:
        shutil.copytree(addOnSoftware, repoDir)
    except OSError as err:
        logger.error("Problems were encountered while copying the additional software RPMs to '" + repoDir + "'.\n" + str(err))
        errorMessage = 'Problems were encountered while copying the additional software RPMs to the repository; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)

    command = 'createrepo ' + repoDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while creating the additional software RPMs repository.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while creating the additional software RPMs repository; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    try:
        shutil.copy2(repositoryTemplate, '/etc/yum.repos.d')
    except IOError as err:
        logger.error('Problems were encountered while copying the additional software RPMs repository template into place.\n' + str(err))
        errorMessage = 'Problems were encountered while copying the additional software RPMs repository template into place; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)

    command = "sed -ri 's|^\\s*baseurl=file://.*|" + baseURL + "|' /etc/yum.repos.d/local.repo"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while updating the additional software RPMs repository template.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while updating the additional software RPMs repository; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    command = 'yum --disablerepo="*" --enablerepo="local" -y install \\*'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while installing the additional software RPMs.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while installing the additional software RPMs; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    try:
        os.remove('/etc/yum.repos.d/local.repo')
        shutil.rmtree(repoDir)
    except OSError as err:
        logger.error('Problems were encountered while removing the additional software RPMs repository.\n' + str(err))
        errorMessage = 'Problems were encountered while removing the additional software RPMs repository; the RPMs repository will need to be removed manually.'

    logger.info('Done installing the additional software RPMs needed for the upgrade.')
    return (errorMessage, addOnSoftwareInstalled)


def disableMultipathd(cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Disabling multipathd, since the server is not part of a CS500 Scale-out system.')
    cursesThread.insertMessage(['informative', 'Disabling multipathd, since the server is not part of a CS500 Scale-out system.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'systemctl disable multipathd'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while disabling multipathd.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while disabling multipathd.'
        return errorMessage
    logger.info('Done disabling multipathd, since the server is not part of a CS500 Scale-out system.')
    return errorMessage


def extractOSRestorationArchive(osRestorationArchive, osRestorationArchiveErrorFile, cursesThread):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Extracting the OS restoration archive image.')
    command = 'tar -zxf ' + osRestorationArchive + ' -C /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info("The command used to extract the OS restoration archive was: '" + command + "'.")
    if result.returncode != 0:
        logger.error("There was a problem extracting the OS restoration archive '" + osRestorationArchive + "'.\n" + err + '\n' + out)
        updateOSRestorationArchiveErrorFile(restorationArchiveErrorFile, cursesThread)
        displayErrorMessage("There was a problem extracting the os restoration archive '" + osRestorationArchive + "'; fix the problem and try again.", cursesThread)
    logger.info('Done extracting the OS restoration archive image.')


def checkOSRestorationArchive(programParentDir, osRestorationArchiveErrorFile, osDist, cursesThread):
    osRestorationArchiveFile = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking the OS restoration archive to make sure it is not corrupt.')
    osArchiveFileRegex = re.compile('.*_OS_Restoration_Backup_For_' + osDist + '_Upgrade_[0-9]{6}[A-Za-z]{3}[0-9]{4}.tar.gz')
    archiveImageDir = programParentDir + '/archiveImages'
    command = 'ls ' + archiveImageDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Unable to get a listing of the files in '" + archiveImageDir + "'.\n" + err + '\n' + out)
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("Unable to get a listing of the files in '" + archiveImageDir + "'; fix the problem and try again.", cursesThread)
    fileList = out.splitlines()
    osRestorationArchiveFound = False
    for file in fileList:
        if re.match(osArchiveFileRegex, file):
            md5sumFile = re.sub('tar.gz', 'md5sum', file)
            osRestorationArchiveFile = archiveImageDir + '/' + file
            osRestorationArchiveMd5sumFile = archiveImageDir + '/' + md5sumFile
            osRestorationArchiveFound = True
            break

    if not osRestorationArchiveFound:
        logger.error("The OS restoration archive '" + archiveImageDir + '/' + osArchiveFileRegex.pattern + "' could not be found.")
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("The OS restoration archive '" + archiveImageDir + '/' + osArchiveFileRegex.pattern + "' could not be found; fix the problem and try again.", cursesThread)
    if not os.path.isfile(osRestorationArchiveMd5sumFile):
        logger.error("The OS restoration archive's md5sum file '" + osRestorationArchiveMd5sumFile + "' is missing.")
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("The OS restoration archive's md5sum file '" + osRestorationArchiveMd5sumFile + "' is missing; fix the problem and try again.", cursesThread)
    command = 'md5sum ' + osRestorationArchiveFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Unable to determine the md5sum of the OS restoration archive '" + osRestorationArchiveFile + "'.\n" + err + '\n' + out)
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("Unable to determine the md5sum of the OS restoration archive '" + osRestorationArchiveFile + "'; fix the problem and try again.", cursesThread)
    try:
        osRestorationArchiveMd5sum = re.match('([0-9,a-f]*)\\s+', out).group(1)
    except AttributeError as err:
        logger.error('There was a match error when trying to match against ' + out + '.\n' + str(err))
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("There was a match error when matching against '" + out + "'; fix the problem and try again.", cursesThread)

    try:
        with open(osRestorationArchiveMd5sumFile) as f:
            for line in f:
                line = line.strip()
                if file in line:
                    originalOSRestorationArchiveMd5sum = re.match('([0-9,a-f]*)\\s+', line).group(1)

    except IOError as err:
        logger.error("Unable to get the md5sum of the OS restoration archive from '" + osRestorationArchiveMd5sumFile + "'.\n" + str(err))
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("Unable to get the md5sum of the OS restoration archive from '" + osRestorationArchiveMd5sumFile + "'; fix the problem and try again.", cursesThread)
    except AttributeError as err:
        logger.error("There was a match error when trying to match against '" + line + "'.\n" + str(err))
        updateOSestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("There was a match error when matching against '" + line + "'; fix the problem and try again.", cursesThread)

    if osRestorationArchiveMd5sum != originalOSRestorationArchiveMd5sum:
        logger.error("The OS restoration archive '" + osRestorationArchiveFile + "' is corrupt; its md5sum does not match its md5sum in '" + osRestorationArchiveMd5sumFile + "'.")
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("The OS restoration archive '" + osRestorationArchiveFile + "' is corrupt; fix the problem and try again.", cursesThread)
    logger.info('Done checking the OS restoration archive to make sure it is not corrupt.')
    return osRestorationArchiveFile


def updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile, cursesThread):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Updating the OS restoration archive error file with an archive failure attempt.')
    try:
        f = open(osRestorationArchiveErrorFile, 'a')
        if os.stat(osRestorationArchiveErrorFile).st_size == 0:
            f.write('First Attempt Failed\n')
        elif os.stat(osRestorationArchiveErrorFile).st_size < 25:
            f.write('Second Attempt Failed\n')
        elif os.stat(osRestorationArchiveErrorFile).st_size < 45:
            f.write('Third Attempt Failed\n')
    except IOError as err:
        logger.error('Could not write to the OS restoration archive error file ' + osRestorationArchiveErrorFile + '.\n' + str(err))
        displayErrorMessage("Could not write to the OS restoration archive error file '" + osRestorationArchiveErrorFile + "'; fix the problem and try again.", cursesThread)

    f.close()
    logger.info('Done updating the restoration archive error file with an archive failure attempt.')


def displayErrorMessage(message, cursesThread):
    cursesThread.insertMessage(['error', message])
    cursesThread.insertMessage(['informative', ''])
    cursesThread.getUserInput(['error', 'Press enter to exit and try again.'])
    cursesThread.insertMessage(['informative', ''])
    while not cursesThread.isUserInputReady():
        time.sleep(0.1)

    exit(1)


def stageAddOnRPMS(programParentDir, upgradeWorkingDir, serverModel, osDist):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Copying the additional RPMs needed for the post-upgrade to the pre-upgrade working directory.')
    if 'DL380' in serverModel or 'DL360' in serverModel:
        if osDist == 'SLES':
            addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/SGLX/SLES'
        else:
            addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/SGLX/RHEL'
    elif 'DL320' in serverModel:
        if osDist == 'SLES':
            addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/SGeSAP/SLES'
        else:
            addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/SGeSAP/RHEL'
    elif 'DL580' in serverModel:
        if osDist == 'SLES':
            addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/CS500/SLES'
        else:
            addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/CS500/RHEL'
    elif osDist == 'SLES':
        addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/CS900/SLES'
    else:
        addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/CS900/RHEL'
    addOnSoftwareRPMSDir = upgradeWorkingDir + '/addOnSoftwareRPMS'
    if os.listdir(addOnSoftwareRPMDir):
        if not os.path.isdir(addOnSoftwareRPMSDir):
            try:
                os.mkdir(addOnSoftwareRPMSDir)
            except OSError as err:
                logger.error("Unable to create the additional RPMs directory '" + addOnSoftwareRPMSDir + "'.\n" + str(err))
                print RED + "Unable to create the additional RPMs directory '" + addOnSoftwareRPMSDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

        command = 'cp ' + addOnSoftwareRPMDir + '/* ' + addOnSoftwareRPMSDir
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info("The command used to copy the additional RPMs into place for the post upgrade installation was: '" + command + "'.")
        if result.returncode != 0:
            logger.error("Unable to copy the additional RPMs from '" + addOnSoftwareRPMDir + "' to '" + addOnSoftwareRPMSDir + "'.\n" + err + '\n' + out)
            print RED + "Unable to copy the additional RPMs from '" + addOnSoftwareRPMDir + "' to '" + addOnSoftwareRPMSDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
    else:
        logger.info('There were no additional RPMs present for the post-upgrade.')
    logger.info('Done copying the additional RPMs needed for the post-upgrade to the pre-upgrade working directory.')


def getMultipathConf():
    multipathConfList = []
    fibrePresent = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking to see if Fibre cards are present, which is used to determine if /etc/multipath.conf needs to be added to the restoration archive.')
    command = 'lspci'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Unable to determine if Fibre cards are present.\n' + err + '\n' + out)
        print RED + 'Unable to determine if Fibre cards are present; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if re.search('Fibre', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None:
        multipathConfList.append('/etc/multipath.conf')
        fibrePresent = True
    logger.info('Done checking to see if Fibre cards are present, which is used to determine if /etc/multipath.conf needs to be added to the restoration archive.')
    return (multipathConfList, fibrePresent)


def enableMultipathd(cursesThread, osDist, serverModel):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Enabling and starting multipathd.')
    cursesThread.insertMessage(['informative', 'Enabling and starting multipathd.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'systemctl enable multipathd'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Failed to enable multipathd.\n' + err + '\n' + out)
        errorMessage = 'Failed to enable multipathd; thus multipathd will have to be enabled and started manually.'
        return errorMessage
    else:
        command = 'systemctl start multipathd'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Failed to start multipathd.\n' + err + '\n' + out)
            errorMessage = 'Failed to start multipathd; thus multipathd will have to be enabled and started manually.'
            return errorMessage
        if serverModel == 'Superdome':
            command = 'lsblk -l'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error('Unable to get the partition information for the root file system.\n' + err + '\n' + out)
                errorMessage = 'Unable to get the root partition information; thus the multipath configuration needs to be confirmed and the initramfs will have to be built manually before rebooting.'
                return errorMessage
            count = 0
            countDict = {1: 'first',
             2: 'second',
             3: 'third'}
            while 1:
                if re.match('.*vv[0-9]+.*\\s+part\\s+.*/boot/efi.*$', out, re.DOTALL | re.MULTILINE) != None:
                    try:
                        partition = re.match('.*(vv[0-9]+).*\\s+part\\s+/boot/efi.*$', out, re.DOTALL | re.MULTILINE).group(1)
                        logger.info('The friendly name of the root partition is: ' + partition + '.')
                        break
                    except AttributeError as err:
                        logger.error('There was a match error when trying to match against\n' + out + '\n' + str(err))
                        errorMessage = 'Problems were encountered while getting the friendly name of the root partition; thus the multipath configuration needs to be confirmed and the initramfs will have to be built manually before rebooting.'
                        return errorMessage

                else:
                    if count != 0:
                        logger.warn('The ' + countDict[count] + ' attempt to set the root partition to its friendly name failed.\n' + out)
                    else:
                        logger.warn('The root partition did not have its friendly name set; will try to set it by restarting multipathd.\n' + out)
                    command = 'systemctl restart multipathd'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        logger.error('Problems were encountered while restarting multipathd.\n' + err + '\n' + out)
                        errorMessage = 'Problems were encountered while restarting multipathd; thus multipath will have to be fixed and the initramfs will have to be built manually before rebooting.'
                        return errorMessage
                    time.sleep(1.0)
                    command = 'lsblk -l'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        logger.error('Problems were encountered while getting the root file system partition information.\n' + err + '\n' + out)
                        errorMessage = 'Problems were encountered while getting the root file system partition information; thus the multipath configuration needs to be confirmed and the initramfs will have to be built manually before rebooting.'
                        return errorMessage
                    count += 1
                    if count > 3:
                        errorMessage = 'Unable to set the root partition to its friendly name; thus multipath will have to be fixed and the initramfs will have to be built manually before rebooting.'
                        return errorMessage
                    time.sleep(2.0)
                    continue

        if osDist == 'SLES':
            command = 'dracut --force --add multipath'
        else:
            command = 'dracut --force --add multipath --include /etc/multipath'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Failed to build the initramfs after enabling multipath.\n' + err + '\n' + out)
            errorMessage = 'Failed to rebuild the initramfs after enabling multipath; thus the initramfs will have to be rebuilt manually before rebooting.'
            return errorMessage
        logger.info('Done enabling and starting multipathd.')
        return errorMessage


def updateInstallCtrlFile(programParentDir, upgradeWorkingDir, processor, **kwargs):
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    cs500ScaleOut = False
    autoinstImageFile = programParentDir + '/installCtrlFiles/autoinst.img'
    autoinstImgMountPoint = '/tmp/autoinstImg_' + dateTimestamp
    installCtrlFileDir = upgradeWorkingDir + '/installCtrlFile'
    lunID = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Updating the install control file with the partition ID that will have the OS installed on it.')
    if 'cs500ScaleOut' in kwargs:
        cs500ScaleOut = True
    if cs500ScaleOut:
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/cs500-autoinst.xml'
        ctrlFile = installCtrlFileDir + '/autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/cs500-SUSE-floppy.img'
    else:
        if processor == 'ivybridge':
            installCtrlFileTemplate = programParentDir + '/installCtrlFiles/cs900-ivb_autoinst.xml'
        else:
            installCtrlFileTemplate = programParentDir + '/installCtrlFiles/cs900-hsw_autoinst.xml'
        ctrlFile = installCtrlFileDir + '/01_autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/01_autoinst.img'
    if not os.path.isdir(installCtrlFileDir):
        try:
            os.mkdir(installCtrlFileDir)
            shutil.copy2(installCtrlFileTemplate, ctrlFile)
            shutil.copy2(autoinstImageFile, ctrlFileImg)
        except OSError as err:
            logger.error("Unable to create install control file directory '" + installCtrlFileDir + "'.\n" + str(err))
            print RED + "Unable to create the install control file directory '" + installCtrlFileDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        except IOError as err:
            logger.error("Unable to copy the install control files to '" + ctrlFile + "'.\n" + str(err))
            print RED + "Unable to copy the install control files to '" + ctrlFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    if not os.path.isdir(autoinstImgMountPoint):
        try:
            os.mkdir(autoinstImgMountPoint)
        except OSError as err:
            logger.error("Unable to create mount point '" + autoinstImgMountPoint + "'.\n" + str(err))
            print RED + "Unable to create mount point '" + autoinstImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    command = 'mount -o loop -o rw ' + ctrlFileImg + ' ' + autoinstImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Unable to mount '" + ctrlFileImg + "' on '" + autoinstImgMountPoint + "'.\n" + err + '\n' + out)
        print RED + "Unable to mount '" + ctrlFileImg + "' on '" + autoinstImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    command = 'lsblk -l'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Unable to get the partition information for the root file system.\n' + err + '\n' + out)
        print RED + 'Unable to get the partition information for the root file system; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    try:
        if cs500ScaleOut:
            lunID = re.match('.*(360002ac0+.*)[_-]part.*/boot/efi.*$', out, re.DOTALL | re.MULTILINE).group(1)
        else:
            try:
                device = re.match('.*vv[0-9]+.*\\s+\\((dm-[0-9]+)\\)\\s+.*/boot/efi.*$', out, re.DOTALL | re.MULTILINE).group(1)
                command = 'find -L /dev/ -samefile /dev/' + device
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    if not 'already visited the directory' in err:
                        if not 'No such' in err:
                            logger.error("Failed to get the files linked to '/dev/" + device + "'.\n" + err + '\n' + out)
                            print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                            exit(1)
                        else:
                            logger.warn('find complained while searching for files linked to /dev/' + device + ': \n' + err + '\n' + out)
                    fileList = out.splitlines()
                    for file in fileList:
                        if '360002ac0' in file:
                            lunID = re.match('.*360002ac0+([1-9a-f]{1}).*', file).group(1)
                            break

                    lunID == '' and logger.error("Unable to identify the OS LUN ID using the device's (" + device + ') linked file list: ' + str(fileList))
                    print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)
            except AttributeError as err:
                logger.info("The first attempt to get the OS LUN ID failed to match against '" + out + "'.\n" + str(err))

            if lunID == '':
                lunID = re.match('.*360002ac0+([1-9a-f]{1}).*/boot/efi.*$', out, re.DOTALL | re.MULTILINE).group(1)
    except AttributeError as err:
        logger.error("There was a match error when trying to match against '" + out + "'.\n" + str(err))
        print RED + 'There was a match error when trying to get the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    logger.info("The OS LUN ID was determined to be '" + lunID + "'.")
    if cs500ScaleOut:
        command = "sed -i 's/OS_INST_SAN_LUN=<OS_LUN>/OS_INST_SAN_LUN=" + lunID + "/' " + ctrlFile
    else:
        command = "sed -ri '0,/^\\s*OS_DEVICE_LUN_ID=.*/s//OS_DEVICE_LUN_ID=" + lunID + "/' " + ctrlFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Unable to update '" + ctrlFile + "' with the OS LUN ID '" + lunID + "'.\n" + err + '\n' + out)
        print RED + 'Unable to update the install control file with the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    try:
        shutil.copy2(ctrlFile, autoinstImgMountPoint)
    except IOError as err:
        logger.error("Unable to copy the install control file '" + ctrlFile + "' to '" + autoinstImgMountPoint + "'.\n" + str(err))
        print RED + "Unable to copy the install control file '" + ctrlFile + "' to '" + autoinstImgMountPoint + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    command = 'umount ' + autoinstImgMountPoint
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.warn("Unable to unmount '" + autoinstImgMountPoint + "'.\n" + err + '\n' + out)
        print YELLOW + "Unable to unmount '" + autoinstImgMountPoint + "'; ." + RESETCOLORS
        exit(1)
    logger.info('Done updating the install control file with the partition ID that will have the OS installed on it.')
    return ctrlFileImg


def updateKdump(cursesThread):
    errorMessage = ''
    kdumpServiceFile = '/usr/lib/systemd/system/kdump.service'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Updating kdump.service to address bug 1008170.')
    cursesThread.insertMessage(['informative', 'Updating kdump.service to address bug 1008170.'])
    cursesThread.insertMessage(['informative', ''])
    commandList = ["sed -ri '0,/^\\s*Wants=kdump-rebuild-initrd.service/s//Requires=kdump-rebuild-initrd.service/' /usr/lib/systemd/system/kdump.service", "sed -ri '0,/^\\s*After=local-fs.target/s//After=local-fs.target kdump-rebuild-initrd.service/' /usr/lib/systemd/system/kdump.service"]
    logger.info("The list of commands used to update '" + kdumpServiceFile + "' is: " + str(commandList) + '.')
    for command in commandList:
        command = command
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Problems were encountered while updating'" + kdumpServiceFile + "'.\n" + err + '\n' + out)
            errorMessage = "Problems were encountered while updating '" + kdumpServiceFile + "'; thus the file will need to be updated manually."
            return errorMessage

    logger.info("Done setting the server's hostname.")
    return errorMessage


def copyRepositoryTemplate(programParentDir, upgradeWorkingDir):
    repositoryTemplate = programParentDir + '/repositoryTemplate/local.repo'
    repoDir = upgradeWorkingDir + '/repositoryTemplate'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Copying the yum repository template needed for the post-upgrade to the pre-upgrade working directory.')
    try:
        if not os.path.isdir(repoDir):
            os.mkdir(repoDir)
        shutil.copy(repositoryTemplate, repoDir)
    except OSError as err:
        logger.error("Unable to create the yum repository directory '" + repoDir + "'.\n" + str(err))
        print RED + "Unable to create the yum repository directory '" + repoDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    except IOError as err:
        logger.error("Unable to copy the yum repository template from '" + repositoryTemplate + "' to '" + repoDir + "'.\n" + str(err))
        print RED + "Unable to copy the yum repository template from '" + repositoryTemplate + "' to '" + repoDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    logger.info('Done copying the yum repository template needed for the post-upgrade to the pre-upgrade working directory.')


def configureMellanox(programParentDir):
    errorMessage = ''
    pciIdsFile = programParentDir + '/nicDataFile/pci.ids'
    mellanoxDriverRPM = programParentDir + '/mellanoxDriver/*.rpm'
    mellanoxBusList = []
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Configuring the Mellanox cards by installing the Mellanox driver and updating connectx.conf.')
    command = 'lspci -i ' + pciIdsFile + ' -mvv'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Failed to get the lspci output used to get the Compute Node's Mellanox NIC bus list.\n" + err + '\n' + out)
        return "Failed to get the lspci output used to get the Compute Node's Mellanox NIC bus list; thus the network configuration was not confirmed."
    out = re.sub('\n{2,}', '####', out)
    deviceList = out.split('####')
    for device in deviceList:
        if ('Ethernet controller' in device or 'Network controller' in device) and 'Mellanox' in device:
            try:
                bus = re.match('\\s*[a-zA-Z]+:\\s+([0-9a-f]{2}:[0-9a-f]{2}\\.[0-9])', device, re.MULTILINE | re.DOTALL).group(1)
                logger.info('The bus information for device:\n' + device[0:100] + '\nwas determined to be: ' + bus + '.\n')
                mellanoxBusList.append(bus)
            except AttributeError as err:
                logger.error('An AttributeError was encountered while getting the Mellanox nic bus information: ' + str(err) + '\n' + device[0:200])
                return 'An AttributeError was encountered while getting the Mellanox nic bus information; thus the network configuration was not confirmed.'

    command = 'rpm -Uvh ' + mellanoxDriverRPM
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Failed to install the Mellanox driver.\n' + err + '\n' + out)
        return 'Failed to install the Mellanox driver; thus the network configuration was not confirmed.'
    for bus in mellanoxBusList:
        command = 'connectx_port_config -d ' + bus + ' -c eth,eth'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Failed to update Mellanox bus '" + bus + "' from infininband to ethernet.\n" + err + '\n' + out)
            return 'Failed to update Mellanox from infiniband to ethernet; thus the network configuration was not confirmed.'

    logger.info('Done configuring the Mellanox cards by installing the Mellanox driver and updating connectx.conf.')
    return errorMessage


def checkForMellanox(programParentDir, upgradeWorkingDir, osDist):
    pciIdsFile = programParentDir + '/mellanoxFiles/pci.ids'
    mellanoxPresent = False
    if osDist == 'SLES':
        mellanoxDriverRPM = glob.glob(programParentDir + '/mellanoxFiles/SLES/*.rpm')[0]
    else:
        mellanoxDriverRPM = glob.glob(programParentDir + '/mellanoxFiles/RHEL/*.rpm')[0]
    mellanoxDriverDir = upgradeWorkingDir + '/mellanoxDriver'
    nicDataFileDir = upgradeWorkingDir + '/nicDataFile'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking to see if Mellanox NIC cards are present.')
    print GREEN + 'Checking to see if Mellanox NIC cards are present.' + RESETCOLORS
    command = 'lspci -i ' + pciIdsFile + ' -mvv'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Failed to get the lspci output which is used to check if Mellanox NIC cards are present.\n' + err + '\n' + out)
        print RED + 'Failed to get the lspci output which is used to check if Mellanox NIC cards are present; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    out = re.sub('\n{2,}', '####', out)
    deviceList = out.split('####')
    for device in deviceList:
        if ('Ethernet controller' in device or 'Network controller' in device) and 'Mellanox' in device:
            mellanoxPresent = True
            break

    if mellanoxPresent:
        try:
            os.mkdir(mellanoxDriverDir)
            shutil.copy2(mellanoxDriverRPM, mellanoxDriverDir)
        except OSError as err:
            logger.error("Unable to create the Mellanox driver directory '" + mellanoxDriverDir + "'.\n" + str(err))
            print RED + "Unable to create the Mellanox driver directory '" + mellanoxDriverDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        except IOError as err:
            logger.error("Unable to copy the Mellanox driver to '" + mellanoxDriverDir + "'.\n" + str(err))
            print RED + "Unable to copy the Mellanox driver to '" + mellanoxDriverDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

        try:
            shutil.copy2(pciIdsFile, nicDataFileDir)
        except IOError as err:
            logger.error("Unable to copy the pci.ids file to '" + nicDataFileDir + "'.\n" + str(err))
            print RED + "Unable to copy the pci.ids file to '" + nicDataFileDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    logger.info('Done checking to see if Mellanox NIC cards are present.')