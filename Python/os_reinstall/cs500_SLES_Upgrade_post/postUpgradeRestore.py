# Embedded file name: ./postUpgradeRestore.py
import subprocess
import re
import os
import sys
import logging
import time
import traceback
import datetime
import optparse
from modules.cursesThread import CursesThread
from modules.computeNode import getOSDistribution, getServerModel, getProcessorType
from modules.sapHANANodeSpec import installAddOnFiles, restoreHANAUserAccounts, restoreHANAPartitionData, updateTuningProfile, prepareSAPHanaDirs, extractSAPRestorationArchive, updateBIOS
from modules.upgradeMisc import installSLESAddOnSoftware, installRHELAddOnSoftware, extractOSRestorationArchive, checkOSRestorationArchive, updateOSRestorationArchiveErrorFile, updateNTPConf, setHostname, updateMultipathConf, updateKdump, configureSnapper, setTimezone, displayErrorMessage
from modules.serviceGuardNodeSpec import buildDeadmanDriver, configureXinetd, updateNFSListeners, createNFSMountPoint, updateClusterCfg, configureServiceguardQS, updateLvmConf
RED = '\x1b[31m'
RESETCOLORS = '\x1b[0m'

def main():
    programVersion = '2018.03-0'
    addOnSoftwareInstalled = False
    hanaPartitionsRestored = False
    scaleUpSystem = False
    errorMessageList = []
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS
        exit(1)
    usage = 'usage: %prog [[-h] [-p] [-v]]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-p', action='store_true', default=False, help='This option should be ran from the primary NFS Serviceguard node after the upgrade of both nodes when the upgrade caused the NIC cards to be renamed on one or both of the NFS Serviceguard nodes.')
    parser.add_option('-v', action='store_true', default=False, help="This option is used to display the application's version.")
    options, args = parser.parse_args()
    programName = os.path.basename(sys.argv[0])
    if options.v:
        print programName + ' ' + programVersion
        exit(0)
    osDist, osDistLevel = getOSDistribution()
    upgradeLogDir = '/var/log/CoESapHANA_' + osDist + '_UpgradeLogDir'
    if not os.path.isdir(upgradeLogDir):
        try:
            os.mkdir(upgradeLogDir)
        except OSError as err:
            print RED + "Unable to create the post upgrade log directory '" + upgradeLogDir + "'; fix the problem and try again; exiting program execution.\n" + str(err) + RESETCOLORS
            exit(1)

    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    logFile = upgradeLogDir + '/' + osDist + '_Post_Upgrade_' + dateTimestamp + '.log'
    handler = logging.FileHandler(logFile)
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info('The current version of the program is: ' + programVersion + '.')
    serverModel = getServerModel()
    if 'DL580' in serverModel:
        processor = getProcessorType()
    if options.p:
        if not ('DL380p' in serverModel or 'DL360p' in serverModel):
            print RED + "The '-p' option is only for Serviceguard NFS servers; exiting program execution." + RESETCOLORS
            exit(1)
        updateClusterCfg()
    else:
        try:
            programParentDir = ''
            cwd = os.getcwd()
            programParentDir = os.path.dirname(os.path.realpath(__file__))
            if cwd != programParentDir:
                os.chdir(programParentDir)
        except OSError as err:
            logger.error("Unable to change into the programs parent directory '" + programParentDir + "'.\n" + str(err))
            print RED + "Unable to change into the programs parent directory '" + programParentDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

        if osDist == 'SLES':
            from modules.upgradeMisc import checkSLESNetworkConfiguration as checkNetworkConfiguration
        else:
            from modules.upgradeMisc import checkRHELNetworkConfiguration as checkNetworkConfiguration
        if 'DL580' in serverModel or serverModel == 'Superdome':
            if osDist == 'SLES':
                from modules.sapHANANodeSpec import updateSLESOSSettings as updateOSSettings
            else:
                from modules.sapHANANodeSpec import updateRHELOSSettings as updateOSSettings
        if 'DL580' in serverModel:
            command = 'cat /proc/scsi/scsi'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            out = out.strip()
            if result.returncode != 0:
                logger.error('Unable to determine if the DL580 is a Scale-up.\n' + str(out) + '\n' + str(err))
                print RED + 'Unable to determine if the DL580 is a Scale-up; fix the problem and try again; exiting program execution.' + RESETCOLORS
                exit(1)
            searchResult = re.search('P830i', out, re.MULTILINE | re.DOTALL)
            if not searchResult == None:
                globalIni = 'global.ini'
                globalIniList = []
                scaleOutSystem = False
                for root, dirs, files in os.walk(programParentDir):
                    if globalIni in files:
                        globalIniList.append(root + '/' + globalIni)

                for file in globalIniList:
                    with open(file, 'r') as f:
                        data = f.read()
                        if re.match('.*log|data_{1,}wwid\\s*=\\s*360002ac0+', data, re.MULTILINE | re.DOTALL) != None:
                            scaleOutSystem = True
                            multipathArguments = ['enable', 'start']
                            for argument in multipathArguments:
                                command = 'systemctl ' + argument + ' multipathd'
                                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, err = result.communicate()
                                out = out.strip()
                                if result.returncode != 0:
                                    logger.error('Unable to ' + argument + ' multipathd.\n' + str(out) + '\n' + str(err))
                                    print RED + 'Unable to ' + argument + ' multipathd; fix the problem and try again; exiting program execution.' + RESETCOLORS
                                    exit(1)
                                time.sleep(0.1)

                            break

                if not scaleOutSystem:
                    scaleUpSystem = True
        upgradeResourceDict = {}
        try:
            with open('upgradeResourceFile') as f:
                for line in f:
                    line = line.strip()
                    if len(line) == 0 or re.match('^\\s*#', line) or re.match('^\\s+$', line):
                        continue
                    else:
                        line = re.sub('[\'"]', '', line)
                        key, val = line.split('=')
                        key = key.strip()
                        upgradeResourceDict[key] = re.sub('\\s*,\\s*', ',', val).strip()

        except IOError as err:
            logger.error("Unable to access the application's resource file 'upgradeResourceFile'.\n" + str(err))
            print RED + "Unable to access the application's resource file 'upgradeResourceFile'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

        sessionScreenLog = upgradeLogDir + '/sessionScreenLog.log'
        cursesLog = upgradeLogDir + '/cursesLog.log'
        try:
            cursesThread = CursesThread(sessionScreenLog, cursesLog)
            cursesThread.daemon = True
            cursesThread.start()
            osRestorationArchiveErrorFile = upgradeLogDir + '/.osRestorationArchiveError'
            if not os.path.isfile(osRestorationArchiveErrorFile):
                try:
                    os.mknod(osRestorationArchiveErrorFile)
                except OSError as err:
                    logger.error("Unable to create the OS restoration archive error file '" + osRestorationArchiveErrorFile + "'.\n" + str(err))
                    displayErrorMessage("Unable to create the OS restoration archive error file '" + osRestorationArchiveErrorFile + "'; fix the problem and try again.", cursesThread)

            progressStatusFile = upgradeLogDir + '/.restorationProgress'
            try:
                if os.path.isfile(progressStatusFile):
                    with open(progressStatusFile) as f:
                        progressDict = dict.fromkeys((x.strip() for x in f))
                else:
                    progressDict = {}
                if os.path.isfile(progressStatusFile):
                    f = open(progressStatusFile, 'a')
                else:
                    f = open(progressStatusFile, 'w')
                osRestorationArchiveExtracted = False
                try:
                    if os.stat(osRestorationArchiveErrorFile).st_size < 50 and 'osRestorationArchiveExtracted' not in progressDict:
                        cursesThread.insertMessage(['informative', 'Checking and extracting the OS restoration archive file.'])
                        cursesThread.insertMessage(['informative', ''])
                        osRestorationArchive = checkOSRestorationArchive(programParentDir, osRestorationArchiveErrorFile, osDist, cursesThread)
                        extractOSRestorationArchive(osRestorationArchive, osRestorationArchiveErrorFile, cursesThread)
                        f.write('osRestorationArchiveExtracted\n')
                        osRestorationArchiveExtracted = True
                except OSError as err:
                    logger.error("Unable to access the OS restoration archive error file '" + osRestorationArchiveErrorFile + "'.\n" + str(err))
                    displayErrorMessage("Unable to access the OS restoration archive error file '" + osRestorationArchiveErrorFile + "'; fix the problem and try again.", cursesThread)

                if os.path.isdir(programParentDir + '/addOnSoftwareRPMS'):
                    if 'installaddOnSoftware' not in progressDict:
                        f.write('installaddOnSoftware\n')
                        if osDist == 'SLES':
                            errorMessage, addOnSoftwareInstalled = installSLESAddOnSoftware(programParentDir, cursesThread)
                        else:
                            errorMessage, addOnSoftwareInstalled = installRHELAddOnSoftware(programParentDir, cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The additional RPMs were not installed, since an attempt to add them was already made.')
                else:
                    addOnSoftwareInstalled = True
                    logger.info('There were no additional RPMs present for the post-upgrade.')
                if 'setTimezone' not in progressDict:
                    f.write('setTimezone\n')
                    errorMessage = setTimezone(programParentDir, cursesThread)
                    if len(errorMessage) > 0:
                        errorMessageList.append(errorMessage)
                else:
                    errorMessageList.append('The time zone was not set, since an attempt to set it was already made.')
                if 'checkNetworkConfiguration' not in progressDict and ('osRestorationArchiveExtracted' in progressDict or osRestorationArchiveExtracted):
                    f.write('checkNetworkConfiguration\n')
                    if (serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9') and osDistLevel == '11.4':
                        errorMessage = checkNetworkConfiguration(programParentDir, osDist, cursesThread, osDistLevel=osDistLevel)
                    else:
                        errorMessage = checkNetworkConfiguration(programParentDir, osDist, cursesThread)
                    if len(errorMessage) > 0:
                        errorMessageList.append(errorMessage)
                else:
                    errorMessageList.append('The network configuration was not checked; either because it was already checked or the OS restoration archive was not successfully extracted.')
                if not ((serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9') and osDistLevel == '11.4'):
                    if 'setHostname' not in progressDict:
                        f.write('setHostname\n')
                        errorMessage = setHostname(programParentDir, cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The host name was not set, since an attempt to set it was already made.')
                if osDist == 'SLES':
                    if 'updateNTPConf' not in progressDict:
                        f.write('updateNTPConf\n')
                        errorMessage = updateNTPConf(cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The ntp configuration was not updated, since an attempt to update it was already made.')
                    if 'configureSnapper' not in progressDict:
                        f.write('configureSnapper\n')
                        errorMessage = configureSnapper(osDistLevel, cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The snapper configuration was not updated, since an attempt to update it was already made.')
                if serverModel != 'Superdome':
                    if 'updateMultipathConf' not in progressDict:
                        f.write('updateMultipathConf\n')
                        errorMessage = updateMultipathConf(cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The multipath blacklist configuration was not updated, since an attempt to update it was already made.')
                if 'DL580' in serverModel or serverModel == 'Superdome':
                    if 'DL580' in serverModel:
                        if 'updateBIOS' not in progressDict and addOnSoftwareInstalled:
                            f.write('updateBIOS\n')
                            errorMessage = updateBIOS(programParentDir, cursesThread)
                            if len(errorMessage) > 0:
                                errorMessageList.append(errorMessage)
                        else:
                            errorMessageList.append('The BIOS was not updated; either because it was already updated or the additional RPMs failed to install.')
                        if os.path.isdir(programParentDir + '/addOnFileArchive'):
                            if 'installAddOnFiles' not in progressDict:
                                f.write('installAddOnFiles\n')
                                errorMessage = installAddOnFiles(programParentDir, upgradeResourceDict.copy(), osDist, cursesThread, processor=processor)
                                if len(errorMessage) > 0:
                                    errorMessageList.append(errorMessage)
                            else:
                                errorMessageList.append('The files from the add on files archive were not installed, since an attempt to add them was already made.')
                    if serverModel == 'Superdome':
                        if os.path.isdir(programParentDir + '/addOnFileArchive'):
                            if 'installAddOnFiles' not in progressDict:
                                f.write('installAddOnFiles\n')
                                errorMessage = installAddOnFiles(programParentDir, upgradeResourceDict.copy(), osDist, cursesThread, serverModel=serverModel)
                                if len(errorMessage) > 0:
                                    errorMessageList.append(errorMessage)
                            else:
                                errorMessageList.append('The files from the add on files archive were not installed, since an attempt to add them was already made.')
                        if osDist == 'SLES':
                            if 'updateKdump' not in progressDict:
                                f.write('updateKdump\n')
                                errorMessage = updateKdump(cursesThread)
                                if len(errorMessage) > 0:
                                    errorMessageList.append(errorMessage)
                            else:
                                errorMessageList.append('The update of kdump.service to address bug 1008170 was not performed, since an attempt to update the service was already made.')
                    if 'restoreHANAUserAccounts' not in progressDict:
                        f.write('restoreHANAUserAccounts\n')
                        errorMessage = restoreHANAUserAccounts(programParentDir, cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The SAP HANA user account data was not restored, since an attempt to restore the account data was already made.')
                    if 'restoreHANAPartitionData' not in progressDict:
                        f.write('restoreHANAPartitionData\n')
                        errorMessage, hanaPartitionsRestored = restoreHANAPartitionData(programParentDir, cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The SAP HANA parition data was not restored, since an attempt to restore the data was already made.')
                    if 'sapRestorationArchiveExtracted' not in progressDict and hanaPartitionsRestored:
                        f.write('sapRestorationArchiveExtracted\n')
                        errorMessage = extractSAPRestorationArchive(programParentDir, osDist, cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The SAP restoration archive was not extracted; either because it was already extracted or the SAP HANA partition data was not successfully restored.')
                    if not scaleUpSystem:
                        if 'prepareSAPHanaDirs' not in progressDict:
                            f.write('prepareSAPHanaDirs\n')
                            errorMessage = prepareSAPHanaDirs(programParentDir, cursesThread)
                            if len(errorMessage) > 0:
                                errorMessageList.append(errorMessage)
                        else:
                            errorMessageList.append('The /hana/data/SID and /hana/log/SID directories were not created; since an attempt to create them was already made.')
                if 'DL380p' in serverModel or 'DL360p' in serverModel:
                    if 'configureXinetd' not in progressDict:
                        f.write('configureXinetd\n')
                        errorMessage = configureXinetd(cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('xinetd was not configured; since an attempt to configure it was already made.')
                    if 'updateLvmConf' not in progressDict:
                        f.write('updateLvmConf\n')
                        errorMessage = updateLvmConf(cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('/etc/lvm.conf was not updated; since an attempt to enable it was already made.')
                    if 'updateNFSListeners' not in progressDict:
                        f.write('updateNFSListeners\n')
                        errorMessage = updateNFSListeners(cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append("The number of NFS listeners in '/opt/cmcluster/nfstoolkit/hananfs.sh' was not updated; since an attempt to update the number was already made.")
                    if 'createNFSMountPoint' not in progressDict:
                        f.write('createNFSMountPoint\n')
                        errorMessage = createNFSMountPoint(cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The hananfs mount point was not created; since an attempt to create it was already made.')
                    if 'buildDeadmanDriver' not in progressDict:
                        f.write('buildDeadmanDriver\n')
                        errorMessage = buildDeadmanDriver(cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('The deadman driver was not built and installed; since an attempt to build and install it was already made.')
                if serverModel == 'ProLiant DL320e Gen8 v2' or serverModel == 'ProLiant DL360 Gen9':
                    if 'configureServiceguardQS' not in progressDict:
                        f.write('configureServiceguardQS\n')
                        errorMessage = configureServiceguardQS(programParentDir, osDistLevel, cursesThread)
                        if len(errorMessage) > 0:
                            errorMessageList.append(errorMessage)
                    else:
                        errorMessageList.append('Serviceguard QS was not configured; since an attempt to configure it was already made.')
            except IOError as err:
                logger.error('Could not access ' + progressStatusFile + '.\n' + str(err))
                displayErrorMessage("Could not access '" + progressStatusFile + "'; fix the problem and try again.", cursesThread)

            f.close()
            if len(errorMessageList) > 0:
                cursesThread.insertMessage(['warning', "Restoration of the server's configuration has completed with the errors shown below; check the log file for additional information before continuing with the re-installation process:"])
                cursesThread.insertMessage(['warning', ''])
                for message in errorMessageList:
                    cursesThread.insertMessage(['warning', message])
                    cursesThread.insertMessage(['warning', ''])

            else:
                cursesThread.insertMessage(['informative', "Restoration of the server's configuration has completed; continue with the next step in the re-installation process."])
                cursesThread.insertMessage(['informative', ''])
            cursesThread.getUserInput(['informative', 'Press enter to exit the program.'])
            cursesThread.insertMessage(['informative', ''])
            while not cursesThread.isUserInputReady():
                time.sleep(0.1)

            exit(0)
        except Exception as err:
            cursesThread.join()
            logger.error('An unexpected error was encountered:\n' + traceback.format_exc())
            print RED + "An unexpected error was encountered; collect the application's log file and report the error back to the SAP HANA CoE DevOps team." + RESETCOLORS
            print RED + 'Error: ' + str(err) + RESETCOLORS
            exit(1)
        finally:
            cursesThread.join()

    return


main()