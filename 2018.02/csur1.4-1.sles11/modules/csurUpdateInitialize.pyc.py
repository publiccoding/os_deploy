Ñò
·IYc        	   @   sc   d  d k  Z  d  d k Z d  d k Z d  d k Z d  d k Z d  d k l Z d d d     YZ d S(   iÿÿÿÿN(   t   GetComponentInformationt
   Initializec           B   s,   e  Z d    Z d   Z d   Z d   Z RS(   c         C   s   h  |  _  | |  _ d  S(   N(   t   csurResourceDictt   cursesThread(   t   selfR   (    (    s   ./csurUpdateInitialize.pyt   __init__   s    	c         C   s1  d | } t  |  } d } t  |  } d } t  |  } d } t  |  }	 d d d d }
 d | d	 d | d } d | d	 d | d } d | d	 d | d } d | d	 d |	 d } d d d d } |
 | | | | | g } x$ | D] } |  i i d
 | g  q÷ W|  i i d
 d g  d  S(   Ns   Version s    SAP HANA CSUR Update Applications   Bill Neumann - SAP HANA CoEs<   (c) Copyright 2016 Hewlett Packard Enterprise Development LPt   +t   -iA   t   |t    t   infot    (   t   lenR   t   insertMessage(   R   t   programVersiont   versiont   versionLengtht   titlet   titleLengtht   authort   authorLengtht	   copyrightt   copyrightLengtht   welcomeMessageTopt   welcomeMessageTitlet   welcomeMessageVersiont   welcomeMessageAuthort   welcomeMessageCopyrightt   welcomeMessageBottomt   welcomMessageContainert   line(    (    s   ./csurUpdateInitialize.pyt   __printHeader   s&    
 c         C   s  | |  i  d <|  i |  | o |  i i d d g  n |  i i d d g  | d } yÓ t |  i i   } z³ | ~ } x£ | D] }	 |	 i   }	 t i	 d d |	  }	 t
 |	  d j p& t i d	 |	  p t i d
 |	  o q q |	 i d  \ }
 } |
 i   }
 | i   |  i  |
 <q WWd  QXWn* t j
 o } |  i d | d  n X| |  i  d <y |  i  d } Wn8 t j
 o, } |  i d t |  d | d  n X| | } t i |  } t i d  } | i t i  t i d d d } | i |  | i |  | d } t i |  } t i d  } | i t i  | i |  t |  i  |  i  } | i | |  } | |  i  d <|  i  S(   Nt   csurBasePatht   informatives6   Phase 1: Collecting system version information report.s,   Phase 1: Initializing for the system update.s"   /resourceFiles/csurAppResourceFiles   ['"]R   i    s   ^\s*#s   ^\s+$t   =s5   Unable to open the csur application's resource file (sH   ) for reading; fix the problem and try again; exiting program execution.t
   logBaseDirt   mainApplicationLogs   The resource key (s5   ) was not present in the application's resource file s;   ; fix the problem and try again; exiting program execution.t   mainApplicationLoggers%   %(asctime)s:%(levelname)s:%(message)st   datefmts   %m/%d/%Y %H:%M:%Ss   versionInformationLog.logt   versionInformationLogt   componentListDict(   R   t   _Initialize__printHeaderR   R   t   opent   __exit__t	   __enter__t   stript   ret   subR   t   matcht   splitt   IOErrort   _Initialize__exitOnErrort   KeyErrort   strt   loggingt   FileHandlert	   getLoggert   setLevelt   INFOt	   Formattert   setFormattert
   addHandlerR    t   getComponentInformation(   R   R    R#   R   t   versionInformationLogOnlyt   updateOSHarddrivest   csurAppResourceFilet   _[1]t   fR   t   keyt   valt   errR$   t   mainApplicationHandlert   loggert	   formatterR'   t   versionInformationHandlert   versionInformationLoggerR>   R(   (    (    s   ./csurUpdateInitialize.pyt   init9   sP    
# 9!(

c         C   s>   |  i  i d | g  t i d  |  i  i   t d  d  S(   Nt   errorg      @i   (   R   R   t   timet   sleept   joint   exit(   R   t   message(    (    s   ./csurUpdateInitialize.pyt   __exitOnError   s    (   t   __name__t
   __module__R   R)   RL   R3   (    (    (    s   ./csurUpdateInitialize.pyR      s   			"	N(    (   R6   t   ost
   subprocessR.   RN   t   collectComponentInformationR    R   (    (    (    s   ./csurUpdateInitialize.pyt   <module>   s   