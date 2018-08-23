# Embedded file name: ./rhelUpgrade.py
import os
import re
import glob
import shutil
import sys
import logging
import traceback
import optparse
import datetime
import time
import subprocess
import threading
from modules.computeNode import getServerModel, getOSDistribution
RED = '\x1b[31m'
YELLOW = '\x1b[33m'
GREEN = '\x1b[32m'
RESETCOLORS = '\x1b[0m'

class UpgradeFeedbackThread(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.stop = False
        self.message = ''

    def run(self):
        i = 0
        while self.stop != True:
            timeStamp = time.strftime('%H:%M:%S', time.gmtime(i))
            feedbackMessage = self.message + ': ' + timeStamp
            sys.stdout.write('\r' + feedbackMessage)
            sys.stdout.flush()
            time.sleep(1.0)
            i += 1

    def stopThread(self):
        self.stop = True

    def setMessage(self, message):
        self.message = message


def processRPMS(processType, *args):
    upgradeLogger = logging.getLogger('coeOSUpgradeLogger')
    if processType == 'upgradeServer':
        command = 'yum update --noplugins -y'
    elif processType == 'installAdditionalRPMS':
        command = 'yum install --noplugins ' + ' '.join(args[0]) + ' -y'
    else:
        command = 'yum update-minimal --security -y'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    while True:
        output = result.stdout.readline().rstrip()
        if not output:
            break
        yield output

    out, err = result.communicate()
    if result.returncode != 0:
        if processType == 'upgradeServer':
            upgradeLogger.error('Errors were encountered while upgrading the server.\n' + err + '\n' + out)
            upgradeLogger.info('The command used to upgrade the server was: ' + command)
            print RED + '\nErrors were encountered while upgrading the server; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        elif processType == 'installAdditionalRPMS':
            upgradeLogger.error('Errors were encountered while installing the additional RPMS based on the reference RPM list and what RPMS are currently installed.\n' + err + '\n' + out)
            upgradeLogger.info('The command used to install the additional RPMS based on the reference RPM list and what RPMS are currently installed was: ' + command)
            print RED + '\nErrors were encountered while installing the additional RPMS based on the reference RPM list and what RPMS are currently installed; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        else:
            upgradeLogger.error('Errors were encounterd while applying the security patches to the server.\n' + err + '\n' + out)
            upgradeLogger.info('The command used to apply the security patches to the server was: ' + command)
            print RED + '\nErrors were encountered while applying the security patches to the server; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)


def cleanupGrubCfg():
    timestamp = datetime.datetime.now().strftime('%d%H%M%S%b%Y')
    cmdlineResource = 'GRUB_CMDLINE_LINUX'
    updatedCmdlineList = []
    errorsEncountered = False
    upgradeLogger = logging.getLogger('coeOSUpgradeLogger')
    upgradeLogger.info('Configuring /etc/default/grub.')
    try:
        shutil.copy('/etc/default/grub', '/etc/default/grub.SAVED.' + timestamp)
    except IOError as err:
        upgradeLogger.warn("Unable to backup the grub configuration file to '" + '/etc/default/grub.SAVED.' + timestamp + "'.\n" + str(err))

    command = "awk '/^[[:space:]]*GRUB_CMDLINE_LINUX/{print}' /etc/default/grub"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        upgradeLogger.error('Errors were encountered while getting the GRUB_CMDLINE_LINUX resource from /etc/default/grub.\n' + err + '\n' + out)
        upgradeLogger.info('The command used to get the GRUB_CMDLINE_LINUX resource from /etc/default/grub was: ' + command)
        print RED + '\nErrors were encountered while getting the GRUB_CMDLINE_LINUX resource from /etc/default/grub; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    out = out.strip()
    if out == '' or len(out.split('=')) != 2 or len(out.split('=')[1]) == 0:
        if not out == '':
            command = "sed -i '/^\\s*GRUB_CMDLINE_LINUX.*$/d' /etc/default/grub"
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                upgradeLogger.error('Errors were encountered while removing the GRUB_CMDLINE_LINUX resource from /etc/default/grub.\n' + err + '\n' + out)
                upgradeLogger.info('The command used to remove the GRUB_CMDLINE_LINUX resource from /etc/default/grub was: ' + command)
                print RED + '\nErrors were encountered while removing the GRUB_CMDLINE_LINUX resource from /etc/default/grub; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
        command = 'cat /proc/cmdline'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            upgradeLogger.error('Errors were encountered while getting the contents of /proc/cmdline.\n' + err + '\n' + out)
            upgradeLogger.info('The command used to get the contents of /proc/cmdline was: ' + command)
            print RED + '\nErrors were encountered while getting the  contents of /proc/cmdline; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        out = re.sub('\\s+,\\s+', ',', out).strip()
        cmdlineList = re.sub('\\s+=\\s+', '=', out).split()
        for item in cmdlineList:
            item = item.strip()
            if 'BOOT_IMAGE=' in item or 'root=' in item or 'crashkernel' in item or item.strip() == 'ro':
                continue
            if item not in updatedCmdlineList:
                if 'cstate' in item:
                    updatedCmdlineList.append(re.sub('=0', '=1', item))
                else:
                    updatedCmdlineList.append(item)

        updatedResource = cmdlineResource + '=' + '"' + ' '.join(updatedCmdlineList) + '"\n'
    else:
        command = "sed -i '/^\\s*GRUB_CMDLINE_LINUX.*$/d' /etc/default/grub"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            upgradeLogger.error('Errors were encountered while removing the GRUB_CMDLINE_LINUX resource from /etc/default/grub.\n' + err + '\n' + out)
            upgradeLogger.info('The command used to remove the GRUB_CMDLINE_LINUX resource from /etc/default/grub was: ' + command)
            print RED + '\nErrors were encountered while removing the GRUB_CMDLINE_LINUX resource from /etc/default/grub; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        resourceList = out.split('=', 1)
        kernelParameters = re.sub('\\s+,\\s+', ',', resourceList[1])
        kernelParameterList = re.sub('\\s+=\\s+', '=', resourceList[1].strip('"')).split()
        for item in kernelParameterList:
            item = item.strip()
            if 'crashkernel' in item:
                continue
            if item not in updatedCmdlineList:
                if 'cstate' in item:
                    updatedCmdlineList.append(re.sub('=0', '=1', item))
                else:
                    updatedCmdlineList.append(item)

        updatedResource = cmdlineResource + '=' + '"' + ' '.join(updatedCmdlineList) + '"\n'
    try:
        with open('/etc/default/grub', 'a') as f:
            f.write(updatedResource)
    except IOError as err:
        print 'Errors were encountered while adding the GRUB_CMDLINE_LINUX resource to /etc/default/grub.\n' + str(err)
        print RED + '\nErrors were encountered adding the GRUB_CMDLINE_LINUX resource to /etc/default/grub; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)


def main():
    programVersion = '1.0-0'
    programName = os.path.basename(sys.argv[0]).split('.')[0]
    programParentDir = os.path.dirname(os.path.realpath(__file__))
    errorsEncountered = False
    upgradeFeedbackThread = None
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS
        exit(1)
    usage = 'usage: %prog [-h] [-v]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-v', action='store_true', default=False, help="This option is used to display the application's version.")
    options, args = parser.parse_args()
    if options.v:
        print programName + ' ' + programVersion
        exit(0)
    osDist, _ = getOSDistribution()
    logDir = '/var/log/CoESapHANA_' + osDist + '_UpgradeLogDir'
    if not os.path.isdir(logDir):
        print RED + "The upgrade log directory '" + logDir + "' is missing, it was created by the preupgrade script; fix the problem and try again; exiting program execution.\n" + str(err) + RESETCOLORS
        exit(1)
    upgradeLogFile = logDir + '/upgrade.log'
    try:
        with open(logDir + '/upgradeVersionReference.log', 'r') as f:
            osUpgradeVersion = f.readline().strip()
    except OSError as err:
        upgradeLogger.error("Errors were encountered while reading the OS upgrade version log file '" + logDir + "/upgradeVersionReference.log'.\n" + str(err))
        print RED + 'Errors were encountered while reading the OS upgrade version log file; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    upgradeHandler = logging.FileHandler(upgradeLogFile)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    upgradeHandler.setFormatter(formatter)
    upgradeLogger = logging.getLogger('coeOSUpgradeLogger')
    upgradeLogger.setLevel(logging.INFO)
    upgradeLogger.addHandler(upgradeHandler)
    upgradeLogger.info("The program's version is: " + programVersion + '.')
    upgradeLogger.info('Upgrading the server to ' + osUpgradeVersion + '.')
    print GREEN + 'Upgrading the server to ' + osUpgradeVersion + '.' + RESETCOLORS
    serverModel = getServerModel()
    if 'DL580' in serverModel:
        motdInfo = 'HPE SAP HANA CS500 Converged System'
        releaseInfo = 'HPE SAP HANA CoE CS500'
    elif serverModel == 'ProLiant DL360 Gen9' or serverModel == 'ProLiant DL380p Gen8':
        motdInfo = 'HPE SAP HANA Serviceguard NFS Server'
        releaseInfo = 'HPE SAP HANA CoE Serviceguard NFS Server'
    elif serverModel == 'Superdome':
        motdInfo = 'HPE SAP HANA CS900 Converged System'
        releaseInfo = 'HPE SAP HANA CoE CS900'
    progressStatusFile = logDir + '/progress.log'
    try:
        if os.path.isfile(progressStatusFile):
            f = open(progressStatusFile, 'a+')
            progressDict = dict.fromkeys((x.strip() for x in f))
        else:
            f = open(progressStatusFile, 'w')
            progressDict = {}
        if 'cleanupGrubCfg' not in progressDict:
            cleanupGrubCfg()
            f.write('cleanupGrubCfg\n')
        if 'filesystemRPMUpgraded' not in progressDict:
            upgradeLogger.info('Updating the filesystem package.')
            command = 'rpm -Uvh /tmp/rhelFilesystemRPM/filesystem*.rpm'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                upgradeLogger.error('Failed to upgrade the filesystem RPM (/tmp/rhelFilesystemRPM/filesystem*.rpm):\n' + err + '\n' + out)
                print RED + 'Failed to upgrade the filesystem RPM (/tmp/rhelFilesystemRPM/filesystem*.rpm); fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            else:
                f.write('filesystemRPMUpgraded\n')
        imageDevice = '/dev/sr0'
        while True:
            command = 'mount -o loop ' + imageDevice + ' /mnt'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                if 'is already mounted' not in err.lower():
                    upgradeLogger.error('Failed to mount the RHEL DVD on /mnt.\n' + err + '\n' + out)
                    upgradeLogger.info('The command used to mount the RHEL DVD on /mnt was: ' + command)
                    upgradeLogger.info("Prompting for the DVD's scsci device file.")
                    print RED + 'Failed to mount the RHEL DVD using device file ' + imageDevice + '.\n' + RESETCOLORS
                    response = raw_input("Please provide the correct device file for the RHEL DVD (hint check dmesg (tail dmesg)) or 'q' to quit: ")
                    response = response.strip()
                    if response.lower() == 'q':
                        upgradeLogger.info('The upgrade was cancelled.')
                        exit(1)
                    else:
                        imageDevice = response
                else:
                    upgradeLogger.info('An attempt to mount the DVD reported that it was already mounted; thus, continuing the upgrade.\n' + err + '\n' + out)
                    break
            else:
                break

        try:
            command = 'yum --disablerepo=* clean all'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                if 'there are no enabled repos' not in err.lower():
                    upgradeLogger.error('Errors were encountered while disabling the current repositories.\n' + err + '\n' + out)
                    upgradeLogger.info('The command used to disable the current repositories was: ' + command)
                    print RED + 'Errors were encountered while disabling the current repositories; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)
            if os.path.isfile('/etc/yum.repos.d/HPECoERHELUpgrade.repo'):
                try:
                    os.remove('/etc/yum.repos.d/HPECoERHELUpgrade.repo')
                    time.sleep(1.0)
                except OSError as err:
                    upgradeLogger.error('Errors were encountered while removing the upgrade repository /etc/yum.repos.d/HPECoERHELUpgrade.repo.\n' + str(err))
                    print RED + 'Errors were encountered while removing the upgrade repository; the repository will need to be removed manually.' + RESETCOLORS
                    exit(1)

            if not os.path.isdir('/tmp/CoEYumRepoBackupDir'):
                try:
                    os.mkdir('/tmp/CoEYumRepoBackupDir')
                except OSError as err:
                    upgradeLogger.error('Errors were encountered while creating the yum repository backup directory /tmp/CoEYumRepoBackupDir.\n' + str(err))
                    print RED + 'Errors were encountered while creating the yum repository backup directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

                try:
                    repoFiles = os.listdir('/etc/yum.repos.d')
                    for file in repoFiles:
                        shutil.move('/etc/yum.repos.d/' + file, '/tmp/CoEYumRepoBackupDir/' + file)

                except (OSError, IOError, Error) as err:
                    upgradeLogger.error('Errors were encountered while moving the yum repository files from /etc/yum.repos.d to backup directory /tmp/CoEYumRepoBackupDir.\n' + str(err))
                    print RED + 'Errors were encountered while moving the yum repository files to the backup directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

            command = 'cp /mnt/media.repo /etc/yum.repos.d/HPECoERHELUpgrade.repo'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                upgradeLogger.error('Failed to get a copy of the RHEL DVD repo file.\n' + err + '\n' + out)
                upgradeLogger.info('The command used to get a copy of the RHEL DVD repo file was: ' + command)
                print RED + 'Failed to get a copy of the RHEL DVD repo file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            if 'serverUpgraded' not in progressDict:
                upgradeLogger.info('Updating the baseurl for the install media in the upgrade repo file /etc/yum.repos.d/HPECoERHELUpgrade.repo. Also, adding the SAPHana repository to the file.')
                try:
                    with open('/etc/yum.repos.d/HPECoERHELUpgrade.repo', 'a') as repoFile:
                        repoFile.write('baseurl=file:///mnt\n')
                        repoFile.write('enabled=1\n')
                        repoFile.write('\n')
                        repoFile.write('[SAP_HANA_RPMS]\n')
                        repoFile.write('name=SAP HANA RPMS\n')
                        repoFile.write('baseurl=file:///mnt/addons/SAPHana\n')
                        repoFile.write('enabled=1\n')
                        repoFile.write('gpgcheck=0\n')
                except OSError as err:
                    upgradeLogger.error('Errors were encountered while updating the upgrade repo file (/etc/yum.repos.d/HPECoERHELUpgrade.repo).\n' + str(err))
                    print RED + 'Errors were encountered while updating the upgrade repo file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

                upgradeLogger.info('Applying updates to upgrade the server.')
                upgradeFeedbackThread = UpgradeFeedbackThread()
                upgradeFeedbackThread.setMessage('Applying updates to upgrade the server.')
                upgradeFeedbackThread.start()
                for output in processRPMS('upgrade'):
                    upgradeLogger.info(output)

                f.write('serverUpgraded\n')
            if 'installedAdditionalRPMS' not in progressDict:
                command = 'rpm -qa --qf "%{NAME}\n" | sort > /tmp/currentRHEL7.4RPMList'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    upgradeLogger.error("Errors were encountered while getting the server's RPM list.\n" + err + '\n' + out)
                    upgradeLogger.info("The command used to get the server's RPM list was: " + command)
                    print RED + "\nErrors were encountered while getting the server's RPM list; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)
                command = 'comm -23 ' + programParentDir + '/rhelRPMReferenceList/rhel7.4RPMList /tmp/currentRHEL7.4RPMList'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    upgradeLogger.error('Errors were encountered while getting the list of RPMS that were not installed.\n' + err + '\n' + out)
                    upgradeLogger.info('The command used to get the list of RPMS that were not installed was: ' + command)
                    print RED + '\nErrors were encountered while getting the list of RPMS that were not installed; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)
                rpmsNotInstalledList = out.splitlines()
                if len(rpmsNotInstalledList) > 0:
                    upgradeLogger.info('Installing additional RPMS to enable uniformity amongst ConvergedSystems.')
                    if upgradeFeedbackThread == None:
                        upgradeFeedbackThread = UpgradeFeedbackThread()
                    upgradeFeedbackThread.setMessage('Installing additional RPMS to enable uniformity amongst ConvergedSystems.')
                    upgradeFeedbackThread.start()
                    for output in processRPMS('install'):
                        upgradeLogger.info(output)

                else:
                    upgradeLogger.info('A comparison of the RPMS installed and what was listed in RPM reference list showed that no additional RPMS needed to be installed.')
                f.write('installedAdditionalRPMS\n')
            if 'appliedSecurityPatches' not in progressDict:
                try:
                    with open('/etc/yum.repos.d/HPECoERHELUpgrade.repo', 'a') as repoFile:
                        repoFile.write('baseurl=file:///mnt\n')
                        repoFile.write('enabled=1\n')
                        repoFile.write('\n')
                        repoFile.write('[Security_Patches]\n')
                        repoFile.write('name=Security Patches\n')
                        repoFile.write('baseurl=file:///mnt/addons/SecurityPatches\n')
                        repoFile.write('enabled=1\n')
                        repoFile.write('gpgcheck=0\n')
                except OSError as err:
                    upgradeLogger.error('Errors were encountered while updating the upgrade repo file with security patch information.\n' + str(err))
                    print RED + 'Errors were encountered while updating the upgrade repo file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

                if upgradeFeedbackThread == None:
                    upgradeFeedbackThread = UpgradeFeedbackThread()
                upgradeLogger.info('Applying security patches to the server.')
                upgradeFeedbackThread.setMessage('Applying security patches to the server.')
                upgradeFeedbackThread.start()
                for output in processRPMS('install'):
                    upgradeLogger.info(output)

                f.write('appliedSecurityPatches\n')
        finally:
            if not upgradeFeedbackThread == None:
                upgradeFeedbackThread.stopThread()
            command = 'umount /mnt'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                upgradeLogger.error('Errors were encountered while unmounting the OS DVD.\n' + err + '\n' + out)

    except IOError as err:
        upgradeLogger.error('Could not access ' + progressStatusFile + '.\n' + str(err))
        print RED + "Could not access '" + progressStatusFile + "'; fix the problem and try again." + RESETCOLORS
    finally:
        f.close()

    upgradeLogger.info('Removing the upgrade repository and restoring the original repositories.')
    try:
        os.remove('/etc/yum.repos.d/HPECoERHELUpgrade.repo')
    except OSError as err:
        upgradeLogger.error('Errors were encountered while removing the upgrade repository /etc/yum.repos.d/HPECoERHELUpgrade.repo.\n' + str(err))
        print RED + 'Errors were encountered while removing the upgrade repository; the repository will need to be removed manually.' + RESETCOLORS

    try:
        repoFiles = os.listdir('/tmp/CoEYumRepoBackupDir')
        for file in repoFiles:
            shutil.move('/tmp/CoEYumRepoBackupDir/' + file, '/etc/yum.repos.d/' + file)

        os.rmdir('/tmp/CoEYumRepoBackupDir/')
    except (OSError, IOError, Error) as err:
        upgradeLogger.error('Errors were encountered while moving the repository files in /tmp/CoEYumRepoBackupDir back to /etc/yum.repos.d and then deleting the directory.\n' + str(err))
        print RED + 'Errors were encountered while moving the repository files back in place; the files will need to be moved manually and the backup directory removed.' + RESETCOLORS

    upgradeLogger.info('Updating /etc/motd with the message:\n\tThis is RHEL for SAP Applications on a ' + motdInfo + '.')
    try:
        with open('/etc/motd', 'w') as motdFile:
            motdFile.write('This is RHEL for SAP Applications on a ' + motdInfo + '.')
    except OSError as err:
        upgradeLogger.error('Errors were encountered while updating the motd file.\n' + str(err))
        upgradeLogger.info('The following was being written to /etc/motd:\n' + 'This is RHEL for SAP Applications on a ' + motdInfo + '.')
        print RED + 'Errors were encountered while updating the motd file; the file will have to be updated manually, see the log file for the message.' + RESETCOLORS

    date = datetime.datetime.now()
    upgradeLogger.info('Updating /etc/hpe-release with the release information:\n\t' + releaseInfo + ' Upgrade Release ' + programVersion + '.\n\tUpgraded on ' + date.strftime('%b %d, %Y @ %H:%M:%S') + '.')
    try:
        with open('/etc/hpe-release', 'w') as releaseFile:
            releaseFile.write(releaseInfo + ' Upgrade Release ' + programVersion + '.\n')
            releaseFile.write('Upgraded on ' + date.strftime('%b %d, %Y @ %H:%M:%S') + '.')
    except OSError as err:
        upgradeLogger.error('Errors were encountered while updating the hpe-release file.\n' + str(err))
        upgradeLogger.info('The following was being written to /etc/hpe-release:\n' + releaseInfo + ' Upgrade Release ' + programVersion + '.\nUpgraded on ' + date.strftime('%b %d, %Y @ %H:%M:%S') + '.')
        print RED + 'Errors were encountered while updating the hpe-releae file; the file will have to be updated manually, see the log file for its contents.' + RESETCOLORS

    upgradeLogger.info('Disabling kdump and openwsmand if they are enabled.')
    serviceList = ['kdump.service', 'openwsmand.service']
    for service in serviceList:
        command = 'systemctl is-enabled ' + service
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0 and out.strip() != 'disabled':
            upgradeLogger.error('Errors were encountered while checking to see if ' + service + ' is enabled.\n' + err + '\n' + out)
            upgradeLogger.info('The command used to check if ' + service + ' is enabled was: ' + command)
            print RED + 'Errors were encountered while checking to see if ' + service + ' is enabled before disabling the service; the service will have to be checked and disabled manually.' + RESETCOLORS
        elif out.strip() == 'enabled':
            command = 'systemctl disable ' + service
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                upgradeLogger.error('Errors were encountered while disabling ' + service + '.\n' + err + '\n' + out)
                upgradeLogger.info('The command used to disable ' + service + ' was: ' + command)
                print RED + 'Errors were encountered while disabling ' + service + '; the service will have to be disabled manually.' + RESETCOLORS

    upgradeLogger.info('Done upgrading the server to ' + osUpgradeVersion + '.')
    print GREEN + 'Done upgrading the server to ' + osUpgradeVersion + '; proceed with the next steps in the upgrade process.' + RESETCOLORS
    return


try:
    main()
except Exception as err:
    try:
        upgradeLogger = logging.getLogger('coeOSUpgradeLogger')
        upgradeLogger.error('An unexpected error was encountered:\n' + traceback.format_exc())
        print RED + "An unexpected error was encountered; collect the application's log file and report the error back to the SAP HANA CoE DevOps team." + RESETCOLORS
        print RED + 'Error: ' + str(err) + RESETCOLORS
        exit(1)
    except NameError:
        print RED + "An unexpected error was encountered; collect the application's log file as well as the error message and report the error back to the SAP HANA CoE DevOps team." + RESETCOLORS
        print RED + 'Error: ' + str(err) + RESETCOLORS
        exit(1)