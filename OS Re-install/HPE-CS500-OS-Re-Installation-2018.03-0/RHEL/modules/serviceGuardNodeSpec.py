# Embedded file name: ./modules/serviceGuardNodeSpec.py
import subprocess
import logging
import re
import os
RED = '\x1b[31m'
GREEN = '\x1b[32m'
RESETCOLORS = '\x1b[0m'

def checkCluster():
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking the cluster status and attempting to halt it if it is running.')
    command = 'cmviewcl -f line'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("There was a problem getting the cluster's status.\n" + err + '\n' + out)
        return
    else:
        if re.search('status\\s*=\\s*up', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None:
            command = 'cmhaltcl -f'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error('Problems were encountered while attempting to halt the cluster.\n' + err + '\n' + out)
                return
        else:
            logger.info('The cluster appears to already be halted.')
        logger.info('Done checking the cluster status and attempting to halt it if it is running.')
        return


def buildDeadmanDriver(cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Building and installing the deadman driver.')
    cursesThread.insertMessage(['informative', 'Building and installing the deadman driver.'])
    cursesThread.insertMessage(['informative', ''])
    sgDriverDir = '/opt/cmcluster/drivers'
    cwd = os.getcwd()
    try:
        os.chdir(sgDriverDir)
    except OSError as err:
        logger.error("Could not change into the deadman drivers directory '" + sgDriverDir + "'.\n" + str(err))
        errorMessage = 'Could not change into the deadman drivers directory; thus the driver was not built and installed.'
        return errorMessage

    driverBuildCommandsList = ['make modules', 'make modules_install', 'depmod -a']
    for command in driverBuildCommandsList:
        buildCommand = command
        result = subprocess.Popen(buildCommand, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Failed to build and install the deadman driver.\n' + err + '\n' + out)
            errorMessage = 'Failed to build and install the deadman driver; thus the driver was not built and installed.'

    try:
        os.chdir(cwd)
    except:
        pass

    logger.info('Done building and installing the deadman driver.')
    return errorMessage


def configureXinetd(cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Configuring and starting xinetd.')
    cursesThread.insertMessage(['informative', 'Configuring and starting xinetd.'])
    cursesThread.insertMessage(['informative', ''])
    command = 'chkconfig --level 35 xinetd on'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Failed to configure xinetd.\n' + err + '\n' + out)
        errorMessage = 'Failed to configure xinetd; thus xinetd will have to be configured and started manually.'
        return errorMessage
    command = 'systemctl start xinetd'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Failed to start xinetd.\n' + err + '\n' + out)
        errorMessage = 'Failed to start xinetd; thus xinetd will have to be configured and started manually.'
        return errorMessage
    logger.info('Done configuring and starting xinetd.')
    return errorMessage


def updateNFSListeners(cursesThread):
    errorMessage = ''
    nfsToolkitDir = '/opt/cmcluster/nfstoolkit'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Updating the Serviceguard NFS toolkit variable 'RPCNFSDCOUNT' to be set to 64.")
    cursesThread.insertMessage(['informative', "Updating the Serviceguard NFS toolkit variable 'RPCNFSDCOUNT' to be set to 64."])
    cursesThread.insertMessage(['informative', ''])
    cwd = os.getcwd()
    try:
        os.chdir(nfsToolkitDir)
    except OSError as err:
        logger.error("Could not change into the NFS toolkit directory '" + nfsToolkitDir + "'.\n" + str(err))
        errorMessage = "Could not change into the NFS toolkit directory; thus the NFS toolkit variable 'RPCNFSDCOUNT' was not updated to 64."
        return errorMessage

    command = "sed -ri '0,/^\\s*RPCNFSDCOUNT\\s*=\\s*[0-9]+.*/s//RPCNFSDCOUNT=64/'  *.sh"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Failed to update the Serviceguard NFS toolkit variable 'RPCNFSDCOUNT'.\n" + err + '\n' + out)
        errorMessage = "Failed to update the Serviceguard NFS toolkit variable 'RPCNFSDCOUNT' to 64; thus the variable will have to be updated manually."
    try:
        os.chdir(cwd)
    except:
        pass

    logger.info("Done updating the Serviceguard NFS toolkit variable 'RPCNFSDCOUNT' to be set to 64.")
    return errorMessage


def createNFSMountPoint(cursesThread):
    errorMessage = ''
    mountPoint = '/hananfs'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Creating the 'hananfs' mount point if necessary.")
    cursesThread.insertMessage(['informative', "Creating the 'hananfs' mount point if necessary."])
    cursesThread.insertMessage(['informative', ''])
    if not os.path.isdir(mountPoint):
        try:
            os.mkdir(mountPoint)
        except OSError as err:
            logger.error("Problems were encountered while creating the 'hananfs' mount point.\n" + str(err))
            errorMessage = "Problems were encountered while creating the 'hananfs' mount point; thus it will need to be created manually."
            return errorMessage

    logger.info("Done creating the 'hananfs' mount point if necessary.")
    return errorMessage


def updateClusterCfg():
    nicsRenamed = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Performing post update of NFS Serviceguard cluster.')
    clusterCfgFile = '/opt/cmcluster/conf/hananfs/hananfs.ascii'
    pkgCfgFile = '/opt/cmcluster/conf/hananfs/nfs/nfs.conf'
    cfgFileList = [clusterCfgFile, pkgCfgFile]
    cfgFileStrList = ['cluster configuration file', 'package configuration file']
    while True:
        count = 0
        while True:
            response = raw_input("Is '" + cfgFileList[count] + "' the current " + cfgFileStrList[count] + ' [y/n]: ')
            response = response.lower().strip()
            if response != 'y' and response != 'n':
                print RED + 'An invalid entry was provided; please try again.\n' + RESETCOLORS
                continue
            if response == 'y':
                if count > 0:
                    break
                else:
                    count += 1
            else:
                while True:
                    if count == 0:
                        clusterCfgFile = raw_input('Please provide the name (full path) of the cluster configuration file: ')
                        cfgFile = clusterCfgFile
                    else:
                        pkgCfgFile = raw_input('Please provide the name (full path) of the package configuration file: ')
                        cfgFile = pkgCfgFile
                    if not os.path.isfile(cfgFile):
                        print RED + 'An invalid entry was provided; please try again.' + RESETCOLORS
                    else:
                        break

                break

        while True:
            response = raw_input('Where any of the NICs renamed on either node [y/n]: ')
            response = response.lower().strip()
            if response != 'y' and response != 'n':
                print RED + 'An invalid entry was provided; please try again.\n' + RESETCOLORS
                continue
            if response == 'y':
                nicsRenamed = True
                break
            else:
                break

        if nicsRenamed:
            interfaceNameList = []
            nodeNameList, ipAddressList = getSGNodeReferences(clusterCfgFile)
            locationCount = 0
            for node in nodeNameList:
                count = 0
                while count < 2:
                    nicName = raw_input('Please provide the name of the NIC cooresponding to ' + node + "'s heartbeat IP " + ipAddressList[locationCount] + ': ')
                    interfaceNameList.append(nicName.strip())
                    locationCount += 1
                    count += 1

        print '\nThe current cluster configuration file is: ' + clusterCfgFile + '.'
        print 'The current package configuration file is: ' + pkgCfgFile + '.'
        if nicsRenamed:
            print '\nThe current node NIC mapping is:'
            locationCount = 0
            for node in nodeNameList:
                print '\tNode name: ' + node
                count = 0
                while count < 2:
                    print '\t\tNetwork interface name = ' + interfaceNameList[locationCount]
                    print '\t\tNetwork interface IP = ' + ipAddressList[locationCount] + '\n'
                    locationCount += 1
                    count += 1

        while True:
            response = raw_input('Is the above information correct[y/n]: ')
            response = response.lower().strip()
            if response != 'y' and response != 'n':
                print RED + 'An invalid entry was provided; please try again.\n' + RESETCOLORS
            else:
                break

        if response == 'y':
            break

    if nicsRenamed:
        try:
            with open(clusterCfgFile) as f:
                currentCfgList = f.read().splitlines()
        except IOError as err:
            logger.error("Unable to read the cluster's configuration file '" + clusterCfgFile + "'.\n" + str(err))
            print RED + "Unable to read the cluster's configuration file; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

        updatedCfgList = []
        count = 0
        for line in currentCfgList:
            if re.match('\\s*NETWORK_INTERFACE\\s+', line) != None and 'bond' not in line:
                updatedLine = re.sub('[0-9a-z]+$', interfaceNameList[count], line)
                updatedCfgList.append(updatedLine)
                count += 1
            else:
                updatedCfgList.append(line)

        try:
            f = open(clusterCfgFile, 'w')
            for line in updatedCfgList:
                f.write(line + '\n')

        except IOError as err:
            logger.error("Unable to write to the cluster's configuration file '" + clusterCfgFile + "'.\n" + str(err))
            print RED + "Unable to write to the cluster's configuration file; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

        f.close()
    print "\tChecking the cluster's configuration file."
    command = '/opt/cmcluster/bin/cmcheckconf -C ' + clusterCfgFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
    out, err = result.communicate(input='y')
    if result.returncode != 0:
        logger.error("There appears to be a problem with the cluster's configuration file '" + clusterCfgFile + "'.\n" + err + '\n' + out)
        print RED + "There appears to be a problem with the cluster's configuration file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    print "\tApplying the cluster's configuration file."
    command = '/opt/cmcluster/bin/cmapplyconf -C ' + clusterCfgFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
    out, err = result.communicate(input='y')
    if result.returncode != 0:
        logger.error("Unable to apply the cluster's updated configuration from '" + clusterCfgFile + "'.\n" + err + '\n' + out)
        print RED + "Unable to apply the cluster's updated configuration; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    print "\tChecking the package's configuration file."
    command = '/opt/cmcluster/bin/cmcheckconf -P ' + pkgCfgFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
    out, err = result.communicate(input='y')
    if result.returncode != 0:
        logger.error("There appears to be a problem with the packages's configuration file '" + pkgCfgFile + "'.\n" + err + '\n' + out)
        print RED + "There appears to be a problem with the packages's configuration file; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    print "\tApplying the package's configuration file."
    command = '/opt/cmcluster/bin/cmapplyconf -P ' + pkgCfgFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
    out, err = result.communicate(input='y')
    if result.returncode != 0:
        logger.error("Unable to apply the package's configuration from '" + pkgCfgFile + "'.\n" + err + '\n' + out)
        print RED + "Unable to apply the package's configuration; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    else:
        print GREEN + 'The cluster configuration was successfully updated; perform a functional check of the cluster to ensure it is functioning as expected.' + RESETCOLORS
    logger.info('Done performing post update of NFS Serviceguard cluster.')
    return


def getSGNodeReferences(clusterCfgFile):
    nodeNameList = []
    ipAddressList = []
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Getting the names of the nodes in the cluster.')
    command = 'cat ' + clusterCfgFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Unable to get cluster information from '" + clusterCfgFile + "'.\n" + err + '\n' + out)
        print RED + "Unable to get cluster information from '" + clusterCfgFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    clusterData = out.splitlines()
    nicCount = 0
    try:
        for line in clusterData:
            line = line.strip()
            if re.match('NODE_NAME\\s+(.*)', line) != None:
                nodeNameList.append(re.match('NODE_NAME\\s+(.*)', line).group(1))
            if re.match('STATIONARY_IP\\s+(.*)', line) != None:
                ipAddressList.append(re.match('STATIONARY_IP\\s+(.*)', line).group(1))
                nicCount += 1
            if nicCount == 4:
                break

    except AttributeError as err:
        logger.error("There was a match error when trying to match against '" + line + "'.\n" + str(err))
        print RED + "There was a match error when trying to match against '" + line + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    if len(nodeNameList) != 2:
        logger.error('There was a problem getting the node names. There should be two nodes: ' + str(nodeNameList))
        print RED + 'There was a problem getting the node names. There should be two nodes; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if len(ipAddressList) != 4:
        logger.error('There was a problem getting the NIC IPs. There should be four IPs (two for each node): ' + str(ipAddressList))
        print RED + 'There was a problem getting the NIC IPs. There should be four IPs (two for each node); fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done getting the names of the nodes in the cluster.')
    return (nodeNameList, ipAddressList)


def updateLvmConf(cursesThread):
    errorMessage = ''
    lvmConfFile = '/etc/lvm/lvm.conf'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Adding a tags entry to '" + lvmConfFile + "'.")
    cursesThread.insertMessage(['informative', "Adding a tags entry to '" + lvmConfFile + "'."])
    cursesThread.insertMessage(['informative', ''])
    command = 'echo "tags {hosttags = 1}" >> ' + lvmConfFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Failed to add 'tags {hosttags = 1}' to '" + lvmConfFile + "'.\n" + err + '\n' + out)
        errorMessage = "Failed to add the tags entry to '" + lvmConfFile + "'; thus lvm.conf will have to be updated manually."
    logger.info("Done adding a tags entry to '" + lvmConfFile + "'.")
    return errorMessage