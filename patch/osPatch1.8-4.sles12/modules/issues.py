# Embedded file name: ./issues.py
import subprocess
import logging
import re
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