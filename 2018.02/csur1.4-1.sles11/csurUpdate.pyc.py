Ñò
 7/Yc           @   sì   d  d k  Z  d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k	 l
 Z
 d  d k l Z l Z l Z d  d k l Z d  d k l Z d  d k l Z d  d k l Z d   Z e   d S(	   iÿÿÿÿN(   t   Thread(   t   REDt   RESETCOLORSt   SignalHandler(   t
   Initialize(   t   ComputeNodeUpdate(   t   updateVersionInformationFile(   t   CursesThreadc           C   s±
  t  i   d j o t d t GHt d  n d }  d } t i d |  } | i d d d	 d
 t d d | i d d d	 d
 t d d | i d d d	 d
 t d d | i d d d	 d
 t d d | i	   \ } } | i
 o. t  i i t i d  d |  GHt d  n | i o
 | i p( | i o
 | i p | i o% | i o t d t GHt d  n | i o
 t } n t } | i o
 t } n t } | i o%d } t i | d t i d t i d t } | i   \ }	 }
 |	 i   }	 | i d j o t d t GHt d  n y1 t i d |	 t i  i d  i d d  } WnB t j
 o6 }
 t d |	 d t |
  d t GHt d  n X| d j o( | d  j o t d! t GHt d  qÌn d" } t  i  i!   i" d#  } | d$ | d% } | d& } | d' } y t  i# |  Wn> t$ j
 o2 }
 t d( | d) t |
  t GHt d  n Xz=yt% | |  } t | _& | i'   t( |  } | i) | | |  | |  } | i o t | d* <n t | d* <| i ow | i* d+ d, g  | i* d- d g  t+ | d.  d j o6 | i* d/ d0 | d. d1 g  | i* d- d g  q!
nÎt+ | d2 d3  d j o` t+ | d.  d j oI | i* d4 d5 g  | i* d- d g  | i* d4 d0 | d. d1 g  nSt+ | d2 d3  d j o | i* d+ d6 g  n!d } | d2 d3 d i,   } | d7 } | o | i* d+ d8 | d9 g  n^ t+ | d.  d j o+ | i* d/ d: | d; | d. d1 g  n | i* d+ d: | d< g  t- | | i.   |  } t/ i0 t/ i1  } t/ i0 t/ i2  } t3 |  } t/ i/ t/ i1 | i4  t/ i/ t/ i2 | i4  t5 d= | i6  } | i'   xn t7 i8 d>  | i9   p Pn | i:   } | d j o3 | d? j o" | i;   | i<   t d  qªq?q?t/ i/ t/ i1 |  t/ i/ t/ i2 |  | i=   } | p t> | i.    } n | i* d- d g  t+ | d@  d j oOt+ | dA  d j o8t+ | dB  d j o!| pÕ | pg | i* d/ dC | dD g  | i* d- d g  | dE o | i* dF dG g  q,| i* dF dH g  qq| i* d+ dC | dI g  | i* d- d g  | dE o | i* dF dJ g  qq| i* dF dK g  q!
| i* d+ dC | dI g  | i* d- d g  | i* dF dK g  n­| pdL | dM } t+ | d@  d j o¹ dN | d@ j o) | dO dP i< | d@ i?    dQ 7} qZ	t+ | d@  d j o | dO | d@ dN dQ 7} qZ	| dO | d@ dN dP 7} | d@ dN =| dP i< | d@ i?    dQ 7} n t+ | dA  d j o) | dR dP i< | dA i?    dQ 7} n t+ | dB  d j o) | dS dP i< | dB i?    dQ 7} n | p | dT 7} n | i* d4 | g  n | i* d4 dU | dV g  | i* d- d g  | i@ d+ dW g  x | iA   p t7 i8 d>  qJ
WWn1 tB j
 o% | i<   tC iD   t d  n XWd  | i<   Xd  S(X   Ni    s@   You must be root to run this program; exiting program execution.i   s   1.4-1s'   usage: %prog [[-h] [-r] [-s] [-u] [-v]]t   usages   -rt   actiont
   store_truet   defaultt   helps1   This option is used to generate a version report.s   -ss¬   This option is used when upgrading Servicegaurd nodes to indicate which node is the primary node; the secondary node should already be upgraded before envoking this option.s   -usR   This option is used to update the local OS hard drives before the mirror is split.s   -vs9   This option is used to display the application's version.t    s^   Options 'r', 's', and 'u' are mutually exclusive; please try again; exiting program execution.s    dmidecode -s system-product-namet   stdoutt   stderrt   shellsk   Unable to get the system's model information (dmidecode -s system-product-name); exiting program execution.s   [a-z,0-9]+\s+(.*)t    sC   There was a system model match error when trying to match against 's   ':
t   .t
   DL380pGen8t
   DL360pGen8sX   The '-s' option can only be used on NFS Serviceguard systems (DL380pGen8 or DL360pGen8).s   /hp/support/csurs   Date_%d%H%M%S%b%Ys   /log/t   /s   sessionScreenLog.logs   cursesLog.logs+   Unable to create the current log directory s<   ; fix the problem and try again; exiting program execution.
t   sgNode1t   informativesG   The system version report has been created and is in the log directory.t   infot   hardDrivesMissingFirmwaret   warnings?   Hard drive firmware was missing for the following hard drives: s!   ; make sure to file a bug report.t   componentListDictt   computeNodeListt   errorsn   The compute node's local OS hard drives are not being updated, since firmware for the hard drives was missing.s8   The compute node is already up to date; no action taken.t   hostnames   Phase 2: Updating compute node s'   's hard drives that need to be updated.s#   Phase 2: Updating the compute node so   's components that need to be updated, however, hard drive firmware was missing for the following hard drives: s&   's components that need to be updated.t   targetg¹?t   yt   Softwaret   Driverst   Firmwares   The update of compute node s    completed succesfully, however, the version information file update failed; check the log file for errors and update the file manually.t   externalStoragePresentt   finals   Once the version information file is updated, power cycle the attached storage controller(s) and reboot the system for the changes to take effect.s_   Once the version information file is updated, reboot the system for the changes to take effect.s    completed succesfully.sd   Power cycle the attached storage controller(s) and reboot the system for the changes to take effect.s1   Reboot the system for the changes to take effect.sN   The following components encountered errors during the update of compute node s!   ; check the log file for errors:
t   rpmRemovalFailures
   Software: s   , s   
s	   Drivers: s
   Firmware: sm   Also, the version information file update failed; check the log file for errors and update the file manually.s4   Errors were encountered while updating compute node s6   's hard drive firmware; check the log file for errors.s   Press enter to exit.(E   t   ost   geteuidR   R   t   exitt   optparset   OptionParsert
   add_optiont   Falset
   parse_argst   vt   patht   basenamet   syst   argvt   rt   ut   st   Truet
   subprocesst   Popent   PIPEt   communicatet   stript
   returncodet   ret   matcht
   IGNORECASEt   groupt   replacet   AttributeErrort   strt   datetimet   nowt   strftimet   mkdirt   OSErrorR   t   daemont   startR   t   initt   insertMessaget   lent   getComputeNodeDictR   t   copyt   signalt	   getsignalt   SIGINTt   SIGQUITR   t   signal_handlerR    t   updateComputeNodeComponentst   timet   sleept   is_alivet   getResponset   endTaskt   joint   getUpdateComponentProblemDictR   t   keyst   getUserInputt   isUserInputReadyt	   Exceptiont	   tracebackt	   print_exc(    t   programVersionR   t   parsert   optionst   argst   versionInformationLogOnlyt   updateOSHarddrivest   commandt   resultt   outt   errt   systemModelt   csurBasePatht   currentLogDirt
   logBaseDirt   sessionScreenLogt	   cursesLogt   cursesThreadt
   initializet   csurResourceDictt   timerThreadLocationt   computeNodeDictR   t   computeNodeUpdatet   original_sigint_handlert   original_sigquit_handlerR6   t   workerThreadt   responset   componentProblemDictt"   updateVersionInformationFileResultt   errorMessage(    (    s   ./csurUpdate.pyt   main   s&   
 <




'1#

 	



2#
+


E)%)) 

(   R>   RQ   RW   R2   R'   R*   R8   Rb   RE   t	   threadingR    t   modules.csurUpdateUtilsR   R   R   t   modules.csurUpdateInitializeR   t   modules.computeNodeUpdateR   t    modules.updateReleaseInformationR   t   modules.cursesThreadR   R   (    (    (    s   ./csurUpdate.pyt   <module>   s    	û