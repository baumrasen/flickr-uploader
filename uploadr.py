#!/usr/bin/env python

"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

    THIS SCRIPT IS PROVIDED WITH NO WARRANTY WHATSOEVER.
    PLEASE REVIEW THE SOURCE CODE TO MAKE SURE IT WILL WORK FOR YOUR NEEDS.
    FEEDBACK ON ANY TESTING AND FEEDBACK YOU DO IS GREATLY APPRECIATED.
    IF YOU FIND A BUG, PLEASE REPORT IT.

    Some giberish. Please ignore!
    -----------------------------
    Area for my personal notes on on-going work! Please ignore!
    * On first authenticate... removedeletemedia seems to fail
    * Test if it Re-upload or not pictures removed from flickr Web interface.
    * CODING: Should extend this control to other parameters (Enhancement #7)
        Check error:  DuplicateSectionError or DuplicateOptionError.
        Check also: api_key. KeyError(key)
    * CODING Logging/Messaging groundrules:
      niceprint
      niceprint with verbose
      logging.critical: Blocking situations
      logging.error: Relevant errors
      Handled Exceptions: Messages controlled via reportError function
      logging.warning: relevant conclusions/situations
      logging.info: relevant output of variables
      logging.debug: entering and exiting functions
      Note: Consider using assertions: check niceassert function.

    * Change code to insert on database prior to upload and then update result
    * Protect all DB access (single processing or multiprocessing) with:
      And even more:
        try:
            # Acquire DB lock if running in multiprocessing mode
            self.useDBLock( lock, True)
            cur.execute('SELECT rowid,files_id,path,set_id,md5,tagged,'
                      'last_modified FROM files WHERE path = ?', (file,))
        except lite.Error as e:
            reportError(Caught=True,
                CaughtPrefix='+++ DB',
                CaughtCode='990',
                CaughtMsg='DB error on SELECT: [{!s}]'
                          .format(e.args[0]),
                NicePrint=True)
        finally:
            # Release DB lock if running in multiprocessing mode
            self.useDBLock( lock, False)

    ## Update History
    -----------------
    * Functions to be migrated...
       * convertRawFiles

    ## Recognition
    --------------
    Inspired by:
    * https://github.com/sybrenstuvel/flickrapi
    * http://micampe.it/things/flickruploadr
    * https://github.com/joelmx/flickrUploadr/blob/master/python3/uploadr.py

    ## Pending improvements/Known issues
    ------------------------------------
    * AVOID using uploadr when performing massive delete operations on flicr.
      While deleting many files on flickr some of the function calls return
      values like the title of a Set as empty(None). This prompts printing
      information to fail with TypeError: cannot concatenate 'str' and
      'NoneType' objects. Added specific control on function upload:
      setName if setName is not None else 'None'
      BUT worst than that is that one will be saving on the local database
      sets with name (title) empty which will cause other functions to fail.
    * converRawFiles is not tested. Also requires an exif tool to be installed
      and configured as RAW_TOOL_PATH in INI file. Make sure to leave
      CONVERT_RAW_FILES = False in INI file or use at your own risk.
    * Consider using python module exiftool?
    * On some systems it may be required to also import xml.etree.ElementTree
    * If one changes the FILES_DIR folder and do not DELETE all from flickr,
      uploadr WILL not delete the files.
    * Would be nice to update ALL tags on replacePhoto and not only the
      mandatory checksum tag as FLICKR maintains the tags from the first load.
    * If local flickrdb is deleted it will re-upload entire local Library.
      It would be interesting to attempt to rebuild local database. With the
      exception of tags (would require use of exiftool) almost all other
      information could be obtained. On V2.6.8, the function
      is_photo_already_uploaded would already search pics with checksum+Set
      and, if it finds it it will update the local DB.
    * In multiprocessing mode, when uploading additional files to your library
      the work is divided into sorted chunks by each process and it may occur
      that some processes have more work than others defeating the purpose
      of multiprocessing. When loading from scratch a big Library it works
      like a charm.
    * If you reduce FILE_MAX_SIZE in settings, the previously loaded files
      (over such size) are not removed.
    * If you change IGNORED_REGEX in settings, the previously loaded files
      (which match such regular expression) are not removed.
    * Arguments not fully tested:
        -z (not yet fully developed)
    * Regular Output needs to be aligned/simplified to include:
        successful uploads
        successful update of date/time in videos
        successful replacement of photos

    ## Programming Remarks
    ----------------------
    * Follow PEP8 coding guidelines. (see http://pep8online.com/checkresult)
    * If using isThisStringUnicode for (something) if test else (other) make
      sure to break lines with \ correctly. Be careful.
    * Use niceprint function to output messages to stdout.
    * Use logging. for CRITICAL, ERROR, WARNING, INFO, DEBUG messages to stderr
    * Some ocasional critical messages are generated with sys.stderr.write()
    * Specific CODING related comments are marked with 'CODING' keyword
    * Prefix coding for some output messages:
        *****   Section informative
        ===     Multiprocessing related
        ___     Retry related (check retry function)
        +++     Exceptions handling related
        +++ DB  Database Exceptions handling related
        xxx     Error related
    * As far as my testing goes :) the following errors are handled:
            Flickr reports file not loaded due to error: 5
                [flickr:Error: 5: Filetype was not recognised]
                Such files are recorded so that they are not reloaded again.
                Check -b and -c options.
            Flickr reports file not loaded due to error: 8
                [flickr:Error: 8: Filesize was too large]
            Database is locked
            error setting video date
            error 502: flickrapi
            error 504: flickrapi

    ## README.md
    ------------
    * Check README.md file for much more information including:

    ## Description
    ## Features
    ## Requirements
    ## Setup on Synology
    ## Configuration
    ## Usage/Arguments/Options
    ## Task Scheduler (cron)
    ## Recognition
    ## Final remarks
    ## Q&A

"""

# ----------------------------------------------------------------------------
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function, unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1

# ----------------------------------------------------------------------------
# Import section
#
# Check if it is still required httplib
#     Only use is for exception httplib.HTTPException
try:
    import httplib as httplib      # Python 2
except ImportError:
    import http.client as httplib  # Python 3
    
import sys
import argparse
import mimetypes
import os
import time
import sqlite3 as lite
import hashlib
import fcntl
import errno
import subprocess
import re
try:
    import ConfigParser as ConfigParser  # Python 2
except ImportError:
    import configparser as ConfigParser  # Python 3

import multiprocessing
import flickrapi
import xml
# CODING: For some systems this second import is required. To confirm.
# Seems to avoid problem
# logging.info(xml.etree.ElementTree.tostring(
# AttributeError: 'module' object has no attribute 'etree'
# import xml.etree.ElementTree
import os.path
import logging
import pprint
# For repeating functions
from functools import wraps
import random

# =============================================================================
# Init code
#
# Python version must be greater than 2.7 for this script to run
#
if sys.version_info < (2, 7):
    sys.stderr.write("This script requires Python 2.7 or newer.\n")
    sys.stderr.write("Current version: " + sys.version + "\n")
    sys.stderr.flush()
    sys.exit(1)
else:
    # Define LOGGING_LEVEL to allow logging even if everything's else is wrong!
    LOGGING_LEVEL = logging.WARNING
    sys.stderr.write('--------- ' + 'Init: ' + ' ---------\n')
    sys.stderr.write('Python version on this system: ' + sys.version + '\n')
    sys.stderr.flush()


# ----------------------------------------------------------------------------
# Constants class
#
# List out the constants to be used
#
class UPLDRConstants:
    """ UPLDRConstants class
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
        pass

# -----------------------------------------------------------------------------
# Global Variables
# CODING: Consider moving them into Class UPLDRConstants!!!
#
#   nutime       = for working with time module (import time)
#   nuflickr     = object for flickr API module (import flickrapi)
#   flick        = Class Uploadr (created in the Main code)
#   nulockDB     = multiprocessing Lock for access to Database
#   numutex      = multiprocessing mutex to control access to value nurunning
#   nurunning    = multiprocessing Value to count processed photos
#   nuMediacount = counter of total files to initially upload
#                = moved to class UPLDRConstants
nutime = time
nuflickr = None
nulockDB = None
numutex = None
nurunning = None
# CODING: To be changed to x=UPLDRContants() and x.nuMediacount = 0
UPLDRConstants.nuMediacount = 0

# -----------------------------------------------------------------------------
# isThisStringUnicode
#
# Returns true if String is Unicode
#
def isThisStringUnicode(s):
    """
    Determines if a string is Unicode (return True) or not (returns False)
    to allow correct print operations.

    Used by StrUnicodeOut function.
    Example:
        niceprint('Checking file:[{!s}]...'.format(
                                 file.encode('utf-8') \
                                 if isThisStringUnicode(file) \
                                 else file))

    """
    # CODING: Python 2 and 3 compatibility
    # CODING: On Python 3 should always return False to return s
    # in the example
    #    s.encode('utf-8') if isThisStringUnicode(s) else s
    if sys.version_info < (3, ):
        if isinstance(s, unicode):
            return True
        elif isinstance(s, str):
            return False
        else:
            return False
    elif isinstance(s, str):
        return False
    else:
        return False


# -----------------------------------------------------------------------------
# StrUnicodeOut
#
# Returns true if String is Unicode
#
def StrUnicodeOut(s):
    """
    Outputs s.encode('utf-8') if isThisStringUnicode(s) else s
        niceprint('Checking file:[{!s}]...'.format(StrUnicodeOut(file))
    """
    if s is not None:
        return s.encode('utf-8') if isThisStringUnicode(s) else s
    else:
        return ''.encode('utf-8') if isThisStringUnicode('') else ''


# -----------------------------------------------------------------------------
# niceprint
#
# Print a message with the format:
#   [2017.10.25 22:32:03]:[PRINT   ]:[uploadr] Some Message
#
def niceprint(s, fname='uploadr'):
    """
    Print a message with the format:
        [2017.11.19 01:53:57]:[PID       ][PRINT   ]:[uploadr] Some Message
        Accounts for UTF-8 Messages
    """
    print('{}[{!s}][{!s}]:[{!s:11s}]{}[{!s:8s}]:[{!s}] {!s}'.format(
            UPLDRConstants.G,
            UPLDRConstants.Run,
            nutime.strftime(UPLDRConstants.TimeFormat),
            os.getpid(),
            UPLDRConstants.W,
            'PRINT',
            StrUnicodeOut(fname),
            StrUnicodeOut(s)))


# -----------------------------------------------------------------------------
# niceassert
#
def niceassert(s):
    """
     Returns a message with the format:
         [2017.11.19 01:53:57]:[PID       ][ASSERT  ]:[uploadr] Message
         Accounts for UTF-8 Messages

     Usage:
         assert param1 >= 0, niceassert('param1 is not >= 0:'.format(param1))
    """
    return('{}[{!s}][{!s}]:[{!s:11s}]{}[{!s:8s}]:[{!s}] {!s}'.format(
           UPLDRConstants.R,
           UPLDRConstants.Run,
           nutime.strftime(UPLDRConstants.TimeFormat),
           os.getpid(),
           UPLDRConstants.W,
           'ASSERT',
           'uploadr',
           StrUnicodeOut(s)))

# -----------------------------------------------------------------------------
# reportError
#
# Provides a messaging wrapper for logging.error, niprint & str(sys.exc_info()
#
# Examples of use of reportError:
# except flickrapi.exceptions.FlickrError as ex:
#     reportError(Caught=True,
#                 CaughtPrefix='+++',
#                 CaughtCode='990',
#                 CaughtMsg='Flickrapi exception on photos.setdates',
#                 exceptUse=True,
#                 exceptCode=ex.code,
#                 exceptMsg=ex,
#                 NicePrint=True,
#                 exceptSysInfo=True)
# except lite.Error as e:
#     reportError(Caught=True,
#                 CaughtPrefix='+++ DB',
#                 CaughtCode='991',
#                 CaughtMsg='DB error on INSERT: [{!s}]'
#                           .format(e.args[0]),
#                 NicePrint=True)
#     # Release the lock on error.
#     self.useDBLock(lock, False)
#     success = False
# except:
#     reportError(Caught=True,
#                 CaughtPrefix='+++',
#                 CaughtCode='992',
#                 CaughtMsg='Caught exception in XXXX',
#                 exceptSysInfo=True)
#
def reportError(Caught=False, CaughtPrefix='', CaughtCode=0, CaughtMsg='',
                NicePrint=False,
                exceptUse=False, exceptCode=0, exceptMsg='',
                exceptSysInfo=''):
    """ reportError

      Caught = True/False
      CaughtPrefix
        ===     Multiprocessing related
        +++     Exceptions handling related
        +++ DB  Database Exceptions handling related
        xxx     Error related
      CaughtCode = '010'
      CaughtMsg = 'Flickrapi exception on...'/'DB Error on INSERT'
      NicePrint = True/False
      exceptUse = True/False
      exceptCode = ex.code
      exceptMsg = ex
      exceptSysInfo = True/False
    """

    if Caught is not None and Caught:
        logging.error('{!s}#{!s}: {!s}'.format(CaughtPrefix,
                                               CaughtCode,
                                               CaughtMsg))
        if NicePrint is not None and NicePrint:
            niceprint('{!s}#{!s}: {!s}'.format(CaughtPrefix,
                                               CaughtCode,
                                               CaughtMsg))
    if exceptUse is not None and exceptUse:
        logging.error('Error code: [{!s}]'.format(exceptCode))
        logging.error('Error code: [{!s}]'.format(exceptMsg))
        if NicePrint is not None and NicePrint:
            niceprint('Error code: [{!s}]'.format(exceptCode))
            niceprint('Error code: [{!s}]'.format(exceptMsg))
    if exceptSysInfo is not None and exceptSysInfo:
        logging.error(str(sys.exc_info()))
        if NicePrint is not None and NicePrint:
            niceprint(str(sys.exc_info()))

    sys.stderr.flush()
    if NicePrint is not None and NicePrint:
        sys.stdout.flush()


# -----------------------------------------------------------------------------
# retry
#
# retries execution of a function
#
def retry(attempts=3, waittime=5, randtime=False):
    """
    Catches exceptions while running a supplied function
    Re-runs it for times while sleeping X seconds in-between
    outputs 3 types of errors (coming from the parameters)

    attempts = Max Number of Attempts
    waittime = Wait time in between Attempts
    randtime = Randomize the Wait time from 1 to randtime for each Attempt
    """
    def wrapper_fn(f):
        @wraps(f)
        def new_wrapper(*args, **kwargs):

            rtime = time
            error = None

            if LOGGING_LEVEL <= logging.WARNING:
                if args is not None:
                    logging.warning('___Retry f():[{!s}] '
                                    'Max:[{!s}] Delay:[{!s}] Rnd[{!s}]'
                                    .format(f.__name__, attempts,
                                            waittime, randtime))
                    for i, a in enumerate(args):
                        logging.warning('___Retry f():[{!s}] arg[{!s}]={!s}'
                                        .format(f.__name__, i, a))
            for i in range(attempts if attempts > 0 else 1):
                try:
                    logging.warning('___Retry f():[{!s}]: '
                                    'Attempt:[{!s}] of [{!s}]'
                                    .format(f.__name__, i+1, attempts))
                    return f(*args, **kwargs)
                except Exception as e:
                    logging.error('___Retry f():[{!s}]: Error code A: [{!s}]'
                                  .format(f.__name__, e))
                    error = e
                except flickrapi.exceptions.FlickrError as ex:
                    logging.error('___Retry f():[{!s}]: Error code B: [{!s}]'
                                  .format(f.__name__, ex))
                except lite.Error as e:
                    logging.error('___Retry f():[{!s}]: Error code C: [{!s}]'
                                  .format(f.__name__, e))
                    error = e
                    # Release the lock on error.
                    # CODING: Check how to handle this particular scenario.
                    # flick.useDBLock(nulockDB, False)
                    # self.useDBLock( lock, True)
                except:
                    logging.error('___Retry f():[{!s}]: Error code D: Catchall'
                                  .format(f.__name__))

                logging.warning('___Function:[{!s}] Waiting:[{!s}] Rnd:[{!s}]'
                                .format(f.__name__, waittime, randtime))
                if randtime:
                    rtime.sleep(random.randrange(0,
                                                 (waittime+1)
                                                 if waittime >= 0
                                                 else 1))
                else:
                    rtime.sleep(waittime if waittime >= 0 else 0)
            logging.error('___Retry f():[{!s}] '
                            'Max:[{!s}] Delay:[{!s}] Rnd[{!s}]: Raising ERROR!'
                            .format(f.__name__, attempts,
                                    waittime, randtime))
            raise error
        return new_wrapper
    return wrapper_fn
# -----------------------------------------------------------------------------
# Samples
# @retry(attempts=3, waittime=2)
# def retry_divmod(argslist):
#     return divmod(*argslist)
# print retry_divmod([5, 3])
# try:
#     print(retry_divmod([5, 'H']))
# except:
#     logging.error('Error Caught (Overall Catchall)...')
# finally:
#     logging.error('...Continuing')
# nargslist=dict(Caught=True, CaughtPrefix='+++')
# retry_reportError(nargslist)


# -----------------------------------------------------------------------------
# class LastTime to be used with rate_limited
#
class LastTime:

    def __init__(self, name):
        self.name = name
        self.ratelock = None
        self.cnt = None
        self.last_time_called = None
        
        logging.debug('\t__init__: name=[{!s}]'.format(self.name))

    def start(self):
        self.ratelock = multiprocessing.Lock()
        self.cnt = multiprocessing.Value('i', 0)
        self.last_time_called = multiprocessing.Value('f', 0.0)
        # self.debug('start')

    def acquire(self):
        # self.debug('acquire')
        self.ratelock.acquire()

    def release(self):
        # self.debug('release')
        self.ratelock.release()

    def set_last_time_called(self):
        xtime=time.time()
        logging.debug('Set xtime last_time_called:[{!s}]/[{!s}]'
                      .format(time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(xtime)),
                              xtime))
        self.last_time_called.value = xtime 
        # self.debug('set_last')
        logging.debug('Set real last_time_called:[{!s}]/[{!s}]'
                      .format(time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(
                                                self.last_time_called.value)),
                              self.last_time_called.value))
        
    def get_last_time_called(self):
        # self.debug('get_last')
        return self.last_time_called.value
    
    def add_cnt(self):
        self.cnt.value += 1
        # self.debug('add_cnt')

    def get_cnt(self):
        # self.debug('get_cnt')
        return self.cnt.value
        
    def debug(self, debugname):
        logging.debug('___Rate name:[{!s}] '
                      'debug=[{!s}] '
                      'cnt:[{!s}] '
                      'last_called:{!s} '
                      'timenow():{!s} '
                      .format(self.name,
                              debugname,
                              self.cnt.value,
                              time.strftime('%T',
                                            time.localtime(
                                                self.last_time_called.value)),
                              time.strftime('%T')))
        

# -----------------------------------------------------------------------------
# rate_limited
#
# retries execution of a function
def rate_limited(max_per_second):

    min_interval = 1.0 / max_per_second
    LT = LastTime('rate_limited')
    LT.start()

    def decorate(func):
        LT.acquire()
        logging.debug('1st decorate: last_time_called=[{!s}]'
                      .format(time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(
                                                LT
                                                .last_time_called.value))))
        if LT.get_last_time_called() == 0:
            LT.set_last_time_called()
            logging.debug('Setting last_time_called time to approx:[{!s}]'
                          .format(time.strftime('%Y-%m-%d %H:%M:%S')))
        logging.debug('2nd decorate: last_time_called=[{!s}]'
                      .format(time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(
                                                LT.get_last_time_called()))))
        LT.release()

        @wraps(func)
        def rate_limited_function(*args, **kwargs):

            logging.warning('___Rate_limited f():[{!s}]: '
                            'Max_per_Second:[{!s}]'
                            .format(func.__name__, max_per_second))

            try:
                # CODING: xfrom before acquire will ensure rate limt is
                # respected accross processes. If not all process will
                # execute at the same time
                xfrom = time.time()
                LT.acquire()
                LT.add_cnt()

                # elapsed = time.time() - context.last_time_called
                elapsed = xfrom - LT.get_last_time_called()
                left_to_wait = min_interval - elapsed
                logging.debug('___Rate f():[{!s}] '
                              'cnt:[{!s}] '
                              'last_called:{!s} '
                              'time():{!s} '
                              'elapsed:{:6.2f} '
                              'min:{!s} '
                              'to_wait:{:6.2f}'
                              .format(func.__name__,
                                      LT.get_cnt(),
                                      time.strftime(
                                            '%T',
                                            nutime.localtime(
                                                LT.get_last_time_called())),
                                      time.strftime('%T',
                                                    nutime.localtime(xfrom)),
                                      elapsed,
                                      min_interval,
                                      left_to_wait))
                if left_to_wait > 0:
                    time.sleep(left_to_wait)

                ret = func(*args, **kwargs)

                LT.set_last_time_called()
                LT.debug('OVER')
            except Exception as ex:
                reportError(Caught=True,
                             CaughtPrefix='+++',
                             CaughtCode='000',
                             CaughtMsg='Exception on rate_limited_function',
                             exceptUse=True,
                             # exceptCode=ex.code,
                             exceptMsg=ex,
                             NicePrint=False,
                             exceptSysInfo=True)
                raise
            finally:
                LT.release()
            return ret

        return rate_limited_function

    return decorate
# -----------------------------------------------------------------------------
# Samples
# @rate_limited(5) # 5 calls per second
# def print_num(num):
#     print (num )


# =============================================================================
# Look for Config file uploadr.ini
#
config = ConfigParser.ConfigParser()
try:
    INIFiles = None
    INIFiles = config.read(os.path.join(os.path.dirname(sys.argv[0]),
                                        "uploadr.ini"))
except Exception as err:
    sys.stderr.write('[{!s}]:[{!s}][ERROR   ]:[uploadr] INI file: [{!s}] '
                     'not found or incorrect format: [{!s}]!\n'
                     .format(nutime.strftime(UPLDRConstants.TimeFormat),
                             os.getpid(),
                             os.path.join(os.path.dirname(sys.argv[0]),
                                          'uploadr.ini'),
                             str(err)))
    sys.stderr.flush()
if not INIFiles:
    sys.stderr.write('[{!s}]:[{!s}][ERROR   ]:[uploadr] INI file: [{!s}] '
                     'not found or incorrect format! Exiting...\n'
                     .format(nutime.strftime(UPLDRConstants.TimeFormat),
                             os.getpid(),
                             os.path.join(os.path.dirname(sys.argv[0]),
                                          'uploadr.ini')))
    sys.stderr.flush()
    sys.exit(2)
# -----------------------------------------------------------------------------
# Look for [Config] section file uploadr.ini file
if not config.has_section('Config'):
    sys.stderr.write('[{!s}]:[{!s}][ERROR   ]:[uploadr] INI file: [{!s}] '
                     'has no [Config] section! Exiting...\n'
                     .format(nutime.strftime(UPLDRConstants.TimeFormat),
                             os.getpid(),
                             os.path.join(os.path.dirname(sys.argv[0]),
                                          'uploadr.ini')))
    sys.stderr.flush()
    sys.exit(2)
# -----------------------------------------------------------------------------
# Obtain configuration from uploadr.ini
# Refer to contents of uploadr.ini for explanation on configuration parameters
# Obtain configuration LOGGING_LELVE from Configuration file.
# If not available or not valid assume WARNING level and notify of that fact.
# Force conversion of LOGGING_LEVEL into int() for later use in conditionals
LOGGING_LEVEL = (config.get('Config', 'LOGGING_LEVEL')
                if config.has_option('Config', 'LOGGING_LEVEL')
                else logging.WARNING)
if (int(str(LOGGING_LEVEL)) if str.isdigit(str(LOGGING_LEVEL)) else 99) not in\
                       [logging.NOTSET,
                        logging.DEBUG,
                        logging.INFO,
                        logging.WARNING,
                        logging.ERROR,
                        logging.CRITICAL]:
    LOGGING_LEVEL = logging.WARNING
    sys.stderr.write('[{!s}]:[WARNING ]:[uploadr] LOGGING_LEVEL '
                     'not defined or incorrect on INI file: [{!s}]. '
                     'Assuming WARNING level.\n'.format(
                            nutime.strftime(UPLDRConstants.TimeFormat),
                            os.path.join(os.path.dirname(sys.argv[0]),
                                         "uploadr.ini")))
    sys.stderr.flush()
LOGGING_LEVEL = int(str(LOGGING_LEVEL))
if config.has_option('Config', 'FILES_DIR'):
    try:
        FILES_DIR = unicode(eval(config.get('Config', 'FILES_DIR')), 'utf-8') \
                    if sys.version_info < (3, ) \
                    else str(eval(config.get('Config', 'FILES_DIR')))
    except Exception as err:
        sys.stderr.write('[{!s}]:[{!s}][ERROR   ]:[uploadr] FILES_DIR: '
                         'not defined or incorrect on INI file: [{!s}]\n'
                         .format(nutime.strftime(UPLDRConstants.TimeFormat),
                                 os.getpid(),
                                 str(err)))
        sys.stderr.flush()
        sys.exit(3)
else:
    # Undefined FILES_DIR. Will be reported as an error later on Main code.
    FILES_DIR = unicode('', 'utf-8') if sys.version_info < (3, ) else str('')
FLICKR = eval(config.get('Config', 'FLICKR'))
SLEEP_TIME = eval(config.get('Config', 'SLEEP_TIME'))
DRIP_TIME = eval(config.get('Config', 'DRIP_TIME'))
DB_PATH = eval(config.get('Config', 'DB_PATH'))
try:
    TOKEN_CACHE = eval(config.get('Config', 'TOKEN_CACHE'))
# CODING: Should extend this control to other parameters (Enhancement #7)
except (ConfigParser.NoOptionError, ConfigParser.NoOptionError) as err:
    sys.stderr.write('[{!s}]:[{!s}][WARNING ]:[uploadr] ({!s}) TOKEN_CACHE '
                     'not defined or incorrect on INI file: [{!s}]. '
                     'Assuming default value [{!s}].\n'
                     .format(nutime.strftime(UPLDRConstants.TimeFormat),
                             os.getpid(),
                             str(err),
                             os.path.join(os.path.dirname(sys.argv[0]),
                                          "uploadr.ini"),
                             os.path.join(os.path.dirname(sys.argv[0]),
                                          "token")))
    sys.stderr.flush()
    TOKEN_CACHE = os.path.join(os.path.dirname(sys.argv[0]), "token")
LOCK_PATH = eval(config.get('Config', 'LOCK_PATH'))
TOKEN_PATH = eval(config.get('Config', 'TOKEN_PATH'))
# Read EXCLUDED_FOLDERS and convert them into Unicode folders
inEXCLUDED_FOLDERS = eval(config.get('Config', 'EXCLUDED_FOLDERS'))
EXCLUDED_FOLDERS = []
for folder in inEXCLUDED_FOLDERS:
    # CODING: Python 2 and 3 compatibility
    EXCLUDED_FOLDERS.append(unicode(folder, 'utf-8')
                            if sys.version_info < (3, )
                            else str(folder))
    if LOGGING_LEVEL <= logging.INFO:
        sys.stderr.write('[{!s}]:[{!s}][INFO    ]:[uploadr] '
                         'folder from EXCLUDED_FOLDERS:[{!s}] '
                         'type:[{!s}]\n'
                         .format(nutime.strftime(UPLDRConstants.TimeFormat),
                                 os.getpid(),
                                 StrUnicodeOut(EXCLUDED_FOLDERS[
                                            len(EXCLUDED_FOLDERS)-1]),
                                 type(EXCLUDED_FOLDERS[
                                        len(EXCLUDED_FOLDERS)-1])))
        sys.stderr.flush()
del inEXCLUDED_FOLDERS
# Consider Unicode Regular expressions
IGNORED_REGEX = [re.compile(regex, re.UNICODE) for regex in
                 eval(config.get('Config', 'IGNORED_REGEX'))]
if LOGGING_LEVEL <= logging.INFO:
    sys.stderr.write('[{!s}]:[{!s}][INFO    ]:[uploadr] '
                     'Number of IGNORED_REGEX entries:[{!s}]\n'
                     .format(nutime.strftime(UPLDRConstants.TimeFormat),
                             os.getpid(),
                             len(IGNORED_REGEX)))
    sys.stderr.flush()
ALLOWED_EXT = eval(config.get('Config', 'ALLOWED_EXT'))
RAW_EXT = eval(config.get('Config', 'RAW_EXT'))
FILE_MAX_SIZE = eval(config.get('Config', 'FILE_MAX_SIZE'))
MANAGE_CHANGES = eval(config.get('Config', 'MANAGE_CHANGES'))
RAW_TOOL_PATH = eval(config.get('Config', 'RAW_TOOL_PATH'))
CONVERT_RAW_FILES = eval(config.get('Config', 'CONVERT_RAW_FILES'))
FULL_SET_NAME = eval(config.get('Config', 'FULL_SET_NAME'))
MAX_SQL_ATTEMPTS = eval(config.get('Config', 'MAX_SQL_ATTEMPTS'))
MAX_UPLOAD_ATTEMPTS = eval(config.get('Config', 'MAX_UPLOAD_ATTEMPTS'))


# =============================================================================
# Logging
#
# Two uses:
#   Simply log message at approriate level
#       logging.warning('Status: {!s}'.format('Setup Complete'))
#   Control additional specific output to stderr depending on level
#       if LOGGING_LEVEL <= logging.INFO:
#            logging.info('Output for {!s}:'.format('uploadResp'))
#            logging.info(xml.etree.ElementTree.tostring(
#                                                    addPhotoResp,
#                                                    encoding='utf-8',
#                                                    method='xml'))
#            <generate any further output>
#   Control additional specific output to stdout depending on level
#       if LOGGING_LEVEL <= logging.INFO:
#            niceprint ('Output for {!s}:'.format('uploadResp'))
#            xml.etree.ElementTree.dump(uploadResp)
#            <generate any further output>
#
logging.basicConfig(stream=sys.stderr,
                    level=int(LOGGING_LEVEL),
                    datefmt=UPLDRConstants.TimeFormat,
                    format=UPLDRConstants.P+'[' +
                           str(UPLDRConstants.Run)+']' +
                           '[%(asctime)s]:[%(processName)-11s]' +
                           UPLDRConstants.W +
                           '[%(levelname)-8s]:[%(name)s] %(message)s')
# =============================================================================
# Test section for logging.
# CODING: Uncomment for testing.
#   Only applicable if LOGGING_LEVEL is INFO or below (DEBUG, NOTSET)
#
# if LOGGING_LEVEL <= logging.INFO:
#     logging.info(u'sys.getfilesystemencoding:[{!s}]'.
#                     format(sys.getfilesystemencoding()))
#     logging.info('LOGGING_LEVEL Value: {!s}'.format(LOGGING_LEVEL))
#     if LOGGING_LEVEL <= logging.WARNING:
#         logging.critical('Message with {!s}'.format(
#                                     'CRITICAL UNDER min WARNING LEVEL'))
#         logging.error('Message with {!s}'.format(
#                                     'ERROR UNDER min WARNING LEVEL'))
#         logging.warning('Message with {!s}'.format(
#                                     'WARNING UNDER min WARNING LEVEL'))
#         logging.info('Message with {!s}'.format(
#                                     'INFO UNDER min WARNING LEVEL'))
if LOGGING_LEVEL <= logging.INFO:
    niceprint('Output for FLICKR Configuration:')
    pprint.pprint(FLICKR)

# =============================================================================
# CODING: Search 'Main code' section for code continuation after definitions


# -----------------------------------------------------------------------------
# FileWithCallback class
#
# For use with flickrapi upload for showing callback progress information
# Check function callback definition
#
class FileWithCallback(object):
    # -------------------------------------------------------------------------
    # class FileWithCallback __init__
    #
    def __init__(self, filename, callback):
        """ class FileWithCallback __init__
        """
        self.file = open(filename, 'rb')
        self.callback = callback
        # the following attributes and methods are required
        self.len = os.path.getsize(filename)
        self.fileno = self.file.fileno
        self.tell = self.file.tell

    # -------------------------------------------------------------------------
    # class FileWithCallback read
    #
    def read(self, size):
        """ read

        read file to upload into Flickr with FileWithCallback
        """
        if self.callback:
            self.callback(self.tell() * 100 // self.len)
        return self.file.read(size)


# -----------------------------------------------------------------------------
# callback
#
# For use with flickrapi upload for showing callback progress information
# Check function FileWithCallback definition
# Uses global args.verbose-progress parameter
#
def callback(progress):
    """ callback

    Print progress % while uploading into Flickr.
    Valid only if global variable args.verbose_progress is True
    """
    # only print rounded percentages: 0, 10, 20, 30, up to 100
    # adapt as required
    # if ((progress % 10) == 0):
    # if verbose option is set
    if (args.verbose_progress):
        if ((progress % 40) == 0):
            print(progress)


# -----------------------------------------------------------------------------
# Uploadr class
#
#   Main class for uploading of files.
#
class Uploadr:
    """ Uploadr class
    """

    # Flicrk connection authentication token
    token = None

    # -------------------------------------------------------------------------
    # class Uploadr __init__
    #
    def __init__(self):
        """ class Uploadr __init__

        Gets FlickrAPI cached token, if available.
        Adds .3gp mimetime as video.
        """

        # get self.token/nuflickr from Cache (getCachedToken)
        self.token = self.getCachedToken()

        # Add mimetype .3gp to allow detection of .3gp as video
        logging.info('Adding mimetpye "video/3gp"/".3gp"')
        mimetypes.add_type('video/3gpp', '.3gp')
        if not mimetypes.types_map['.3gp'] == 'video/3gpp':
            reportError(Caught=True,
                        CaughtPrefix='xxx',
                        CaughtCode='001',
                        CaughtMsg='Not able to add mimetype'
                                  ' ''video/3gp''/''.3gp'' correctly',
                        NicePrint=True)
        else:
            logging.warning('Added mimetype "video/3gp"/".3gp" correctly.')

    # -------------------------------------------------------------------------
    # useDBLock
    #
    # Control use of DB lock. acquire/release
    #
    def useDBLock(self, useDBthisLock, useDBoperation):
        """ useDBLock

            useDBthisLock  = lock to be used
            useDBoperation = True => Lock
                           = False => Release
        """

        useDBLockReturn = False
        # CODING: Not used for now:
        # useDBLockTimeout = 0.5

        logging.debug('Entering useDBLock with useDBoperation:[{!s}].'
                      .format(useDBoperation))

        if useDBthisLock is None:
            return useDBLockReturn

        if useDBoperation is None:
            return useDBLockReturn

        if (args.processes is not None) and\
           (args.processes) and \
           (args.processes > 0):
            if useDBoperation:
                # Control for when running multiprocessing set locking
                logging.debug('===Multiprocessing=== in.lock.acquire')
                try:
                    # CODING: Not used for now
                    # if lock.acquire(timeout=useDBLockTimeout):
                    if useDBthisLock.acquire():
                        useDBLockReturn = True
                    # CONDIG: not used for now
                    # else:
                    #     useDBthisLock.release()
                    #     logging.warning('===Multiprocessing=== '
                    #                     'TIMEOUT in.lock.acquire')
                    #     useDBLockReturn = False
                except:
                    reportError(Caught=True,
                                CaughtPrefix='+++ ',
                                CaughtCode='002',
                                CaughtMsg='Caught an exception lock.acquire',
                                NicePrint=True,
                                exceptSysInfo=True)
                    raise
                logging.info('===Multiprocessing=== out.lock.acquire')
            else:
                # Control for when running multiprocessing release locking
                logging.debug('===Multiprocessing=== in.lock.release')
                try:
                    useDBthisLock.release()
                    useDBLockReturn = True
                except:
                    reportError(Caught=True,
                                CaughtPrefix='+++ ',
                                CaughtCode='003',
                                CaughtMsg='Caught an exception lock.release',
                                NicePrint=True,
                                exceptSysInfo=True)
                    # Raise aborts execution
                    raise
                logging.info('===Multiprocessing=== out.lock.release')

            logging.info('Exiting useDBLock with useDBoperation:[{!s}]. '
                         'Result:[{!s}]'
                         .format(useDBoperation, useDBLockReturn))
        else:
            useDBLockReturn = True
            logging.warning('(No multiprocessing. Nothing to do) '
                            'Exiting useDBLock with useDBoperation:[{!s}]. '
                            'Result:[{!s}]'
                            .format(useDBoperation, useDBLockReturn))

        return useDBLockReturn

    # -------------------------------------------------------------------------
    # niceprocessedfiles
    #
    # Nicely print number of processed files
    #
    def niceprocessedfiles(self, count, cTotal, total):
        """
        niceprocessedfiles

        count  = Nicely print number of processed files rounded to 100's
        cTotal = Shows also the total number of items to be processed
        total  = if true shows the final count (use at the end of processing)
        """

        if not total:
            if (int(count) % 100 == 0):
                niceprint('\t{!s} of \t{!s} files processed (uploaded, md5ed '
                          'or timestamp checked).'
                          .format(count, cTotal))
        else:
            if (int(count) % 100 > 0):
                niceprint('\t{!s} of \t{!s} files processed (uploaded, md5ed '
                          'or timestamp checked).'
                          .format(count, cTotal))

        sys.stdout.flush()


    # -------------------------------------------------------------------------
    # authenticate
    #
    # Authenticates via flickrapi on flickr.com
    #
    def authenticate(self):
        """
        Authenticate user so we can upload files.
        Assumes the cached token is not available or valid.
        """
        global nuflickr

        # Instantiate nuflickr for connection to flickr via flickrapi
        nuflickr = flickrapi.FlickrAPI(FLICKR["api_key"],
                                       FLICKR["secret"],
                                       token_cache_location=TOKEN_CACHE)
        # Get request token
        niceprint('Getting new token.')
        nuflickr.get_request_token(oauth_callback='oob')

        # Show url. Copy and paste it in your browser
        authorize_url = nuflickr.auth_url(perms=u'delete')
        print(authorize_url)

        # Prompt for verifier code from the user.
        verifier = unicode(raw_input('Verifier code (NNN-NNN-NNN): ')) \
                   if sys.version_info < (3, ) \
                   else input('Verifier code (NNN-NNN-NNN): ')

        logging.warning('Verifier: {!s}'.format(verifier))

        # Trade the request token for an access token
        try:
            nuflickr.get_access_token(verifier)
        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='005',
                        CaughtMsg='Flickrapi exception on get_access_token. '
                                  'Exiting...',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True,
                        exceptSysInfo=True)
            sys.exit(4)

        niceprint('{!s} with {!s} permissions: {!s}'.format(
                                    'Check Authentication',
                                    'delete',
                                    nuflickr.token_valid(perms='delete')))
        # logging.critical('Token Cache: {!s}', nuflickr.token_cache.token)

    # -------------------------------------------------------------------------
    # getCachedToken
    #
    # If available, obtains the flickrapi Cached Token from local file.
    # Saves the token on the Class variable "token"
    # Saves the token on the global variable nuflickr.
    #
    def getCachedToken(self):
        """
        Attempts to get the flickr token from disk.
        """
        global nuflickr

        logging.info('Obtaining Cached token')
        logging.debug('TOKEN_CACHE:[{!s}]'.format(TOKEN_CACHE))
        nuflickr = flickrapi.FlickrAPI(FLICKR["api_key"],
                                       FLICKR["secret"],
                                       token_cache_location=TOKEN_CACHE)

        try:
            # Check if token permissions are correct.
            if nuflickr.token_valid(perms='delete'):
                logging.info('Cached token obtained: {!s}'
                             .format(nuflickr.token_cache.token))
                return nuflickr.token_cache.token
            else:
                logging.warning('Token Non-Existant.')
                return None
        except:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='007',
                        CaughtMsg='Unexpected error in token_valid',
                        exceptSysInfo=True)
            raise

    # -------------------------------------------------------------------------
    # checkToken
    #
    # If available, obtains the flickrapi Cached Token from local file.
    #
    # Returns
    #   True: if global token is defined and allows flicrk 'delete' operation
    #   False: if global token is not defined or flicrk 'delete' is not allowed
    #
    def checkToken(self):
        """ checkToken
        flickr.auth.checkToken

        Returns the credentials attached to an authentication token.
        """
        global nuflickr

        logging.warning('checkToken:(self.token is None):[{!s}]'
                        'checkToken:(nuflickr is None):[{!s}]'
                        'checkToken:(nuflickr.token_cache.token is None):'
                        '[{!s}]'
                        .format(self.token is None,
                                nuflickr is None,
                                nuflickr.token_cache.token is None))

        # if (self.token is None):
        if (nuflickr.token_cache.token is None):
            return False
        else:
            return True

    # -------------------------------------------------------------------------
    # removeExcludedMedia
    #
    # When EXCLUDED_FOLDERS defintion changes. You can run the -g
    # or --remove-excluded option in order to remove files previously uploaded.
    #
    def removeExcludedMedia(self):
        """ removeExcludedMedia

        Remove previously uploaded files, that are now being excluded due to
        change of the INI file configuration EXCLUDED_FOLDERS.
        """
        niceprint('*****Removing files from Excluded Folders*****')

        if (not flick.checkToken()):
            flick.authenticate()
        con = lite.connect(DB_PATH)
        con.text_factory = str

        with con:
            cur = con.cursor()
            cur.execute("SELECT files_id, path FROM files")
            rows = cur.fetchall()

            for row in rows:
                logging.debug('Checking file_id:[{!s}] file:[{!s}] '
                              'isFileExcluded?'
                              .format(StrUnicodeOut(row[0]),
                                      StrUnicodeOut(row[1])))
                logging.debug('type(row[1]):[{!s}]'.format(type(row[1])))
                # row[0] is photo_id
                # row[1] is filename
                # CODING
                # debug#A with unicode
                if (self.isFileExcluded(unicode(row[1], 'utf-8')
                                        if sys.version_info < (3, )
                                        else str(row[1]))):
                # debug#B with StrUnicodeOut
                # if (self.isFileExcluded(StrUnicodeOut(row[1])
                #                         if sys.version_info < (3, )
                #                         else str(row[1]))):
                # debug#C with row[1] => Fails TravisCI test 331.5
                # if (self.isFileExcluded(row[1]
                #                         if sys.version_info < (3, )
                #                         else str(row[1]))):
                    self.deleteFile(row, cur)

        # Closing DB connection
        if con is not None:
            con.close()

        niceprint('*****Completed files from Excluded Folders*****')

    # -------------------------------------------------------------------------
    # removeDeleteMedia
    #
    # Remove files deleted at the local source
    #
    def removeDeletedMedia(self):
        """
        Remove files deleted at the local source
            loop through database
            check if file exists
            if exists, continue
            if not exists, delete photo from fickr (flickr.photos.delete.html)
        """

        niceprint('*****Removing deleted files*****')

        if (not flick.checkToken()):
            flick.authenticate()
        con = lite.connect(DB_PATH)
        con.text_factory = str

        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT files_id, path FROM files")
                rows = cur.fetchall()
                niceprint('[{!s}] will be checked for Removal...'
                          .format(str(len(rows))))
            except lite.Error as e:
                reportError(Caught=True,
                    CaughtPrefix='+++ DB',
                    CaughtCode='008',
                    CaughtMsg='DB error on SELECT: [{!s}]'
                              .format(e.args[0]),
                    NicePrint=True)
                if con is not None:
                    con.close()
                return False

            count = 0
            for row in rows:
                if (not os.path.isfile(row[1].decode('utf-8')
                                       if isThisStringUnicode(row[1])
                                       else row[1])):
                    success = self.deleteFile(row, cur)
                    logging.warning('deleteFile result: {!s}'.format(success))
                    count = count + 1
                    if (count % 3 == 0):
                        niceprint('\t[{!s}] files removed...'
                                  .format(str(count)))
            if (count % 100 > 0):
                niceprint('\t[{!s}] files removed...'
                          .format(str(count)))

        # Closing DB connection
        if con is not None:
            con.close()

        niceprint('*****Completed deleted files*****')

    # -------------------------------------------------------------------------
    # upload
    #
    #  Main cycle for file upload
    #
    def upload(self):
        """ upload
        Add files to flickr and into their sets(Albums)
        If enabled CHANGE_MEDIA, checks for file changes and updates flickr
        """

        global nulockDB
        global numutex
        global nurunning

        niceprint("*****Uploading files*****")

        allMedia = self.grabNewFiles()
        # If managing changes, consider all files
        if MANAGE_CHANGES:
            logging.warning('MANAGED_CHANGES is True. Reviewing allMedia.')
            changedMedia = allMedia

        # If not, then get just the new and missing files
        else:
            logging.warning('MANAGED_CHANGES is False. Reviewing only '
                            'changedMedia.')
            con = lite.connect(DB_PATH)
            con.text_factory = str
            with con:
                cur = con.cursor()
                cur.execute("SELECT path FROM files")
                existingMedia = set(file[0] for file in cur.fetchall())
                changedMedia = set(allMedia) - existingMedia

        changedMedia_count = len(changedMedia)
        UPLDRConstants.nuMediacount = changedMedia_count
        niceprint('Found [{!s}] files to upload.'
                  .format(str(changedMedia_count)))

        if (args.bad_files):
            # Cater for bad files
            con = lite.connect(DB_PATH)
            con.text_factory = str
            with con:
                cur = con.cursor()
                cur.execute("SELECT path FROM badfiles")
                badMedia = set(file[0] for file in cur.fetchall())
                changedMedia = set(changedMedia) - badMedia
                logging.debug('len(badMedia)'.format(len(badMedia)))

            changedMedia_count = len(changedMedia)
            # Careful with control on "i != changedMedia_count - 1"
            # UPLDRConstants.nuMediacount = changedMedia_count
            niceprint('Removing {!s} badfiles. Found {!s} files to upload.'
                      .format(len(badMedia),
                              changedMedia_count))

        # running in multi processing mode
        if (args.processes and args.processes > 0):
            logging.debug('Running Pool of [{!s}] processes...'
                          .format(args.processes))
            logging.debug('__name__:[{!s}] to prevent recursive calling)!'
                          .format(__name__))

            # To prevent recursive calling, check if __name__ == '__main__'
            if __name__ == '__main__':
                logging.debug('===Multiprocessing=== Setting up logger!')
                multiprocessing.log_to_stderr()
                logger = multiprocessing.get_logger()
                logger.setLevel(LOGGING_LEVEL)

                logging.debug('===Multiprocessing=== Lock defined!')

                # -------------------------------------------------------------------------
                # chunk
                #
                # Divides an iterable in slices/chunks of size size
                #
                from itertools import islice

                def chunk(it, size):
                    """
                        Divides an iterable in slices/chunks of size size
                    """
                    it = iter(it)
                    # lambda: creates a returning expression function
                    # which returns slices
                    # iter, with the second argument () stops creating
                    # iterators when it reaches the end
                    return iter(lambda: tuple(islice(it, size)), ())

                uploadPool = []
                nulockDB = multiprocessing.Lock()
                nurunning = multiprocessing.Value('i', 0)
                numutex = multiprocessing.Lock()

                sz = (len(changedMedia) // int(args.processes)) \
                     if ((len(changedMedia) // int(args.processes)) > 0) \
                     else 1

                logging.debug('len(changedMedia):[{!s}] '
                              'int(args.processes):[{!s}] '
                              'sz per process:[{!s}]'
                              .format(len(changedMedia),
                                      int(args.processes),
                                      sz))

                # Split the Media in chunks to distribute accross Processes
                for nuChangeMedia in chunk(changedMedia, sz):
                    logging.warning('===Actual/Planned Chunk size: '
                                    '[{!s}]/[{!s}]'
                                    .format(len(nuChangeMedia), sz))
                    logging.debug('===type(nuChangeMedia)=[{!s}]'
                                  .format(type(nuChangeMedia)))
                    logging.debug('===Job/Task Process: Creating...')
                    uploadTask = multiprocessing.Process(
                                        target=self.uploadFileX,
                                        args=(nulockDB,
                                              nurunning,
                                              numutex,
                                              nuChangeMedia,))
                    uploadPool.append(uploadTask)
                    logging.debug('===Job/Task Process: Starting...')
                    uploadTask.start()
                    logging.debug('===Job/Task Process: Started')
                    if (args.verbose):
                        niceprint('===Job/Task Process: [{!s}] Started '
                                  'with pid:[{!s}]'
                                  .format(uploadTask.name,
                                          uploadTask.pid))

                # Check status of jobs/tasks in the Process Pool
                if LOGGING_LEVEL <= logging.DEBUG:
                    logging.debug('===Checking Processes launched/status:')
                    for j in uploadPool:
                        niceprint('{!s}.is_alive = {!s}'
                                  .format(j.name, j.is_alive()))

                # Regularly print status of jobs/tasks in the Process Pool
                # Prints status while there are processes active
                # Exits when all jobs/tasks are done.
                while (True):
                    if not (any(multiprocessing.active_children())):
                        logging.debug('===No active children Processes.')
                        break
                    for p in multiprocessing.active_children():
                        logging.debug('==={!s}.is_alive = {!s}'
                                      .format(p.name, p.is_alive()))
                        if (args.verbose):
                            niceprint('==={!s}.is_alive = {!s}'
                                      .format(p.name, p.is_alive()))
                        uploadTaskActive = p
                    logging.info('===Will wait for 60 on {!s}.is_alive = {!s}'
                                 .format(uploadTaskActive.name,
                                         uploadTaskActive.is_alive()))
                    if (args.verbose):
                        niceprint('===Will wait for 60 on {!s}.is_alive = {!s}'
                                  .format(uploadTaskActive.name,
                                          uploadTaskActive.is_alive()))

                    uploadTaskActive.join(timeout=60)
                    logging.info('===Waited for 60s on {!s}.is_alive = {!s}'
                                 .format(uploadTaskActive.name,
                                         uploadTaskActive.is_alive()))
                    if (args.verbose):
                        niceprint('===Waited for 60s on {!s}.is_alive = {!s}'
                                  .format(uploadTaskActive.name,
                                          uploadTaskActive.is_alive()))

                # Wait for join all jobs/tasks in the Process Pool
                # All should be done by now!
                for j in uploadPool:
                    j.join()
                    if (args.verbose):
                        niceprint('==={!s} (is alive: {!s}).exitcode = {!s}'
                                  .format(j.name, j.is_alive(), j.exitcode))

                logging.warning('===Multiprocessing=== pool joined! '
                                'All processes finished.')
                niceprint('===Multiprocessing=== pool joined! '
                          'All processes finished.')

                # Will release (set to None) the nulockDB lock control
                # this prevents subsequent calls to useDBLock( nuLockDB, False)
                # to raise exception:
                #    ValueError('semaphore or lock released too many times')
                if (args.verbose):
                    niceprint('===Multiprocessing=== pool joined! '
                              'What happens to nulockDB is None:[{!s}]? '
                              'It seems not, it still has a value! '
                              'Setting it to None!'
                              .format(nulockDB is None))
                nulockDB = None

                # Show number of total files processed
                self.niceprocessedfiles(nurunning.value,
                                        UPLDRConstants.nuMediacount,
                                        True)

            else:
                niceprint('Pool not in __main__ process. '
                          'Windows or recursive?'
                          'Not possible to run Multiprocessing mode')
        # running in single processing mode
        else:
            count = 0
            for i, file in enumerate(changedMedia):
                logging.debug('file:[{!s}] type(file):[{!s}]'
                              .format(file, type(file)))
                # lock parameter not used (set to None) under single processing
                success = self.uploadFile(lock=None, file=file)
                if args.drip_feed and success and i != changedMedia_count - 1:
                    niceprint('Waiting [{!s}] seconds before next upload'
                              .format(str(DRIP_TIME)))
                    nutime.sleep(DRIP_TIME)
                count = count + 1
                self.niceprocessedfiles(count,
                                        UPLDRConstants.nuMediacount,
                                        False)

            # Show number of total files processed
            self.niceprocessedfiles(count, UPLDRConstants.nuMediacount, True)

        niceprint("*****Completed uploading files*****")

    # -------------------------------------------------------------------------
    # convertRawFiles
    #
    def convertRawFiles(self):
        """ convertRawFiles

        CODING: Not converted yet.
        """

        # CODING: Not tested. Not in use at this time. I do not use RAW Files.
        # Also you need Image-ExifTool-9.69 or similar installed.
        # Check INI config file for and make sure you keep
        # CONVERT_RAW_FILES = False
        # Change and use at your own risk at this time.

        """ convertRawFiles
        """
        if (not CONVERT_RAW_FILES):
            return

        niceprint('*****Converting files*****')
        for ext in RAW_EXT:
            niceprint('About to convert files with extension: [{!s}]'
                      .format(StrUnicodeOut(ext)))

            for dirpath, dirnames, filenames in os.walk(
                                                FILES_DIR,
                                                followlinks=True):
                if '.picasaoriginals' in dirnames:
                    dirnames.remove('.picasaoriginals')
                if '@eaDir' in dirnames:
                    dirnames.remove('@eaDir')
                for f in filenames:

                    fileExt = f.split(".")[-1]
                    filename = f.split(".")[0]
                    if (fileExt.lower() == ext):

                        if (not os.path.exists(dirpath + "/" +
                                               filename + ".JPG")):
                            niceprint('About to create JPG from raw[{!s}/{!s}]'
                                      .format(StrUnicodeOut(dirpath),
                                              StrUnicodeOut(f)))
                            # CODING if previous like ok, eliminate next line:
                            # if isThisStringUnicode(dirpath):
                            #     if isThisStringUnicode(f):
                            #         print(u'About to create JPG from raw ' +
                            #               dirpath.encode('utf-8') +
                            #               u'/' +
                            #               f.encode('utf-8'))
                            #     else:
                            #         print(u'About to create JPG from raw ' +
                            #               dirpath.encode('utf-8') +
                            #               u'/' +
                            #               f)
                            # elif isThisStringUnicode(f):
                            #     print("About to create JPG from raw " +
                            #           dirpath +
                            #           "/" +
                            #           f.encode('utf-8'))
                            # else:
                            #     print("About to create JPG from raw " +
                            #           dirpath + "/" + f)

                            flag = ""
                            if ext is "cr2":
                                flag = "PreviewImage"
                            else:
                                flag = "JpgFromRaw"

                            command = RAW_TOOL_PATH + "exiftool -b -" + flag +\
                                      " -w .JPG -ext " + ext + " -r '" +\
                                      dirpath + "/" +\
                                      filename + "." + fileExt + "'"
                            logging.info(command)

                            p = subprocess.call(command, shell=True)

                        if (not os.path.exists(dirpath + "/" +
                                               filename + ".JPG_original")):

                            niceprint('About to copy tags from:[{!s}/{!s}]'
                                      .format(dirpath.encode('utf-8')
                                              if isThisStringUnicode(dirpath)
                                              else dirpath,
                                              f.encode('utf-8')
                                              if isThisStringUnicode(f)
                                              else f))
                            # CODING if line above ok remove next lines
                            # if isThisStringUnicode(dirpath):
                            #     if isThisStringUnicode(f):
                            #         print(u'About to copy tags from ' +
                            #               dirpath.encode('utf-8') +
                            #               u'/' +
                            #               f.encode('utf-8') +
                            #               u' to JPG.')
                            #     else:
                            #         print(u'About to copy tags from ' +
                            #               dirpath.encode('utf-8') +
                            #               u'/' +
                            #               f +
                            #               " to JPG.")
                            # elif isThisStringUnicode(f):
                            #     print("About to copy tags from " +
                            #           dirpath +
                            #           "/" +
                            #           f.encode('utf-8') +
                            #           u' to JPG.')
                            # else:
                            #     print("About to copy tags from " +
                            #           dirpath +
                            #           "/" +
                            #           f +
                            #           " to JPG.")

                            command = RAW_TOOL_PATH +\
                                      "exiftool -tagsfromfile '" +\
                                      dirpath + "/" + f +\
                                      "' -r -all:all -ext JPG '" +\
                                      dirpath + "/" + filename + ".JPG'"
                            logging.info(command)

                            p = subprocess.call(command, shell=True)

                            niceprint('Finished copying tags.')

            niceprint('Finished converting files with extension:[{!s}]'
                      .format(StrUnicodeOut(ext)))

        if p is None:
            del p

        niceprint('*****Completed converting files*****')

    # -------------------------------------------------------------------------
    # grabNewFiles
    #
    def grabNewFiles(self):
        """ grabNewFiles

            Select files from FILES_DIR taking into consideration
            EXCLUDED_FOLDERS and IGNORED_REGEX filenames.
            Returns sorted file list.
        """

        files = []
        for dirpath, dirnames, filenames in\
                os.walk(FILES_DIR, followlinks=True):

            # Prevent walking thru files in the list of EXCLUDED_FOLDERS
            # Reduce time by not checking a file in an excluded folder

            # CODING
            # For Debugging: UnicodeWarning comparison
            logging.debug('Check for UnicodeWarning comparison '
                          'dirpath:[{!s}] type:[{!s}]'
                          .format(StrUnicodeOut(os.path.basename(
                                                  os.path.normpath(dirpath))),
                                  type(os.path.basename(
                                                  os.path.normpath(dirpath)))))
            if os.path.basename(os.path.normpath(dirpath)) \
                in EXCLUDED_FOLDERS:
                dirnames[:] = []
                filenames[:] = []
                logging.warning('Folder [{!s}] on path [{!s}] excluded.'
                                .format(
                                    StrUnicodeOut(os.path.basename(
                                                    os.path.normpath(dirpath))
                                                 ),
                                    StrUnicodeOut(os.path.normpath(dirpath)))
                               )
                niceprint('Folder [{!s}] on path [{!s}] excluded.'
                          .format(StrUnicodeOut(os.path.basename(
                                                   os.path.normpath(dirpath))
                                               ),
                                StrUnicodeOut(os.path.normpath(dirpath))))

            for f in filenames:
                filePath = os.path.join(dirpath, f)
                # CODING: No need as files in EXCLUDED_FOLDERS were already
                # removed.
                # if self.isFileExcluded(filePath):
                #     logging.debug('File {!s} in EXCLUDED_FOLDERS:'
                #                   .format(filePath.encode('utf-8')))
                #     continue
                if any(ignored.search(f) for ignored in IGNORED_REGEX):
                    logging.debug('File {!s} in IGNORED_REGEX:'
                                  .format(filePath.encode('utf-8')))
                    continue
                ext = os.path.splitext(os.path.basename(f))[1][1:].lower()
                if ext in ALLOWED_EXT:
                    fileSize = os.path.getsize(dirpath + "/" + f)
                    if (fileSize < FILE_MAX_SIZE):
                        files.append(
                            os.path.normpath(
                                StrUnicodeOut(dirpath) +
                                StrUnicodeOut("/") +
                                StrUnicodeOut(f).replace("'", "\'")))
                    else:
                        niceprint('Skipping file due to '
                                  'size restriction: [{!s}]'.format(
                                        os.path.normpath(
                                            StrUnicodeOut(dirpath) +
                                            StrUnicodeOut('/') +
                                            StrUnicodeOut(f))))
        files.sort()
        if LOGGING_LEVEL <= logging.DEBUG:
            niceprint('Pretty Print Output for {!s}:'.format('files'))
            pprint.pprint(files)

        return files

    # -------------------------------------------------------------------------
    # isFileExcluded
    #
    # Check if a filename is within the list of EXCLUDED_FOLDERS. Returns:
    #   True = if filename's folder is within one of the EXCLUDED_FOLDERS
    #   False = if filename's folder not on one of the EXCLUDED_FOLDERS
    #
    def isFileExcluded(self, filename):
        """ isFileExcluded

        Returns True if a file is within an EXCLUDED_FOLDERS directory/folder
        """
        for excluded_dir in EXCLUDED_FOLDERS:
            logging.debug('type(excluded_dir):[{!s}]'
                          .format(type(excluded_dir)))
            logging.debug('is excluded_dir unicode?[{!s}]'
                          .format(isThisStringUnicode(excluded_dir)))
            logging.debug('type(filename):[{!s}]'
                          .format(type(filename)))
            logging.debug('is filename unicode?[{!s}]'
                          .format(isThisStringUnicode(filename)))
            logging.debug('is os.path.dirname(filename) unicode?[{!s}]'
                          .format(isThisStringUnicode(
                                        os.path.dirname(filename))))
            logging.debug('excluded_dir:[{!s}] filename:[{!s}]'
                          .format(StrUnicodeOut(excluded_dir),
                                  StrUnicodeOut(filename)))
            # Now everything should be in Unicode
            if excluded_dir in os.path.dirname(filename):
                logging.debug('Returning isFileExcluded:[True]')
                return True

        logging.debug('Returning isFileExcluded:[False]')
        return False

    # -------------------------------------------------------------------------
    # updatedVideoDate
    #
    """ updatedVideoDate

    Update the video date taken based on last_modified time of file
    """
    def updatedVideoDate(self, xfile_id, xfile, xlast_modified):

        # Update Date/Time on Flickr for Video files
        # Flickr doesn't read it  from the video file itself.
        filetype = mimetypes.guess_type(xfile)
        logging.info('filetype is:[{!s}]'.format('None'
                                                 if filetype is None
                                                 else filetype[0]))

        # update video date/time TAKEN.
        # Flickr doesn't read it  from the video file itself.
        if ((not filetype[0] is None) and ('video' in filetype[0])):
            res_set_date = None
            video_date = nutime.strftime('%Y-%m-%d %H:%M:%S',
                                         nutime.localtime(xlast_modified))
            logging.info('video_date:[{!s}]'.format(video_date))

            try:
                res_set_date = flick.photos_set_dates(xfile_id,
                                                      str(video_date))
                logging.debug('Output for {!s}:'.format('res_set_date'))
                logging.debug(xml.etree.ElementTree.tostring(
                                                       res_set_date,
                                                       encoding='utf-8',
                                                       method='xml'))
                if self.isGood(res_set_date):
                    niceprint('Successfully set date [{!s}] for file:[{!s}].'
                              .format(StrUnicodeOut(video_date),
                                      StrUnicodeOut(xfile)))
            except (IOError, ValueError, httplib.HTTPException):
                reportError(Caught=True,
                            CaughtPrefix='+++',
                            CaughtCode='010',
                            CaughtMsg='Error setting date '
                                      'file_id:[{!s}]'
                                      .format(xfile_id),
                            NicePrint=True,
                            exceptSysInfo=True)
                raise
            finally:
                if not self.isGood(res_set_date):
                    raise IOError(res_set_date)

            niceprint('Successfully set date [{!s}] for pic [{!s}]'
                      .format(StrUnicodeOut(video_date),
                              StrUnicodeOut(xfile)))
            return True
        else:
            return True

    # -------------------------------------------------------------------------
    # uploadFileX
    #
    # uploadFile wrapper for multiprocessing purposes
    #
    def uploadFileX(self, lock, running, mutex, filelist):
        """ uploadFileX

            Wrapper function for multiprocessing support to call uploadFile
            with a chunk of the files.
            lock = for database access control in multiprocessing
            running = shared value to count processed files in multiprocessing
            mutex = for running access control in multiprocessing
        """

        for i, f in enumerate(filelist):
            logging.warning('===Current element of Chunk: [{!s}][{!s}]'
                            .format(i, f))
            self.uploadFile(lock, f)

            # no need to check for
            # (args.processes and args.processes > 0):
            # as uploadFileX is already multiprocessing

            logging.debug('===Multiprocessing=== in.mutex.acquire(w)')
            mutex.acquire()
            running.value += 1
            xcount = running.value
            mutex.release()
            logging.warning('===Multiprocessing=== out.mutex.release(w)')

            # Show number of files processed so far
            self.niceprocessedfiles(xcount, UPLDRConstants.nuMediacount, False)


    # -------------------------------------------------------------------------
    # uploadFile
    #
    # uploads a file into flickr
    #   lock = parameter for multiprocessing control of access to DB.
    #          if args.processes = 0 then lock can be None as it is not used
    #   file = file to be uploaded
    #
    def uploadFile(self, lock, file):
        """ uploadFile
        uploads file into flickr

        May run in single or multiprocessing mode

        lock = parameter for multiprocessing control of access to DB.
               (if args.processes = 0 then lock may be None as it is not used)
        file = file to be uploaded
        """

        global nuflickr

        # ---------------------------------------------------------------------
        # dbInsertIntoFiles
        #
        def dbInsertIntoFiles(lock,
                              file_id, file, file_checksum, last_modified):
            """ dbInsertIntoFiles

            Insert into local DB files table.

            lock          = for multiprocessing
            file_id       = pic id
            file          = filename
            file_checksum = md5 checksum
            last_modified = Last modified time
            """

            # Database Locked is returned often on this INSERT
            # Will try MAX_SQL_ATTEMPTS...
            for x in range(0, MAX_SQL_ATTEMPTS):
                logging.info('BEGIN SQL:[{!s}]...[{!s}/{!s} attempts].'
                             .format('INSERT INTO files', x, MAX_SQL_ATTEMPTS))
                DBexception = False
                try:
                    # Acquire DBlock if in multiprocessing mode
                    self.useDBLock(lock, True)
                    cur.execute(
                        'INSERT INTO files '
                        '(files_id, path, md5, '
                        'last_modified, tagged) '
                        'VALUES (?, ?, ?, ?, 1)',
                        (file_id, file, file_checksum,
                         last_modified))
                except lite.Error as e:
                    DBexception = True
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='030',
                                CaughtMsg='DB error on INSERT: '
                                          '[{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True,
                                exceptSysInfo=True)
                finally:
                    # Release DBlock if in multiprocessing mode
                    self.useDBLock(lock, False)

                if DBexception:
                    logging.error('Sleep 2 and retry SQL...')
                    niceprint('Sleep 2 and retry SQL...')
                    nutime.sleep(2)
                else:
                    logging.info(
                        'END SQL:[{!s}]...[{!s}/{!s} attempts].'
                        .format('INSERT INTO files',
                                x,
                                MAX_SQL_ATTEMPTS))
                    # Break the cycle of SQL_ATTEMPTS and continue
                    break
        # ---------------------------------------------------------------------

        if (args.dry_run is True):
            niceprint('Dry Run Uploading file:[{!s}]...'
                      .format(StrUnicodeOut(file)))
            return True

        if (args.verbose):
            niceprint('Checking file:[{!s}]...'
                      .format(StrUnicodeOut(file)))

        setName = self.getSetNameFromFile(file, FILES_DIR, FULL_SET_NAME)

        success = False
        # For tracking bad response from search_photos
        TraceBackIndexError = False
        con = lite.connect(DB_PATH)
        con.text_factory = str
        with con:
            cur = con.cursor()
            logging.debug('Output for uploadFILE SELECT:')
            logging.debug('{!s}: {!s}'.format('SELECT rowid,files_id,path,'
                                              'set_id,md5,tagged,'
                                              'last_modified FROM '
                                              'files WHERE path = ?',
                                              file))

            try:
                # Acquire DB lock if running in multiprocessing mode
                self.useDBLock(lock, True)
                cur.execute('SELECT rowid,files_id,path,set_id,md5,tagged,'
                            'last_modified FROM files WHERE path = ?',
                            (file,))
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='015',
                            CaughtMsg='DB error on SELECT: [{!s}]'
                                      .format(e.args[0]),
                            NicePrint=True)
            finally:
                # Release DB lock if running in multiprocessing mode
                self.useDBLock(lock, False)

            row = cur.fetchone()
            logging.debug('row {!s}:'.format(row))

            # use file modified timestamp to check for changes
            last_modified = os.stat(file).st_mtime
            file_checksum = None

            # Check if file is already loaded
            if (args.not_is_already_uploaded):
                isLoaded = False
                isfile_id = None
                isNoSet = None
                logging.warning('not_is_photo_already_uploaded:[{!s}] '
                                .format(isLoaded))
            else:
                file_checksum = self.md5Checksum(file)
                isLoaded, isCount, isfile_id, isNoSet = \
                                self.is_photo_already_uploaded(file,
                                                               file_checksum,
                                                               setName)
                logging.info('is_photo_already_uploaded:[{!s}] '
                              'count:[{!s}] pic:[{!s}] '
                              'row is None == [{!s}] '
                              'isNoSet:[{!s}]'
                              .format(isLoaded, isCount,
                                      isfile_id, row is None,
                                      isNoSet))

            if isLoaded and row is None:
                if file_checksum is None:
                    file_checksum = self.md5Checksum(file)

                # Insert into DB files
                logging.warning('ALREADY LOADED. '
                                'DO NOT PERFORM ANYTHING ELSE. '
                                'ROW IS NONE... UPDATING LOCAL DATABASE.')
                niceprint('Already loaded file:[{!s}]...'
                          'On Album:[{!s}]... UPDATING LOCAL DATABASE.'
                          .format(StrUnicodeOut(file),
                                  StrUnicodeOut(setName)))
                dbInsertIntoFiles(lock, isfile_id, file,
                                  file_checksum, last_modified)

                # Update the Video Date Taken
                self.updatedVideoDate(isfile_id, file, last_modified)

            elif row is None:
                if (args.verbose):
                    niceprint('Uploading file:[{!s}]...'
                              'On Album:[{!s}]...'
                              .format(StrUnicodeOut(file),
                                      StrUnicodeOut(setName)))

                logging.warning('Uploading file:[{!s}]... '
                                'On Album:[{!s}]...'
                                .format(StrUnicodeOut(file),
                                        StrUnicodeOut(setName)))

                if file_checksum is None:
                    file_checksum = self.md5Checksum(file)

                # Title Handling
                if args.title:  # Replace
                    FLICKR["title"] = args.title
                if args.description:  # Replace
                    FLICKR["description"] = args.description
                if args.tags:  # Append a space to later add -t TAGS
                    FLICKR["tags"] += " "
                    if args.verbose:
                        niceprint('TAGS:[{} {}]'
                                  .format(FLICKR["tags"],
                                         args.tags).replace(',', ''))

                # if FLICKR["title"] is empty...
                # if filename's exif title is empty...
                #   Can't check without import exiftool
                # set it to filename OR do not load it up in order to
                # allow flickr.com itself to set it up
                # NOTE: an empty title forces flickrapi/auth.py
                # code at line 280 to encode into utf-8 the filename
                # this causes an error
                # UnicodeDecodeError: 'ascii' codec can't decode byte 0xc3
                # in position 11: ordinal not in range(128)
                # Worked around it by forcing the title to filename
                if FLICKR["title"] == "":
                    path_filename, title_filename = os.path.split(file)
                    logging.info('path:[{!s}] '
                                 'filename:[{!s}] '
                                 'ext=[{!s}]'.format(
                                      path_filename,
                                      title_filename,
                                      os.path.splitext(title_filename)[1]))
                    title_filename = os.path.splitext(title_filename)[0]
                    logging.warning('title_name:[{!s}]'.format(title_filename))
                else:
                    title_filename = FLICKR["title"]
                    logging.warning('title from INI file:[{!s}]'
                                    .format(title_filename))

                # CODING focus this try and not cover so much code!
                try:
                    # Perform actual upload of the file
                    search_result = None
                    for x in range(0, MAX_UPLOAD_ATTEMPTS):
                        # Reset variables on each iteration
                        search_result = None
                        uploadResp = None
                        logging.warning('Uploading/Reuploading '
                                        '[{!s}/{!s} attempts].'
                                        .format(x, MAX_UPLOAD_ATTEMPTS))
                        if (x > 0):
                            niceprint('Reuploading:[{!s}]...'
                                      '[{!s}/{!s} attempts].'
                                      .format(StrUnicodeOut(file),
                                              x,
                                              MAX_UPLOAD_ATTEMPTS))

                        # Upload file to Flickr
                        # replace commas from tags and checksum tags
                        # to avoid tags conflicts
                        try:
                            uploadResp = nuflickr.upload(
                                    filename=file,
                                    fileobj=FileWithCallback(file,
                                                             callback),
                                    title=title_filename
                                          if FLICKR["title"] == ""
                                          else str(FLICKR["title"]),
                                    description=str(FLICKR["description"]),
                                    tags='{} checksum:{} album:"{}" {}'
                                         .format(
                                                FLICKR["tags"],
                                                file_checksum,
                                                StrUnicodeOut(setName),
                                                args.tags if args.tags else '')
                                                .replace(',', ''),
                                    is_public=str(FLICKR["is_public"]),
                                    is_family=str(FLICKR["is_family"]),
                                    is_friend=str(FLICKR["is_friend"])
                                    )

                            logging.debug('uploadResp: ')
                            logging.debug(xml.etree.ElementTree.tostring(
                                                uploadResp,
                                                encoding='utf-8',
                                                method='xml'))
                            logging.info('uploadResp:[{!s}]'
                                         .format(self.isGood(uploadResp)))

                            # Save photo_id returned from Flickr upload
                            photo_id = uploadResp.findall('photoid')[0].text
                            logging.warning('Uploaded [{!s}] photo_id=[{!s}] '
                                            'Ok. Will check for issues ('
                                            'duplicates or wrong checksum)'
                                            .format(StrUnicodeOut(file),
                                                    photo_id))
                            if (args.verbose):
                                niceprint('Uploaded [{!s}] photo_id=[{!s}] '
                                          'Ok. Will check for issues ('
                                          'duplicates or wrong checksum)'
                                          .format(StrUnicodeOut(file),
                                                  photo_id))

                            # Successful upload. Break attempts cycle
                            break

                        # Exceptions for flickr.upload function call...
                        # No as it is caught in the outer try to consider the
                        # Error #5 invalid videos format loading...
                        except (IOError, httplib.HTTPException):
                            reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='020',
                                CaughtMsg='Caught IOError, HTTP exception',
                                NicePrint=True)
                            logging.error('Sleep 10 and check if file is '
                                          'already uploaded')
                            niceprint('Sleep 10 and check if file is '
                                      'already uploaded')
                            nutime.sleep(10)

                            # on error, check if exists a photo
                            # with file_checksum
                            # CODING: Revise and simplify this code
                            # CODING: Possibly use is_photo_already_uploaded
                            # CODING: but checking without SET
                            ZisLoaded, ZisCount, Zisfile_id, zisNoSet = \
                                self.is_photo_already_uploaded(
                                                                file,
                                                                file_checksum,
                                                                setName)
                            logging.debug('CODING NEW CODE: '
                                          'is_photo_already_uploaded:[{!s}] '
                                          'Zcount:[{!s}] Zpic:[{!s}] '
                                          'ZisNoSet:[{!s}]'
                                          .format(ZisLoaded, ZisCount,
                                                  Zisfile_id, zisNoSet))
                            # CODING: END... to check how to replace following
                            # lines. Check MAX_ATTEMPTS. Replace with retry?
                            search_result = self.photos_search(file_checksum)
                            if not self.isGood(search_result):
                                raise IOError(search_result)
                            logging.warning('Output for {!s}:'
                                            .format('search_result'))
                            logging.warning(xml.etree.ElementTree.tostring(
                                                   search_result,
                                                   encoding='utf-8',
                                                   method='xml'))

                            if int(search_result.find('photos')
                                   .attrib['total']) == 0:
                                if x == MAX_UPLOAD_ATTEMPTS - 1:
                                    niceprint('Reached maximum number '
                                              'of attempts to upload, '
                                              'file: [{!s}]'.format(file))
                                    raise ValueError('Reached maximum number '
                                                     'of attempts to upload, '
                                                     'skipping')
                                niceprint('Not found, reuploading '
                                          '[{!s}/{!s} attempts].'
                                          .format(x, MAX_UPLOAD_ATTEMPTS))
                                continue

                            if int(search_result.find('photos')
                                   .attrib['total']) > 1:
                                raise IOError('More then one file with same '
                                              'checksum! Any collisions? ' +
                                              search_result)

                            if int(search_result.find('photos')
                                   .attrib['total']) == 1:
                                niceprint('Found, continuing with next image.')
                                break

                    # Error on upload and search for photo not performed/empty
                    if not search_result and not self.isGood(uploadResp):
                        niceprint('A problem occurred while attempting to '
                                  'upload the file:[{!s}]'
                                  .format(StrUnicodeOut(file)))
                        raise IOError(uploadResp)

                    # Successful update
                    niceprint('Successfully uploaded the file:[{!s}].'
                              .format(StrUnicodeOut(file)))

                    # Save file_id... from uploadResp or search_result
                    # CODING: Obtained IndexOut of Range error after 1st load
                    # attempt failed and when search_Result returns 1 entry
                    logging.info('search_result:[{!s}]'.format(search_result))
                    if search_result:
                        logging.info('len(search_result(photos)'
                                     '.[photo]=[{!s}]'
                                     .format(len(search_result
                                                 .find('photos')
                                                 .findall('photo'))))
                        if (len(search_result
                               .find('photos')
                               .findall('photo')) == 0):
                            logging.error('xxx #E10 Error: '
                                          'IndexError: search_result yields '
                                          'Index out of range. '
                                          'Manually check file:[{!s}] '
                                          'Continuing with next image.'
                                          .format(file))
                            TraceBackIndexError = True
                        else:
                            file_id = search_result.find('photos')\
                                        .findall('photo')[0].attrib['id']
                            # file_id = uploadResp.findall('photoid')[0].text
                            logging.debug('Output for {!s}:'
                                         .format('search_result'))
                            logging.debug(xml.etree.ElementTree.tostring(
                                                search_result,
                                                encoding='utf-8',
                                                method='xml'))
                            logging.warning('SEARCH_RESULT file_id={!s}'
                                            .format(file_id))
                    else:
                        # Successful update given that search_result is None
                        file_id = uploadResp.findall('photoid')[0].text
                        logging.debug('Output for {!s}:'.format('uploadResp'))
                        logging.debug(xml.etree.ElementTree.tostring(
                                            uploadResp,
                                            encoding='utf-8',
                                            method='xml'))

                    # For tracking bad response from search_photos
                    logging.info('TraceBackIndexError:[{!s}]'
                                 .format(TraceBackIndexError))
                    if not TraceBackIndexError:
                        # Insert into DB files
                        dbInsertIntoFiles(lock, file_id, file,
                                          file_checksum, last_modified)

                        # Update the Video Date Taken
                        self.updatedVideoDate(file_id, file, last_modified)

                        success = True
                    else:
                        success = False
                except flickrapi.exceptions.FlickrError as ex:
                    reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='040',
                                CaughtMsg='Flickrapi exception on upload',
                                exceptUse=True,
                                exceptCode=ex.code,
                                exceptMsg=ex,
                                NicePrint=True,
                                exceptSysInfo=True)
                    # Error code: [5]
                    # Error code: [Error: 5: Filetype was not recognised]
                    # Error code: [8]
                    # Error code: [Error: 8: Filesize was too large]
                    if (((format(ex.code) == '5') or (format(ex.code) == '8'))
                        and (args.bad_files)):
                        # Add to db the file NOT uploaded
                        # Control for when running multiprocessing set locking
                        niceprint('Adding to Bad files table:[{!s}] '
                                  'due to [{!s}]'
                                  .format(file,
                                          'Filetype was not recognised'
                                          if (format(ex.code) == '5')
                                          else 'Filesize was too large'))
                        logging.info('Bad file:[{!s}]'.format(file))

                        self.useDBLock(lock, True)
                        # files_id column is autoincrement. No need to specify
                        cur.execute(
                          'INSERT INTO badfiles ( path, md5, '
                          'last_modified, tagged) VALUES (?, ?, ?, 1)',
                          (file, file_checksum, last_modified))
                        # Control for when running multiprocessing
                        # release locking
                        self.useDBLock(lock, False)

                except lite.Error as e:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='041',
                                CaughtMsg='DB error on INSERT: [{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True)
                    self.useDBLock(lock, False)

                    return False

            elif (MANAGE_CHANGES):
                # we have a file from disk which is found on the database
                # and is also on flickr but is set on flickr is not defined.
                # So we need to reset the local datbase set_id so that it will
                # be later assigned once we run createSets()
                logging.debug('str(row[1]) == str(isfile_id:[{!s}])'
                              'row[1]:[{!s}]=>type:[{!s}] '
                              'isfile_id:[{!s}]=>type:[{!s}]'
                              .format(str(row[1]) == str(isfile_id),
                                      row[1], type(row[1]),
                                      isfile_id, type(isfile_id)))
                if (isLoaded and
                    isNoSet and
                    (row is not None) and
                    (str(row[1]) == str(isfile_id))):

                    logging.info('Will UPDATE files SET set_id = null '
                                 'for pic:[{!s}] '
                                 .format(row[1]))
                    try:
                        self.useDBLock(lock, True)
                        cur.execute('UPDATE files SET set_id = null '
                                    'WHERE files_id = ?', (row[1],))
                    except lite.Error as e:
                        reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='045',
                            CaughtMsg='DB error on UPDATE: [{!s}]'.format(e.args[0]),
                            NicePrint=True)
                    finally:
                        con.commit()
                        self.useDBLock(lock, False)

                    logging.info('Did UPDATE files SET set_id = null '
                                 'for pic:[{!s}] '
                                 .format(row[1]))

                # we have a file from disk which is found on the database also
                # row[6] is last_modified date/timestamp
                # row[1] is files_id
                # row[4] is md5
                #   if DB/last_modified is None update it with current
                #   file/last_modified value and do nothing else
                #
                #   if DB/lastmodified is different from file/lastmodified
                #   then: if md5 has changed then perform replacePhoto
                #   operation on Flickr
                try:
                    logging.warning('CHANGES row[6]=[{!s}-({!s})]'
                                    .format(nutime.strftime(
                                                    UPLDRConstants.TimeFormat,
                                                    nutime.localtime(row[6])),
                                            row[6]))
                    if (row[6] is None):
                        # Update db the last_modified time of file

                        # Control for when running multiprocessing set locking
                        self.useDBLock(lock, True)
                        cur.execute('UPDATE files SET last_modified = ? '
                                    'WHERE files_id = ?', (last_modified,
                                                           row[1]))
                        con.commit()
                        self.useDBLock(lock, False)

                    logging.warning('CHANGES row[6]!=last_modified: [{!s}]'
                                    .format((row[6] != last_modified)))
                    if (row[6] != last_modified):
                        # Update db both the new file/md5 and the
                        # last_modified time of file by by calling replacePhoto

                        if file_checksum is None:
                            file_checksum = self.md5Checksum(file)
                        if (file_checksum != str(row[4])):
                            self.replacePhoto(lock, file, row[1], row[4],
                                              file_checksum, last_modified,
                                              cur, con)
                except lite.Error as e:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='050',
                                CaughtMsg='Error: UPDATE files '
                                          'SET last_modified: [{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True)

                    self.useDBLock(lock, False)
                    if (args.processes and args.processes > 0):
                        logging.debug('===Multiprocessing==='
                                      'lock.release (in Error)')
                        lock.release()
                        logging.debug('===Multiprocessing==='
                                      'lock.release (in Error)')

        # Closing DB connection
        if con is not None:
            con.close()
        return success

    # -------------------------------------------------------------------------
    # replacePhoto
    #   Should be only called from uploadFile
    #
    #   lock            = parameter for multiprocessing control of access to DB
    #                     if args.processes = 0 then lock can be None/not used
    #   file            = file to be uploaded to replace existing file
    #   file_id         = ID of the photo being replaced
    #   oldfileMd5      = Old file MD5 (required to update checksum tag
    #                     on Flikr)
    #   fileMd5         = New file MD5
    #   last_modified   = date/time last modification of the file to update
    #                     database
    #   cur             = current cursor for updating Database
    #   con             = current DB connection
    #
    def replacePhoto(self, lock, file, file_id,
                     oldFileMd5, fileMd5, last_modified, cur, con):
        """ replacePhoto
        lock            = parameter for multiprocessing control of access to DB
                          if args.processes = 0 then lock can be None/not used
        file            = file to be uploaded to replace existing file
        file_id         = ID of the photo being replaced
        oldfileMd5      = Old file MD5 (required to update checksum tag
                          on Flikr)
        fileMd5         = New file MD5
        last_modified   = date/time last modification of the file to update
                          database
        cur             = current cursor for updating Database
        con             = current DB connection
        """

        # CODING: Flickr does not allow to replace videos.
        global nuflickr

        if (args.dry_run is True):
            niceprint('Dry Run Replacing file:[{!s}]...'
                      .format(StrUnicodeOut(file)))
            return True

        if (args.verbose):
            niceprint('Replacing file:[{!s}]...'.format(StrUnicodeOut(file)))

        success = False
        try:
            # nuflickr.replace accepts both a filename and a file object.
            # when using filenames with unicode characters
            #    - the flickrapi seems to fail with filename
            # so I've used photo FileObj and filename='dummy'
            photo = open(file.encode('utf-8'), 'rb')\
                    if isThisStringUnicode(file)\
                    else open(file, 'rb')
            logging.debug('photo:[{!s}] type(photo):[{!s}]'
                          .format(photo, type(photo)))

            for x in range(0, MAX_UPLOAD_ATTEMPTS):
                res_add_tag = None
                res_get_info = None
                replaceResp = None

                try:
                    if (x > 0):
                        niceprint('Re-Replacing:[{!s}]...[{!s}/{!s} attempts].'
                                  .format(StrUnicodeOut(file),
                                          x,
                                          MAX_UPLOAD_ATTEMPTS))

                    # Use fileobj with filename='dummy'to accept unicode file.
                    replaceResp = nuflickr.replace(
                                filename='dummy',
                                fileobj=photo,
                                # fileobj=FileWithCallback(file, callback),
                                photo_id=file_id
                                )

                    logging.debug('replaceResp: ')
                    logging.debug(xml.etree.ElementTree.tostring(
                                                    replaceResp,
                                                    encoding='utf-8',
                                                    method='xml'))
                    logging.info('replaceResp:[{!s}]'
                                 .format(self.isGood(replaceResp)))

                    if (self.isGood(replaceResp)):
                        # Update checksum tag at this time.
                        res_add_tag = flick.photos_add_tags(
                                        file_id,
                                        ['checksum:{}'.format(fileMd5)]
                                      )
                        logging.debug('res_add_tag: ')
                        logging.debug(xml.etree.ElementTree.tostring(
                                                res_add_tag,
                                                encoding='utf-8',
                                                method='xml'))
                        if (self.isGood(res_add_tag)):
                            # Gets Flickr file info to obtain all tags
                            # in order to update checksum tag if exists
                            res_get_info = flick.photos_get_info(
                                                photo_id=file_id
                                                )
                            logging.debug('res_get_info: ')
                            logging.debug(xml.etree.ElementTree.tostring(
                                                    res_get_info,
                                                    encoding='utf-8',
                                                    method='xml'))
                            # find tag checksum with oldFileMd5
                            # later use such tag_id to delete it
                            if (self.isGood(res_get_info)):
                                tag_id = None
                                for tag in res_get_info\
                                                .find('photo')\
                                                .find('tags')\
                                                .findall('tag'):
                                    if (tag.attrib['raw'] ==
                                           'checksum:{}'.format(oldFileMd5)):
                                        tag_id = tag.attrib['id']
                                        logging.info('Found tag_id:[{!s}]'
                                                     .format(tag_id))
                                        break
                                if not tag_id:
                                    niceprint('Can\'t find tag [{!s}]'
                                              'for file [{!s}]'
                                              .format(tag_id, file_id))
                                    # break from attempting to update tag_id
                                    break
                                else:
                                    # update tag_id with new Md5
                                    logging.info('Will remove tag_id:[{!s}]'
                                                 .format(tag_id))
                                    remtagResp = self.photos_remove_tag(tag_id)
                                    logging.debug('remtagResp: ')
                                    logging.debug(xml.etree.ElementTree
                                                  .tostring(remtagResp,
                                                            encoding='utf-8',
                                                            method='xml'))
                                    if (self.isGood(remtagResp)):
                                        niceprint('Tag removed.')
                                    else:
                                        niceprint('Tag Not removed.')

                    break
                # Exceptions for flickr.upload function call...
                except (IOError, ValueError, httplib.HTTPException):
                    reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='060',
                                CaughtMsg='Caught IOError, ValueError, '
                                          'HTTP exception',
                                NicePrint=True,
                                exceptSysInfo=True)
                    logging.error('Sleep 10 and try to replace again.')
                    niceprint('Sleep 10 and try to replace again.')
                    nutime.sleep(10)

                    if x == MAX_UPLOAD_ATTEMPTS - 1:
                        raise ValueError('Reached maximum number of attempts '
                                         'to replace, skipping')
                    continue

            if (not self.isGood(replaceResp)) or \
                   (not self.isGood(res_add_tag)) or \
                   (not self.isGood(res_get_info)):
                niceprint('A problem occurred while attempting to '
                          'replace the file:[{!s}]'
                          .format(StrUnicodeOut(file)))

            if (not self.isGood(replaceResp)):
                raise IOError(replaceResp)

            if (not(self.isGood(res_add_tag))):
                raise IOError(res_add_tag)

            if (not self.isGood(res_get_info)):
                raise IOError(res_get_info)

            niceprint('Successfully replaced the file:[{!s}].'
                      .format(StrUnicodeOut(file)))

            # Update the db the file uploaded
            # Control for when running multiprocessing set locking
            self.useDBLock(lock, True)
            try:
                cur.execute('UPDATE files SET md5 = ?,last_modified = ? '
                            'WHERE files_id = ?',
                            (fileMd5, last_modified, file_id))
                con.commit()
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='070',
                            CaughtMsg='DB error on UPDATE: [{!s}]'
                                      .format(e.args[0]),
                            NicePrint=True)
            finally:
                # Release DB lock if running in multiprocessing mode
                self.useDBLock(lock, False)

            # Update the Video Date Taken
            self.updatedVideoDate(file_id, file, last_modified)

            success = True

        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='080',
                        CaughtMsg='Flickrapi exception on upload(or)replace',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True,
                        exceptSysInfo=True)
        except lite.Error as e:
            reportError(Caught=True,
                        CaughtPrefix='+++ DB',
                        CaughtCode='081',
                        CaughtMsg='DB error: [{!s}]'
                                  .format(e.args[0]),
                        NicePrint=True)
            # Release the lock on error.
            self.useDBLock(lock, False)
            success = False
        except:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='082',
                        CaughtMsg='Caught exception in replacePhoto',
                        exceptSysInfo=True)
            success = False

        return success

    # -------------------------------------------------------------------------
    # deletefile
    #
    # When EXCLUDED_FOLDERS defintion changes. You can run the -g
    # or --remove-ignored option in order to remove files previously loaded
    # files from flickr
    #
    def deleteFile(self, file, cur):
        """ deleteFile

        delete file from flickr
        cur represents the control dabase cursor to allow, for example,
            deleting empty sets
        """

        global nuflickr

        if args.dry_run:
            niceprint('Dry Run Deleting file:[{!s}]'
                      .format(StrUnicodeOut(file[1])))
            return True

        @retry(attempts=2, waittime=2, randtime=False)
        def R_photos_delete(kwargs):
            return nuflickr.photos.delete(**kwargs)

        niceprint('Deleting file:[{!s}]'.format(StrUnicodeOut(file[1])))

        success = False

        try:
            deleteResp = None
            deleteResp = R_photos_delete(dict(photo_id=str(file[0])))

            logging.debug('Output for {!s}:'.format('deleteResp'))
            logging.debug(xml.etree.ElementTree.tostring(
                                    deleteResp,
                                    encoding='utf-8',
                                    method='xml'))
            if (self.isGood(deleteResp)):
                # Find out if the file is the last item in a set, if so,
                # remove the set from the local db
                cur.execute("SELECT set_id FROM files WHERE files_id = ?",
                            (file[0],))
                row = cur.fetchone()
                cur.execute("SELECT set_id FROM files WHERE set_id = ?",
                            (row[0],))
                rows = cur.fetchall()
                if (len(rows) == 1):
                    niceprint('File is the last of the set, '
                              'deleting the set ID: ' + str(row[0]))
                    cur.execute("DELETE FROM sets WHERE set_id = ?", (row[0],))

                # Delete file record from the local db
                cur.execute("DELETE FROM files WHERE files_id = ?", (file[0],))
                niceprint("Successful deletion.")
                success = True
            else:
                reportError(Caught=True,
                            CaughtPrefix='xxx',
                            CaughtCode='089',
                            CaughtMsg='Failed delete photo (deleteFile)',
                            NicePrint=True)
                # CODING: Change this to deleteResp
                # Detect error #1 via exception format(ex.code) == '1'
                # or via analysis of XML reply? Confirmed: via except
                # <?xml version="1.0" encoding="utf-8" ?>
                # <rsp stat="fail">
                #   <err code="1" msg="Photo "123" not found (invalid ID)" />
                # </rsp>
        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='090',
                        CaughtMsg='Flickrapi exception on photos.delete',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True)
            # Error: 1: File already removed from Flickr
            if (ex.code == 1):
                try:
                    cur.execute("DELETE FROM files WHERE files_id = ?",
                                (file[0],))
                except lite.Error as e:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='091',
                                CaughtMsg='Error: DELETE FROM files:[{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True)
            else:
                reportError(Caught=True,
                            CaughtPrefix='xxx',
                            CaughtCode='092',
                            CaughtMsg='Failed delete photo (deleteFile)',
                            NicePrint=True)
        except:
            # If you get 'attempt to write a readonly database', set 'admin'
            # as owner of the DB file (fickerdb) and 'users' as group
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='093',
                        CaughtMsg='Caught exception in deleteFile',
                        exceptSysInfo=True)

        return success

    # -------------------------------------------------------------------------
    # logSetCreation
    #
    #   Creates on flickrdb local database a SetName(Album)
    #
    def logSetCreation(self, setId, setName, primaryPhotoId, cur, con):
        """ logSetCreation

        Creates on flickrdb local database a SetName(Album)
        with Primary photo Id.

        Assigns Primary photo Id to set on the local DB.

        Also updates photo DB entry with its set_id
        """

        logging.warning('Adding set: [{!s}] to database log.'
                        .format(StrUnicodeOut(setName)))
        if (args.verbose):
            niceprint('Adding set: [{!s}] to database log.'
                      .format(StrUnicodeOut(setName)))

        try:
            cur.execute('INSERT INTO sets (set_id, name, primary_photo_id) '
                        'VALUES (?,?,?)',
                        (setId, setName, primaryPhotoId))
        except lite.Error as e:
            reportError(Caught=True,
                CaughtPrefix='+++ DB',
                CaughtCode='094',
                CaughtMsg='DB error on INSERT: [{!s}]'
                          .format(e.args[0]),
                NicePrint=True)

        try:
            cur.execute('UPDATE files SET set_id = ? WHERE files_id = ?',
                        (setId, primaryPhotoId))
        except lite.Error as e:
            reportError(Caught=True,
                CaughtPrefix='+++ DB',
                CaughtCode='095',
                CaughtMsg='DB error on UPDATE: [{!s}]'.format(e.args[0]),
                NicePrint=True)

        con.commit()

        return True

    # -------------------------------------------------------------------------
    # isGood
    #
    def isGood(self, res):
        """ isGood

            If res is b=not None it will return true...
            if res.attrib['stat'] == "ok" for a given XML object
        """
        if (res is None):
            return False
        elif (not res == "" and res.attrib['stat'] == "ok"):
            return True
        else:
            return False

    # -------------------------------------------------------------------------
    # run
    #
    # run in daemon mode. runs upload every SLEEP_TIME
    #
    def run(self):
        """ run
            Run in daemon mode. runs upload every SLEEP_TIME seconds.
        """

        logging.warning('Running in Daemon mode.')
        while (True):
            niceprint('Running in Daemon mode. Execute at [{!s}].'
                      .format(nutime.strftime(UPLDRConstants.TimeFormat)))
            # run upload
            self.upload()
            niceprint('Last check: [{!s}]'
                      .format(str(nutime.asctime(time.localtime()))))
            logging.warning('Running in Daemon mode. Sleep [{!s}] seconds.'
                            .format(SLEEP_TIME))
            nutime.sleep(SLEEP_TIME)
    # -------------------------------------------------------------------------
    # getSetNameFromFile
    #
    # Return setName for a file path depending on FULL_SET_NAME True/False
    #   File to upload: /home/user/media/2014/05/05/photo.jpg
    #        FILES_DIR:  /home/user/media
    #    FULL_SET_NAME:
    #       False: 05
    #       True: 2014/05/05
    #
    def getSetNameFromFile(self, afile, aFILES_DIR, aFULL_SET_NAME):
        """getSetNameFromFile

           Return setName for a file path depending on FULL_SET_NAME True/False
           File to upload: /home/user/media/2014/05/05/photo.jpg
           FILES_DIR:  /home/user/media
           FULL_SET_NAME:
              False: 05
              True: 2014/05/05
        """

        assert len(afile) > 0, niceassert('len(afile) is not > 0:'
                                          .format(afile))

        logging.debug('getSetNameFromFile in: '
                      'afile:[{!s}] aFILES_DIR=[{!s}] aFULL_SET_NAME:[{!s}]'
                      .format(afile, aFILES_DIR, aFULL_SET_NAME))
        if aFULL_SET_NAME:
            asetName = os.path.relpath(os.path.dirname(afile), aFILES_DIR)
        else:
            head, asetName = os.path.split(os.path.dirname(afile))
        logging.debug('getSetNameFromFile out: '
                      'afile:[{!s}] aFILES_DIR=[{!s}] aFULL_SET_NAME:[{!s}]'
                      ' asetName:[{!s}]'
                      .format(afile, aFILES_DIR, aFULL_SET_NAME, asetName))

        return asetName

    # -------------------------------------------------------------------------
    # createSets
    #
    def createSets(self):
        """
            Creates a set (Album) in Flickr
        """
        niceprint('*****Creating Sets*****')

        if args.dry_run:
                return True

        con = lite.connect(DB_PATH)
        con.text_factory = str
        with con:
            cur = con.cursor()
            cur.execute("SELECT files_id, path, set_id FROM files")

            files = cur.fetchall()

            for row in files:
                # row[1] = path for the file from table files
                setName = self.getSetNameFromFile(row[1],
                                                  FILES_DIR,
                                                  FULL_SET_NAME)
                newSetCreated = False

                # Search local DB for set_id by setName(folder name )
                cur.execute("SELECT set_id, name FROM sets WHERE name = ?",
                            (setName,))
                set = cur.fetchone()

                if set is None:
                    # row[0] = files_id from files table
                    setId = self.createSet(setName, row[0], cur, con)
                    niceprint('Created the set: [{!s}]'.
                              format(StrUnicodeOut(setName)))
                    newSetCreated = True
                else:
                    # set[0] = set_id from sets table
                    setId = set[0]

                logging.debug('Creating Sets newSetCreated:[{!s}]'
                              'setId=[{!s}]'.format(newSetCreated, setId))

                # row[1] = path for the file from table files
                # row[2] = set_id from files table
                if row[2] is None and newSetCreated is False:
                    niceprint('adding file to set [{!s}]...'
                              .format(StrUnicodeOut(row[1])))

                    self.addFileToSet(setId, row, cur)

        # Closing DB connection
        if con is not None:
            con.close()
        niceprint('*****Completed creating sets*****')

    # -------------------------------------------------------------------------
    # addFiletoSet
    #
    def addFileToSet(self, setId, file, cur):
        """ addFileToSet

            adds a file to set...
            setID = set
            file = file
            cur = cursor for updating local DB
        """

        global nuflickr

        if args.dry_run:
                return True

        @retry(attempts=2, waittime=0, randtime=False)
        def R_photosets_addPhoto(kwargs):
            return nuflickr.photosets.addPhoto(**kwargs)

        try:
            con = lite.connect(DB_PATH)
            con.text_factory = str

            logging.info('Calling nuflickr.photosets.addPhoto'
                         'set_id=[{!s}] photo_id=[{!s}]'
                         .format(setId, file[0]))
            # REMARK Result for Error 3 (Photo already in set)
            # is passed via exception and so it is handled there
            addPhotoResp = None
            addPhotoResp = R_photosets_addPhoto(dict(photoset_id=str(setId),
                                                     photo_id=str(file[0])))

            logging.debug('Output for addPhotoResp:')
            logging.debug(xml.etree.ElementTree.tostring(
                                                addPhotoResp,
                                                encoding='utf-8',
                                                method='xml'))

            if (self.isGood(addPhotoResp)):
                niceprint('Successfully added file:[{!s}] to its set.'
                          .format(StrUnicodeOut(file[1])))
                try:
                    cur.execute("UPDATE files SET set_id = ? "
                                "WHERE files_id = ?",
                                (setId, file[0]))
                    con.commit()
                except lite.Error as e:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='096',
                                CaughtMsg='DB error on UPDATE files: [{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True)
            else:
                reportError(Caught=True,
                            CaughtPrefix='xxx',
                            CaughtCode='097',
                            CaughtMsg='Failed add photo to set (addFiletoSet)',
                            NicePrint=True)

            # CODING how to handle return error code from flickr via flickrapi?
            # via <err code> or via exception? Confirmed: via exception!
            # <?xml version="1.0" encoding="utf-8" ?>
            # <rsp stat="fail">
            #   <err code="1" msg="Photoset not found" />
            # </rsp>
        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='100',
                        CaughtMsg='Flickrapi exception on photosets.addPhoto',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True)
            # Error: 1: Photoset not found
            if (ex.code == 1):
                niceprint('Photoset not found, creating new set...')
                setName = self.getSetNameFromFile(file[1],
                                                  FILES_DIR,
                                                  FULL_SET_NAME)
                self.createSet(setName, file[0], cur, con)
            # Error: 3: Photo Already in set
            elif (ex.code == 3):
                try:
                    niceprint('Photo already in set... updating DB'
                              'set_id=[{!s}] photo_id=[{!s}]'
                              .format(setId, file[0]))
                    cur.execute('UPDATE files SET set_id = ? '
                                'WHERE files_id = ?', (setId, file[0]))
                    con.commit()
                except lite.Error as e:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='110',
                                CaughtMsg='DB error on UPDATE SET: [{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True)
            else:
                reportError(Caught=True,
                            CaughtPrefix='xxx',
                            CaughtCode='111',
                            CaughtMsg='Failed add photo to set (addFiletoSet)',
                            NicePrint=True)
        except lite.Error as e:
            reportError(Caught=True,
                        CaughtPrefix='+++ DB',
                        CaughtCode='120',
                        CaughtMsg='DB error on UPDATE files: [{!s}]'
                                  .format(e.args[0]),
                        NicePrint=True)
        except:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='121',
                        CaughtMsg='Caught exception in addFiletoSet',
                        NicePrint=True,
                        exceptSysInfo=True)

    # -------------------------------------------------------------------------
    # createSet
    #
    def createSet(self, setName, primaryPhotoId, cur, con):
        """ createSet

        Creates an Album in Flickr.
        Calls logSetCreation to create Album on local database.
        """

        global nuflickr

        logging.info('Creating new set:[{!s}]'
                     .format(StrUnicodeOut(setName)))
        niceprint('Creating new set:[{!s}]'
                  .format(StrUnicodeOut(setName)))

        if args.dry_run:
            return True

        @retry(attempts=3, waittime=10, randtime=True)
        def R_photosets_create(kwargs):
            return nuflickr.photosets.create(**kwargs)

        try:
            createResp = None
            createResp = R_photosets_create(dict(
                                        title=setName,
                                        primary_photo_id=str(primaryPhotoId)))

        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='130',
                        CaughtMsg='Flickrapi exception on photosets.create',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True,
                        exceptSysInfo=True)
            # Add to db the file NOT uploaded
            # A set on local DB (with primary photo) failed to be created on
            # FLickr because Primary Photo is not available.
            # Sets (possibly from previous runs) exist on local DB but the pics
            # are not loaded into Flickr.
            # FlickrError(u'Error: 2: Invalid primary photo id (nnnnnn)
            if (format(ex.code) == '2'):
                niceprint('Primary photo [{!s}] for Set [{!s}] '
                          'does not exist on Flickr. '
                          'Probably deleted from Flickr but still on local db '
                          'and local file.'
                          .format(primaryPhotoId,
                                  StrUnicodeOut(setName)))
                logging.error(
                          'Primary photo [{!s}] for Set [{!s}] '
                          'does not exist on Flickr. '
                          'Probably deleted from Flickr but still on local db '
                          'and local file.'
                          .format(primaryPhotoId,
                                  StrUnicodeOut(setName)))

                return False

        except:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='140',
                        CaughtMsg='Caught exception in createSet',
                        NicePrint=True,
                        exceptSysInfo=True)
        finally:
            if (self.isGood(createResp)):
                logging.warning('createResp["photoset"]["id"]:[{!s}]'
                                .format(createResp.find('photoset')
                                        .attrib['id']))
                self.logSetCreation(createResp.find('photoset').attrib['id'],
                                    setName,
                                    primaryPhotoId,
                                    cur,
                                    con)
                return createResp.find('photoset').attrib['id']
            else:
                logging.warning('createResp: ')
                if createResp is None:
                    logging.warning('None')
                else:
                    logging.warning(xml.etree.ElementTree.tostring(
                                                        createResp,
                                                        encoding='utf-8',
                                                        method='xml'))
                    reportError(exceptUse=False,
                                exceptCode=createResp['code']
                                           if 'code' in createResp
                                           else createResp,
                                exceptMsg=createResp['message']
                                          if 'message' in createResp
                                          else createResp,
                                NicePrint=True)

        return False

    # -------------------------------------------------------------------------
    # setupDB
    #
    # Creates the control database
    #
    def setupDB(self):
        """
            setupDB

            Creates the control database
        """

        niceprint('Setting up database:[{!s}]'.format(DB_PATH))
        con = None
        try:
            con = lite.connect(DB_PATH)
            con.text_factory = str
            cur = con.cursor()
            cur.execute('CREATE TABLE IF NOT EXISTS files '
                        '(files_id INT, path TEXT, set_id INT, '
                        'md5 TEXT, tagged INT)')
            cur.execute('CREATE TABLE IF NOT EXISTS sets '
                        '(set_id INT, name TEXT, primary_photo_id INTEGER)')
            cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS fileindex '
                        'ON files (path)')
            cur.execute('CREATE INDEX IF NOT EXISTS setsindex ON sets (name)')
            con.commit()

            # Check database version.
            # [0] = newly created
            # [1] = with last_modified column
            # [2] = badfiles table added
            # [3] = Adding album tags to pics on upload.
            #       Used in subsequent searches.
            cur = con.cursor()
            cur.execute('PRAGMA user_version')
            row = cur.fetchone()
            if (row[0] == 0):
                # Database version 1 <=========================DB VERSION: 1===
                niceprint('Adding last_modified column to database')
                cur = con.cursor()
                cur.execute('PRAGMA user_version="1"')
                cur.execute('ALTER TABLE files ADD COLUMN last_modified REAL')
                con.commit()
                # obtain new version to continue updating database
                cur = con.cursor()
                cur.execute('PRAGMA user_version')
                row = cur.fetchone()
            if (row[0] == 1):
                # Database version 2 <=========================DB VERSION: 2===
                # Cater for badfiles
                niceprint('Adding table badfiles to database')
                cur.execute('PRAGMA user_version="2"')
                cur.execute('CREATE TABLE IF NOT EXISTS badfiles '
                            '(files_id INTEGER PRIMARY KEY AUTOINCREMENT, '
                            'path TEXT, set_id INT, md5 TEXT, tagged INT, '
                            'last_modified REAL)')
                cur.execute('CREATE UNIQUE INDEX IF NOT EXISTS badfileindex '
                            'ON badfiles (path)')
                con.commit()
                cur = con.cursor()
                cur.execute('PRAGMA user_version')
                row = cur.fetchone()
            if (row[0] == 2):
                niceprint('Database version: [{!s}]'.format(row[0]))
                # Database version 3 <=========================DB VERSION: 3===
                niceprint('Adding album tags to pics on upload... ')
                if flick.addAlbumsMigrate():
                    niceprint('Successfully added album tags to pics '
                              'on upload. Updating Database version.',
                              fname='addAlbumsMigrate')

                    cur.execute('PRAGMA user_version="3"')
                    con.commit()
                    cur = con.cursor()
                    cur.execute('PRAGMA user_version')
                    row = cur.fetchone()
                else:
                    logging.warning('Failed adding album tags to pics '
                                    'on upload. Not updating Database version.'
                                    'please check logs, correct, and retry.')
                    niceprint('Failed adding album tags to pics '
                              'on upload. Not updating Database version.'
                              'Please check logs, correct, and retry.',
                              fname='addAlbumsMigrate')

            if (row[0] == 3):
                niceprint('Database version: [{!s}]'.format(row[0]))
                # Database version 4 <=========================DB VERSION: 4===
                # ...for future use!
            # Closing DB connection
            if con is not None:
                con.close()
        except lite.Error as e:
            reportError(Caught=True,
                       CaughtPrefix='+++ DB',
                       CaughtCode='145',
                       CaughtMsg='DB error on DB create: [{!s}]'
                                 .format(e.args[0]),
                       NicePrint=True)

            if con is not None:
                con.close()
            sys.exit(5)
        finally:
            niceprint('Completed database setup')

    # -------------------------------------------------------------------------
    # cleanDBbadfiles
    #
    # Cleans up (deletes) contents from DB badfiles table
    #
    def cleanDBbadfiles(self):
        """
            cleanDBbadfiles

            Cleans up (deletes) contents from DB badfiles table
        """
        niceprint('Cleaning up badfiles table from the database: [{!s}]'
                  .format(DB_PATH))
        con = None
        try:
            con = lite.connect(DB_PATH)
            con.text_factory = str
            cur = con.cursor()
            cur.execute('PRAGMA user_version')
            row = cur.fetchone()
            if (row[0] >= 2):
                # delete from badfiles table and reset SEQUENCE
                niceprint('Deleting from badfiles table. Reseting sequence.')
                try:
                    cur.execute('DELETE FROM badfiles')
                    cur.execute('DELETE FROM SQLITE_SEQUENCE '
                                'WHERE name="badfiles"')
                    con.commit()
                except lite.Error as e:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='147',
                                CaughtMsg='DB error on SELECT FROM '
                                          'badfiles: [{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True)
                    raise
            else:
                niceprint('Wrong DB version. '
                          'Expected 2 or higher and not:[{!s}]'.format(row[0]))
            # Closing DB connection
            if con is not None:
                con.close()
        except lite.Error as e:
            reportError(Caught=True,
                        CaughtPrefix='+++ DB',
                        CaughtCode='148',
                        CaughtMsg='DB error on SELECT: [{!s}]'
                                  .format(e.args[0]),
                        NicePrint=True)
            if con is not None:
                con.close()
            sys.exit(6)
        finally:
            niceprint('Completed cleaning up badfiles table from the database')

    # -------------------------------------------------------------------------
    # md5Checksum
    #
    def md5Checksum(self, filePath):
        """ md5Checksum

            Calculates the MD5 checksum for filePath
        """
        with open(filePath, 'rb') as fh:
            m = hashlib.md5()
            while True:
                data = fh.read(8192)
                if not data:
                    break
                m.update(data)
            return m.hexdigest()

    # -------------------------------------------------------------------------
    # removeUselessSetsTable
    #
    # Method to clean unused sets (Sets are Albums)
    #
    def removeUselessSetsTable(self):
        """ removeUselessSetsTable

        Remove unused Sets (Sets not listed on Flickr) form local DB
        """
        niceprint('*****Removing empty Sets from DB*****')
        if args.dry_run:
                return True

        con = lite.connect(DB_PATH)
        con.text_factory = str
        with con:
            cur = con.cursor()

            try:
                unusedsets = None
                # Acquire DB lock if running in multiprocessing mode
                # self.useDBLock( lock, True)
                cur.execute("SELECT set_id, name FROM sets WHERE set_id NOT IN\
                            (SELECT set_id FROM files)")
                unusedsets = cur.fetchall()
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='150',
                            CaughtMsg='DB error SELECT FROM sets: [{!s}]'
                                      .format(e.args[0]),
                            NicePrint=True)
            finally:
                # Release DB lock if running in multiprocessing mode
                # self.useDBLock( lock, False)
                pass

            for row in unusedsets:
                if args.verbose:
                    niceprint('Removing set [{!s}] ({!s}).'
                              .format(StrUnicodeOut(row[0]),
                                      StrUnicodeOut(row[1])))

                try:
                    # Acquire DB lock if running in multiprocessing mode
                    # self.useDBLock( lock, True)
                    cur.execute("DELETE FROM sets WHERE set_id = ?", (row[0],))
                except lite.Error as e:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='160',
                                CaughtMsg='DB error DELETE FROM sets: [{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True)
                finally:
                    # Release DB lock if running in multiprocessing mode
                    # self.useDBLock( lock, False)
                    pass

            con.commit()

        # Closing DB connection
        if con is not None:
            con.close()
        niceprint('*****Completed removing empty Sets from DB*****')

    # -------------------------------------------------------------------------
    # Display Sets
    #
    # CODING: Not being used!
    def displaySets(self):
        """ displaySets

        Prints the list of sets/albums recorded on the local database
        """
        con = lite.connect(DB_PATH)
        con.text_factory = str
        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT set_id, name FROM sets")
                allsets = cur.fetchall()
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='163',
                            CaughtMsg='DB error on SELECT FROM '
                                      'sets: [{!s}]'
                                      .format(e.args[0]),
                            NicePrint=True)
            for row in allsets:
                niceprint('Set: [{!s}] ({!s})'.format(str(row[0]), row[1]))

        # Closing DB connection
        if con is not None:
            con.close()

    # -------------------------------------------------------------------------
    # Get sets from Flickr
    #
    # Selects the flickrSets from Flickr
    # for each flickrSet
    #   Searches localDBSet from local database (flickrdb)
    #   if localDBSet is None then INSERTs flickrset into flickrdb
    #
    def getFlickrSets(self):
        """
            getFlickrSets

            Gets list of FLickr Sets (Albums) and populates
            local DB accordingly
        """
        global nuflickr

        niceprint('*****Adding Flickr Sets to DB*****')
        if args.dry_run:
                return True

        con = lite.connect(DB_PATH)
        con.text_factory = str
        try:
            sets = nuflickr.photosets_getList()

            logging.debug('Output for {!s}'.format('photosets_getList:'))
            logging.debug(xml.etree.ElementTree.tostring(
                                                sets,
                                                encoding='utf-8',
                                                method='xml'))

            """

sets = flickr.photosets.getList(user_id='73509078@N00')

sets.attrib['stat'] => 'ok'
sets.find('photosets').attrib['cancreate'] => '1'

set0 = sets.find('photosets').findall('photoset')[0]

+-------------------------------+-----------+
| variable                      | value     |
+-------------------------------+-----------+
| set0.attrib['id']             | u'5'      |
| set0.attrib['primary']        | u'2483'   |
| set0.attrib['secret']         | u'abcdef' |
| set0.attrib['server']         | u'8'      |
| set0.attrib['photos']         | u'4'      |
| set0.title[0].text            | u'Test'   |
| set0.description[0].text      | u'foo'    |
| set0.find('title').text       | 'Test'    |
| set0.find('description').text | 'foo'     |
+-------------------------------+-----------+

... and similar for set1 ...

            """

            if (self.isGood(sets)):
                cur = con.cursor()

                for row in sets.find('photosets').findall('photoset'):
                    logging.debug('Output for {!s}:'.format('row'))
                    logging.debug(xml.etree.ElementTree.tostring(
                                                        row,
                                                        encoding='utf-8',
                                                        method='xml'))

                    setId = row.attrib['id']
                    setName = row.find('title').text
                    primaryPhotoId = row.attrib['primary']

                    logging.debug('isThisStringUnicode [{!s}]:{!s}'
                                  .format('setId',
                                          isThisStringUnicode(setId)))
                    logging.debug('isThisStringUnicode [{!s}]:{!s}'
                                  .format('setName',
                                          isThisStringUnicode(setName)))
                    logging.debug('isThisStringUnicode [{!s}]:{!s}'
                                  .format('primaryPhotoId',
                                          isThisStringUnicode(primaryPhotoId)))

                    if (args.verbose):
                        niceprint('setName=[{!s}] '
                                  'setId=[{!s}] '
                                  'primaryPhotoId=[{!s}]'
                                  .format('None'
                                          if setName is None
                                          else StrUnicodeOut(setName),
                                          setId,
                                          primaryPhotoId))

                    # Control for when flickr return a setName (title) as None
                    # Occurred while simultaneously performing massive delete
                    # operation on flickr.
                    if setName is not None:
                        logging.info('Searching on DB for setId:[{!s}] '
                                     'setName:[{!s}] '
                                     'primaryPhotoId:[{!s}]'
                                     .format(setId,
                                             StrUnicodeOut(setName),
                                             primaryPhotoId))
                    else:
                        logging.info('Searching on DB for setId:[{!s}] '
                                     'setName:[None] '
                                     'primaryPhotoId:[{!s}]'
                                     .format(setId,
                                             primaryPhotoId))

                    logging.info('SELECT set_id FROM sets '
                                 'WHERE set_id = "{!s}"'
                                 .format(setId))
                    try:
                        cur.execute("SELECT set_id FROM sets "
                                    "WHERE set_id = '" + setId + "'")
                        foundSets = cur.fetchone()
                        logging.info('Output for foundSets is [{!s}]'
                                     .format('None'
                                             if foundSets is None
                                             else foundSets))
                    except lite.Error as e:
                        reportError(Caught=True,
                                    CaughtPrefix='+++ DB',
                                    CaughtCode='164',
                                    CaughtMsg='DB error on SELECT FROM '
                                              'sets: [{!s}]'
                                              .format(e.args[0]),
                                    NicePrint=True)

                    if (foundSets is None):
                        if setName is None:
                            logging.info('Adding set [{!s}] ({!s}) '
                                         'with primary photo [{!s}].'
                                         .format(setId,
                                                 'None',
                                                 primaryPhotoId))
                        else:
                            logging.info('Adding set [{!s}] ({!s}) '
                                         'with primary photo [{!s}].'
                                         .format(
                                            setId,
                                            StrUnicodeOut(setName),
                                            primaryPhotoId))
                        try:
                            cur.execute('INSERT INTO sets (set_id, name, '
                                        'primary_photo_id) VALUES (?,?,?)',
                                        (setId, setName, primaryPhotoId))
                        except lite.Error as e:
                            reportError(Caught=True,
                                        CaughtPrefix='+++ DB',
                                        CaughtCode='165',
                                        CaughtMsg='DB error on INSERT INTO '
                                                  'sets: [{!s}]'
                                                  .format(e.args[0]),
                                        NicePrint=True)
                    else:
                        logging.info('Flickr Set/Album already on '
                                     'local database.')
                        if (args.verbose):
                            niceprint('Flickr Set/Album already on '
                                      'local database.')

                con.commit()

                if con is not None:
                    con.close()
            else:
                logging.warning(xml.etree.ElementTree.tostring(
                                    sets,
                                    encoding='utf-8',
                                    method='xml'))
                reportError(exceptUse=True,
                            exceptCode=sets['code']
                                       if 'code' in sets
                                       else sets,
                            exceptMsg=sets['message']
                                      if 'message' in sets
                                      else sets,
                            NicePrint=True)

        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='170',
                        CaughtMsg='Flickrapi exception on photosets_getList',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True,
                        exceptSysInfo=True)

        # Closing DB connection
        if con is not None:
            con.close()
        niceprint('*****Completed adding Flickr Sets to DB*****')

    # -------------------------------------------------------------------------
    # is_photo_already_uploaded
    #
    # Checks if image is already loaded with tag:checksum
    # (calls Flickr photos.search)
    #
    # CODING: possible outcomes
    # A) checksum,                             Count=0  THEN NOT EXISTS
    # B) checksum, title, empty setName,       Count=1  THEN EXISTS, ASSIGN SET
    #                                                   IF tag album IS FOUND
    # C) checksum, title, setName (1 or more), Count>=1 THEN EXISTS
    # D) checksum, title, other setName,       Count>=1 THEN NOT EXISTS
    # E) checksum, title, setName & ALSO checksum, title, other setName => N/A
    # F) checksum, title, setName & ALSO checksum, title, empty setName => N/A
    #
    # Logic:
    #   Search photos with checksum
    #   Verify if title is filename's (without extension)
    #         not compatible with use of the -i option
    #   Confirm if setname is the same.
    #   THEN yes found loaded.
    # Note: There could be more entries due to errors. To be checked manually
    #
    def is_photo_already_uploaded(self, xfile, xchecksum, xsetName):
        """ is_photo_already_uploaded

            Searchs for image with same:
                title(file without extension)
                tag:checksum
                SetName
                    CODING: Being implemented...
                    if setName is not defined on a pic, it attempts to
                    check tag:album

            returnIsPhotoUploaded = True (already loaded)/False(not loaded)
            returnPhotoUploaded   = Number of found Images
            returnPhotoID         = Pic ID on Flickr
            returnUploadedNoSet   = True , B, C, D, E or F
            Case | returnIsPhotoUploaded | returnUploadedNoSet |
            A    | False                 | False               |
            B    | True                  | True                |
            C    | True                  | False               |
            D    | False                 | False               |
        """

        global nuflickr
        returnIsPhotoUploaded = False
        returnPhotoUploaded = 0
        returnPhotoID = None
        returnUploadedNoSet = False

        logging.info('Is Already Uploaded:[checksum:{!s}] [album:{!s}]?'
                     .format(xchecksum, xsetName))

        # CODING: Used with a big random waitime to avoid errors in
        # multiprocessing mode.
        @retry(attempts=3, waittime=20, randtime=True)
        def R_photos_search(kwargs):
            return nuflickr.photos.search(**kwargs)

        try:
            searchIsUploaded = None
            searchIsUploaded = R_photos_search(dict(user_id="me",
                                                    tags='checksum:{}'
                                                         .format(xchecksum),
                                                    extras='tags'))
        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='180',
                        CaughtMsg='Flickrapi exception on photos.search',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex)
        except (IOError, httplib.HTTPException):
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='181',
                        CaughtMsg='Caught IO/HTTP Error in photos.search')
        except:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='182',
                        CaughtMsg='Caught exception in photos.search',
                        exceptSysInfo=True)
        finally:
            if searchIsUploaded is None or not self.isGood(searchIsUploaded):
                logging.error('searchIsUploadedOK:[{!s}]'
                              .format('None'
                                      if searchIsUploaded is None
                                      else self.isGood(searchIsUploaded)))
                # CODING: how to indicate an error... different from False?
                # Possibly raising an exception?
                # raise Exception('photos_search: Max attempts exhausted.')
                niceprint('return: IS_PHOTO_UPLOADED: ERROR#1',
                          fname='is_photo_already_uploaded')
                logging.warning('return: IS_PHOTO_UPLOADED: ERROR#1')
                return returnIsPhotoUploaded, \
                       returnPhotoUploaded, \
                       returnPhotoID, \
                       returnUploadedNoSet

        logging.debug('searchIsUploaded:')
        logging.debug(xml.etree.ElementTree.tostring(searchIsUploaded,
                                                     encoding='utf-8',
                                                     method='xml'))

        # Number of pics with specified checksum
        returnPhotoUploaded = int(searchIsUploaded
                                  .find('photos').attrib['total'])

        if returnPhotoUploaded == 0:
            # A) checksum,                             Count=0  THEN NOT EXISTS
            returnIsPhotoUploaded = False
        elif returnPhotoUploaded >= 1:
            logging.warning('+++#190: '
                            'Found [{!s}] images with checksum:[{!s}]'
                            .format(returnPhotoUploaded, xchecksum))
            # Get title from filepath as filename without extension
            # NOTE: not compatible with use of the -i option
            xpath_filename, xtitle_filename = os.path.split(xfile)
            xtitle_filename = os.path.splitext(xtitle_filename)[0]
            logging.info('Title:[{!s}]'.format(StrUnicodeOut(xtitle_filename)))

            # For each pic found on Flickr 1st check title and then Sets
            # CODING returnList not being used
            # returnList = []
            freturnPhotoUploaded = 0
            for pic in searchIsUploaded.find('photos').findall('photo'):
                freturnPhotoUploaded +=1
                logging.debug('idx=[{!s}] pic.id=[{!s}] '
                              'pic.title=[{!s}] pic.tags=[{!s}]'
                              .format(freturnPhotoUploaded,
                                      pic.attrib['id'],
                                      StrUnicodeOut(pic.attrib['title']),
                                      StrUnicodeOut(pic.attrib['tags'])))

                # CODING: UnicodeWarning: Unicode equal comparison failed to
                # convert both arguments to Unicode
                logging.debug('xtitle_filename/type=[{!s}]/[{!s}] '
                              'pic.attrib[title]/type=[{!s}]/[{!s}]'
                              .format(StrUnicodeOut(xtitle_filename),
                                      type(xtitle_filename),
                                      StrUnicodeOut(pic.attrib['title']),
                                      type(pic.attrib['title'])))
                logging.info('Compare Titles=[{!s}]'
                            .format((StrUnicodeOut(xtitle_filename) ==
                                     StrUnicodeOut(pic.attrib['title']))))

                # if pic with checksum has a different title, continue
                if not (StrUnicodeOut(xtitle_filename) ==
                            StrUnicodeOut(pic.attrib['title'])):
                    logging.info('Different titles: File:[{!s}] Flickr:[{!s}]'
                                 .format(StrUnicodeOut(xtitle_filename),
                                         StrUnicodeOut(pic.attrib['title'])))
                    continue

                @retry(attempts=3, waittime=8, randtime=True)
                def R_photos_getAllContexts(kwargs):
                    return nuflickr.photos.getAllContexts(**kwargs)

                try:
                    resp = None
                    resp = R_photos_getAllContexts(
                                            dict(photo_id=pic.attrib['id']))
                except flickrapi.exceptions.FlickrError as ex:
                    reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='195',
                                CaughtMsg='Flickrapi exception on '
                                          'getAllContexts',
                                exceptUse=True,
                                exceptCode=ex.code,
                                exceptMsg=ex)
                except (IOError, httplib.HTTPException):
                    reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='196',
                                CaughtMsg='Caught IO/HTTP Error in '
                                          'getAllContexts')
                except:
                    reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='197',
                                CaughtMsg='Caught exception in '
                                          'getAllContexts',
                                exceptSysInfo=True)
                finally:
                    if resp is None or not self.isGood(resp):
                        logging.error('resp.getAllContextsOK:[{!s}]'
                                      .format('None'
                                               if resp is None
                                               else self.isGood(resp)))
                        # CODING: how to indicate an error?
                        # Possibly raising an exception?
                        # raise Exception('photos_getAllContexts: Max attempts exhausted.')
                        niceprint('return: IS_PHOTO_UPLOADED: ERROR#2',
                                  fname='is_photo_already_uploaded')
                        logging.warning('return: IS_PHOTO_UPLOADED: ERROR#2')
                        return returnIsPhotoUploaded, \
                               returnPhotoUploaded, \
                               returnPhotoID, \
                               returnUploadedNoSet
                    logging.debug('resp.getAllContextsOK:')
                    logging.debug(xml.etree.ElementTree.tostring(
                                                        resp,
                                                        encoding='utf-8',
                                                        method='xml'))

                logging.info('len(resp.findall(''set'')):[{!s}]'
                             .format(len(resp.findall('set'))))

                # B) checksum, title, empty setName,       Count=1  THEN EXISTS, ASSIGN SET
                #                                                   IF tag album IS FOUND
                if (len(resp.findall('set')) == 0):
                    # CODING returnList not being used
                    # returnList.append({'id': pic.attrib['id'],
                    #                    'title': pic.attrib['title'],
                    #                    'set': '',
                    #                    'tags': pic.attrib['tags'],
                    #                    'result': 'empty'})
                    # CODING: TEST
                    # Valid for re-running interrupted runs EXCEPT when
                    # you have two pics, with same file name and checksum on
                    # two different sets. SAME Orphaned pic will then be
                    # assigned to TWO DIFFERENT SETS.
                    # Unless it has the tag album:setName defined!
                    # Consider one additional result for PHOTO UPLOADED
                    # WITHOUT SET WITH ALBUM TAG when row exists on DB. Mark
                    # such row on the database files.set_id to null
                    # to force re-assigning to Album/Set on flickr.
                    tfind, tid = self.photos_find_tag(
                                            photo_id = pic.attrib['id'],
                                            intag = 'album:{}'
                                                    .format(xsetName))
                    if tfind:
                        niceprint('return: PHOTO UPLOADED WITHOUT SET '
                                  'WITH ALBUM TAG',
                                  fname='is_photo_already_uploaded')
                        logging.warning('return: PHOTO UPLOADED WITHOUT SET '
                                        'WITH ALBUM TAG')
                        returnIsPhotoUploaded = True
                        returnPhotoID = pic.attrib['id']
                        returnUploadedNoSet = True
                        return returnIsPhotoUploaded, \
                               returnPhotoUploaded, \
                               returnPhotoID, \
                               returnUploadedNoSet
                    else:
                        if args.verbose_progress:
                            niceprint('PHOTO UPLOADED WITHOUT SET '
                                      'WITHOUT ALBUM TAG',
                                      fname='is_photo_already_uploaded')
                        logging.warning('PHOTO UPLOADED WITHOUT SET '
                                        'WITHOUT ALBUM TAG')

                for setinlist in resp.findall('set'):
                    logging.warning('setinlist:')
                    logging.warning(xml.etree.ElementTree.tostring(
                                                        setinlist,
                                                        encoding='utf-8',
                                                        method='xml'))

                    logging.warning(
                              '\nCheck : id=[{!s}] File=[{!s}]\n'
                              'Check : Title:[{!s}] Set:[{!s}]\n'
                              'Flickr: Title:[{!s}] Set:[{!s}] Tags:[{!s}]\n'
                              .format(pic.attrib['id'],
                                      StrUnicodeOut(xfile),
                                      StrUnicodeOut(xtitle_filename),
                                      StrUnicodeOut(xsetName),
                                      StrUnicodeOut(pic.attrib['title']),
                                      StrUnicodeOut(setinlist.attrib['title']),
                                      StrUnicodeOut(pic.attrib['tags'])))

                    logging.warning(
                              'Compare Sets=[{!s}]'
                              .format((StrUnicodeOut(xsetName) ==
                                          StrUnicodeOut(setinlist
                                                        .attrib['title']))))

                    # CODING returnList not being used
                    # returnList.append({'id': pic.attrib['id'],
                    #                    'title': pic.attrib['title'],
                    #                    'set': setinlist.attrib['title'],
                    #                    'tags': pic.attrib['tags'],
                    #                    'result': 'nothing'})
                    # logging.info('output for returnList:[{!s}]'
                    #              .format(returnList))

                    # C) checksum, title, setName (1 or more), Count>=1 THEN EXISTS
                    if (StrUnicodeOut(xsetName) ==
                            StrUnicodeOut(setinlist.attrib['title'])):
                        niceprint('return: IS PHOTO UPLOADED='
                                  'TRUE WITH SET',
                                  fname='is_photo_already_uploaded')
                        logging.warning('return: IS PHOTO UPLOADED=TRUE WITH SET')
                        returnIsPhotoUploaded = True
                        returnPhotoID = pic.attrib['id']
                        returnUploadedNoSet = False
                        return returnIsPhotoUploaded, \
                               returnPhotoUploaded, \
                               returnPhotoID, \
                               returnUploadedNoSet
                    else:
                        # D) checksum, title, other setName,       Count>=1 THEN NOT EXISTS
                        if args.verbose_progress:
                            niceprint('IS PHOTO UPLOADED=FALSE OTHER SET, '
                                      'CONTINUING SEARCH IN SETS',
                                      fname='is_photo_already_uploaded')
                        logging.warning('IS PHOTO UPLOADED=FALSE OTHER SET, '
                                        'CONTINUING SEARCH IN SETS')
                        continue

        return returnIsPhotoUploaded, returnPhotoUploaded, \
               returnPhotoID, returnUploadedNoSet
# <?xml version="1.0" encoding="utf-8" ?>
# <rsp stat="ok">
#   <photos page="1" pages="1" perpage="100" total="2">
#     <photo id="37564183184" owner="146995488@N03" secret="5390570f1c" server="4540" farm="5" title="DSC01397" ispublic="0" isfriend="0" isfamily="0" tags="autoupload checksum1133825cea9d605f332d04b40a44a6d6" />
#     <photo id="38210659646" owner="146995488@N03" secret="2786b173f4" server="4536" farm="5" title="DSC01397" ispublic="0" isfriend="0" isfamily="0" tags="autoupload checksum1133825cea9d605f332d04b40a44a6d6" />
#   </photos>
# </rsp>
# CAREFULL... flickrapi on occasion indicates total=2 but the list only brings 1
#
# <?xml version="1.0" encoding="utf-8" ?>
# <rsp stat="ok">
#   <photos page="1" pages="1" perpage="100" total="2">
#     <photo id="26486922439" owner="146995488@N03" secret="7657801015" server="4532" farm="5" title="017_17a-5" ispublic="0" isfriend="0" isfamily="0" tags="autoupload checksum0449d770558cfac7a6786e468f917b9c joana" />
#   </photos>
# </rsp>

    # -------------------------------------------------------------------------
    # photos_search
    #
    # Searchs for image with tag:checksum (calls Flickr photos.search)
    #
    # Sample response:
    # <photos page="2" pages="89" perpage="10" total="881">
    #     <photo id="2636" owner="47058503995@N01"
    #             secret="a123456" server="2" title="test_04"
    #             ispublic="1" isfriend="0" isfamily="0" />
    #     <photo id="2635" owner="47058503995@N01"
    #         secret="b123456" server="2" title="test_03"
    #         ispublic="0" isfriend="1" isfamily="1" />
    # </photos>
    def photos_search(self, checksum):
        """
            photos_search
            Searchs for image with on tag:checksum
        """
        global nuflickr

        logging.info('FORMAT:[checksum:{!s}]'.format(checksum))

        searchResp = nuflickr.photos.search(user_id="me",
                                            tags='checksum:{}'
                                                 .format(checksum))
        # Debug
        logging.debug('Search Results SearchResp:')
        logging.debug(xml.etree.ElementTree.tostring(searchResp,
                                                     encoding='utf-8',
                                                     method='xml'))

        return searchResp

    # -------------------------------------------------------------------------
    # people_get_photos
    #
    #   Local Wrapper for Flickr people.getPhotos
    #
    def people_get_photos(self):
        """
        """

        global nuflickr

        getPhotosResp = None
        try:
            getPhotosResp = nuflickr.people.getPhotos(user_id="me", per_page=1)
        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='200',
                        CaughtMsg='Error in photos.search',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex)
        except (IOError, httplib.HTTPException):
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='201',
                        CaughtMsg='Caught IO/HTTP Error in photos.search')
        except:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='202',
                        CaughtMsg='Caught exception in photos.search',
                        exceptSysInfo=True)
        finally:
            if getPhotosResp is None or not self.isGood(getPhotosResp):
                logging.debug('getPhotosResp:[{!s}]'
                              .format('None'
                                      if getPhotosResp is None
                                      else self.isGood(getPhotosResp)))

        return getPhotosResp

    # -------------------------------------------------------------------------
    # photos_get_not_in_set
    #
    #   Local Wrapper for Flickr photos.getNotInSet
    #
    def photos_get_not_in_set(self, per_page):
        """
        Local Wrapper for Flickr photos.getNotInSet
        """

        global nuflickr

        @retry(attempts=2, waittime=12, randtime=False)
        def R_photos_getNotInSet(kwargs):
            return nuflickr.photos.getNotInSet(**kwargs)

        notinsetResp = R_photos_getNotInSet(dict(per_page=per_page))

        # notinsetResp = nuflickr.photos.getNotInSet(per_page=per_page)

        return notinsetResp

    # -------------------------------------------------------------------------
    # photos_get_info
    #
    #   Local Wrapper for Flickr photos.getInfo
    #
    def photos_get_info(self, photo_id):
        """
        Local Wrapper for Flickr photos.getInfo
        """

        global nuflickr

        photos_get_infoResp = nuflickr.photos.getInfo(photo_id=photo_id)

        return photos_get_infoResp

    # -------------------------------------------------------------------------
    # photos_find_tag
    #
    #   Determines if tag is assigned to a pic.
    #
    def photos_find_tag(self, photo_id, intag):
        """
        Determines if intag is assigned to a pic.

        found_tag = False or True
        tag_id = tag_id if found
        """

        global nuflickr

        logging.info('find_tag: photo:[{!s}] intag:[{!s}]'
                     .format(photo_id, intag))

        # CODING: Used with a big random waitime to avoid errors in
        # multiprocessing mode.
        @retry(attempts=3, waittime=20, randtime=True)
        def R_tags_getListPhoto(kwargs):
            return nuflickr.tags.getListPhoto(**kwargs)

        try:
            tagsResp = None
            tagsResp = R_tags_getListPhoto(dict(photo_id=photo_id))
        except (IOError, ValueError, httplib.HTTPException):
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='205',
                        CaughtMsg='Caught IOError, ValueError, '
                                  'HTTP exception on getListPhoto',
                        NicePrint=True,
                        exceptSysInfo=True)
        except flickrapi.exceptions.FlickrError as ex:
            if (format(ex.code) == '1'):
                logging.warning('+++206: '
                                'Photo_id:[{!s}] Flickr: Photo not found '
                                'on getListPhoto.'
                                .format(photo_id))
                niceprint('+++206: '
                          'Photo_id:[{!s}] Flickr: Photo not found '
                          'on getListPhoto.'
                          .format(photo_id),
                          fname='photos_find_tag')
            else:
                reportError(Caught=True,
                            CaughtPrefix='+++',
                            CaughtCode='207',
                            CaughtMsg='Flickrapi exception on getListPhoto',
                            exceptUse=True,
                            exceptCode=ex.code,
                            exceptMsg=ex,
                            NicePrint=True,
                            exceptSysInfo=True)
            raise

        if (not self.isGood(tagsResp)):
            raise IOError(tagsResp)

        logging.debug('Output for photo_find_tag:')
        logging.debug(xml.etree.ElementTree.tostring(tagsResp,
                                                     encoding='utf-8',
                                                     method='xml'))

        tag_id = None
        for tag in tagsResp.find('photo').find('tags').findall('tag'):
            logging.info(tag.attrib['raw'])
            if (StrUnicodeOut(tag.attrib['raw']) ==
                    StrUnicodeOut(intag)):
                tag_id = tag.attrib['id']
                logging.info('Found tag_id:[{!s}] for intag:[{!s}]'
                             .format(tag_id, intag))
                return True, tag_id

        return False, ''


    # -------------------------------------------------------------------------
    # photos_add_tags
    #
    #   Local Wrapper for Flickr photos.addTags
    #
    def photos_add_tags(self, photo_id, tags):
        """
        Local Wrapper for Flickr photos.addTags
        """

        global nuflickr

        logging.info('photos_add_tags: photo_id:[{!s}] tags:[{!s}]'
                     .format(photo_id, tags))
        photos_add_tagsResp = nuflickr.photos.addTags(photo_id=photo_id,
                                                      tags=tags)
        return photos_add_tagsResp

    # -------------------------------------------------------------------------
    # photos_remove_tag
    #
    #   Local Wrapper for Flickr photos.removeTag
    #   The tag to remove from the photo. This parameter should contain
    #   a tag id, as returned by flickr.photos.getInfo.
    #
    def photos_remove_tag(self, tag_id):
        """
        Local Wrapper for Flickr photos.removeTag

        The tag to remove from the photo. This parameter should contain
        a tag id, as returned by flickr.photos.getInfo.
        """

        global nuflickr

        removeTagResp = nuflickr.photos.removeTag(tag_id=tag_id)

        return removeTagResp

    # -------------------------------------------------------------------------
    # photos_set_dates
    #
    # Update Date/Time Taken on Flickr for Video files
    #
    def photos_set_dates(self, photo_id, datetxt):
        """
        Update Date/Time Taken on Flickr for Video files
        """
        global nuflickr

        if (args.verbose):
            niceprint('Setting Date photo_id=[{!s}] date_taken=[{!s}]'
                      .format(photo_id, datetxt))
        logging.warning('Setting Date photo_id=[{!s}] date_taken=[{!s}]'
                        .format(photo_id, datetxt))

        @retry(attempts=3, waittime=10, randtime=True)
        def R_photos_setdates(kwargs):
            return nuflickr.photos.setdates(**kwargs)

        try:
            respDate = None
            respDate = R_photos_setdates(
                                dict(photo_id=photo_id,
                                     date_taken='{!s}'.format(datetxt),
                                     date_taken_granularity=0))

            # respDate = nuflickr.photos.setdates(
            #                     photo_id=photo_id,
            #                     date_taken='{!s}'.format(datetxt),
            #                     date_taken_granularity=0)
            logging.debug('Output for {!s}:'.format('respDate'))
            logging.debug(xml.etree.ElementTree.tostring(
                                    respDate,
                                    encoding='utf-8',
                                    method='xml'))

            if (args.verbose):
                niceprint('Set Date Response:[{!s}]'
                          .format(self.isGood(respDate)))

        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='210',
                        CaughtMsg='Flickrapi exception on photos.setdates',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True)
            # logging.error('Sleep 10 and try to set date again.')
            # niceprint('Sleep 10 and try to set date again.')
            # nutime.sleep(10)
        except (IOError, httplib.HTTPException):
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='211',
                        CaughtMsg='Caught IOError, HTTP exception'
                                  'on photos.setdates',
                        NicePrint=True)
            # logging.error('Sleep 10 and try to set date again.')
            # niceprint('Sleep 10 and try to set date again.')
            # nutime.sleep(10)
        except:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='212',
                        CaughtMsg='Caught exception on photos.setdates',
                        NicePrint=True,
                        exceptSysInfo=True)
            # logging.error('Sleep 10 and try to set date again.')
            # niceprint('Sleep 10 and try to set date again.')
            # nutime.sleep(10)
        finally:
            if (respDate is not None) and self.isGood(respDate):
                logging.debug('Set Date Response: OK!')

        return respDate

    # -------------------------------------------------------------------------
    # searchForDuplicates
    #
    # List Local pics, loaded pics into Flickr, pics not in sets on Flickr
    #
    # CODING: to be developed. Consider making allMedia (coming from
    # grabnewfiles from  uploadr) a global variable to pass onto this function
    def searchForDuplicates(self):

        pass

    @rate_limited(1) # 1 calls per second
    def rate4maddAlbumsMigrate(self):
        """
        """
        logging.debug('rate_limit timestamp:[{!s}]'
                      .format(int(round(nutime.time() * 1000))))


    # -------------------------------------------------------------------------
    # maddAlbumsMigrate
    #
    # maddAlbumsMigrate wrapper for multiprocessing purposes
    #
    def maddAlbumsMigrate(self, lock, running, mutex, filelist, countTotal):
        """ maddAlbumsMigrate

            Wrapper function for multiprocessing support to call uploadFile
            with a chunk of the files.
            lock = for database access control in multiprocessing
            running = shared value to count processed files in multiprocessing
            mutex = for running access control in multiprocessing
            countTotal = grand total of items.
        """

        for i, f in enumerate(filelist):
            logging.warning('===Current element of Chunk: [{!s}][{!s}]'
                            .format(i, f))

            # f[0] = files_id
            # f[1] = path
            # f[2] = set_name
            # f[3] = set_id
            niceprint('ID:[{!s}] Path:[{!s}] Set:[{!s}] SetID:[{!s}]'
                      .format(str(f[0]), f[1], f[2], f[3]),
                      fname='addAlbumMigrate')

            # row[1] = path for the file from table files
            setName = self.getSetNameFromFile(f[1],
                                              FILES_DIR,
                                              FULL_SET_NAME)
            try:
                terr = False
                tfind, tid = self.photos_find_tag(
                                    photo_id = f[0],
                                    intag = 'album:{}'.format(f[2] \
                                    if f[2] is not None
                                    else setName))
                niceprint('Found:[{!s}] TagId:[{!s}]'
                          .format(tfind, tid))
            except Exception as ex:
                reportError(Caught=True,
                             CaughtPrefix='+++',
                             CaughtCode='216',
                             CaughtMsg='Exception on photos_find_tag',
                             exceptUse=True,
                             exceptCode=ex.code,
                             exceptMsg=ex,
                             NicePrint=False,
                             exceptSysInfo=True)

                logging.warning('Error processing Photo_id:[{!s}]. '
                                'Continuing...'
                                .format(str(f[0])))
                niceprint('Error processing Photo_id:[{!s}]. Continuing...'
                          .format(str(f[0])),
                          fname='addAlbumMigrate')

                terr = True

            if not terr and not tfind:
                res_add_tag = self.photos_add_tags(
                                f[0],
                                ['album:"{}"'.format(f[2] \
                                        if f[2] is not None
                                        else setName)]
                              )
                logging.debug('res_add_tag: ')
                logging.debug(xml.etree.ElementTree.tostring(
                                        res_add_tag,
                                        encoding='utf-8',
                                        method='xml'))

            logging.debug('===Multiprocessing=== in.mutex.acquire(w)')
            mutex.acquire()
            running.value += 1
            xcount = running.value
            mutex.release()
            logging.info('===Multiprocessing=== out.mutex.release(w)')

            # Show number of files processed so far
            self.niceprocessedfiles(xcount, countTotal, False)

            self.rate4maddAlbumsMigrate()


    # -------------------------------------------------------------------------
    # addAlbumsMigrate
    #
    # Prepare for version 2.7.0 Add album info to loaded pics
    #
    def addAlbumsMigrate(self):

        # -----------------------------------------------------------------------------
        # Local Variables
        #
        #   mlockDB     = multiprocessing Lock for access to Database
        #   mmutex      = multiprocessing mutex for access to value mrunning
        #   mrunning    = multiprocessing Value to count processed photos
        mlockDB = None
        mmutex = None
        mrunning = None

        con = lite.connect(DB_PATH)
        con.text_factory = str
        with con:
            try:
                cur = con.cursor()
                cur.execute('SELECT files_id, path, sets.name, sets.set_id '
                            'FROM files LEFT OUTER JOIN sets ON '
                            'files.set_id = sets.set_id')
                existingMedia = cur.fetchall()
                logging.info('len(existingMedia)=[{!s}]'
                             .format(len(existingMedia)))
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='215',
                            CaughtMsg='DB error on SELECT FROM '
                                      'sets: [{!s}]'
                                      .format(e.args[0]),
                            NicePrint=True)
                return False

            countTotal=len(existingMedia)
            # running in multi processing mode
            if (args.processes and args.processes > 0):
                logging.debug('Running Pool of [{!s}] processes...'
                              .format(args.processes))
                logging.debug('__name__:[{!s}] to prevent recursive calling)!'
                              .format(__name__))

                # To prevent recursive calling, check if __name__ == '__main__'
                if __name__ == '__main__':
                    logging.debug('===Multiprocessing=== Setting up logger!')
                    multiprocessing.log_to_stderr()
                    logger = multiprocessing.get_logger()
                    logger.setLevel(LOGGING_LEVEL)

                    logging.debug('===Multiprocessing=== Lock defined!')

                    # ---------------------------------------------------------
                    # chunk
                    #
                    # Divides an iterable in slices/chunks of size size
                    #
                    from itertools import islice

                    def chunk(it, size):
                        """
                            Divides an iterable in slices/chunks of size size
                        """
                        it = iter(it)
                        # lambda: creates a returning expression function
                        # which returns slices
                        # iter, with the second argument () stops creating
                        # iterators when it reaches the end
                        return iter(lambda: tuple(islice(it, size)), ())

                    migratePool = []
                    mlockDB = multiprocessing.Lock()
                    mrunning = multiprocessing.Value('i', 0)
                    mmutex = multiprocessing.Lock()

                    sz = (len(existingMedia) // int(args.processes)) \
                         if ((len(existingMedia) // int(args.processes)) > 0) \
                         else 1

                    logging.debug('len(existingMedia):[{!s}] '
                                  'int(args.processes):[{!s}] '
                                  'sz per process:[{!s}]'
                                  .format(len(existingMedia),
                                          int(args.processes),
                                          sz))

                    # Split the Media in chunks to distribute accross Processes
                    for mexistingMedia in chunk(existingMedia, sz):
                        logging.warning('===Actual/Planned Chunk size: '
                                        '[{!s}]/[{!s}]'
                                        .format(len(mexistingMedia), sz))
                        logging.debug('===type(mexistingMedia)=[{!s}]'
                                      .format(type(mexistingMedia)))
                        logging.debug('===Job/Task Process: Creating...')
                        migrateTask = multiprocessing.Process(
                                            target=self.maddAlbumsMigrate,
                                            args=(mlockDB,
                                                  mrunning,
                                                  mmutex,
                                                  mexistingMedia,
                                                  countTotal,))
                        migratePool.append(migrateTask)
                        logging.debug('===Job/Task Process: Starting...')
                        migrateTask.start()
                        logging.debug('===Job/Task Process: Started')
                        if (args.verbose):
                            niceprint('===Job/Task Process: [{!s}] Started '
                                      'with pid:[{!s}]'
                                      .format(migrateTask.name,
                                              migrateTask.pid))

                    # Check status of jobs/tasks in the Process Pool
                    if LOGGING_LEVEL <= logging.DEBUG:
                        logging.debug('===Checking Processes launched/status:')
                        for j in migratePool:
                            niceprint('{!s}.is_alive = {!s}'
                                      .format(j.name, j.is_alive()))

                    # Regularly print status of jobs/tasks in the Process Pool
                    # Prints status while there are processes active
                    # Exits when all jobs/tasks are done.
                    while (True):
                        if not (any(multiprocessing.active_children())):
                            logging.debug('===No active children Processes.')
                            break
                        for p in multiprocessing.active_children():
                            logging.debug('==={!s}.is_alive = {!s}'
                                          .format(p.name, p.is_alive()))
                            if (args.verbose):
                                niceprint('==={!s}.is_alive = {!s}'
                                          .format(p.name, p.is_alive()))
                            mTaskActive = p
                        logging.info('===Will wait for 60 on '
                                     '{!s}.is_alive = {!s}'
                                     .format(mTaskActive.name,
                                             mTaskActive.is_alive()))
                        if (args.verbose):
                            niceprint('===Will wait for 60 on '
                                      '{!s}.is_alive = {!s}'
                                      .format(mTaskActive.name,
                                              mTaskActive.is_alive()))

                        mTaskActive.join(timeout=60)
                        logging.info('===Waited for 60s on '
                                     '{!s}.is_alive = {!s}'
                                     .format(mTaskActive.name,
                                             mTaskActive.is_alive()))
                        if (args.verbose):
                            niceprint('===Waited for 60s on '
                                      '{!s}.is_alive = {!s}'
                                      .format(mTaskActive.name,
                                              mTaskActive.is_alive()))

                    # Wait for join all jobs/tasks in the Process Pool
                    # All should be done by now!
                    for j in migratePool:
                        j.join()
                        if (args.verbose):
                            niceprint('==={!s} (is alive: {!s}).exitcode = {!s}'
                                      .format(j.name, j.is_alive(), j.exitcode))

                    logging.warning('===Multiprocessing=== pool joined! '
                                    'All processes finished.')
                    niceprint('===Multiprocessing=== pool joined! '
                              'All processes finished.')

                    # Will release (set to None) the nulockDB lock control
                    # this prevents subsequent calls to useDBLock( nuLockDB, False)
                    # to raise exception:
                    #    ValueError('semaphore or lock released too many times')
                    if (args.verbose):
                        niceprint('===Multiprocessing=== pool joined! '
                                  'What happens to mlockDB is None:[{!s}]? '
                                  'It seems not, it still has a value! '
                                  'Setting it to None!'
                                  .format(mlockDB is None))
                    mlockDB = None

                    # Show number of total files processed
                    self.niceprocessedfiles(mrunning.value,
                                            countTotal,
                                            True)

            else:
                count=0
                countTotal=len(existingMedia)
                for row in existingMedia:
                    count += 1
                    # row[0] = files_id
                    # row[1] = path
                    # row[2] = set_name
                    # row[3] = set_id
                    niceprint('ID:[{!s}] Path:[{!s}] Set:[{!s}] SetID:[{!s}]'
                              .format(str(row[0]), row[1], row[2], row[3]),
                              fname='addAlbumMigrate')

                    # row[1] = path for the file from table files
                    setName = self.getSetNameFromFile(row[1],
                                                      FILES_DIR,
                                                      FULL_SET_NAME)
                    try:
                        tfind, tid = self.photos_find_tag(
                                            photo_id = row[0],
                                            intag = 'album:{}'.format(row[2] \
                                            if row[2] is not None
                                            else setName))
                        niceprint('Found:[{!s}] TagId:[{!s}]'
                                  .format(tfind, tid))
                    except Exception as ex:
                        reportError(Caught=True,
                                     CaughtPrefix='+++',
                                     CaughtCode='216',
                                     CaughtMsg='Exception on photos_find_tag',
                                     exceptUse=True,
                                     exceptCode=ex.code,
                                     exceptMsg=ex,
                                     NicePrint=False,
                                     exceptSysInfo=True)

                        logging.warning('Error processing Photo_id:[{!s}]. '
                                        'Continuing...'
                                        .format(str(row[0])))
                        niceprint('Error processing Photo_id:[{!s}]. Continuing...'
                                  .format(str(row[0])),
                                  fname='addAlbumMigrate')

                        self.niceprocessedfiles(count, countTotal, False)

                        continue

                    if not tfind:
                        res_add_tag = self.photos_add_tags(
                                        row[0],
                                        ['album:"{}"'.format(row[2] \
                                                if row[2] is not None
                                                else setName)]
                                      )
                        logging.debug('res_add_tag: ')
                        logging.debug(xml.etree.ElementTree.tostring(
                                                res_add_tag,
                                                encoding='utf-8',
                                                method='xml'))
                    self.niceprocessedfiles(count, countTotal, False)

                self.niceprocessedfiles(count, countTotal, True)

        return True

    # -------------------------------------------------------------------------
    # listBadFiles
    #
    # Prepare for version 2.7.0 Add album info to loaded pics
    #
    def listBadFiles(self):

        con = lite.connect(DB_PATH)
        con.text_factory = str
        with con:
            try:
                cur = con.cursor()
                cur.execute('SELECT files_id, path, set_id, md5, tagged, '
                            'last_modified '
                            'FROM badfiles ORDER BY path')
                badFiles = cur.fetchall()
                logging.info('len(badFiles)=[{!s}]'
                             .format(len(badFiles)))
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='218',
                            CaughtMsg='DB error on SELECT FROM '
                                      'sets: [{!s}]'
                                      .format(e.args[0]),
                            NicePrint=True)
                return False

            count=0
            countTotal=len(badFiles)
            for row in badFiles:
                count += 1
                # row[0] = files_id
                # row[1] = path
                # row[2] = set_id
                # row[3] = md5
                # row[4] = tagged
                # row[5] = last_modified
                print('files_id|path|set_id|md5|tagged|last_modified')
                print('{!s}|{!s}|{!s}|{!s}|{!s}|{!s}'
                      .format(StrUnicodeOut(str(row[0])),
                              StrUnicodeOut(str(row[1])),
                              StrUnicodeOut(str(row[2])),
                              StrUnicodeOut(str(row[3])),
                              StrUnicodeOut(str(row[4])),
                              nutime.strftime(UPLDRConstants.TimeFormat,
                                              nutime.localtime(row[5]))))
                sys.stdout.flush()

            self.niceprocessedfiles(count, countTotal, True)

        return True



    # -------------------------------------------------------------------------
    # printStat
    #
    # List Local pics, loaded pics into Flickr, pics not in sets on Flickr
    #
    def printStat(self, InitialFoundFiles):
        """ printStat
        Shows Total photos and Photos Not in Sets on Flickr
        InitialFoundFiles = shows the Found files prior to processing
        """
        # Total Local photos count
        con = lite.connect(DB_PATH)
        con.text_factory = str

        countlocal = 0
        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT Count(*) FROM files")
                countlocal = cur.fetchone()[0]
                logging.info('Total photos on local: {}'.format(countlocal))
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='220',
                            CaughtMsg='DB error on SELECT FROM files: [{!s}]'
                                      .format(e.args[0]),
                            NicePrint=True)

        # Total Local badfiles photos count
        BadFilesCount = 0
        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT Count(*) FROM badfiles")
                BadFilesCount = cur.fetchone()[0]
                logging.info('Total badfiles count on local: {}'
                             .format(BadFilesCount))
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='230',
                            CaughtMsg='DB error on SELECT FROM '
                                      'badfiles: [{!s}]'
                                      .format(e.args[0]),
                            NicePrint=True)

        # Total FLickr photos count:
        #       find('photos').attrib['total']
        countflickr = 0
        res = self.people_get_photos()
        if not self.isGood(res):
            raise IOError(res)
        logging.debug('Output for people_get_photos:')
        logging.debug(xml.etree.ElementTree.tostring(res,
                                                     encoding='utf-8',
                                                     method='xml'))

        countflickr = format(res.find('photos').attrib['total'])
        logging.debug('Total photos on flickr: {!s}'.format(countflickr))

        # Total photos not on Sets/Albums on FLickr
        # (per_page=1 as only the header is required to obtain total):
        #       find('photos').attrib['total']
        try:
            res = self.photos_get_not_in_set(1)

        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='400',
                        CaughtMsg='Flickrapi exception on '
                                  'getNotInSet',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex)
        except (IOError, httplib.HTTPException):
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='401',
                        CaughtMsg='Caught IO/HTTP Error in '
                                  'getNotInSet')
        except:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='402',
                        CaughtMsg='Caught exception in '
                                  'getNotInSet',
                        exceptSysInfo=True)
        finally:
            logging.debug('Output for get_not_in_set:')
            logging.debug(xml.etree.ElementTree.tostring(
                                    res,
                                    encoding='utf-8',
                                    method='xml'))
            countnotinsets = 0
            if self.isGood(res):
                countnotinsets = int(format(
                                        res.find('photos').attrib['total']))
                logging.debug('Photos not in sets on flickr: {!s}'
                              .format(countnotinsets))

            # Print total stats counters
            niceprint('\n  Initial Found Files:[{!s:>6s}]\n'
                      '          - Bad Files:[{!s:>6s}] = [{!s:>6s}] \n'
                      '          Note: some Bad files may no longer exist!\n'
                      'Photos count:\n'
                      '                Local:[{!s:>6s}] \n'
                      '               Flickr:[{!s:>6s}] \n'
                      'Not in sets on Flickr:[{!s:>6s}]'
                      .format(str(InitialFoundFiles),
                              str(BadFilesCount),
                              str(InitialFoundFiles-BadFilesCount),
                              str(countlocal),
                              str(countflickr),
                              str(countnotinsets)))

        # List pics not in sets (if within a parameter)
        # Maximum allowed per_page by Flickr is 500.
        # Avoid going over in order not to have to handle multipl pages.
        if (args.list_photos_not_in_set and
                args.list_photos_not_in_set > 0 and
                countnotinsets > 0):
            niceprint('*****Listing Photos not in a set in Flickr******')
            # List pics not in sets (if within a parameter, default 10)
            # (per_page=min(args.list_photos_not_in_set, 500):
            #       find('photos').attrib['total']
            res = self.photos_get_not_in_set(min(args.list_photos_not_in_set,
                                                 500))
            if not self.isGood(res):
                raise IOError(res)
            logging.debug('Output for list get_not_in_set:')
            logging.debug(xml.etree.ElementTree.tostring(res,
                                                         encoding='utf-8',
                                                         method='xml'))
            for count, row in enumerate(res.find('photos').findall('photo')):
                logging.info('Photo get_not_in_set id:[{!s}] title:[{!s}]'
                             .format(row.attrib['id'],
                                     row.attrib['title']))
                logging.debug(xml.etree.ElementTree.tostring(row,
                                                             encoding='utf-8',
                                                             method='xml'))
                niceprint('Photo get_not_in_set: id:[{!s}] title:[{!s}] '
                          .format(row.attrib['id'],
                                  row.attrib['title']))
                logging.info('count=[{!s}]'.format(count))
                if (count == 500) or \
                        (count >= (args.list_photos_not_in_set-1)) or \
                        (count >= (countnotinsets-1)):
                    logging.info('Stopped at photo [{!s}] listing '
                                  'photos not in a set'.format(count))
                    break
            niceprint('*****Completed Listing Photos not in a set '
                      'in Flickr******')

# =============================================================================
# Main code
#
niceprint('--------- (V{!s}) Start time: {!s} ---------'
          .format(UPLDRConstants.Version,
                  nutime.strftime(UPLDRConstants.TimeFormat)))
if __name__ == "__main__":
    # Ensure that only once instance of this script is running
    f = open(LOCK_PATH, 'w')
    try:
        fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as e:
        if e.errno == errno.EAGAIN:
            sys.stderr.write('[{!s}] Script already running.\n'
                             .format(
                                nutime.strftime(UPLDRConstants.TimeFormat)))
            sys.stderr.flush()
            sys.exit(-1)
        raise

    parser = argparse.ArgumentParser(
                        description='Upload files to Flickr. '
                                    'Uses uploadr.ini as config file.',
                        epilog='by oPromessa, 2017, 2018'
                        )

    # Verbose related options
    vgrpparser = parser.add_argument_group('Verbose and dry-run options')
    vgrpparser.add_argument('-v', '--verbose', action='store_true',
                            help='Provides some more verbose output. '
                                 'See also -x option. '
                                 'See also LOGGING_LEVEL value in INI file.')
    vgrpparser.add_argument('-x', '--verbose-progress', action='store_true',
                             help='Provides progress indicator on each upload. '
                                  'Normally used in conjunction with -v option.'
                                  ' See also LOGGING_LEVEL value in INI file.')
    vgrpparser.add_argument('-n', '--dry-run', action='store_true',
                            help='Dry run. No changes are actually performed.')

    # Information related options
    igrpparser = parser.add_argument_group('Information options')
    igrpparser.add_argument('-i', '--title', action='store',
                            help='Title for uploaded files. '
                                 'Overwrites title set in INI config file. '
                                 'If not specified and not set in INI file, '
                                 'it uses filename as title (*Recommended).')
    igrpparser.add_argument('-e', '--description', action='store',
                            help='Description for uploaded files'
                                 'Overwrites description set in INI file. ')
    igrpparser.add_argument('-t', '--tags', action='store',
                            help='Space-separated tags for uploaded files. '
                                 'It appends to the tags defined in INI file.')
    # used in printStat function
    igrpparser.add_argument('-l', '--list-photos-not-in-set',
                            metavar='N', type=int,
                            help='List as many as N photos not in set. '
                                 'Maximum listed photos is 500.')
    # finds duplicated images (based on checksum, titlename, setName) in Flickr
    igrpparser.add_argument('-z', '--search-for-duplicates',
                            action='store_true',
                            help='Lists duplicated files: same checksum, '
                                 'same title, list SetName (if different). '
                                 'Not operational at this time.')

    # Processing related options
    pgrpparser = parser.add_argument_group('Processing related options')
    pgrpparser.add_argument('-r', '--drip-feed', action='store_true',
                            help='Wait a bit between uploading individual '
                                 'files.')
    pgrpparser.add_argument('-p', '--processes',
                            metavar='P', type=int,
                            help='Number of photos to upload simultaneously.')
    pgrpparser.add_argument('-u', '--not-is-already-uploaded',
                            action='store_true',
                            help='Do not check if file is already uploaded '
                                 'and exists on flickr prior to uploading.')
    # run in daemon mode uploading every X seconds
    pgrpparser.add_argument('-d', '--daemon', action='store_true',
                            help='Run forever as a daemon.'
                                 'Uploading every SLEEP_TIME seconds. Please '
                                 'note it only performs upload/replace.')

    # Cater for bad files. files in your Library that flickr does not recognize
    # Options: -b, -c, -s and -g
    bgrpparser = parser.add_argument_group('Handling bad and excluded files')
    # -b add files to badfiles table
    bgrpparser.add_argument('-b', '--bad-files', action='store_true',
                        help='Save on database bad files to prevent '
                             'continuous uploading attempts. Bad files are '
                             'files in your Library that flickr does not '
                             'recognize (Error 5) or are too large (Error 8). '
                             'Check also option -c.')
    # -c clears the badfiles table to allow a reset of the list
    bgrpparser.add_argument('-c', '--clean-bad-files', action='store_true',
                        help='Resets the badfiles table/list to allow a new '
                             'uploading attempt for bad files. Bad files are '
                             'files in your Library that flickr does not '
                             'recognize (Error 5) or are too large (Error 8). '
                             'Check also option -b.')
    # -s list the badfiles table
    bgrpparser.add_argument('-s', '--list-bad-files', action='store_true',
                        help='List the badfiles table/list.')
    # when you change EXCLUDED_FOLDERS setting
    bgrpparser.add_argument('-g', '--remove-excluded', '--remove-ignored',
                            action='store_true',
                            help='Remove previously uploaded files, that are '
                                 'now being excluded due to change of the INI '
                                 'file configuration EXCLUDED_FOLDERS.'
                                 'NOTE: Please drop use of --remove-ignored '
                                 'in favor of --remove-excluded or -r. '
                                 'From version 2.7.0 it will be dropped.')

    # Migration related options
    # 2.7.0 Version will add album/setName as one
    agrpparser = parser.add_argument_group('Migrate to v2.7.0')
    agrpparser.add_argument('--add-albums-migrate', action='store_true',
                            help='From v2.7.0 onwards, uploadr adds to Flickr '
                                 'an album tag to each pic. '
                                 'This option adds such tag to previously '
                                 'loaded pics. uploadr v2.7.0 will perform '
                                 'automatically such migration upon first run '
                                 'This option is *only* available to re-run '
                                 'it, should it be necessary.')

    # parse arguments
    args = parser.parse_args()

    # Debug to show arguments
    if LOGGING_LEVEL <= logging.INFO:
        niceprint('Output for arguments(args):')
        pprint.pprint(args)

    if args.verbose:
        niceprint('FILES_DIR: [{!s}]'.format(StrUnicodeOut(FILES_DIR)))

    logging.warning('FILES_DIR: [{!s}]'.format(StrUnicodeOut(FILES_DIR)))
    if FILES_DIR == "":
        niceprint('Please configure the name of the folder [FILES_DIR] '
                  'in the INI file [normally uploadr.ini], '
                  'with media available to sync with Flickr.')
        sys.exit(7)
    else:
        if not os.path.isdir(FILES_DIR):
            niceprint('Please configure the name of an existant folder '
                      'in the INI file [normally uploadr.ini] '
                      'with media available to sync with Flickr.')
            sys.exit(8)

    if FLICKR["api_key"] == "" or FLICKR["secret"] == "":
        niceprint('Please enter an API key and secret in the configuration '
                  'script file, normaly uploadr.ini (see README).')
        sys.exit(9)

    # Instantiate class Uploadr
    logging.debug('Instantiating the Main class flick = Uploadr()')
    flick = Uploadr()

    # Setup the database
    flick.setupDB()
    if (args.clean_bad_files):
        flick.cleanDBbadfiles()

    if args.daemon:
        # Will run in daemon mode every SLEEP_TIME seconds
        logging.warning('Will run in daemon mode every {!s} seconds'
                        .format(SLEEP_TIME))
        logging.warning('Make sure you have previously authenticated!')
        flick.run()
    else:
        niceprint('Checking if token is available... if not will authenticate')
        if (not flick.checkToken()):
            flick.authenticate()

        if args.add_albums_migrate:
            niceprint('Performing preparation for migrate to 2.7.0',
                      fname='addAlbumsMigrate')

            if flick.addAlbumsMigrate():
                niceprint('Successfully added album tags to pics '
                          'on upload.',
                           fname='addAlbumsMigrate')
            else:
                logging.warning('Failed adding album tags to pics '
                                'on upload. '
                                'Please check logs, correct, and retry.')
                niceprint('Failed adding album tags to pics '
                          'on upload. '
                          'Please check logs, correct, and retry.',
                          fname='addAlbumsMigrate')
        elif  args.list_bad_files:
            niceprint('Listing badfiles: Start.',
                  fname='listBadFiles')
            flick.listBadFiles()
            niceprint('Listing badfiles: End. No more options will run.',
                  fname='listBadFiles')
        else:
            flick.removeUselessSetsTable()
            flick.getFlickrSets()
            flick.convertRawFiles()
            flick.upload()
            flick.removeDeletedMedia()

            if args.search_for_duplicates:
                flick.searchForDuplicates()

            if args.remove_excluded:
                flick.removeExcludedMedia()

            flick.createSets()
            flick.printStat(UPLDRConstants.nuMediacount)

niceprint('--------- (V{!s}) End time: {!s} ---------'
          .format(UPLDRConstants.Version,
                  nutime.strftime(UPLDRConstants.TimeFormat)))
sys.stderr.write('--------- ' + 'End: ' + ' ---------\n')
sys.stderr.flush()
