Ñò
·IYc           @   s1   d  d k  Z  d  d k Z d  d k Z d   Z d S(   iÿÿÿÿNc         C   sM  t  } |  d d d i   } t i | d  } | i d  y' |  d } t i d d |  d	  } Wn6 t j
 o* } | i d
 t	 |  d  t
 } n X| o t i d d t	 t i i    |  } z] y$ t | d  } | i | d  Wn2 t j
 o& } | i d t	 |   t
 } n XWd  | i   Xn | i d  | S(   Nt   componentListDictt   computeNodeListi    t
   loggerNames2   Updating the csur bundle version information file.t   releaseNotess   \s+t    t   versionInformationFiles   The resource key (s'   ) was not present in the resource file.s   Install Date:s   Install Date: t   as   
s;   Unable to update the csur bundle version information file.
s7   Done updating the csur bundle version information file.(   t   Truet   getComputeNodeDictt   loggingt	   getLoggert   infot   ret   subt   KeyErrort   errort   strt   Falset   datetimet   nowt   opent   writet   IOErrort   close(   t   csurResourceDictt   resultt   computeNodeDictt   loggerR   R   t   errt   f(    (    s   ./updateReleaseInformation.pyt   updateVersionInformationFile   s,    
( (   R	   R   R   R   (    (    (    s   ./updateReleaseInformation.pyt   <module>   s   