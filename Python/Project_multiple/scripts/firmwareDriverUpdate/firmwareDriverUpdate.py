#!/usr/bin/python

import logging
import os
import fnmatch
import optparse
import subprocess
import time
import socket
import re
import signal
import computeNode
import csurUtils
import csurUpdate


def init():

	#The program can only be ran by root.
	if os.geteuid() != 0:
		print csurUtils.RED + "You must be root to run this program." + csurUtils.RESETCOLORS
		exit(1)

	usage = 'usage: %prog [-c CSUR_DIRECTORY -l LOG_FILENAME [-d]]'

	parser = optparse.OptionParser(usage=usage)

	parser.add_option('-d', action='store_true', default=False, help='This option is used to collect debug information.', metavar=' ')
	parser.add_option('-c', action='store', help='This option is mandatory and requires its argument to be the directory hosting the CSURs.', metavar='DIRECTORY')
	parser.add_option('-l', action='store', help='This option is mandatory and requires its argument to be the directory where the applications log file will be saved.', metavar='DIRECTORY')

	(options, args) = parser.parse_args()

	if not options.c or not options.l:
		parser.print_help()
		exit(1)
	else:
		#Remove trailing slash if it was provided.
		csurBaseDirectory = (options.c).rstrip('/')

		logFile = (options.l).rstrip('/') + '/firmwareDriverUpdate.log'

	#Always start with a new log file.
	try:
		if os.path.isfile(logFile):
			os.remove(logFile)
		else:
			open(logFile, 'w').close()
	except IOError:
		print csurUtils.RED + "Unable to access " + logFile + " for writing.\n" + csurUtils.RESETCOLORS
		exit(1)

	handler = logging.FileHandler(logFile)

	if options.d:
		logger.setLevel(logging.DEBUG)
	else:
		logger.setLevel(logging.INFO)

	formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
	handler.setFormatter(formatter)
	logger.addHandler(handler)

	#Need OS distribution level which is needed to determine driver information.
	command = "cat /proc/version|grep -i suse"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		logger.error("Unable to get system OS type.\n" + err + "\n; exiting program execution.")
		print csurUtils.RED + "Unable to get system OS type.\n" + err + csurUtils.RESETCOLORS
		exit(1)
		
	if result.returncode == 0:
		OSDist = 'SLES'
		command = "cat /etc/SuSE-release | grep PATCHLEVEL|awk '{print $3}'"
	else:
		OSDist = 'RHEL'
		command = "cat /etc/redhat-release | egrep -o \"[1-9]{1}\.[0-9]{1}\""

	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		logger.error("Unable to get OS distribution level.\n" + err + "\n; exiting program execution.")
		print csurUtils.RED + "Unable to get OS distribution level.\n" + err + csurUtils.RESETCOLORS
		exit(1)
	else:
		if OSDist == 'SLES':
			OSDistLevel = OSDist + 'SP' + out.strip()
		else:
			OSDistLevel = OSDist +  out.strip()

	#Get system model.
	command = "dmidecode -s system-product-name|awk '{print $2$3}'"
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if err != '':
		logger.error("Unable to get system model.\n" + err + "\n; exiting program execution.")
		print csurUtils.RED + "Unable to get system model.\n" + err + csurUtils.RESETCOLORS
		exit(1)
		
	systemModel = out.strip()	

	if systemModel == 'DL580Gen8':
		generation = 'CS500IB'

	csurDirectory = csurBaseDirectory + '/' + generation + '/'

	try:
		for file in os.listdir(csurDirectory):
			if fnmatch.fnmatch(file, generation + '*CSUR*'):
				csurDataFile = csurDirectory + file
				break
	except OSError as e:
		logger.error("Errors were encountered while looking for the csurDataFile in " + csurDirectory + ";Error: " + str(e) + "; exiting program execution.")
		print csurUtils.RED + "Errors were encountered while looking for the csurDataFile in " + csurDirectory + ";Error: " + str(e) + "\n" + csurUtils.RESETCOLORS
		exit(1)

	#Need to make sure the correct CSUR directory was provided.
	command = "egrep \"^" + OSDistLevel + "-.*" + systemModel + "\" "  + csurDataFile
	result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	out, err = result.communicate()

	if result.returncode != 0:
		logger.error("The wrong CSUR directory (" + csurDirectory + ") was provided for this system (" + systemModel + "); exiting program execution.")
		print csurUtils.RED + "The wrong CSUR directory (" + csurDirectory + ") was provided for this system (" + systemModel + ")" + csurUtils.RESETCOLORS
		exit(1)

	try:
		fh = open(csurDataFile)
		csurData = fh.readlines()
	except IOError:	
		logger.error("Unable to open " + csurDataFile + " for reading; exiting program execution.")
		print csurUtils.RED + "Unable to open " + csurDataFile + " for reading.\n" + csurUtils.RESETCOLORS
		exit(1)

	fh.close()

	return csurDirectory, csurData, OSDistLevel, systemModel
#End init()


'''
Once the update begins we do not want it interrupted as this could result in a system
being in an unknown state.
'''
def signal_handler(signum, frame):
	regex = r"^(y|n)$"

	print csurUtils.RED + "\nThe update should not be interrupted once started, since it could put the system in an unknown state.\n" + csurUtils.RESETCOLORS

	while True:
		response = raw_input("Do you really want to interrupt the update [y|n]: ")
		
		if not re.match(regex, response):
			print "A valid response is y|n.  Please try again."
			continue
		elif(response == 'y'):
			exit(1)
		else:
			return
#End signal_handler(signum, frame):


def firmware_signal_handler(signum, frame):
	print csurUtils.RED + "\nThe firmware update should not be interrupted once started, since it could put the system in an unknown state.\nIf you really want to interrupt the firmware update process then you will have to kill it.\n" + csurUtils.RESETCOLORS
#End firmware_signal_handler(signum, frame):
		
	
#####################################################################################################
# Main program starts here.
#####################################################################################################
logger = logging.getLogger("firmwareDriverLogger")

firmwareToUpdate = []

csurDirectory, csurData, OSDistLevel, systemModel = init()

#For now this is only written for CS500.  Will update as needed.
if systemModel == 'DL580Gen8':
	computeNode = computeNode.DL580Gen8ComputeNode(systemModel, OSDistLevel)
else:
	logger.error("Model " + systemModel + " is not a supported system type; exiting program execution.")
	print "Model " + systemModel + " is not a supported system type."
	exit(1)

firmwareDict = computeNode.getFirmwareDict(csurData[:])

logger.info("Phase 1: Initializing system update.")

#---------------------------------------------------------------------------------------
#Get firmware inventory. We always get storage firmware first for data file formatting purposes.
computeNode.getStorageFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)
computeNode.getNICFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)
computeNode.getCommonFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)
computeNode.getComputeNodeSpecificFirmwareInventory(firmwareDict.copy(), firmwareToUpdate)

if computeNode.getFirmwareStatus():
	logger.error("There were problems getting firmware information; exiting program execution.")
	print "\n" + csurUtils.RED + "There were problems getting firmware information.\nCheck log file for addtional information.\n" + csurUtils.RESETCOLORS
	exit(1)

#---------------------------------------------------------------------------------------
#Get driver inventory.
driversToUpdate = computeNode.getDriverInventory(csurData[:])

if computeNode.getDriverStatus():
	logger.error("There were problems getting driver information; exiting program execution.")
	print "\n" + csurUtils.RED + "There were problems getting driver information.\nCheck log file for addtional information.\n" + csurUtils.RESETCOLORS
	exit(1)

#---------------------------------------------------------------------------------------
#Get software inventory from CSUR file.
softwareToUpdate = computeNode.getSoftwareInventory(csurData[:])

if computeNode.getSoftwareStatus():
	logger.error("There were problems getting software information; exiting program execution.")
	print "\n" + csurUtils.RED + "There were problems getting software information.\nCheck log file for addtional information.\n" + csurUtils.RESETCOLORS
	exit(1)

#---------------------------------------------------------------------------------------
#Beginning of update section.

#Set traps so that the software and driver update is not interrupted by the user without first giving them a chance to continue.
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGQUIT, signal_handler)

#Instantiate the computeNode update class.
computeNodeUpdate = csurUpdate.ComputeNodeUpdate(csurDirectory)

#Update software.
if len(softwareToUpdate) != 0:
	logger.info("Phase 2: Updating software.")
	updateDict = csurUtils.getPackageDict(softwareToUpdate[:], csurData[:], 'Software', OSDistLevel, systemModel)
	
	computeNodeUpdate.updateSoftware(softwareToUpdate[:], updateDict.copy(), OSDistLevel)
else:
	logger.info("Phase 2: There was no software that needed to be updated.")

#A 5 second delay between phases to give one a chance to read the screen in case it scrolls off.
time.sleep(5)
#Update drivers.
if len(driversToUpdate) != 0:
	logger.info("Phase 3: Updating drivers.")
	updateDict = csurUtils.getPackageDict(driversToUpdate[:], csurData[:], 'Drivers', OSDistLevel, systemModel)	

	computeNodeUpdate.updateDrivers(updateDict.copy(), OSDistLevel, systemModel)
else:
	logger.info("Phase 3: There were no drivers that needed to be updated.")

time.sleep(5)

#Set traps so that the firmware update is not interrupted by the user.
signal.signal(signal.SIGINT, firmware_signal_handler)
signal.signal(signal.SIGQUIT, firmware_signal_handler)

#Update firmware.
if len(firmwareToUpdate) != 0:
	logger.info("Phase 4: Updating firmware.")
	updateDict = csurUtils.getPackageDict(firmwareToUpdate[:], csurData[:], 'Firmware')	
else:
	logger.info("Phase 4: There was no firmware that needed to be updated.")

#Shutdown system once update is completed.
logger.info("Phase 5: Server update complete, shutting down server now.")
os.system("shutdown -h now")


