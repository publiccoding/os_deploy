# Embedded file name: ./postUpgradeTasks.py
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

def checkRHELNetworkConfiguration(programParentDir, osDist, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking the network configuration.')
    cursesThread.insertMessage(['informative', 'Checking the network configuration.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'systemctl stop network'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while shutting down the network.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while shutting down the network; thus the network configuration was not confirmed.'
        return errorMessage
    time.sleep(15.0)
    if os.path.isdir(programParentDir + '/mellanoxDriver'):
        errorMessage = configureMellanox(programParentDir, osDist)
        if len(errorMessage) != 0:
            return errorMessage
    command = 'modprobe -r tg3'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while unloading the tg3 driver.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while unloading the tg3 driver; thus the network configuration was not confirmed.'
        return errorMessage
    time.sleep(2.0)
    command = 'modprobe tg3'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while reloading the tg3 driver.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while reloading the tg3 driver; thus the network configuration was not confirmed.'
        return errorMessage
    time.sleep(2.0)
    command = 'ifconfig -a'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get NIC card information.\n' + err + '\n' + out)
        errorMessage = 'Unable to get NIC card information; thus the network configuration was not confirmed.'
        return errorMessage
    nicDataList = out.splitlines()
    debugLogger.info('The NIC card data list was: ' + str(nicDataList))
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
                    debugLogger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                    errorMessage = "There was a match error when trying to match against '" + data + "'; thus the network configuration was not confirmed."
                    return errorMessage

            elif 'flags=' in data and 'bond' in data:
                skip = True
            elif 'ether' in data and 'txqueuelen' in data and not skip:
                try:
                    nicMACAddress = re.match('\\s*ether\\s+([a-z0-9:]+)', data, re.IGNORECASE).group(1)
                    count += 1
                except AttributeError as err:
                    debugLogger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
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
        debugLogger.error("Unable to get the MAC address list from '" + macAddressDataFile + "'.\n" + str(err))
        errorMessage = "Unable to get the MAC address list from '" + macAddressDataFile + "'; thus the network configuration was not confirmed."
        return errorMessage

    macAddressDict = dict((x.strip().split('|') for x in macAddressData))
    macAddressDict = dict(map(reversed, macAddressDict.items()))
    debugLogger.info('The MAC address dictionary (previous NIC mapping) was determined to be: ' + str(macAddressDict) + '.')
    changedNicDict = {}
    for macAddress in macAddressDict:
        currentNicName = macAddressDict[macAddress]
        try:
            previousNicName = nicDict[macAddress]
        except KeyError as err:
            debugLogger.error('The resource key (' + str(err) + ') was not present in the previous NIC dictionary.')
            errorMessage = 'The resource key (' + str(err) + ') was not present in the previous NIC dictionary; thus the network configuration was not confirmed.'
            return errorMessage

        if currentNicName != previousNicName:
            changedNicDict[previousNicName] = currentNicName

    if len(changedNicDict) != 0:
        errorMessage = updateNICNames(changedNicDict, osDist, cursesThread)
    logger.info('Done checking the network configuration.')
    return errorMessage


def checkSLESNetworkConfiguration(programParentDir, osDist, osDistLevel, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking the network configuration.')
    cursesThread.insertMessage(['informative', 'Checking the network configuration.'])
    cursesThread.insertMessage(['informative', ''])
    if os.path.isdir(programParentDir + '/mellanoxDriver'):
        errorMessage = configureMellanox(programParentDir, osDist)
        if len(errorMessage) != 0:
            return errorMessage
    if osDistLevel == '11.4':
        command = 'service network stop'
    else:
        command = 'systemctl stop network'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while shutting down the network.\n' + err + '\n' + out)
        debugLogger.info('The command use to shut down the network was: ' + command)
        errorMessage = 'Problems were encountered while shutting down the network; thus the network configuration was not confirmed.'
        return errorMessage
    time.sleep(15.0)
    command = 'ifconfig -a'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get NIC card information.\n' + err + '\n' + out)
        debugLogger.info('The command use to get NIC card information was: ' + command)
        errorMessage = 'Unable to get NIC card information; thus the network configuration was not confirmed.'
        return errorMessage
    nicDataList = out.splitlines()
    debugLogger.info('The NIC card data list was: ' + str(nicDataList))
    nicDict = {}
    for data in nicDataList:
        if 'HWaddr' in data:
            try:
                nicList = re.match('\\s*([a-z0-9]+)\\s+.*HWaddr\\s+([a-z0-9:]+)', data, re.IGNORECASE).groups()
            except AttributeError as err:
                debugLogger.error("There was a match error while getting NIC card MAC addresses '" + data + "'.\n" + str(err))
                errorMessage = 'There was an error while getting NIC card MAC addresses; thus the network configuration was not confirmed.'
                return errorMessage

            nicDict[nicList[1].lower()] = nicList[0]

    debugLogger.info('The NIC card dictionary was determined to be: ' + str(nicDict))
    try:
        macAddressDataFile = programParentDir + '/nicDataFile/macAddressData.dat'
        with open(macAddressDataFile) as f:
            macAddressData = f.readlines()
    except IOError as err:
        debugLogger.error("Unable to get the MAC address list from '" + macAddressDataFile + "'.\n" + str(err))
        errorMessage = "Unable to get the MAC address list from '" + macAddressDataFile + "'; thus the network configuration was not confirmed."
        return errorMessage

    macAddressDict = dict((x.strip().split('|') for x in macAddressData))
    macAddressDict = dict(map(reversed, macAddressDict.items()))
    debugLogger.info('The MAC address dictionary (previous NIC mapping) was determined to be: ' + str(macAddressDict) + '.')
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
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Updating the network configuration, since the NIC names changed.')
    cursesThread.insertMessage(['informative', 'Updating the network configuration, since the NIC names changed.'])
    cursesThread.insertMessage(['informative', ''])
    debugLogger.info('The changed NIC dictionary was determined to be: ' + str(changedNicDict))
    networkCfgFileList = []
    if osDist == 'SLES':
        networkDir = '/etc/sysconfig/network'
    else:
        networkDir = '/etc/sysconfig/network-scripts'
    try:
        os.chdir(networkDir)
    except OSError as err:
        debugLogger.error("Unable to change into the server's network configuration directory '" + networkDir + "'.\n" + str(err))
        errorMessage = "Unable to change into the server's network configuration directory; thus the network configuration was not confirmed."
        return errorMessage

    command = 'ls ifcfg-*'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while getting a listing of the NIC configuration files.\n' + err + '\n' + out)
        debugLogger.info('The command used to get a listing of the NIC configuration files was: ' + command)
        errorMessage = 'Problems were encountered while getting a listing of the NIC configuration files; thus the network configuration was not confirmed.'
        return errorMessage
    nicCfgFileList = out.splitlines()
    debugLogger.info('The NIC configuration files were determined to be: ' + str(nicCfgFileList) + '.')
    tmpNicNameDict = dict(((nic.strip().replace('ifcfg-', ''), nic.strip()) for nic in nicCfgFileList))
    nicNameDict = {}
    for key in tmpNicNameDict:
        if '.' not in key and key != 'lo':
            nicNameDict[key] = tmpNicNameDict[key]
            networkCfgFileList.append(tmpNicNameDict[key])

    debugLogger.info('The NIC name dictionary was determined to be: ' + str(nicNameDict) + '.')
    debugLogger.info('The NIC configuration file list was determined to be: ' + str(networkCfgFileList) + '.')
    command = ''
    if osDist == 'SLES':
        if glob.glob('ifroute-*'):
            command = 'ls ifroute-*'
    elif glob.glob('route-*'):
        command = 'ls route-*'
    routeNicNameDict = {}
    if not command == '':
        debugLogger.info("The command used to get the list of NIC specific route configuration files was: '" + command + "'.")
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Problems were encountered while getting a listing of the NIC specific route configuration files.\n' + err + '\n' + out)
            errorMessage = 'Problems were encountered while getting a listing of the NIC specific route configuration files; thus the network configuration was not confirmed.'
            return errorMessage
        routeCfgFileList = out.splitlines()
        debugLogger.info('The route configuration file list was determined to be: ' + str(routeCfgFileList) + '.')
        if osDist == 'SLES':
            tmpRouteNicNameDict = dict(((route.strip().replace('ifroute-', ''), route.strip()) for route in routeCfgFileList))
        else:
            tmpRouteNicNameDict = dict(((route.strip().replace('route-', ''), route.strip()) for route in routeCfgFileList))
        for key in tmpRouteNicNameDict:
            if '.' not in key and key != 'lo':
                routeNicNameDict[key] = tmpRouteNicNameDict[key]
                networkCfgFileList.append(tmpRouteNicNameDict[key])

    if len(routeNicNameDict) > 0:
        debugLogger.info('The route name dictionary was determined to be: ' + str(routeNicNameDict) + '.')
    for nicName in changedNicDict:
        previousNICName = changedNicDict[nicName]
        command = "sed -i 's/" + previousNICName + '/' + nicName + "/g' " + ' '.join(networkCfgFileList)
        debugLogger.info("The command used to update the NIC configuration files with the new NIC name was: '" + command + "'.")
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Problems were encountered while updating the configuration file with the new NIC name '" + nicName + "'.\n" + err + '\n' + out)
            errorMessage = 'Problems were encountered while updating the configuration files with the new NIC names; thus the network configuration was not confirmed.'
            return errorMessage
        if previousNICName in nicNameDict:
            command = 'mv ' + nicNameDict[previousNICName] + ' ifcfg-' + nicName
            debugLogger.info("The command used to move the NIC configuration file '" + nicNameDict[previousNICName] + "' to its new name was: '" + command + "'.")
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Problems were encountered while moving '" + nicNameDict[previousNICName] + "' to 'ifcfg-" + nicName + "'.\n" + err + '\n' + out)
                errorMessage = 'Problems were encountered while moving the NIC configuration files to their new name; thus the network configuration was not confirmed.'
                return errorMessage
            networkCfgFileList.remove(nicNameDict[previousNICName])
        if previousNICName in routeNicNameDict:
            if osDist == 'SLES':
                newRouteFileName = 'ifroute-' + nicName
            else:
                newRouteFileName = 'route-' + nicName
            command = 'mv ' + routeNicNameDict[previousNICName] + ' ' + newRouteFileName
            debugLogger.info('The command used to move the NIC route configuration file ' + routeNicNameDict[previousNICName] + "' to its new name was: '" + command + "'.")
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Problems were encountered while moving '" + routeNicNameDict[previousNICName] + "' to '" + newRouteFileName + "'.\n" + err + '\n' + out)
                errorMessage = 'Problems were encountered while moving the NIC route configuration files to their new name; thus the network configuration was not confirmed.'
                return errorMessage
            networkCfgFileList.remove(routeNicNameDict[previousNICName])

    logger.info('Done updating the network configuration, since the NIC names changed.')
    return errorMessage


def setHostname(programParentDir, cursesThread):
    errorMessage = ''
    hostnameFile = programParentDir + '/hostnameData/hostname'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Setting the server's hostname.")
    cursesThread.insertMessage(['informative', "Setting the server's hostname."])
    cursesThread.insertMessage(['informative', ''])
    try:
        f = open(hostnameFile, 'r')
        hostname = f.readline()
    except IOError as err:
        debugLogger.error("Problems were encountered while reading the server's hostname from '" + hostnameFile + "'.\n" + str(err))
        errorMessage = "Problems were encountered while reading the server's hostname from '" + hostnameFile + "'; thus the server's hostname was not set."
        return errorMessage

    command = 'hostnamectl set-hostname ' + hostname
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Problems were encountered while setting the server's hostname '" + hostname + "'.\n" + err + '\n' + out)
        debugLogger.info("The command use to set the server's hostname was: " + command)
        errorMessage = "Problems were encountered while setting the server's hostname; thus the server's hostname may not be set."
    command = 'echo -n "' + hostname + '" > /etc/hostname'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Problems were encountered while setting the server's hostname '" + hostname + "'.\n" + err + '\n' + out)
        debugLogger.info("The command use to set the server's hostname was: " + command)
        errorMessage = "Problems were encountered while setting the server's hostname; thus the server's hostname may not be set."
    logger.info("Done setting the server's hostname.")
    return errorMessage


def updateSysctl(kernelParameters, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Removing kernel parameters from /etc/sysctl.conf.')
    cursesThread.insertMessage(['informative', 'Removing kernel parameters from /etc/sysctl.conf.'])
    cursesThread.insertMessage(['informative', ''])
    kernelParameterDict = dict(((x.split(':')[0].strip(), x.split(':')[1].strip()) for x in re.sub('\\s*,\\s*', ',', kernelParameters).split(',')))
    command = "sed -ri '/^[[:space:]]*(" + '|'.join(kernelParameterDict.keys()) + ").*$/d' /etc/sysctl.conf"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Errors were encountered while removing kernel parameters from /etc/sysctl.conf.\n' + err + '\n' + out)
        debugLogger.info('The command used to remove kernel parameters from /etc/sysctl.conf was: ' + command)
        errorMessage = 'Errors were encountered while removing kernel parameters from /etc/sysctl.conf; thus they will need to be removed manually.'
    logger.info('Done removing kernel parameters from /etc/sysctl.conf.')
    return errorMessage


def updateNTPConf(cursesThread):
    errorMessage = ''
    ntpConfigurationFile = '/etc/ntp.conf'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Checking and updating ntp's controlkey setting if necessary.")
    cursesThread.insertMessage(['informative', "Checking and updating ntp's controlkey setting if necessary."])
    cursesThread.insertMessage(['informative', ''])
    command = 'egrep "^\\s*keys" ' + ntpConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    debugLogger.info('The output of the command (' + command + ') used to get the keys resource from ' + ntpConfigurationFile + ' was: ' + out.strip() + '.')
    if result.returncode == 0:
        command = 'egrep "^\\s*controlkey\\s+[0-9]+\\s*.*" ' + ntpConfigurationFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        debugLogger.info('The output of the command (' + command + ') used to get the controlkey resource from ' + ntpConfigurationFile + ' was: ' + out.strip() + '.')
        if result.returncode == 0:
            command = "sed -ri '0,/^\\s*controlkey\\s+[0-9]+\\s*.*/s//controlkey 1/' " + ntpConfigurationFile
        else:
            command = "sed -i 's/^\\s*keys.*/&\\ncontrolkey 1/' " + ntpConfigurationFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Problems were encountered while setting ntp's controlkey variable.\n" + err + '\n' + out)
            debugLogger.info("The command used to set ntp's controlkey variable was: " + command)
            errorMessage = "Problems were encountered while setting ntp's controlkey variable; thus the server's ntp server was not configured."
            return errorMessage
    logger.info("Done checking and updating ntp's controlkey setting if necessary.")
    return errorMessage


def installSLESAddOnSoftware(programParentDir, cursesThread):
    errorMessage = ''
    addOnSoftwareInstalled = True
    addOnSoftwareDir = programParentDir + '/addOnSoftwareRPMS'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Installing the additional software RPMS needed for the upgrade.')
    cursesThread.insertMessage(['informative', 'Installing the additional software RPMS needed for the upgrade.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'zypper ar -G -t plaindir ' + addOnSoftwareDir + ' addOnSoftwareRPMS'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while creating the software repository for the additional software RPMS.\n' + err + '\n' + out)
        debugLogger.info('The command used to create the software repository for the additional software RPMS was: ' + command)
        errorMessage = 'Problems were encountered while creating the software repository for the additional software RPMS; the RPMS will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    command = 'zypper in -y addOnSoftwareRPMS:*'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while installing the additional software RPMS.\n' + err + '\n' + out)
        debugLogger.info('The command used to install the additional software RPMS was: ' + command)
        errorMessage = 'Problems were encountered while installing the additional software RPMS; the RPMS will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    command = 'zypper rr addOnSoftwareRPMS'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while removing the additional software RPMS repository.\n' + err + '\n' + out)
        debugLogger.info('The command used to remove the software repository for the additional software RPMS was: ' + command)
        errorMessage = 'Problems were encountered while removing the additional software RPMS repository; the repository will need to be removed manually.'
    logger.info('Done installing the additional software RPMS needed for the upgrade.')
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
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Installing the additional software RPMs needed for the upgrade.')
    cursesThread.insertMessage(['informative', 'Installing the additional software RPMs needed for the upgrade.'])
    cursesThread.insertMessage(['informative', ''])
    try:
        shutil.copytree(addOnSoftware, repoDir)
    except OSError as err:
        debugLogger.error("Problems were encountered while copying the additional software RPMs to '" + repoDir + "'.\n" + str(err))
        errorMessage = 'Problems were encountered while copying the additional software RPMs to the repository; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)

    command = 'createrepo ' + repoDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while creating the additional software RPMs repository.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while creating the additional software RPMs repository; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    try:
        shutil.copy2(repositoryTemplate, '/etc/yum.repos.d')
    except IOError as err:
        debugLogger.error('Problems were encountered while copying the additional software RPMs repository template into place.\n' + str(err))
        errorMessage = 'Problems were encountered while copying the additional software RPMs repository template into place; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)

    command = "sed -ri 's|^\\s*baseurl=file://.*|" + baseURL + "|' /etc/yum.repos.d/local.repo"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while updating the additional software RPMs repository template.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while updating the additional software RPMs repository; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    command = 'yum --disablerepo="*" --enablerepo="local" -y install \\*'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while installing the additional software RPMs.\n' + err + '\n' + out)
        errorMessage = 'Problems were encountered while installing the additional software RPMs; the RPMs will need to be installed manually before proceeding.'
        addOnSoftwareInstalled = False
        return (errorMessage, addOnSoftwareInstalled)
    try:
        os.remove('/etc/yum.repos.d/local.repo')
        shutil.rmtree(repoDir)
    except OSError as err:
        debugLogger.error('Problems were encountered while removing the additional software RPMs repository.\n' + str(err))
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
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Configuring snapper to keep snapshots for the last 7 days.')
    cursesThread.insertMessage(['informative', 'Configuring snapper to keep snapshots for the last 7 days.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'snapper list-configs'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while getting the list of snapper configurations.\n' + err + '\n' + out)
        debugLogger.info('The command used to get the list of snapper configurations was: ' + command)
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
                debugLogger.error("Problems were encountered while setting the resource '" + resource + "' for the snapper configuration '" + config + "'.\n" + err + '\n' + out)
                debugLogger.info("The command used to set the resource '" + resource + "' for the snapper configuration '" + config + "' was: " + command)
                debugLogger.info('The resources were being set to:\n' + str(snapperResourceList))
                errorMessage = 'Problems were encountered while setting the snapper configuration resources.'
                return errorMessage
            time.sleep(1.0)

    logger.info('Done configuring snapper to keep snapshots for the last 7 days.')
    return errorMessage


def extractOSRestorationArchive(osRestorationArchive, osRestorationArchiveErrorFile, cursesThread):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Extracting the OS restoration archive image.')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    command = 'tar -zxf ' + osRestorationArchive + ' -C /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    debugLogger.info("The command used to extract the OS restoration archive was: '" + command + "'.")
    if result.returncode != 0:
        debugLogger.error("There was a problem extracting the OS restoration archive '" + osRestorationArchive + "'.\n" + err + '\n' + out)
        updateOSRestorationArchiveErrorFile(restorationArchiveErrorFile, cursesThread)
        displayErrorMessage("There was a problem extracting the os restoration archive '" + osRestorationArchive + "'; fix the problem and try again.", cursesThread)
    logger.info('Done extracting the OS restoration archive image.')


def checkOSRestorationArchive(programParentDir, osRestorationArchiveErrorFile, osDist, cursesThread):
    osRestorationArchiveFile = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking the OS restoration archive to make sure it is not corrupt.')
    osArchiveFileRegex = re.compile('.*_OS_Restoration_Backup_For_' + osDist + '_Upgrade_[0-9]{6}[A-Za-z]{3}[0-9]{4}.tar.gz')
    archiveImageDir = programParentDir + '/archiveImages'
    command = 'ls ' + archiveImageDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to get a listing of the files in '" + archiveImageDir + "'.\n" + err + '\n' + out)
        debugLogger.info("The command used to get a listing of the files in '" + archiveImageDir + "' was: " + command)
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage('Unable to get a listing of the files in archive directory; fix the problem and try again.', cursesThread)
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
        debugLogger.error("The OS restoration archive '" + archiveImageDir + '/' + osArchiveFileRegex.pattern + "' could not be found.")
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage('The OS restoration archive could not be found; fix the problem and try again.', cursesThread)
    if not os.path.isfile(osRestorationArchiveMd5sumFile):
        debugLogger.error("The OS restoration archive's md5sum file '" + osRestorationArchiveMd5sumFile + "' is missing.")
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("The OS restoration archive's md5sum file is missing; fix the problem and try again.", cursesThread)
    command = 'md5sum ' + osRestorationArchiveFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to determine the md5sum of the OS restoration archive '" + osRestorationArchiveFile + "'.\n" + err + '\n' + out)
        debugLogger.info('The command used to determine the md5sum of the OS restoration archive was: ' + command)
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage('Unable to determine the md5sum of the OS restoration archive; fix the problem and try again.', cursesThread)
    try:
        osRestorationArchiveMd5sum = re.match('([0-9,a-f]*)\\s+', out).group(1)
    except AttributeError as err:
        debugLogger.error('There was a match error when trying to get the md5sum of the OS restoration archive.\n' + out + '\n' + str(err))
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage('There was an error when trying to get the md5sum of the OS restoration archive; fix the problem and try again.', cursesThread)

    try:
        with open(osRestorationArchiveMd5sumFile) as f:
            for line in f:
                line = line.strip()
                if file in line:
                    originalOSRestorationArchiveMd5sum = re.match('([0-9,a-f]*)\\s+', line).group(1)

    except IOError as err:
        debugLogger.error("Unable to get the md5sum of the OS restoration archive from '" + osRestorationArchiveMd5sumFile + "'.\n" + str(err))
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("Unable to get the md5sum of the OS restoration archive from '" + osRestorationArchiveMd5sumFile + "'; fix the problem and try again.", cursesThread)
    except AttributeError as err:
        debugLogger.error("There was a match error when trying to match against '" + line + "'.\n" + str(err))
        updateOSestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage("There was a match error when matching against '" + line + "'; fix the problem and try again.", cursesThread)

    if osRestorationArchiveMd5sum != originalOSRestorationArchiveMd5sum:
        debugLogger.error("The OS restoration archive '" + osRestorationArchiveFile + "' is corrupt; its md5sum does not match its md5sum in '" + osRestorationArchiveMd5sumFile + "'.")
        updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile)
        displayErrorMessage('The OS restoration archive is corrupt; fix the problem and try again.', cursesThread)
    logger.info('Done checking the OS restoration archive to make sure it is not corrupt.')
    return osRestorationArchiveFile


def updateOSRestorationArchiveErrorFile(osRestorationArchiveErrorFile, cursesThread):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
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
        debugLogger.error('Could not write to the OS restoration archive error file ' + osRestorationArchiveErrorFile + '.\n' + str(err))
        displayErrorMessage('Could not write to the OS restoration archive error file; fix the problem and try again.', cursesThread)

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


def updateMultipathConf(cursesThread):
    errorMessage = ''
    started = False
    vendorMatched = False
    productMatched = False
    blackListPresent = False
    blacklist = '\'\n\n#Added so that HPE controllers are ignored by multipath.\nblacklist {\n\tdevnode         "^(ram|raw|loop|fd|md|dm-|sr|scd|st)[0-9]*"\n\tdevnode         "^hd[a-z][[0-9]*]"\n\n\tdevice {\n\t\tvendor "HP"\n\t\tproduct "LOGICAL VOLUME.*"\n\t}\n}\''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
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
            debugLogger.error('Failed to update /etc/multipath.conf to blacklist HPE controllers.\n' + err + '\n' + out)
            debugLogger.info('The command used to update /etc/multipath.conf to blacklist HPE controllers was: \n' + command)
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
            debugLogger.info('The blacklist for /etc/multipath.conf was not updated, since it is already up to date.')
        else:
            command = 'echo -e ' + blacklist + ' >> /etc/multipath.conf'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('Failed to update /etc/multipath.conf to blacklist HPE controllers.\n' + err + '\n' + out)
                debugLogger.info('The command used to update /etc/multipath.conf to blacklist HPE controllers was: \n' + command)
                errorMessage = 'Failed to update /etc/multipath.conf to blacklist HPE controllers; thus /etc/multipath.conf will have to be updated manually.'
    logger.info('Done updating /etc/multipath.conf to blacklist HPE controllers.')
    return errorMessage


def configureMellanox(programParentDir, osDist):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Configuring the Mellanox cards.')
    mellanoxDriverRPM = programParentDir + '/mellanoxDriver/*.rpm'
    command = 'rpm -Uvh ' + mellanoxDriverRPM
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to install the Mellanox driver.\n' + err + '\n' + out)
        return 'Failed to install the Mellanox driver.'
    mellanoxBusList = []
    command = 'lspci -mvv'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Failed to get the lspci output used to get the Compute Node's Mellanox NIC bus list.\n" + err + '\n' + out)
        debugLogger.info("The command to get the lspci output, which is used to get the Compute Node's Mellanox NIC bus list was: " + command)
        return "Failed to get the lspci output used to get the Compute Node's Mellanox NIC bus list."
    out = re.sub('\n{2,}', '####', out)
    deviceList = out.split('####')
    debugLogger.info('The lspci device list was: ' + str(deviceList))
    for device in deviceList:
        if ('Ethernet controller' in device or 'Network controller' in device) and 'Mellanox' in device:
            try:
                bus = re.match('\\s*[a-zA-Z]+:\\s+([0-9a-f]{2}:[0-9a-f]{2}\\.[0-9])', device, re.MULTILINE | re.DOTALL).group(1)
                debugLogger.info('The bus information for device:\n' + device[0:100] + '\nwas determined to be: ' + bus + '.\n')
                mellanoxBusList.append(bus)
            except AttributeError as err:
                debugLogger.error('An AttributeError was encountered while getting the Mellanox nic bus information: ' + str(err) + '\n' + device[0:200])
                return 'An AttributeError was encountered while getting the Mellanox nic bus information.'

    errorsEncountered = False
    for bus in mellanoxBusList:
        command = 'connectx_port_config -d ' + bus + ' -c eth,eth'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Failed to update Mellanox bus '" + bus + "' configuration from infininband to ethernet.\n" + err + '\n' + out)
            return 'Failed to update the Mellanox bus configuration from infininband to ethernet.'
        if osDist == 'SLES':
            ifcfgFileList = glob.glob('/etc/sysconfig/network/ifcfg-ib*')
        else:
            ifcfgFileList = glob.glob('/etc/sysconfig/network-scripts/ifcfg-ib*')
        if len(ifcfgFileList) != 0:
            if osDist == 'SLES':
                command = 'rm -f /etc/sysconfig/network/ifcfg-ib*'
            else:
                command = 'rm -f /etc/sysconfig/network-scripts/ifcfg-ib*'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.warn('Failed to remove the Mellanox infiniband configuration files ' + str(ifcfgFileList) + '.\n' + err + '\n' + out)

    logger.info('Done configuring the Mellanox cards.')
    return errorMessage


def setTimezone(programParentDir, cursesThread):
    errorMessage = ''
    linkFileExists = False
    timezoneFile = programParentDir + '/timezoneData/timezoneLinks'
    localTimeFile = programParentDir + '/timezoneData/localtime'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Setting the server's time zone.")
    cursesThread.insertMessage(['informative', "Setting the server's time zone."])
    cursesThread.insertMessage(['informative', ''])
    if os.path.isfile(localTimeFile):
        try:
            shutil.copy(localTimeFile, '/etc')
        except IOError as err:
            debugLogger.error("Unable to copy '" + localTimeFile + "' to /etc/localtime.\n" + str(err))
            errorMessage = "Unable to copy '" + localTimeFile + "' into place; thus the server's time zone was not set."

    else:
        try:
            with open(timezoneFile) as f:
                timezoneLinkData = f.readlines()
        except IOError as err:
            debugLogger.error("Unable to get the time zone link list from '" + timezoneFile + "'.\n" + str(err))
            errorMessage = "Unable to get the time zone link list; thus the server's time zone was not set."
            return errorMessage

        try:
            os.remove('/etc/localtime')
        except OSError as err:
            debugLogger.warn('The following error was encounterd while removing /etc/localtime: ' + str(err))

        for link in timezoneLinkData:
            link = link.strip()
            if os.path.isfile(link):
                linkFileExists = True
                command = 'ln ' + link + ' /etc/localtime'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    debugLogger.error("Problems were encountered while linking /etc/localtime to '" + link + "'.\n" + err + '\n' + out)
                    debugLogger.info("The command used to link /etc/localtime to '" + link + "' was: " + command)
                    errorMessage = "Problems were encountered while linking /etc/localtime; thus the server's time zone was not set."
                    return errorMessage
                break

        if not linkFileExists:
            debugLogger.error('There was not a link file present for /etc/localtime to link against; the selection of link files was: ' + str(timezoneLinkData))
            errorMessage = "There was not a link file present for /etc/localtime to link against; thus the server's time zone was not set."
    logger.info("Done setting the server's time zone.")
    return errorMessage


def checkServices():
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking systemd services for failures.')
    print GREEN + 'Checking systemd services for failures.' + RESETCOLORS
    command = 'systemctl --all --no-pager --failed'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while checking systemd services for failures.\n' + err + '\n' + out)
        debugLogger.info('The command used to check systemd services for failures was: ' + command)
        errorsEncountered = True
    elif re.match('\\s*0 loaded units listed', out, re.DOTALL | re.MULTILINE) == None:
        debugLogger.error('There were systemd services with failures.\n' + out)
        debugLogger.info('The command used to check systemd services for failures was: ' + command)
        errorsEncountered = True
    logger.info('Done checking systemd services for failures.')
    return errorsEncountered


def disableServices(disableServiceList, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Disabling systemd services.')
    cursesThread.insertMessage(['informative', 'Disabling systemd services.'])
    cursesThread.insertMessage(['informative', ''])
    debugLogger.info('The list of services to be disabled was: ' + str(disableServiceList))
    for service in disableServiceList:
        command = 'systemctl disable ' + service
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Problems were encountered while disabling the service '" + service + "'.\n" + err + '\n' + out)
            debugLogger.info("The command used to disable the service '" + service + "' was: " + command)
            if len(errorMessage) == 0:
                errorMessage = 'Problems were encountered while disabling systemd services.'
        time.sleep(1.0)

    logger.info('Done disabling systemd services.')
    return errorMessage