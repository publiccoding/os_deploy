# Embedded file name: ./bin/healthCheck.py
import re
import signal
import time
import sys
import os
import optparse
import traceback
import datetime
from threading import Thread
from modules.computeNodeInventory import ComputeNodeInventory, Gen1ScaleUpComputeNodeInventory
from modules.healthCheckUtils import RED, RESETCOLORS, SignalHandler
from modules.healthCheckInitialize import Initialize
from modules.cursesThread import CursesThread

def main():
    if os.geteuid() != 0:
        print RED + 'You must be root to run this program; exiting program execution.' + RESETCOLORS
        exit(1)
    programVersion = '1.0-0'
    usage = 'usage: %prog [[-d] [-h] [-v]]'
    parser = optparse.OptionParser(usage=usage)
    parser.add_option('-d', action='store_true', default=False, help='This option is used when problems are encountered and additional debug information is needed.')
    parser.add_option('-v', action='store_true', default=False, help="This option is used to display the application's version.")
    options, args = parser.parse_args()
    if options.v:
        print os.path.basename(sys.argv[0]) + ' ' + programVersion
        exit(0)
    if options.d:
        debug = True
    else:
        debug = False
    versionInformationLogOnly = True
    updateOSHarddrives = False
    healthBasePath = '/hp/support/health'
    currentLogDir = datetime.datetime.now().strftime('Date_%d%b%Y_Time_%H:%M:%S')
    logBaseDir = healthBasePath + '/log/' + currentLogDir + '/'
    sessionScreenLog = logBaseDir + 'sessionScreenLog.log'
    cursesLog = logBaseDir + 'cursesLog.log'
    try:
        os.mkdir(logBaseDir)
    except OSError as err:
        print RED + 'Unable to create the current log directory ' + logBaseDir + '; fix the problem and try again; exiting program execution.\n' + str(err) + RESETCOLORS
        exit(1)

    try:
        cursesThread = CursesThread(sessionScreenLog, cursesLog)
        cursesThread.daemon = True
        cursesThread.start()
        initialize = Initialize(cursesThread)
        healthResourceDict = initialize.init(healthBasePath, logBaseDir, debug, programVersion, versionInformationLogOnly, updateOSHarddrives)
        cursesThread.insertMessage(['informative', 'The Health Check report has been created and is in the ' + healthBasePath + ' directory.'])
        cursesThread.insertMessage(['info', ' '])
        cursesThread.getUserInput(['informative', 'Press enter to exit.'])
        while not cursesThread.isUserInputReady():
            time.sleep(0.1)

    except Exception:
        cursesThread.join()
        traceback.print_exc()
        exit(1)
    finally:
        cursesThread.join()
        versionInformationLog = logBaseDir + 'HealthCheckReport.txt'
        if os.path.isfile(versionInformationLog):
            try:
                with open(versionInformationLog) as f:
                    for line in f:
                        print line.strip()

                    print '\n'
            except IOError as err:
                print 'I/O Error while trying to print ' + versionInformationLog + '.\n' + err + '\n'


main()