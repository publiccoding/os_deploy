��
�IYc           @   s]   d  d k  Z  d  d k Z d  d k Z d  d k Z d f  d �  �  YZ d e f d �  �  YZ d S(   i����Nt   ComputeNodeInventoryc           B   s�   e  Z d  �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z	 d �  Z
 d	 �  Z d
 �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z d �  Z RS(   c         K   s`  | d |  _  | d |  _ | |  _ | |  _ d | j o. |  i  d j o | d d j o d |  _ n
 d |  _ t |  _ | d } | d	 } t i | � |  _	 t i d
 � |  _
 |  i
 i d i d | d � d � t |  _ t |  _ g  |  _ t |  _ t |  _ h  |  _ h h  d 6h  d 6g  d 6g  d 6g  d 6|  _ g  |  _ d |  _ d |  _ d |  _ d  S(   Nt   systemModelt   osDistLevelt   systemGenerationt
   DL380pGen8s   Gen1.xt   iLODL380pGen8t   iLOt
   loggerNamet   hostnamet   versionInformationLogs   {0:40}s%   Version information for Compute Node t   :s   
t   Firmwaret   Driverst   Softwaret
   sgSoftwaret   sgNFSSoftwaret   FAILt   PASSt   WARNING(   R   R   t   noPMCFirmwareUpdateModelst   computeNodeResourcest   iLOFirmwareTypet   Falset   externalStoragePresentt   loggingt	   getLoggert   loggert   versionInformationLoggert   infot   formatt   inventoryErrort   hardDriveFirmwareMissingt   hardDrivesMissingFirmwaret
   hbaPresentt   localStoragePresentt   firmwareDictt   componentUpdateDictt   mellanoxBusListt   notVersionMatchMessaget   versionMatchMessaget   versionMatchWarningMessage(   t   selft   computeNodeDictR   R   t   kwargsR   R   (    (    s   ./computeNodeInventory.pyt   __init__
   s0    		.		

%						,			c         C   s�   t  } |  i i d � x� |  i D]� } | i d d � } t i d | � o | o q  q  t i d | � o t } q  q  t i d | � o Pq  | i d � } | d | d g |  i	 | d	 <q  W|  i i d
 t
 |  i	 � d � |  i i d � d  S(   Ns    Getting the firmware dictionary.t    t    s
   Firmware.*s   \s*$t   |i   i   i    s7   The firmware dictionary contents was determined to be: t   .s%   Done getting the firmware dictionary.(   R   R   R   R   t   replacet   ret   matcht   Truet   splitR#   t   str(   R)   t   startedt   datat   firmwareList(    (    s   ./computeNodeInventory.pyt   __getFirmwareDictQ   s     
 #!c      	   C   s�  y` | d d | d } | d } | d } | d } | d } | d } | d	 } | d
 }	 Wn: t  j
 o. }
 t i d t |
 � d � t |  _ d  SXd } d } d } d } d } d } d } d } |  i �  |  i i d i	 d � d � |  i i d i	 | | | | � � |  i i d i	 | | | | � � |  i
 d j o% |  i �  d j o |  i �  qmn |  i | | � |  i �  |  i �  |  i
 d j o� |  i i d d i	 d � d � |  i i d i	 | | | | � � |  i i d i	 | | | | � � |  i | | � |  i �  n |  i i d d i	 d � d � |  i i d i	 | | | | � � |  i i d i	 | | | | � � |  i | | | |	 � |  i �  d  S(   Nt   csurBasePaths   /resourceFiles/t
   pciIdsFilet   nicListt   sgSoftwareListt   sgNFSSoftwareListt
   hbaDriverst   hbaSoftwaret   localStorageDriverst   localStorageSoftwares   The resource key (s'   ) was not present in the resource file.t	   Components	   ---------s   CSUR Versions   ------------s   Current Versions   ---------------t   Statuss   ------s   {0:40}s   Firmware Versions:s   
s   {0:40} {1:25} {2:25} {3}t   16sx86t   Presents   Driver Versions:s   Software Versions:(   t   KeyErrorR   t   errorR6   R4   R   t&   _ComputeNodeInventory__getFirmwareDictR   R   R   R   t&   _ComputeNodeInventory__getLocalStoraget2   _ComputeNodeInventory__getStorageFirmwareInventoryt.   _ComputeNodeInventory__getNICFirmwareInventoryt1   _ComputeNodeInventory__getCommonFirmwareInventoryt(   _getComputeNodeSpecificFirmwareInventoryt)   _ComputeNodeInventory__getDriverInventoryt&   _getComputeNodeSpecificDriverInventoryt+   _ComputeNodeInventory__getSoftwareInventoryt(   _getComputeNodeSpecificSoftwareInventory(   R)   t   csurResourceDictR<   R=   R>   R?   R@   RA   RB   RC   t   errt   componentHeadert   componentUnderLinet   csurVersionHeadert   csurVersionUnderLinet   currentVersionHeadert   currentVersionUnderLinet   statusHeadert   statusUnderLine(    (    s   ./computeNodeInventory.pyt   getComponentUpdateInventoryp   sT    





	
""

!""!""c         C   sX   d  } |  i �  d j o |  i �  t } |  i �  n |  i �  d j o
 t } n | S(   NRG   t   Absent(   t   NoneRK   RJ   R4   t;   _ComputeNodeInventory__getLocalOSHardDriveFirmwareInventoryR   (   R)   t   hardDrivesLocal(    (    s   ./computeNodeInventory.pyt"   getLocalHardDriveFirmwareInventory�   s    

c         C   sQ  |  i  i d � t i i d � o
 d } nX t i i d � o
 d } n; t i i d � o
 d } n |  i  i d � t |  _ d  S| d } t i	 | d t i
 d t i
 d	 t �} | i �  \ } } |  i  i d
 | d | i �  � | i d j o" |  i  i d | � t |  _ d  St i d | t i t i B� } |  i  i d t | � d � g  } x�| D]�} | i �  d }	 | i �  d }
 |  i |	 d } | d |
 d } t i	 | d t i
 d t i
 d	 t �} | i �  \ } } |  i  i d
 | d | i �  � | i d j o" |  i  i d | � t |  _ d  St i d | t i t i B� i d � } |  i  i d | d � | | j o] |  i |	 d d j oE |  i |	 d |  i d |	 <|  i i d i |	 | | |  i � � n& |  i i d i |	 | | |  i � � |	 d j p |	 d j o�|  i d j o |  i d d } d } n |  i d d } d } t |  _ | d |
 d  } t i	 | d t i
 d t i
 d	 t �} | i �  \ } } |  i  i d
 | d! | i �  � | i d j o" |  i  i d" | � t |  _ d  St i d# | t i t i B� i d � } |  i  i d$ | d � | | j o] |  i | d d j oE |  i | d |  i d | <|  i i d i | | | |  i � � q�|  i i d i | | | |  i � � n | d |
 d% } t i	 | d t i
 d t i
 d	 t �} | i �  \ } } |  i  i d
 | d& | i �  � | i d j o" |  i  i d' | � t |  _ d  St i d( | t i t i B� } |  i  i d) t | � d � x= | D]5 } | i �  } | d d* | d+ } | i | � q�WqeW| i �  |  i  i d, t | � d � g  } d } x� | D]x } | i �  } | d j o) | i | d � | d } | d 7} q<| d | j o | i | d � | d } q<q<W|  i  i d- t | � � xh| D]`} t  } y |  i | d } WnG t! j
 o; |  i  i d. | d/ � t |  _" |  i# i | � q�n Xx� | D]� } | i �  } | d | j o� | d } |  i  i d0 | d � | | j od |  i | d d j oL |  i | d |  i d | <|  i i d i | | | |  i � � t } PqqKqKW| p) |  i i d i | | | |  i � � q�q�W|  i  i d1 � d  S(2   Ns'   Getting the storage firmware inventory.s   /usr/sbin/ssaclis   /usr/sbin/hpssaclis   /usr/sbin/hpacuclis=   There is no Smart Storage Administration software installed.
s    ctrl all showt   stdoutt   stderrt   shells   The output of the command (s3   ) used to get the list of storage controllers was: i    s/   Failed to get the list of storage controllers.
s   P\d{3}i*\s+in\s+Slot\s+\d{1}s*   The controller list was determined to be: R0   i����s    ctrl slot=s    shows<   ) used to get the storage controllers firmware version was: s"   .*Firmware Version:\s+(\d+\.\d+).*i   s8   The controller's firmware version was determined to be: R`   R   s   {0:40} {1:25} {2:25} {3}t   P812t   P431t	   DL580Gen9t   D2700t   D3700s    enclosure all show detailsF   ) used to get the storage controllers enclosure firmware version was: s/   Failed to get the storage contoller's details.
s&   .*Firmware Version:\s+(\d+\.\d+|\d+).*sB   The controller's enclosure firmware version was determined to be: s    pd all show detailsB   ) used to get the hard drive list and their firmware version was: s#   Failed to get hard drive versions.
s�   Firmware\s+Revision:\s+[0-9A-Z]{4}\s+Serial\s+Number:\s+[0-9A-Z]+\s+WWID:\s+[0-9A-F]+\s+Model:\s+HP\s+[0-9A-Z]+|Firmware\s+Revision:\s+[0-9A-Z]{4}\s+Serial\s+Number:\s+[0-9A-Z]+\s+Model:\s+HP\s+[0-9A-Z]+s/   The hard drive data list was determined to be: R-   i   s*   The hard drive list was determined to be: s-   The hard drive models were determined to be: s"   Firmware for the hard drive model s!    is missing from the csur bundle.s8   The hard drive's firmware version was determined to be: s,   Done getting the storage firmware inventory.($   R   R   t   ost   patht   isfileRI   R4   R   t
   subprocesst   Popent   PIPEt   communicatet   stript
   returncodeR2   t   findallt	   MULTILINEt   DOTALLR6   R5   R#   R3   t   groupR$   R   R   R&   R'   R   R   t   appendt   sortR   RH   R   R    (   R)   t   arrayCfgUtilFilet   commandt   resultt   outRU   t   controllerListt   hardDriveListt
   controllert   controllerModelt   controllerSlott   csurControllerFirmwareVersiont"   installedControllerFirmwareVersiont   csurEnclosureFirmwareVersiont	   enclosuret!   installedEnclosureFirmwareVersiont   hardDriveDataListt	   hardDrivet   hardDriveDatat   hardDriveVersiont   hardDriveModelst   countt   hdt   tmpHardDriveModelt   hardDriveModelt   hardDriveVersionMismatcht   csurHardDriveFirmwareVersiont!   installedHardDriveFirmwareVersion(    (    s   ./computeNodeInventory.pyt   __getStorageFirmwareInventory�   s�    


	
'"	 '"	(%)%
	'"	(%))'"	 
 
 	 
%%-c         C   s�  |  i  i d � t i i d � o
 d } n\ t i i d � o
 d } n? t i i d � o
 d } n" |  i  i d | � t |  _ d  S| d } t i	 | d t i
 d t i
 d	 t �} | i �  \ } } |  i  i d
 | d | i �  � | i d j o" |  i  i d | � t |  _ d  St i d | t i t i B� oT t i d | t i t i B� i d � } t i d | t i t i B� i d � } n |  i  i d � t |  _ d  S|  i  i d | d | d � g  } | d | d } t i	 | d t i
 d t i
 d	 t �} | i �  \ } } |  i  i d
 | d | i �  � | i d j o" |  i  i d | � t |  _ d  St i d | t i t i B� }	 |  i  i d t |	 � d � x= |	 D]5 }
 |
 i �  } | d d | d } | i | � q�W| i �  |  i  i d t | � d � g  } d } x� | D]x } | i �  } | d j o) | i | d � | d } | d 7} q-| d | j o | i | d � | d } q-q-W|  i  i d  t | � � x| D]	} t } y |  i | d } WnE t j
 o9 |  i  i d! | d" � t |  _ |  i i | � Pn Xx� | D]� } | i �  } | d | j or | d } |  i  i d# | d � | | j o? |  i | d d$ j o' |  i | d |  i d% | <t } Pq�q:q:Wq�W|  i  i d& � d  S('   Ns3   Getting the local OS hard drive firmware inventory.s   /usr/sbin/ssaclis   /usr/sbin/hpssaclis   /usr/sbin/hpacuclis=   There is no Smart Storage Administration software installed.
s    ctrl all showRd   Re   Rf   s   The output of the command (s<   ) used to get the list of attached storage controllers was: i    s8   Failed to get the list of attached storage controllers.
s.   \s*Smart\s+Array\s+P\d{3}i\s+in\s+Slot\s+\d{1}s0   \s*Smart\s+Array\s+(P\d{3}i)\s+in\s+Slot\s+\d{1}i   s0   \s*Smart\s+Array\s+P\d{3}i\s+in\s+Slot\s+(\d{1})s<   Failed to get the internal storage controller's information.s%   The controller was determined to be: s	    in slot R0   s    ctrl slot=s    pd all show detailsB   ) used to get the hard drive list and their firmware version was: s#   Failed to get hard drive versions.
s�   Firmware\s+Revision:\s+[0-9A-Z]{4}\s+Serial\s+Number:\s+[0-9A-Z]+\s+WWID:\s+[0-9A-F]+\s+Model:\s+HP\s+[0-9A-Z]+|Firmware\s+Revision:\s+[0-9A-Z]{4}\s+Serial\s+Number:\s+[0-9A-Z]+\s+Model:\s+HP\s+[0-9A-Z]+s/   The hard drive data list was determined to be: i����R-   i   s*   The hard drive list was determined to be: s-   The hard drive models were determined to be: s"   Firmware for the hard drive model s!    is missing from the csur bundle.s8   The hard drive's firmware version was determined to be: R`   R   s8   Done getting the local OS hard drive firmware inventory.(   R   R   Rl   Rm   Rn   RI   R4   R   Ro   Rp   Rq   Rr   Rs   Rt   R2   R3   Rv   Rw   Rx   Ru   R6   R5   Ry   Rz   R   R#   RH   R   R    R$   (   R)   R{   RU   R|   R}   R~   R�   R�   R�   R�   R�   R�   R�   R�   R�   R�   R�   R�   R�   R�   R�   (    (    s   ./computeNodeInventory.pyt&   __getLocalOSHardDriveFirmwareInventory{  s�    


	
'"	 (,	 '"	 
 
 	 
%c         C   s�  g  } d } |  i  i d � |  i | | � } | d j o d  Sx� | D]x } | i �  } | d j o) | i | d � | d } | d 7} qG | d | j o | i | d � | d } qG qG W|  i  i d t | � d � d }	 t i |	 d t i d	 t i d
 t	 �}
 |
 i
 �  \ } } |  i  i d |	 d | i �  � |
 i d j o" |  i  i d | � t	 |  _ d  St i d | t i t i B� } |  i  i d t | � d � x4| D],} t } t } d } y |  i | d } Wn7 t j
 o+ |  i  i d | d � t	 |  _ q�n Xx�| D]�} t } | i �  } | d } | d } | | j o3x�| D]�} d | }	 t i |	 d t i d	 t i d
 t	 �}
 |
 i
 �  \ } } |  i  i d |	 d | i �  � |
 i d j o, |  i  i d | d | � t	 |  _ qfn | | j o | } t	 } n qf| i �  } xr | D]j } d | j oW | i �  } d | j p d | j o# t i d | d � i d � } q�| d } q@q@W|  i  i d t | � d � | | j o~ | d j oq |  i | d d j oK |  i | d |  i d | <t	 } |  i i d i | | | |  i � � n | d 7} n PqfW| p+ |  i  i d | d  � t	 |  _ t	 } q�n q&| d j o Pq&q&W| o1 | o) |  i i d i | | | |  i � � q�q�W|  i  i d! � d  S("   Ni    s(   Getting the NIC card firmware inventory.t   NICBusFailurei   s+   The NIC card models were determined to be: R0   s   ifconfig -aRd   Re   Rf   s   The output of the command (s%   ) used to get the NIC card list was: s0   Failed to get the Compute Node's NIC card list.
s   ^[empth0-9]{3,}s(   The NIC card list was determined to be: s    Firmware for the NIC card model s!    is missing from the csur bundle.s   ethtool -i s+   ) used to check the NIC card firmware was: s,   Failed to get the NIC card information for (s   ).
s   firmware-versions   5719-vs   5720-vs
   \d{4}-(.*)i����s4   The NIC card firmware version was determined to be: R`   R   s   {0:40} {1:25} {2:25} {3}s   The NIC card (sc   ) was not found (ifconfig -a), thus there is some sort of NIC card issue that needs to be resolved.s-   Done getting the NIC card firmware inventory.(   R   R   t$   _ComputeNodeInventory__getNicBusListR5   Ry   R6   Ro   Rp   Rq   R4   Rr   Rs   Rt   RI   R   R2   Ru   Rv   Rw   R   R#   RH   t
   splitlinesR3   Rx   R$   R   R   R&   R'   (   R)   R<   R=   t   nicCardModelsR�   t
   nicBusListt   ndt   nicCardDatat   tmpNicCardModelR|   R}   R~   RU   t   nicCardListt   nicCardModelt   nicCardVersionMismatcht   nicCardFoundErrort   csurNicCardFirmwareVersionR8   t   foundt   nicBust   installedNicCardModelt   nict	   nicDevicet   versionListt   lineR9   t   installedNicCardFirmwareVersion(    (    s   ./computeNodeInventory.pyt   __getNICFirmwareInventory�  s�     
'"	 	 

 
'"	
 #)		-c         C   s�  g  } h  } |  i  i d � d | d } t i | d t i d t i d t �} | i �  \ } } | i d j o" |  i  i d | � t |  _	 d	 S|  i  i d
 | d | i
 �  � t i d d | � } | i d � }	 x�|	 D]}}
 d |
 j p d |
 j o]t i d | d |
 t i t i B� } y� | p+ |  i  i d |
 d d !� t |  _	 w� n |  i  i d |
 d d !d | i d � d � | i d � d  } | | j o_ d | | <| i | i d � d | i d � � d |
 j o |  i i | i d � � qn Wq_t j
 o> } |  i  i d t | � d |
 d d !� t |  _	 q� q_Xq� q� W| i d  d! �  � |  i  i d" t | � d# � |  i  i d$ � | S(%   Ns   Getting the NIC bus list.s	   lspci -i s    -mvvRd   Re   Rf   i    s/   Failed to get the Compute Node's NIC bus list.
R�   s   The output of the command (s0   ) used to get the NIC card bus information was: s   
{2,}s   ####s   Ethernet controllers   Network controllers3   \s*[a-zA-Z]+:\s+([0-9a-f]{2}:[0-9a-f]{2}\.[0-9]).*(s   )\s+Adapter.*sL   A match error was encountered while getting nic bus information for device: i�   s    The bus information for device:
id   s   
was determined to be: i   s   .
i����R.   R-   i   t   MellanoxsE   An AttributeError was encountered while getting nic bus information: s   
t   keyc         S   s   |  i  �  d  S(   i   (   R5   (   t   n(    (    s   ./computeNodeInventory.pyt   <lambda>�  s    s,   The NIC card bus list was determined to be: R0   s   Done getting the NIC bus list.(   R   R   Ro   Rp   Rq   R4   Rr   Rt   RI   R   Rs   R2   t   subR5   R3   Rv   Rw   Rx   Ry   R%   t   AttributeErrorR6   Rz   (   R)   R<   R=   R�   t   busDictR|   R}   R~   RU   t
   deviceListt   devicet   bust	   busPrefix(    (    s   ./computeNodeInventory.pyt   __getNicBusList~  sJ    '	" '	0
'%)	c         C   s�	  d |  i  } |  i i d � |  i  d j od } t i | d t i d t i d t �} | i �  \ } } |  i i d | d	 | i �  � | i	 d
 j o! |  i i
 d | � t |  _ n� | i �  } | i d � } | d d | d
 d | d } |  i i d | d � |  i | d
 }	 | |	 j o] |  i | d d j oE |  i | d |  i d | <|  i i d i d |	 | |  i � � n& |  i i d i d |	 | |  i � � d } t i | d t i d t i d t �} | i �  \ } } |  i i d | d | i �  � | i	 d
 j o! |  i i
 d | � t |  _ q3t i d | t i t i B� i d � }
 |  i i d |
 d � |  i |  i d
 } |
 | j oc |  i |  i d d j oH |  i |  i d |  i d d <|  i i d i d | |
 |  i � � q3|  i i d i d | |
 |  i � � n d } t i | d t i d t i d t �} | i �  \ } } |  i i d | d | i �  � | i	 d
 j o! |  i i
 d | � t |  _ n�t i d | t i t i B� d  j oc| i d � } |  i p t |  _ n d } h  } x�| D]�} t i d | t i t i B� d  j ohd } d } d } | i �  } xG| D];} t i d  | � d  j o7 t i d! | � i d � } |  i i d" | d � n t i d# | � d  j o7 t i d$ | � i d � } |  i i d% | d � n t i d& | � d  j oO t i d' | � i d � } |  i i d( | d � | | j o
 | } q�Pn | d j o | d j o| d j oy |  i | d
 } Wn5 t j
 o) |  i i
 d) | d* � t |  _ Pn X| | j o� |  i | d d j ok | |  i d j o  |  i | d |  i d | <n | | j p | | d o | | t g | | <q�n% | | j o | | t g | | <n PququWq$q$Wx� | D]� } | | d p9 |  i i d i | | | d
 | | d |  i � � q�|  i i d i | | | d
 | | d |  i � � q�Wn |  i  |  i j o*d } d+ } t i | d t i d t i d t �} | i �  \ } } |  i i d | d, | i �  � | i	 d
 j o! |  i i
 d- | � t |  _ q�	| i �  } t } xo | D]g } | o& t i d. | � d  j o t } qq| o) | i �  } |  i i d/ | d � PqqqW| d j o� d0 |  i  } y |  i | d
 } Wn, t j
 o  |  i i
 d1 � t |  _ q�	X| | j o] |  i | d d j oE |  i | d |  i d | <|  i i d i d0 | | |  i � � q�	|  i i d i d0 | | |  i � � q�	|  i i
 d2 � t |  _ n |  i i d3 � d  S(4   Nt   BIOSs3   Getting the compute node common firmware inventory.RF   s   dmidecode -s bios-release-dateRd   Re   Rf   s   The output of the command (s7   ) used to get the compute node's BIOS information was: i    s8   Failed to get the compute node's BIOS firmware version.
t   /i   R0   i   s6   The compute node's bios version was determined to be: R`   R   s   {0:40} {1:25} {2:25} {3}s
   hponcfg -gs6   ) used to get the compute node's iLO information was: s7   Failed to get the Compute Node's iLO firmware version.
s&   .*Firmware Revision\s+=\s+(\d+\.\d+).*s5   The compute node's iLO version was determined to be: R   s   systool -c scsi_host -vs6   ) used to get the compute node's HBA information was: s.   Failed to get compute node's HBA information.
t   HBAs
   Device = "R.   s   \s+fw_versions   \s*fw_version\s+=\s+"(.*)\s+\(s1   The HBA's firmware version was determined to be: s   \s*model_names   \s*model_name\s+=\s+"(.*)"s&   The HBA's model was determined to be: s   \s*serial_nums   \s*serial_num\s+=\s+"(.*)"s.   The HBA's serial number was determined to be: s   Firmware for the HBA model s!    is missing from the csur bundle.t	   dmidecodes<   ) used to get the compute node's dmidecode information was: sz   Failed to get compute node's dmidecode information needed to determine the Power Management Contoller's firmware version.
s,   ^\s*Power Management Controller Firmware\s*$sI   The Power Management Controller's firmware version was determined to be: t   PMCsM   Firmware for the Power Management Controller is missing from the csur bundle.s\   The Power Management Controller's firmware version was not found in the output of dmidecode.s8   Done getting the compute node common firmware inventory.(    R   R   R   Ro   Rp   Rq   R4   Rr   Rs   Rt   RI   R   R5   R#   R$   R   R   R&   R'   R2   R3   Rv   Rw   Rx   R   t   searchR`   R!   R�   RH   R   R   (   R)   t   biosFirmwareTypeR|   R}   R~   RU   t   biosFirmwareDatet   biosFirmwareDateListt   installedBiosFirmwareVersiont   csurBiosFirmwareVersiont   installedILOFirmwareVersiont   csurILOFirmwareVersiont   hostListt   previousSerialNumbert   hbaResultDictt   hostt   currentSerialNumbert   installedHBAFirmwareVersiont   hbaModelt   hostDataListR8   t   csurHBAFirmwareVersiont   installedPMCFirmwareVersiont   dmidecodeListR�   t   pmcCSURReferencet   csurPMCFirmwareVersion(    (    s   ./computeNodeInventory.pyt   __getCommonFirmwareInventory�  s�    '""%)%'"(())'"&
 & 
'	%  9='" !%))c         C   s�  t  } t  } g  } t i g  } | i d � D] } | | i �  q, ~ � } t i g  }	 | i d � D] } |	 | i �  qe ~	 � }
 d } |  i i d � x|  i D] } | i d d � } d | j o | o q� q� d | j o t	 } q� q� |  i
 | j o |  i | j o | o q� q� |  i
 | j o |  i | j o t	 } q� q� t i d | � o Pq� | i d � } | d } | d	 } |  i o | | j o q� n |  i o | |
 j o q� n d
 | } t i | d t i d t i d t	 �} | i �  \ } } |  i i d | d | i �  � | i d j o} | d j p | d j o: | d j o- |  i i d | d | � | d	 7} q� q�|  i i d | d | � t	 |  _ n | i �  } xB | D]: } t i d | � d  j o | i �  } | d	 } Pq�q�W|  i i d | d � | | j oO | d d j o> | d |  i d | <|  i i d i | | | |  i � � q� |  i i d i | | | |  i � � q� W|  i i d � d  S(   Nt   ,i    s   Getting the driver inventory.R-   R.   R   s   \s*$R/   i   s   modinfo Rd   Re   Rf   s   The output of the command (s*   ) used to get the driver information was: t   mlx4_ent   mlnxs#   The first Mellanox driver checked (s+   ) appears not to be the driver being used.
s;   Failed to get the Compute Node's driver version for driver s   .
s   version:\s+.*s)   The driver version was determined to be: R0   i   R`   s   {0:40} {1:25} {2:25} {3}s"   Done getting the driver inventory.(   R   t   dictt   fromkeysR5   Rs   R   R   R   R1   R4   R   R   R2   R3   R!   R"   Ro   Rp   Rq   Rr   Rt   t   warnRI   R   R�   R`   R$   R   R   R&   R'   (   R)   R@   RB   R7   t   driversFoundt   updateDriverListt   _[1]t   xt   hbaDriverDictt   _[2]t   localStorageDriverDictt	   mlnxCountR8   t   csurDriverListt
   csurDrivert   csurDriverVersionR|   R}   R~   RU   t   driverDataListR�   t   installedDriverVersion(    (    s   ./computeNodeInventory.pyt   __getDriverInventory|  sj    99	
 ) 


'"'
 
	))c         C   s�  t  } t  } g  } t i g  } | i d � D] }	 | |	 i �  q, ~ � }
 t i g  } | i d � D] }	 | |	 i �  qe ~ � } t i g  } | i d � D] }	 | |	 i �  q� ~ � } t i g  } | i d � D] }	 | |	 i �  q� ~ � } |  i i d � x�|  i D]�} | i d d � } d | j o | o qqd | j o t	 } qq|  i
 | j o |  i | j o | o qq|  i
 | j o |  i | j o t	 } qqt i d | � o Pq| i d � } | d } | d	 } | d
 } |  i o | | j o qn |  i o | | j o qn |  i d j o |  i d j o d | j o qn d | } t i | d t i d t i d t	 �} | i �  \ } } |  i i d | d | i �  � | i d j o� d | j o� | | j o |  i d i | d � nB | |
 j o |  i d i | d � n |  i d i | d � |  i i d i | | d |  i � � qq�|  i i d | d | � t	 |  _ qn | i �  i d � } | d } | d	 } |  i i d | d � | | j o� | d d j o� | | j o |  i d i | d � nB | |
 j o |  i d i | d � n |  i d i | d � |  i i d i | | | |  i � � q|  i i d i | | | |  i � � qW|  i i d  � d  S(!   NR�   s   Getting the software inventory.R-   R.   R   s   \s*$R/   i    i   i   R   t
   DL360pGen8t   serviceguards<   rpm -q --queryformat=%{buildtime}':'%{version}'-'%{release} Rd   Re   Rf   s   The output of the command (s>   ) used to get the software epoch and version information was: s   is not installedR   i   R   s   {0:40} {1:25} {2:25} {3}s   Not Installeds?   Failed to get the Compute Node's software version for software s   .
R
   s.   The software epoch date was determined to be: R0   R`   s$   Done getting the software inventory.(   R   R�   R�   R5   Rs   R   R   R   R1   R4   R   R   R2   R3   R!   R"   Ro   Rp   Rq   Rr   Rt   R$   Ry   R   R   R(   RI   R   R&   R'   (   R)   R>   R?   RA   RC   R7   t   softwareFoundt   updateSoftwareListR�   R�   t   sgSoftwareDictR�   t   sgNFSSoftwareDictt   _[3]t   hbaSoftwareDictt   _[4]t   localStorageSoftwareDictR8   t   csurSoftwareListt   csurSoftwaret   csurSoftwareEpocht   csurSoftwareVersionR|   R}   R~   RU   t   rpmInformationListt   installedSoftwareEpocht   installedSoftwareVersion(    (    s   ./computeNodeInventory.pyt   __getSoftwareInventory�  s|    9999
 ) 


-
'"%	

))c         C   s7  |  i  i d � d } t i | d t i d t i d t �} | i �  \ } } |  i  i d | d | i �  � | i d j o" |  i  i	 d	 | � t |  _
 d
 St i g  } | i �  D] } | | i �  d q� ~ � } |  i  i d t | � � d | j p d | j o t |  _ d Sd S|  i  i d � d  S(   Ns.   Checking to see if there is any local storage.s	   lsscsi -HRd   Re   Rf   s   The output of the command (s*   ) used to get a list of SCSI devices was: i    s(   Failed to get the list of SCSI devices.
t   Errori   s(   The SCSI devices were determined to be: t   hpsat   ccissRG   R_   s3   Done checking to see if there is any local storage.(   R   R   Ro   Rp   Rq   R4   Rr   Rs   Rt   RI   R   R�   R�   R�   R5   R6   R"   (   R)   R|   R}   R~   RU   R�   t   colt   scsiDict(    (    s   ./computeNodeInventory.pyt   __getLocalStorage<  s     '"	:	c         C   s   |  i  S(   N(   R$   (   R)   (    (    s   ./computeNodeInventory.pyt   getComponentUpdateDict]  s    c         C   s   |  i  S(   N(   R%   (   R)   (    (    s   ./computeNodeInventory.pyt   getMellanoxBusListe  s    c         C   s   |  i  S(   N(   R   (   R)   (    (    s   ./computeNodeInventory.pyt   getInventoryStatusm  s    c         C   s   |  i  S(   N(   R   (   R)   (    (    s   ./computeNodeInventory.pyt   getHardDriveFirmwareStatusu  s    c         C   s   d i  |  i � S(   Ns   , (   t   joinR    (   R)   (    (    s   ./computeNodeInventory.pyt   getHardDrivesMissingFirmware}  s    c         C   s   d  S(   N(    (   R)   (    (    s   ./computeNodeInventory.pyRO   �  s    c         C   s   d  S(   N(    (   R)   (    (    s   ./computeNodeInventory.pyRQ   �  s    c         C   s   d  S(   N(    (   R)   (    (    s   ./computeNodeInventory.pyRS   �  s    c         C   s   |  i  S(   N(   R   (   R)   (    (    s   ./computeNodeInventory.pyt   isExternalStoragePresent�  s    (   t   __name__t
   __module__R,   RJ   R^   Rc   RL   Ra   RM   R�   RN   RP   RR   RK   R   R  R  R  R  RO   RQ   RS   R  (    (    (    s   ./computeNodeInventory.pyR       s*   	G		>		�	{	�	>	�	^	b	!								
t   Gen1ScaleUpComputeNodeInventoryc           B   s5   e  Z d  �  Z d �  Z d �  Z d �  Z d �  Z RS(   c         C   s#   t  i |  | | | � g  |  _ d  S(   N(   R    R,   t   busList(   R)   R*   R   R   (    (    s   ./computeNodeInventory.pyR,   �  s    c         C   s�  |  i  i d � d } t i | d t i d t i d t �} | i �  \ } } |  i  i d | d | i �  � | i d j o" |  i  i	 d	 | � t |  _
 d  S| i �  } d } h  } d
 } |  i d d }	 x�| D]�}
 |
 i �  }
 d |
 j p t i d |
 � o� d |
 j o? t i d |
 � i d � | d <|  i  i d | d d � n< t i d |
 � i d � | d <|  i  i d | d d � | d 7} n | d j o� | d |	 j o| |  i i | d � | d
 j o& |  i d d |  i d d <d } n |  i i d i d | d |	 | d |  i � � n2 |  i i d i d | d |	 | d |  i � � | i �  d } q� q� W|  i  i d � d  S(   Ns7   Getting the compute node's FusionIO firmware inventory.s
   fio-statusRd   Re   Rf   s   The output of the command (s5   ) used to get the FusionIO firmware information was: i    sm   Failed to get the FusionIO status information needed to determine the FusionIO firmware version information.
t   not   FusionIOR   s"   PCI:[0-9a-f]{2}:[0-9]{2}\.[0-9]{1}s$   Firmware\s+(v([0-9]\.){2}[0-9]{1,2})i   s2   The ioDIMM firmware version was determined to be: R0   s"   .*([0-9a-f]{2}:[0-9]{2}\.[0-9]{1})R�   s%   The ioDIMM bus was determined to be: i   t   yess   {0:40} {1:25} {2:25} {3}s   FusionIOBus: s<   Done getting the compute node's FusionIO firmware inventory.(   R   R   Ro   Rp   Rq   R4   Rr   Rs   Rt   RI   R   R�   R#   R2   R�   R3   Rx   R
  Ry   R$   R   R   R&   R'   t   clear(   R)   R|   R}   R~   RU   t   fioStatusListR�   t   ioDIMMStatusDictt   firmwareUpdateRequiredt   csurFusionIOFirmwareVersionR�   (    (    s   ./computeNodeInventory.pyRO   �  sF    '"	   
51
c      	   C   s�  t  } g  } |  i i d � x�|  i D]�} | i d d � } t i d | � o | o q& q& t i d | � o t } q& q& | i d � } | d } d } t	 i
 | d t	 i d	 t	 i d
 t �} | i �  \ } }	 |  i i d | d | i �  � | i d j o! |  i i d |	 � t |  _ n� t i d | t i t i B� i d � }
 |  i i d |
 d � |
 | j o> | d |  i d d <|  i i d i d | |
 |  i � � n& |  i i d i d | |
 |  i � � Pq& W|  i i d � d  S(   Ns5   Getting the compute node's FusionIO driver inventory.R-   R.   t   FusionIODriverR/   i   s   modinfo iomemory_vslRd   Re   Rf   s   The output of the command (s3   ) used to get the FusionIO driver information was: i    s/   Failed to get the FusionIO driver information.
s   .*srcversion:\s+([1-3][^\s]+)s2   The FusionIO driver version was determined to be: R0   i   R   t   iomemory_vsls   {0:40} {1:25} {2:25} {3}s:   Done getting the compute node's FusionIO driver inventory.(   R   R   R   R   R1   R2   R3   R4   R5   Ro   Rp   Rq   Rr   Rs   Rt   RI   R   Rv   Rw   Rx   R$   R   R   R&   R'   (   R)   R7   R�   R8   R�   R�   R|   R}   R~   RU   R�   (    (    s   ./computeNodeInventory.pyRQ   �  s8    
 
'"()%c      	   C   s�  t  } t  } |  i i d � xP|  i D]E} | i d d � } t i d | � o | o q& q& t i d | � o t } q& q& t i d | � o Pq& | i d � } | d } | d } | d	 } d
 | } t	 i
 | d t	 i d t	 i d t �}	 |	 i �  \ }
 } |  i i d | d |
 i �  � |	 i d j o� d | j p d |
 j o= | p
 t } n |  i i d i | | d |  i � � q& q�|  i i d | d | � t |  _ q& n |
 i �  i d � } | d } | d } |  i i d | d � | | j o: | p
 t } n |  i i d i | | | |  i � � q& |  i i d i | | | |  i � � q& W| o |  i d i d � n |  i i d � d  S(   Ns7   Getting the compute node's FusionIO software inventory.R-   R.   t   FusionIOSoftwares   \s*$R/   i    i   i   s<   rpm -q --queryformat=%{buildtime}':'%{version}'-'%{release} Rd   Re   Rf   s   The output of the command (s2   ) used to get the software epoch information was: s   is not installeds   {0:40} {1:25} {2:25} {3}s   Not Installeds?   Failed to get the Compute Node's software version for software s   .
R
   s.   The software epoch date was determined to be: R0   R   R  s<   Done getting the compute node's FusionIO software inventory.(   R   R   R   R   R1   R2   R3   R4   R5   Ro   Rp   Rq   Rr   Rs   Rt   R   R   R(   RI   R   R&   R'   R$   Ry   (   R)   R�   t   updateRequiredR8   R�   R�   R�   R�   R|   R}   R~   RU   R�   R�   R�   (    (    s   ./computeNodeInventory.pyRS   -  sT    
 



'"
%	


))c         C   s   |  i  S(   N(   R
  (   R)   (    (    s   ./computeNodeInventory.pyt   getFusionIOBusLists  s    (   R  R  R,   RO   RQ   RS   R  (    (    (    s   ./computeNodeInventory.pyR	  �  s
   		>	6	F(   R2   Rl   Ro   R   R    R	  (    (    (    s   ./computeNodeInventory.pyt   <module>   s   � � � � �