"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

    Helper class and functions for UPLoaDeR Global Constants.
"""

# -----------------------------------------------------------------------------
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function,
#    unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1

# -----------------------------------------------------------------------------
# Import section
#
import time
from . import __version__


# -----------------------------------------------------------------------------
# class UPLDRConstants wiht Global Constants and Variables for flickr-uploadr.
#
class UPLDRConstants:
    """ UPLDRConstants class

        >>> import lib.UPLDRConstants as UPLDRConstantsClass
        >>> UPLDRConstants = UPLDRConstantsClass.UPLDRConstants()
        >>> UPLDRConstants.nuMediacount = 999
        >>> print(UPLDRConstants.nuMediacount)
        999
        >>> print(0 < UPLDRConstants.Run < 10000 )
        True
    """

    # -------------------------------------------------------------------------
    # Class Global Variables
    #   class variable shared by all instances
    #
    #   TimeFormat   = Format to display date and time. Used with strftime
    #   Version      = Version Major.Minor.Fix
    #   Run          = Unique identifier for the execution Run of this process.
    #   nuMediacount = Counter of total files to initially upload
    #
    nuMediacount = None
    TimeFormat = '%Y.%m.%d %H:%M:%S'
    Run = eval(time.strftime('int("%j")+int("%H")*100+int("%M")*10+int("%S")'))
    try:
        if __version__.__version__ is not None:
            Version = __version__.__version__
        else:
            Version = '2.7.0'
    except BaseException:
        Version = '2.7.0'

    # -------------------------------------------------------------------------
    # Color Codes for colorful output
    W = '\033[0m'    # white (normal)
    R = '\033[31m'   # red
    G = '\033[32m'   # green
    Or = '\033[33m'   # orange
    B = '\033[34m'   # blue
    P = '\033[35m'   # purple

    # -------------------------------------------------------------------------
    # class UPLDRConstants __init__
    #
    def __init__(self):
        """ class UPLDRConstants __init__
        """
        # ---------------------------------------------------------------------
        # Instance Global Variables
        #   instance variable unique to each instance
        #
        #   baseDir      = Base configuration directory for files
        #   INIfile      = Location of INI file, normally named "uploadr.ini"
        #
        self.baseDir = str('.')
        self.INIfile = str('uploadr.ini')


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    import logging
    import sys

    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                        '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()

    # Comment following line to allow further debugging/testing
    sys.exit(0)
