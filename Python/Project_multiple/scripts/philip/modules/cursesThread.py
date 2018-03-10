#! /usr/bin/python


from __future__ import division
from csurUpdateUtils import TimerThread
from math import *
import time
import datetime
import curses
import threading
import os
import logging
import textwrap
import re

'''
This class is used to provide the user interface.  It provides two scrolling windows.  The top window is for feedback,
while the bottom window is a conversation window; printing messages and accepting user input.
'''
class CursesThread(threading.Thread):
        def __init__(self, sessionScreenLog, cursesLog):
                super(CursesThread, self).__init__()

		self.cursesLog = cursesLog

                self.stop = threading.Event()
		self.timerThreadList = []
		self.messagesList = []

		self.userInput = None
		self.gettingUserInput = False
		self.userInputReady = False
		self.insertingUserInput = False
		self.lastMessageInMessagesList = None

		self.stdscr = None

		#Configure logging to record all screen text.
                sessionScreenHandler = logging.FileHandler(sessionScreenLog)
                self.sessionScreenLogger = logging.getLogger('sessionScreenLogger')
                self.sessionScreenLogger.setLevel(logging.INFO)
                self.sessionScreenLogger.addHandler(sessionScreenHandler)

        #End __init__(self):


	'''
	This is the main part of the class whose run function is responsible for managing the user interface.
	'''
	def run(self):
		#Configure logging
		cursesLogFile = self.cursesLog
                cursesHandler = logging.FileHandler(cursesLogFile)

                logger = logging.getLogger('cursesLogFile')

                logger.setLevel(logging.INFO)

                formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%m/%d/%Y %H:%M:%S')
                cursesHandler.setFormatter(formatter)
                logger.addHandler(cursesHandler)

		try:
			#Initialize curses
			self.stdscr = curses.initscr()

			#Turn off echoing of keys, and enter cbreak mode, where no tty buffering is performed.
			curses.noecho()
			curses.cbreak()

			self.stdscr.nodelay(1)
			self.stdscr.keypad(1)

			#Setup to use colors and create color pairs.
			curses.start_color()
			curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_YELLOW)
			curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
			curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_BLACK)
			curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
			curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_GREEN)
			curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_BLACK)
			curses.init_pair(7, curses.COLOR_MAGENTA, curses.COLOR_BLACK)

			feedbackHighlight = curses.color_pair(1)
			errorHighlight = curses.color_pair(2)
			informativeHighlight = curses.color_pair(3)
			scrollBarBackground = curses.color_pair(4)
			scrollBarHighlight = curses.color_pair(5)
			warnHighlight = curses.color_pair(6)
			finalHighlight = curses.color_pair(7)

			#Only allow three rows to be displayed at a time in the feedback window.
			maxRowsFeedbackWindow = 3 

			#Window focus starts with the conversation window and is controlled by the Tab key.
			windowFocus = 'conversationWindow'

			#Set initial values before entering loop.
			if len(self.messagesList) > 0:
				conversationHighlightPosition = len(self.messagesList) - 1
			else:
				conversationHighlightPosition = 0

			if len(self.timerThreadList) > 0:
				feedbackHighlightPosition = len(self.timerThreadList) - 1
			else:
				feedbackHighlightPosition = 0

			loopStarted = False
			yPosition = None
			previousMessagesListLength = 0
			previousTimerThreadListLength = 0
			wrappedMessagesList = []

			while not self.stop.isSet():
				#This keeps the cursor from flashing.
				time.sleep(0.04)

				initializing = False

				try:
					'''
					Get screen dimensions each time through so that the drawing area can be resized if the
					terminal size has been changed.
					'''
					y, x = self.stdscr.getmaxyx()

					'''
					Need to set initializing to True so the first time through the 
					conversationStartingPosition is not modified due to a previous messagesList length change.
					'''
					if not loopStarted:
						loopStarted = True
						initializing = True

					maxRows = y - (3 + maxRowsFeedbackWindow)

					#Set the starting position of the lists.
					if len(self.messagesList) < maxRows:
						conversationStartingPosition = 0
					else:
						conversationStartingPosition = len(self.messagesList) - maxRows

					if len(self.timerThreadList) < maxRowsFeedbackWindow:
						feedbackStartingPosition = 0
					else:
						feedbackStartingPosition = len(self.timerThreadList) - maxRowsFeedbackWindow

					#This window is the main container for the subpads.
					mainWindow = curses.newpad(y, x)

					'''
					This window is for displaying feedback, which is a thread running
					that shows elapsed time.
					'''
					feedbackWindow = mainWindow.subpad(maxRowsFeedbackWindow + 2, 0, 0, 0)
					feedbackWindow.border('|', '|', '-', '-', '+', '+', '+', '+')

					scrollBarWindow = mainWindow.subpad(y - 4, 3, 4, 0)
					scrollBarWindow.border('|', '|', '-', '-', '+', '+', '+', '+')

					conversationWindow = mainWindow.subpad(y - 4, 0, 4, 2)
					conversationWindow.border('|', '|', '-', '-', '+', '+', '+', '+')
					input = self.stdscr.getch()

					'''
					The curses.KEY_DOWN and curses.KEY_UP are for scrolling the window's content up or down.
					Also, 9 represents the Tab key for changing focus between the windows for scrolling purposes.
					'''
					if input == curses.KEY_DOWN:
						if windowFocus == 'conversationWindow':
							#If already at the end of the list do nothing.
							if conversationHighlightPosition == len(self.messagesList) - 1:
								continue
		
							if conversationHighlightPosition != len(self.messagesList) - 1:
								conversationHighlightPosition += 1
						else:
							if feedbackHighlightPosition == len(self.timerThreadList) - 1:
								continue

							if feedbackHighlightPosition != len(self.timerThreadList) - 1:
								feedbackHighlightPosition += 1
							
					elif input == curses.KEY_UP:
						if windowFocus == 'conversationWindow':
							#If already at the beginning of the list do nothing.
							if conversationHighlightPosition == 0:
								continue

							conversationHighlightPosition -= 1
						else:
							if feedbackHighlightPosition == 0:
								continue

							feedbackHighlightPosition -= 1
					elif input == 9:
						if windowFocus == 'feedbackWindow':
							windowFocus = 'conversationWindow'
						else:
							windowFocus = 'feedbackWindow'

					if windowFocus == 'conversationWindow':
						if self.gettingUserInput:
							#The input will be '-1' when no input has been recieved.
							if input != -1:
								'''
								10 is equal to the enter key and characters between 32 and 127 are printable characters, which we want; none printable characters are ignored.
								The user input string is built one chracter at a time.
								263 is equal to backspace.
								'''
								if input == 263:
									self.userInput = self.userInput[:-1]
									self.insertUserInput()
								elif input != 10 and not input < 32 and not input > 127 :
									#This causes the display to scroll to the end of the display to show the current prompt.
									if maxRows < len(self.messagesList):
										if conversationHighlightPosition != maxRows - 1:
											conversationHighlightPosition = maxRows - 1
									elif conversationHighlightPosition != len(self.messagesList) - 1:
										conversationHighlightPosition = len(self.messagesList) - 1
									self.userInput += chr(input)
									self.insertUserInput()
								elif input == 10:
									self.gettingUserInput = False
									self.userInputReady = True
									self.recordScreenConversation(self.messagesList[-1][1])

					'''
					This causes the window to scroll down when the highlighted row goes above the
					top of the window's visible area.
					'''
					if windowFocus == 'conversationWindow':
						if conversationHighlightPosition < conversationStartingPosition:
							conversationStartingPosition = conversationHighlightPosition
					else:
						if feedbackHighlightPosition < feedbackStartingPosition:
							feedbackStartingPosition = feedbackHighlightPosition

					#This section adjusts the list to fit the maxRows when the terminal is resized.
					if yPosition != None and maxRows > yPosition:
						if conversationStartingPosition - (maxRows - yPosition) >= 0:
							conversationStartingPosition = conversationStartingPosition - ((maxRows - yPosition) + 1)
						else:
							conversationStartingPosition = 0

					#This section moves the scrollbar and text when additional rows of text are added.
					if windowFocus == 'conversationWindow':
						if len(self.messagesList) != previousMessagesListLength:
							previousMessagesListLength = len(self.messagesList)
							conversationHighlightPosition = previousMessagesListLength - 1  

							if conversationStartingPosition < len(self.messagesList) - 1 and len(self.messagesList) > maxRows and not initializing:
								conversationStartingPosition += 1

						#This moves the feedbackHighlightPosition down even when the window does not have focus.
						if len(self.timerThreadList) != previousTimerThreadListLength:
							previousTimerThreadListLength = len(self.timerThreadList)
							feedbackHighlightPosition = previousTimerThreadListLength - 1  
					else:
						if len(self.timerThreadList) != previousTimerThreadListLength:
							previousTimerThreadListLength = len(self.timerThreadList)
							feedbackHighlightPosition = previousTimerThreadListLength - 1  

							if feedbackStartingPosition < len(self.timerThreadList) - 1 and len(self.timerThreadList) > maxRowsFeedbackWindow and not initializing:
								feedbackStartingPosition += 1

						#This moves the conversationHighlightPosition down even when the window does not have focus.
						if len(self.messagesList) != previousMessagesListLength:
							previousMessagesListLength = len(self.messagesList)
							conversationHighlightPosition = previousMessagesListLength - 1  

					yPosition = 1

					#Make the text and border bold for whichever window has focus.
					if windowFocus == 'feedbackWindow':
						feedbackWindow.attrset(curses.A_BOLD)
						conversationWindow.attrset(curses.A_DIM)
						scrollBarWindow.attrset(curses.A_DIM)
					else:
						feedbackWindow.attrset(curses.A_DIM)
						conversationWindow.attrset(curses.A_BOLD)
						scrollBarWindow.attrset(curses.A_BOLD)

					#This section updated the timer thread feedback window.
					if len(self.timerThreadList) > 0:
						for i in range(feedbackStartingPosition, feedbackStartingPosition + maxRowsFeedbackWindow):
							timerList = self.timerThreadList[i]

							if timerList[1].isAlive():
								message = timerList[1].getMessage() + timerList[1].getTimeStamp()
							else:
								message = timerList[0]


							if i == feedbackHighlightPosition:
								feedbackWindow.addstr(yPosition, 1, message, feedbackHighlight)
							else:
								feedbackWindow.addstr(yPosition, 1, message)

							yPosition += 1

							if i == len(self.timerThreadList) - 1:
								break

					yPosition = 1

					#This section updates the conversation window.
					if len(self.messagesList) > 0:
						wrappedMessagesList = self.__wrapText(self.messagesList[conversationStartingPosition:conversationStartingPosition + maxRows], maxRows, x - 5)

						for i in range(0, maxRows):
							messageList = wrappedMessagesList[i]
							message = messageList[1]

							if messageList[0] == 'error':
								conversationWindow.addstr(yPosition, 1, message, errorHighlight)
							elif messageList[0] == 'informative':
								conversationWindow.addstr(yPosition, 1, message, informativeHighlight)
							elif messageList[0] == 'warning':
								conversationWindow.addstr(yPosition, 1, message, warnHighlight)
							elif messageList[0] == 'final':
								conversationWindow.addstr(yPosition, 1, message, finalHighlight)
							else:
								conversationWindow.addstr(yPosition, 1, message)
								#conversationWindow.addstr(yPosition, 1, message + ' sp = ' + str(conversationStartingPosition) + ' maxRows = ' + str(maxRows) + ' wML = ' + str(len(wrappedMessagesList)) + ' mL = ' + str(len(self.messagesList)) + ' hlP = ' + str(conversationHighlightPosition) + ' i = ' + str(i) + ' yP = ' + str(yPosition))

							if i == maxRows - 1 and conversationHighlightPosition > i:
								scrollBarWindow.addstr(maxRows, 1, ' ', scrollBarHighlight)
							elif i == conversationHighlightPosition:
								scrollBarWindow.addstr(yPosition, 1, ' ', scrollBarHighlight)
							else:
								scrollBarWindow.addstr(yPosition, 1, ' ', scrollBarBackground)

							yPosition += 1

							#This sets the scrollbar background if the window is bigger then the list.
							if i == len(wrappedMessagesList) - 1:
								if y >= len(wrappedMessagesList):
									for i in range(0, (y - len(wrappedMessagesList)) - 6):
										scrollBarWindow.addstr(yPosition, 1, ' ', scrollBarBackground)
										yPosition += 1
								break

					scrollBarWindow.refresh(0, 0, 4, 0, y, 3)
					feedbackWindow.refresh(0, 0, 0, 0, 5, x)
					conversationWindow.refresh(0, 0, 4, 2, y, x)

				except curses.error:
					logger.exception('A curses exception occurred')
					curses.endwin()

			#Set everything back to normal
			curses.echo()
			curses.nocbreak()
			curses.endwin()
		except Exception:
			curses.echo()
			curses.nocbreak()
			curses.endwin()
			logger.exception('An exception occured while in curses mode.')
	#End run(self):


        '''
        This function cancels curses mode.
        '''
	def join(self, timeout=None):
		self.stop.set()
		super(CursesThread, self).join(timeout)
	#End join(self, timeout=None):


	'''
	This function is for adding timer threads to the timerThreadList.
	'''
	def insertTimerThread(self, timerThread):
		self.timerThreadList.append(timerThread)
	#End insertTimerThread(self, timerThread):


	'''
	This function updates a timer thread's message before stopping the thread.
	'''
	def updateTimerThread(self, message, index):
		self.timerThreadList[index][0] = message
	#End updateTimerThread(self, message, index):


	'''
	This function is for adding to the conversation list.
	'''
	def insertMessage(self, message):
		self.messagesList.append(message)
		self.recordScreenConversation(message[1])
	#End insertMessage(self, message):

	'''
	This function is used to insert the users input into the conversation list so that it is 
	echoed to the conversation window.
	It is mainly used to get a string of length > 1.
	'''	
	def insertUserInput(self):
		currentLine =  self.lastMessageInMessagesList + self.userInput
		
		self.messagesList[-1][1] = currentLine
	#End insertUserInput(self):


	'''
	This function is for recording screen text.
	'''
	def recordScreenConversation(self, message):
                self.sessionScreenLogger.info(message)
	#End recordScreenConversation(self, message):


	'''
	This function is for getting the length of the timerThreadList so that we
	can keep track of a threads location in the list for when we want to update
	its message after it is dead.
	'''
	def getTimerThreadListLength(self):
		return len(self.timerThreadList)
	#End insertTimerThread(self):


	'''
	This function is for initializing for getting user input.  self.userInputReady is set to False
	until the user hits the enter key at which time it changes to True.  
	'''
	def getUserInput(self, prompt):
		self.lastMessageInMessagesList = prompt[1]
		self.messagesList.append(prompt)
		self.userInputReady = False
		self.gettingUserInput = True
		self.userInput = ''
	#End getUserInput(self):


	'''
	This function is used to determine when the user has completed entering their input, which
	results in self.userInputReady being set to True.
	'''
	def isUserInputReady(self):
		return self.userInputReady
	#End isUserInputReady(self):


	'''
	This function is used to retrieve the users input string.
	'''
	def getUserResponse(self):
		return self.userInput
	#End getUserResponse(self):


	def __wrapText(self, messagesList, maxRows, width):
		wrappedMessagesList = []

		for message in messagesList:
			messageType = message[0]
			
			if len(message[1].rstrip()) != 0:
				wrappedTextList = textwrap.wrap(message[1], width)

				for line in wrappedTextList:
					wrappedMessagesList.append([messageType, line])
			else:
				wrappedMessagesList.append(message)

		if len(wrappedMessagesList) > maxRows:
			return wrappedMessagesList[len(wrappedMessagesList) - maxRows:maxRows + 1]
		else:
			return wrappedMessagesList

	#End __wrapText(self, messagesList, maxRows, width):
