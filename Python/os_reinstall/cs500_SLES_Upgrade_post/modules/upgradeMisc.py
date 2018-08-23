# Embedded file name: ./upgradeMisc.py
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
        if 'flags=' in data and not ('lo:' in data or 'bond' in data):
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
        if count == 2:
            nicDict[nicMACAddress] = nicName
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


def checkSLESNetworkConfiguration(programParentDir, osDist, cursesThread, **kwargs):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking the network configuration.')
    cursesThread.insertMessage(['informative', 'Checking the network configuration.'])
    cursesThread.insertMessage(['informative', ''])
    if 'osDistLevel' in kwargs:
        osDistLevel = kwargs['osDistLevel']
    else:
        osDistLevel = ''
    if osDistLevel == '11.4':
        command = 'service network stop'
    else:
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
        logger.error("Problems were encountered while setting the server's hostname '" + hostname + "'.\n" + command + '\n' + err + '\n' + out)
        errorMessage = "Problems were encountered while setting the server's hostname '" + hostname + "'; thus the server's hostname may not be set."
    command = 'echo -n "' + hostname + '" > /etc/hostname'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Problems were encountered while setting the server's hostname '" + hostname + "'.\n" + command + '\n' + err + '\n' + out)
        errorMessage = "Problems were encountered while setting the server's hostname '" + hostname + "'; thus the server's hostname may not be set."
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


def configureSnapper(osDistLevel, cursesThread):
    errorMessage = ''
    snapperResourceList = ['NUMBER_CLEANUP="yes"',
     'NUMBER_LIMIT="7"',
     'TIMELINE_LIMIT_HOURLY="0"',
     'TIMELINE_LIMIT_DAILY="7"',
     'TIMELINE_LIMIT_WEEKLY="0"',
     'TIMELINE_LIMIT_MONTHLY="0"',
     'TIMELINE_LIMIT_YEARLY="0"']
    configList = []
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Configuring snapper to keep snapshots for the last 7 days.')
    cursesThread.insertMessage(['informative', 'Configuring snapper to keep snapshots for the last 7 days.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'snapper list-configs'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Problems were encountered while getting the list of snapper configurations.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while getting the list of snapper configurations.'
        return errorMessage
    configDataList = out.splitlines()
    for line in configDataList:
        line = line.strip()
        if len(line) == 0 or re.match('^-', line) or re.match('^\\s+$', line) or re.match('^Config', line, re.IGNORECASE):
            continue
        else:
            configList.append(re.sub('\\s+', '', line).split('|')[0])

    for config in configList:
        for resource in snapperResourceList:
            if resource == 'TIMELINE_LIMIT_WEEKLY=0' and osDistLevel == '11.4':
                continue
            if osDistLevel == '11.4':
                command = "sed -i 's/^\\s*" + resource.split('=')[0] + '=.*$/' + resource + "/g' /etc/snapper/configs/" + config
            else:
                command = 'snapper -c ' + config + ' set-config ' + resource
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Problems were encountered while setting the resource '" + resource + "' for the snapper configuration '" + config + "'.\n" + err + '\n' + out)
                errorMessage = 'Problems were encountered while setting the snapper configuration resources.'
                return errorMessage
            time.sleep(1.0)

    logger.info('Done configuring snapper to keep snapshots for the last 7 days.')
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


def stageAddOnRPMS(programParentDir, upgradeWorkingDir, osDist, osUpgradeVersion):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Copying the additional RPMs needed for the post-upgrade to the pre-upgrade working directory.')
    addOnSoftwareRPMDir = programParentDir + '/addOnSoftwareRPMS/' + osDist + '/' + osUpgradeVersion
    addOnSoftwareRPMSDir = upgradeWorkingDir + '/addOnSoftwareRPMS'
    try:
        if os.listdir(addOnSoftwareRPMDir):
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
            if osDist == 'RHEL':
                copyRepositoryTemplate(programParentDir, upgradeWorkingDir)
        else:
            logger.info('There were no additional RPMs present for the post-upgrade.')
    except OSError as err:
        logger.error("Unable to get a listing of the additional RPMs needed for the post-upgrade, if any, from '" + addOnSoftwareRPMDir + "'.\n" + str(err))
        print RED + 'Unable to get a listing of the additional RPMs needed for the post-upgrade, if any; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    logger.info('Done copying the additional RPMs needed for the post-upgrade to the pre-upgrade working directory.')


def updateMultipathConf(cursesThread):
    errorMessage = ''
    started = False
    vendorMatched = False
    productMatched = False
    blackListPresent = False
    blacklist = '\'\n\n#Added so that HPE controllers are ignored by multipath.\nblacklist {\n\tdevnode         "^(ram|raw|loop|fd|md|dm-|sr|scd|st)[0-9]*"\n\tdevnode         "^hd[a-z][[0-9]*]"\n\n\tdevice {\n\t\tvendor "HP"\n\t\tproduct "LOGICAL VOLUME.*"\n\t}\n}\''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Updating /etc/multipath.conf to blacklist HPE controllers.')
    cursesThread.insertMessage(['informative', 'Updating /etc/multipath.conf to blacklist HPE controllers.'])
    cursesThread.insertMessage(['informative', ''])
    command = "grep -zPo '^\\s*blacklist\\s+(\\{([^{}]++|(?1))*\\})' /etc/multipath.conf"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        command = 'echo -e ' + blacklist + ' >> /etc/multipath.conf'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Failed to update /etc/multipath.conf to blacklist HPE controllers.\n' + err + '\n' + out)
            logger.info('The command used to update /etc/multipath.conf to blacklist HPE controllers was: \n' + command)
            errorMessage = 'Failed to update /etc/multipath.conf to blacklist HPE controllers; thus /etc/multipath.conf will have to be updated manually.'
    else:
        currrentBlacklist = out.splitlines()
        for line in currrentBlacklist:
            if re.match('\\s*device\\s*{\\s*$', line):
                if started:
                    started = False
                    continue
                else:
                    started = True
                    continue
            elif started:
                if re.match('\\s*vendor\\s+"HP"\\s*$', line):
                    if vendorMatched:
                        started = False
                        continue
                    else:
                        vendorMatched = True
                        continue
                if re.match('\\s*product\\s+"LOGICAL VOLUME\\.\\*"\\s*$', line):
                    if productMatched:
                        started = False
                        continue
                    else:
                        productMatched = True
                        continue
                if re.match('\\s*}\\s*$', line) and vendorMatched and productMatched:
                    blackListPresent = True
                    break
                elif re.match('\\s*}\\s*$', line) and (vendorMatched or productMatched):
                    break
                elif vendorMatched and productMatched and not re.match('\\s*$|\\s*#', line):
                    break
                else:
                    continue
            else:
                continue

        if blackListPresent:
            logger.info('The blacklist for /etc/multipath.conf was not updated, since it is already up to date.')
        else:
            command = 'echo -e ' + blacklist + ' >> /etc/multipath.conf'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error('Failed to update /etc/multipath.conf to blacklist HPE controllers.\n' + err + '\n' + out)
                logger.info('The command used to update /etc/multipath.conf to blacklist HPE controllers was: \n' + command)
                errorMessage = 'Failed to update /etc/multipath.conf to blacklist HPE controllers; thus /etc/multipath.conf will have to be updated manually.'
    logger.info('Done updating /etc/multipath.conf to blacklist HPE controllers.')
    return errorMessage


def updateInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, **kwargs):
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    cs500ScaleOut = False
    serverModel = 'Superdome'
    autoinstImageFile = programParentDir + '/installCtrlFiles/autoinst.img'
    autoinstImgMountPoint = '/tmp/autoinstImg_' + dateTimestamp
    installCtrlFileDir = upgradeWorkingDir + '/installCtrlFile'
    ctrlFile = installCtrlFileDir + '/autoinst.xml'
    lunID = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Updating the install control file with the partition ID that will have the OS installed on it.')
    if 'cs500ScaleOut' in kwargs:
        cs500ScaleOut = True
    if 'serverModel' in kwargs:
        serverModel = kwargs['serverModel']
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/cs500-autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/cs500_autoinst.img'
    else:
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/cs900-autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/cs900_autoinst.img'
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
    if serverModel == 'Superdome' or cs500ScaleOut:
        command = 'df /boot/efi'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Unable to get the partition information for the root file system.\n' + err + '\n' + out)
            print RED + 'Unable to get the partition information for the root file system; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        out = out.strip()
        logger.info('df shows that the /boot/efi partition is mounted on:\n' + out)
        if '/dev' not in out:
            logger.error('Unable to identify the the OS LUN device.')
            print RED + 'Unable to identify the OS LUN device; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        try:
            if '360002ac0' in out:
                lunID = re.match('.*(360002ac0+[0-9a-f]+)[_-]part', out, re.DOTALL | re.MULTILINE).group(1)
            else:
                device = re.match('.*(/dev/[0-9a-z/-_]*)\\s+', out, re.DOTALL | re.MULTILINE).group(1)
                command = 'find -L /dev -samefile ' + device
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    if not ('already visited the directory' in err or 'No such' in err):
                        logger.error("Failed to get the files linked to '" + device + "'.\n" + err + '\n' + out)
                        print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)
                    else:
                        logger.warn('find complained while searching for files linked to ' + device + ': \n' + err + '\n' + out)
                fileList = out.splitlines()
                for file in fileList:
                    if '360002ac0' in file:
                        try:
                            lunID = re.match('.*(360002ac0+[0-9a-f]+)', file).group(1)
                        except AttributeError as err:
                            logger.error("There was a match error when trying to match against '" + file + "'.\n" + str(err))
                            print RED + 'There was a match error when trying to get the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                            exit(1)

                        break

                if lunID == '':
                    logger.error("Unable to identify the OS LUN ID using the device's (" + device + ') linked file list: ' + str(fileList))
                    print RED + 'Unable to identify the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)
        except AttributeError as err:
            logger.error("There was a match error when trying to match against '" + out + "'.\n" + str(err))
            print RED + 'There was a match error when trying to get the OS LUN ID; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

        logger.info("The OS LUN ID was determined to be '" + lunID + "'.")
        osLUNDevice = '/dev/mapper/' + lunID
        command = "sed -ri 's,%%bootDisk%%," + osLUNDevice + ",g' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to update '" + ctrlFile + "' with the OS LUN device '" + osLUNDevice + "'.\n" + err + '\n' + out)
            print RED + 'Unable to update the install control file with the OS LUN device; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if osUpgradeVersion == '12.1':
        slesSP1PackageDict = {'sapconf': 'saptune',
         'rear116': 'rear118a'}
        for package in slesSP1PackageDict:
            command = "sed -i 's,<package>" + slesSP1PackageDict[package] + '</package>,<package>' + package + "</package>,' " + ctrlFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Unable to update '" + ctrlFile + "' with the HPE SAP HANA specific package (" + package + ') for SLES for SAP 12 SP1.\n' + err + '\n' + out)
                print RED + 'Unable to update the install control file with the HPE SAP HANA specific package for SLES for SAP 12 SP1; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            time.sleep(1.0)

    if serverModel == 'DL580' and osUpgradeVersion == '12.1':
        hpeTune = "mkdir -p /mnt/usr/lib/tuned/sap-hpe-hana\\ncat<<EOF > /mnt/usr/lib/tuned/sap-hpe-hana/tuned.conf\\n######################################################\\n# START: tuned profile sap-hpe-hana settings\\n######################################################\\n#\\n# tuned configuration for HPE SAP HANA.\\n# Inherited from SuSE/SAP 'sap-hana' profile\\n#\\n# Allows HPE SAP HANA specific tunings\\n#\\n[main]\\ninclude = sap-hana\\n"
        command = "sed -i '\\|<START HPE TUNE>|,\\|<END HPE TUNE>|c\\" + hpeTune + "' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to update '" + ctrlFile + "' with the HPE SAP HANA specific tuning for SLES for SAP 12 SP1.\n" + err + '\n' + out)
            print RED + 'Unable to update the install control file with the HPE SAP HANA specific tuning for SLES for SAP 12 SP1; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    elif serverModel == 'DL580':
        command = "sed -i '/<START HPE TUNE>\\|<END HPE TUNE>/d' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to remove the tuning boundaries from '" + ctrlFile + "'.\n" + err + '\n' + out)
            print RED + 'Unable to remove the tuning boundaries from the install control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if 'cs500ScaleOut' in kwargs:
        command = 'sed -i \'s@<start_multipath config:type="boolean">false</start_multipath>@<start_multipath config:type="boolean">true</start_multipath>@\' ' + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to update '" + ctrlFile + "' with the removal of the pre-scripts section.\n" + err + '\n' + out)
            print RED + 'Unable to update the install control file with the removal of the pre-scripts section; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = 'sed -i \'\\|^[ \\t]*<pre-scripts config:type="list">|,\\|^[ \\t]*</pre-scripts>|d\' ' + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to update '" + ctrlFile + "' with the removal of the pre-scripts section.\n" + err + '\n' + out)
            print RED + 'Unable to update the install control file with the removal of the pre-scripts section; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        askContents = '    <ask-list config:type="list">\\n      <ask>\\n        <title>OS LUN: ' + osLUNDevice + '</title> \\n        <question>Choose option</question> \\n        <selection config:type="list"> \\n          <entry> \\n            <label>Reboot Server</label> \\n            <value>reboot</value> \\n          </entry> \\n          <entry> \\n            <label>Halt Server</label> \\n            <value>halt</value> \\n          </entry> \\n          <entry> \\n            <label>Continue to overwrite the LUN device.</label> \\n            <value>continue</value> \\n          </entry> \\n        </selection> \\n        <stage>initial</stage> \\n        <script> \\n          <environment config:type="boolean">true</environment> \\n          <feedback config:type="boolean">true</feedback> \\n          <debug config:type="boolean">false</debug> \\n          <rerun_on_error config:type="boolean">true</rerun_on_error> \\n          <source> \\n<![CDATA[ \\n#!/bin/bash \\n \\ncase "$VAL" in \\n    "reboot") \\n        echo b > /proc/sysrq-trigger \\n        exit 0 \\n        ;; \\n    "halt") \\n        echo o > /proc/sysrq-trigger \\n        exit 0 \\n        ;; \\n    "continue") \\n        exit 0 \\n        ;; \\nesac \\n]]> \\n          </source> \\n        </script> \\n      </ask> \\n    </ask-list>'
        command = 'sed -i \'\\|<ask-list config:type="list">|,\\|</ask-list>|c\\' + askContents + "' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to update '" + ctrlFile + "' with the current ask-list section.\n" + err + '\n' + out)
            print RED + 'Unable to update the install control file with the current ask-list section; fix the problem and try again; exiting program execution.' + RESETCOLORS
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


def updateSGInstallCtrlFile(programParentDir, upgradeWorkingDir, osUpgradeVersion, serverModel):
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    autoinstImageFile = programParentDir + '/installCtrlFiles/autoinst.img'
    autoinstImgMountPoint = '/tmp/autoinstImg_' + dateTimestamp
    installCtrlFileDir = upgradeWorkingDir + '/installCtrlFile'
    ctrlFile = installCtrlFileDir + '/autoinst.xml'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Updating the install control file for the Serviceguard node.')
    if serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9':
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/sgQS-autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/sgQS_autoinst.img'
    else:
        installCtrlFileTemplate = programParentDir + '/installCtrlFiles/sgNFS-autoinst.xml'
        ctrlFileImg = installCtrlFileDir + '/sgNFS_autoinst.img'
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
    if serverModel == 'ProLiant DL360 Gen9':
        command = "sed -i 's/B120i/P440ar/g' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to update '" + ctrlFile + "' with the DL360's controller model (P440ar).\n" + err + '\n' + out)
            print RED + "Unable to update the install control file with the DL360's controller model (P440ar); fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
    if osUpgradeVersion != '12.2':
        if osUpgradeVersion == '11.4':
            slesPackageDict = {'sapconf': 'saptune',
             'rear': 'rear118a'}
        else:
            slesPackageDict = {'sapconf': 'saptune',
             'rear116': 'rear118a'}
        for package in slesPackageDict:
            command = "sed -i 's,<package>" + slesPackageDict[package] + '</package>,<package>' + package + "</package>,' " + ctrlFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Unable to update '" + ctrlFile + "' with the HPE SAP HANA specific package (" + package + ') for SLES for SAP 12 SP1.\n' + err + '\n' + out)
                print RED + 'Unable to update the install control file with the HPE SAP HANA specific package for SLES for SAP 12 SP1; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            time.sleep(1.0)

    if osUpgradeVersion == '11.4':
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
                logger.error("Unable to remove the packages from the control file '" + ctrlFile + "' that are not present for SLES 11.4.\n" + err + '\n' + out + '\n' + str(removalPackageList))
                print RED + 'Unable to remove the packages from the control file that are not present for SLES 11.4; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            time.sleep(0.1)

        command = "sed -i 's@<loader_type>grub2</loader_type>@<loader_type>grub</loader_type>@' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to change the loader type in the control file '" + ctrlFile + "' from grub2 to grub.\n" + err + '\n' + out)
            print RED + 'Unable to change the loader type in the control file from grub2 to grub; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = "sed -i '\\|<services-manager>|,\\|</services-manager>|c\\" + sles11Services + "' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Unable to change the "services-manager" section in the control file \'' + ctrlFile + "'.\n" + err + '\n' + out)
            print RED + 'Unable to change the "services-manager" section in the control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = "sed -i 's@<package>quota-nfs</package>@&\\n      <package>net-snmp</package>\\n      <package>biosdevname</package>@' " + ctrlFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to add the net-snmp package to the control file '" + ctrlFile + "'.\n" + err + '\n' + out)
            print RED + 'Unable to add the net-snmp package to the control file; fix the problem and try again; exiting program execution.' + RESETCOLORS
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
    logger.info('Done updating the install control file the Serviceguard node.')
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

    logger.info('Done updating kdump.service to address bug 1008170.')
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


def checkForMellanox(programParentDir, upgradeWorkingDir, osDist, osDistLevel):
    pciIdsFile = programParentDir + '/mellanoxFiles/pci.ids'
    mellanoxPresent = False
    if osDist == 'SLES':
        mellanoxDriverRPMS = glob.glob(programParentDir + '/mellanoxFiles/SLES/' + osDistLevel + '/*.rpm')
    else:
        mellanoxDriverRPMS = glob.glob(programParentDir + '/mellanoxFiles/RHEL/' + osDistLevel + '/*.rpm')
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
            for file in mellanoxDriverRPMS:
                shutil.copy2(file, mellanoxDriverDir)
                time.sleep(1.0)

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


def getOSUpgradeVersion(supportedOSVersions):
    logger = logging.getLogger('coeOSUpgradeLogger')
    while True:
        if len(supportedOSVersions) > 1:
            count = 0
            choiceNumberDict = {}
            prompt = 'Select the OS version that the server is being upgraded to ('
            for version in supportedOSVersions:
                osVersion = supportedOSVersions[count]
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
        else:
            osVersion = supportedOSVersions[0]
        while True:
            response = raw_input('The server is going to be upgraded to ' + osVersion[:4] + ' ' + osVersion[5:] + '; is this correct [y|n|q]: ')
            response = response.strip().lower()
            if not (response == 'y' or response == 'n' or response == 'q'):
                print 'An invalid entry was provided; please try again.\n'
                continue
            else:
                if response == 'y':
                    validOS = True
                elif response == 'n':
                    validOS = False
                else:
                    logger.info('Upgrade was cancelled while selecting the OS to upgrade to.')
                    exit(0)
                break

        if validOS:
            osUpgradeVersion = osVersion[5:]
            logger.info('The choice to upgrade to ' + osUpgradeVersion + ' was made.')
            break
        else:
            continue

    return osUpgradeVersion


def setTimezone(programParentDir, cursesThread):
    errorMessage = ''
    linkFileExists = False
    timezoneFile = programParentDir + '/timezoneData/timezoneLinks'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Setting the server's time zone.")
    cursesThread.insertMessage(['informative', "Setting the server's time zone."])
    cursesThread.insertMessage(['informative', ''])
    try:
        with open(timezoneFile) as f:
            timezoneLinkData = f.readlines()
    except IOError as err:
        logger.error("Unable to get the time zone link list from '" + timezoneFile + "'.\n" + str(err))
        errorMessage = "Unable to get the time zone link list; thus the server's time zone was not set."
        return errorMessage

    try:
        os.remove('/etc/localtime')
    except OSError as err:
        logger.warn('The following error was encounterd while removing /etc/localtime: ' + str(err))

    for link in timezoneLinkData:
        link = link.strip()
        if os.path.isfile(link):
            linkFileExists = True
            command = 'ln ' + link + ' /etc/localtime'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Problems were encountered while linking /etc/localtime to '" + link + "'.\n" + err + '\n' + out)
                errorMessage = "Problems were encountered while linking /etc/localtime; thus the server's time zone was not set."
                return errorMessage
            break

    if not linkFileExists:
        logger.error('There was not a link file present for /etc/localtime to link against; the selection of link files was: ' + str(timezoneLinkData))
        errorMessage = "There was not a link file present for /etc/localtime to link against; thus the server's time zone was not set."
    logger.info("Done setting the server's time zone.")
    return errorMessage