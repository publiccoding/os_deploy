#Colors used when printing messages to screen.
YELLOW = '\033[1;33m'
RED = '\033[1;31m'
GREEN = '\033[1;32m'
BLUE = '\033[1;34m'
RESETCOLORS = '\033[1;0m'


'''
This function is used to prevent users from interrupting the update process before
warning them of the consequences.
'''
def signal_handler(signum, frame):
        regex = r"^(y|n)$"

        print spUtils.RED + "\nThe update should not be interrupted once started, since it could put the system in an unknown state.\n" + spUtils.RESETCOLORS

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
