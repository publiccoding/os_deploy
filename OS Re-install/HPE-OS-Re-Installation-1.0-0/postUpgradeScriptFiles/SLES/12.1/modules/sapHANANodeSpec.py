# Embedded file name: ./sapHANANodeSpec.py
import subprocess
import re
import os
import shutil
import logging
import time
import struct
RED = '\x1b[31m'
GREEN = '\x1b[32m'
YELLOW = '\x1b[33m'
RESETCOLORS = '\x1b[0m'

def getSapInitBackupList():
    sapInitList = []
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Getting the list of sapinit related files that will be added to the restoration backup.')
    command = 'find -L /etc -samefile /etc/init.d/sapinit'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        if not ('already visited the directory' in err or 'No such' in err):
            debugLogger.error("There was a problem getting the files linked to '/etc/init.d/sapinit'.\n" + err + '\n' + out)
            debugLogger.info("The command used to get the files linked to '/etc/init.d/sapinit' was: " + command)
            print RED + "There was a problem getting the files linked to '/etc/init.d/sapinit'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        else:
            debugLogger.warn('find complained while getting links to /etc/init.d/sapinit: \n' + err + '\n' + out)
    sapInitList += out.splitlines()
    debugLogger.info('The list of sapinit related files that will be added to the restoration backup was determined to be: ' + str(sapInitList) + '.')
    logger.info('Done getting the list of sapinit related files that will be added to the restoration backup.')
    return sapInitList


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


def getSAPUserLoginData(upgradeWorkingDir, sidList, **kwargs):
    userLoginDataDir = upgradeWorkingDir + '/userLoginData'
    hanaHomeDirList = []
    sidadmLDAPUsersDict = {}
    tenantUserDict = {}
    credentialWarning = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Getting SAP HANA user account login data.')
    print GREEN + 'Getting SAP HANA user account login data.' + RESETCOLORS
    if 'tenantUserDict' in kwargs:
        tenantUserDict = kwargs['tenantUserDict']
    try:
        os.mkdir(userLoginDataDir)
    except OSError as err:
        debugLogger.error("Unable to create the pre-upgrade SAP HANA user login data directory '" + userLoginDataDir + "'.\n" + str(err))
        print RED + 'Unable to create the SAP HANA user login data directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    passwordFile = userLoginDataDir + '/passwd'
    shadowFile = userLoginDataDir + '/shadow'
    groupFile = userLoginDataDir + '/group'
    sidOwnershipFile = userLoginDataDir + '/sidOwnership'
    command = 'cat /etc/passwd'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("There was a problem getting the password information from '/etc/passwd'.\n" + err + '\n' + out)
        print RED + "There was a problem getting the password information from '/etc/passwd'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    passwordList = filter(None, (x.strip() for x in out.splitlines()))
    passwordDict = dict(((x.split(':')[0], [x, x.split(':')[3]]) for x in passwordList))
    if 'sapadm' in passwordDict:
        sidList.append('SAP')
        debugLogger.info('The SID list was determined to be: ' + str(sidList) + '.')
    command = 'cat /etc/shadow'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("There was a problem getting the shadow information from '/etc/shadow'.\n" + err + '\n' + out)
        print RED + "There was a problem getting the shadow information from '/etc/shadow'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    shadowList = filter(None, (x.strip() for x in out.splitlines()))
    shadowDict = dict(((x.split(':')[0], x) for x in shadowList))
    command = 'cat /etc/group'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("There was a problem getting the group information from '/etc/group'.\n" + err + '\n' + out)
        print RED + "There was a problem getting the group information from '/etc/group'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    groupList = filter(None, (x.strip() for x in out.splitlines()))
    groupDict = dict(((x.split(':')[2], x) for x in groupList))
    try:
        passwd = open(passwordFile, 'w')
        shadow = open(shadowFile, 'w')
        group = open(groupFile, 'w')
        sidOwnership = open(sidOwnershipFile, 'w')
        groupAddedDict = {}
        for sid in sidList:
            sidadm = sid.lower() + 'adm'
            homeDir = '/home/' + sidadm
            if os.path.isdir(homeDir):
                hanaHomeDirList.append(homeDir)
            if sid != 'SAP':
                if sidadm in passwordDict:
                    sidOwnership.write(sid + '|' + passwordDict[sidadm][0].split(':')[2] + '|' + passwordDict[sidadm][0].split(':')[3] + '\n')
                    passwd.write(passwordDict[sidadm][0] + '\n')
                else:
                    command = 'id -ur ' + sidadm
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        debugLogger.error('There was a problem getting the user id for ' + sidadm + '.\n' + err + '\n' + out)
                        print RED + 'There was a problem getting the user id for ' + sidadm + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)
                    userID = out.strip()
                    command = 'id -gr ' + sidadm
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        debugLogger.error('There was a problem getting the group id for ' + sidadm + '.\n' + err + '\n' + out)
                        print RED + 'There was a problem getting the group id for ' + sidadm + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)
                    groupID = out.strip()
                    sidOwnership.write(sid + '|' + userID + '|' + groupID + '\n')
                    debugLogger.warn('The password account information for ' + sidadm + ' was missing from /etc/password.')
                    if not credentialWarning:
                        credentialWarning = True
            else:
                passwd.write(passwordDict[sidadm][0] + '\n')
            if sidadm not in shadowDict:
                debugLogger.warn('The shadow account information for ' + sidadm + ' was missing from /etc/shadow.')
                if not credentialWarning:
                    credentialWarning = True
            else:
                shadow.write(shadowDict[sidadm] + '\n')
            if sidadm in passwordDict:
                if passwordDict[sidadm][1] not in groupAddedDict:
                    try:
                        group.write(groupDict[passwordDict[sidadm][1]] + '\n')
                    except AttributeError as err:
                        debugLogger.warn('The primary group ID (' + passwordDict[sidadm][1] + ') information for ' + sidadm + ' was missing from /etc/group.\n' + str(err))
                        if not credentialWarning:
                            credentialWarning = True

                    groupAddedDict[passwordDict[sidadm][1]] = None
                if not sid == 'SAP':
                    sidshm = sid.lower() + 'shm'
                    command = 'getent group ' + sidshm
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if result.returncode != 0:
                        debugLogger.warn('There was a problem getting the secondary group (' + sidshm + ') for ' + sidadm + '.\n' + err + '\n' + out)
                        if not credentialWarning:
                            credentialWarning = True
                    else:
                        groupID = out.strip().split(':')[2]
                        if groupID not in groupAddedDict:
                            group.write(groupDict[groupID] + '\n')
                        groupAddedDict[groupID] = None

        if len(tenantUserDict) != 0:
            for tenantUser in tenantUserDict:
                homeDir = '/home/' + tenantUser
                if os.path.isdir(homeDir):
                    hanaHomeDirList.append(homeDir)
                if tenantUser in passwordDict:
                    passwd.write(passwordDict[tenantUser][0] + '\n')
                else:
                    debugLogger.warn('The password account information for ' + tenantUser + ' was missing from /etc/password.')
                    if not credentialWarning:
                        credentialWarning = True
                if tenantUser in shadowDict:
                    shadow.write(shadowDict[tenantUser] + '\n')
                else:
                    debugLogger.warn('The shadow account information for ' + tenantUser + ' was missing from /etc/shadow.')
                    if not credentialWarning:
                        credentialWarning = True
                groupList = tenantUserDict[tenantUser]
                for groupID in groupList:
                    if groupID not in groupAddedDict:
                        try:
                            group.write(groupDict[groupID] + '\n')
                        except AttributeError as err:
                            debugLogger.warn('The group account information for ' + tenantUser + ' was missing from /etc/group.\n' + str(err))
                            if not credentialWarning:
                                credentialWarning = True

                        groupAddedDict[groupID] = None

    except IOError as err:
        debugLogger.error('Could not write user account login data.\n' + str(err))
        print RED + 'Could not write user account login data; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    finally:
        passwd.close()
        shadow.close()
        group.close()

    if credentialWarning:
        print YELLOW + "Warning: There were credential warnings while collecting credential information for the SAP HANA users; check the application's debug log file for further details." + RESETCOLORS
    logger.info('Done getting SAP HANA user account login data.')
    return hanaHomeDirList


def getHANAFstabData(upgradeWorkingDir, fstabHANAEntries):
    fstabDataDir = upgradeWorkingDir + '/fstabData'
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Getting SAP HANA related partition data from '/etc/fstab'.")
    print GREEN + "Getting SAP HANA related partition data from '/etc/fstab'." + RESETCOLORS
    try:
        os.mkdir(fstabDataDir)
    except OSError as err:
        debugLogger.error("Unable to create the fstab data directory '" + fstabDataDir + "'.\n" + str(err))
        print RED + 'Unable to create the fstab data directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    fstabFile = fstabDataDir + '/fstab'
    command = 'cat /etc/fstab'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('There was a problem getting the SAP HANA partition data from /etc/fstab.\n' + err + '\n' + out)
        print RED + 'There was a problem getting the SAP HANA partition data from /etc/fstab; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    fstabDataList = out.splitlines()
    try:
        f = open(fstabFile, 'w')
        for line in fstabDataList:
            if any((fstabHANAEntry in line for fstabHANAEntry in fstabHANAEntries)):
                if re.match('\\s*#', line) == None:
                    f.write(line + '\n')

    except IOError as err:
        debugLogger.error("Could not write HANA fstab data to '" + fstabFile + "'.\n" + str(err))
        print RED + 'Could not write out the HANA fstab data; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    f.close()
    logger.info("Done getting SAP HANA related partition data from '/etc/fstab'.")
    return


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
        debugLogger.error('SAP HANA is still running.\n' + out)
        debugLogger.info('The command used to check if SAP HANA is still running was: ' + command)
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

    tenantUserDict = getGlobalIniFiles(upgradeWorkingDir, sidList)
    if serverModel != 'Superdome':
        unMountHANAShared()
    else:
        unMountHANAShared(mountedSIDList, hanaSharedPresent)
    logger.info('Done checking SAP HANA related components.')
    return (sidList, tenantUserDict)


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
        debugLogger.info('The command used to get the SAP HANA SID information was: ' + command)
        print RED + 'Unable to get the SAP HANA SID information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    sapServicesData = out.splitlines()
    debugLogger.info('The sapservices data was:\n' + str(sapServicesData))
    for data in sapServicesData:
        if re.match('\\s*LD_LIBRARY_PATH\\s*=\\s*/usr/sap', data):
            try:
                sid = re.match('\\s*LD_LIBRARY_PATH\\s*=\\s*/usr/sap.*([a-z0-9]{3})adm$', data).group(1).upper()
            except AttributeError as err:
                debugLogger.error("There was a match error when trying to get the sidadm username '" + data + "'.\n" + str(err))
                print RED + 'There was a match error when trying to get the sidadm username; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

            sidList.append(sid)

    debugLogger.info("The active SID list as determined by '/usr/sap/sapservices' was: " + str(sidList) + '.')
    logger.info("Done getting the SID list for the currently active SIDs as identified by '/usr/sap/sapservices'.")
    return sidList


def checkSIDDirOwnership(sapHanaIDDict):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    dirDataDict = {}
    command = 'ls -dln /hana/shared/*'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Unable to get the /hans/shared directory listing.\n' + err + '\n' + out)
        debugLogger.info('The command used to get the /hans/shared directory listing was: ' + command)
        print RED + 'Unable to get the /hans/shared directory listing; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    dirList = out.splitlines()
    for dirData in dirList:
        dirData = dirData.strip()
        if re.match('[drwx-]+\\s+\\d+\\s+(\\d+)\\s+(\\d+).*(/hana/shared/([A-Z0-9]{3})$)', dirData) != None:
            dirDataList = re.match('[drwx-]+\\s+\\d+\\s+(\\d+)\\s+(\\d+).*(/hana/shared/([A-Z0-9]{3})$)', dirData).groups()
            dirDataDict[dirDataList[3]] = dirDataList[0:3]

    sidDict = dict.fromkeys((sidadm[:3].upper() for sidadm in sapHanaIDDict.keys()))
    additionalSIDUserSet = set(sidDict.keys()) - set(dirDataDict.keys())
    if len(additionalSIDUserSet) != 0:
        invalidUsers = ', '.join((sid.lower() + 'adm' for sid in additionalSIDUserSet))
        debugLogger.error('The sidadm users (' + invalidUsers + '), which were in the resource file do not have matching SID directories.')
        print RED + 'The sidadm users (' + invalidUsers + '), which were in the resource file do not have matching SID directories; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    for sid in dirDataDict:
        sidadm = sid.lower() + 'adm'
        if sidadm not in sapHanaIDDict:
            continue
        if not sapHanaIDDict[sidadm].split(':')[0] != dirDataDict[sid][0]:
            debugLogger.error('The sidadm (' + sidadm + ") user's uid does not match the uid set on " + dirDataDict[sid][2] + '.')
            print RED + 'The sidadm (' + sidadm + ") user's uid does not match the uid set on " + dirDataDict[sid][2] + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        if not sapHanaIDDict[sidadm].split(':')[1] != dirDataDict[sid][1]:
            debugLogger.error('The sidadm (' + sidadm + ") user's gid does not match the gid set on " + dirDataDict[sid][2] + '.')
            print RED + 'The sidadm (' + sidadm + ") user's gid does not match the gid set on " + dirDataDict[sid][2] + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)

    return


def getGlobalIniFiles(upgradeWorkingDir, sidList):
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Getting the global.ini files for the currently active SIDs and tenant user information if the SID is a MDC with high isolation.')
    tenantUserDict = {}
    for sid in sidList:
        globalIni = '/hana/shared/' + sid + '/global/hdb/custom/config/global.ini'
        sidDir = upgradeWorkingDir + '/' + sid
        if os.path.isfile(globalIni):
            multiTenant, isolation = checkMultiTenant(globalIni, sid)
            try:
                os.mkdir(sidDir)
            except OSError as err:
                debugLogger.error("Unable to create the backup global.ini SID directory '" + sidDir + "'.\n" + str(err))
                print RED + 'Unable to create the backup global.ini SID directory; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

            try:
                shutil.copy2(globalIni, sidDir)
            except IOError as err:
                debugLogger.error("Unable to copy the global.ini to '" + sidDir + "'.\n" + str(err))
                print RED + 'Unable to get a copy of the global.ini file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

            if multiTenant:
                databaseListFile = '/hana/shared/' + sid + '/global/hdb/mdc/databases.lst'
                try:
                    shutil.copy2(databaseListFile, sidDir)
                except IOError as err:
                    debugLogger.error("Unable to copy '" + databaseListFile + "' to '" + sidDir + "'.\n" + str(err))
                    print RED + 'Unable to get a copy of the databases.lst file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                    exit(1)

                if isolation == 'high':
                    try:
                        with open(databaseListFile) as f:
                            for line in f:
                                line = line.strip()
                                if len(line) == 0 or re.match('^\\s*#', line) or re.match('^\\s+$', line):
                                    continue
                                else:
                                    tenantUser = line.split(':')[2].strip()
                                    if len(tenantUser) == 0:
                                        debugLogger.error('The tenant user is missing from ' + databaseListFile + '.')
                                        print RED + 'The tenant user is missing from databases.lst file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                                        exit(1)
                                    command = 'id -G ' + tenantUser
                                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                    out, err = result.communicate()
                                    if result.returncode != 0:
                                        debugLogger.error("Unable to get the tenant user's (" + tenantUser + ') group information.\n' + err + '\n' + out)
                                        print RED + "Unable to get the tenant user's group information; fix the problem and try again; exiting program execution." + RESETCOLORS
                                        exit(1)
                                    tenantUserDict[tenantUser] = out.strip().split()

                    except IOError as err:
                        debugLogger.error("Unable to access '" + databaseListFile + "'.\n" + str(err))
                        print RED + 'Unable to access the databases.lst file; fix the problem and try again; exiting program execution.' + RESETCOLORS
                        exit(1)

        else:
            debugLogger.warn("A custom global.ini '" + globalIni + "' was not present for SID " + sid + '.')
            print YELLOW + 'A custom global.ini file was not present for SID ' + sid + '.' + RESETCOLORS

    logger.info('Done getting the global.ini files for the currently active SIDs and tenant user information if the SID is a MDC with high isolation.')
    return tenantUserDict


def checkMultiTenant(globalIni, sid):
    multiTenant = False
    isolation = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Checking to see if '" + sid + "' is a multitenant database container.")
    command = 'cat ' + globalIni
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to access '" + globalIni + "' to check if '" + sid + "' is a multitenant database container.\n" + err + '\n' + out)
        debugLogger.info("The command used to check if '" + sid + "' is a multitenant database container was: " + command)
        print RED + "Unable to access '" + globalIni + "' to check if '" + sid + "' is a multitenant database container; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    out = out.strip()
    if re.match('.*mode\\s*=\\s*multidb', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None:
        multiTenant = True
    if multiTenant:
        if re.match('.*database_isolation\\s*=\\s*high', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None:
            isolation = 'high'
        else:
            isolation = 'low'
    logger.info("Done checking to see if '" + sid + "' is a multitenant database container.")
    return (multiTenant, isolation)


def unMountHANAShared(*args):
    sapinitServicePresent = True
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    command = 'service sapinit status'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        if 'no such service' in err:
            sapinitServicePresent = False
        elif re.search('No process running', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) == None:
            debugLogger.error('Unable to get the status of sapinit.\n' + err + '\n' + out)
            debugLogger.info('The command used to get the status of sapinit was:' + command)
            print RED + 'Unable to get the status of sapinit; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if sapinitServicePresent:
        if re.search('No process running', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) == None:
            command = 'service sapinit stop'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error('Unable to stop the sapinit process.\n' + err + '\n' + out)
                debugLogger.info('The command used to stop sapinit was:' + command)
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
                debugLogger.info('The command used to kill additional SAP HANA related processes was:' + command)
                print RED + 'Problems were encountered when trying to kill additional SAP HANA related processes; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
        time.sleep(1.0)

    time.sleep(10.0)
    if len(args) == 0:
        command = 'umount /hana/shared'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Unable to unmount '/hana/shared'.\n" + err + '\n' + out)
            debugLogger.info("The command used to unmount '/hana/shared' was:" + command)
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


def installAddOnFiles(programParentDir, upgradeResourceDict, osDist, cursesThread, **kwargs):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Installing/replacing the files from the add-on archive.')
    cursesThread.insertMessage(['informative', 'Installing/replacing the files from the add-on archive.'])
    cursesThread.insertMessage(['informative', ''])
    if 'processor' in kwargs:
        processor = kwargs['processor']
        if processor == 'ivybridge':
            if 'RHEL' in osDist:
                addOnFileArchive = programParentDir + '/addOnFileArchive/' + upgradeResourceDict['ivyBridgeRHELAddOnFileArchive']
            else:
                addOnFileArchive = programParentDir + '/addOnFileArchive/' + upgradeResourceDict['ivyBridgeSLESAddOnFileArchive']
        elif 'RHEL' in osDist:
            addOnFileArchive = programParentDir + '/addOnFileArchive/' + upgradeResourceDict['haswellRHELAddOnFileArchive']
        else:
            addOnFileArchive = programParentDir + '/addOnFileArchive/' + upgradeResourceDict['haswellSLESAddOnFileArchive']
    if 'serverModel' in kwargs:
        serverModel = kwargs['serverModel']
        if serverModel == 'Superdome':
            if 'RHEL' in osDist:
                addOnFileArchive = programParentDir + '/addOnFileArchive/' + upgradeResourceDict['cs900RHELAddOnFileArchive']
            else:
                addOnFileArchive = programParentDir + '/addOnFileArchive/' + upgradeResourceDict['cs900SLESAddOnFileArchive']
    command = 'tar -zxf ' + addOnFileArchive + ' -C /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('An error was encountered while installing/replacing the files from the add-on file archive.\n' + err + '\n' + out)
        debugLogger.info('The command used to install/replace files from the add-on file archive was: ' + command)
        errorMessage = 'An error was encountered while installing/replacing the files from the add-on file archive.'
        return errorMessage
    logger.info('Done installing/replacing the files from the add-on archive.')
    return errorMessage


def restoreHANAUserAccounts(programParentDir, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Restoring SAP HANA user accounts.')
    cursesThread.insertMessage(['informative', 'Restoring SAP HANA user accounts.'])
    cursesThread.insertMessage(['informative', ''])
    userLoginDataDir = programParentDir + '/userLoginData'
    accountFileList = ['group', 'passwd', 'shadow']
    debugLogger.info('The account file list was: ' + str(accountFileList))
    for file in accountFileList:
        accountFile = '/etc/' + file
        command = 'cat ' + userLoginDataDir + '/' + file + ' >> ' + accountFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Problems were encountered while adding SAP HANA user accounts to '" + accountFile + "'.\n" + err + '\n' + out)
            debugLogger.info("The command used to add SAP HANA user accounts to '" + accountFile + "' was: " + command)
            errorMessage = 'Problems were encountered while adding SAP HANA user accounts; thus the SAP HANA accounts were not successfully restored.'
            return errorMessage

    logger.info('Done restoring SAP HANA user accounts.')
    return errorMessage


def restoreHANAPartitionData(programParentDir, cursesThread):
    errorMessage = ''
    hanaPartitionRestored = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.')
    cursesThread.insertMessage(['informative', 'Restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.'])
    cursesThread.insertMessage(['informative', ''])
    fstabDataFile = programParentDir + '/fstabData/fstab'
    debugLogger.info('The fstab data list was: ' + str(fstabDataFile))
    command = 'cat ' + fstabDataFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("There was a problem getting the SAP HANA partition data from '" + fstabDataFile + "'.\n" + err + '\n' + out)
        debugLogger.info("The command used to get the SAP HANA partition data from '" + fstabDataFile + "' was: " + command)
        errorMessage = 'There was a problem getting the SAP HANA partition data; thus the SAP HANA partition data was not successfully restored.'
        return (errorMessage, hanaPartitionRestored)
    fstabDataList = out.splitlines()
    for partition in fstabDataList:
        partitionList = partition.split()
        partition = partitionList[1]
        if not os.path.isdir(partition):
            try:
                os.makedirs(partition)
            except OSError as err:
                debugLogger.error("Unable to create the mount point '" + partition + "'.\n" + str(err))
                errorMessage = 'Unable to create the SAP HANA mount points; thus the SAP HANA partition data was not successfully restored.'
                return (errorMessage, hanaPartitionRestored)

    command = 'cat ' + fstabDataFile + ' >> /etc/fstab'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Problems were encountered while adding SAP HANA mount points to '/etc/fstab'.\n" + err + '\n' + out)
        debugLogger.info("The command used to add the SAP HANA mount points to '/etc/fstab' was: " + command)
        errorMessage = "Problems were encountered while adding SAP HANA mount points to '/etc/fstab'; thus the fstab file was not updated."
        return (errorMessage, hanaPartitionRestored)
    hanaPartitionRestored = True
    if not prepareUsrSAP():
        debugLogger.error("Problems were encountered while preparing '/usr/sap' for the SAP HANA archive restoration.")
        errorMessage = "Problems were encountered while preparing '/usr/sap' for the SAP HANA archive restoration."
        hanaPartitionRestored = False
        return (errorMessage, hanaPartitionRestored)
    logger.info('Done restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.')
    return (errorMessage, hanaPartitionRestored)


def prepareUsrSAP():
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Preparing /usr/sap for the SAP HANA restoration.')
    if not os.path.isdir('/usr/sap'):
        try:
            os.mkdir('/usr/sap')
        except OSError as err:
            debugLogger.error("Unable to create the '/usr/sap directory'.\n" + str(err))
            return False

    command = 'egrep -i "^\\s*(/[a-z-]+){2,}\\s+/usr/sap" /etc/fstab'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode == 0:
        command = 'mount'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error("Problems were encountered while checking to see if '/usr/sap' was already mounted.\n" + err + '\n' + out)
            debugLogger.info("The command used to check if '/usr/sap' was already mounted was: " + command)
            return False
        if re.search('on\\s+/usr/sap\\s+', out, re.DOTALL | re.MULTILINE) == None:
            command = 'mount /usr/sap'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                debugLogger.error("Problems were encountered while mounting '/usr/sap'.\n" + err + '\n' + out)
                debugLogger.info("The command used to mount '/usr/sap' was: " + command)
                return False
    else:
        debugLogger.info('Not mounting /usr/sap, since it is not present in /etc/fstab.')
    logger.info('Done preparing /usr/sap for the SAP HANA restoration.')
    return True


def prepareSAPHanaDirs(programParentDir, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Creating SID log, data, and shared mount points.')
    cursesThread.insertMessage(['informative', 'Creating SID log, data and shared mount points.'])
    cursesThread.insertMessage(['informative', ''])
    sidOwnershipFile = programParentDir + '/userLoginData/sidOwnership'
    try:
        hanaLogBasePath = '/hana/log/'
        hanaDataBasePath = '/hana/data/'
        hanaSharedBasePath = '/hana/shared/'
        with open(sidOwnershipFile) as f:
            for line in f:
                line = line.strip()
                sidData = line.split('|')
                hanaLogDir = hanaLogBasePath + sidData[0]
                if not os.path.isdir(hanaLogDir):
                    os.makedirs(hanaLogDir)
                os.chown(hanaLogDir, int(sidData[1]), int(sidData[2]))
                hanaDataDir = hanaDataBasePath + sidData[0]
                if not os.path.isdir(hanaDataDir):
                    os.makedirs(hanaDataDir)
                os.chown(hanaDataDir, int(sidData[1]), int(sidData[2]))
                hanaSharedDir = hanaSharedBasePath + sidData[0]
                if not os.path.isdir(hanaSharedDir):
                    os.makedirs(hanaSharedDir)
                os.chown(hanaSharedDir, int(sidData[1]), int(sidData[2]))

    except OSError as err:
        debugLogger.error("Problems were encountered while preparing the /hana/{data,log,shared}/SID directories using '" + sidOwnershipFile + "' as the reference file.\n" + str(err))
        errorMessage = 'Problems were encountered while preparing the /hana/{data,log,shared}/SID directories; thus they will have to be created manually.'

    logger.info('Done creating SID log, data, and shared mount points.')
    return errorMessage


def extractSAPRestorationArchive(programParentDir, osDist, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Extracting the SAP restoration archive.')
    cursesThread.insertMessage(['informative', 'Extracting the SAP restoration archive.'])
    cursesThread.insertMessage(['informative', ''])
    sapArchiveFileRegex = re.compile('.*_SAP_Restoration_Backup_For_' + osDist + '_Upgrade_[0-9]{6}[A-Za-z]{3}[0-9]{4}.tar.gz')
    archiveImageDir = programParentDir + '/archiveImages'
    command = 'ls ' + archiveImageDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error("Unable to get a listing of the files in '" + archiveImageDir + "'.\n" + err + '\n' + out)
        debugLogger.info("The command used to get a listing of the files in '" + archiveImageDir + "' was: " + command)
        errorMessage = "Unable to get a listing of the files in '" + archiveImageDir + "'; thus the SAP restoration archive was not extracted."
        return errorMessage
    fileList = out.splitlines()
    sapRestorationArchiveFound = False
    for file in fileList:
        if re.match(sapArchiveFileRegex, file):
            sapRestorationArchive = archiveImageDir + '/' + file
            sapRestorationArchiveFound = True
            break

    if not sapRestorationArchiveFound:
        debugLogger.error("The SAP restoration archive '" + archiveImageDir + '/' + sapArchiveFileRegex.pattern + "' could not be found.")
        errorMessage = "The SAP restoration archive '" + archiveImageDir + '/' + sapArchiveFileRegex.pattern + "' could not be found."
        return errorMessage
    command = 'tar -zxf ' + sapRestorationArchive + ' -C /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info("The command used to extract the SAP restoration archive was: '" + command + "'.")
    if result.returncode != 0:
        debugLogger.error("There was a problem extracting the SAP restoration archive '" + sapRestorationArchive + "'.\n" + err + '\n' + out)
        errorMessage = "There was a problem extracting the SAP restoration archive '" + sapRestorationArchive + "'."
        return errorMessage
    logger.info('Done extracting the SAP restoration archive.')
    return errorMessage


def updateBIOS(programParentDir, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info("Updating the server's BIOS.")
    cursesThread.insertMessage(['informative', "Updating the server's BIOS."])
    cursesThread.insertMessage(['informative', ''])
    command = 'conrep -l -f ' + programParentDir + '/conrepFile/conrep.dat'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    debugLogger.info("The command used to update the server's BIOS was: '" + command + "'.")
    if result.returncode != 0:
        debugLogger.error("An error was encountered while updating the server's BIOS.\n" + err + '\n' + out)
        errorMessage = "An error was encountered while updating the server's BIOS."
        return errorMessage
    logger.info("Done updating the server's BIOS.")
    return errorMessage


def checkSAPHANAConfiguration(serverModel, osDist, osDistLevel, *args):
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
            debugLogger.error("'force_latency' is not set to 70 in /usr/lib/tuned/saptune/tuned.conf.")
            errorsEncountered = True
    except IOError as err:
        debugLogger.error("Failed to confirm if 'force_latency' was set to 70.\n" + str(err))
        errorsEncountered = True

    if osDistLevel != '12.1' and osDist == 'SLES':
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
    command = 'tuned-adm active'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('Failed to confirm if the tuned active profile was set correctly.\n' + err + '\n' + out)
        debugLogger.info('The command used to check if the tuned active profile was set correctly was: ' + command)
        errorsEncountered = True
    else:
        profileError = False
        if osDist == 'SLES':
            if osDistLevel != '12.1':
                profile = 'saptune'
            elif serverModel != 'Superdome':
                profile = 'sap-hpe-hana'
            else:
                profile = 'sap-hana'
        elif serverModel != 'Superdome':
            profile = 'sap-hpe-hana'
        else:
            profile = 'sap-hana'
        if re.match('.*Current active profile:\\s+' + profile + '', out, re.MULTILINE | re.DOTALL) == None:
            debugLogger.error("The tuned active profile was not set to '" + profile + "'.\n" + out)
            debugLogger.info('The command used to check if the tuned active profile was set correctly was: ' + command)
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
    if osDist == 'SLES':
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
    logger.info('Done checking the SAP HANA tuning configuration.')
    return errorsEncountered


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


def configureNofile(limitsFile, nofileValue, cursesThread):
    solutionReverted = False
    softNofilePresent = False
    hardNofilePresent = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    debugLogger = logging.getLogger('coeOSUpgradeDebugLogger')
    logger.info('Configuring/Checking @sapsys nofile limit in /etc/security/limits.conf.')
    cursesThread.insertMessage(['informative', 'Configuring/Checking @sapsys nofile limit in /etc/security/limits.conf.'])
    cursesThread.insertMessage(['informative', ''])
    try:
        shutil.copy2(limitsFile, '/etc/security')
    except IOError as err:
        debugLogger.error('Unable to copy ' + limitsFile + ' to /etc/security.\n' + str(err))
        return 'Unable to copy ' + limitsFile + ' to /etc/security; thus saptune was not configured.'

    command = "awk '/^[[:space:]]*@sapsys[[:space:]]+[soft|hard]+[[:space:]]+nofile[[:space:]]+[0-9]+/{print}' /etc/security/limits.conf"
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        debugLogger.error('An error was encountered while getting the nofile data from /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
        debugLogger.info("The command used to get the nofile data from /etc/security/limits.conf for @sapsys was: '" + command + "'.")
        return 'An error was encountered while getting the nofile data from /etc/security/limits.conf for @sapsys; thus saptune was not configured.'
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
            return 'An error was encountered while reverting the HANA solution in preparation to update /etc/security/limits.conf for @sapsys; thus saptune was not configured.'
    for group in sapsysGroupList:
        try:
            currentNofileValue = re.match('.*\\s+([0-9]+)$', group).group(1)
            resourceHead = re.match('(.*)\\s+([0-9]+)$', group).group(1).strip()
        except AttributeError as err:
            debugLogger.error('An error was encountered while parsing ' + group + ', which was retrieved from /etc/security/limits.conf.\n' + str(err))
            return 'An error was encountered while parsing ' + group + ', which was retrieved from /etc/security/limits.conf; thus saptune was not configured.'

        if int(currentNofileValue) < int(nofileValue):
            if not solutionReverted:
                solutionReverted = True
                command = 'saptune solution revert HANA'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                out, err = result.communicate()
                if result.returncode != 0:
                    debugLogger.error('An error was encountered while reverting the HANA solution in preparation to update /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
                    debugLogger.info("The command used to revert the HANA solution in preparation to update /etc/security/limits.conf for @sapsys was: '" + command + "'.")
                    return 'An error was encountered while reverting the HANA solution in preparation to update /etc/security/limits.conf for @sapsys; thus saptune was not configured.'
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
                return 'An error was encountered while setting the nofile value in /etc/security/limits.conf for @sapsys; thus saptune was not configured.'

    if not softNofilePresent:
        command = "echo '@sapsys soft nofile " + nofileValue + "' >> /etc/security/limits.conf"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('An error was encountered while adding the soft nofile entry in /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
            debugLogger.info("The command used to add the soft nofile entry in /etc/security/limits.conf for @sapsys was: '" + command + "'.")
            return 'An error was encountered while adding the soft nofile entry in /etc/security/limits.conf for @sapsys; thus saptune was not configured.'
    if not hardNofilePresent:
        command = "echo '@sapsys hard nofile " + nofileValue + "' >> /etc/security/limits.conf"
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('An error was encountered while adding the hard nofile entry in /etc/security/limits.conf for @sapsys.\n' + err + '\n' + out)
            debugLogger.info("The command used to add the hard nofile entry in /etc/security/limits.conf for @sapsys was: '" + command + "'.")
            return 'An error was encountered while adding the hard nofile entry in /etc/security/limits.conf for @sapsys; thus saptune was not configured.'
    if solutionReverted:
        command = 'saptune solution apply HANA'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            debugLogger.error('An error was encountered while applying the HANA solution.\n' + err + '\n' + out)
            debugLogger.info("The command used to apply the HANA solution was: '" + command + "'.")
            return 'An error was encountered while applying the HANA solution; thus saptune was not configured.'
    logger.info('Done configuring/checking @sapsys nofile limit in /etc/security/limits.conf.')
    return ''