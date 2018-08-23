# Embedded file name: ./bin/modules/cursorTest.py
from cursesThread import CursesThread
from healthUpdateUtils import TimerThread
import time
import signal

def resize_handler(signum, frame):
    cursesThread = cursesThreadDict['cursesThread']
    cursesThread.resizeWindow()


cursesThread = CursesThread('screenLog.log')
cursesThread.daemon = True
cursesThread.start()
cursesThreadDict = {'cursesThread': cursesThread}
version = 'Version 1.0-0'
versionLength = len(version)
title = 'SAP HANA CSUR Update Application'
titleLength = len(title)
author = 'Bill Neumann - SAP HANA CoE'
authorLength = len(author)
copyright = '(c) Copyright 2016 Hewlett Packard Enterprise Development LP'
copyrightLength = len(copyright)
welcomeMessageTop = '+' + '-' * 67 + '+'
welcomeMessageTitle = '|' + title + ' ' * (67 - titleLength) + '|'
welcomeMessageVersion = '|' + version + ' ' * (67 - versionLength) + '|'
welcomeMessageAuthor = '|' + author + ' ' * (67 - authorLength) + '|'
welcomeMessageCopyright = '|' + copyright + ' ' * (67 - copyrightLength) + '|'
welcomeMessageBottom = '+' + '-' * 67 + '+'
welcomMessageContainer = [welcomeMessageTop,
 welcomeMessageTitle,
 welcomeMessageVersion,
 welcomeMessageAuthor,
 welcomeMessageCopyright,
 welcomeMessageBottom]
for line in welcomMessageContainer:
    cursesThread.insertMessage(['info', line])

cursesThread.insertMessage(['info', ''])
timerThread1 = TimerThread('Updating switch 10.41.0.9 ... ')
timerThread1.daemon = True
timerThread1.start()
timerThread1Location = cursesThread.getTimerThreadListLength()
cursesThread.insertTimerThread(['', timerThread1])
cursesThread.insertMessage(['info', "Let's see how things are going."])
time.sleep(1.0)
timerThread2 = TimerThread('Updating switch 10.254.0.23 ... ')
timerThread2.daemon = True
timerThread2.start()
timerThread2Location = cursesThread.getTimerThreadListLength()
cursesThread.insertTimerThread(['', timerThread2])
cursesThread.insertMessage(['info', 'Another thread was started.'])
time.sleep(2.0)
timerThread3 = TimerThread('Updating switch 10.254.0.23 ... ')
timerThread3.daemon = True
timerThread3.start()
timerThread3Location = cursesThread.getTimerThreadListLength()
cursesThread.insertTimerThread(['', timerThread3])
cursesThread.insertMessage(['info', 'Stopping the first thread.'])
time.sleep(2.0)
timerThread1.stopTimer()
cursesThread.updateTimerThread('Update of switch 10.41.0.9 has completed.', timerThread1Location)
cursesThread.insertMessage(['error', 'The update of switch 10.41.0.9 completed with errors, there were many erros; so make sure and check the logs.'])
time.sleep(4.0)
cursesThread.getUserInput(['info', 'Do you want to continue: '])
while not cursesThread.isUserInputReady():
    time.sleep(0.1)

response = cursesThread.getUserResponse()
cursesThread.insertMessage(['info', 'You said, ' + response])
count = 0
while 1:
    time.sleep(0.5)
    count += 1
    if count > 3:
        cursesThread.join()
        break