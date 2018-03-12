"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

    Helper class and functions for UPLoaDeR Global Constants.
"""

# ----------------------------------------------------------------------------
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function, unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1

# ----------------------------------------------------------------------------
# Import section
#
import time

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
    #   TimeFormat = Format to display date and time. Used with strftime
    #   Version    = Version Major.Minor.Fix
    #   Run        = Identify the execution Run of this process. Unique number
    #
    TimeFormat = '%Y.%m.%d %H:%M:%S'
    Version = '2.7.1'
    Run = eval(time.strftime('int("%j")+int("%H")*100+int("%M")'))

    # -------------------------------------------------------------------------
    # Color Codes for colorful output
    W = '\033[0m'    # white (normal)
    R = '\033[31m'   # red
    G = '\033[32m'   # green
    O = '\033[33m'   # orange
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
        #   nuMediacount = counter of total files to initially upload
        #
        self.nuMediacount = None


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
