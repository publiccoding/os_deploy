# Embedded file name: ./sapHANANodeSpec.py
import subprocess
import re
import os
import shutil
import logging
import time
RED = '\x1b[31m'
GREEN = '\x1b[32m'
YELLOW = '\x1b[33m'
RESETCOLORS = '\x1b[0m'

def checkSAPHANA(upgradeWorkingDir, serverModel, supportedSAPHANARevisionList):
    hanaSharedPresent = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Checking SAP HANA related components.')
    print GREEN + 'Checking SAP HANA related components.' + RESETCOLORS
    command = 'ps -C hdbnameserver,hdbcompileserver,hdbindexserver,hdbpreprocessor,hdbxsengine,hdbwebdispatcher,hdbxscontroller,hdbxsexecagent,hdbxsuaaserver'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode == 0:
        debugLogger.error('SAP HANA is still running. The following processes were detected:\n' + out)
        print RED + 'It appears that SAP HANA is still running; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    sidList = getSIDList()
    sidRevisionList = []
    supported = True
    for sid in sidList:
        sidadm = sid.lower() + 'adm'
        command = 'su - ' + sidadm + " -c 'HDB version'"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Errors were encountered while getting the SAP HANA revision.\n' + out)
            debugLogger.info('The command used to get the SAP HANA revision was: ' + command)
            print RED + 'Errors were encountered while getting the SAP HANA revision; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        if re.match('.*version:\\s+(([0-9]+.){3}[0-9]+)', out, re.MULTILINE | re.DOTALL) == None:
            debugLogger.error('Could not determine the SAP HANA revision for SID: ' + sid + '\n' + out)
            print RED + 'Could not determine the SAP HANA revision for SID: ' + sid + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        else:
            hanaVersion = re.match('.*version:\\s+(([0-9]+.){3}[0-9]+)', out, re.MULTILINE | re.DOTALL).group(1)
            for version in supportedSAPHANARevisionList:
                if hanaVersion[:4] == version[:4]:
                    if not float(hanaVersion[5:]) >= float(version[5:]):
                        debugLogger.error('The current SAP HANA revision (' + hanaVersion + ') for SID: ' + sid + ' is not supported for the targeted upgrade OS. The installed SAP HANA revision must be ' + version + ' or higher.')
                        sidRevisionList.append(sid)
                        if supported:
                            supported = False
                    break

    if not supported:
        print RED + 'The current SAP HANA revision for SID(s) "' + ', '.join(sidRevisionList) + '" is not supported for the targeted upgrade OS; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    command = 'mount'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to check if the /hana/shared partition is mounted.\n' + err + '\n' + out)
        print RED + 'Unable to check if the /hana/shared partition is mounted; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if serverModel != 'Superdome':
        if re.search('/hana/shared', out, re.MULTILINE | re.DOTALL) == None:
            debugLogger.error("The '/hana/shared' partition is not mounted.\n" + out)
            print RED + "The '/hana/shared' partition is not mounted; please mount it and try again; exiting program execution." + RESETCOLORS
            exit(1)
    else:
        mountedSIDList = []
        if re.match('.*\\s+/hana/shared\\s+', out, re.MULTILINE | re.DOTALL) != None:
            hanaSharedPresent = True
        for sid in sidList:
            hanaSharedEscaped = '\\/hana\\/shared\\/' + sid
            hanaShared = '/hana/shared/' + sid
            if re.search(hanaShared, out, re.MULTILINE | re.DOTALL) == None:
                command = "awk '/^[[:space:]]*[^#].*[[:space:]]+" + hanaSharedEscaped + "/{print}' /etc/fstab"
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    debugLogger.error("Unable to check if the '" + hanaShared + "' partition is mounted.\n" + err + '\n' + out)
                    print RED + "Unable to check if the '" + hanaShared + "' partition is mounted; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)
                if len(out) != 0:
                    debugLogger.error("The '" + hanaShared + "' partition is not mounted.\n" + out)
                    print RED + "The '" + hanaShared + "' partition is not mounted; please mount it and try again (Note, all HANA Shared partitions need to be mounted.); exiting program execution." + RESETCOLORS
                    exit(1)
                elif not hanaSharedPresent:
                    debugLogger.error("The '" + hanaShared + "' partition is not mounted; /usr/sap/sapservices had an entry for the SID.\n" + out)
                    print RED + "The '" + hanaShared + "' partition is not mounted; please mount it and try again (Note, all HANA Shared partitions need to be mounted.); exiting program execution." + RESETCOLORS
                    exit(1)
                else:
                    debugLogger.info("The server did not have '/hana/shared/SID' mounted, but '/hana/shared' was mounted.")
            else:
                mountedSIDList.append(sid)

    getGlobalIniFiles(upgradeWorkingDir, sidList)
    if serverModel != 'Superdome':
        unMountHANAShared()
    else:
        unMountHANAShared(mountedSIDList, hanaSharedPresent)
    logger.info('Done checking SAP HANA related components.')
    return


def getSIDList():
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Getting the SID list for the currently active SIDs as identified by '/usr/sap/sapservices'.")
    sidList = []
    command = 'cat /usr/sap/sapservices'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get the SAP HANA SID information.\n' + err + '\n' + out)
        print RED + 'Unable to get the SAP HANA SID information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    sapServicesData = out.splitlines()
    debugLogger.info('The sapServicesData from sapservices is:\n' + str(sapServicesData))
    for data in sapServicesData:
        if re.match('\\s*LD_LIBRARY_PATH\\s*=\\s*/usr/sap', data):
            try:
                sid = re.match('\\s*LD_LIBRARY_PATH\\s*=\\s*/usr/sap.*([a-z0-9]{3})adm$', data).group(1).upper()
            except AttributeError as err:
                debugLogger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                print RED + 'There was a match error while getting the SID list; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

            sidList.append(sid)

    debugLogger.info("The active SID list as determined by '/usr/sap/sapservices' was: " + str(sidList) + '.')
    logger.info("Done getting the SID list for the currently active SIDs as identified by '/usr/sap/sapservices'.")
    return sidList


def getGlobalIniFiles(upgradeWorkingDir, sidList):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Getting the global.ini files for the currently active SIDs.')
    for sid in sidList:
        globalIni = '/hana/shared/' + sid + '/global/hdb/custom/config/global.ini'
        sidDir = upgradeWorkingDir + '/' + sid
        if os.path.isfile(globalIni):
            try:
                os.mkdir(sidDir)
            except OSError as err:
                debugLogger.error("Unable to create the backup global.ini SID directory '" + sidDir + "'.\n" + str(err))
                print RED + "Unable to create the backup global.ini SID directory '" + sidDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

            try:
                shutil.copy2(globalIni, sidDir)
            except IOError as err:
                debugLogger.error("Unable to copy the global.ini to '" + sidDir + "'.\n" + str(err))
                print RED + "Unable to copy the global.ini to '" + sidDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

        else:
            debugLogger.warn("A custom global.ini '" + globalIni + "' was not present for SID " + sid + '.')
            print YELLOW + 'A custom global.ini file was not present for SID ' + sid + '.' + RESETCOLORS

    logger.info('Done getting the global.ini files for the currently active SIDs.')


def unMountHANAShared(*args):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    command = 'systemctl show -p ActiveState sapinit'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get the status of sapinit.\n' + err + '\n' + out)
        print RED + 'Unable to get the status of sapinit; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    out = out.strip()
    if re.match('\\s*ActiveState\\s*=\\s*active', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None:
        command = 'systemctl stop sapinit'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('Unable to stop the sapinit process.\n' + err + '\n' + out)
            print RED + 'Unable to stop the sapinit process; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    sapProcessList = ['hdbrsutil', 'sapstartsrv']
    for sapProcess in sapProcessList:
        command = 'ps -fC ' + sapProcess
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode == 0:
            command = 'killall -v ' + sapProcess
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('Problems were encountered when trying to kill ' + sapProcess + '.\n' + err + '\n' + out)
                print RED + 'Problems were encountered when trying to kill ' + sapProcess + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
        time.sleep(1.0)

    time.sleep(10.0)
    if len(args) == 0:
        command = 'umount /hana/shared'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to unmount '/hana/shared'.\n" + err + '\n' + out)
            print RED + "Unable to unmount '/hana/shared' (Note, /hana/shared needs to be mounted initially when the program runs); fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
    else:
        sids = args[0]
        hanaSharedPresent = args[1]
        for sid in sids:
            hanaShared = '/hana/shared/' + sid
            command = 'umount ' + hanaShared
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to unmount '" + hanaShared + "'.\n" + err + '\n' + out)
                print RED + "Unable to unmount '" + hanaShared + "' (Note, all HANA Shared partitions need to be mounted initially when the program runs); fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

        if hanaSharedPresent:
            command = 'umount /hana/shared'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Unable to unmount '/hana/shared'.\n" + err + '\n' + out)
                print RED + "Unable to unmount '/hana/shared' (Note, all HANA Shared partitions need to be mounted initially when the program runs); fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)
    return


def getConrepFile(programParentDir, conrepDir):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Getting the conrep file that will be used during the post-upgrade to update the server's BIOS.")
    print GREEN + "Getting the conrep file that will be used during the post-upgrade to update the server's BIOS." + RESETCOLORS
    defaultConrepFile = programParentDir + '/conrepFile/conrep.dat'
    try:
        updateConrepFile = conrepDir + '/conrep.dat'
        os.mkdir(conrepDir)
        shutil.copy2(defaultConrepFile, updateConrepFile)
    except (OSError, IOError) as err:
        debugLogger.error("Unable to copy the conrep file '" + updateConrepFile + "' to '" + conrepDir + "'.\n" + str(err))
        print RED + 'Unable to get a copy of the conrep file; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    logger.info("Done getting the conrep file that will be used during the post-upgrade to update the server's BIOS.")


def updateBIOS(programParentDir):
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Updating the server's BIOS.")
    print GREEN + "Updating the server's BIOS." + RESETCOLORS
    command = 'conrep -l -f ' + programParentDir + '/conrepFile/conrep.dat'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("An error was encountered while updating the server's BIOS.\n" + err + '\n' + out)
        debugLogger.info("The command used to update the server's BIOS was: '" + command + "'.")
        errorsEncountered = True
    logger.info("Done updating the server's BIOS.")
    return errorsEncountered


def restoreFstab(fstabFile):
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Restoring the fstab file.')
    print GREEN + 'Restoring the fstab file.' + RESETCOLORS
    try:
        shutil.copy2(fstabFile, '/etc/')
    except IOError as err:
        debugLogger.error('Unable to copy ' + fstabFile + ' to /etc.\n' + str(err))
        errorsEncountered = True

    logger.info('Done restoring the fstab file.')
    return errorsEncountered


def configureNofile(limitsFile, nofileValue):
    solutionReverted = False
    softNofilePresent = False
    hardNofilePresent = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Configuring/Checking @sapsys nofile limit in /etc/security/limits.conf.')
    print GREEN + 'Configuring/Checking @sapsys nofile limit in /etc/security/limits.conf.' + RESETCOLORS
    try:
        shutil.copy2(limitsFile, '/etc/security')
    except IOError as err:
        debugLogger.error('Unable to copy ' + limitsFile + ' to /etc/security.\n' + str(err))
        return True

    command = "awk '/^[[:space:]]*@sapsys[[:space:]]+[soft|hard]+[[:space:]]+nofile[[:space:]]+[0-9]+/{print}' /etc/security/limits.conf"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('An error was encountered while getting the nofile data from /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
        debugLogger.info("The command used to get the nofile data from /etc/security/limits.conf for @sapsys was: '" + command + "'.")
        return True
    sapsysGroupList = out.splitlines()
    debugLogger.info('The settings in /etc/security/limits.conf for @sapsys were: ' + str(sapsysGroupList))
    if len(sapsysGroupList) == 0:
        solutionReverted = True
        command = 'saptune solution revert HANA'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('An error was encountered while reverting the HANA solution in preparation to update /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
            debugLogger.info("The command used to revert the HANA solution in preparation to update /etc/security/limits.conf for @sapsys was: '" + command + "'.")
            return True
    for group in sapsysGroupList:
        try:
            currentNofileValue = re.match('.*\\s+([0-9]+)$', group).group(1)
            resourceHead = re.match('(.*)\\s+([0-9]+)$', group).group(1).strip()
        except AttributeError as err:
            debugLogger.error('An error was encountered while parsing ' + group + ', which was retrieved from /etc/security/limits.conf.\n' + str(err))
            return True

        if int(currentNofileValue) < int(nofileValue):
            if not solutionReverted:
                solutionReverted = True
                command = 'saptune solution revert HANA'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    debugLogger.error('An error was encountered while reverting the HANA solution in preparation to update /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
                    debugLogger.info("The command used to revert the HANA solution in preparation to update /etc/security/limits.conf for @sapsys was: '" + command + "'.")
                    return True
            if 'soft' in group:
                softNofilePresent = True
                debugLogger.info("The current soft value of nofile for @sapsys '" + currentNofileValue + "' is being changed to '" + nofileValue + "'.")
                command = "sed -i 's/^\\(" + resourceHead + '\\)\\s\\+[0-9]\\+$/\\1 ' + nofileValue + "/' /etc/security/limits.conf"
            else:
                hardNofilePresent = True
                debugLogger.info("The current hard value of nofile for @sapsys '" + currentNofileValue + "' is being changed to '" + nofileValue + "'.")
                command = "sed -i 's/^\\(" + resourceHead + '\\)\\s\\+[0-9]\\+$/\\1 ' + nofileValue + "/' /etc/security/limits.conf"
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('An error was encountered while setting the nofile value in /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
                debugLogger.info("The command used to set the nofile value in /etc/security/limits.conf for @sapsys was: '" + command + "'.")
                return True

    if not softNofilePresent:
        command = "echo '@sapsys soft nofile " + nofileValue + "' >> /etc/security/limits.conf"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('An error was encountered while adding the soft nofile entry in /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
            debugLogger.info("The command used to add the soft nofile entry in /etc/security/limits.conf for @sapsys was: '" + command + "'.")
            return True
    if not hardNofilePresent:
        command = "echo '@sapsys hard nofile " + nofileValue + "' >> /etc/security/limits.conf"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('An error was encountered while adding the hard nofile entry in /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
            debugLogger.info("The command used to add the hard nofile entry in /etc/security/limits.conf for @sapsys was: '" + command + "'.")
            return True
    if solutionReverted:
        command = 'saptune solution apply HANA'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('An error was encountered while applying the HANA solution.\n' + err + '\n' + out)
            debugLogger.info("The command used to apply the HANA solution was: '" + command + "'.")
            return True
    logger.info('Done configuring/checking @sapsys nofile limit in /etc/security/limits.conf.')
    return False


def backupLimitsFile(upgradeWorkingDir):
    limitsDir = upgradeWorkingDir + '/limitsFile'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Backing up /etc/security/limits.conf.')
    print GREEN + 'Backing up /etc/security/limits.conf.' + RESETCOLORS
    try:
        os.mkdir(limitsDir)
        shutil.copy2('/etc/security/limits.conf', limitsDir)
    except OSError as err:
        debugLogger.error("Unable to create the limits.conf backup directory '" + limitsDir + "'.\n" + str(err))
        print RED + "Unable to create the limits.conf backup directory '" + limitsDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    except IOError as err:
        debugLogger.error("Unable to copy /etc/security/limits.conf to '" + limitsDir + "'.\n" + str(err))
        print RED + "Unable to copy /etc/security/limits.conf to '" + limitsDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    logger.info('Done backing up /etc/security/limits.conf.')


def updateSysctl(kernelParameters):
    errorsEncountered = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Removing kernel parameters from /etc/sysctl.conf.')
    print GREEN + 'Removing kernel parameters from /etc/sysctl.conf.' + RESETCOLORS
    kernelParameterDict = dict(((x.split(':')[0].strip(), x.split(':')[1].strip()) for x in re.sub('\\s*,\\s*', ',', kernelParameters).split(',')))
    command = "sed -ri '/^[[:space:]]*(" + '|'.join(kernelParameterDict.keys()) + ").*$/d' /etc/sysctl.conf"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Errors were encountered while removing kernel parameters from /etc/sysctl.conf.\n' + err + '\n' + out)
        debugLogger.info('The command used to remove kernel parameters from /etc/sysctl.conf was: ' + command)
        errorsEncountered = True
    logger.info('Done removing kernel parameters from /etc/sysctl.conf.')
    return errorsEncountered