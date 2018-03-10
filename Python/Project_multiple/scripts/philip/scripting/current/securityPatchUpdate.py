#!/usr/bin/python


import logging
import os
import optparse
import subprocess
import signal
from modules.spUtils import RED, GREEN, RESETCOLORS, signal_handler
from modules.configureRepository import configureRepositories
from modules.updateZyppConf import updateZyppConf
from modules.applyPatches import applyPatches

'''
It is expected that whether OS patches are being installed or kernel patches are being installed that the 
directory structure to them is as follows:
/hp/support/securityPatches/OSDistLevel/kernelSecurityRPMs/
/hp/support/securityPatches/OSDistLevel/OSSecurityRPMs/

For example,

SLES
/hp/support/securityPatches/SLES_SP3/kernelSecurityRPMs/
/hp/support/securityPatches/SLES_SP3/OSSecurityRPMs/

RHEL
/hp/support/securityPatches/RHEL_Release_6.6/kernelSecurityRPMs/
/hp/support/securityPatches/RHEL_Release_6.6/OSSecurityRPMs/
'''	

'''
This function is used to initialize the program.  It performs the following:
	1.  Ensures that the program is being ran as root.
	2.  Removes any old log files if they exist.  This would occur if the program has already been ran previously.
	3.  Sets up logging.
	4.  Ensures that the patches being installed are for the correct current OS that is installed.
	5.  Calls a function to update /etc/zypp/zypp.conf.
	6.  Calls a function to set up the repositories.
	7.  Returns "patchDirList" which has the list of patch repositories to use for the update, e.g. kernelSecurityRPMs, OSSecurityRPMs or both.
'''
def init():
	applicationLogFile = '/hp/support/log/securityPatchLog.log'
	zyppConfUpdateLogFile = '/hp/support/log/zyppConfUpdateLog.log'
	securityPatchBaseDir = '/hp/support/securityPatches'

	#The program can only be ran by root.
	if os.geteuid() != 0:
		print RED + "You must be root to run this program." + RESETCOLORS
		exit(1)

	usage = 'usage: %prog [[-a] [-k] [-o] -d] [-h]'

	parser = optparse.OptionParser(usage=usage)

        parser.add_option('-a', action='store_true', default=False, help='This option will result in the application of both OS and Kernel security patches.')
	parser.add_option('-d', action='store_true', default=False, help='This option is used when problems are encountered and additional debug information is needed.')
        parser.add_option('-k', action='store_true', default=False, help='This option will result in the application of Kernel security patches.')
        parser.add_option('-o', action='store_true', default=False, help='This option will result in the application of OS security patches.')

	(options, args) = parser.parse_args()

	if (options.a and options.k) or (options.a and options.o) or (options.k and options.o):
		parser.error("Options -a, -k, and -o are mutually exclusive.")

	if not options.a and not options.k and not options.o:
		parser.error("At least one of the following options is required: -a, -k, or -o.")

	#Always start with a new log file.
	try:
		if os.path.isfile(applicationLogFile):
			os.remove(applicationLogFile)
		else:
			open(applicationLogFile, 'w').close()
	except IOError:
		print RED + "Unable to access " + applicationLogFile + " for writing.\n" + RESETCOLORS
		exit(1)

	#Configure logging.
	handler = logging.FileHandler(applicationLogFile)

	logger = logging.getLogger("securityPatchLogger")

	if options.d:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)

	formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	#Check to see what OS is installed. If it is not SLES then it must be RHEL.
	command = "cat /proc/version|grep -i suse"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		logger.error("Unable to get system OS type.\n" + err + "\n; exiting program execution.")
		print RED + "Unable to get system OS type; check log file for errors." + RESETCOLORS
		exit(1)
		
	if result.returncode == 0:
		OSDist = 'SLES'
		command = "cat /etc/SuSE-release | grep PATCHLEVEL|awk '{print $3}'"
	else:
		OSDist = 'RHEL'
		command = "cat /etc/redhat-release | egrep -o \"[1-9]{1}\.[0-9]{1}\""

	#Get the current OS SP/Release level.
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		logger.error("Unable to get OS distribution level.\n" + err + "\n; exiting program execution.")
		print RED + "Unable to get OS distribution level; check log file for errors." + RESETCOLORS
		exit(1)
	else:
                if OSDist == 'SLES':
                        OSDistLevel = OSDist + '_SP' + out.strip()
                else:
                        OSDistLevel = OSDist + '_Release_' + out.strip()
	
	#By default we strip off a trailing '/' to avoid an issue where the path to "securityPatchBaseDir" had a trailing '/' added to it.
	securityPatchDir = securityPatchBaseDir.rstrip('/') + '/' + OSDistLevel

	#Check that the security patch directory exists for the current OS.
	if not os.path.exists(securityPatchDir):
		logger.error("This is not a " + OSDistLevel + " installed system or the patch directory (" + securityPatchDir +") is missing; exiting program execution.")
		print RED + "This is not a " + OSDistLevel + " installed system or the patch directory (" + securityPatchDir +") is missing; exiting program execution.\n" + RESETCOLORS
		exit(1)

	#Depending on the option selected we now check for the specific patch directory (OS, Kernel or both).
	kernelDir = securityPatchDir + '/kernelSecurityRPMs'
	osDir = securityPatchDir + '/OSSecurityRPMs'

	if options.a:
		if not (os.path.exists(kernelDir) and os.path.exists(osDir)):
			logger.error("Option -a was selected, however, both of the OS and kernel security patch directories (" + kernelDir + ", " + osDir + ") are not present; exiting program execution.")
			print RED + "Option -a was selected, however, both of the OS and kernel security patch directories (" + kernelDir + ", " + osDir + ") are not present; exiting program execution.\n" + RESETCOLORS
			exit(1)
		else:
			patchDirList = ['kernelSecurityRPMs', 'OSSecurityRPMs']
	elif options.k:
		if not os.path.exists(kernelDir):
			logger.error("Option -k was selected, however, the kernel security patch directory (" + kernelDir + ") is not present; exiting program execution.")
			print RED + "Option -k was selected, however, the kernel security patch directory (" + kernelDir + ") is not present; exiting program execution.\n" + RESETCOLORS
			exit(1)
		else:
			patchDirList = ['kernelSecurityRPMs']
	else:
		if not os.path.exists(osDir):
			logger.error("Option -o was selected, however, the OS security patch directory (" + osDir + ") is not present; exiting program execution.")
			print RED + "Option -o was selected, however, the OS security patch directory (" + osDir + ") is not present; exiting program execution.\n" + RESETCOLORS
			exit(1)
		else:
			patchDirList = ['OSSecurityRPMs']

	#Configure the necessary patch repositories.
        if configureRepositories(securityPatchDir, patchDirList):
                logger.info("Successfully configured security patch repositories.")
        else:
                logger.error("Unable to configure security patch repositories; exiting program execution.")
                print RED + "Unable to configure security patch repositories; check log file for errors." + RESETCOLORS
		exit(1)

	'''
	Update zypp.conf so that the current kernel and the new kernel are both installed.
	This way the current kernel is available as a fallback in case issues arise with the new kernel.
	'''
        if updateZyppConf(zyppConfUpdateLogFile):
                logger.info("Successfully updated /etc/zypp/zypp.conf.")
        else:
                logger.error("Unable to update /etc/zypp/zypp.conf; exiting program execution.")
                print RED + "Unable to update /etc/zypp/zypp.conf; check log files for errors." + RESETCOLORS
		exit(1)

	return patchDirList
#End init()

def main():
	logger = logging.getLogger("securityPatchLogger")

	print "Phase 1: Initializing for system update."
	patchDirList = init()

	#Set traps so that the patch update is not interrupted by the user without first giving them a chance to continue.
	signal.signal(signal.SIGINT, signal_handler)
	signal.signal(signal.SIGQUIT, signal_handler)

	print "Phase 2: Updating system with security patches."
	updateStatus = applyPatches(patchDirList)

	if updateStatus == '':
		logger.info("The system was successfully updated.  Before rebooting verify the bootloader is properly configured.")
		print GREEN + "The system was successfully updated.  Before rebooting verify the bootloader is properly configured." + RESETCOLORS
	else:
		if 'kernelSecurityRPMs' in updateStatus and 'OSSecurityRPMs' in updateStatus:
			logger.error("The " + updateStatus + " repositories were unsuccessfully updated; Before rebooting check the log files for errors and that the bootloader is properly configured.  If necessary rerun the update.")
			print RED + "The " + updateStatus + " repositories were unsuccessfully updated; Before rebooting check the log files for errors and that the bootloader is properly configured.  If necessary rerun the update." + RESETCOLORS
		elif 'kernelSecurityRPMs' in updateStatus:
			logger.error("The " + updateStatus + " repository was unsuccessfully updated; Before rebooting check the log files for errors and that the bootloader is properly configured.  If necessary rerun the update.")
			print RED + "The " + updateStatus + " repository was unsuccessfully updated; Before rebooting check the log files for errors and that the bootloader is properly configured.  If necessary rerun the update." + RESETCOLORS
		else:
			logger.error("The " + updateStatus + " repository was unsuccessfully updated; Before rebooting check the log files for errors.  If necessary rerun the update.")
			print RED + "The " + updateStatus + " repository was unsuccessfully updated; Before rebooting check the log files for errors.  If necessary rerun the update." + RESETCOLORS
#End main()

#####################################################################################################
# Main program starts here.
#####################################################################################################

main()
