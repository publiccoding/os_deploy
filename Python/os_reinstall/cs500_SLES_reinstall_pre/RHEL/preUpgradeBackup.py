# Embedded file name: ./preUpgradeBackup.py
import re
import os
import shutil
import datetime
import logging
from modules.sapHANANodeSpec import getSapInitBackupList, getSAPUserLoginData, getHANAFstabData, getGlobalIniFiles, checkSAPHANA, getConrepFile
from modules.computeNode import getServerModel, getOSDistribution, getProcessorType, getHostname
from modules.upgradeMisc import checkDiskspace, createNetworkInformationFile, createBackup, stageAddOnRPMS, getMultipathConf, updateInstallCtrlFile, copyRepositoryTemplate, checkForMellanox
RED = '\x1b[31m'
PURPLE = '\x1b[35m'
GREEN = '\x1b[32m'
BOLD = '\x1b[1m'
RESETCOLORS = '\x1b[0m'

def backupPreparation(upgradeWorkingDir, programParentDir, osDist):
    logger = logging.getLogger('coeOSUpgradeLogger')
    ctrlFileImg = ''
    cs500HSWScaleOut = False
    getHostname(upgradeWorkingDir)
    serverModel = getServerModel()
    if not 'DL380' in serverModel:
        if not 'DL360' in serverModel:
            if not 'DL320' in serverModel:
                processor = getProcessorType()
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
                            upgradeResourceDict[key] = re.sub('\\s+', '', val)

            except IOError as err:
                logger.error("Unable to access the application's resource file 'upgradeResourceFile'.\n" + str(err))
                print RED + "Unable to access the application's resource file 'upgradeResourceFile'; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

            try:
                if 'DL380' in serverModel or 'DL360' in serverModel:
                    archiveBackup = re.split('\\s*,\\s*', upgradeResourceDict['osArchiveBackup']) + re.split('\\s*,\\s*', upgradeResourceDict['sglxArchiveBackup'])
                    if osDist == 'SLES':
                        restorationBackup = re.split('\\s*,\\s*', upgradeResourceDict['slesOSRestorationBackup']) + re.split('\\s*,\\s*', upgradeResourceDict['sglxRestorationBackup'])
                    else:
                        restorationBackup = re.split('\\s*,\\s*', upgradeResourceDict['rhelOSRestorationBackup']) + re.split('\\s*,\\s*', upgradeResourceDict['sglxRestorationBackup'])
                elif 'DL320' in serverModel:
                    pass
                else:
                    archiveBackup = re.split('\\s*,\\s*', upgradeResourceDict['osArchiveBackup'])
                    if osDist == 'SLES':
                        restorationBackup = re.split('\\s*,\\s*', upgradeResourceDict['slesOSRestorationBackup'])
                        sapRestorationBackup = re.split('\\s*,\\s*', upgradeResourceDict['sapRestorationBackup'])
                        if 'DL580' in serverModel:
                            if processor == 'ivybridge':
                                addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['ivyBridgeSLESAddOnFileArchive']
                            else:
                                addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['haswellSLESAddOnFileArchive']
                        elif serverModel == 'Superdome':
                            addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['cs900SLESAddOnFileArchive']
                    else:
                        restorationBackup = re.split('\\s*,\\s*', upgradeResourceDict['rhelOSRestorationBackup'])
                        sapRestorationBackup = re.split('\\s*,\\s*', upgradeResourceDict['sapRestorationBackup'])
                        if 'DL580' in serverModel:
                            if processor == 'ivybridge':
                                addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['ivyBridgeRHELAddOnFileArchive']
                            else:
                                addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['haswellRHELAddOnFileArchive']
                        elif serverModel == 'Superdome':
                            addOnFileArchive = programParentDir + '/addOnFileArchives/' + upgradeResourceDict['cs900RHELAddOnFileArchive']
                    fstabHANAEntries = upgradeResourceDict['fstabHANAEntries'].split(',')
            except KeyError as err:
                logger.error('The resource key ' + str(err) + " was not present in the application's resource file.")
                print RED + 'The resource key ' + str(err) + " was not present in the application's resource file; fix the problem and try again; exiting program execution." + RESETCOLORS
                exit(1)

            stageAddOnRPMS(programParentDir, upgradeWorkingDir, serverModel, osDist)
            if osDist == 'RHEL':
                copyRepositoryTemplate(programParentDir, upgradeWorkingDir)
            if not 'DL380' in serverModel:
                if not 'DL320' in serverModel:
                    if not 'DL360' in serverModel:
                        if 'DL580' in serverModel or serverModel == 'Superdome':
                            addOnFileArchiveDir = upgradeWorkingDir + '/addOnFileArchive'
                            try:
                                os.mkdir(addOnFileArchiveDir)
                                shutil.copy2(addOnFileArchive, addOnFileArchiveDir)
                            except (OSError, OIError) as err:
                                logger.error("Unable to copy the add on files archive '" + addOnFileArchive + "' to '" + addOnFileArchiveDir + "'.\n" + str(err))
                                print RED + "Unable to copy the add on files archive '" + addOnFileArchive + "' to '" + addOnFileArchiveDir + "'; fix the problem and try again; exiting program execution." + RESETCOLORS
                                exit(1)

                        hanaSharedWithSID = getHANAFstabData(upgradeWorkingDir, fstabHANAEntries, serverModel, processor)
                        sidList, tenantUserDict = checkSAPHANA(upgradeWorkingDir, hanaSharedWithSID, serverModel)
                        if len(tenantUserDict) != 0:
                            homeDirList = getSAPUserLoginData(upgradeWorkingDir, sidList, tenantUserDict=tenantUserDict)
                        else:
                            homeDirList = getSAPUserLoginData(upgradeWorkingDir, sidList)
                        restorationBackup += homeDirList
                        restorationBackup += getSapInitBackupList()
                        multipathConfList, fibrePresent = getMultipathConf()
                        if len(multipathConfList) > 0:
                            restorationBackup += multipathConfList
                        if 'DL580' in serverModel:
                            conrepDir = upgradeWorkingDir + '/conrepFile'
                            getConrepFile(programParentDir, conrepDir, processor)
                        if serverModel == 'Superdome' and osDist == 'SLES':
                            ctrlFileImg = updateInstallCtrlFile(programParentDir, upgradeWorkingDir, processor)
                        ctrlFileImg = 'DL580' in serverModel and processor == 'haswell' and fibrePresent and updateInstallCtrlFile(programParentDir, upgradeWorkingDir, processor, cs500ScaleOut='cs500ScaleOut')
                        cs500HSWScaleOut = True
                backupItems = 'DL380' in serverModel or 'DL320' in serverModel or 'DL360' in serverModel or ' '.join(restorationBackup) + ' ' + ' '.join(archiveBackup) + ' ' + ' '.join(sapRestorationBackup)
                backupItems = [restorationBackup, sapRestorationBackup, archiveBackup]
            else:
                backupItems = ' '.join(restorationBackup) + ' ' + ' '.join(archiveBackup)
                backupItems = [restorationBackup, archiveBackup]
            checkDiskspace(backupItems)
            createNetworkInformationFile(upgradeWorkingDir, osDist)
            'DL580' in serverModel and 'Gen9' in serverModel and checkForMellanox(programParentDir, upgradeWorkingDir, osDist)
        return 'DL380' in serverModel or 'DL320' in serverModel or 'DL360' in serverModel or ([restorationBackup, archiveBackup, sapRestorationBackup],
         serverModel,
         ctrlFileImg,
         cs500HSWScaleOut)
    else:
        return ([restorationBackup, archiveBackup],
         serverModel,
         ctrlFileImg,
         cs500HSWScaleOut)


def main():
    programVersion = '2017.05-rc11'
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS
        exit(1)
    try:
        programParentDir = ''
        cwd = os.getcwd()
        programDir = os.path.dirname(os.path.realpath(__file__))
        programParentDir = '/'.join(programDir.split('/')[:-1])
        if cwd != programParentDir:
            os.chdir(programParentDir)
    except OSError as err:
        print RED + "Unable to change into the programs parent directory '" + programParentDir + "'; fix the problem and try again; exiting program execution.\n" + str(err) + RESETCOLORS
        exit(1)

    osDist = getOSDistribution()
    dateTimestamp = datetime.datetime.now().strftime('%d%H%M%b%Y')
    upgradeWorkingDir = '/tmp/CoE_SAP_HANA_' + osDist + '_Upgrade_Working_Dir_' + dateTimestamp
    if not os.path.exists(upgradeWorkingDir):
        try:
            if osDist == 'SLES':
                postUpgradeScriptDir = programParentDir + '/postUpgradeScriptFiles/SLES'
            else:
                postUpgradeScriptDir = programParentDir + '/postUpgradeScriptFiles/RHEL'
            shutil.copytree(postUpgradeScriptDir, upgradeWorkingDir)
        except OSError as err:
            print RED + "Unable to copy the post-upgrade script files from '" + postUpgradeScriptDir + "' to '" + upgradeWorkingDir + "/postUpgradeScriptFiles'; fix the problem and try again; exiting program execution." + RESETCOLORS
            exit(1)

    logDir = upgradeWorkingDir + '/log'
    if not os.path.isdir(logDir):
        try:
            os.mkdir(logDir)
        except OSError as err:
            print RED + "Unable to create the pre-upgrade log directory '" + logDir + "'; fix the problem and try again; exiting program execution.\n" + str(err) + RESETCOLORS
            exit(1)

    logFile = logDir + '/' + osDist + '_Pre-Upgrade_' + dateTimestamp + '.log'
    handler = logging.FileHandler(logFile)
    logger = logging.getLogger('coeOSUpgradeLogger')
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("The program's version is: " + programVersion + '.')
    backupList, serverModel, ctrlFileImg, cs500HSWScaleOut = backupPreparation(upgradeWorkingDir, programParentDir, osDist)
    backupISO, archiveImage = createBackup(backupList, upgradeWorkingDir, osDist)
    if 'Superdome' in serverModel:
        print not 'SLES' in osDist and not cs500HSWScaleOut and GREEN + 'The pre-upgrade backup successfully completed.\n\nSave the following files and their md5sum files if applicable to another system:\n\t- ' + backupISO + '\n\t- ' + archiveImage + BOLD + PURPLE + '\n\n**** Finally, make sure to copy the files in binary format to avoid corrupting the files; you should also double check the files and their contents before continuing with the upgrade. ****' + RESETCOLORS
    else:
        print GREEN + 'The pre-upgrade backup successfully completed.\n\nSave the following files and their md5sum if applicable to another system:\n\t- ' + backupISO + '\n\t- ' + archiveImage + '\n\t- ' + ctrlFileImg + BOLD + PURPLE + '\n\n**** Finally, make sure to copy the files in binary format to avoid corrupting the files; you should also double check the files and their contents before continuing with the upgrade. ****' + RESETCOLORS


main()