# Embedded file name: ./configure.py
import re
import optparse
import os
import sys
import subprocess
import shutil
RED = '\x1b[31m'
GREEN = '\x1b[32m'
PURPLE = '\x1b[35m'
YELLOW = '\x1b[33m'
RESETCOLORS = '\x1b[0m'
debug = False
supportedComputeNodeModels = 'DL580Gen9, DL580Gen8, DL380pGen8, DL580G7, DL980G7, DL580, BL680cG7'
supportedDistributionLevels = 'SLES11, SLES12, RHEL6, RHEL7'
systemListDict = {'DL580Gen8': 'CS500 IvyBridge',
 'DL580Gen9': 'CS500',
 'DL580G7': 'Gen1',
 'DL980G7': 'Gen1',
 'BL680cG7': 'Gen1'}
processorListDict = {'E7-8890v3': 'Haswell',
 'E7-8890v4': 'Broadwell',
 'E7-8880v3': 'Haswell',
 'E7-8880Lv3': 'Haswell',
 'Unkn': ''}
healthDir = '/hp/support/health/'
binDir = healthDir + 'bin'
logDir = healthDir + 'log'
rpmsDir = healthDir + 'RPMs'
resourceDir = healthDir + 'resourceFiles'
rcFile = healthDir + '.healthrc'
if os.geteuid() != 0:
    print RED + 'You must be root to run this program.' + RESETCOLORS
    exit(1)
usage = 'usage: %prog [[-d] [-h]]'
parser = optparse.OptionParser(usage=usage)
parser.add_option('-d', action='store_true', default=False, help='Use debug option when additional debug information is needed.')
options, args = parser.parse_args()
if options.d:
    debug = True
command = 'dmidecode -s system-product-name'
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()
if result.returncode != 0:
    print RED + "Unable to get the system model using (' + command +'). Please correct and try again.\n" + err + RESETCOLORS
    exit(1)
out = out.strip()
try:
    systemModel = re.match('[a-z,0-9]+\\s+(.*)', out, re.IGNORECASE).group(1).replace(' ', '')
except AttributeError as err:
    print RED + "There was a system model match error when trying to match against '" + out + "':\n" + str(err) + '.' + RESETCOLORS
    exit(1)

try:
    if systemModel not in supportedComputeNodeModels:
        subModel = re.match('(\\w\\w\\d\\d\\d)', systemModel)
        if subModel != None and subModel.group(1) in supportedComputeNodeModels:
            pass
        else:
            print RED + "The system's model (" + systemModel + ') is not supported by this tool.' + RESETCOLORS
            exit(1)
except KeyError as err:
    print RED + 'Internal Error: The source key (' + str(err) + ") was not present in this configure tool's supported models list. Please check for a newer version of this tool, or report the error to the HPE SAP HANA CoE DevOps team." + RESETCOLORS
    exit(1)

if debug:
    print "DEBUG: The system's model is " + systemModel
if systemModel == 'DL580Gen9':
    command = 'dmidecode -s processor-version'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    out = out.strip()
    if result.returncode != 0:
        print RED + "Unable to get the processor version using (' + command +'). Please correct and try again.\n" + err + RESETCOLORS
        exit(1)
    try:
        processorVersion = re.search('CPU (E\\d-\\s*\\d{4}\\w* v\\w*)', out).group(1).replace(' ', '')
    except AttributeError as err:
        print YELLOW + "There was a processor version match error when trying to match against '" + out + "':\n" + str(err) + '.' + RESETCOLORS
        processorVersion = 'Unkn'

    if debug:
        print 'DEBUG: The processor version is ' + processorVersion
if systemModel in systemListDict:
    system = systemListDict[systemModel]
else:
    system = systemModel
if systemModel == 'DL580Gen9':
    system = system + ' ' + processorListDict[processorVersion]
print GREEN + 'System Model: ' + system + RESETCOLORS
command = 'cat /proc/version'
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()
if debug:
    print 'DEBUG: The output of the command (' + command + ') used to get the OS distribution information was: ' + out.strip()
if result.returncode != 0:
    print RED + "Unable to get the system's OS distribution version information.\n" + err + RESETCOLORS
    exit(1)
versionInfo = out.lower()
if 'suse' in versionInfo:
    OSDist = 'SLES'
    command = 'cat /etc/SuSE-release'
else:
    OSDist = 'RHEL'
    command = 'cat /etc/redhat-release'
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()
if result.returncode != 0:
    print +RED + "Unable to get the system's OS distribution level.\n" + err + RESETCOLORS
    exit(1)
else:
    releaseInfo = out.replace('\n', ' ')
if OSDist == 'SLES':
    try:
        slesVersion = re.match('.*version\\s*=\\s*([1-4]{2})', releaseInfo, re.IGNORECASE).group(1)
    except AttributeError as err:
        print RED + "There was a SLES OS version match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.' + RESETCOLORS
        exit(1)

    try:
        slesPatchLevel = re.search('patchlevel\\s*=\\s*([1-4]{1})', releaseInfo, re.IGNORECASE).group(1)
    except AttributeError as err:
        print RED + "There was SLES patch level match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.' + RESETCOLORS
        exit(1)

    osDistLevel = OSDist + slesVersion
else:
    try:
        rhelVersion = re.match('.*release\\s+([6-7]{1})\\.([0-9]{1}).*', releaseInfo, re.IGNORECASE).group(1)
    except AttributeError as err:
        print RED + "There was RHEL OS version match error when trying to match against '" + releaseInfo + "':\n" + str(err) + '.' + RESETCOLORS
        exit(1)

    osDistLevel = OSDist + rhelVersion
if osDistLevel not in supportedDistributionLevels:
    print RED + "The system's OS distribution level (" + osDistLevel + ') is not supported by this tool release.' + RESETCOLORS
    exit(1)
if debug:
    print "DEBUG: The system's OS distribution level was determined to be: " + osDistLevel + '.'
appFile = 'healthAppResourceFile'
computeFile = 'computeNodeResourceFile'
appFileFound = False
computeFileFound = False
if os.path.exists(resourceDir):
    files = os.listdir(resourceDir)
    try:
        systemClass = re.match('(\\w+)', system).group(1)
    except AttributeError as err:
        print YELLOW + "There was a system class match error when trying to match against '" + system + "':\n" + str(err) + '.' + RESETCOLORS
        exit(1)

    for file in files:
        if systemClass in file:
            if computeFile in file:
                destFile = computeFile
            elif appFile in file:
                destFile = appFile
            else:
                continue
            try:
                fileVersion = re.search('-(20\\d\\d\\.\\d\\d-\\d)', file).group(1)
            except AttributeError as err:
                print YELLOW + "There was a resource file version match error when trying to match against '" + file + "':\n" + str(err) + '.' + RESETCOLORS

            if destFile == computeFile:
                if computeFileFound:
                    if fileVersion > computeFileVersion:
                        computeFileVersion = fileVersion
                        computeFileSrc = file
                else:
                    computeFileFound = True
                    computeFileVersion = fileVersion
                    computeFileSrc = file
            elif destFile == appFile:
                if appFileFound:
                    if fileVersion > appFileVersion:
                        appFileVersion = fileVersion
                        appFileSrc = file
                else:
                    appFileFound = True
                    appFileVersion = fileVersion
                    appFileSrc = file

    if not (computeFileFound and appFileFound):
        print RED + 'Unable to locate either the healthApp or computeNode resource file. Both need to exist. computeNode File:' + computeFile + ', healthApp File:' + appFile + '.' + RESETCOLORS
        exit(1)
    srcFile = resourceDir + '/' + appFileSrc
    destFile = resourceDir + '/' + appFile
    try:
        shutil.copyfile(srcFile, destFile)
    except IOError as err:
        print RED + 'I/O Error: Unable to copy ' + appFileSrc + ' to ' + appFile + '. Please fix the problem and try again.\n' + str(err) + RESETCOLORS
        exit(1)

    print GREEN + 'Copied ' + appFileSrc + ' to ' + appFile + RESETCOLORS
    srcFile = resourceDir + '/' + computeFileSrc
    destFile = resourceDir + '/' + computeFile
    try:
        shutil.copyfile(srcFile, destFile)
    except IOError as err:
        print RED + 'I/O Error: Unable to copy ' + computeFileSrc + ' to ' + computeFile + '. Please fix the problem and try again.\n' + str(err) + RESETCOLORS
        exit(1)

    print GREEN + 'Copied ' + computeFileSrc + ' to ' + computeFile + RESETCOLORS
if os.path.exists(logDir):
    dirs = os.listdir(logDir)
    for dir in dirs:
        dir = logDir + '/' + dir
        try:
            shutil.rmtree(dir)
        except IOError as err:
            print RED + 'Unable to delete the current health related directory (' + dir + '); fix the problem and try again.\n' + str(err) + RESETCOLORS
            exit(1)

if os.path.exists(rcFile):
    os.remove(rcFile)
command = 'rpm -qa |grep python-curses'
result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
out, err = result.communicate()
if debug:
    print 'DEBUG: The output of the command (' + command + ') used to check if python-curses is installed: ' + out.strip()
if result.returncode == 1:
    command = 'python -V'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if debug:
        print 'DEBUG: The output of the command (' + command + ') used to get the python version was: ' + err.strip()
    if result.returncode != 0:
        print RED + 'Unable to get the python version.\n' + err + RESETCOLORS
        exit(1)
    try:
        pythonVersion = re.match('Python (\\d+\\.\\d+\\.\\d+)', err).group(1)
    except AttributeError as err:
        print RED + 'There was a python version match error when trying to match against ' + out + "':\n" + str(err) + '.' + RESETCOLORS
        exit(1)

    Vmin = 266
    Vmax = 283
    Vx = 0
    cnt = 2
    for i in pythonVersion.split('.'):
        Vx = int(i) * 10 ** cnt + Vx
        cnt -= 1

    if cnt == 0:
        Vx = Vx * 10
    if Vmin <= Vx and Vx <= Vmax:
        pass
    else:
        print RED + 'WARNING: Python version (' + pythonVersion + ') is not a supported version (2.6.6 to 2.7.13).'
    if os.path.exists(rpmsDir):
        files = os.listdir(rpmsDir)
        for file in files:
            if pythonVersion in file and 'python-curses' in file and '.rpm' in file:
                rpm = file
                command = 'rpm -ihv ' + rpmsDir + '/' + rpm + ' &'
                if '2.7.13' in rpm:
                    command = 'rpm -ihv ' + rpmsDir + '/' + rpm + ' --nodeps &'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                if debug:
                    print 'DEBUG: The command used to install python-curses was: (' + command + "). If this step fails, then please run command by hand adding the '--nodeps' option at the end."
                print GREEN + rpm + ' maybe installed. Please verify by running (rpm -qa |grep python-curses)' + RESETCOLORS
                break

elif result.returncode != 0:
    print RED + 'Unable to get the python version.\n' + err + RESETCOLORS
    exit(1)
if os.path.isfile(binDir + '/transform'):
    command = 'rpm -qa |grep libmcrypt'
    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, err = result.communicate()
    if debug:
        print 'DEBUG: The output of the command (' + command + ') used to check if libmcrypt is installed: ' + out.strip()
    if result.returncode == 1:
        if os.path.exists(rpmsDir):
            files = os.listdir(rpmsDir)
            for file in files:
                if 'libmcrypt' in file and '.rpm' in file:
                    rpm = file
                    command = 'rpm -ihv ' + rpmsDir + '/' + rpm + ' &'
                    result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                    out, err = result.communicate()
                    if debug:
                        print 'DEBUG: The command used to install libmcrypt was: (' + command + ').'
                    if result.returncode != 0:
                        print RED + 'Unable to install libmcrypt.\n' + err + RESETCOLORS
                        exit(1)
                    print GREEN + rpm + ' installed. ' + RESETCOLORS
                    break

print GREEN + '\nThe Health Check tool has been successfully configured. \nTo run the healchCheck tool from the ' + healthDir + ' directory: \n\t# python bin/healthCheck.pyc [-d|h|v]\n' + RESETCOLORS