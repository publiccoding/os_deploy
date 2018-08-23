# Embedded file name: ./computeNode.py
import subprocess
import re
import logging
import os
import shutil
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
        debugLogger.error("The command used to get the server's model information was: " + command)
        print RED + "Unable to get the server's model information; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    debugLogger.info("The server's model was determined to be: " + out + '.')
    if 'Superdome' in out:
        serverModel = 'Superdome'
    else:
        serverModel = out
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
     '63': 'haswell'}
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


def getHostname(upgradeWorkingDir):
    hostnameDir = upgradeWorkingDir + '/hostnameData'
    hostnameFile = hostnameDir + '/hostname'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Getting the server's hostname.")
    print GREEN + "Getting the server's hostname." + RESETCOLORS
    hostname = os.uname()[1]
    debugLogger.info("The server's hostname was determined to be: " + hostname + '.')
    if not os.path.isdir(hostnameDir):
        try:
            os.mkdir(hostnameDir)
        except OSError as err:
            debugLogger.error("Unable to create the pre-upgrade hostname data directory '" + hostnameDir + "'.\n" + str(err))
            print RED + 'Unable to create the pre-upgrade hostname data directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

    try:
        f = open(hostnameFile, 'w')
        f.write(hostname)
    except IOError as err:
        debugLogger.error("Could not write the server's hostname '" + hostname + "' to '" + hostnameFile + "'.\n" + str(err))
        print RED + "Could not write out the server's hostname; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    f.close()
    logger.info("Done getting the server's hostname.")


def getLocalTimeLink(upgradeWorkingDir):
    timezoneDir = upgradeWorkingDir + '/timezoneData'
    timezoneFile = timezoneDir + '/timezoneLinks'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Getting the server's time zone information.")
    print GREEN + "Getting the server's time zone information." + RESETCOLORS
    if not os.path.isfile('/etc/localtime'):
        debugLogger.error('/etc/localtime is missing.')
        print RED + '/etc/localtime is missing; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if not os.path.isdir(timezoneDir):
        try:
            os.mkdir(timezoneDir)
        except OSError as err:
            debugLogger.error("Unable to create the pre-upgrade time zone data directory '" + timezoneDir + "'.\n" + str(err))
            print RED + "Unable to create the pre-upgrade time zone data directory '" + timezoneDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    command = 'ls -li /etc/localtime'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get the file attributes of /etc/localtime.\n' + err + '\n' + out)
        debugLogger.info('The command used to get the file attributes of /etc/localtime was:' + command)
        print RED + 'Unable to get the file attributes of /etc/localtime; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    out = out.strip()
    debugLogger.info('The output of the command (' + command + ') used to get the file attributes of /etc/localtime was: ' + out)
    if '->' in out:
        if re.match('.*(/usr/share/zoneinfo.*)', out):
            try:
                localTimeLink = re.match('.*(/usr/share/zoneinfo.*)', out).group(1)
            except AttributeError as err:
                debugLogger.error('Unable to get the file that /etc/localtime is linked against.\n' + out + '\n' + str(err))
                print RED + 'Unable to get the file that /etc/localtime is linked against; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

            if not os.path.isfile(localTimeLink):
                debugLogger.error('Unable to get the file that /etc/localtime is linked against, since the link is broken.\n' + out)
                print RED + 'Unable to get the file that /etc/localtime is linked against, since the link is broken; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
        else:
            debugLogger.error('Unable to get the file that /etc/localtime is linked against off of /usr/share/zoneinfo.\n' + out)
            print RED + 'Unable to get the file that /etc/localtime is linked against; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        try:
            f = open(timezoneFile, 'w')
            f.write(localTimeLink)
        except IOError as err:
            debugLogger.error("Could not write the link file '" + localTimeLink + "' that /etc/localtime is linked against to '" + timezoneFile + "'.\n" + str(err))
            print RED + 'Could not write the link file that /etc/localtime is linked against; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        finally:
            f.close()

    else:
        try:
            inode = re.match('([0-9]+)', out).group(1)
        except AttributeError as err:
            debugLogger.error('There was a match error when trying to match against\n' + out + '\n' + str(err))
            print 'Unable to get the inode number of /etc/localtime; fix the problem and try again; exiting program execution.'
            exit(1)

        command = 'find /usr/share/zoneinfo -inum ' + inode
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Unable to get the file(s) that /etc/localtime is linked against.\n' + err + '\n' + out)
            debugLogger.info('The command used to get the file(s) that /etc/localtime is linked against was: ' + command)
            print RED + 'Unable to get the file(s) that /etc/localtime is linked against; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        out = out.strip()
        if out == '':
            command = 'file /etc/localtime'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('Unable to get the file type of /etc/localtime.\n' + err + '\n' + out)
                debugLogger.info('The command used to get the file type of /etc/localtime was: ' + command)
                print RED + 'Unable to get the file type of /etc/localtime; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            if 'timezone data' not in out:
                debugLogger.error('/etc/localtime is not a time zone file.\n' + out)
                debugLogger.info('The command used to check if /etc/localtime was a time zone data file was: ' + command)
                print RED + '/etc/localtime is not a time zone file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            else:
                try:
                    shutil.copy2('/etc/localtime', timezoneDir)
                except IOError as err:
                    debugLogger.error("Unable to copy '/etc/localtime' to '" + timezoneDir + "'.\n" + str(err))
                    print RED + 'Unable to get a copy of the localtime file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

        else:
            localTimeLinkList = out.splitlines()
            debugLogger.info("The output list of files from '" + command + "' was: " + str(localTimeLinkList))
            try:
                f = open(timezoneFile, 'w')
                for link in localTimeLinkList:
                    if not link == localTimeLinkList[-1:]:
                        f.write(link + '\n')
                    else:
                        f.write(link)

            except IOError as err:
                debugLogger.error('Could not write the link file(s) \n' + str(localTimeLinkList) + "\nthat /etc/localtime is linked against to '" + timezoneFile + "'.\n" + str(err))
                print RED + 'Could not write the link file(s) that /etc/localtime is linked against; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            finally:
                f.close()

    logger.info("Done getting the server's time zone information.")