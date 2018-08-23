# Embedded file name: ./computeNode.py
import subprocess
import re
import logging
import os
RED = '\x1b[31m'
GREEN = '\x1b[32m'
RESETCOLORS = '\x1b[0m'

def getServerModel():
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Getting the server's model information.")
    print GREEN + "Getting the server's model information." + RESETCOLORS
    command = 'dmidecode -s system-product-name'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    if result.returncode != 0:
        debugLogger.error("Unable to get the server's model information.\n" + err + '\n' + out)
        print RED + "Unable to get the server's model information; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    if 'Superdome' in out:
        serverModel = 'Superdome'
    else:
        serverModel = out
    debugLogger.info("The server's model was determined to be: " + serverModel + '.')
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
        osDist = 'SLES'
        if os.path.isfile('/etc/products.d/SUSE_SLES_SAP.prod'):
            productFile = '/etc/products.d/SUSE_SLES_SAP.prod'
        elif os.path.isfile('/etc/products.d/SLES_SAP.prod'):
            productFile = '/etc/products.d/SLES_SAP.prod'
        else:
            print RED + "Unable to determine the SLES OS distribution level, since the SLES product file (SUSE_SLES_SAP.prod or SLES_SAP.prod) was missing from the '/etc/products.d' directory; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        try:
            with open(productFile) as f:
                for line in f:
                    if 'SLES_SAP-release' in line:
                        osDistLevel = re.match('^.*version="([0-9]{2}.[0-9]{1}).*', line).group(1)
                        break

        except IOError as err:
            print RED + 'Unable to determine the SLES OS distribution level.\nError: ' + str(err) + '\nfix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

    elif 'red hat' in versionInfo:
        osDist = 'RHEL'
        command = 'cat /etc/redhat-release'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            print RED + 'Unable to determine the RHEL OS distribution level.\nError: ' + err + '\nfix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        out = out.strip()
        try:
            osDistLevel = re.match('.*release\\s+([6-7]{1}.[0-9]{1}).*', out, re.IGNORECASE).group(1)
        except AttributeError as err:
            print RED + "There was a RHEL OS distribution level match error when trying to match against '" + out + "':\n" + str(err) + RESETCOLORS
            exit(1)

    else:
        print RED + "The server's OS distribution is not supported; exiting program execution.\n" + out + RESETCOLORS
        exit(1)
    return (osDist, osDistLevel)


def getProcessorType():
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Getting the server's processor type.")
    print GREEN + "Getting the server's processor type." + RESETCOLORS
    processorDict = {'62': 'ivybridge',
     '63': 'haswell',
     '79': 'broadwell'}
    command = 'cat /proc/cpuinfo'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('There was a problem getting the cpu information.\n' + err + '\n' + out)
        debugLogger.info('The command used to get the cpu information was: ' + command)
        print RED + 'There was a problem getting the cpu information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    cpudata = out.splitlines()
    for line in cpudata:
        if re.match('\\s*model\\s+:\\s+[2-9]{2}', line) != None:
            try:
                processor = processorDict[re.match('\\s*model\\s+:\\s+([2-9]{2})', line).group(1)]
            except AttributeError as err:
                debugLogger.error("There was a match error when trying to match against '" + line + "'.\n" + str(err))
                print RED + "There was a match error when trying to match against '" + line + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)
            except KeyError as err:
                debugLogger.error('The processor model identifier (' + str(err) + ') was not present in the processor dictionary.')
                print RED + 'The server is unsupported, since it does not have a supported processor; exiting program execution.' + RESETCOLORS
                exit(1)

            break

    debugLogger.info("The server's processor type was determined to be: " + processor + '.')
    logger.info("Done getting the server's processor type.")
    return processor