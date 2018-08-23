# Embedded file name: ./configureNics.py
import subprocess
import datetime
import shutil
import os
GREEN = '\x1b[32m'
RED = '\x1b[31m'
RESETCOLORS = '\x1b[0m'
programDir = os.path.dirname(os.path.realpath(__file__))
try:
    netPersistentRulesFile = open('/etc/udev/rules.d/70-persistent-net.rules', 'w')
except OSError as err:
    print RED + 'Unable to access /etc/udev/rules.d/70-persistent-net.rules; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS
    exit(1)

try:
    nicDataFile = programDir + '/nicDataFile/macAddressData.dat'
    with open(nicDataFile, 'r') as macAddressDataFile:
        for line in macAddressDataFile:
            if '|' in line:
                line = line.strip()
                netPersistentRulesFile.write('SUBSYSTEM=="net", ACTION=="add", DRIVERS=="?*", ATTR{address}=="' + line.split('|')[1] + '", ATTR{dev_id}=="0x0", ATTR{type}=="1", KERNEL=="eth*", NAME="' + line.split('|')[0] + '"\n\n')

except OSError as err:
    print RED + 'Unable to access ' + nicDataFile + '; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS
    exit(1)
finally:
    netPersistentRulesFile.close()