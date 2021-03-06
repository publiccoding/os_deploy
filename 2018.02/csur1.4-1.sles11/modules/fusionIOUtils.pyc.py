Ñò
·IYc           @   s:   d  d k  Z  d  d k Z d  d k Z d   Z d   Z d S(   iÿÿÿÿNc      
   K   s  t  i |  } d } d | j o | d } n t } | i d | d  t i d d |   }  |  i d  } g  } xÃ | D]» }	 d |	 }
 t i |
 d t i	 d	 t i	 d
 t } | i
   \ } } | i d |
 d |	 d | i    | i d j o( | i d | d |	 d |  q| q| | i | i    q| Wt |  d j o¨ d i |  } d | }
 t i |
 d t i	 d	 t i	 d
 t } | i
   \ } } | i d |
 d | i    | i d j o# | i d | d |  t } qön | i d | d  | S(   Nt    t   kernels   Removing FusionIO s
    packages.s   \s+t   ,s   rpm -qa t   stdoutt   stderrt   shells   The output of the command (s/   ) used to get the currently installed FusionIO s    package was: i    s   Failed to verify if the s
    package 's   ' was installed.
t    s   rpm -e sB   ) used to remove the currently installed FusionIO package(s) was: s>   Problems were encountered while trying to remove the FusionIO s    packages.
s   Done removing FusionIO (   t   loggingt	   getLoggert   Truet   infot   ret   subt   splitt
   subprocesst   Popent   PIPEt   communicatet   stript
   returncodet   errort   extendt
   splitlinest   lent   joint   False(   t   packageListt   typet   computeNodeLoggert   kwargst   loggerR   t   removalStatust   fusionIOPackageListt   packageRemovalListt   packaget   commandt   resultt   outt   errt   packages(    (    s   ./fusionIOUtils.pyt   removeFusionIOPackages   s<     
''!
'c         C   sN  t  i |  } t } | i d  d } t i | d t i d t i d t } | i   \ } } | i d | d | i    | i	 d j o | i
 d	 |  t } n | i   } x | D]{ }	 |	 i   }	 d
 |	 j oY t i d |	  i d  }
 | i d |
 d  |
 |  j o | i
 d  t } Pq9q¾ q¾ q¾ W| i d  | S(   Ns\   Checking to see if the FusionIO firmware is at a supported version for an automatic upgrade.s
   fio-statusR   R   R   s   The output of the command (s5   ) used to get the FusionIO firmware information was: i    sm   Failed to get the FusionIO status information needed to determine the FusionIO firmware version information.
t   Firmwares   Firmware\s+(v.*),i   s2   The ioDIMM firmware version was determined to be: t   .sM   The fusionIO firmware is not at a supported version for an automatic upgrade.s_   Done checking to see if the FusionIO firmware is at a supported level for an automatic upgrade.(   R   R   R	   R
   R   R   R   R   R   R   R   R   R   R   t   matcht   group(   t   fusionIOFirmwareVersionListt
   loggerNameR   t   automaticUpgradeR#   R$   R%   R&   t   fioStatusListt   linet   firmwareVersion(    (    s   ./fusionIOUtils.pyt#   checkFusionIOFirmwareUpgradeSupportG   s0    '
 	(   R   R   R   R(   R3   (    (    (    s   ./fusionIOUtils.pyt   <module>   s   		;