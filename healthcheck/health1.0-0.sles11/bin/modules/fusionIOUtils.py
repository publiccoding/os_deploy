# Embedded file name: /hp/support/health/bin/modules/fusionIOUtils.py
import subprocess
import logging
import re

def checkFusionIOFirmwareUpgradeSupport(fusionIOFirmwareVersionList, loggerName):
    logger = logging.getLogger(loggerName)
    automaticUpgrade = True
    logger.info('Checking to see if the FusionIO firmware is at a supported version for an automatic upgrade.')
    command = 'fio-status'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    logger.debug('The output of the command (' + command + ') used to get the FusionIO firmware information was: ' + out.strip())
    if result.returncode != 0:
        logger.error('Failed to get the FusionIO status information needed to determine the FusionIO firmware version information.\n' + err)
        automaticUpgrade = False
    else:
        fioStatusList = out.splitlines()
        for line in fioStatusList:
            line = line.strip()
            if 'Firmware' in line:
                firmwareVersion = re.match('Firmware\\s+(v.*),', line).group(1)
                logger.debug('The ioDIMM firmware version was determined to be: ' + firmwareVersion + '.')
                if firmwareVersion not in fusionIOFirmwareVersionList:
                    logger.error('The fusionIO firmware is not at a supported version for an automatic upgrade.')
                    automaticUpgrade = False
                    break
            else:
                continue

    logger.info('Done checking to see if the FusionIO firmware is at a supported level for an automatic upgrade.')
    return automaticUpgrade