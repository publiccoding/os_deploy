Ñò
·IYc           @   s;   d  d k  Z  d  d k Z d  d k Z d d d     YZ d S(   iÿÿÿÿNt   OneOffsc           B   s    e  Z d  Z d   Z d   Z RS(   s)   
	This function is used to remove RPMs.
	c   
      C   si  t  i |  } | i d  t i d d |  i   } |  i | |  \ } } | p | i d  t | f Sd i	 |  } t
 |  d j oµ d | } t i | d t i d t i d	 t } | i   \ } }	 | i d
 | d | i    | i d j o | i d |  qR| i d |	  t t i d d |  f Sn | i d  | i d  t d f S(   NsO   Removing the RPMs, which were identified by the csur resource file for removal.s   ,\s*t    sK   Problems were encountered while getting the updated list of RPMs to remove.i    s   rpm -e t   stdoutt   stderrt   shells   The output of the command (s:   ) used to remove the pre-identified RPMs for removal was: s)   Successfully removed the following RPMs: sp   Problems were encountered while removing the RPMs which were identified by the patch resource file for removal.
s   \s+s   , s-   There were no RPMs that needed to be removed.sT   Done removing the RPMs, which were identified by the csur resource file for removal.t    (   t   loggingt	   getLoggert   infot   ret   subt   splitt   _OneOffs__checkRPMsForRemovalt   errort   Falset   joint   lent
   subprocesst   Popent   PIPEt   Truet   communicatet   stript
   returncode(
   t   selft   rpmsToRemovet
   loggerNamet   loggert   rpmsToRemoveListt   rpmListt   resultt   commandt   outt   err(    (    s   ./oneOffs.pyt
   removeRPMs   s(    
'c         C   s   g  } t  } t i |  } | i d  d } t i | d t i d t i d t  } | i   \ } } | i d | d | i    | i	 d j o | i
 d	 |  t } nY | i   }	 xI | D]A }
 x8 |	 D]0 } t i |
 |  d  j o | i |  qÑ qÑ WqÄ W| i d
  | | f S(   Ns(   Checking the installed RPMs for removal.s   rpm -qaR   R   R   s   The output of the command (s0   ) used to get a list of the installed RPMs was: i    sF   Problems were encountered while getting a list of the installed RPMs.
s-   Done checking the installed RPMs for removal.(   R   R   R   R   R   R   R   R   R   R   R   R   R   R	   t   matcht   Nonet   append(   R   R   R   t   updatedRPMListR   R   R   R    R!   R   t   rpmt   installedRPM(    (    s   ./oneOffs.pyt   __checkRPMsForRemoval:   s(    '
  (   t   __name__t
   __module__t   __doc__R"   R   (    (    (    s   ./oneOffs.pyR    	   s   	-(    (   R   R   R	   R    (    (    (    s   ./oneOffs.pyt   <module>   s   