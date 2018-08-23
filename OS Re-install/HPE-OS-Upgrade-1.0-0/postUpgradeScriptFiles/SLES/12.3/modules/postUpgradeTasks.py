# Embedded file name: ./postUpgradeTasks.py
import subprocess
import re
import time
import logging
import struct
import shutil
import datetime
import os
GREEN = '\x1b[32m'
RESETCOLORS = '\x1b[0m'

def configureSnapper():
    errorsEncountered = False
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
    print GREEN + 'Configuring snapper to keep snapshots for the last 7 days.' + RESETCOLORS
    command = 'snapper list-configs'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while getting the list of snapper configurations.\n' + err + '\n' + out)
        debugLogger.info('The command used to get the list of snapper configurations was: ' + command)
        errorsEncountered = True
    if not errorsEncountered:
        configDataList = out.splitlines()
        for line in configDataList:
            line = line.strip()
            if len(line) == 0 or re.match('^-', line) or re.match('^\\s+$', line) or re.match('^Config', line, re.IGNORECASE):
                continue
            else:
                configList.append(re.sub('\\s+', '', line).split('|')[0])

        for config in configList:
            for resource in snapperResourceList:
                command = 'snapper -c ' + config + ' set-config ' + resource
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    debugLogger.error("Problems were encountered while setting the resource '" + resource + "' for the snapper configuration '" + config + "'.\n" + err + '\n' + out)
                    debugLogger.info("The command used to configure the snapper resource '" + resource + "' was: " + command)
                    errorsEncountered = True
                time.sleep(0.5)

    logger.info('Done configuring snapper to keep snapshots for the last 7 days.')
    return errorsEncountered


def enableMultiversionSupport():
    zyppConfigurationFile = '/etc/zypp/zypp.conf'
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Enabling kernel multiversion support.')
    print GREEN + 'Enabling kernel multiversion support.' + RESETCOLORS
    command = 'egrep "^#\\s*multiversion\\s*=\\s*" ' + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    debugLogger.info('The output of ' + command + ' used to get the multiversion resource was:\n' + out + '\n' + err)
    if result.returncode == 0:
        command = "sed -i '0,/^#\\s*multiversion\\s*=\\s*.*$/s//multiversion = provides:multiversion(kernel)/' " + zyppConfigurationFile
    else:
        command = "echo 'multiversion = provides:multiversion(kernel)' >> " + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    debugLogger.info('The output of the command (' + command + ') used to update the multiversion resource was: ' + out)
    if result.returncode != 0:
        debugLogger.error("Unable to update the system's zypper configuration file " + zyppConfigurationFile + '.\n' + err + '\n' + out)
    command = 'egrep "^#\\s*multiversion.kernels\\s*=\\s*" ' + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    debugLogger.info('The output of the command (' + command + ') used to get the multiversion.kernels resource was:\n' + out + '\n' + err)
    if result.returncode == 0:
        command = "sed -i '0,/^#\\s*multiversion.kernels\\s*=\\s*.*$/s//multiversion.kernels = latest,latest-1,running/' " + zyppConfigurationFile
    else:
        command = "echo 'multiversion.kernels = latest,latest-1,running' >> " + zyppConfigurationFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    debugLogger.info('The output of the command (' + command + ') used to update the multiversion.kernels resource was: ' + out)
    if result.returncode != 0:
        debugLogger.error("Unable to update the system's zypper configuration file " + zyppConfigurationFile + '.\n' + err + '\n' + out)
    logger.info('Done enabling kernel multiversion support.')
    return errorsEncountered


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


def checkSAPHANAConfiguration(serverModel, osDist, *args):
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking the SAP HANA tuning configuration.')
    print GREEN + 'Checking the SAP HANA tuning configuration.' + RESETCOLORS
    if serverModel != 'Superdome':
        kernelParameters = args[0]
        kernelParameterDict = dict(((x.split(':')[0].strip(), x.split(':')[1].strip()) for x in re.sub('\\s*,\\s*', ',', kernelParameters).split(',')))
        debugLogger.info('The kernel parameter dictionary was:\n' + str(kernelParameterDict))
        command = 'sysctl -a'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        out = out.strip()
        if result.returncode != 0:
            debugLogger.error("Failed to get the server's kernel parameters.\n" + err + '\n' + out)
            debugLogger.info("The command used to get the server's kernel parameters was: " + command)
            errorsEncountered = True
        else:
            currentKernelParameterList = out.splitlines()
            currentKernelParameterDict = dict(((x.split('=')[0].strip(), re.sub('\\s+', ' ', x.split('=')[1]).strip()) for x in currentKernelParameterList))
            for kernelParameter in kernelParameterDict:
                if kernelParameterDict[kernelParameter] != currentKernelParameterDict[kernelParameter]:
                    debugLogger.error('The ' + kernelParameter + " kernel parameter was not set to '" + kernelParameterDict[kernelParameter] + "'.")
                    errorsEncountered = True

    try:
        with open('/dev/cpu_dma_latency', 'r') as f:
            data = f.read()
        val = struct.unpack('i', data)
        latency = val[0]
        if latency != 70:
            debugLogger.error("'force_latency' is not set to 70 in /etc/tuned/saptune/tuned.conf.")
            errorsEncountered = True
    except IOError as err:
        debugLogger.error("Failed to confirm if 'force_latency' was set to 70.\n" + str(err))
        errorsEncountered = True

    if osDist == 'SLES':
        command = 'cat /sys/fs/cgroup/pids/user.slice/user-0.slice/pids.max'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        userTasksMax = out.strip()
        if result.returncode != 0:
            debugLogger.error("Failed to confirm if 'UserTasksMax' was set to infinity.\n" + err + '\n' + out)
            debugLogger.info("The command used to check if 'UserTasksMax' was set to infinity was: " + command)
            errorsEncountered = True
        elif userTasksMax != 'max':
            debugLogger.error("'UserTasksMax' is not set to infinity in /etc/systemd/logind.conf.d/sap-hana.conf.")
            debugLogger.info("The command used to check if 'UserTasksMax' was set to infinity was: " + command)
            errorsEncountered = True
        command = 'saptune solution list'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Failed to confirm if the saptune solution 'HANA' was enabled.\n" + err + '\n' + out)
            debugLogger.info("The command used to check if the saptune solution 'HANA' was enabled was: " + command)
            errorsEncountered = True
        elif re.match('.*\\*\\s+HANA', out, re.MULTILINE | re.DOTALL) == None:
            debugLogger.error("The saptune solution 'HANA' is not enabled.\n" + out)
            debugLogger.info("The command used to check if the saptune solution 'HANA' was enabled was: " + command)
            errorsEncountered = True
        if serverModel != 'Superdome':
            command = 'saptune note list'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Failed to confirm if the saptune note 'HPE' was enabled.\n" + err + '\n' + out)
                debugLogger.info("The command used to check if the saptune note 'HPE' was enabled was: " + command)
                errorsEncountered = True
            elif re.match('.*\\+\\s+HPE\\s+Recommended_OS_settings', out, re.MULTILINE | re.DOTALL) == None:
                debugLogger.error("The saptune solution 'HANA' is not enabled.\n" + out)
                debugLogger.info("The command used to check if the saptune solution 'HANA' was enabled was: " + command)
                errorsEncountered = True
        command = 'sysctl vm.pagecache_limit_mb'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Failed to confirm if Linux Page Cache limit is set to unlimited.\n' + err + '\n' + out)
            debugLogger.info('The command used to check if Linux Page Cache limit is set to unlimited was: ' + command)
            errorsEncountered = True
        elif out.split('=')[1].strip() != '0':
            debugLogger.error('Linux Page Cache limit is not set to unlimited.\n' + out)
            debugLogger.info('The command used to check if Linux Page Cache limit is set to unlimited was: ' + command)
            errorsEncountered = True
    command = 'tuned-adm active'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Failed to confirm if the tuned active profile is set to 'saptune'.\n" + err + '\n' + out)
        debugLogger.info("The command used to check if the tuned active profile is set to 'saptune' was: " + command)
        errorsEncountered = True
    else:
        if osDist == 'SLES':
            profile = 'saptune'
        elif serverModel != 'Superdome':
            profile = 'sap-hpe-hana'
        else:
            profile = 'sap-hana'
        if re.match('.*Current active profile:\\s+' + profile + '', out, re.MULTILINE | re.DOTALL) == None:
            debugLogger.error("The tuned active profile is not set to '" + profile + "'.\n" + out)
            debugLogger.info("The command used to check if the tuned active profile is set to '" + profile + "' was: " + command)
            errorsEncountered = True
        else:
            debugLogger.info("The server's tuned active profile was set to " + profile + '.')
    command = 'cat /sys/kernel/mm/transparent_hugepage/enabled'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to confirm if transparent huge pages is disabled.\n' + err + '\n' + out)
        debugLogger.info('The command used to check if transparent huge pages is disabled was: ' + command)
        errorsEncountered = True
    elif re.match('.*\\[never\\]', out, re.MULTILINE | re.DOTALL) == None:
        debugLogger.error('Transparent huge pages is not disabled.\n' + out)
        debugLogger.info('The command used to check if transparent huge pages is disabled was: ' + command)
        errorsEncountered = True
    command = 'cat /proc/sys/kernel/numa_balancing'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to confirm if auto numa balancing is disabled.\n' + err + '\n' + out)
        debugLogger.info('The command used to check if auto numa balancing is disabled was: ' + command)
        errorsEncountered = True
    elif out.strip() != '0':
        debugLogger.error('Auto numa balancing is not disabled.\n' + out)
        debugLogger.info('The command used to check if auto numa balancing is disabled was: ' + command)
        errorsEncountered = True
    command = 'cat /proc/cmdline'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to confirm if cstates are set to one.\n' + err + '\n' + out)
        debugLogger.info('The command used to check if cstates are set to one was: ' + command)
        errorsEncountered = True
    elif re.match('.*processor.max_cstate=1', out) == None or re.match('.*intel_idle.max_cstate=1', out) == None:
        debugLogger.error('cstates are not set to one.\n' + out)
        debugLogger.info('The command used to check if cstates are set to one was: ' + command)
        errorsEncountered = True
    if 'DL580' not in serverModel:
        command = 'cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Failed to confirm if CPU Frequency/Voltage scaling is set to 'performance'.\n" + err + '\n' + out)
            debugLogger.info("The command used to check if CPU Frequency/Voltage scaling is set to 'performance' was: " + command)
            errorsEncountered = True
        elif out.strip() != 'performance':
            debugLogger.error("CPU Frequency/Voltage scaling is not set to 'performance'.\n" + out)
            debugLogger.info("The command used to check if CPU Frequency/Voltage scaling is set to 'performance' was: " + command)
            errorsEncountered = True
    command = 'cat /sys/kernel/mm/ksm/run'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to confirm if kernel samepage is disabled.\n' + err + '\n' + out)
        debugLogger.info('The command used to check if kernel samepage is disabled was: ' + command)
        errorsEncountered = True
    elif out.strip() != '0':
        debugLogger.error('Kernel samepage is not disabled.\n' + out)
        debugLogger.info('The command used to check if kernel samepage is disabled was: ' + command)
        errorsEncountered = True
    if osDist == 'RHEL':
        command = 'getenforce'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Failed to confirm if SELinux is disabled.\n' + err + '\n' + out)
            debugLogger.info('The command used to check if SELinux is disabled was: ' + command)
            errorsEncountered = True
        elif out.strip() != 'Disabled':
            debugLogger.error('SELinux is not disabled.\n' + out)
            debugLogger.info('The command used to check if SELinux is disabled was: ' + command)
            errorsEncountered = True
    command = 'cpupower -c all info -b'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to confirm if Energy Performance Bias is set to maximum performance.\n' + err + '\n' + out)
        debugLogger.info('The command used to check if Energy Performance Bias is set to maximum performance was: ' + command)
        errorsEncountered = True
    else:
        unsetCPUList = re.findall('perf-bias:\\s+[^0]', out, re.MULTILINE | re.DOTALL)
        if len(unsetCPUList) != 0:
            debugLogger.error('Energy Performance Bias is not set to maximum performance.\n' + str(unsetCPUList))
            debugLogger.info('The command used to check if Energy Performance Bias is set to maximum performance was: ' + command)
            errorsEncountered = True
    logger.info('Done checking the SAP HANA tuning configuration.')
    return errorsEncountered


def updateServiceguardPackages(serviceguardRPMDir):
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Updating the Serviceguard packages that needed to be updated.')
    print GREEN + 'Updating the Serviceguard packages that needed to be updated.' + RESETCOLORS
    command = 'rpm -U --quiet --nosignature ' + serviceguardRPMDir + '/*.rpm'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Problems were encountered while updating the Serviceguard packages.\n' + err + '\n' + out)
        debugLogger.info('The command used to update the Serviceguard packages was: ' + command)
        errorsEncountered = True
    logger.info('Done updating the Serviceguard packages that needed to be updated.')
    return errorsEncountered


def cleanupGrubCfg():
    timestamp = datetime.datetime.now().strftime('%d%H%M%S%b%Y')
    cmdlineResource = 'GRUB_CMDLINE_LINUX_DEFAULT'
    updatedCmdlineList = []
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Configuring /etc/default/grub.')
    print GREEN + 'Configuring /etc/default/grub.' + RESETCOLORS
    if os.path.isfile('/etc/default/grub'):
        try:
            shutil.copy('/etc/default/grub', '/etc/default/grub.SAVED.' + timestamp)
        except IOError as err:
            debugLogger.warn("Unable to backup the grub configuration file to '" + '/etc/default/grub.SAVED.' + timestamp + "'.\n" + str(err))

        command = "awk '/^[[:space:]]*GRUB_CMDLINE_LINUX_DEFAULT/{print}' /etc/default/grub"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Problems were encountered while getting the GRUB_CMDLINE_LINUX_DEFAULT resource from /etc/default/grub.\n' + err + '\n' + out)
            debugLogger.info('The command used to get the GRUB_CMDLINE_LINUX_DEFAULT resource from /etc/default/grub was: ' + command)
            errorsEncountered = True
        out = out.strip()
        if out == '' or len(out.split('=')) != 2 or len(out.split('=')[1]) == 0:
            if not out == '':
                command = "sed -i '/^\\s*GRUB_CMDLINE_LINUX_DEFAULT.*$/d' /etc/default/grub"
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    debugLogger.error('Problems were encountered while removing the GRUB_CMDLINE_LINUX_DEFAULT resource from /etc/default/grub.\n' + err + '\n' + out)
                    debugLogger.info('The command used to remove the GRUB_CMDLINE_LINUX_DEFAULT resource from /etc/default/grub was: ' + command)
                    errorsEncountered = True
            command = 'cat /proc/cmdline'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('Problems were encountered while getting the GRUB_CMDLINE_LINUX_DEFAULT resource from /etc/default/grub.\n' + err + '\n' + out)
                debugLogger.info('The command used to get the GRUB_CMDLINE_LINUX_DEFAULT resource from /etc/default/grub was: ' + command)
                errorsEncountered = True
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
            command = "sed -i '/^\\s*GRUB_CMDLINE_LINUX_DEFAULT.*$/d' /etc/default/grub"
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('Problems were encountered while removing the GRUB_CMDLINE_LINUX_DEFAULT resource from /etc/default/grub.\n' + err + '\n' + out)
                debugLogger.info('The command used to remove the GRUB_CMDLINE_LINUX_DEFAULT resource from /etc/default/grub was: ' + command)
                errorsEncountered = True
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
            print 'Problems were encountered while adding the GRUB_CMDLINE_LINUX_DEFAULT resource to /etc/default/grub.\n' + str(err)
            errorsEncountered = True

    else:
        debugLogger.info('/etc/default/grub was not present, thus configuration changes were not made.')
    logger.info('Done configuring /etc/default/grub.')
    return errorsEncountered


def configureMellanox(programParentDir):
    mellanoxDriverRPM = programParentDir + '/mellanoxDriver/*.rpm'
    mellanoxBusList = []
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Configuring the Mellanox cards by installing the Mellanox driver and updating connectx.conf.')
    print GREEN + 'Configuring the Mellanox cards.' + RESETCOLORS
    command = 'lspci -mvv'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Failed to get the lspci output used to get the Compute Node's Mellanox NIC bus list.\n" + err + '\n' + out)
        debugLogger.info("The command to get the lspci output, which is used to get the Compute Node's Mellanox NIC bus list was: " + command)
        return True
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
                return True

    command = 'rpm -Uvh ' + mellanoxDriverRPM
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to install the Mellanox driver.\n' + err + '\n' + out)
        return True
    for bus in mellanoxBusList:
        command = 'connectx_port_config -d ' + bus + ' -c eth,eth'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Failed to update Mellanox bus '" + bus + "' from infininband to ethernet.\n" + err + '\n' + out)
            if not errorsEncountered:
                errorsEncountered = True

    logger.info('Done configuring the Mellanox cards by installing the Mellanox driver and updating connectx.conf.')
    return errorsEncountered


def disableServices(disableServiceList):
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Disabling systemd services.')
    print GREEN + 'Disabling systemd services.' + RESETCOLORS
    debugLogger.info('The list of services to be disabled was: ' + str(disableServiceList))
    for service in disableServiceList:
        command = 'systemctl disable ' + service
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Problems were encountered while disabling the service '" + service + "'.\n" + err + '\n' + out)
            debugLogger.info("The command used to disable the service '" + service + "' was: " + command)
            if not errorsEncountered:
                errorsEncountered = True
        time.sleep(1.0)

    logger.info('Done disabling systemd services.')
    return errorsEncountered