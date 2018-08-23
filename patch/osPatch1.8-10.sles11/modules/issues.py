# Embedded file name: ./issues.py
import subprocess
import logging
import re
import os
import shutil
import datetime
from modules.spUtils import RED, RESETCOLORS

def updateSUSE_SLES_SAPRelease(patchResourceDict, loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Updating SUSE_SLES_SAP-release.')
    command = 'rpm -e --nodeps SUSE_SLES_SAP-release'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to remove the SUSE_SLES_SAP-release package was: ' + out.strip())
    if result.returncode != 0:
        logger.error('Unable to remove the SUSE_SLES_SAP-release package.\n' + err)
        print RED + 'Unable to remove the SUSE_SLES_SAP-release package; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)
    try:
        patchBaseDir = re.sub('\\s+', '', patchResourceDict['patchBaseDir']).rstrip('/')
        osSubDir = re.sub('\\s+', '', patchResourceDict['osSubDir'])
        suseSLESSAPReleaseRPM = re.sub('\\s+', '', patchResourceDict['suseSLESSAPReleaseRPM'])
        osDistLevel = re.sub('\\s+', '', patchResourceDict['osDistLevel'])
        suseSLESSAPReleaseRPM = patchBaseDir + '/' + osDistLevel + '/' + osSubDir + '/' + suseSLESSAPReleaseRPM
    except KeyError as err:
        logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
        print RED + 'A resource key was not present in the resource file; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)

    command = 'zypper -n --non-interactive-include-reboot-patches in ' + suseSLESSAPReleaseRPM
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to install the SUSE_SLES_SAP-release RPM was: ' + out.strip())
    if result.returncode != 0:
        logger.error('Unable to install the SUSE_SLES_SAP-release RPM.\n' + err)
        print RED + 'Unable to install the SUSE_SLES_SAP-release RPM; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)
    logger.info('Done updating SUSE_SLES_SAP-release.')


def sles12MultipathFix(loggerName):
    configFile = '/etc/dracut.conf.d/10-mp.conf'
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    configFileBackup = configFile + '.' + dateTimestamp
    logger = logging.getLogger(loggerName)
    logger.info("Ensuring '" + configFile + "' is present and configured.")
    if os.path.isfile(configFile):
        shutil.copy2(configFile, configFileBackup)
    command = 'echo \'force_drivers+=" dm-multipath "\' > ' + configFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Failed to update '" + configFile + "'.:" + err)
        print RED + "Failed to update '" + configFile + "'; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)
    logger.info("Done ensuring '" + configFile + "' is present and configured.")


def checkStorage(loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Checking to see if local storage is present.')
    command = 'lsscsi'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to check if local storage is present was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Failed to get the compute node's SCSI information.\n" + err)
        print RED + "Unable to get the compute node's SCSI information; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)
    else:
        scsiDict = dict.fromkeys([ col.split()[1] for col in out.splitlines() ])
        logger.info('The SCSI devices were determined to be: ' + str(scsiDict))
        if 'storage' in scsiDict:
            localStoragePresent = True
            logger.info('Local storage was determined to be present.')
        else:
            localStoragePresent = False
    logger.info('Done checking to see if local storage is present.')
    return localStoragePresent


def checkForMellanox(loggerName):
    mellanoxPresent = False
    logger = logging.getLogger(loggerName)
    logger.info('Checking to see if Mellanox NIC cards are present.')
    command = 'lspci -mvv'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to check if Mellanox cards are present was: ' + out.strip())
    if result.returncode != 0:
        logger.error("Failed to get the compute node's PCI information.\n" + err)
        print RED + "Unable to get the compute node's PCI information; check the log file for errors; exiting program execution." + RESETCOLORS
        exit(1)
    out = re.sub('\n{2,}', '####', out)
    deviceList = out.split('####')
    for device in deviceList:
        if ('Ethernet controller' in device or 'Network controller' in device) and 'Mellanox' in device:
            mellanoxPresent = True
            logger.info('Mellanox NIC cards were determined to be present.')
            break

    logger.info('Done checking to see if Mellanox NIC cards are present.')
    return mellanoxPresent


def removeMellanoxDriver(loggerName):
    logger = logging.getLogger(loggerName)
    logger.info('Checking for installed Mellanox driver components before trying to remove them.')
    command = 'rpm -q mlnx-ofa_kernel-kmp-default'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to check if mlnx-ofa_kernel-kmp-default is installed was: ' + out.strip())
    if result.returncode == 0:
        out = out.splitlines()
        command = 'rpm -e ' + ' '.join(out)
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to remove mlnx-ofa_kernel-kmp-default was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Problems were encountered while trying to remove mlnx-ofa_kernel-kmp-default.\n' + err)
            print RED + 'Unable to remove mlnx-ofa_kernel-kmp-default; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
    command = 'rpm -q mlnx-ofa_kernel'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to check if mlnx-ofa_kernel is installed was: ' + out.strip())
    if result.returncode == 0:
        out = out.splitlines()
        command = 'rpm -e ' + ' '.join(out)
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to remove mlnx-ofa_kernel was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Problems were encountered while trying to remove mlnx-ofa_kernel.\n' + err)
            print RED + 'Unable to remove mlnx-ofa_kernel; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)


def mlx4Configure(loggerName):
    logger = logging.getLogger(loggerName)
    persistNetRulesFile = '/etc/udev/rules.d/70-persistent-net.rules'
    if os.path.exists(persistNetRulesFile):
        try:
            os.remove(persistNetRulesFile)
        except OSError as err:
            logger.error('Problems were encountered while trying to remove 70-persistent-net.rules.\n' + err)
            exit(1)

    command = 'ln -s /dev/null /etc/udev/rules.d/70-persistent-net.rules'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info('The output of the command (' + command + ') used to disable 70-persistent-net.rules was: ' + out.strip())
    if result.returncode != 0:
        logger.error('Problems were encountered while trying to disable 70-persistent-net.rules.\n' + err)
        print RED + 'Unable to disable 70-persistent-net.rules; check the log file for errors; exiting program execution.' + RESETCOLORS
        exit(1)
    mlxConfigurationFile = '/opt/hpe/mellanox/mlxConfig.sh'
    if not os.path.exists(mlxConfigurationFile):
        hpeMlxConfigDir = '/opt/hpe/mellanox'
        if not os.path.isdir(hpeMlxConfigDir):
            os.makedirs(hpeMlxConfigDir)
        try:
            f = open(mlxConfigurationFile, 'w')
            f.write('#!/bin/sh\n\n')
            f.write('#This script configures the Mellanox cards to operate in Ethernet mode and not Infiniband mode.\n\n')
            f.write("module=$(lsmod|egrep -o '^mlx4_en')\n\n")
            f.write('if [[ -z $module ]]; then\n')
            f.write('   modprobe mlx4_en\n')
            f.write('fi\n\n')
            f.write("busList=$(lspci |grep Mellanox|awk '{print $1}')\n\n")
            f.write('for i in `echo $busList`; do\n')
            f.write('   for j in 1 2; do\n')
            f.write('      echo eth > /sys/bus/pci/devices/0000:${i}/mlx4_port${j}\n')
            f.write('   done\n')
            f.write('done\n')
        except IOError as err:
            logger.error('Could not access ' + mlxConfigurationFile + '.\n' + err)
            print RED + 'Could not access ' + mlxConfigurationFile + '; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)

        f.close()
        command = 'chmod 755 ' + mlxConfigurationFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to change permissions for ' + mlxConfigurationFile + ' was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Unable to change permissions for ' + mlxConfigurationFile + '.\n' + err)
            print RED + 'Unable to change permissions for ' + mlxConfigurationFile + '; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
    mlxConfigServiceFile = '/etc/systemd/system/mlxConfigure.service'
    if not os.path.exists(mlxConfigServiceFile):
        try:
            f = open(mlxConfigServiceFile, 'w')
            f.write('[Unit]\n')
            f.write('Description=Set Mellanox cards to Ethernet Before=network.service\n\n')
            f.write('[Service]\n')
            f.write('Type=oneshot\n')
            f.write('ExecStart=/opt/hpe/mellanox/mlxConfig.sh\n\n')
            f.write('[Install]\n')
            f.write('WantedBy=default.target\n')
        except IOError as err:
            logger.error('Could not access ' + mlxConfigServiceFile + '.\n' + err)
            print RED + 'Could not access ' + mlxConfigServiceFile + '; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)

        f.close()
        command = 'chmod 664 ' + mlxConfigServiceFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to change permissions for ' + mlxConfigServiceFile + ' was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Unable to change permissions for ' + mlxConfigServiceFile + '.\n' + err)
            print RED + 'Unable to change permissions for ' + mlxConfigServiceFile + '; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
        command = 'systemctl daemon-reload'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to reload daemon was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Unable to reload daemon.\n' + err)
            print RED + 'Unable to reload daemon; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)
        command = 'systemctl enable mlxConfigure.service'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info('The output of the command (' + command + ') used to enable mlxConfigure service was: ' + out.strip())
        if result.returncode != 0:
            logger.error('Unable to enable mlxConfigure service.\n' + err)
            print RED + 'Unable to enable mlxConfigure service; check the log file for errors; exiting program execution.' + RESETCOLORS
            exit(1)


def getProcessorType(loggerName):
    logger = logging.getLogger(loggerName)
    logger.info("Getting the server's processor type.")
    processorDict = {'62': 'ivybridge',
     '63': 'haswell',
     '79': 'broadwell'}
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
                logger.error('The processor model identifier (' + str(err) + ') was not present in the processor dictionary.')
                print RED + 'The server is unsupported, since it does not have a supported processor; exiting program execution.' + RESETCOLORS
                exit(1)

            break

    logger.info("The server's processor type was determined to be: " + processor + '.')
    logger.info("Done getting the server's processor type.")
    return processor


def updateFstabTimeout(loggerName):
    logger = logging.getLogger(loggerName)
    timestamp = datetime.datetime.now().strftime('%d%H%M%S%b%Y')
    fstabFile = '/etc/fstab'
    logger.info('Updating the fstab SAP HANA related mount points to include an extended systemd timeout.')
    try:
        shutil.copy(fstabFile, fstabFile + '.SAVED.' + timestamp)
    except IOError as err:
        logger.error("Unable to backup the fstab file to '" + fstabFile + '.SAVED.' + timestamp + "'.\n" + str(err))
        print RED + 'Unable to backup the fstab file; check the log file for errors; exiting program execution.' + RESETCOLORS
        print 'Unable to backup the fstab file; check the log file for errors; exiting program execution.'
        exit(1)

    command = "sed -ri 's/,x-systemd.device-timeout=[0-9]+[s]*//g; s/x-systemd.device-timeout=[0-9]+[s,]*//g; s@^\\s*([A-Za-z0-9.:_/]*[[:space:]]+/(hana|usr)/(sap|log|data|shared)[a-zA-Z0-9/]*[[:space:]]+(nfs|nfs4|xfs)[[:space:]]+)(.*)@\\1x-systemd.device-timeout=300s,\\5@' " + fstabFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Unable to update the SAP HANA related mount points in /etc/fstab to include an extended systemd timeout.\n' + err + '\n' + out)
        logger.info('The command used to update the SAP HANA related mount points in /etc/fstab file was: ' + command)
        print RED + 'Unable to update the SAP HANA related mount points in /etc/fstab; check the log file for errors; exiting program execution.' + RESETCOLORS
        print 'Unable to update the SAP HANA related mount points in /etc/fstab; check the log file for errors; exiting program execution.'
        exit(1)
    logger.info('Done updating the fstab SAP HANA related mount points to include an extended systemd timeout.')