#!/usr/bin/python

import re
import shutil
import os
import sys
import subprocess


RED = '\033[31m'
GREEN = '\033[32m'
RESETCOLORS = '\033[0m'

#This is the base path for the csur directory.
csurDir = '/hp/support/csur'

#The program can only be ran by root.
if os.geteuid() != 0:
	print RED + "You must be root to run this program." + RESETCOLORS
	exit(1)

'''
Delete the current csur bundle directory contents, except for the bin directory, so that we start clean.
Also, we want to delete the csur bundle directories that may of been left behind so that they do not contribute
to the root file system's usage check.
'''
if os.path.exists(csurDir):
        dirs = os.listdir(csurDir)

        for dir in dirs:
		#We do not want to delete the bin directory hosting the csur bundle application.
                if dir == 'bin':
                        continue
                else:
			dir = csurDir + '/' + dir

                        try:
                                shutil.rmtree(dir)
                        except IOError as err:
                                print RED + "Unable to delete the current csur bundle related directory (" + dir + "); fix the problem and try again.\n" + str(err) + RESETCOLORS
                                exit(1)

#Get the root file system's usage.  There must be at least 10GB free in order to do the csur update.
command = "df /"
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
	print RED + "Unable to check the available disk space of the root file system; fix the problem and try again.\n" + err + RESETCOLORS
	exit(1)

out = out.strip()

tmpVar = re.match('(.*\s+){3}([0-9]+)\s+', out).group(2)

availableDiskSpace = round(float(tmpVar)/float(1024*1024), 2)

if not availableDiskSpace >= 1:
	print RED + "There is not enough disk space (" + str(availableDiskSpace) + "GB) on the root file system; There needs to be at least 10GB of free space on the root file system; fix the problem and try again." + RESETCOLORS
	exit(1)

#Get the location of where the archive was extracted to, so that we can add it to the archive image name.
executableFullPath = os.path.abspath(sys.argv[0])
executableName = os.path.basename(sys.argv[0])
executablePath = re.sub(executableName, '', executableFullPath)

command = 'ls ' + executablePath + '*.tgz'
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
	print RED + "Unable to get the csur archive name; fix the problem and try again.\n" + err + RESETCOLORS
	exit(1)

csurArchive = out.strip()
csurArchiveName = re.match(r'.*/(.*\.tgz)', csurArchive).group(1)
csurArchiveMd5sumFile = re.sub('tgz', 'md5sum', csurArchiveName)

#Check the md5sum of the csur archive to make sure it is not corrupt.
command = 'md5sum ' + csurArchive
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
        print RED + "Unable to determine the md5sum of the csur archive (" + csurArchive + "); fix the problem and try again.\n" + err + RESETCOLORS
        exit(1)

csurArchiveMd5sum = re.match('([0-9,a-f]*)\s+', out).group(1)

try:
	with open(csurArchiveMd5sumFile) as f:
		for line in f:
			line = line.strip()
			if csurArchiveName in line:
				csurMd5sum = re.match('([0-9,a-f]*)\s+', out).group(1)
except IOError as err:
        print RED + "Unable to get the md5sum of the csur archive from (" + csurArchiveMd5sumFile + "); fix the problem and try again.\n" + err + RESETCOLORS
        exit(1)

if csurArchiveMd5sum != csurMd5sum:
        print RED + "The csur archive (" + csurArchive + ") is corrupt; fix the problem and try again.\n" + err + RESETCOLORS
        exit(1)

#Change into the root directory and extract the csur archive.
try:
	os.chdir('/')
except OSError as err:
	print RED + "Could not change into the root (/) directory; fix the problem and try again.\n" + str(err) + RESETCOLORS
	exit(1)

command = 'tar -zxvf ' + csurArchive
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()

if result.returncode != 0:
	print RED + "Unable to extract the csur archive (" + csurArchive + "); fix the problem and try again.\n" + err + RESETCOLORS
	exit(1)

print GREEN + "The csur archive has successfully been extracted to (" + csurDir + ") and is ready to install.\n\n" + RESETCOLORS

print RED + "Before updating the system make sure the following tasks have been completed as necessary:\n"
print "\t1. The SAP HANA application has been shut down.\n"
print "\t2. The system has been backed up.\n"
print "\t3. If the system is a Gen 1.0 Scale-up, then make sure the log partition is completely backed up.\n"
print RESETCOLORS
