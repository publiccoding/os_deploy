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
		self.password = None
		self.gettingPassword = False

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
			curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_RED)
			curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)
			curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_MAGENTA)

			feedbackHighlight = curses.color_pair(1)
			errorHighlight = curses.color_pair(2)
			informativeHighlight = curses.color_pair(3)
			scrollBarBackground = curses.color_pair(4)
			scrollBarHighlight = curses.color_pair(5)
			warnHighlight = curses.color_pair(6)
			finalHighlight = curses.color_pair(7)
			errorFeedbackHighlight = curses.color_pair(8)
			informativeFeedbackHighlight = curses.color_pair(9)
			finalFeedbackHighlight = curses.color_pair(10)

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

					maxRowsConversationWindow = y - (3 + maxRowsFeedbackWindow)

					'''
					Need to set initializing to True so the first time through the 
					conversationStartingPosition is not modified due to a previous messagesList length change.
					'''
					if not loopStarted:
						loopStarted = True
						initializing = True

						#Set the starting position of the lists.
						if len(self.messagesList) < maxRowsConversationWindow:
							conversationStartingPosition = 0
						else:
							conversationStartingPosition = len(self.messagesList) - maxRowsConversationWindow

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
							if conversationHighlightPosition == maxRowsConversationWindow - 1 and conversationStartingPosition + maxRowsConversationWindow < len(self.messagesList):
								conversationStartingPosition += 1
							elif conversationHighlightPosition < maxRowsConversationWindow -1 and conversationHighlightPosition < len(wrappedMessagesList) - 1:
								conversationHighlightPosition += 1
							else:
								continue
						else:
							if feedbackHighlightPosition == maxRowsFeedbackWindow - 1 and feedbackStartingPosition + maxRowsFeedbackWindow < len(self.timerThreadList):
								feedbackStartingPosition += 1
							elif feedbackHighlightPosition < maxRowsFeedbackWindow -1 and feedbackHighlightPosition < len(self.timerThreadList) - 1:
								feedbackHighlightPosition += 1
							else:
								continue

					elif input == curses.KEY_UP:
						if windowFocus == 'conversationWindow':
							#If already at the beginning of the list do nothing.
							if conversationHighlightPosition == 0 and conversationStartingPosition > 0:
									conversationStartingPosition -= 1
							elif conversationHighlightPosition == 0:
								continue
							else:
								conversationHighlightPosition -= 1
						else:
							if feedbackHighlightPosition == 0 and feedbackStartingPosition > 0:
									feedbackStartingPosition -= 1
							elif feedbackHighlightPosition == 0:
								continue
							else:
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
								The user input string is built one character at a time.
								263 is equal to backspace.
								'''
								if input == 263:
									if self.gettingPassword:
										self.password = self.password[:-1]
									else:
										self.userInput = self.userInput[:-1]
										self.insertUserInput()
								elif input != 10 and not input < 32 and not input > 127 :
									#This causes the display to scroll to the end of the display to show the current prompt.
									if maxRowsConversationWindow < len(self.messagesList):
										if conversationStartingPosition != len(self.messagesList) - maxRowsConversationWindow:
											conversationStartingPosition = len(self.messagesList) - maxRowsConversationWindow
											conversationHighlightPosition = maxRowsConversationWindow - 1
										else:
											conversationHighlightPosition = maxRowsConversationWindow - 1
									elif conversationHighlightPosition != len(self.messagesList) - 1:
										conversationHighlightPosition = len(self.messagesList) - 1
									
									if self.gettingPassword:
										self.password += chr(input)
									else:
										self.userInput += chr(input)
										self.insertUserInput()
								elif input == 10:
									self.gettingUserInput = False
									self.userInputReady = True
								
									if self.gettingPassword:
										self.gettingPassword = False
									else: 
										self.recordScreenConversation(self.messagesList[-1][1])

					#This section adjusts the list to fit the maxRowsConversationWindow when the terminal is resized.
					if yPosition != None and maxRowsConversationWindow > yPosition:
						if conversationStartingPosition - (maxRowsConversationWindow - yPosition) >= 0:
							conversationStartingPosition = conversationStartingPosition - ((maxRowsConversationWindow - yPosition) + 1)
						else:
							conversationStartingPosition = 0

					#This keeps the conversationHighlightPosition on the screen when window is shrunk.	
					if conversationHighlightPosition > maxRowsConversationWindow - 1:
						conversationHighlightPosition = maxRowsConversationWindow - 1

					#This section moves the scrollbar and text when additional rows of text are added.
					if len(self.messagesList) != previousMessagesListLength:
						previousMessagesListLength = len(self.messagesList)

						if len(self.messagesList) > maxRowsConversationWindow:
							conversationStartingPosition = len(self.messagesList) - maxRowsConversationWindow
							conversationHighlightPosition = maxRowsConversationWindow - 1
						else:
							conversationHighlightPosition = len(self.messagesList) - 1

					if len(self.timerThreadList) != previousTimerThreadListLength:
						previousTimerThreadListLength = len(self.timerThreadList)

						if len(self.timerThreadList) > maxRowsFeedbackWindow:
							feedbackStartingPosition = len(self.timerThreadList) - maxRowsFeedbackWindow
							feedbackHighlightPosition = maxRowsFeedbackWindow - 1
						else:
							feedbackHighlightPosition = len(self.timerThreadList) - 1

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
						wrappedMessagesList = self.__wrapText(self.messagesList[conversationStartingPosition:conversationStartingPosition + maxRowsConversationWindow], maxRowsConversationWindow, x - 5)

						for i in range(0, maxRowsConversationWindow):
							messageList = wrappedMessagesList[i]
							message = messageList[1]

							if messageList[0] == 'error':
								if i == conversationHighlightPosition:
									conversationWindow.addstr(yPosition, 1, message, errorFeedbackHighlight)
								else:
									conversationWindow.addstr(yPosition, 1, message, errorHighlight)
							elif messageList[0] == 'informative':
								if i == conversationHighlightPosition:
									conversationWindow.addstr(yPosition, 1, message, informativeFeedbackHighlight)
								else:
									conversationWindow.addstr(yPosition, 1, message, informativeHighlight)
							elif messageList[0] == 'warning':
								if i == conversationHighlightPosition:
									conversationWindow.addstr(yPosition, 1, message, feedbackHighlight)
								else:
									conversationWindow.addstr(yPosition, 1, message, warnHighlight)
							elif messageList[0] == 'final':
								if i == conversationHighlightPosition:
									conversationWindow.addstr(yPosition, 1, message, finalFeedbackHighlight)
								else:
									conversationWindow.addstr(yPosition, 1, message, finalHighlight)
							else:
								if i == conversationHighlightPosition:
									conversationWindow.addstr(yPosition, 1, message, feedbackHighlight)
									#conversationWindow.addstr(yPosition, 1, message + ' sp = ' + str(conversationStartingPosition) + ' maxRowsConversationWindow = ' + str(maxRowsConversationWindow) + ' wML = ' + str(len(wrappedMessagesList)) + ' mL = ' + str(len(self.messagesList)) + ' hlP = ' + str(conversationHighlightPosition) + ' i = ' + str(i) + ' yP = ' + str(yPosition), feedbackHighlight)
								else:
									conversationWindow.addstr(yPosition, 1, message)
									#conversationWindow.addstr(yPosition, 1, message + ' sp = ' + str(conversationStartingPosition) + ' maxRowsConversationWindow = ' + str(maxRowsConversationWindow) + ' wML = ' + str(len(wrappedMessagesList)) + ' mL = ' + str(len(self.messagesList)) + ' hlP = ' + str(conversationHighlightPosition) + ' i = ' + str(i) + ' yP = ' + str(yPosition))

							if i == maxRowsConversationWindow - 1 and conversationHighlightPosition > i:
								scrollBarWindow.addstr(maxRowsConversationWindow, 1, ' ', scrollBarHighlight)
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
		except Exception as err:
			curses.echo()
			curses.nocbreak()
			curses.endwin()
			logger.exception('An exception occured while in curses mode.' + str(err))
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
	If the thread is added for the first time for a component then it is
	just added to the end of the list. Otherwise args[0] will contain
	threads location in the list.
	'''
	def insertTimerThread(self, timerThread, *args):
		if len(args) == 0:
			self.timerThreadList.append(timerThread)
		else:
			self.timerThreadList[args[0]] = timerThread
	#End insertTimerThread(self, timerThread):


	'''
	This function is used to get the location of a component's timer thread
	when it is added to the list so that we update the appropriate component
	thread location with its messages.	
	'''
	def getTimerThreadLocation(self):
		return len(self.timerThreadList) - 1
	#End getTimerThreadLocation(self):


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
	This function is for initializing for getting user input.  self.userInputReady is set to False
	until the user hits the enter key at which time it changes to True.  
	Also, *args should only be used to indicate that a password is being retrieved. By 
	default we should pass in 'password' for readability purposes, since only the length of *args is 
	checked.
	'''
	def getUserInput(self, prompt, *args):
		if len(args) == 1:
			self.gettingPassword = True
			self.password = ''

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


	'''
	This function is used to retrieve the users password string.
	'''
	def getUserPassword(self):
		return self.password
	#End getUserPassword(self):


	def __wrapText(self, messagesList, maxRowsConversationWindow, width):
		wrappedMessagesList = []

		for message in messagesList:
			messageType = message[0]
			
			if len(message[1].rstrip()) != 0:
				wrappedTextList = textwrap.wrap(message[1], width)

				for line in wrappedTextList:
					wrappedMessagesList.append([messageType, line])
			else:
				wrappedMessagesList.append(message)

		if len(wrappedMessagesList) > maxRowsConversationWindow:
			return wrappedMessagesList[len(wrappedMessagesList) - maxRowsConversationWindow:maxRowsConversationWindow + 1]
		else:
			return wrappedMessagesList

	#End __wrapText(self, messagesList, maxRowsConversationWindow, width):
