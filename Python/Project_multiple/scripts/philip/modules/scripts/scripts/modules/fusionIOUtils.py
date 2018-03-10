import subprocess
import logging
import re


'''
This function is used to remove FusionIO packages before they are updated.
The 'type' argument is either 'software' or 'drivers' and the kwargs is 
the kernel version, which will be used for removing FusionIO packages
that have the kernel version in the name.
'''
def removeFusionIOPackages(packageList, type, computeNodeLogger, **kwargs):
	logger = logging.getLogger(computeNodeLogger)

	kernel = ''

	if 'kernel' in kwargs:
		kernel = kwargs['kernel']

	removalStatus = True

	logger.info("Removing FusionIO " + type + " packages.")

	packageList = re.sub('\s+', '', packageList)

	fusionIOPackageList = packageList.split(',')

	packageRemovalList = []

	#Before trying to remove a package we need to see if it is present.
	for package in fusionIOPackageList:
		command = "rpm -qa " + package
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        	out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to get the currently installed FusionIO " + package + " package was: " + out.strip())

	        if result.returncode != 0:
			logger.error("Failed to verify if the " + type + " package '" + package + "' was installed.\n" + err)
			continue
		else:
			#Using extend in case more then one package was returned.
                	packageRemovalList.extend(out.splitlines())

	#Now remove any of the packages that were present. This should almost always have a length greater than zero.
	if len(packageRemovalList) > 0:
		packages = " ".join(packageRemovalList)

		command = "rpm -e " + packages

		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		logger.debug("The output of the command (" + command + ") used to remove the currently installed FusionIO package(s) was: " + out.strip())

		if result.returncode != 0:
			logger.error("Problems were encountered while trying to remove the FusionIO " + type + " packages.\n" + err)
			removalStatus = False

	logger.info("Done removing FusionIO " + type + " packages.")

	return removalStatus

#End removeFusionIOPackages(packageList, type, **kwargs):


'''
This function is used to check if the FusionIO firmware is at a supported level for 
an automatic upgrade.
'''
def checkFusionIOFirmwareUpgradeSupport(fusionIOFirmwareVersionList, loggerName):
        logger = logging.getLogger(loggerName)

	automaticUpgrade = True

        logger.info("Checking to see if the FusionIO firmware is at a supported version for an automatic upgrade.")

	command = "fio-status"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	logger.debug("The output of the command (" + command + ") used to get the FusionIO firmware information was: " + out.strip())

	if result.returncode != 0:
		logger.error("Failed to get the FusionIO status information needed to determine the FusionIO firmware version information.\n" + err)
		automaticUpgrade = False
	else:
		fioStatusList = out.splitlines()

		for line in fioStatusList:
			line = line.strip()

			if "Firmware" in line:
				firmwareVersion = re.match("Firmware\s+(v.*),", line).group(1)

				logger.debug("The ioDIMM firmware version was determined to be: " + firmwareVersion  + ".")

				if firmwareVersion not in fusionIOFirmwareVersionList:
					logger.error("The fusionIO firmware is not at a supported version for an automatic upgrade.")
					automaticUpgrade = False
					break
			else:
				continue

        logger.info("Done checking to see if the FusionIO firmware is at a supported level for an automatic upgrade.")

	return automaticUpgrade

#End checkFusionIOFirmwareUpgradeSupport(fusionIOFirmwareVersionList):
