#!/usr/bin/env python

"""
    by oPromessa, 2017, 2018
    Published on https://github.com/oPromessa/flickr-uploader/

    ## LICENSE.txt
    --------------
    * Check usage and licensing notice on LICENSE.txt file.
    * PLEASE REVIEW THE SOURCE CODE TO MAKE SURE IT WILL WORK FOR YOUR NEEDS.

    ## CONTRIBUTIONS ARE WELCOME!
    -----------------------------
    * Check CONTRIBUTING and TODO files
    * FEEDBACK ON ANY TESTING AND FEEDBACK YOU DO IS GREATLY APPRECIATED.
    * IF YOU FIND A BUG, PLEASE REPORT IT.

    ## Recognition
    --------------
    Inspired by:
    * https://github.com/sybrenstuvel/flickrapi
    * http://micampe.it/things/flickruploadr
    * https://github.com/joelmx/flickrUploadr/

    ## README.md
    ------------
    * Check README.md file for information including:
        ### Description
        ### Features
        ### Requirements
        ### Setup on Synology
        ### Configuration
        ### Usage/Arguments/Options
        ### Task Scheduler (cron)
        ### Recognition
        ### Final remarks
        ### Q&A
"""

# =============================================================================
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function,
#    unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1


# =============================================================================
# Import section
import sys
import traceback
import logging
import logging.handlers
import argparse
import os
import os.path
try:
    # Use portalocker if available. Required for Windows systems
    import portalocker as FileLocker  # noqa
    FILELOCK = FileLocker.lock
except ImportError:
    # Use fcntl
    import fcntl as FileLocker
    FILELOCK = FileLocker.lockf
import errno
import pprint
# -----------------------------------------------------------------------------
# Helper FlickrUploadr class to upload pics/videos into Flickr.
import lib.FlickrUploadr as FlickrUploadr
# -----------------------------------------------------------------------------
# Helper class and functions for UPLoaDeR Global Constants.
import lib.Konstants as KonstantsClass
# -----------------------------------------------------------------------------
# Helper class and functions to print messages.
import lib.NicePrint as NicePrint
# -----------------------------------------------------------------------------
# Helper class and functions to load, process and verify INI configuration.
import lib.MyConfig as MyConfig
# -----------------------------------------------------------------------------
# Helper class to allow multiprocessing looging into a single file
import lib.multiprocessing_logging as multiprocessing_logging


# =============================================================================
# Logging init code
#
# Getting definitions from Konstants
UPLDR_K = KonstantsClass.Konstants()
# Sets LOGGING_LEVEL to allow logging even if everything else is wrong!
# Parent logger is set to Maximum (DEBUG) so that suns will log as appropriate
# Produces too much ouput info on MyConfig. Setting it to WARNING
logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger()
for i, orig_handler in enumerate(list(logger.handlers)):
    print(i, ' removing handler deafut')
    logger.removeHandler(orig_handler)

# define a Handler which writes WARNING messages or higher to the sys.stderr
CONSOLE_LOGGING = logging.StreamHandler()
CONSOLE_LOGGING.setLevel(logging.DEBUG)
CONSOLE_LOGGING.setFormatter(logging.Formatter(
    fmt=UPLDR_K.Pur + '[' + str(UPLDR_K.Run) + ']' +
    '[%(asctime)s]:[%(processName)-11s]' + UPLDR_K.Std +
    '[%(levelname)-8s]:[%(name)s] %(message)s',
    datefmt=UPLDR_K.TimeFormat))
logging.getLogger().addHandler(CONSOLE_LOGGING)

# Inits with default configuration value, namely LOGGING_LEVEL
MY_CFG = MyConfig.MyConfig()
# Update console logging level as per LOGGING_LEVEL from default config
CONSOLE_LOGGING.setLevel(int(MY_CFG.LOGGING_LEVEL))
# -----------------------------------------------------------------------------


# =============================================================================
# Init code
#
# Python version must be greater than 2.7 for this script to run
#
if sys.version_info < (2, 7):
    logging.critical('----------- (V%s) Error Init -----------(Log:%s)'
                     'This script requires Python 2.7 or newer.'
                     'Current Python version: [%s] '
                     'Exiting...',
                     UPLDR_K.Version,
                     MY_CFG.LOGGING_LEVEL,
                     sys.version)
    sys.exit(1)
else:
    logging.warning('----------- (V%s) Init -----------(Log:%s)'
                    'Python version on this system: [%s]',
                    UPLDR_K.Version,
                    MY_CFG.LOGGING_LEVEL,
                    sys.version)
# -----------------------------------------------------------------------------


logger = logging.getLogger()

for i, orig_handler in enumerate(list(logger.handlers)):
    print(i, orig_handler)


logging.debug('DEBUG')
logging.warning('WARNING')
logging.error('ERROR')
logging.critical('CRITICAL')
