��
�IYc           @   s�   d  d k  Z  d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k	 l
 Z
 l Z d  d k l Z d  d k l Z l Z d  d k l Z d  d k l Z d d	 d �  �  YZ d S(
   i����N(   t   TimedProcessThreadt   TimerThread(   t   removeFusionIOPackages(   t   FusionIODriverUpdatet   FusionIOFirmwareUpdate(   t   OneOffs(   t   Serviceguardt   ComputeNodeUpdatec           B   s�   e  Z d  �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z	 d �  Z
 d	 �  Z d
 �  Z d �  Z d �  Z d �  Z d �  Z RS(   c         C   s�   | |  _  | |  _ | |  _ |  i d d d i �  |  _ |  i d |  _ h h  d 6h  d 6h  d 6|  _ |  i d |  _ t i	 |  i d	 � |  _
 d
 |  _ d |  _ t |  _ t |  _ t |  _ t |  _ d
 |  _ g  |  _ d |  _ d  S(   Nt   componentListDictt   computeNodeListi    t   componentUpdateDictt   Firmwaret   Driverst   Softwaret   csurBasePatht
   loggerNamet    s   /etc/infiniband/connectx.conf(   t   cursesThreadt   timerThreadLocationt   csurResourceDictt   getComputeNodeDictt   computeNodeDictR
   t   updateComponentProblemDictR   t   loggingt	   getLoggert   loggert   timedProcessThreadt   pidt   Falset   waitt   cancelt   fusionIODriverUpdateStartedt   fusionIOFirmwareUpdateStartedt   fusionIODriverUpdatet    fusionIOFirmwareUpdateThreadListt   connectXCfgFile(   t   selfR   R   R   (    (    s   ./computeNodeUpdate.pyt   __init__   s"    											c         C   s�  t  d |  i d d � } t | _ | i �  |  i i d | g � d |  i d j o t �  |  _	 n t
 |  i d � d j o |  i �  n t
 |  i d � d j o |  i o |  i �  n t
 |  i d	 � d j o |  i o |  i �  n t
 |  i d
 � d j p t
 |  i d � d j ob |  i oW t |  i � } | i |  i i �  � } | p% |  i i d � d |  i d	 d <q�n | i �  | i �  |  i i d |  i d d |  i � d  S(   Ns   Updating compute node t   hostnames    ... R   t   iomemory_vslR   i    R   R   t
   sgSoftwaret   sgNFSSoftwares/   The Serviceguard upgrade completed with errors.R   s   Done updating compute node t   .(   R   R   t   Truet   daemont   startR   t   insertTimerThreadR
   R   R!   t   lent!   _ComputeNodeUpdate__updateDriversR   t"   _ComputeNodeUpdate__updateFirmwaret"   _ComputeNodeUpdate__updateSoftwareR   R   t   upgradeServiceguardR   t   copyt   errorR   t	   stopTimert   joint   updateTimerThreadR   (   R$   t   timerThreadt   serviceguardt   upgradeCompleted(    (    s   ./computeNodeUpdate.pyt   updateComputeNodeComponentsF   s*    	
%%?

c         C   s�  |  i  d } |  i d } |  i d } |  i d } |  i i d � | d j o' |  i �  p d |  i d d <d  Sn x�| D]�} t i d	 | � i	 d
 � i
 d � } t i d � x |  i o t i d
 � q� W|  i o d  S| d j oBt i d | � o/d } t i | d t i d t i d t �} | i �  \ }	 }
 |  i i d | d |	 i
 �  � | i d j o� |	 i �  }	 d d i |	 � } t i | d t i d t i d t �} | i �  \ }	 }
 |  i i d | d |	 i
 �  � | i d j o, |  i i d |
 � d |  i d | <q q/q3n | d j ojd } t i | d t i d t i d t �} | i �  \ }	 }
 |  i i d | d |	 i
 �  � | i d j o�t i d | � o
 d } n d } t | d  |  i d! � |  _ |  i i �  |  i i �  |  _ |  i i �  } | d } d |  _ | d" j o'|  i i d# � d$ } t i | d t i d t i d t �} | i �  \ }	 }
 |  i i d | d% |	 i
 �  � | i d j o� |	 i
 �  } d& | } t | d  |  i d! � |  _ |  i i �  |  i i �  |  _ |  i i �  } d |  _ | d" j o( |  i i d' � d |  i d | <q qaq�q�| d( j o0 |  i i d) | d
 � d |  i d | <q q�q�n | d* j o� t |  i d+ d, |  i d! � p( |  i i d- � d |  i d | <q n t i  d. d |  i d/ � } | t i  d d | | � } n | | } d0 | } t | d1 |  i d! � |  _ |  i i! t � |  i i �  |  i i �  |  _ |  i i �  } d |  _ | d* j oP d2 |  i d3 j p d* |  i d4 j o( |  i i d5 � d |  i d d* <q n^ | d* j oP | i" �  } d } x+ | D]# } | t i  d6 d | � d 7} q7W| i
 �  } n | d d" j oe| d* j o& |  i i d7 | d8 � d9 | } n# |  i i d7 | d8 � d9 | } t i | d t i d t i d t �} | i �  \ }	 }
 | d* j o. |  i i d | d: | d; |	 i
 �  � n+ |  i i d | d: | d; |	 i
 �  � | i d j o^ | d* j o  |  i i d< | d= |
 � n |  i i d< | d= |
 � d |  i d | <qWq | d d> j ob | d* j o  |  i i d< | d= |
 � n! |  i i d< | d= | d
 � d |  i d | <q q W|  i i d? � d@ |  i j os t# |  i d@ � d j oU |  i d@ } t$ �  } | i% | |  i d! � \ } } | p | |  i d dA <q�q�n d  S(B   Ns   /software/computeNode/R   t   osDistLevelt   systemModelsC   Updating the software that was identified as needing to be updated.t   16sx86R   t   prepareForCS900SoftwareUpdates   (([a-zA-Z]+-*)+)i   t   -i   t   hponcfgs   RHEL6.*s   rpm -q hponcfgt   stdoutt   stderrt   shells   The output of the command (s-   ) used to check if hponcfg is installed was: i    s   rpm -e t    s   ) used to remove hponcfg was: sK   Problems were encountered while trying to remove hponcfg; skipping update.
s	   hp-healths   rpm -q hp-healths/   ) used to check if hp-health is installed was: s   SLES12.*s   systemctl stop hp-healths   /etc/init.d/hp-health stopix   R   t   timedOuts8   hp-health could not be stopped; will try to kill it now.s   pgrep -x hpasmliteds(   ) used to get the PID of hp-health was: s   kill -9 sK   A second attempt to stop hp-health timed out; skipping update of hp-health.t   FailedsW   An error was encountered while trying to stop hp-health; skipping update of hp-health.
t   FusionIOt"   fusionIOSoftwareRemovalPackageListt   softwareso   The FusionIO software could not be removed before updating/re-installing; skipping update of FusionIO software.s   ,\s*t"   fusionIOSoftwareInstallPackageListsG   rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature i�   R'   R   R   s{   The FusionIO software update was skipped due to errors that were encountered during the FusionIO driver or firmware update.s   -[0-9]{1}.*s%   Verifying the installation status of s5   , since it appears it may not of installed correctly.s-   rpm -V --nomtime --nomode --nouser --nogroup s,   ) used to verify the installation status of s     was: s)   Problems were encountered while updating s   .
t	   SucceededsH   Done updating the software that was identified as needing to be updated.t   rpmsToRemovet   rpmRemovalFailure(&   R   R
   R   R   t   infot1   _ComputeNodeUpdate__prepareForCS900SoftwareUpdateR   t   ret   matcht   groupt   stript   timet   sleepR   R   t
   subprocesst   Popent   PIPER+   t   communicatet
   returncodet
   splitlinesR7   R5   R    R   R-   t   getProcessPIDR   t   getCompletionStatusR   R   t   subt	   setDaemont   splitR/   R   t
   removeRPMs(   R$   t   softwareDirt   softwareListR=   R>   RK   t   softwareNamet   commandt   resultt   outt   errt
   statusListt   statust   hpHealthPIDt   updateSoftwareListt   softwarePackaget   fusionIOSoftwarePkgListt   packageNamest   packageRN   t   oneOffst   rpmRemovalList(    (    s   ./computeNodeUpdate.pyt   __updateSoftwarei   s�    	 $ 

 '"'"'"

	'"
	!!

	5 !
'.*   	c         C   s  |  i  d } |  i d } t } |  i d } t i g  } | i d � D] } | | i �  qG ~ � } |  i i	 d � x�| D]�} t
 i d | � i d � i d � }	 |	 | j oOd	 |	 }
 t i |
 d
 t i d t i d t �} | i �  \ } } |  i i	 d |
 d |	 d | i �  � | i d j o� | i �  i d � \ } } |  i i	 d |	 d | � t | � d j o: |  i | � p t } Pn |  i | � p
 t } n Pq�d t | � j o
 d j n o" |  i d g � p
 t } n Pq�qq} q} W|  i i	 d � | S(   NR   R=   t   wbemSoftwaret   ,s    Preparing for a software update.s   (([a-zA-Z]+-*)+)i   RA   s    rpm -q --queryformat=%{release} RC   RD   RE   s   The output of the command (s   ) used to check if s    was installed was: i    R*   s   The revision of s    was determined to be: i3   i4   i7   s   hpsmx-webapps%   Done preparing for a software update.(   R
   R   R+   R   t   dictt   fromkeysRb   RU   R   RP   RR   RS   RT   RX   RY   RZ   R[   R\   t   intt$   _ComputeNodeUpdate__stopWBEMServicesR   t&   _ComputeNodeUpdate__removeWBEMSoftware(   R$   Re   R=   t   successfullyPreparedRv   t   _[1]t   xt   wbemSoftwareDictRK   Rf   Rg   Rh   Ri   Rj   t   revisiont   _(    (    s   ./computeNodeUpdate.pyt   __prepareForCS900SoftwareUpdateN  s<    9 $
'*
$
c   	   
   C   s�  g  } t  } x� | D]� } d | } t i | d t i d t i d t  �} | i �  \ } } |  i i d | d | d | i �  � | i d j o | i	 | � q q Wt
 | � d j o� d	 d
 i | � } t i | d t i d t i d t  �} | i �  \ } } |  i i d | d d
 i | � d | i �  � | i d j o/ |  i i d d
 i | � d | � t } q�n | S(   Ns   rpm -q RC   RD   RE   s   The output of the command (s   ) used to check if s    was installed was: i    s   rpm -e RF   s   ) used to remove s    was: s1   Problems were encountered while trying to remove s   : (   R+   RX   RY   RZ   R[   R   RP   RU   R\   t   appendR/   R7   R5   R   (	   R$   Rv   t   softwareToRemovet   softwareRemovedRK   Rg   Rh   Ri   Rj   (    (    s   ./computeNodeUpdate.pyt   __removeWBEMSoftware�  s&     
'*'3%c      	   C   sT  d d d g } d d d g } d d d g } t  } d | j ox| D]� } d | d } t i | d	 t i d
 t i d t  �} | i �  \ }	 }
 |  i i d | d | d |	 i �  � d | d } t i | d	 t i d
 t i d t  �} | i �  \ }	 }
 d |	 j o' |  i i d | d |	 � t	 } PqG qG Wnd | j o� x�| D]� } d | } t i | d	 t i d
 t i d t  �} | i �  \ }	 }
 |  i i d | d | d |	 i �  � d | } t i | d	 t i d
 t i d t  �} | i �  \ }	 }
 | i
 d j o' |  i i d | d |	 � t	 } PqUqUWnd | j ox�| D]� } d | d } t i | d	 t i d
 t i d t  �} | i �  \ }	 }
 |  i i d | d | d |	 i �  � d | d } t i | d	 t i d
 t i d t  �} | i �  \ }	 }
 d |	 j o' |  i i d | d |	 � t	 } Pq^q^Wn� x� | D]� } d | } t i | d	 t i d
 t i d t  �} | i �  \ }	 }
 |  i i d | d | d |	 i �  � d | } t i | d	 t i d
 t i d t  �} | i �  \ }	 }
 | i
 d j o' |  i i d | d |	 � t	 } Pq_q_W| S(   Nt   hpshdt   sfcbt
   hpmgmtbases
   sblim-sfcbs   tog-pegasust   RHEL6s   service s    stopRC   RD   RE   s   The output of the command (s   ) used to stop s    was: s    statust   runnings/   Problems were encountered while trying to stop s   .
t   RHEL7s   systemctl stop s   systemctl --quiet is-active i    t   SLES11s   /etc/init.d/(   R+   RX   RY   RZ   R[   R   RP   RU   R5   R   R\   (   R$   R=   t   sles11ServicesListt   sles12ServicesListt   rhelServicesListt   servicesStoppedt   serviceRg   Rh   Ri   Rj   (    (    s   ./computeNodeUpdate.pyt   __stopWBEMServices�  sx     '*' 
'*
' '*' 
'*
'	c         C   s�  |  i  d } |  i d } |  i d } |  i d } |  i i d � xw| D]o} t i d � x |  i o t i d � qa W|  i o d  Sd |  _	 | d	 j o0| d
 j p | d j od } t
 i | d t
 i d t
 i d t �} | i �  \ } }	 |  i i d | d | i �  � | i d j o� d } t
 i | d t
 i d t
 i d t �} | i �  \ } }	 |  i i d | d | i �  � | i d j o, |  i i d |	 � d |  i d | <qK q�q�n | d j od } t
 i | d t
 i d t
 i d t �} | i �  \ } }	 |  i i d | d | i �  � | i d j o� d } t
 i | d t
 i d t
 i d t �} | i �  \ } }	 |  i i d | d | i �  � | i d j o, |  i i d |	 � d |  i d | <qK q�q�n | d j o�yk d | j o/ t i d d |  i d  � }
 |
 i d � } n, t i d d |  i d! � }
 |
 i d � } WnG t j
 o; }	 |  i i d" t |	 � d# � d |  i d | <qK n Xg  } xO | D]G } d$ | d% } t
 i | d t �} | d j o | i | � q�q�Wt | � d j o� d i | � }
 d& |
 } t
 i | d t
 i d t
 i d t �} | i �  \ } }	 |  i i d | d' | i �  � | i d j o, |  i i d( |	 � d |  i d | <qK q�q�n | d) j o|  i �  o d |  i d | <qK n |  i �  o d |  i d | <qK n t i i  �  i! d* � } d+ | } y t" i# d, | � Wn@ t$ j
 o4 }	 |  i i d- t |	 � � d |  i d | <n Xt% |  i d. d/ |  i d0 d1 |  i d1 �p( |  i i d2 � d |  i d | <qK qn d3 | | j o | | | } n+ | | } | i& d3 d | � } | | } d4 | } t
 i | d t
 i d t
 i d5 t' i( d t �} | i	 |  _	 | i �  \ } }	 |  i i d | d6 | d7 | i �  � | i d j o4 |  i i d8 | d9 |	 � d |  i d | <qK n_ t i) d: | t i* t i+ Bt i, B� d  j o1 |  i i. d; | d9 | � d |  i d | <n | d) j o� t |  _/ |  i0 i1 |  i i2 �  | |  i d0 � p% |  i i d< � d |  i d | <n t3 |  _/ y t" i# | d, � Wq=t$ j
 o4 }	 |  i i d= t |	 � � d |  i d | <q=Xn | d j op d> | j p d? | j oV t |  i d@ � d j o< t' i4 i5 |  i6 � o& |  i7 �  p d |  i d | <q�qK qK W|  i i dA � d  S(B   Ns   /drivers/computeNode/R   R>   R=   sC   Updating the drivers that were identified as needing to be updated.i   i   i    t   nx_nict   DL580G7t   DL980G7s   rpm -qa|grep ^hpqlgc-nxRC   RD   RE   s   The output of the command (s;   ) used to check if the new nx_nic driver is installed was: s,   rpm -e hp-nx_nic-kmp-default hp-nx_nic-toolss(   ) used to remove the nx_nic driver was: sm   Problems were encountered while trying to remove hp-nx_nic-kmp-default and hp-nx_nic-tools; skipping update.
R   t   be2nets   rpm -q hp-be2net-kmp-defaults;   ) used to check if the old be2net driver is installed was: s   rpm -e hp-be2net-kmp-defaults(   ) used to remove the be2net driver was: sY   Problems were encountered while trying to remove hp-be2net-kmp-default; skipping update.
t   mlx4_ent   SLESs   \s*,\s*RF   t   slesMellanoxPackageListt   rhelMellanoxPackageLists   The resource key (s'   ) was not present in the resource file.s   rpm -q s    > /dev/null 2>&1s   rpm -e s4   ) used to remove the Mellanox conflicting RPMs was: sa   Problems were encountered while trying to remove the Mellanox conflicting RPMs; skipping update.
R'   s   %Y%m%d%H%M%Ss   /etc/sysconfig/iomemory-vsl.s   /etc/sysconfig/iomemory-vslsI   Unable to make a backup of the system's iomemory-vsl configuration file.
t    fusionIODriverRemovalPackageListt   driverR   t   kernels�   The FusionIO driver packages could not be removed before building/re-installing the FusionIO driver; skipping update of FusionIO driver.t   :sG   rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature t
   preexec_fns   ) used to update the 's   ' driver was: s1   Problems were encountered while updating driver 's   '.
t   warnings1   Warnings were encountered while updating driver 'sL   Problems were encountered while building and installing the FusionIO driver.s@   Failed to restore the system's iomemory-vsl configuration file.
s   SLES11.4s   RHEL6.7t   mellanoxBusListsH   Done updating the drivers that were identified as needing to be updated.(8   R   R
   R   R   RP   RV   RW   R   R   R   RX   RY   RZ   R+   R[   RU   R\   R5   R   RR   R`   R   Rb   t   KeyErrort   strt   callR�   R/   R7   t$   _ComputeNodeUpdate__checkIOMemoryVSLt(   _ComputeNodeUpdate__unloadFusionIODrivert   datetimet   nowt   strftimet   shutilt   copy2t   IOErrorR   t   replacet   ost   setpgrpt   searcht	   MULTILINEt   DOTALLt
   IGNORECASEt   Nonet   warnR   R!   t   buildInstallFusionIODriverR4   R   t   patht   existsR#   t"   _ComputeNodeUpdate__updateConnectX(   R$   t	   driverDirt
   driverDictR>   R=   R�   Rg   Rh   Ri   Rj   t   packagest   mellanoxPackageListt   mellanoxRemovalListRr   t   dateTimestampt   iomemoryCfgBackupt   driverRPMListt   driverRPMsStringt   tmpDriverRPMList(    (    s   ./computeNodeUpdate.pyt   __updateDrivers�  s�      

	''"'"'"'" 
'"
.


0*-	)	Wc         C   s-  |  i  d } |  i d } |  i d } d } d } d } |  i i d � |  i �  x�| D]�} t i d � x |  i o t i d	 � qp W|  i	 o d  Sd
 |  _
 | d j o< d |  i d j o( |  i i d � d |  i d | <qZ n4| d j o]|  i �  o d |  i d | <qZ n | | | } |  i d }	 g  }
 t |  _ xE |	 D]= } |  i i t | | |
 |  i d � � |  i d i �  qPWxq t i d � xC t d
 t |  i � � D]) } |  i | i �  p |  i | =Pq�q�Wt |  i � d
 j o Pq�q�t |
 � d
 j o2 |  i i d d i |
 � � d |  i d | <n t |  _ n�t i | | | � o� t i | � d | | d } t i | d t i d t i d t i  d t �} | i
 |  _
 | i! �  \ } } |  i i d | d | d | i" �  � |  i i d t# | i$ � � | i$ d  j o4 |  i i d! | d" | � d |  i d | <qZ q n�| | } d# | | } t i | d t i d t i d t i  d t �} | i
 |  _
 | i! �  \ } } |  i i d | d | d | i" �  � | i$ d
 j o4 |  i i d! | d" | � d |  i d | <qZ n | i% d$ � o$ d% } | | d
 | i& d& � !} n! d' } | | d
 | i& d( � !} t i | � | d) } t i' i( | � o! d* | j o
 d+ } q�d, } n d* | j o
 d- } n d. } t i | d t i d t i d t i  d t �} | i
 |  _
 | i! �  \ } } |  i i d | d | d | i" �  � |  i i d t# | i$ � � | i$ d  j o� t i) d/ | t i* t i+ Bt i, B� d  j o4 |  i i d! | d" | � d |  i d | <qZ q |  i i d0 | d1 | � n | | j o� t i d2 | � o� d3 } t i | d t i d t i d t �} | i! �  \ } } |  i i d | d4 | i" �  � | i$ d
 j o) |  i i d5 | � d6 |  i d | <qt i) | | t i* t i+ B� d  j o |  i. | � qqZ qZ W|  i i d7 � d  S(8   Ns   /firmware/computeNode/R   R=   t   BIOSDL580Gen8s	   .*\.scexes   em49|em50|em51|em52sD   Updating the firmware that were identified as needing to be updated.i   i   i    RI   R'   R   so   The FusionIO firmware update was skipped due to errors that were encountered during the FusionIO driver update.R   t   busListR   i����g      �?sP   Problems were encountered while updating the FusionIO firmware for the IODIMMS: RF   s   ./s    -f -sRC   RD   R�   RE   s   The output of the command (s   ) used to update the firmware s    was: s5   The return code from the smart component update was: i   s2   Problems were encountered while updating firmware s   .
sG   rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature s
   x86_64.rpms   /usr/lib/x86_64-linux-gnu/s   .x86_64.rpms   /usr/lib/i386-linux-gnu/s	   .i386.rpms   /hpsetupt   mellanoxs   ./hpsetup -ss   ./hpsetup -f -ss   ./.hpsetup -ss   ./.hpsetup -f -ssK   All selected devices are either up-to-date or have newer versions installeds   A firmware update of s,    was not done due to the following reason: 
s   SLES.*s   ifconfig -asn   ) used to get the list of NIC interfaces for checking if renaming is needed as a result of a bios update was: s�   Problems were encountered while getting the list of NIC interfaces for checking if renaming is needed as a result of a bios update.
s   Network name update failure.sI   Done updating the firmware that were identified as needing to be updated.(/   R   R
   R   R   RP   t#   _ComputeNodeUpdate__bringUpNetworksRV   RW   R   R   R   R   R5   R�   R+   R    R"   R�   R   R-   t   rangeR/   t   isAliveR7   R   RR   RS   R�   t   chdirRX   RY   RZ   R�   R[   RU   R�   R\   t   endswitht   indexR�   t   isfileR�   R�   R�   R�   R�   t*   _ComputeNodeUpdate__updateNICConfiguration(   R$   t   firmwareDirt   firmwareDictR=   t   biosReferencet   regext   nicRegext   firmwaret   firmwareImageR�   t!   fusionIOFirmwareUpdateFailureListt   bust   iRg   Rh   Ri   Rj   t   rpmt   firmwareRPMDirt   setupDirt	   setupFile(    (    s   ./computeNodeUpdate.pyt   __updateFirmware�  s�    
  

	!	 & 
	0*
0*



0*-  '"&c         C   s�  d } g  } d } t  i | d t  i d t  i d t �} | i �  \ } } |  i i d | d | i �  � | i d j o |  i i	 d	 | � d  S| i
 �  } x^ | D]V } t i d
 | � o= t i d | � }	 |	 d  j o | i |	 i d � � q� q� q� Wx� | D]� }
 d |
 d t | � d } t  i | d t  i d t  i d t �} | i �  \ } } |  i i d | d |
 d | i �  � | i d j o  |  i i	 d |
 d | � n | d 7} q
Wd  S(   Ni   s   ip link showRC   RD   RE   s   The output of the command (sC   ) used to get the information for the NIC cards that are down was: i    sY   Problems were encountered while getting the information for the NIC cards that are down.
t   DOWNs8   [0-9]{1,2}:\s+(eth[0-9]{1,}|em[0-9]{1,}|(p[0-9]{1,}){2})s	   ifconfig s    10.1.1.s   /32  ups   ) used to bring up NIC card s    was: s5   Problems were encountered while bringing up NIC card s   .
(   RX   RY   RZ   R+   R[   R   RP   RU   R\   R5   R]   RR   R�   RS   R�   R�   RT   R�   (   R$   t   countt   nicDownListRg   Rh   Ri   Rj   t   nicDataListt   dataRS   t   nic(    (    s   ./computeNodeUpdate.pyt   __bringUpNetworks�  s2    '" " '* c         C   s:  h d d 6d d 6d d 6d d 6} d	 } d
 } t  i | d t  i d t  i d t �} | i �  \ } } |  i i d | d | i �  � | i d j o d |  i	 d | <d  S| i
 �  } xx| D]p} y9 t | � i i �  }	 z |	 ~	 }
 |
 i �  } Wd  QXWnI t j
 o= } |  i i d | d t | � � d |  i	 d | <d  SXd | j o� | i d � } | d d | | d } d | d | } t  i | d t  i d t  i d t �} | i �  \ } } | i d j o2 |  i i d | d | � d |  i	 d | <d  Sq� q� t i | | t i t i B� d  j o� | i
 �  } xc | D][ } d } xL | D]D } | | j o' t i | | | | � } | | | <n | d 7} qcWqPWy) t | d � }
 |
 i d i | � � WnI t j
 o= } |  i i d | d t | � � d |  i	 d | <d  SX|
 i �  q� q� Wd  S(   Nt   em0t   em49t   em1t   em50t   em2t   em51t   em3t   em52s   em49|em50|em51|em52s+   ls /etc/sysconfig/network/ifcfg-{bond*,em*}RC   RD   RE   s   The output of the command (sE   ) used to get the list of network configuration files to update was: i    s*   Network configuration file update failure.R   sC   Problems were encountered while reading network configuration file s   .
t   emRA   i   s   mv RF   sQ   Problems were encountered while updating (moving) the network configuration file t   ws   
sS   Problems were encountered while writing out the updated network configuration file (   RX   RY   RZ   R+   R[   R   RP   RU   R\   R   R]   t   opent   __exit__t	   __enter__t   readR�   R5   R�   Rb   RR   R�   R�   R�   R�   R`   t   writeR7   t   close(   R$   R�   t   emDictR�   Rg   Rh   Ri   Rj   t   fileR~   t   ft   nicDatat   tmpListt   newFileR�   R�   R�   R�   (    (    s   ./computeNodeUpdate.pyt   __updateNICConfiguration�  sb    "'" #"'&  "c         C   s  |  i  i d � |  i o |  i i �  |  _ n |  i ov x� t d t |  i	 � � D]U } |  i	 | i �  } y& t
 i | � } t
 i | t i � WqS t j
 o qS XqS WnT |  i d j oC y) t
 i |  i � } t
 i | t i � Wqt j
 o qXn t |  _ t |  _ d  S(   Ns*   The CSUR update was cancelled by the user.i    (   R   RP   R   R!   t   getUpdatePIDR   R    R�   R/   R"   R�   t   getpgidt   killpgt   signalt   SIGKILLt   OSErrorR+   R   R   R   (   R$   R�   R   t   pgid(    (    s   ./computeNodeUpdate.pyt   endTask�  s(    

 		c         C   s   |  i  S(   N(   R   (   R$   (    (    s   ./computeNodeUpdate.pyt   getUpdateComponentProblemDict  s    c      
   C   s�  t  } d } d | } t i | d t i d t i d t i d t �} | i �  \ } } | i d j o�d | j o' |  i	 i
 d	 | d
 | � t } d  S|  i	 i d | d � d | } t i | d t i d t i d t i d t �} | i �  \ } } | i �  } |  i	 i d | d | d | � t | � d j o d | d | } n d | } |  i	 i d | d | d � t i | d t i d t i d t �} | i �  \ } } | i d j o& |  i	 i
 d	 | d
 | � t } q�n d  S(   Ns   /etc/sysconfig/iomemory-vsls   egrep '^\s*ENABLED=1' RC   RD   R�   RE   i    s   No such files1   Problems were encountered while trying to update s   .
s	   Updating sG   , since it is not currently enabled for use by /etc/init.d/iomemory-vsls   egrep 'ENABLED=' s   The output of the command s    used to check ENABLED= in s    was:
s
   sed -i 's/s   /ENABLED=1/' s   sed -i '0,/^$/s/^$/ENABLED=1/' s   The command used to update s    was: R*   (   R   RX   RY   RZ   R�   R�   R+   R[   R\   R   R5   RP   RU   R/   (   R$   t   checkFailuret   fusionIOConfigurationFilet   cmdRh   Ri   Rj   t   enabledCurrent(    (    s   ./computeNodeUpdate.pyt   __checkIOMemoryVSL!  s2    
0
0$
 'c      
   C   sK  t  } d } t i | d t i d t i d t i d t �} | i �  \ } } |  i i	 d | d | i
 �  � | i d j o |  i i d	 | � t } n� d
 | j o� d } t i | d t i d t i d t i d t �} | i �  \ } } |  i i	 d | d | i
 �  � | i d j o |  i i d | � t } qGn | S(   Ns   /etc/init.d/iomemory-vsl statusRC   RD   R�   RE   s   The output of the command (s7   ) used to check if the FusionIO driver is running was: i    sI   Problems were detected while checking if the FusionIO driver is running:
s
   is runnings   /etc/init.d/iomemory-vsl stops5   ) used to stop the FusionIO driver from running was: s;   Problems were detected while stopping the FusionIO driver:
(   R   RX   RY   RZ   R�   R�   R+   R[   R   RP   RU   R\   R5   (   R$   t   unloadFailureRg   Rh   Ri   Rj   (    (    s   ./computeNodeUpdate.pyt   __unloadFusionIODriverQ  s"    0"
0"c         C   s�   t  i  i �  i d � } |  i d | } y t i |  i | � Wn& t j
 o } d |  i d GHt SXzp yC t |  i d � } x* |  i	 d D] } | i
 d | d � q� WWn& t j
 o } d |  i d	 GHt SXWd  | i �  Xt S(
   Ns   %Y%m%d%H%M%SR*   s   Unable to make a backup of R�   R�   s   connectx_port_config -d s    -c eth,eth
s   Unable to update s&    with the Mellanox port configuration.(   R�   R�   R�   R#   R�   t   moveR�   R   R�   R   R�   R�   R+   (   R$   R�   t   connectXCfgBackupRj   R�   R�   (    (    s   ./computeNodeUpdate.pyt   __updateConnectXr  s$      
(   t   __name__t
   __module__R%   R<   R2   RQ   R|   R{   R0   R1   R�   R�   R  R  R�   R�   R�   (    (    (    s   ./computeNodeUpdate.pyR      s   	0	#	�	7	 	T	�	�	+	F	#			0	!(    (   RX   R�   RR   RV   R   t	   threadingR�   R�   R  t   csurUpdateUtilsR    R   t   fusionIOUtilsR   t   fusionIOUpdateR   R   Rs   R   R:   R   R   (    (    (    s   ./computeNodeUpdate.pyt   <module>   s   