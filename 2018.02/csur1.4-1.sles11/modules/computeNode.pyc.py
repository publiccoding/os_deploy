Ñò
"èYc        	   @   sm   d  d k  Z  d  d k Z d  d k Z d  d k Z d  d k l Z d  d k l Z l Z d d d     YZ	 d S(   iÿÿÿÿN(   t#   checkFusionIOFirmwareUpgradeSupport(   t   ComputeNodeInventoryt   Gen1ScaleUpComputeNodeInventoryt   ComputeNodec           B   s5   e  Z d    Z d   Z d   Z d   Z d   Z RS(   c   
      C   s
  | |  _  h  |  _ y |  i  d } Wn' t j
 o } t t |    n X| |  i d <t i   d } | |  i d <| d | d } t i |  } | d |  _ |  i |  i d <t i	 |  i  } | i
 t i  t i d	 d
 d }	 | i |	  | i |  d  S(   Nt
   logBaseDirt   ipi   t   hostnamet   computeNode_s   .logt   Loggert
   loggerNames%   %(asctime)s:%(levelname)s:%(message)st   datefmts   %m/%d/%Y %H:%M:%S(   t   csurResourceDictt   computeNodeDictt   KeyErrort   strt   ost   unamet   loggingt   FileHandlerR	   t	   getLoggert   setLevelt   INFOt	   Formattert   setFormattert
   addHandler(
   t   selfR   R   R   t   errR   t   computeNodeLogt   handlert   loggert	   formatter(    (    s   ./computeNode.pyt   __init__
   s$    		c      !   C   sË  t  i |  i  } h t d 6g  d 6d d 6} d } t i | d t i d t i d t } | i   \ } }	 | i	   } | i
 d	 | d
 |  | i d j o' | i d |	  | d i d  | Sy1 t i d | t i  i d  i d d  }
 WnJ t j
 o> }	 | i d | d t |	  d  | d i d  | SXyC |
 |  i d j o+ | i d |
 d  | d i d  | SWnB t j
 o6 }	 | i d t |	  d  | d i d  | SX| i
 d |
 d  |
 |  i d <d } t i | d t i d t i d t } | i   \ } }	 | i
 d	 | d | i	    | i d j o' | i d  |	  | d i d!  | S| i   } d" | j o d# } d$ } n d% } d& } t i | d t i d t i d t } | i   \ } }	 | i d j o' | i d' |	  | d i d(  | S| i d) d  } | d# j oú y% t i d* | t i  i d  } WnJ t j
 o> }	 | i d+ | d t |	  d  | d i d,  | SXy% t i d- | t i  i d  } WnJ t j
 o> }	 | i d. | d t |	  d  | d i d/  | SX| | d | } n} y% t i d0 | t i  i d  } WnJ t j
 o> }	 | i d1 | d t |	  d  | d i d2  | SX| | } yC | |  i d3 j o+ | i d4 | d  | d i d5  | SWnB t j
 o6 }	 | i d t |	  d6  | d i d  | SX| i
 d7 | d  | |  i d8 <| p/d9 |
 j p d: |
 j obd# | j o
 d; } n d< } | d= } t i | d t i d t i d t } | i   \ } }	 | i
 d	 | d> | i	    | i d j o' | i d? |	  | d i d@  | S| i   } xe | D]] } t i dA |  oD t i dB |  o- | i dC | i	    | d i dD  | SqSqSW| dE } t i | d t i d t i d t } | i   \ } }	 | i	   } | i
 d	 | dF |  | i d j o' | i dG |	  | d i dH  | S| d dI !} yC | |  i dJ j o+ | i dK | dL  | d i dM  | SWqìt j
 o6 }	 | i d t |	  d6  | d i d  | SXn d9 |
 j p dN |
 j p
 d: |
 j p dO } t i | d t i d t i d t } | i   \ } }	 | i
 d	 | dP | i	    | i d j o' | i dQ |  | d i dR  | Sn |
 dS j p |
 dT j oÕdU } t i | d t i d t i d t } | i   \ } }	 | i
 d	 | dV | i	    | i d j o' | i dW |	  | d i dX  | St i dY | t i t i B d  j o# | i dZ  | d i d[  | Sd\ } t i | d t i d t i d t } | i   \ } }	 | i	   } | i
 d	 | d] |  | i d j o' | i d^ |	  | d i d_  | S| i
 d` | d  | |  i da <db } t i | d t i d t i d t } | i   \ } }	 | i	   } | i
 d	 | dc |  | i d j o' | i dd |	  | d i de  | S| i
 df | d  | |  i dg <y4 t |  i dh |  i  p | d i di  | SWqt j
 o6 }	 | i d t |	  d6  | d i d  | SXqn | oJ |
 dj j o< |  i  | |
 |  } | d j o | d i |  | Sn yÃ |
 dS j p |
 dT j o& t! |  i i"   |  i dk |  } n |
 dl j oP dm |  i j o@ |  i dm dn j o, t# |  i i"   |  i dk | dm dn } n# t# |  i i"   |  i dk |  } WnB t j
 o6 }	 | i d t |	  d6  | d i d  | SX| p | i$ |  i i"    n8 | i%   } | d  j o | o | d i do  | S| i&   o | d i dp  | S| i'   o | i(   | d <n | o | S| i)   } | of t* | dq  d j o2 t* | d  d j o | |  i dr <t | d <qÇ| i ds | d d  n® g  } | i+   D] } | t* |  q+~ } t, dt   | D  oi | |  i dr <t | d <| i-   |  i du <dv | dq j o | i.   |  i dw <n | i/   |  i dx <n | S(y   Nt   updateNeededt   errorMessagest    t   hardDrivesMissingFirmwares    dmidecode -s system-product-namet   stdoutt   stderrt   shells   The output of the command (s&   ) used to get the system's model was: i    s.   Unable to get the system's model information.
s-   Unable to get the system's model information.s   [a-z,0-9]+\s+(.*)i   t    sC   There was a system model match error when trying to match against 's   ':
t   .s%   There was a system model match error.t   supportedComputeNodeModelss   The system's model (s'   ) is not supported by this CSUR bundle.s8   The system's model is not supported by this CSUR bundle.s   The resource key (s5   ) was not present in the application's resource file.s%   A resource key error was encountered.s)   The system's model was determined to be: t   systemModels   cat /proc/versions3   ) used to get the OS distribution information was: s@   Unable to get the system's OS distribution version information.
s?   Unable to get the system's OS distribution version information.t   suset   SLESs   cat /etc/SuSE-releaset   RHELs   cat /etc/redhat-releases2   Unable to get the system's OS distribution level.
s1   Unable to get the system's OS distribution level.s   
s   .*version\s*=\s*([1-4]{2})sD   There was SLES OS version match error when trying to match against 's(   There was a SLES OS version match error.s   .*patchlevel\s*=\s*([1-4]{1})sE   There was SLES patch level match error when trying to match against 's)   There was a SLES patch level match error.s!   .*release\s+([6-7]{1}.[0-9]{1}).*sD   There was RHEL OS version match error when trying to match against 's(   There was a RHEL OS version match error.t   supportedDistributionLevelss$   The system's OS distribution level (sH   The system's OS distribution level is not supported by this CSUR bundle.s'   ) was not present in the resource file.s9   The system's OS distribution level was determined to be: t   osDistLevelt   DL380t   DL360s   /opt/cmcluster/bins   /usr/local/cmcluster/bins   /cmviewcl -f line -l clusters/   ) used to check if the cluster is running was: s+   Unable to check if the cluster is running.
s*   Unable to check if the cluster is running.s   ^status=s	   status=ups.   It appears that the cluster is still running.
s-   It appears that the cluster is still running.s
   /cmversions*   ) used to get Serviceguard's version was: s&   Unable to get Serviceguard's version.
s%   Unable to get Serviceguard's version.i   t   supportedServiceguardLevelss$   The current version of Serviceguard s!    is not supported for an upgrade.s5   The current version of Serviceguard is not supported.t   DL320s`   ps -C hdbnameserver,hdbcompileserver,hdbindexserver,hdbpreprocessor,hdbxsengine,hdbwebdispatchers'   ) used to check if SAP is running was: s+   It appears that SAP HANA is still running.
s*   It appears that SAP HANA is still running.t   DL580G7t   DL980G7t   mounts5   ) used to check if the log partition is mounted was: s1   Unable to check if the log partition is mounted.
s0   Unable to check if the log partition is mounted.s   /hana/log|/HANA/IMDB-logs#   The log partition is still mounted.sE   The log partition needs to be unmounted before the system is updated.s   uname -rs-   ) used to get the currently used kernel was: s7   Unable to get the system's current kernel information.
s6   Unable to get the system's current kernel information.s0   The currently used kernel was determined to be: t   kernels   uname -ps5   ) used to get the compute node's processor type was: s+   Unable to get the system's processor type.
s*   Unable to get the system's processor type.s8   The compute node's processor type was determined to be: t   processorTypet   fusionIOFirmwareVersionListsM   The fusionIO firmware is not at a supported version for an automatic upgrade.t   16sx86t   noPMCFirmwareUpdateModelst
   DL380pGen8t   systemGenerations   Gen1.xsS   There are no local hard drives to update, since there were no controllers detected.s<   Errors were encountered during the compute node's inventory.t   Firmwaret   componentUpdateDictsg   The local hard drives are not being updated, since firmware was missing for the following hard drives: c         s   s   x |  ] } | d  j Vq Wd S(   i    N(    (   t   .0t   x(    (    s   ./computeNode.pys	   <genexpr>w  s   	 t   mellanoxBusListt   FusionIOt   busListt   externalStoragePresent(0   R   R   R	   t   Falset
   subprocesst   Popent   PIPEt   Truet   communicatet   stript   infot
   returncodet   errort   appendt   ret   matcht
   IGNORECASEt   groupt   replacet   AttributeErrorR   R   R   R   t   lowert
   splitlinest   searcht   warnt	   MULTILINEt   DOTALLt   NoneR    t   _ComputeNode__checkDriversR   t   copyR   t   getComponentUpdateInventoryt"   getLocalHardDriveFirmwareInventoryt   getInventoryStatust   getHardDriveFirmwareStatust   getHardDrivesMissingFirmwaret   getComponentUpdateDictt   lent   valuest   anyt   getMellanoxBusListt   getFusionIOBusListt   isExternalStoragePresent(   R   t   computeNodeResourcest   versionInformationLogOnlyt   updateOSHarddrivesR   t
   resultDictt   commandt   resultt   outR   R*   t   versionInfot   OSDistt   releaseInfot   slesVersiont   slesPatchLevelR/   t   rhelVersiont	   sgBinPatht   clusterViewt   linet	   sgVersionR7   R8   t   computeNodeInventoryt   hardDrivesLocalR?   t   _[1]t   dictt   componentDictSizes(    (    s   ./computeNode.pyt   computeNodeInitialize7   s°   '1#	'
'%#%#%#
	

' 
'	
''	'&''		&1,&.-
c         C   s  d } t  i |  i  } |  i   \ } } | d  j p | d  j o d } | Sy |  i d } |  i d }	 Wn7 t j
 o+ }
 | i d t |
  d  d } | SXt	 i
 g  } | i d  D] } | | i   qÁ ~  } t	 i
 g  } |	 i d  D] } | | i   qú ~  } d	 } } t i | d
 t i d t i d t } | i   \ } }
 | i d | d | i    | i d j o | i d |
  d } | St	 i
 g  } | i   D] } | | i   d q¾~  } | i d t |   t } t } t } xt| D]l} | i d d  } d | j o | o qqd | j o t } qq| | j o
 | | j o | o qq| | j o | | j o t } qqt i d |  o Pq| i d  } | d } | o | | j o qn | o | | j o qn | | j oW | d j p | d j o | o t } qn | i d | d  d | d } | SqW| S(   NR"   sB   Problems were encountered while checking local storage components.t
   hbaDriverst   localStorageDriverss   The resource key (s'   ) was not present in the resource file.s4   A resource key was not present in the resource file.t   ,s   cat /proc/modulesR$   R%   R&   s   The output of the command (s.   ) used to get the list of loaded drivers was: i    s*   Could not get the list of loaded drivers.
s)   Could not get the list of loaded drivers.s,   The driver dictionary was determined to be: R'   t   Driverss   \s*$t   |t   mlx4_ent   mlnxs   The s%    driver does not appear to be loaded.(   R   R   R	   t   _ComputeNode__checkStorageR]   R   R   RO   R   R   t   fromkeyst   splitRL   RG   RH   RI   RJ   RK   RM   RN   RX   RF   RU   RQ   RR   (   R   Rl   R*   R/   t   errorMessageR   t
   hbaPresentt   localStoragePresentR   R   R   R   RA   t   hbaDriverDictt   _[2]t   localStorageDriverDictRp   Rq   Rr   t   _[3]t   colt
   driverDictt   driversFoundt   startedt   mlnxDriverFoundt   datat   computeNodeDriverListt   computeNodeDriver(    (    s   ./computeNode.pyt   __checkDrivers  sr    99
': #
"	c         C   sì  d  } d  } t i |  i  } | i d  d } t i | d t i d t i d t } | i	   \ } } | i d | d | i
    | i d j o | i d	 |  n7 t i d
 | t i t i B d  j o
 t } n t } d } t i | d t i d t i d t } | i	   \ } } | i d | d | i
    | i d j o | i d |  no t i g  } | i   D] }	 | |	 i   d q~~  }
 | i d t |
   d |
 j o
 t } n t } | i d  | | f S(   Ns&   Checking for local storage components.s   systool -c scsi_host -vR$   R%   R&   s   The output of the command (s)   ) used to check if HBAs are present was: i    s2   Failed to get the compute node's HBA information.
t   HBAt   lsscsis1   ) used to check if local storage is present was: s3   Failed to get the compute node's SCSI information.
i   s(   The SCSI devices were determined to be: t   storages+   Done checking for local storage components.(   R]   R   R   R	   RM   RG   RH   RI   RJ   RK   RL   RN   RO   RQ   RY   R[   R\   RF   R   R   RX   R   R   (   R   R   R   R   Rp   Rq   Rr   R   R   R   t   scsiDict(    (    s   ./computeNode.pyt   __checkStorageé  s4    '&
':
c         C   s   |  i  S(   N(   R   (   R   (    (    s   ./computeNode.pyt   getComputeNodeDict  s    (   t   __name__t
   __module__R   R   R^   R   R¢   (    (    (    s   ./computeNode.pyR   	   s   	-	ÿ X	[	5(    (
   R   R   RG   RQ   t   fusionIOUtilsR    R}   R   R   R   (    (    (    s   ./computeNode.pyt   <module>   s   