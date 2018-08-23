# Embedded file name: ./modules/sapHANANodeSpec.py
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

def getSapInitBackupList():
    sapInitList = []
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Getting the list of sapinit related files that will be added to the restoration backup.')
    command = 'find -L /etc -samefile /etc/init.d/sapinit'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        if not 'already visited the directory' in err:
            'No such' in err or logger.error("There was a problem getting the files linked to '/etc/init.d/sapinit'.\n" + err + '\n' + out)
            print RED + "There was a problem getting the files linked to '/etc/init.d/sapinit'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
        else:
            logger.warn('find complained while getting links to /etc/init.d/sapinit: \n' + err + '\n' + out)
    sapInitList += out.splitlines()
    logger.info('The list of sapinit related files that will be added to the restoration backup was determined to be: ' + str(sapInitList) + '.')
    logger.info('Done getting the list of sapinit related files that will be added to the restoration backup.')
    return sapInitList


def getConrepFile(programParentDir, conrepDir, processor):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Getting the conrep file that will be used during the post-upgrade to update the server's BIOS.")
    print GREEN + "Getting the conrep file that will be used during the post-upgrade to update the server's BIOS." + RESETCOLORS
    if not processor == 'ivybridge':
        if os.path.isfile('/usr/sbin/ssacli'):
            arrayCfgUtilFile = '/usr/sbin/ssacli'
        elif os.path.isfile('/usr/sbin/hpssacli'):
            arrayCfgUtilFile = '/usr/sbin/hpssacli'
        elif os.path.isfile('/usr/sbin/hpacucli'):
            arrayCfgUtilFile = '/usr/sbin/hpacucli'
        else:
            logger.error('There is no Smart Storage Administration software installed.\n')
            print RED + 'There is no Smart Storage Administration software installed; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
        command = arrayCfgUtilFile + ' ctrl all show'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            if re.search('No controllers detected', out, re.MULTILINE | re.DOTALL) == None:
                logger.error("Could not get the server's controller information.\n" + err + '\n' + out)
                print RED + "Could not get the server's  controller information; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)
            else:
                conrepFile = programParentDir + '/conrepFiles/' + processor + '/conrepSO.dat'
        else:
            conrepFile = programParentDir + '/conrepFiles/' + processor + '/conrepSU.dat'
    else:
        conrepFile = programParentDir + '/conrepFiles/' + processor + '/conrep.dat'
    logger.info('The conrep file was determined to be: ' + conrepFile + '.')
    try:
        renamedConrepFile = conrepDir + '/conrep.dat'
        os.mkdir(conrepDir)
        shutil.copy2(conrepFile, renamedConrepFile)
    except (OSError, IOError) as err:
        logger.error("Unable to copy the conrep file '" + renamedConrepFile + "' to '" + conrepDir + "'.\n" + str(err))
        print RED + "Unable to copy the conrep file '" + renamedConrepFile + "' to '" + conrepDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    logger.info("Done getting the conrep file that will be used during the post-upgrade to update the server's BIOS.")
    return


def getSAPUserLoginData(upgradeWorkingDir, sidList, **kwargs):
    userLoginDataDir = upgradeWorkingDir + '/userLoginData'
    hanaHomeDirList = []
    if 'tenantUserDict' in kwargs:
        tenantUserDict = kwargs['tenantUserDict']
    else:
        tenantUserDict = {}
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Getting SAP HANA user account login data.')
    print GREEN + 'Getting SAP HANA user account login data.' + RESETCOLORS
    if not os.path.isdir(userLoginDataDir):
        try:
            os.mkdir(userLoginDataDir)
        except OSError as err:
            logger.error("Unable to create the pre-upgrade user login data directory '" + userLoginDataDir + "'.\n" + str(err))
            print RED + "Unable to create the pre-upgrade user login data directory '" + userLoginDataDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    passwordFile = userLoginDataDir + '/passwd'
    shadowFile = userLoginDataDir + '/shadow'
    groupFile = userLoginDataDir + '/group'
    sidOwnershipFile = userLoginDataDir + '/sidOwnership'
    command = 'cat /etc/passwd'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("There was a problem getting the password information from '/etc/passwd'.\n" + err + '\n' + out)
        print RED + "There was a problem getting the password information from '/etc/passwd'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    passwordList = out.splitlines()
    passwordDict = dict(((x.split(':')[0], [x, x.split(':')[3]]) for x in passwordList))
    if 'sapadm' in passwordDict:
        sidList.append('SAP')
        logger.info('The SID list was determined to be: ' + str(sidList) + '.')
    command = 'cat /etc/shadow'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("There was a problem getting the shadow information from '/etc/shadow'.\n" + err + '\n' + out)
        print RED + "There was a problem getting the shadow information from '/etc/shadow'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    shadowList = out.splitlines()
    shadowDict = dict(((x.split(':')[0], x) for x in shadowList))
    command = 'cat /etc/group'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("There was a problem getting the group information from '/etc/group'.\n" + err + '\n' + out)
        print RED + "There was a problem getting the group information from '/etc/group'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    groupList = out.splitlines()
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
            if sidadm in passwordDict:
                if sid != 'SAP':
                    sidOwnership.write(sid + '|' + passwordDict[sidadm][0].split(':')[2] + '|' + passwordDict[sidadm][0].split(':')[3] + '\n')
                passwd.write(passwordDict[sidadm][0] + '\n')
                if sidadm not in shadowDict:
                    logger.warn('The login account information was missing from /etc/shadow for: ' + sidadm + '.')
                    print YELLOW + 'Warning the login account information was missing from /etc/shadow for: ' + sidadm + '.' + RESETCOLORS
                else:
                    shadow.write(shadowDict[sidadm] + '\n')
                if passwordDict[sidadm][1] not in groupAddedDict:
                    try:
                        group.write(groupDict[passwordDict[sidadm][1]] + '\n')
                    except AttributeError as err:
                        logger.error("The group information for '" + sidadm + "' is missing.\n" + str(err))
                        print RED + "The  group information for '" + sidadm + "' is missing; fix the problem and try again; exiting program execution." + RESETCOLORS
                        exit(1)

                    groupAddedDict[passwordDict[sidadm][1]] = None
            else:
                logger.info('The login account information was missing from /etc/passwd for: ' + sidadm + '.')
                print RED + 'The login account information was missing from /etc/passwd for: ' + sidadm + '; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)

        if len(tenantUserDict) != 0:
            for tenantUser in tenantUserDict:
                homeDir = '/home/' + tenantUser
                if os.path.isdir(homeDir):
                    hanaHomeDirList.append(homeDir)
                if tenantUser in passwordDict:
                    passwd.write(passwordDict[tenantUser][0] + '\n')
                    shadow.write(shadowDict[tenantUser] + '\n')
                    groupList = tenantUserDict[tenantUser]
                    for groupID in groupList:
                        if groupID not in groupAddedDict:
                            try:
                                group.write(groupDict[groupID] + '\n')
                            except AttributeError as err:
                                logger.error("The group information for '" + tenantUser + "' is missing.\n" + str(err))
                                print RED + "The  group information for '" + tenantUser + "' is missing; fix the problem and try again; exiting program execution." + RESETCOLORS
                                exit(1)

                            groupAddedDict[groupID] = None

                else:
                    logger.info('The login account information was missing for: ' + tenantUser + '.')
                    print RED + 'The login account information was missing for: ' + tenantUser + '; fix the problem and try again; exiting program execution.' + RESETCOLORS

    except IOError as err:
        logger.error('Could not write user account login data.\n' + str(err))
        print RED + 'Could not write user account login data; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)

    passwd.close()
    shadow.close()
    group.close()
    logger.info('Done getting SAP HANA user account login data.')
    return hanaHomeDirList


def getHANAFstabData(upgradeWorkingDir, fstabHANAEntries, serverModel, processor):
    fstabDataDir = upgradeWorkingDir + '/fstabData'
    hanaSharedWithSID = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Getting SAP HANA related partition data from '/etc/fstab'.")
    print GREEN + "Getting SAP HANA related partition data from '/etc/fstab'." + RESETCOLORS
    if not os.path.isdir(fstabDataDir):
        try:
            os.mkdir(fstabDataDir)
        except OSError as err:
            logger.error("Unable to create the pre-upgrade fstab data directory '" + fstabDataDir + "'.\n" + str(err))
            print RED + "Unable to create the pre-upgrade fstab data directory '" + fstabDataDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    fstabFile = fstabDataDir + '/fstab'
    command = 'cat /etc/fstab'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('There was a problem getting the SAP HANA partition data from /etc/fstab.\n' + err + '\n' + out)
        print RED + 'There was a problem getting the SAP HANA partition data from /etc/fstab; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    fstabDataList = out.splitlines()
    try:
        f = open(fstabFile, 'w')
        for line in fstabDataList:
            if any((fstabHANAEntry in line for fstabHANAEntry in fstabHANAEntries)):
                if re.match('\\s*#', line) == None:
                    if serverModel == 'Superdome' and processor == 'haswell':
                        if '/hana/shared' in line:
                            if re.match('\\s*([0-9]{1,3}.){3}[0-9]{1,3}:.*/hana/shared.*', line) == None:
                                hanaSharedWithSID = True
                    f.write(line + '\n')

    except IOError as err:
        logger.error("Could not write HANA fstab data to '" + fstabFile + "'.\n" + str(err))
        print RED + "Could not write HANA fstab data to '" + fstabFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)

    f.close()
    logger.info("Done getting SAP HANA related partition data from '/etc/fstab'.")
    return hanaSharedWithSID


def checkSAPHANA(upgradeWorkingDir, hanaSharedWithSID, serverModel):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Checking SAP HANA related components.')
    print GREEN + 'Checking SAP HANA related components.' + RESETCOLORS
    command = 'ps -C hdbnameserver,hdbcompileserver,hdbindexserver,hdbpreprocessor,hdbxsengine,hdbwebdispatcher'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode == 0:
        logger.error('SAP HANA is still running.\n' + out)
        print RED + 'It appears that SAP HANA is still running; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    sidList = getSIDList()
    command = 'mount'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Unable to check if the /hana/shared partition is mounted.\n' + err + '\n' + out)
        print RED + 'Unable to check if the /hana/shared partition is mounted; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    if not hanaSharedWithSID:
        if re.search('/hana/shared', out, re.MULTILINE | re.DOTALL) == None:
            logger.error("The '/hana/shared' partition is not mounted.\n" + out)
            print RED + "The '/hana/shared' partition is not mounted; please mount it and try again; exiting program execution." + RESETCOLORS
            exit(1)
    else:
        for sid in sidList:
            hanaShared = '/hana/shared/' + sid
            if re.search(hanaShared, out, re.MULTILINE | re.DOTALL) == None:
                logger.error("The '" + hanaShared + "' partition is not mounted.\n" + out)
                print RED + "The '" + hanaShared + "' partition is not mounted; please mount it and try again; exiting program execution." + RESETCOLORS
                exit(1)

    multiTenantSIDList = getGlobalIniFiles(upgradeWorkingDir, sidList)
    unMountHANAShared(serverModel, sidList, hanaSharedWithSID)
    logger.info('Done checking SAP HANA related components.')
    return (sidList, multiTenantSIDList)


def getSIDList():
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Getting the SID list for the currently active SIDs as identified by '/usr/sap/sapservices'.")
    sidList = []
    command = 'cat /usr/sap/sapservices'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error('Unable to get the SAP HANA SID information.\n' + err + '\n' + out)
        print RED + 'Unable to get the SAP HANA SID information; fix the problem and try again; exiting program execution.' + RESETCOLORS
        exit(1)
    sapServicesData = out.splitlines()
    for data in sapServicesData:
        if re.match('\\s*LD_LIBRARY_PATH\\s*=\\s*/usr/sap', data):
            try:
                sid = re.match('\\s*LD_LIBRARY_PATH\\s*=\\s*/usr/sap.*([a-z0-9]{3})adm$', data).group(1).upper()
            except AttributeError as err:
                logger.error("There was a match error when trying to match against '" + data + "'.\n" + str(err))
                print RED + "There was a match error when trying to match against '" + data + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

            sidList.append(sid)

    logger.info("The active SID list as determined by '/usr/sap/sapservices' was: " + str(sidList) + '.')
    logger.info("Done getting the SID list for the currently active SIDs as identified by '/usr/sap/sapservices'.")
    return sidList


def getGlobalIniFiles(upgradeWorkingDir, sidList):
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Getting the global.ini files for the currently active SIDs and tenant user information if the SID is a MDC.')
    tenantUserDict = {}
    for sid in sidList:
        multiTenant = False
        globalIni = '/hana/shared/' + sid + '/global/hdb/custom/config/global.ini'
        sidDir = upgradeWorkingDir + '/' + sid
        if os.path.isfile(globalIni):
            multiTenant = checkMultiTenant(globalIni, sid)
            if not os.path.isdir(sidDir):
                try:
                    os.mkdir(sidDir)
                except OSError as err:
                    logger.error("Unable to create the backup global.ini SID directory '" + sidDir + "'.\n" + str(err))
                    print RED + "Unable to create the backup global.ini SID directory '" + sidDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)

            try:
                shutil.copy2(globalIni, sidDir)
            except IOError as err:
                logger.error("Unable to copy the global.ini to '" + sidDir + "'.\n" + str(err))
                print RED + "Unable to copy the global.ini to '" + sidDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

            if multiTenant:
                databaseListFile = '/hana/shared/' + sid + '/global/hdb/mdc/databases.lst'
                try:
                    shutil.copy2(databaseListFile, sidDir)
                except IOError as err:
                    logger.error("Unable to copy '" + databaseListFile + "' to '" + sidDir + "'.\n" + str(err))
                    print RED + "Unable to copy '" + databaseListFile + "' to '" + sidDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)

                try:
                    with open(databaseListFile) as f:
                        for line in f:
                            line = line.strip()
                            if len(line) == 0 or re.match('^\\s*#', line) or re.match('^\\s+$', line):
                                continue
                            else:
                                tenantUser = line.split(':')[2]
                                command = 'id -G ' + tenantUser
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()
                                tenantUserDict[tenantUser] = out.strip().split()

                except IOError as err:
                    logger.error("Unable to access '" + databaseListFile + "'.\n" + str(err))
                    print RED + "Unable to access '" + databaseListFile + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                    exit(1)

        else:
            logger.warn("A custom global.ini '" + globalIni + "' was not present for SID " + sid + '.')
            print YELLOW + "A custom global.ini '" + globalIni + "' was not present for SID " + sid + '.' + RESETCOLORS

    logger.info('Done getting the global.ini files for the currently active SIDs and tenant user information if the SID is a MDC.')
    return tenantUserDict


def checkMultiTenant(globalIni, sid):
    multiTenant = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Checking to see if '" + sid + "' is a multitenant database container.")
    command = 'cat ' + globalIni
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Unable to access '" + globalIni + "' to check if '" + sid + "' is a multitenant database container.\n" + err + '\n' + out)
        print RED + "Unable to access '" + globalIni + "' to check if '" + sid + "' is a multitenant database container; fix the problem and try again; exiting program execution." + RESETCOLORS
        exit(1)
    out = out.strip()
    if re.match('.*mode\\s*=\\s*multidb', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) != None:
        multiTenant = True
    logger.info("Done checking to see if '" + sid + "' is a multitenant database container.")
    return multiTenant


def unMountHANAShared(serverModel, sidList, hanaSharedWithSID):
    logger = logging.getLogger('coeOSUpgradeLogger')
    command = 'service sapinit status'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        if re.search('No process running', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) == None:
            logger.error('Unable to get the status of sapinit.\n' + err + '\n' + out)
            print RED + 'Unable to get the status of sapinit; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    if re.search('No process running', out, re.MULTILINE | re.DOTALL | re.IGNORECASE) == None:
        command = 'service sapinit stop'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Unable to stop the sapinit process.\n' + err + '\n' + out)
            print RED + 'Unable to stop the sapinit process; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    command = 'ps -fC hdbrsutil'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode == 0:
        command = 'killall -v hdbrsutil'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error('Problems were encountered when trying to kill hdbrsutil.\n' + err + '\n' + out)
            print RED + 'Problems were encountered when trying to kill hdbrsutil; fix the problem and try again; exiting program execution.' + RESETCOLORS
            exit(1)
    time.sleep(10.0)
    if not hanaSharedWithSID:
        command = 'umount /hana/shared'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Unable to unmount '/hana/shared'.\n" + err + '\n' + out)
            print RED + "Unable to unmount '/hana/shared' (Note, /hana/shared needs to be mounted initially when the program runs); fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)
    else:
        for sid in sidList:
            hanaShared = '/hana/shared/' + sid
            command = 'umount ' + hanaShared
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Unable to unmount '" + hanaShared + "'.\n" + err + '\n' + out)
                print RED + "Unable to unmount '" + hanaShared + "' (Note, /hana/shared/SID needs to be mounted initially when the program runs); fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

    return


def installAddOnFiles(programParentDir, upgradeResourceDict, osDist, cursesThread, **kwargs):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
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
        logger.error('An error was encountered while installing/replacing the files from the add-on file archive.\n' + err + '\n' + out)
        errorMessage = 'An error was encountered while installing/replacing the files from the add-on file archive.'
        return errorMessage
    logger.info('Done installing/replacing the files from the add-on archive.')
    return errorMessage


def restoreHANAUserAccounts(programParentDir, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Restoring SAP HANA user accounts.')
    cursesThread.insertMessage(['informative', 'Restoring SAP HANA user accounts.'])
    cursesThread.insertMessage(['informative', ''])
    userLoginDataDir = programParentDir + '/userLoginData'
    accountFileList = ['group', 'passwd', 'shadow']
    for file in accountFileList:
        accountFile = '/etc/' + file
        command = 'cat ' + userLoginDataDir + '/' + file + ' >> ' + accountFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Problems were encountered while adding SAP HANA user accounts to '" + accountFile + "'.\n" + err + '\n' + out)
            errorMessage = "Problems were encountered while adding SAP HANA user accounts to '" + accountFile + "'; thus the SAP HANA accounts were not successfully restored."
            return errorMessage

    logger.info('Done restoring SAP HANA user accounts.')
    return errorMessage


def restoreHANAPartitionData(programParentDir, cursesThread):
    errorMessage = ''
    hanaPartitionRestored = False
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.')
    cursesThread.insertMessage(['informative', 'Restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.'])
    cursesThread.insertMessage(['informative', ''])
    fstabDataFile = programParentDir + '/fstabData/fstab'
    command = 'cat ' + fstabDataFile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("There was a problem getting the SAP HANA partition data from '" + fstabDataFile + "'.\n" + err + '\n' + out)
        errorMessage = "There was a problem getting the SAP HANA partition data from '" + fstabDataFile + "'; thus the SAP HANA partition data was not successfully restored."
        return (errorMessage, hanaPartitionRestored)
    fstabDataList = out.splitlines()
    for partition in fstabDataList:
        partitionList = partition.split()
        partition = partitionList[1]
        if not os.path.isdir(partition):
            try:
                os.makedirs(partition)
            except OSError as err:
                logger.error("Unable to create the mount point '" + partition + "'.\n" + str(err))
                errorMessage = "Unable to create the mount point '" + partition + "'; thus the SAP HANA partition data was not successfully restored."
                return (errorMessage, hanaPartitionRestored)

    command = 'cat ' + fstabDataFile + ' >> /etc/fstab'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Problems were encountered while adding SAP HANA mount points to '/etc/fstab'.\n" + err + '\n' + out)
        errorMessage = "Problems were encountered while adding SAP HANA mount points to '/etc/fstab'; thus the fstab file was not updated."
        return (errorMessage, hanaPartitionRestored)
    hanaPartitionRestored = True
    if not prepareUsrSAP():
        logger.error("Problems were encountered while preparing '/usr/sap' for the SAP HANA archive restoration.")
        errorMessage = "Problems were encountered while preparing '/usr/sap' for the SAP HANA archive restoration."
        hanaPartitionRestored = False
        return (errorMessage, hanaPartitionRestored)
    logger.info('Done restoring SAP HANA mount points and SAP HANA entries to /etc/fstab.')
    return (errorMessage, hanaPartitionRestored)


def prepareUsrSAP():
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Preparing /usr/sap for the SAP HANA restoration.')
    if not os.path.isdir('/usr/sap'):
        try:
            os.mkdir('/usr/sap')
        except OSError as err:
            logger.error("Unable to create the '/usr/sap directory'.\n" + str(err))
            return False

    command = 'egrep -i "^\\s*(/[a-z-]+){2,}\\s+/usr/sap" /etc/fstab'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode == 0:
        command = 'mount'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        if result.returncode != 0:
            logger.error("Problems were encountered while checking to see if '/usr/sap' was already mounted.\n" + err + '\n' + out)
            return False
        if re.search('on\\s+/usr/sap\\s+', out, re.DOTALL | re.MULTILINE) == None:
            command = 'mount /usr/sap'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            if result.returncode != 0:
                logger.error("Problems were encountered while mounting '/usr/sap'.\n" + err + '\n' + out)
                return False
    else:
        logger.info('Not mounting /usr/sap, since it is not present in /etc/fstab.')
    logger.info('Done preparing /usr/sap for the SAP HANA restoration.')
    return True


def prepareSAPHanaDirs(programParentDir, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
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
        logger.error("Problems were encountered while preparing the /hana/{data,log,shared}/SID directories using '" + sidOwnershipFile + "' as the reference file.\n" + str(err))
        errorMessage = 'Problems were encountered while preparing the /hana/{data,log,shared}/SID directories; thus they will have to be created manually.'

    logger.info('Done creating SID log, data, and shared mount points.')
    return errorMessage


def updateRHELOSSettings(cursesThread):
    errorMessageList = []
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Updating the server's OS settings according to SAP Note 2292690.")
    cursesThread.insertMessage(['informative', "Updating the server's OS settings according to SAP Note 2292690."])
    cursesThread.insertMessage(['informative', ''])
    updateMade = False
    grubCfgFile = '/etc/default/grub'
    try:
        with open(grubCfgFile) as f:
            for line in f:
                line = line.strip()
                if re.match('\\s*GRUB_CMDLINE_LINUX=', line) != None:
                    grubDefault = line
                    if 'intel_idle.max_cstate' in grubDefault:
                        if re.match('.*intel_idle.max_cstate=1', grubDefault) == None:
                            grubDefault = re.sub('intel_idle.max_cstate=[0-9]{1}', 'intel_idle.max_cstate=1', grubDefault)
                            updateMade = True
                    else:
                        grubDefault = grubDefault[:-1] + ' intel_idle.max_cstate=1"'
                        updateMade = True
                    if 'processor.max_state' in grubDefault:
                        if re.match('.*processor.max_state=1', grubDefault) == None:
                            grubDefault = re.sub('processor.max_state=[0-9]{1}', 'processor.magxstate=1', grubDefault)
                            if not updateMade:
                                updateMade = True
                    else:
                        grubDefault = grubDefault[:-1] + ' processor.max_state=1"'
                        if not updateMade:
                            updateMade = True
                    break

    except OSError as err:
        logger.error("Unable to access grub's default configuration file '" + grubCfgFile + "' to update its C-States.\n" + str(err))
        errorMessageList.append("Unable to access grub's default configuration file '" + grubCfgFile + "' to update its C-States.")

    if updateMade:
        command = "sed -i 's|^\\s*GRUB_CMDLINE_LINUX=.*|" + grubDefault + "|' " + grubCfgFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info("The command used to update grub's default configuration file '" + grubCfgFile + "' C-States was: '" + command + "'.")
        if result.returncode != 0:
            logger.error("Could not update the C-States settings in '" + grubCfgFile + "'.\n" + err + '\n' + out)
            errorMessageList.append('Could not update the C-States settings in ' + grubCfgFile + '.')
        else:
            bootGrubCfgFile = '/boot/efi/EFI/redhat/grub.cfg'
            command = 'grub2-mkconfig -o ' + bootGrubCfgFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.info("The command used to generate a new grub.cfg file was: '" + command + "'.")
            if result.returncode != 0:
                logger.error('Could not update the GRUB2 configuration with the updated C-States settings.\n' + err + '\n' + out)
                errorMessageList.append('Could not update the GRUB2 configuration with the updated C-States settings.')
    logger.info("Done updating the server's OS settings according to SAP Note 2292690.")
    return errorMessageList


def updateSLESOSSettings(cursesThread):
    errorMessageList = []
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Updating the server's OS settings according to SAP Note 2205917.")
    cursesThread.insertMessage(['informative', "Updating the server's OS settings according to SAP Note 2205917."])
    cursesThread.insertMessage(['informative', ''])
    updateMade = False
    grubCfgFile = '/etc/default/grub'
    try:
        with open(grubCfgFile) as f:
            for line in f:
                line = line.strip()
                if re.match('\\s*GRUB_CMDLINE_LINUX_DEFAULT=', line) != None:
                    grubDefault = line
                    if 'intel_idle.max_cstate' in grubDefault:
                        if re.match('.*intel_idle.max_cstate=1', grubDefault) == None:
                            grubDefault = re.sub('intel_idle.max_cstate=[0-9]{1}', 'intel_idle.max_cstate=1', grubDefault)
                            updateMade = True
                    else:
                        grubDefault = grubDefault[:-1] + ' intel_idle.max_cstate=1"'
                        updateMade = True
                    if 'processor.max_state' in grubDefault:
                        if re.match('.*processor.max_state=1', grubDefault) == None:
                            grubDefault = re.sub('processor.max_state=[0-9]{1}', 'processor.magxstate=1', grubDefault)
                            if not updateMade:
                                updateMade = True
                    else:
                        grubDefault = grubDefault[:-1] + ' processor.max_state=1"'
                        if not updateMade:
                            updateMade = True
                    break

    except OSError as err:
        logger.error("Unable to access grub's default configuration file '" + grubCfgFile + "' to update its C-States.\n" + str(err))
        errorMessageList.append("Unable to access grub's default configuration file '" + grubCfgFile + "' to update its C-States.")

    if updateMade:
        command = "sed -i 's|^\\s*GRUB_CMDLINE_LINUX_DEFAULT=.*|" + grubDefault + "|' " + grubCfgFile
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.info("The command used to update grub's default configuration file '" + grubCfgFile + "' C-States was: '" + command + "'.")
        if result.returncode != 0:
            logger.error("Could not update the C-States settings in '" + grubCfgFile + "'.\n" + err + '\n' + out)
            errorMessageList.append('Could not update the C-States settings in ' + grubCfgFile + '.')
        else:
            bootGrubCfgFile = '/boot/grub2/grub.cfg'
            command = 'grub2-mkconfig -o ' + bootGrubCfgFile
            command = 'grub2-mkconfig -o ' + bootGrubCfgFile
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.info("The command used to generate a new grub.cfg file was: '" + command + "'.")
            if result.returncode != 0:
                logger.error('Could not update the GRUB2 configuration with the updated C-States settings.\n' + err + '\n' + out)
                errorMessageList.append('Could not update the GRUB2 configuration with the updated C-States settings.')
    logger.info("Done updating the server's OS settings according to SAP Note 2205917.")
    return errorMessageList


def updateTuningProfile(serverModel, cursesThread):
    errorMessage = ''
    if serverModel == 'Superdome':
        tuningProfile = 'sap-hana-cs900'
    else:
        tuningProfile = 'sap-hpe-hana'
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Updating the OS's tuning profile to be '" + tuningProfile + "'.")
    cursesThread.insertMessage(['informative', "Updating the OS's tuning profile to be '" + tuningProfile + "'."])
    cursesThread.insertMessage(['informative', ''])
    command = 'tuned-adm profile ' + tuningProfile
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Problems were encountered while updating the OS's tuning profile to be '" + tuningProfile + "'.\n" + err + '\n' + out)
        errorMessage = "Problems were encountered while updating the OS's tuning profile to be '" + tuningProfile + "'."
        return errorMessage
    logger.info("Done updating the OS's tuning profile to be '" + tuningProfile + "'.")
    return errorMessage


def extractSAPRestorationArchive(programParentDir, osDist, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info('Extracting the SAP restoration archive.')
    cursesThread.insertMessage(['informative', 'Extracting the SAP restoration archive.'])
    cursesThread.insertMessage(['informative', ''])
    sapArchiveFileRegex = re.compile('.*_SAP_Restoration_Backup_For_' + osDist + '_Upgrade_[0-9]{6}[A-Za-z]{3}[0-9]{4}.tar.gz')
    archiveImageDir = programParentDir + '/archiveImages'
    command = 'ls ' + archiveImageDir
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if result.returncode != 0:
        logger.error("Unable to get a listing of the files in '" + archiveImageDir + "'.\n" + err + '\n' + out)
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
        logger.error("The SAP restoration archive '" + archiveImageDir + '/' + sapArchiveFileRegex.pattern + "' could not be found.")
        errorMessage = "The SAP restoration archive '" + archiveImageDir + '/' + sapArchiveFileRegex.pattern + "' could not be found."
        return errorMessage
    command = 'tar -zxf ' + sapRestorationArchive + ' -C /'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info("The command used to extract the SAP restoration archive was: '" + command + "'.")
    if result.returncode != 0:
        logger.error("There was a problem extracting the SAP restoration archive '" + sapRestorationArchive + "'.\n" + err + '\n' + out)
        errorMessage = "There was a problem extracting the SAP restoration archive '" + sapRestorationArchive + "'."
        return errorMessage
    logger.info('Done extracting the SAP restoration archive.')
    return errorMessage


def updateBIOS(programParentDir, cursesThread):
    errorMessage = ''
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.info("Updating the server's BIOS.")
    cursesThread.insertMessage(['informative', "Updating the server's BIOS."])
    cursesThread.insertMessage(['informative', ''])
    command = 'conrep -l -f ' + programParentDir + '/conrepFile/conrep.dat'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.info("The command used to update the server's BIOS was: '" + command + "'.")
    if result.returncode != 0:
        logger.error("An error was encountered while updating the server's BIOS.\n" + err + '\n' + out)
        errorMessage = "An error was encountered while updating the server's BIOS."
        return errorMessage
    logger.info("Done updating the server's BIOS.")
    return errorMessage