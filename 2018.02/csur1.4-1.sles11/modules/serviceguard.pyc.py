Ñò
·IYc           @   s{   d  d k  Z  d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k Z d  d k l Z d d d     YZ	 d S(   iÿÿÿÿN(   t	   copy_treet   Serviceguardc           B   sG   e  Z d    Z d   Z d   Z d   Z d   Z d   Z d   Z RS(   c         C   s(   | |  _  d |  _ d |  _ d |  _ d  S(   Nt    (   t   loggert	   sgBinPatht   hanfst
   hanaNFSDir(   t   selfR   (    (    s   ./serviceguard.pyt   __init__   s    			c         C   s  |  i  i d  | d d d i   } | d } | d } | d } | d } | d	 } |  i |  p t St |  d j o |  i | |  p t Sn t |  d j o |  i | |  p t Sn | d
 o |  i   p t Sn |  i  i d  t	 S(   Ns   Upgrading Serviceguard.t   componentListDictt   computeNodeListi    t   componentUpdateDictt
   sgSoftwaret   sgNFSSoftwaret   osDistLevelt   csurBasePatht   sgNode1s   Done upgrading Serviceguard.(
   R   t   infot   getComputeNodeDictt   _Serviceguard__backupSGConfigt   Falset   lent"   _Serviceguard__upgradeServiceguardt"   _Serviceguard__upgradeSGNFSToolKitt$   _Serviceguard__reconfigureNFSPackaget   True(   R   t   csurResourceDictt   computeNodeDictR   t   sgSoftwareListt   sgNFSSoftwareListR   R   (    (    s   ./serviceguard.pyt   upgradeServiceguard   s(    




			c      
   C   s	  t  i  i   i d  } |  i i d  d | j oâ d |  _ d |  _ d |  _ y t |  i |  i d |  WnA t	 i
 i j
 o/ } |  i i d |  i d	 t |   t SXy" t i |  i |  i d |  Wqõt j
 o/ } |  i i d
 |  i d	 t |   t SXnß d |  _ d |  _ d |  _ y t |  i |  i d |  WnA t	 i
 i j
 o/ } |  i i d |  i d	 t |   t SXy" t i |  i |  i d |  Wn; t j
 o/ } |  i i d
 |  i d	 t |   t SX|  i i d  t S(   Ns   %Y%m%d%H%M%Ss2   Making a backup of the Serviceguard configuration.t   SLESs   /opt/cmcluster/bins"   /opt/cmcluster/nfstoolkit/hanfs.shs   /opt/cmcluster/conf/hananfst   _s@   Failed to make a backup of the Serviceguard HANA NFS directory (s   ).
sN   Failed to make a backup of the Serviceguard toolkit hanfs configuration file (s   /usr/local/cmcluster/bins(   /usr/local/cmcluster/nfstoolkit/hanfs.shs!   /usr/local/cmcluster/conf/hananfss7   Done making a backup of the Serviceguard configuration.(   t   datetimet   nowt   strftimeR   R   R   R   R   R    t	   distutilst   errorst   DistutilsFileErrort   errort   strR   t   shutilt   copy2t   IOErrorR   (   R   R   t   dateTimestampt   err(    (    s   ./serviceguard.pyt   __backupSGConfig?   s>    			%"%
			%"%c   	      C   sâ   | d } |  i  i d  x± | D]© } d | | } t i | d t i d t i d t i d t } | i   \ } } |  i  i d | d	 | d
 | i	    | i
 d j o |  i  i d |  t Sq! W|  i  i d  t S(   Ns#   /software/computeNode/serviceGuard/s$   Upgrading the Serviceguard packages.sG   rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature t   stdoutt   stderrt
   preexec_fnt   shells   The output of the command (s#   ) used to upgrade Serviceguard RPM s    was: i    s8   Problems were encountered while upgrading Serviceguard.
s)   Done upgrading the Serviceguard packages.(   R   R   t
   subprocesst   Popent   PIPEt   ost   setpgrpR   t   communicatet   stript
   returncodeR'   R   (	   R   R   R   t   sgSoftwareDirt   rpmt   commandt   resultt   outR-   (    (    s   ./serviceguard.pyt   __upgradeServiceguardq   s    
 0*	c      
   C   sÂ   |  i  i d  |  i d | } t i | d t i d t i d t i d t } | i	   \ } } |  i  i d | d | i
    | i d	 j o |  i  i d
 |  t S|  i  i d  t S(   Ns"   Updating the Serviceguard license.s   /cmsetlicense -i R/   R0   R1   R2   s   The output of the command (s/   ) used to update the Serviceguard license was: i    sC   Problems were encountered while updating the Serviceguard license.
s'   Done updating the Serviceguard license.(   R   R   R   R3   R4   R5   R6   R7   R   R8   R9   R:   R'   R   (   R   t   sgLicenseFileR=   R>   R?   R-   (    (    s   ./serviceguard.pyt   __updateSGLicense   s    0"c   	      C   s  | d } |  i  i d  x± | D]© } d | | } t i | d t i d t i d t i d t } | i   \ } } |  i  i d | d	 | d
 | i	    | i
 d j o |  i  i d |  t Sq! Wd |  i } t i | d t i d t i d t i d t } | i   \ } } |  i  i d | d |  i d
 | i	    | i
 d j o$ |  i  i d |  i d |  t S|  i  i d  t S(   Ns#   /software/computeNode/serviceGuard/s2   Upgrading the Serviceguard NFS Toolkit package(s).sG   rpm -U --quiet --oldpackage --replacefiles --replacepkgs --nosignature R/   R0   R1   R2   s   The output of the command (s3   ) used to upgrade the Serviceguard NFS Toolkit RPM s    was: i    sH   Problems were encountered while upgrading the Serviceguard NFS Toolkit.
s@   sed -i '0,/^\s*RPCNFSDCOUNT\s*=\s*[0-9]\+$/s//RPCNFSDCOUNT=64/' s.   ) used to update the RPCNFSDCOUNT variable in sF   Problems were encountered while updating the RPCNFSDCOUNT variable in s   .
s7   Done upgrading the Serviceguard NFS Toolkit package(s).(   R   R   R3   R4   R5   R6   R7   R   R8   R9   R:   R'   R   R   (	   R   R   R   R;   R<   R=   R>   R?   R-   (    (    s   ./serviceguard.pyt   __upgradeSGNFSToolKit¤   s(    
 0*	0-c         C   sâ  |  i  i d  |  i d } t i | d t i d t i d t i d t } | i	   \ } } |  i  i d | d | i
    | i d	 j o |  i  i d
 |  t S|  i d } t i | d t i d t i d t i d t } | i	   \ } } |  i  i d | d | i
    | i d	 j o |  i  i d |  t Sd	 } | i   } x; | D]3 } d | j o  | d 7} | d j o Pqq]q]W| d j o |  i  i d  t S|  i d } t i | d t i d t i d t i d t } | i	   \ } } |  i  i d | d | i
    | i d	 j o |  i  i d |  t S|  i d |  i d } t i | d t i d t i d t i d t } | i	   \ } } |  i  i d | d | i
    | i d	 j o |  i  i d |  t S|  i d |  i d } t i | d t i d t i d t i d t } | i	   \ } } |  i  i d | d | i
    | i d	 j o |  i  i d |  t S|  i d } t i | d t i d t i d t i d t } | i	   \ } } |  i  i d | d | i
    | i d	 j o |  i  i d |  t S|  i d } t i | d t i d t i d t i d t } | i	   \ } } |  i  i d | d  | i
    | i d	 j o |  i  i d! |  t S|  i  i d"  t S(#   Ns   Reconfiguring the NFS package.s   /cmrunclR/   R0   R1   R2   s   The output of the command (s!   ) used to start the cluster was: i    s6   Problems were encountered while starting the cluster.
s   /cmviewcl -f line -l nodes2   ) used to check that both nodes were running was: sL   Problems were encountered while checking to see if both nodes were running.
s   state=runningi   i   ss   Problems were encountered while checking to see if both nodes were running; both nodes do not appear to be running.s   /cmhaltpkg nfss$   ) used to halt the nfs package was: s9   Problems were encountered while halting the nfs package.
s   /cmcheckconf -v -P s   /nfs/nfs.confs3   ) used to check the nfs package configuration was: sH   Problems were encountered while checking the nfs package configuration.
s   /cmapplyconf -v -f -P sC   ) used to verify and distribute the nfs package configuration was: sZ   Problems were encountered while verifying and distributing the nfs package configuration.
s   /cmrunpkg nfss#   ) used to run the nfs package was: s:   Problems were encountered while starting the nfs package.
s   /cmmodpkg -e nfss2   ) used to enable AUTO_RUN of the nfs package was: sG   Problems were encountered while enabling AUTO_RUN for the nfs package.
s#   Done reconfiguring the NFS package.(   R   R   R   R3   R4   R5   R6   R7   R   R8   R9   R:   R'   R   t   splitR   (   R   R=   R>   R?   R-   t   countt   cmviewclListt   line(    (    s   ./serviceguard.pyt   __reconfigureNFSPackageÊ   s~    0"0" 
0"0"0"0"0"(	   t   __name__t
   __module__R   R   R   R   t   _Serviceguard__updateSGLicenseR   R   (    (    (    s   ./serviceguard.pyR      s   		$	2			&(    (
   R3   t   loggingt   reR6   R)   R!   R$   t   distutils.dir_utilR    R   (    (    (    s   ./serviceguard.pyt   <module>   s   