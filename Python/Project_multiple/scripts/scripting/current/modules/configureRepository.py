#!/usr/bin/python

import spUtils
import subprocess
import logging
import os


'''
This function is used to setup security patch repositories.
The function returns True on success and False on a failure, at which time the log
should be consulted.
'''
def configureRepositories(securityPatchDir, patchDirList):
	
	logger = logging.getLogger("securityPatchLogger")

	logger.info('Configuring security patch repositories.')

	'''
	If a repository already exists then we remove and recreate it in case it has a different configuration.
	Otherwise, if the repository does not already exist it will be created.
	'''	
	for dir in patchDirList:
		#The result from this command is used to determine if a repository exists.
		command = 'zypper lr ' + dir
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		#The returncode is 0 if the repository is succussfully identified.
		if result.returncode == 0:
			logger.info("Removing repository " + dir + ", since it was present.")
			command = "zypper rr " + dir
			result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
			out, err = result.communicate()

			if result.returncode != 0:
				logger.error(err)
				logger.error("stdout = " + out)
				logger.error("Repository " + dir + ", could not be removed.")
				logger.debug("Command used to remove the repository was (" + command + ").")
				return False
			else:
				logger.info("Repository " + dir + ", was successfully removed.")
		elif "Repository '" + dir + "' not found by its alias" in err:
			logger.info("Repository " + dir + ", was not found to be present.")
		else:
			logger.error(err)
			logger.error("stdout = " + out)
			logger.error("Unable to get repository information using command " + command)
			logger.debug("Command used to get the repository information was (" + command + ").")
			return False

		#Create repository.
		patchDir = securityPatchDir + '/' + dir
		logger.info("Adding repository " + dir + ".")
		command = "zypper ar -t plaindir " + patchDir + " " + dir
		result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		out, err = result.communicate()

		if result.returncode != 0:
			logger.error(err)
			logger.error("stdout = " + out)
			logger.error("Repository " + dir + ", was unsuccessfully added.")
			logger.debug("Command used to add repository was (" + command + ").")
			return False
		else:
			logger.info("Repository " + dir + ", was successfully added.")

	logger.info('Done configuring security patch repositories.')

	return True
#End configureRepositories(securityPatchDir):


'''
#This section is for running the module standalone for debugging purposes.  Uncomment to use.
if __name__ == '__main__':

	#Setup logging.
	logger = logging.getLogger()
	logFile = 'configureRepositories.log'

        try:
                open(logFile, 'w').close()
        except IOError:
                print spUtils.RED + "Unable to access " + logFile + " for writing." + spUtils.RESETCOLORS
                exit(1)

        handler = logging.FileHandler(logFile)

	logger.setLevel(logging.INFO)
	handler.setLevel(logging.INFO)

        formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

	if configureRepositories("/hp/support/securityPatches"):
                print spUtils.GREEN + "Successfully configured security patch repositories" + spUtils.RESETCOLORS
	else:
                print spUtils.RED + "Unable to configure security patch repositories; check log file for errors." + spUtils.RESETCOLORS
'''
