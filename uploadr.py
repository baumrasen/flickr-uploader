#!/usr/bin/env python

"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

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

    TimeFormat = '%Y.%m.%d %H:%M:%S'
    # For future use...
    # UTF = 'utf-8'
    Version = '2.6.6'
    # Identify the execution Run of this process
    Run = eval(time.strftime('int("%j")+int("%H")*100+int("%M")'))

    # -------------------------------------------------------------------------
    # Color Codes for colorful output
    W = ''   # white (normal)
    R = ''   # red
    G = ''   # green
    O = ''   # orange
    B = ''   # blue
    P = ''   # purple

    # -------------------------------------------------------------------------
    # class UPLDRConstants __init__
    #
    def __init__(self):
        """ class UPLDRConstants __init__
        """
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
nutime = time
nuflickr = None
nulockDB = None
numutex = None
nurunning = None
nuMediacount = None


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
def niceprint(s):
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
#     print retry_divmod([5, 'H'])
# except:
#     logging.error('Error Caught (Overall Catchall)... Continuing')
# finally:
#     logging.error('...Continuing')
# nargslist=dict(Caught=True, CaughtPrefix='+++')
# retry_reportError(nargslist)


# =============================================================================
# Read Config from config.ini file
# Obtain configuration from uploadr.ini
# Refer to contents of uploadr.ini for explanation on configuration parameters
config = ConfigParser.ConfigParser()
INIFiles = config.read(os.path.join(os.path.dirname(sys.argv[0]),
                                    "uploadr.ini"))
if not INIFiles:
    sys.stderr.write('[{!s}]:[{!s}][ERROR   ]:[uploadr] '
                     'INI file: [{!s}] not found!.\n'
                     .format(nutime.strftime(UPLDRConstants.TimeFormat),
                             os.getpid(),
                             os.path.join(os.path.dirname(sys.argv[0]),
                                          'uploadr.ini')))
    sys.exit(2)
if config.has_option('Config', 'FILES_DIR'):
    FILES_DIR = unicode(eval(config.get('Config', 'FILES_DIR')), 'utf-8') \
                if sys.version_info < (3, ) \
                else str(eval(config.get('Config', 'FILES_DIR')))
else:
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
                         'folder from EXCLUDED_FOLDERS:[{!s}]\n'
                         .format(nutime.strftime(UPLDRConstants.TimeFormat),
                                 os.getpid(),
                                 StrUnicodeOut(folder)))
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
ALLOWED_EXT = eval(config.get('Config', 'ALLOWED_EXT'))
RAW_EXT = eval(config.get('Config', 'RAW_EXT'))
FILE_MAX_SIZE = eval(config.get('Config', 'FILE_MAX_SIZE'))
MANAGE_CHANGES = eval(config.get('Config', 'MANAGE_CHANGES'))
RAW_TOOL_PATH = eval(config.get('Config', 'RAW_TOOL_PATH'))
CONVERT_RAW_FILES = eval(config.get('Config', 'CONVERT_RAW_FILES'))
FULL_SET_NAME = eval(config.get('Config', 'FULL_SET_NAME'))
MAX_SQL_ATTEMPTS = eval(config.get('Config', 'MAX_SQL_ATTEMPTS'))
MAX_UPLOAD_ATTEMPTS = eval(config.get('Config', 'MAX_UPLOAD_ATTEMPTS'))
LOGGING_LEVEL = (config.get('Config', 'LOGGING_LEVEL')
                 if config.has_option('Config', 'LOGGING_LEVEL')
                 else logging.WARNING)

# =============================================================================
# Logging
#
# Obtain configuration level from Configuration file.
# If not available or not valid assume WARNING level and notify of that fact.
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
if (int(LOGGING_LEVEL) if str.isdigit(LOGGING_LEVEL) else 99) not in [
                        logging.NOTSET,
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
# Force conversion of LOGGING_LEVEL into int() for later use in conditionals
LOGGING_LEVEL = int(LOGGING_LEVEL)
logging.basicConfig(stream=sys.stderr,
                    level=int(LOGGING_LEVEL),
                    datefmt=UPLDRConstants.TimeFormat,
                    format=UPLDRConstants.P+'[' +
                           str(UPLDRConstants.Run)+']' +
                           '[%(asctime)s]:[%(processName)-11s]' +
                           UPLDRConstants.W +
                           '[%(levelname)-8s]:[%(name)s] %(message)s')

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
    if (False):
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
            sys.exit(2)

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
                logging.info('Token Non-Existant.')
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
        global nuMediacount

        niceprint("*****Uploading files*****")

        allMedia = self.grabNewFiles()
        # If managing changes, consider all files
        if MANAGE_CHANGES:
            logging.warning('MANAGED_CHANGES is True. Reviewing allMedia.')
            changedMedia = allMedia

        changedMedia_count = len(changedMedia)
        nuMediacount = changedMedia_count
        niceprint('Found [{!s}] files to upload.'
                  .format(str(changedMedia_count)))

        count = 0
        for i, file in enumerate(changedMedia):
            logging.debug('file:[{!s}] type(file):[{!s}]'
                          .format(file, type(file)))
            # lock parameter not used (set to None) under single processing
            success = self.uploadFile(lock=None, file=file)
            count = count + 1

        niceprint("*****Completed uploading files*****")

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
            for f in filenames:
                filePath = os.path.join(dirpath, f)
                if self.isFileIgnored(filePath):
                    logging.debug('File {!s} in EXCLUDED_FOLDERS:'
                                  .format(filePath.encode('utf-8')))
                    continue
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
    # isFileIgnored
    #
    # Check if a filename is within the list of EXCLUDED_FOLDERS. Returns:
    #   True = if filename's folder is within one of the EXCLUDED_FOLDERS
    #   False = if filename's folder not on one of the EXCLUDED_FOLDERS
    #
    def isFileIgnored(self, filename):
        """ isFileIgnored

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
                logging.debug('Returning isFileIgnored:[True]')
                return True

        logging.debug('Returning isFileIgnored:[False]')
        return False

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

        if (args.verbose):
            niceprint('Checking file:[{!s}]...'
                      .format(StrUnicodeOut(file)))

        if FULL_SET_NAME:
            setName = os.path.relpath(os.path.dirname(file),
                                      FILES_DIR)
        else:
            head, setName = os.path.split(os.path.dirname(file))

        success = False
        # For tracking bad response from search_photos
        TraceBackIndexError = False

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
                            tags='{} checksum:{} {}'
                                 .format(
                                        FLICKR["tags"],
                                        '999',
                                        '')
                                        .replace(',', ''),
                            is_public=str(FLICKR["is_public"]),
                            is_family=str(FLICKR["is_family"]),
                            is_friend=str(FLICKR["is_friend"])
                            )
    
                    logging.info('uploadResp: ')
                    logging.info(xml.etree.ElementTree.tostring(
                                        uploadResp,
                                        encoding='utf-8',
                                        method='xml'))
                    logging.warning('uploadResp:[{!s}]'
                                    .format(self.isGood(uploadResp)))
    
                    # Save photo_id returned from Flickr upload
                    photo_id = uploadResp.findall('photoid')[0].text
                    logging.warning('Uploaded photo_id=[{!s}] [{!s}] '
                                    'Ok. Will check for issues ('
                                    'duplicates or wrong checksum)'
                                    .format(photo_id,
                                            StrUnicodeOut(file)))
                    if (args.verbose):
                        niceprint('Uploaded photo_id=[{!s}] [{!s}] '
                                  'Ok. Will check for issues ('
                                  'duplicates or wrong checksum)'
                                  .format(photo_id,
                                          StrUnicodeOut(file)))
    
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
            if (format(ex.code) == '5'):
                # Add to db the file NOT uploaded
                # Control for when running multiprocessing set locking
                niceprint('Adding to Bad files table:[{!s}]'
                          .format(file))
                logging.info('Bad file:[{!s}]'.format(file))
    
        return success

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
            sys.exit(-1)
        raise
    parser = argparse.ArgumentParser(
                        description='Upload files to Flickr. '
                                    'Uses uploadr.ini as config file.'
                        )
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Provides some more verbose output. '
                             'Will provide progress information on upload. '
                             'See also LOGGING_LEVEL value in INI file.')
    
    # parse arguments
    args = parser.parse_args()

    # Debug to show arguments
    if LOGGING_LEVEL <= logging.INFO:
        niceprint('Output for arguments(args):')
        pprint.pprint(args)

    if args.verbose:
        niceprint('FILES_DIR: [{!s}]'.format(FILES_DIR))

    logging.warning('FILES_DIR: [{!s}]'.format(FILES_DIR))
    if FILES_DIR == "":
        niceprint('Please configure the name of the folder [FILES_DIR] '
                  'in the INI file [normally uploadr.ini], '
                  'with media available to sync with Flickr.')
        sys.exit(2)
    else:
        if not os.path.isdir(FILES_DIR):
            niceprint('Please configure the name of an existant folder '
                      'in the INI file [normally uploadr.ini] '
                      'with media available to sync with Flickr.')
            sys.exit(2)

    if FLICKR["api_key"] == "" or FLICKR["secret"] == "":
        niceprint('Please enter an API key and secret in the configuration '
                  'script file, normaly uploadr.ini (see README).')
        sys.exit(2)

    # Instantiate class Uploadr
    logging.debug('Instantiating the Main class flick = Uploadr()')
    flick = Uploadr()

    niceprint("Checking if token is available... if not will authenticate")
    if (not flick.checkToken()):
        flick.authenticate()

    flick.upload()

niceprint('--------- (V{!s}) End time: {!s} ---------'
          .format(UPLDRConstants.Version,
                  nutime.strftime(UPLDRConstants.TimeFormat)))
sys.stderr.write('--------- ' + 'End: ' + ' ---------\n')
