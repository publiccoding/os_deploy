Ñò
·IYc           @   sm   d  d k  Z  d  d k Z d  d k Z d  d k Z d  d k l Z d d d     YZ d e f d     YZ d S(   iÿÿÿÿN(   t   Threadt   FusionIODriverUpdatec           B   s#   e  Z d    Z d   Z d   Z RS(   c         C   s   d |  _  d  S(   Ni    (   t   pid(   t   self(    (    s   ./fusionIOUpdate.pyt   __init__   s    c         C   s®  t  } d |  _ t i |  } | i d  y& | d d d i   } | d } Wn6 t j
 o* } | i d t |  d  t	 } n X| oÈ | d }	 | d	 }
 | d
 | } d | } t
 i | d t
 i d t
 i d t i d t  } | i |  _ | i   \ } } | i d | d | i    | i d j o | i d |  t	 } qYn | o=| i   } | i d d |	  i d |
  } t i d | d t i  } | i d | i  t i | |  i d  } | i d |  d | d | d } t
 i | d t
 i d t
 i d t i d t  } | i |  _ | i   \ } } | i d | d | i    | i d j o | i d |  t	 } qn | i d   | S(!   Ni    s,   Building and installing the FusionIO driver.t   componentListDictt   computeNodeListt   fusionIODriverSrcRPMs   The resource key (s*   ) was not present in the csurResourceDict.t   kernelt   processorTypes   src/s   rpmbuild --rebuild t   stdoutt   stderrt
   preexec_fnt   shells   The output of the command (s)   ) used to build the FusionIO driver was: s%   Failed to build the FusionIO driver:
s   iomemory-vsls   -vsl-t   srcs    .*Wrote:\s+((/[0-9,a-z,A-Z,_]+)+t   )s<   The regex used to get the FusionIO driver RPM location was: i   s)   The FuionIO driver was determined to be: s	   rpm -ivh t    s   libvsl-*.rpms+   ) used to install the FusionIO driver was: s'   Failed to install the FusionIO driver:
s1   Done building and installing the FusionIO driver.(   t   TrueR   t   loggingt	   getLoggert   infot   getComputeNodeDictt   KeyErrort   errort   strt   Falset
   subprocesst   Popent   PIPEt   ost   setpgrpt   communicatet   stript
   returncodet   replacet   ret   compilet   DOTALLt   patternt   matcht   group(   R   t   csurResourceDictt	   driverDirt   computeNodeLoggert   updateStatust   loggert   computeNodeDictR   t   errR   R	   t   fusionIODriverSrcRPMPatht   commandt   resultt   outt   fusionIODriverRPMt   fusionIODriverPatternt	   driverRPM(    (    s   ./fusionIOUpdate.pyt   buildInstallFusionIODriver   sN    	


0"0c         C   s   |  i  S(   N(   R   (   R   (    (    s   ./fusionIOUpdate.pyt   getUpdatePIDf   s    (   t   __name__t
   __module__R   R7   R8   (    (    (    s   ./fusionIOUpdate.pyR      s   		Rt   FusionIOFirmwareUpdatec           B   s#   e  Z d    Z d   Z d   Z RS(   c         C   sG   t  i |   t i |  |  _ | |  _ | |  _ | |  _ d |  _ d  S(   Ni    (	   R    R   R   R   R-   t   bust   firmwareImaget   updateFailureListR   (   R   R<   R=   R>   R+   (    (    s   ./fusionIOUpdate.pyR   q   s    			c      
   C   s  |  i  i d |  i d  d |  i d |  i } t i | d t i d t i d t i d t	 } | i
 |  _
 | i   \ } } |  i  i d	 | d
 |  i d | i    | i d j o6 |  i  i d |  i d |  |  i i |  i  n |  i  i d |  i d  d  S(   Ns*   Updating the FusionIO firmware for IODIMM t   .s   fio-update-iodrive -y -f -s R   R
   R   R   R   s   The output of the command (s2   ) used to update the FusionIO firmware for IODIMM s    was: i    s3   Failed to upgrade the FusionIO firmware for IODIMM s   :
s/   Done updating the FusionIO firmware for IODIMM (   R-   R   R<   R=   R   R   R   R   R   R   R   R   R    R!   R   R>   t   append(   R   R1   R2   R3   R/   (    (    s   ./fusionIOUpdate.pyt   run   s    0-c         C   s   |  i  S(   N(   R   (   R   (    (    s   ./fusionIOUpdate.pyR8      s    (   R9   R:   R   RA   R8   (    (    (    s   ./fusionIOUpdate.pyR;   p   s   		(    (   R   R   R#   R   t	   threadingR    R   R;   (    (    (    s   ./fusionIOUpdate.pyt   <module>   s   e