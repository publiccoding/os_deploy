# Embedded file name: ./modules/computeNode.py
import subprocess
import re
import logging
import os
RED = '\x1b[31m'
GREEN = '\x1b[32m'
RESETCOLORS = '\x1b[0m'

def getServerModel():
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Getting the server's model information.")
    print GREEN + "Getting the server's model information." + RESETCOLORS
    command = 'dmidecode -s system-product-name'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    if result.returncode != 0:
        logger.error("Unable to get the server's model information.\n" + err + '\n' + out)
        print RED + "Unable to get the server's model information; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    logger.info("The server's model was determined to be: " + out + '.')
    try:
        if 'Superdome' in out:
            serverModel = 'Superdome'
        else:
            serverModel = re.match('[a-z,0-9]+\\s+(.*)', out, re.IGNORECASE).group(1).replace(' ', '')
    except AttributeError as err:
        logger.error("There was a server model match error when trying to match against '" + out + "'.\n" + str(err))
        print RED + "There was a server model match error when trying to match against '" + out + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    logger.info("Done getting the server's model information.")
    return serverModel


def getOSDistribution():
    print GREEN + 'Getting the OS distribution installed on the server.' + RESETCOLORS
    command = 'cat /proc/version'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        print RED + "Unable to get the server's OS distribution information; fix the problem and try again; exiting program execution.\n" + err + RESETCOLORS
        exit(1)
    versionInfo = out.lower()
    if 'suse' in versionInfo:
        OSDist = 'SLES'
    elif 'red hat' in versionInfo:
        OSDist = 'RHEL'
    else:
        print RED + "The server's OS distribution is not supported; fix the problem and try again; exiting program execution.\n" + out + RESETCOLORS
        exit(1)
    return OSDist


def getProcessorType():
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Getting the server's processor type and checking to ensure it is an Ivy Bridge or Haswell processor.")
    print GREEN + "Getting the server's processor type and checking to ensure it is an Ivy Bridge or Haswell processor." + RESETCOLORS
    processorDict = {'62': 'ivybridge',
     '63': 'haswell'}
    command = 'cat /proc/cpuinfo'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('There was a problem getting the cpu information.\n' + err + '\n' + out)
        print RED + 'There was a problem getting the cpu information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    cpudata = out.splitlines()
    for line in cpudata:
        if re.match('\\s*model\\s+:\\s+[2-9]{2}', line) != None:
            try:
                processor = processorDict[re.match('\\s*model\\s+:\\s+([2-9]{2})', line).group(1)]
            except AttributeError as err:
                logger.error("There was a match error when trying to match against '" + line + "'.\n" + str(err))
                print RED + "There was a match error when trying to match against '" + line + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)
            except KeyError as err:
                logger.error('The resource key ' + str(err) + ' was not present in the processor dictionary.')
                print RED + 'The resource key ' + str(err) + ' was not present in the processor dictionary, which means the server is unsupported; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

            break

    logger.info("The server's processor type was determined to be: " + processor + '.')
    logger.info("Done getting the server's processor type and checking to ensure it is an Ivy Bridge or Haswell processor.")
    return processor


def getHostname(upgradeWorkingDir):
    hostnameDir = upgradeWorkingDir + '/hostnameData'
    hostnameFile = hostnameDir + '/hostname'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Getting the server's hostname.")
    print GREEN + "Getting the server's hostname." + RESETCOLORS
    hostname = os.uname()[1]
    logger.info("The server's hostname was determined to be: " + hostname + '.')
    if not os.path.isdir(hostnameDir):
        try:
            os.mkdir(hostnameDir)
        except OSError as err:
            logger.error("Unable to create the pre-upgrade hostname data directory '" + hostnameDir + "'.\n" + str(err))
            print RED + "Unable to create the pre-upgrade hostname data directory '" + hostnameDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    try:
        f = open(hostnameFile, 'w')
        f.write(hostname)
    except IOError as err:
        logger.error("Could not write the server's hostname '" + hostname + "' to '" + hostnameFile + "'.\n" + str(err))
        print RED + "Could not write server's hostname '" + hostname + "' to '" + hostnameFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    f.close()
    logger.info("Done getting the server's hostname.")