# Embedded file name: ./fusionIO.py
from spUtils import RED, GREEN, RESETCOLORS, TimeFeedbackThread
import subprocess
import logging
import shutil
import re
import time
import signal
import os
import shutil
import threading

class UpdateFusionIO():
    """
    Use the constructor to create a threading event that will be used to stop and restart the timer thread
    when a signal (SIGINT, SIGQUIT) is captured.
    """

    def __init__(self):
        self.timerController = threading.Event()
        self.timeFeedbackThread = ''
        self.pid = ''
        self.cancelled = 'no'
        self.completionStatus = ''

    def updateFusionIO(self, patchResourceDict, loggerName, **kwargs):
        firmwareUpdateRequired = kwargs['firmwareUpdateRequired']
        iomemoryCfgBackup = kwargs['iomemory-vslBackup']
        logger = logging.getLogger(loggerName)
        if firmwareUpdateRequired == 'yes':
            logger.info('Updating the FusionIO firmware and software.')
            busList = kwargs['busList'].split()
        else:
            logger.info('Updating the FusionIO software.')
        try:
            patchBaseDir = re.sub('\\s+', '', patchResourceDict['patchBaseDir']).rstrip('/')
            fusionIOSubDir = re.sub('\\s+', '', patchResourceDict['fusionIOSubDir'])
            fusionPatchDir = patchBaseDir + '/' + fusionIOSubDir
            fusionSourceDir = fusionPatchDir + '/src/'
            fusionIODriverSrcRPM = re.sub('\\s+', '', patchResourceDict['fusionIODriverSrcRPM'])
        except KeyError as err:
            logger.error('The resource key (' + str(err) + ') was not present in the resource file.')
            print RED + 'A resource key was not present in the resource file; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually.' + RESETCOLORS
            self.completionStatus = 'Failure'
            return

        command = 'uname -r'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.debug('The output of the command (' + command + ') used to get the currently used kernel was: ' + out.strip())
        if result.returncode != 0:
            logger.error("Unable to get the system's current kernel information.\n" + err)
            print RED + "Unable to get the system's current kernel information; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
            self.completionStatus = 'Failure'
            return
        kernel = out.strip()
        command = 'uname -p'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, err = result.communicate()
        logger.debug('The output of the command (' + command + ") used to get the system's processor type was: " + out.strip())
        if result.returncode != 0:
            logger.error("Unable to get the system's processor type.\n" + err)
            print RED + "Unable to get the system's processor type; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually." + RESETCOLORS
            self.completionStatus = 'Failure'
            return
        processorType = out.strip()
        fusionIODriverRPM = fusionIODriverSrcRPM.replace('iomemory-vsl', '-vsl-' + kernel).replace('src', processorType)
        if firmwareUpdateRequired == 'yes':
            for bus in busList:
                time.sleep(2)
                message = 'Updating ioDIMM in slot ' + bus
                self.timeFeedbackThread = TimeFeedbackThread(componentMessage=message, event=self.timerController)
                self.timeFeedbackThread.start()
                command = 'fio-update-iodrive -y -f -s ' + bus + ' ' + fusionPatchDir + '/' + '*.fff'
                result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)
                self.pid = result.pid
                out, err = result.communicate()
                logger.debug('The output of the command (' + command + ') used to update the FusionIO firmware was: ' + out.strip())
                self.timeFeedbackThread.stopTimer()
                self.timeFeedbackThread.join()
                print ''
                if result.returncode != 0:
                    if self.cancelled == 'yes':
                        logger.info('The FusionIO firmware update was cancelled by the user.')
                        print RED + 'The FusionIO firmware update was cancelled; the FusionIO firmware and software/driver will have to be updated manually.' + RESETCOLORS
                    else:
                        logger.error('Failed to upgrade the FusionIO firmware:\n' + err)
                        print RED + 'Failed to upgrade the FusionIO firmware; check the log file for errors; the FusionIO firmware and software/driver will have to be updated manually.' + RESETCOLORS
                    self.completionStatus = 'Failure'
                    return

            command = 'rpm -e fio-util'
            result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            out, err = result.communicate()
            logger.debug('The output of the command (' + command + ') used to remove the fio-util package before updating the FusionIO software was: ' + out.strip())
            if result.returncode != 0:
                logger.error('Failed to remove the fio-util package:\n' + err)
                print RED + 'Failed to remove the fio-util package; check the log file for errors; the FusionIO software/driver will have to be updated manually.' + RESETCOLORS
                self.completionStatus = 'Failure'
                return
        self.timeFeedbackThread = TimeFeedbackThread(componentMessage='Updating the FusionIO driver and software', event=self.timerController)
        self.timeFeedbackThread.start()
        command = 'rpmbuild --rebuild ' + fusionSourceDir + '*.rpm'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)
        self.pid = result.pid
        out, err = result.communicate()
        logger.debug('The output of the command (' + command + ') used to build the FusionIO driver was: ' + out.strip())
        if result.returncode != 0:
            self.timeFeedbackThread.stopTimer()
            self.timeFeedbackThread.join()
            if self.cancelled == 'yes':
                logger.info('The FusionIO driver and software update was cancelled by the user.')
                print RED + '\nThe FusionIO driver and software update was cancelled; the FusionIO software/driver will have to be updated manually.' + RESETCOLORS
            else:
                logger.error('Failed to build the FusionIO driver:\n' + err)
                print RED + 'Failed to build the FusionIO driver; check the log file for errors; the FusionIO software/driver will have to be updated manually.' + RESETCOLORS
            self.completionStatus = 'Failure'
            return
        out = out.strip()
        fusionIODriverPattern = re.compile('.*Wrote:\\s+((/[0-9,a-z,A-Z,_]+)+' + fusionIODriverRPM + ')', re.DOTALL)
        logger.debug('The regex used to get the FusionIO driver RPM location was: ' + fusionIODriverPattern.pattern)
        driverRPM = re.match(fusionIODriverPattern, out).group(1)
        logger.debug('The FuionIO driver was determined to be: ' + driverRPM)
        try:
            shutil.copy2(driverRPM, fusionPatchDir)
        except IOError as err:
            self.timeFeedbackThread.stopTimer()
            self.timeFeedbackThread.join()
            print ''
            logger.error('Unable to retrieve the driver RPM.\n' + err)
            print RED + 'Unable to retrieve the driver RPM; check log file for errors; the FusionIO firmware and software/driver will have to be updated manually.' + RESETCOLORS
            self.completionStatus = 'Failure'
            return

        command = 'rpm -ivh ' + fusionPatchDir + '/' + '*.rpm'
        result = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=self.preexec, shell=True)
        self.pid = result.pid
        out, err = result.communicate()
        logger.debug('The output of the command (' + command + ') used to install the FusionIO software and driver was: ' + out.strip())
        if result.returncode != 0:
            self.timeFeedbackThread.stopTimer()
            self.timeFeedbackThread.join()
            print ''
            if self.cancelled == 'yes':
                logger.info('The FusionIO driver and software installation was cancelled by the user.')
                print RED + 'The FusionIO driver and software installation was cancelled; the FusionIO software/driver will have to be installed manually from ' + fusionPatchDir + '.' + RESETCOLORS
            else:
                logger.error('Failed to install the FusionIO software and driver:\n' + err)
                print RED + 'Failed to install the FusionIO software and driver; check the log file for errors; the FusionIO software/driver will have to be installed manually from ' + fusionPatchDir + '.' + RESETCOLORS
            self.completionStatus = 'Failure'
            return
        try:
            shutil.copy2(iomemoryCfgBackup, '/etc/sysconfig/iomemory-vsl')
        except IOError as err:
            logger.error("Failed to restore the system's iomemory-vsl configuration file.\n" + str(err))
            print RED + "Failed to restore the system's iomemory-vsl configuration file; check the log file for errors; the file will need to be restored manually." + RESETCOLORS

        if firmwareUpdateRequired == 'yes':
            logger.info('Done Updating the FusionIO firmware and software.')
        else:
            logger.info('Done Updating the FusionIO software.')
        self.timeFeedbackThread.stopTimer()
        self.timeFeedbackThread.join()
        print ''
        self.completionStatus = 'Success'

    def endTask(self):
        try:
            self.cancelled = 'yes'
            pgid = os.getpgid(self.pid)
            os.killpg(pgid, signal.SIGKILL)
        except OSError:
            pass

    def preexec(self):
        os.setpgrp()

    def getCompletionStatus(self):
        return self.completionStatus

    def pauseTimerThread(self):
        self.timeFeedbackThread.pauseTimer()

    def resumeTimerThread(self):
        self.timeFeedbackThread.resumeTimer()