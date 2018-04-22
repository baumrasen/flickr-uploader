#!/usr/bin/env python

"""
    by oPromessa, 2017
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
import logging
# Check if required httplib: Used only on exception httplib.HTTPException
try:
    import httplib as httplib      # Python 2
except ImportError:
    import http.client as httplib  # Python 3
import argparse
import mimetypes
import os
import time
import sqlite3 as lite
import hashlib
try:
    # Use portalocker if available. Required for Windows systems
    import portalocker as FileLocker  # noqa
    FileLock = FileLocker.lock
except ImportError:
    # Use fcntl
    import fcntl as FileLocker
    FileLock = FileLocker.lockf
import errno
import subprocess
import multiprocessing
import flickrapi
import xml
# Avoids error on some systems:
#    AttributeError: 'module' object has no attribute 'etree'
#    on logging.info(xml.etree.ElementTree.tostring(...
try:
    dummyxml = xml.etree.ElementTree.tostring(
        xml.etree.ElementTree.Element('xml.etree'),
        encoding='utf-8',
        method='xml')
except AttributeError:
    sys.stderr.write('Importing xml.etree.ElementTree...')
    try:
        import xml.etree.ElementTree
        sys.stderr.write('done.')
    except ImportError:
        sys.stderr.write('failed with ImportError.')
        raise
finally:
    sys.stderr.write(' Continuing.\n')
    sys.stderr.flush()
import os.path
import pprint
# -----------------------------------------------------------------------------
# Helper class and functions for UPLoaDeR Global Constants.
import lib.UPLDRConstants as UPLDRConstantsClass
# -----------------------------------------------------------------------------
# Helper class and functions to print messages.
import lib.niceprint as niceprint
# -----------------------------------------------------------------------------
# Helper class and functions to rate/pace limiting function calls and run a
# function multiple attempts/times on error
import lib.rate_limited as rate_limited
# -----------------------------------------------------------------------------
# Helper class and functions to load, process and verify INI configuration.
import lib.myconfig as myconfig

# =============================================================================
# Logging init code
#
# Getting definitions from UPLDRConstants
UPLDRConstants = UPLDRConstantsClass.UPLDRConstants()
# Sets LOGGING_LEVEL to allow logging even if everything else is wrong!
logging.basicConfig(stream=sys.stderr,
                    level=int(str(logging.WARNING)),  # logging.DEBUG
                    datefmt=UPLDRConstants.TimeFormat,
                    format=UPLDRConstants.P + '[' +
                    str(UPLDRConstants.Run) + ']' +
                    '[%(asctime)s]:[%(processName)-11s]' +
                    UPLDRConstants.W +
                    '[%(levelname)-8s]:[%(name)s] %(message)s')
# Inits with default configuration values.
xCfg = myconfig.MyConfig()
# Get LOGGING_LEVEL defaul configuration
xCfg.LOGGING_LEVEL = int(str(xCfg.LOGGING_LEVEL))
# Update logging level as per LOGGING_LEVEL from default config
logging.getLogger().setLevel(xCfg.LOGGING_LEVEL)
# -----------------------------------------------------------------------------


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
# Uses global ARGS.verbose-progress parameter
#
def callback(progress):
    """ callback

    Print progress % while uploading into Flickr.
    Valid only if global variable ARGS.verbose_progress is True
    """
    # only print rounded percentages: 0, 10, 20, 30, up to 100
    # adapt as required
    # if ((progress % 10) == 0):
    # if verbose option is set
    if (ARGS.verbose_progress):
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
        logging.info('Adding mimetype "video/3gp"/".3gp"')
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

        logging.debug('Entering useDBLock with useDBoperation:[{!s}].'
                      .format(useDBoperation))

        if useDBthisLock is None:
            return useDBLockReturn

        if useDBoperation is None:
            return useDBLockReturn

        if (ARGS.processes is not None) and\
           (ARGS.processes) and \
           (ARGS.processes > 0):
            if useDBoperation:
                # Control for when running multiprocessing set locking
                logging.debug('===Multiprocessing=== in.lock.acquire')
                try:
                    if useDBthisLock.acquire():
                        useDBLockReturn = True
                except BaseException:
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
                except BaseException:
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
                np.niceprint('Files Processed:[{!s:>6s}] of [{!s:>6s}]'
                             .format(count, cTotal))
        else:
            if (int(count) % 100 > 0):
                np.niceprint('Files Processed:[{!s:>6s}] of [{!s:>6s}]'
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
        nuflickr = flickrapi.FlickrAPI(xCfg.FLICKR["api_key"],
                                       xCfg.FLICKR["secret"],
                                       token_cache_location=xCfg.TOKEN_CACHE)
        # Get request token
        np.niceprint('Getting new token.')
        try:
            nuflickr.get_request_token(oauth_callback='oob')
        except Exception as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='004',
                        CaughtMsg='Exception on get_request_token. '
                                   'Exiting...',
                        exceptUse=True,
                        # exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True,
                        exceptSysInfo=True)
            sys.exit(4)

        # Show url. Copy and paste it in your browser
        authorize_url = nuflickr.auth_url(perms=u'delete')
        np.niceprint('Copy and paste following authorizaiton URL '
                     'in your browser to obtain Verifier Code.')
        print(authorize_url)

        # Prompt for verifier code from the user.
        verifier = unicode(raw_input(  # noqa
                                     'Verifier code (NNN-NNN-NNN): ')) \
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
            sys.exit(5)

        np.niceprint('{!s} with {!s} permissions: {!s}'.format(
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
        logging.debug('TOKEN_CACHE:[{!s}]'.format(xCfg.TOKEN_CACHE))
        nuflickr = flickrapi.FlickrAPI(xCfg.FLICKR["api_key"],
                                       xCfg.FLICKR["secret"],
                                       token_cache_location=xCfg.TOKEN_CACHE)

        try:
            # Check if token permissions are correct.
            if nuflickr.token_valid(perms='delete'):
                logging.info('Cached token obtained: {!s}'
                             .format(nuflickr.token_cache.token))
                return nuflickr.token_cache.token
            else:
                logging.warning('Token Non-Existant.')
                return None
        except BaseException:
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
        np.niceprint('*****Removing files from Excluded Folders*****')

        if (not FLICK.checkToken()):
            FLICK.authenticate()
        con = lite.connect(xCfg.DB_PATH)
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
                if (self.isFileExcluded(unicode(row[1], 'utf-8')  # noqa
                                        if sys.version_info < (3, )
                                        else str(row[1]))):
                    # Running in single processing mode, no need for lock
                    self.deleteFile(row, cur)

        # Closing DB connection
        if con is not None:
            con.close()

        np.niceprint('*****Completed files from Excluded Folders*****')

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

        np.niceprint('*****Removing deleted files*****')

        if (not FLICK.checkToken()):
            FLICK.authenticate()
        con = lite.connect(xCfg.DB_PATH)
        con.text_factory = str

        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT files_id, path FROM files")
                rows = cur.fetchall()
                np.niceprint('[{!s:>6s}] will be checked for Removal...'
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
                    # Running in single processing mode, no need for lock
                    success = self.deleteFile(row, cur)
                    logging.warning('deleteFile result: {!s}'.format(success))
                    count = count + 1
                    if (count % 3 == 0):
                        np.niceprint('[{!s:>6s}] files removed...'
                                     .format(str(count)))
            if (count % 100 > 0):
                np.niceprint('[{!s:>6s}] files removed...'
                             .format(str(count)))

        # Closing DB connection
        if con is not None:
            con.close()

        np.niceprint('*****Completed deleted files*****')

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

        np.niceprint("*****Uploading files*****")

        con = None
        allMedia, rawfiles = self.grabNewFiles()
        # If managing changes, consider all files
        if xCfg.MANAGE_CHANGES:
            logging.warning('MANAGE_CHANGES is True. Reviewing allMedia.')
            changedMedia = allMedia

        # If not, then get just the new and missing files
        else:
            logging.warning('MANAGE_CHANGES is False. Reviewing only '
                            'changedMedia.')
            con = lite.connect(xCfg.DB_PATH)
            con.text_factory = str
            with con:
                cur = con.cursor()
                cur.execute("SELECT path FROM files")
                existingMedia = set(file[0] for file in cur.fetchall())
                changedMedia = set(allMedia) - existingMedia

        changedMedia_count = len(changedMedia)
        UPLDRConstants.nuMediacount = changedMedia_count
        np.niceprint('Found [{!s:>6s}] files to upload.'
                     .format(str(changedMedia_count)))

        # Convert Raw files
        FLICK.convertRawFiles(rawfiles, changedMedia)

        if (ARGS.bad_files):
            # Cater for bad files
            con = lite.connect(xCfg.DB_PATH)
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
            np.niceprint('Removing {!s} badfiles. Found {!s} files to upload.'
                         .format(len(badMedia),
                                 changedMedia_count))

        # running in multi processing mode
        if (ARGS.processes and ARGS.processes > 0):
            logging.debug('Running Pool of [{!s}] processes...'
                          .format(ARGS.processes))
            logging.debug('__name__:[{!s}] to prevent recursive calling)!'
                          .format(__name__))

            # To prevent recursive calling, check if __name__ == '__main__'
            if __name__ == '__main__':
                logging.debug('===Multiprocessing=== Setting up logger!')
                multiprocessing.log_to_stderr()
                logger = multiprocessing.get_logger()
                logger.setLevel(xCfg.LOGGING_LEVEL)

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

                sz = (len(changedMedia) // int(ARGS.processes)) \
                    if ((len(changedMedia) // int(ARGS.processes)) > 0) \
                    else 1

                logging.debug('len(changedMedia):[{!s}] '
                              'int(ARGS.processes):[{!s}] '
                              'sz per process:[{!s}]'
                              .format(len(changedMedia),
                                      int(ARGS.processes),
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
                    if (ARGS.verbose):
                        np.niceprint('===Job/Task Process: [{!s}] Started '
                                     'with pid:[{!s}]'
                                     .format(uploadTask.name,
                                             uploadTask.pid))

                # Check status of jobs/tasks in the Process Pool
                if xCfg.LOGGING_LEVEL <= logging.DEBUG:
                    logging.debug('===Checking Processes launched/status:')
                    for j in uploadPool:
                        np.niceprint('{!s}.is_alive = {!s}'
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
                        uploadTaskActive = p
                    logging.info('===Will wait for 60 on {!s}.is_alive = {!s}'
                                 .format(uploadTaskActive.name,
                                         uploadTaskActive.is_alive()))
                    if (ARGS.verbose_progress):
                        np.niceprint('===Will wait for 60 on '
                                     '{!s}.is_alive = {!s}'
                                     .format(uploadTaskActive.name,
                                             uploadTaskActive.is_alive()))

                    uploadTaskActive.join(timeout=60)
                    logging.info('===Waited for 60s on {!s}.is_alive = {!s}'
                                 .format(uploadTaskActive.name,
                                         uploadTaskActive.is_alive()))
                    if (ARGS.verbose):
                        np.niceprint('===Waited for 60s on '
                                     '{!s}.is_alive = {!s}'
                                     .format(uploadTaskActive.name,
                                             uploadTaskActive.is_alive()))

                # Wait for join all jobs/tasks in the Process Pool
                # All should be done by now!
                for j in uploadPool:
                    j.join()
                    if (ARGS.verbose):
                        np.niceprint('==={!s} (is alive: {!s}).exitcode = {!s}'
                                     .format(j.name, j.is_alive(), j.exitcode))

                logging.warning('===Multiprocessing=== pool joined! '
                                'All processes finished.')

                # Will release (set to None) the nulockDB lock control
                # this prevents subsequent calls to useDBLock(nuLockDB, False)
                # to raise exception:
                #    ValueError('semaphore or lock released too many times')
                logging.info('===Multiprocessing=== pool joined! '
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
                np.niceprint('Pool not in __main__ process. '
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
                if ARGS.drip_feed and success and i != changedMedia_count - 1:
                    np.niceprint('Waiting [{!s}] seconds before next upload'
                                 .format(str(xCfg.DRIP_TIME)))
                    nutime.sleep(xCfg.DRIP_TIME)
                count = count + 1
                self.niceprocessedfiles(count,
                                        UPLDRConstants.nuMediacount,
                                        False)

            # Show number of total files processed
            self.niceprocessedfiles(count, UPLDRConstants.nuMediacount, True)

        # Closing DB connection
        if con is not None:
            con.close()
        np.niceprint("*****Completed uploading files*****")

    # -------------------------------------------------------------------------
    # convertRawFiles
    #
    def convertRawFiles(self, rawfiles, finalMediafiles):
        """ convertRawFiles

            rawfiles        = List with raw files
            finalMediafiles = Converted Raw files will be appended to this list
                              list will be sorted
        """

        # CODING: To do: save RAWfiles list from grabNewFiles function...
        # for post-processing...

        if (not xCfg.CONVERT_RAW_FILES):
            return

        np.niceprint('*****Converting files*****')
        for fullpath in rawfiles:
            dirpath, f = os.path.split(fullpath)
            fnameonly = os.path.splitext(f)[0]
            ext = os.path.splitext(f)[1][1:].lower()
            if self.convertRawFile(dirpath, f, ext, fnameonly):
                try:
                    okfileSize = True
                    fileSize = os.path.getsize(
                        os.path.join(StrUnicodeOut(dirpath),
                                     StrUnicodeOut(fnameonly) + '.JPG'))
                    logging.debug('Converted .JPG file size=[{!s}]'
                                  .format(fileSize))
                except Exception:
                    okfileSize = False
                    reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='009',
                                CaughtMsg='Exception in size convertRawFiles',
                                NicePrint=False,
                                exceptSysInfo=True)

                if okfileSize and (fileSize < xCfg.FILE_MAX_SIZE):
                    finalMediafiles.append(
                        os.path.normpath(
                            StrUnicodeOut(dirpath) +
                            StrUnicodeOut("/") +
                            StrUnicodeOut(fnameonly).replace("'", "\'") +
                            StrUnicodeOut('.JPG')))
                else:
                    np.niceprint('Skipping file due to '
                                 'size restriction/issue: [{!s}]'
                                 .format(os.path.normpath(
                                     StrUnicodeOut(dirpath) +
                                     StrUnicodeOut('/') +
                                     StrUnicodeOut(f))))
            else:
                np.niceprint('Convert raw file failed. '
                             'Skipping file: [{!s}]'
                             .format(os.path.normpath(
                                 StrUnicodeOut(dirpath) +
                                 StrUnicodeOut('/') +
                                 StrUnicodeOut(f))))
        finalMediafiles.sort()
        np.niceprint('*****Completed converting files*****')

    # -------------------------------------------------------------------------
    # convertRawFile
    #
    def convertRawFile(self, Ddirpath, Ffname, Fext, Ffnameonly):
        """ convertRawFile

        Ddirpath   = dirpath folder for filename
        Ffname     = filename (including extension)
        Fext       = lower case extension of current file
        Ffnameonly = filiename without extension
        """
        # ---------------------------------------------------------------------
        # convertRawFileCommand
        #
        def convertRawFileCommand(ConvertOrCopyTags):
            """ convertRawFileCommand

            ConvertOrCopyTags = 'Convert'  converts a raw file to JPG
                                'CopyTags' copy tags from raw file to JPG
            """

            assert ConvertOrCopyTags in ['Convert', 'CopyTags'],\
                niceassert('convertRawFileCommand: wrong argument:[{!s}]'
                           .format(ConvertOrCopyTags))

            resultCmd = True
            if ConvertOrCopyTags == 'Convert':
                flag = "-PreviewImage" \
                       if Fext == 'cr2' else "-JpgFromRaw"
                command = os.path.join(StrUnicodeOut(xCfg.RAW_TOOL_PATH),
                                       'exiftool') +\
                    " -b " + flag + " -w .JPG -ext " + Fext + " -r " +\
                    "'" + os.path.join(StrUnicodeOut(Ddirpath),
                                       StrUnicodeOut(Ffname)) + "'"
            elif ConvertOrCopyTags == 'CopyTags':
                command = os.path.join(StrUnicodeOut(xCfg.RAW_TOOL_PATH),
                                       'exiftool') +\
                    " -overwrite_original_in_place -tagsfromfile " +\
                    "'" + os.path.join(StrUnicodeOut(Ddirpath),
                                       StrUnicodeOut(Ffname)) + "'" +\
                    " -r -all:all -ext JPG " +\
                    "'" + os.path.join(StrUnicodeOut(Ddirpath),
                                       StrUnicodeOut(Ffnameonly)) + ".JPG'"
            else:
                # Nothing to do
                return False

            logging.info(command)
            try:
                p = subprocess.call(command, shell=True)
            except BaseException:
                reportError(Caught=True,
                            CaughtPrefix='+++',
                            CaughtCode='999',
                            CaughtMsg='Error calling exiftool (!{s})!'
                                      .format(ConvertOrCopyTags),
                            NicePrint=True,
                            exceptSysInfo=True)
                resultCmd = False
            finally:
                if p is None:
                    del p
                return resultCmd
        # ---------------------------------------------------------------------

        if (ARGS.dry_run is True):
            np.niceprint('Dry Run rawfile:[{!s}]...'
                         .format(StrUnicodeOut(os.path.join(Ddirpath,
                                                            Ffname))))
            return True

        np.niceprint(' Converting raw:[{!s}]'
                     .format(StrUnicodeOut(os.path.join(Ddirpath, Ffname))))
        logging.info(' Converting raw:[{!s}]'
                     .format(StrUnicodeOut(os.path.join(Ddirpath, Ffname))))
        success = False

        # fileExt = FFname's extension (without the ".")
        fileExt = os.path.splitext(Ffname)[-1][1:].lower()
        assert StrUnicodeOut(Fext) == StrUnicodeOut(fileExt),\
            niceassert('File extensions differ:[{!s}]!=[{!s}]'
                       .format(StrUnicodeOut(Fext),
                               StrUnicodeOut(fileExt)))

        if (not os.path.exists(os.path.join(Ddirpath, Ffnameonly) + ".JPG")):
            logging.info('.....Create JPG:[{!s}] jpg:[{!s}] ext:[{!s}]'
                         .format(StrUnicodeOut(Ffname),
                                 StrUnicodeOut(Ffnameonly),
                                 StrUnicodeOut(fileExt)))
            if convertRawFileCommand('Convert'):
                np.niceprint('....Created JPG:[{!s}]'
                             .format(StrUnicodeOut(Ffnameonly) + ".JPG"))
            else:
                np.niceprint('.....raw failed:[{!s}]'.format(Ffname))
                return success
        else:
            np.niceprint('raw: JPG exists:[{!s}]'
                         .format(StrUnicodeOut(Ffnameonly) + ".JPG"))
            logging.warning('raw: JPG exists:[{!s}]'
                            .format(StrUnicodeOut(Ffnameonly) + ".JPG"))
            return success

        if (os.path.exists(StrUnicodeOut(os.path.join(Ddirpath, Ffnameonly)) +
                           ".JPG")):
            np.niceprint('...Copying tags:[{!s}]'
                         .format(StrUnicodeOut(Ffname)))

            if convertRawFileCommand('CopyTags'):
                np.niceprint('....Copied tags:[{!s}]'
                             .format(StrUnicodeOut(Ffname)))
            else:
                np.niceprint('raw tags failed:[{!s}]'.format(Ffname))
                return success
        else:
            np.niceprint('.....raw failed:[{!s}]'.format(Ffname))
            logging.warning('.....raw failed:[{!s}]'.format(Ffname))
            return success

        success = True
        np.niceprint('  Converted raw:[{!s}]'.format(StrUnicodeOut(Ffname)))
        logging.info('  Converted raw:[{!s}]'.format(StrUnicodeOut(Ffname)))

        return success

    # -------------------------------------------------------------------------
    # grabNewFiles
    #
    def grabNewFiles(self):
        """ grabNewFiles

            Select files from FILES_DIR taking into consideration
            EXCLUDED_FOLDERS and IGNORED_REGEX filenames.
            Returns two sorted file lists:
                JPG files found
                RAW files found
        """

        files = []
        rawfiles = []
        for dirpath, dirnames, filenames in\
                os.walk(xCfg.FILES_DIR, followlinks=True):

            # Prevent walking thru files in the list of EXCLUDED_FOLDERS
            # Reduce time by not checking a file in an excluded folder
            logging.debug('Check for UnicodeWarning comparison '
                          'dirpath:[{!s}] type:[{!s}]'
                          .format(StrUnicodeOut(os.path.basename(
                              os.path.normpath(dirpath))),
                              type(os.path.basename(
                                  os.path.normpath(dirpath)))))
            if os.path.basename(os.path.normpath(dirpath)) \
                    in xCfg.EXCLUDED_FOLDERS:
                dirnames[:] = []
                filenames[:] = []
                logging.info('Folder [{!s}] on path [{!s}] excluded.'
                             .format(
                                 StrUnicodeOut(os.path.basename(
                                     os.path.normpath(dirpath))),
                                 StrUnicodeOut(os.path.normpath(dirpath))))

            for f in filenames:
                filePath = os.path.join(StrUnicodeOut(dirpath),
                                        StrUnicodeOut(f))
                # Ignore filenames wihtin IGNORED_REGEX
                if any(ignored.search(f) for ignored in xCfg.IGNORED_REGEX):
                    logging.debug('File {!s} in IGNORED_REGEX:'
                                  .format(filePath.encode('utf-8')))
                    continue
                ext = os.path.splitext(os.path.basename(f))[1][1:].lower()
                if ext in xCfg.ALLOWED_EXT:
                    fileSize = os.path.getsize(os.path.join(
                        StrUnicodeOut(dirpath), StrUnicodeOut(f)))
                    if (fileSize < xCfg.FILE_MAX_SIZE):
                        files.append(
                            os.path.normpath(
                                StrUnicodeOut(dirpath) +
                                StrUnicodeOut("/") +
                                StrUnicodeOut(f).replace("'", "\'")))
                    else:
                        np.niceprint('Skipping file due to '
                                     'size restriction: [{!s}]'.format(
                                         os.path.normpath(
                                             StrUnicodeOut(dirpath) +
                                             StrUnicodeOut('/') +
                                             StrUnicodeOut(f))))
                # Assumes xCFG.ALLOWED_EXT and xCFG.RAW_EXT are disjoint
                elif xCfg.CONVERT_RAW_FILES and (ext in xCfg.RAW_EXT):
                    if not (
                        os.path.exists(
                            os.path.join(
                                StrUnicodeOut(dirpath),
                                StrUnicodeOut(os.path.splitext(f)[0])) +
                            ".JPG")):
                        logging.debug('rawfiles: including:[{!s}]'
                                      .format(StrUnicodeOut(f)))
                        rawfiles.append(
                            os.path.normpath(
                                StrUnicodeOut(dirpath) +
                                StrUnicodeOut("/") +
                                StrUnicodeOut(f).replace("'", "\'")))
                    else:
                        logging.warning('rawfiles: JPG exists. '
                                        'Not including:[{!s}]'
                                        .format(StrUnicodeOut(f)))
                    # CODING----------------------Code moved to ConvertRawFiles
                    # Perform Raw conversion
                    # dirpath   = folder location
                    # f         = filename inclueding extension
                    # extension = lowercase extension (without the dot)
                    # fnameonly = os.path.splitext(f)[0]
                    # if self.convertRawFile(dirpath, f, ext, fnameonly):
                    #     fileSize = os.path.getsize(
                    #         os.path.join(dirpath,
                    #                      fnameonly + '.JPG'))
                    #     logging.debug('Converted .JPG file size=[{!s}]'
                    #                   .format(fileSize))
                    #     if (fileSize < xCfg.FILE_MAX_SIZE):
                    #         files.append(
                    #             os.path.normpath(
                    #                 StrUnicodeOut(dirpath) +
                    #                 StrUnicodeOut("/") +
                    #                 StrUnicodeOut(os.path.splitext(f)[0])
                    #                 .replace("'", "\'") +
                    #                 StrUnicodeOut('.JPG')))
                    #     else:
                    #         np.niceprint('Skipping file due to '
                    #                      'size restriction: [{!s}]'.format(
                    #                          os.path.normpath(
                    #                              StrUnicodeOut(dirpath) +
                    #                              StrUnicodeOut('/') +
                    #                              StrUnicodeOut(f))))
                    # else:
                    #     np.niceprint('Convert raw file failed. '
                    #                  'Skipping file: [{!s}]'.format(
                    #                      os.path.normpath(
                    #                          StrUnicodeOut(dirpath) +
                    #                          StrUnicodeOut('/') +
                    #                          StrUnicodeOut(f))))
        rawfiles.sort()
        files.sort()
        if xCfg.LOGGING_LEVEL <= logging.DEBUG:
            np.niceprint('Pretty Print Output for [files]-------')
            pprint.pprint(files)
            np.niceprint('Pretty Print Output for [rawfiles]----')
            pprint.pprint(rawfiles)
        return files, rawfiles

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
        for excluded_dir in xCfg.EXCLUDED_FOLDERS:
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
        # Flickr doesn't read it from the video file itself.
        filetype = mimetypes.guess_type(xfile)
        logging.info('filetype is:[{!s}]'.format('None'
                                                 if filetype is None
                                                 else filetype[0]))

        # update video date/time TAKEN.
        # Flickr doesn't read it from the video file itself.
        if ((not filetype[0] is None) and ('video' in filetype[0])):
            res_set_date = None
            video_date = nutime.strftime('%Y-%m-%d %H:%M:%S',
                                         nutime.localtime(xlast_modified))
            logging.info('video_date:[{!s}]'.format(video_date))

            try:
                res_set_date = FLICK.photos_set_dates(xfile_id,
                                                      str(video_date))
                logging.debug('Output for {!s}:'.format('res_set_date'))
                logging.debug(xml.etree.ElementTree.tostring(
                    res_set_date,
                    encoding='utf-8',
                    method='xml'))
                if self.isGood(res_set_date):
                    np.niceprint('Successful date:[{!s}] '
                                 'for file:[{!s}]'
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
            # (ARGS.processes and ARGS.processes > 0):
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
    #          if ARGS.processes = 0 then lock can be None as it is not used
    #   file = file to be uploaded
    #
    def uploadFile(self, lock, file):
        """ uploadFile
        uploads file into flickr

        May run in single or multiprocessing mode

        lock = parameter for multiprocessing control of access to DB.
               (if ARGS.processes = 0 then lock may be None as it is not used)
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
            for x in range(0, xCfg.MAX_SQL_ATTEMPTS):
                logging.info('BEGIN SQL:[{!s}]...[{!s}/{!s} attempts].'
                             .format('INSERT INTO files',
                                     x,
                                     xCfg.MAX_SQL_ATTEMPTS))
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
                    con.commit()
                    # Release DBlock if in multiprocessing mode
                    self.useDBLock(lock, False)

                if DBexception:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='031',
                                CaughtMsg='Sleep 2 and retry SQL...'
                                          '[{!s}/{!s} attempts]'
                                          .format(x, xCfg.MAX_SQL_ATTEMPTS),
                                NicePrint=True)
                    nutime.sleep(2)
                else:
                    if (x > 0):
                        reportError(Caught=True,
                                    CaughtPrefix='+++ DB',
                                    CaughtCode='032',
                                    CaughtMsg='Succeed at retry SQL...'
                                    '[{!s}/{!s} attempts]'
                                    .format(x, xCfg.MAX_SQL_ATTEMPTS),
                                    NicePrint=True)
                    logging.info(
                        'END SQL:[{!s}]...[{!s}/{!s} attempts].'
                        .format('INSERT INTO files',
                                x,
                                xCfg.MAX_SQL_ATTEMPTS))
                    # Break the cycle of SQL_ATTEMPTS and continue
                    break
        # ---------------------------------------------------------------------

        if (ARGS.dry_run is True):
            np.niceprint('   Dry Run file:[{!s}]...'
                         .format(StrUnicodeOut(file)))
            return True

        if (ARGS.verbose):
            np.niceprint('  Checking file:[{!s}]...'
                         .format(StrUnicodeOut(file)))

        setName = self.getSetNameFromFile(file,
                                          xCfg.FILES_DIR,
                                          xCfg.FULL_SET_NAME)

        success = False
        con = lite.connect(xCfg.DB_PATH)
        con.text_factory = str
        with con:
            cur = con.cursor()
            logging.debug('uploadFILE SELECT:'
                          '{!s}: {!s}'.format('SELECT rowid,files_id,path,'
                                              'set_id,md5,tagged,'
                                              'last_modified FROM '
                                              'files WHERE path = ?',
                                              file))

            try:
                # Acquire DB lock if running in multiprocessing mode
                self.useDBLock(lock, True)
                cur.execute('SELECT rowid, files_id, path, set_id, md5, '
                            'tagged, last_modified FROM files WHERE path = ?',
                            (file,))
            except lite.Error as e:
                reportError(Caught=True,
                            CaughtPrefix='+++ DB',
                            CaughtCode='035',
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
            if (ARGS.not_is_already_uploaded):
                isLoaded = False
                isfile_id = None
                isNoSet = None
                logging.info('not_is_already_uploaded:[{!s}] '
                             .format(isLoaded))
            else:
                file_checksum = self.md5Checksum(file)
                isLoaded, isCount, isfile_id, isNoSet = \
                    self.is_already_uploaded(file,
                                             file_checksum,
                                             setName)
                logging.info('is_already_uploaded:[{!s}] '
                             'count:[{!s}] pic:[{!s}] '
                             'row is None == [{!s}] '
                             'isNoSet:[{!s}]'
                             .format(isLoaded, isCount,
                                     isfile_id, row is None,
                                     isNoSet))

            # A) File loaded. Not recorded on DB. Update local DB.
            if isLoaded and row is None:
                if file_checksum is None:
                    file_checksum = self.md5Checksum(file)

                # Insert into DB files
                logging.warning(' Already loaded:[{!s}]...'
                                'On Album:[{!s}]... UPDATING LOCAL DATABASE.'
                                .format(StrUnicodeOut(file),
                                        StrUnicodeOut(setName)))
                np.niceprint(' Already loaded:[{!s}]...'
                             'On Album:[{!s}]... UPDATING LOCAL DATABASE.'
                             .format(StrUnicodeOut(file),
                                     StrUnicodeOut(setName)))
                dbInsertIntoFiles(lock, isfile_id, file,
                                  file_checksum, last_modified)

                # Update the Video Date Taken
                self.updatedVideoDate(isfile_id, file, last_modified)

                con.commit()

            # B) Not loaded. Not recorded on DB. Upload file to FLickr.
            elif row is None:
                if (ARGS.verbose):
                    np.niceprint(' Uploading file:[{!s}]...'
                                 'On Album:[{!s}]...'
                                 .format(StrUnicodeOut(file),
                                         StrUnicodeOut(setName)))

                logging.warning(' Uploading file:[{!s}]... '
                                'On Album:[{!s}]...'
                                .format(StrUnicodeOut(file),
                                        StrUnicodeOut(setName)))

                if file_checksum is None:
                    file_checksum = self.md5Checksum(file)

                # Title Handling
                if ARGS.title:
                    xCfg.FLICKR["title"] = ARGS.title
                # Description Handling
                if ARGS.description:
                    xCfg.FLICKR["description"] = ARGS.description
                # Tags Handling
                if ARGS.tags:  # Append a space to later add -t TAGS
                    xCfg.FLICKR["tags"] += " "
                    if ARGS.verbose:
                        np.niceprint('TAGS:[{} {}]'
                                     .format(xCfg.FLICKR["tags"],
                                             ARGS.tags).replace(',', ''))

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
                if xCfg.FLICKR["title"] == "":
                    path_filename, title_filename = os.path.split(file)
                    logging.info('path:[{!s}] '
                                 'filename:[{!s}] '
                                 'ext=[{!s}]'.format(
                                     path_filename,
                                     title_filename,
                                     os.path.splitext(title_filename)[1]))
                    title_filename = os.path.splitext(title_filename)[0]
                    logging.info('title_name:[{!s}]'.format(title_filename))
                else:
                    title_filename = xCfg.FLICKR["title"]
                    logging.info('title from INI file:[{!s}]'
                                 .format(title_filename))

                # CODING: Check MAX_UPLOAD_ATTEMPTS. Replace with @retry?
                uploadResp = None
                photo_id = None
                ZuploadOK = False
                ZbadFile = False
                ZuploadError = False
                for x in range(0, xCfg.MAX_UPLOAD_ATTEMPTS):
                    # Reset variables on each iteration
                    uploadResp = None
                    photo_id = None
                    ZuploadOK = False
                    ZbadFile = False
                    ZuploadError = False
                    logging.warning('Up/Reuploading:[{!s}/{!s} attempts].'
                                    .format(x, xCfg.MAX_UPLOAD_ATTEMPTS))
                    if (x > 0):
                        np.niceprint('    Reuploading:[{!s}] '
                                     '[{!s}/{!s} attempts].'
                                     .format(StrUnicodeOut(file),
                                             x,
                                             xCfg.MAX_UPLOAD_ATTEMPTS))
                    # Upload file to Flickr
                    # replace commas from tags and checksum tags
                    # to avoid tags conflicts
                    try:
                        uploadResp = nuflickr.upload(
                            filename=file,
                            fileobj=FileWithCallback(file, callback),
                            title=title_filename
                            if xCfg.FLICKR["title"] == ""
                            else str(xCfg.FLICKR["title"]),
                            description=str(xCfg.FLICKR["description"]),
                            tags='{} checksum:{} album:"{}" {}'
                            .format(
                                xCfg.FLICKR["tags"],
                                file_checksum,
                                StrUnicodeOut(setName),
                                ARGS.tags if ARGS.tags else '')
                            .replace(',', ''),
                            is_public=str(xCfg.FLICKR["is_public"]),
                            is_family=str(xCfg.FLICKR["is_family"]),
                            is_friend=str(xCfg.FLICKR["is_friend"])
                        )

                        logging.info('uploadResp:[{!s}]'
                                     .format(self.isGood(uploadResp)))
                        logging.debug(xml.etree.ElementTree.tostring(
                            uploadResp,
                            encoding='utf-8',
                            method='xml'))

                        if self.isGood(uploadResp):
                            ZuploadOK = True
                            # Save photo_id returned from Flickr upload
                            photo_id = uploadResp.findall('photoid')[0].text
                            logging.info('  Uploaded file:[{!s}] '
                                         'Id=[{!s}]. Check for '
                                         'duplicates/wrong checksum...'
                                         .format(StrUnicodeOut(file),
                                                 photo_id))
                            if (ARGS.verbose):
                                np.niceprint('  Uploaded file:[{!s}] '
                                             'ID=[{!s}]. Check for '
                                             'duplicates/wrong checksum...'
                                             .format(StrUnicodeOut(file),
                                                     photo_id))

                            break
                        else:
                            ZuploadError = True
                            raise IOError(uploadResp)

                    except (IOError, httplib.HTTPException):
                        reportError(Caught=True,
                                    CaughtPrefix='+++',
                                    CaughtCode='038',
                                    CaughtMsg='Caught IOError, '
                                    'HTTP exception',
                                    NicePrint=True,
                                    exceptSysInfo=True)
                        # CODING: Repeat also below on FlickError (!= 5 and 8)
                        # On error, check if exists a photo with
                        # file_checksum
                        logging.error('Sleep 10 and check if file is '
                                      'already uploaded')
                        np.niceprint('Sleep 10 and check if file is '
                                     'already uploaded')
                        nutime.sleep(10)

                        ZisLoaded, ZisCount, photo_id, ZisNoSet = \
                            self.is_already_uploaded(
                                file,
                                file_checksum,
                                setName)
                        logging.warning('is_already_uploaded:[{!s}] '
                                        'Zcount:[{!s}] Zpic:[{!s}] '
                                        'ZisNoSet:[{!s}]'
                                        .format(ZisLoaded, ZisCount,
                                                photo_id, ZisNoSet))

                        if ZisCount == 0:
                            ZuploadError = True
                            continue
                        elif ZisCount == 1:
                            ZuploadOK = True
                            ZuploadError = False
                            np.niceprint('Found, '
                                         'continuing with next image.')
                            logging.warning('Found, '
                                            'continuing with next image.')
                            break
                        elif ZisCount > 1:
                            ZuploadError = True
                            np.niceprint('More than one file with same '
                                         'checksum/album tag! '
                                         'Any collisions? File: [{!s}]'
                                         .format(StrUnicodeOut(file)))
                            logging.error('More than one file with same '
                                          'checksum/album tag! '
                                          'Any collisions? File: [{!s}]'
                                          .format(StrUnicodeOut(file)))
                            break

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
                        if ((format(ex.code) == '5') or (
                                format(ex.code) == '8')):
                            # Badfile
                            ZbadFile = True
                            if not ARGS.bad_files:
                                # Break for ATTEMPTS cycle
                                break

                            # ARGS.bad_files is True
                            # Add to db the file NOT uploaded
                            # Set locking for when running multiprocessing
                            np.niceprint('   Log Bad file:[{!s}] due to [{!s}]'
                                         .format(file,
                                                 'Filetype was not recognised'
                                                 if (format(ex.code) == '5')
                                                 else 'Filesize was too large')
                                         )
                            logging.info('Bad file:[{!s}]'.format(file))

                            try:
                                self.useDBLock(lock, True)
                                # files_id is autoincrement. No need to mention
                                cur.execute(
                                    'INSERT INTO badfiles '
                                    '( path, md5, last_modified, tagged) '
                                    'VALUES (?, ?, ?, 1)',
                                    (file, file_checksum, last_modified))
                            except lite.Error as e:
                                reportError(Caught=True,
                                            CaughtPrefix='+++ DB',
                                            CaughtCode='041',
                                            CaughtMsg='DB error on INSERT: '
                                                      '[{!s}]'
                                                      .format(e.args[0]),
                                            NicePrint=True)
                            finally:
                                # Control for when running multiprocessing
                                # release locking
                                self.useDBLock(lock, False)

                            # Break for ATTEMPTS cycle
                            break
                        else:
                            # CODING: Repeat above on IOError
                            # On error, check if exists a photo with
                            # file_checksum
                            logging.error('Sleep 10 and check if file is '
                                          'already uploaded')
                            np.niceprint('Sleep 10 and check if file is '
                                         'already uploaded')
                            nutime.sleep(10)

                            ZisLoaded, ZisCount, photo_id, ZisNoSet = \
                                self.is_already_uploaded(
                                    file,
                                    file_checksum,
                                    setName)
                            logging.warning('is_already_uploaded:[{!s}] '
                                            'Zcount:[{!s}] Zpic:[{!s}] '
                                            'ZisNoSet:[{!s}]'
                                            .format(ZisLoaded, ZisCount,
                                                    photo_id, ZisNoSet))

                            if ZisCount == 0:
                                ZuploadError = True
                                continue
                            elif ZisCount == 1:
                                ZuploadOK = True
                                ZuploadError = False
                                np.niceprint('Found, '
                                             'continuing with next image.')
                                logging.warning('Found, '
                                                'continuing with next image.')
                                break
                            elif ZisCount > 1:
                                ZuploadError = True
                                np.niceprint('More than one file with same '
                                             'checksum/album tag! '
                                             'Any collisions? File: [{!s}]'
                                             .format(StrUnicodeOut(file)))
                                logging.error('More than one file with same '
                                              'checksum/album tag! '
                                              'Any collisions? File: [{!s}]'
                                              .format(StrUnicodeOut(file)))
                                break

                    finally:
                        con.commit()

                logging.debug('After CYCLE '
                              'Up/Reuploading:[{!s}/{!s} attempts].'
                              .format(x, xCfg.MAX_UPLOAD_ATTEMPTS))

                # Max attempts reached
                if (not ZuploadOK) and (x == (xCfg.MAX_UPLOAD_ATTEMPTS - 1)):
                    np.niceprint('Reached max attempts to upload. Skipping '
                                 'file: [{!s}]'.format(StrUnicodeOut(file)))
                    logging.error('Reached max attempts to upload. Skipping '
                                  'file: [{!s}]'.format(StrUnicodeOut(file)))
                # Error
                elif (not ZuploadOK) and ZuploadError:
                    np.niceprint('Error occurred while uploading. Skipping '
                                 'file:[{!s}]'
                                 .format(StrUnicodeOut(file)))
                    logging.error('Error occurred while uploading. Skipping '
                                  'file:[{!s}]'
                                  .format(StrUnicodeOut(file)))
                # Bad file
                elif (not ZuploadOK) and ZbadFile:
                    np.niceprint('       Bad file:[{!s}]'
                                 .format(StrUnicodeOut(file)))
                # Successful update
                elif ZuploadOK:
                    np.niceprint('Successful file:[{!s}]'
                                 .format(StrUnicodeOut(file)))

                    assert photo_id is not None, niceassert(
                        'photo_id None:[{!s}]'
                        .format(StrUnicodeOut(file)))
                    # Save file_id: from uploadResp or is_already_uploaded
                    file_id = photo_id

                    # Insert into DB files
                    dbInsertIntoFiles(lock, file_id, file,
                                      file_checksum, last_modified)

                    # Update the Video Date Taken
                    self.updatedVideoDate(file_id, file, last_modified)

                    success = True

            # C) File loaded. Recorded on DB. Look for changes...
            elif (xCfg.MANAGE_CHANGES):
                # We have a file from disk which is found on the database
                # and is also on flickr but its set on flickr is not defined.
                # So we need to reset the local datbase set_id so that it will
                # be later assigned once we run createSets()
                logging.debug('str(row[1]) == str(isfile_id:[{!s}])'
                              'row[1]:[{!s}]=>type:[{!s}] '
                              'isfile_id:[{!s}]=>type:[{!s}]'
                              .format(str(row[1]) == str(isfile_id),
                                      row[1], type(row[1]),
                                      isfile_id, type(isfile_id)))
                # C) File loaded. Recorded on DB. Manage changes & Flickr set.
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
                                    CaughtMsg='DB error on UPDATE: [{!s}]'
                                              .format(e.args[0]),
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
                    if (ARGS.processes and ARGS.processes > 0):
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
    #                     if ARGS.processes = 0 then lock can be None/not used
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
                          if ARGS.processes = 0 then lock can be None/not used
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

        if (ARGS.dry_run is True):
            np.niceprint('Dry Run Replace:[{!s}]...'
                         .format(StrUnicodeOut(file)))
            return True

        if (ARGS.verbose):
            np.niceprint(' Replacing file:[{!s}]...'
                         .format(StrUnicodeOut(file)))

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

            for x in range(0, xCfg.MAX_UPLOAD_ATTEMPTS):
                res_add_tag = None
                res_get_info = None
                replaceResp = None

                try:
                    if (x > 0):
                        np.niceprint('   Re-Replacing:'
                                     '[{!s}]...[{!s}/{!s} attempts].'
                                     .format(StrUnicodeOut(file),
                                             x,
                                             xCfg.MAX_UPLOAD_ATTEMPTS))

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
                        res_add_tag = FLICK.photos_add_tags(
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
                            res_get_info = FLICK.photos_get_info(
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
                                        logging.info('   Found tag_id:[{!s}]'
                                                     .format(tag_id))
                                        break
                                if not tag_id:
                                    np.niceprint(' Can\'t find tag:[{!s}]'
                                                 'for file [{!s}]'
                                                 .format(tag_id, file_id))
                                    # break from attempting to update tag_id
                                    break
                                else:
                                    # update tag_id with new Md5
                                    logging.info('Removing tag_id:[{!s}]'
                                                 .format(tag_id))
                                    remtagResp = self.photos_remove_tag(tag_id)
                                    logging.debug('remtagResp: ')
                                    logging.debug(xml.etree.ElementTree
                                                  .tostring(remtagResp,
                                                            encoding='utf-8',
                                                            method='xml'))
                                    if (self.isGood(remtagResp)):
                                        np.niceprint('    Tag removed.')
                                    else:
                                        np.niceprint('Tag Not removed.')

                    break
                # Exceptions for flickr.upload function call handled on the
                # outer try/except.
                except (IOError, ValueError, httplib.HTTPException):
                    reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='060',
                                CaughtMsg='Caught IOError, ValueError, '
                                          'HTTP exception',
                                NicePrint=True,
                                exceptSysInfo=True)
                    logging.error('Sleep 10 and try to replace again.')
                    np.niceprint('Sleep 10 and try to replace again.')
                    nutime.sleep(10)

                    if x == xCfg.MAX_UPLOAD_ATTEMPTS - 1:
                        raise ValueError('Reached maximum number of attempts '
                                         'to replace, skipping')
                    continue

            if (not self.isGood(replaceResp)) or \
                (not self.isGood(res_add_tag)) or \
                    (not self.isGood(res_get_info)):
                np.niceprint('Issue replacing:[{!s}]'
                             .format(StrUnicodeOut(file)))

            if (not self.isGood(replaceResp)):
                raise IOError(replaceResp)

            if (not(self.isGood(res_add_tag))):
                raise IOError(res_add_tag)

            if (not self.isGood(res_get_info)):
                raise IOError(res_get_info)

            np.niceprint('  Replaced file:[{!s}].'
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
            # Error: 8: Videos can't be replaced
            if (ex.code == 8):
                np.niceprint('..Video replace:[{!s}]'
                             .format(StrUnicodeOut(file)),
                             fname='replace')
                logging.error('Videos can\'t be replaced, delete/uploading...')
                xrow = [file_id, file]
                logging.debug('delete/uploading '
                              'xrow[0].files_id=[{!s}]'
                              'xrow[1].file=[{!s}]'
                              .format(xrow[0], xrow[1]))
                if (self.deleteFile(xrow, cur, lock)):
                    np.niceprint('..Video deleted:[{!s}]'
                                 .format(StrUnicodeOut(file)),
                                 fname='replace')
                    logging.warning('Delete for replace succeed!')
                    if self.uploadFile(lock, file):
                        np.niceprint('.Video replaced:[{!s}]'
                                     .format(StrUnicodeOut(file)),
                                     fname='replace')
                        logging.warning('Upload for replace succeed!')
                    else:
                        np.niceprint('..Failed upload:[{!s}]'
                                     .format(StrUnicodeOut(file)),
                                     fname='replace')
                        logging.error('Upload for replace failed!')
                else:
                    np.niceprint('..Failed delete:[{!s}]'
                                 .format(StrUnicodeOut(file)),
                                 fname='replace')
                    logging.error('Delete for replace failed!')

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
        except BaseException:
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
    # Delete files from flickr
    #
    # When EXCLUDED_FOLDERS defintion changes. You can run the -g
    # or --remove-excluded option in order to remove files previously loaded
    #
    def deleteFile(self, file, cur, lock=None):
        """ deleteFile

        delete file from flickr

        file  = row of database with (files_id, path)
        cur   = represents the control database cursor to allow, for example,
                deleting empty sets
        lock  = for use with useDBLock to control access to DB
        """

        global nuflickr

        # ---------------------------------------------------------------------
        # dbDeleteRecordLocalDB
        #
        def dbDeleteRecordLocalDB(lock, file):
            """ dbDeleteRecordLocalDB

            Find out if the file is the last item in a set, if so,
            remove the set from the local db

            lock  = for use with useDBLock to control access to DB
            file  = row of database with (files_id, path)

            Use new connection and nucur cursor to ensure commit

            """
            con = lite.connect(xCfg.DB_PATH)
            con.text_factory = str
            with con:
                try:
                    nucur = con.cursor()
                    # Acquire DBlock if in multiprocessing mode
                    self.useDBLock(lock, True)
                    nucur.execute("SELECT set_id FROM files "
                                  "WHERE files_id = ?",
                                  (file[0],))
                    row = nucur.fetchone()
                    if (row is not None):
                        nucur.execute("SELECT set_id FROM files "
                                      "WHERE set_id = ?",
                                      (row[0],))
                        rows = nucur.fetchall()
                        if (len(rows) == 1):
                            np.niceprint('File is the last of the set, '
                                         'deleting the set ID: [{!s}]'
                                         .format(str(row[0])))
                            nucur.execute("DELETE FROM sets WHERE set_id = ?",
                                          (row[0],))
                    # Delete file record from the local db
                    logging.debug('deleteFile.dbDeleteRecordLocalDB: '
                                  'DELETE FROM files WHERE files_id = {!s}'
                                  .format(file[0]))
                    nucur.execute("DELETE FROM files WHERE files_id = ?",
                                  (file[0],))
                except lite.Error as e:
                    reportError(Caught=True,
                                CaughtPrefix='+++ DB',
                                CaughtCode='087',
                                CaughtMsg='DB error on SELECT(or)DELETE: '
                                          '[{!s}]'
                                          .format(e.args[0]),
                                NicePrint=True,
                                exceptSysInfo=True)
                except BaseException:
                    reportError(Caught=True,
                                CaughtPrefix='+++',
                                CaughtCode='088',
                                CaughtMsg='Caught exception in '
                                          'dbDeleteRecordLocalDB',
                                NicePrint=True,
                                exceptSysInfo=True)
                    raise
                finally:
                    con.commit()
                    logging.debug('deleteFile.dbDeleteRecordLocalDB: '
                                  'After COMMIT')
                    # Release DBlock if in multiprocessing mode
                    self.useDBLock(lock, False)

            # Closing DB connection
            if con is not None:
                con.close()
        # ---------------------------------------------------------------------

        if (ARGS.dry_run is True):
            np.niceprint('Dry Run Deleting file:[{!s}]'
                         .format(StrUnicodeOut(file[1])))
            return True

        @retry(attempts=2, waittime=2, randtime=False)
        def R_photos_delete(kwargs):
            return nuflickr.photos.delete(**kwargs)

        np.niceprint('  Deleting file:[{!s}]'.format(StrUnicodeOut(file[1])))

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

                dbDeleteRecordLocalDB(lock, file)

                np.niceprint('   Deleted file:[{!s}]'
                             .format(StrUnicodeOut(file[1])))
                success = True
            else:
                reportError(Caught=True,
                            CaughtPrefix='xxx',
                            CaughtCode='089',
                            CaughtMsg='Failed delete photo (deleteFile)',
                            NicePrint=True)
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
                dbDeleteRecordLocalDB(lock, file)
            else:
                reportError(Caught=True,
                            CaughtPrefix='xxx',
                            CaughtCode='092',
                            CaughtMsg='Failed to delete photo (deleteFile)',
                            NicePrint=True)
        except BaseException:
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

        logging.warning('  Add set to DB:[{!s}]'
                        .format(StrUnicodeOut(setName)))
        if (ARGS.verbose):
            np.niceprint('  Add set to DB:[{!s}]'
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
                        CaughtMsg='DB error on UPDATE: [{!s}]'.format(
                            e.args[0]),
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
            np.niceprint('Running in Daemon mode. Execute at [{!s}].'
                         .format(nutime.strftime(UPLDRConstants.TimeFormat)))
            # run upload
            self.upload()
            np.niceprint('Last check: [{!s}]'
                         .format(str(nutime.asctime(time.localtime()))))
            logging.warning('Running in Daemon mode. Sleep [{!s}] seconds.'
                            .format(xCfg.SLEEP_TIME))
            nutime.sleep(xCfg.SLEEP_TIME)

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
    # OldcreateSets
    #
    # def OldcreateSets(self):
    #     """
    #         Creates a set (Album) in Flickr
    #     """
    #     np.niceprint('*****Creating Sets*****')
    # 
    #     if ARGS.dry_run:
    #         return True
    # 
    #     con = lite.connect(xCfg.DB_PATH)
    #     con.text_factory = str
    #     with con:
    #         cur = con.cursor()
    #         cur.execute("SELECT files_id, path, set_id FROM files")
    # 
    #         files = cur.fetchall()
    # 
    #         for row in files:
    #             # row[1] = path for the file from table files
    #             setName = self.getSetNameFromFile(row[1],
    #                                               xCfg.FILES_DIR,
    #                                               xCfg.FULL_SET_NAME)
    #             newSetCreated = False
    # 
    #             # Search local DB for set_id by setName(folder name )
    #             cur.execute("SELECT set_id, name FROM sets WHERE name = ?",
    #                         (setName,))
    #             set = cur.fetchone()
    # 
    #             if set is None:
    #                 # row[0] = files_id from files table
    #                 setId = self.createSet(setName, row[0], cur, con)
    #                 np.niceprint('Created the set:[{!s}]'.
    #                              format(StrUnicodeOut(setName)))
    #                 newSetCreated = True
    #             else:
    #                 # set[0] = set_id from sets table
    #                 setId = set[0]
    # 
    #             logging.debug('Creating Sets newSetCreated:[{!s}]'
    #                           'setId=[{!s}]'.format(newSetCreated, setId))
    # 
    #             # row[1] = path for the file from table files
    #             # row[2] = set_id from files table
    #             if row[2] is None and newSetCreated is False:
    #                 np.niceprint('Add file to set:[{!s}] set:[{!s}]'
    #                              .format(StrUnicodeOut(row[1]),
    #                                      StrUnicodeOut(setName)))
    # 
    #                 self.addFileToSet(setId, row, cur)
    # 
    #     # Closing DB connection
    #     if con is not None:
    #         con.close()
    #     np.niceprint('*****Completed creating sets*****')

   # -------------------------------------------------------------------------
    # createSets
    #
    def createSets(self):
        """
            Creates a set (Album) in Flickr
        """
        # [FIND SETS] Find sets to be created
        # [PRIMARY PIC] For each set found, determine the primary picture
        # [CREATE SET] Create Sets wiht primary picture: CODING: what if it is not found?
        # [WORK THRU PICS] After, then split work and add files to set in multi-processing
        #   CODING use xLocks 
        np.niceprint('*****Creating Sets*****')

        if ARGS.dry_run:
            return True

        con = lite.connect(xCfg.DB_PATH)
        con.text_factory = str
        con.create_function("getSet", 3, getSetNameFromFile)
        
        with con:
            cur = con.cursor()
            # List of Sets to be created
            cur.execute('SELECT DISTINCT getSet(path, ?, ?) '
                        'FROM files WHERE getSet(path, ?, ?) '
                        'NOT IN (SELECT name FROM sets)',
                        (xCfg.FILES_DIR, xCfg.FULL_SET_NAME,
                         xCfg.FILES_DIR, xCfg.FULL_SET_NAME,))
            
            setsToCreate = cur.fetchall()
            
            for set in SetsToCreate:
                # set[0] = setName
                # Find Primary photo
                setName = StrUnicodeOut(set[0])
                cur.execute('SELECT MIN(files_id), path '
                            'FROM files '
                            'WHERE set_id is NULL '
                            'AND getSet(path, ?, ?) = ?',
                            (xCfg.FILES_DIR,
                             xCfg.FULL_SET_NAME,
                             setName,))
                primaryPic = cur.fetchone()
                np.niceprint('   Creating set:[{!s}]'
                             .format(StrUnicodeOut(setName)))

                # primaryPic[0] = files_id from files table
                setId = self.createSet(setName, primaryPic[0], cur, con)
                np.niceprint('Created the set:[{!s}]'.
                             format(StrUnicodeOut(setName)))

                logging.debug('Creating Set newSetCreated:[{!s}]'
                              'setId=[{!s}]'
                              .format(newSetCreated, setId))
            
            cur.execute('SELECT files_id, path, set_id '
                        'FROM files'
                        'WHERE set_id is NULL' )
            files = cur.fetchall()
            
            for filepic in files:
                # filepic[1] = path for the file from table files
                # filepic[2] = set_id from files table
                setName = self.getSetNameFromFile(filepic[1],
                                                  xCfg.FILES_DIR,
                                                  xCfg.FULL_SET_NAME)
                
                cur.execute('SELECT set_id, name '
                            'FROM sets WHERE name = ?',
                            (setName,))
                set = cur.fetchone()
                if set is not None:
                    setId = set[0]
                
                    np.niceprint('Add file to set:[{!s}] '
                                 'set:[{!s}] setId=[{!s}]'
                                 .format(StrUnicodeOut(filepic[1]),
                                         StrUnicodeOut(setName),
                                         setId))
                    self.addFileToSet(setId, filepic, cur)
                else:
                    np.niceprint('Not able to assign pic to set')
                    logging.error('Not able to assign pic to set')

        # Closing DB connection
        if con is not None:
            con.close()
        np.niceprint('*****Completed creating sets*****')

    # -------------------------------------------------------------------------
    # addFiletoSet
    #
    def addFileToSet(self, setId, file, cur):
        """ addFileToSet

            adds a file to set...
            setID = set
            file  = file is a list with file[0]=id, file[1]=path
            cur   = cursor for updating local DB
        """

        global nuflickr

        if ARGS.dry_run:
            return True

        @retry(attempts=2, waittime=0, randtime=False)
        def R_photosets_addPhoto(kwargs):
            return nuflickr.photosets.addPhoto(**kwargs)

        try:
            con = lite.connect(xCfg.DB_PATH)
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
                np.niceprint(' Added file/set:[{!s}] setId:[{!s}]'
                             .format(StrUnicodeOut(file[1]),
                                     StrUnicodeOut(setId)))
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
                np.niceprint('Photoset not found, creating new set...')
                setName = self.getSetNameFromFile(file[1],
                                                  xCfg.FILES_DIR,
                                                  xCfg.FULL_SET_NAME)
                self.createSet(setName, file[0], cur, con)
            # Error: 3: Photo Already in set
            elif (ex.code == 3):
                try:
                    np.niceprint('Photo already in set... updating DB'
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
        except BaseException:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='121',
                        CaughtMsg='Caught exception in addFiletoSet',
                        NicePrint=True,
                        exceptSysInfo=True)
        # Closing DB connection
        if con is not None:
            con.close()

    # -------------------------------------------------------------------------
    # createSet
    #
    def createSet(self, setName, primaryPhotoId, cur, con):
        """ createSet

        Creates an Album in Flickr.
        Calls logSetCreation to create Album on local database.
        """

        global nuflickr

        logging.info('   Creating set:[{!s}]'
                     .format(StrUnicodeOut(setName)))
        np.niceprint('   Creating set:[{!s}]'
                     .format(StrUnicodeOut(setName)))

        if ARGS.dry_run:
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
                np.niceprint('Primary photo [{!s}] for Set [{!s}] '
                             'does not exist on Flickr. '
                             'Probably deleted from Flickr but still '
                             'on local db and local file.'
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

        except BaseException:
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

        np.niceprint('Setting up database:[{!s}]'.format(xCfg.DB_PATH))
        con = None
        try:
            con = lite.connect(xCfg.DB_PATH)
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
                np.niceprint('Adding last_modified column to database')
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
                np.niceprint('Adding table badfiles to database')
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
                np.niceprint('Database version: [{!s}]'.format(row[0]))
                # Database version 3 <=========================DB VERSION: 3===
                np.niceprint('Adding album tags to pics already uploaded... ')
                if FLICK.addAlbumsMigrate():
                    np.niceprint('Successfully added album tags to pics '
                                 'already upload. Updating Database version.',
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
                    np.niceprint('Failed adding album tags to pics '
                                 'on upload. Not updating Database version.'
                                 'Please check logs, correct, and retry.',
                                 fname='addAlbumsMigrate')

            if (row[0] == 3):
                np.niceprint('Database version: [{!s}]'.format(row[0]))
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
            sys.exit(6)
        finally:
            # Closing DB connection
            if con is not None:
                con.close()
            np.niceprint('Completed database setup')

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
        np.niceprint('Cleaning up badfiles table from the database: [{!s}]'
                     .format(xCfg.DB_PATH))
        con = None
        try:
            con = lite.connect(xCfg.DB_PATH)
            con.text_factory = str
            cur = con.cursor()
            cur.execute('PRAGMA user_version')
            row = cur.fetchone()
            if (row[0] >= 2):
                # delete from badfiles table and reset SEQUENCE
                np.niceprint('Deleting from badfiles table. '
                             'Reseting sequence.')
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
                np.niceprint('Wrong DB version. Expected 2 or higher '
                             'and not:[{!s}]'.format(row[0]))
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
            sys.exit(7)
        finally:
            np.niceprint('Completed cleaning up badfiles table '
                         'from the database.')

        # Closing DB connection
        if con is not None:
            con.close()

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
        np.niceprint('*****Removing empty Sets from DB*****')
        if ARGS.dry_run:
            return True

        con = lite.connect(xCfg.DB_PATH)
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
                if ARGS.verbose:
                    np.niceprint('Removing set [{!s}] ({!s}).'
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
        np.niceprint('*****Completed removing empty Sets from DB*****')

    # -------------------------------------------------------------------------
    # Display Sets
    #
    # CODING: Not being used!
    def displaySets(self):
        """ displaySets

        Prints the list of sets/albums recorded on the local database
        """
        con = lite.connect(xCfg.DB_PATH)
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
                np.niceprint('Set: [{!s}] ({!s})'.format(str(row[0]), row[1]))

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

        np.niceprint('*****Adding Flickr Sets to DB*****')
        if ARGS.dry_run:
            return True

        con = lite.connect(xCfg.DB_PATH)
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

                    if (ARGS.verbose):
                        np.niceprint('  Add Set to DB:[{!s}] '
                                     'setId=[{!s}] '
                                     'primaryId=[{!s}]'
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
                        logging.info('Set found on DB:[{!s}]'
                                     .format(StrUnicodeOut(setName)))
                        if (ARGS.verbose):
                            np.niceprint('Set found on DB:[{!s}]'
                                         .format(StrUnicodeOut(setName)))

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
        np.niceprint('*****Completed adding Flickr Sets to DB*****')

    # -------------------------------------------------------------------------
    # is_already_uploaded
    #
    # Checks if image is already loaded with tag:checksum
    # (calls Flickr photos.search)
    #
    # Possible outcomes:
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
    # Note: There could be more entries due to errors. To be checked manually.
    #
    def is_already_uploaded(self, xfile, xchecksum, xsetName):
        """ is_already_uploaded

            Searchs for image with same:
                title(file without extension)
                tag:checksum
                SetName
                    if setName is not defined on a pic, it attempts to
                    check tag:album

            returnIsPhotoUploaded = True (already loaded)/False(not loaded)
            returnPhotoUploaded   = Number of found Images
            returnPhotoID         = Pic ID on Flickr
            returnUploadedNoSet   = True , B, C, D, E or F
            Case | returnIsPhotoUploaded | returnUploadedNoSet | returnPhotoID
            A    | False                 | False               | None
            B    | True                  | True                | pic.['id']
            C    | True                  | False               | pic.['id']
            D    | False                 | False               | None
        """

        global nuflickr

        returnIsPhotoUploaded = False
        returnPhotoUploaded = 0
        returnPhotoID = None
        returnUploadedNoSet = False

        logging.info('Is Already Uploaded:[checksum:{!s}] [album:{!s}]?'
                     .format(xchecksum, xsetName))

        # Use a big random waitime to avoid errors in multiprocessing mode.
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
                        exceptMsg=ex,
                        NicePrint=True,
                        exceptSysInfo=True)
        except (IOError, httplib.HTTPException):
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='181',
                        CaughtMsg='Caught IO/HTTP Error in photos.search')
        except BaseException:
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
                if (ARGS.verbose):
                    np.niceprint(' IS_UPLOADED:[ERROR#1]',
                                 fname='isuploaded')
                logging.warning(' IS_UPLOADED:[ERROR#1]')
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
            freturnPhotoUploaded = 0
            for pic in searchIsUploaded.find('photos').findall('photo'):
                freturnPhotoUploaded += 1
                logging.debug('idx=[{!s}] pic.id=[{!s}] '
                              'pic.title=[{!s}] pic.tags=[{!s}]'
                              .format(freturnPhotoUploaded,
                                      pic.attrib['id'],
                                      StrUnicodeOut(pic.attrib['title']),
                                      StrUnicodeOut(pic.attrib['tags'])))

                # Use StrUnicodeOut in comparison to avoid warning:
                #   "UnicodeWarning: Unicode equal comparison failed to
                #    convert both arguments to Unicode"
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
                except BaseException:
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
                        # raise Exception('photos_getAllContexts: '
                        #                 'Max attempts exhausted.')
                        if (ARGS.verbose):
                            np.niceprint(' IS_UPLOADED:[ERROR#2]',
                                         fname='isuploaded')
                        logging.warning(' IS_UPLOADED:[ERROR#2]')
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

                # B) checksum, title, empty setName,       Count=1
                #                 THEN EXISTS, ASSIGN SET IF tag album IS FOUND
                if (len(resp.findall('set')) == 0):
                    # CODING: Consider one additional result for PHOTO UPLOADED
                    # WITHOUT SET WITH ALBUM TAG when row exists on DB. Mark
                    # such row on the database files.set_id to null
                    # to force re-assigning to Album/Set on flickr.
                    tfind, tid = self.photos_find_tag(
                        photo_id=pic.attrib['id'],
                        intag='album:{}'
                        .format(xsetName))
                    if tfind:
                        if (ARGS.verbose):
                            np.niceprint(' IS_UPLOADED:[UPLOADED WITHOUT'
                                         ' SET WITH ALBUM TAG]',
                                         fname='isuploaded')
                        logging.warning(' IS_UPLOADED:[UPLOADED WITHOUT'
                                        ' SET WITH ALBUM TAG]')
                        returnIsPhotoUploaded = True
                        returnPhotoID = pic.attrib['id']
                        returnUploadedNoSet = True
                        return returnIsPhotoUploaded, \
                            returnPhotoUploaded, \
                            returnPhotoID, \
                            returnUploadedNoSet
                    else:
                        if ARGS.verbose_progress:
                            np.niceprint('IS_UPLOADED:[UPLOADED WITHOUT'
                                         ' SET WITHOUT ALBUM TAG]',
                                         fname='isuploaded')
                        logging.warning('IS_UPLOADED:[UPLOADED WITHOUT'
                                        ' SET WITHOUT ALBUM TAG]')

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

                    # C) checksum, title, setName (1 or more), Count>=1
                    #                                               THEN EXISTS
                    if (StrUnicodeOut(xsetName) ==
                            StrUnicodeOut(setinlist.attrib['title'])):
                        if (ARGS.verbose):
                            np.niceprint(' IS_UPLOADED:[TRUE WITH SET]',
                                         fname='isuploaded')
                        logging.warning(
                            ' IS_UPLOADED:[TRUE WITH SET]')
                        returnIsPhotoUploaded = True
                        returnPhotoID = pic.attrib['id']
                        returnUploadedNoSet = False
                        return returnIsPhotoUploaded, \
                            returnPhotoUploaded, \
                            returnPhotoID, \
                            returnUploadedNoSet
                    else:
                        # D) checksum, title, other setName,       Count>=1
                        #                                       THEN NOT EXISTS
                        if ARGS.verbose_progress:
                            np.niceprint(' IS_UPLOADED:[FALSE OTHER SET, '
                                         'CONTINUING SEARCH IN SETS]',
                                         fname='isuploaded')
                        logging.warning(' IS_UPLOADED:[FALSE OTHER SET, '
                                        'CONTINUING SEARCH IN SETS]')
                        continue

        return returnIsPhotoUploaded, returnPhotoUploaded, \
            returnPhotoID, returnUploadedNoSet
# <?xml version="1.0" encoding="utf-8" ?>
# <rsp stat="ok">
#   <photos page="1" pages="1" perpage="100" total="2">
#     <photo id="37564183184" owner="XXXX" secret="XXX"
# server="4540" farm="5" title="DSC01397" ispublic="0" isfriend="0"
# isfamily="0" tags="autoupload checksum1133825cea9d605f332d04b40a44a6d6" />
#     <photo id="38210659646" owner="XXXX" secret="XXX"
# server="4536" farm="5" title="DSC01397" ispublic="0" isfriend="0"
# isfamily="0" tags="autoupload checksum1133825cea9d605f332d04b40a44a6d6" />
#   </photos>
# </rsp>
# CAREFULL... flickrapi on occasion indicates total=2 but list only brings 1
#
# <?xml version="1.0" encoding="utf-8" ?>
# <rsp stat="ok">
#   <photos page="1" pages="1" perpage="100" total="2">
#     <photo id="26486922439" owner="XXXX" secret="XXX"
# server="4532" farm="5" title="017_17a-5" ispublic="0" isfriend="0"
# isfamily="0" tags="autoupload checksum0449d770558cfac7a6786e468f917b9c" />
#   </photos>
# </rsp>

    # -------------------------------------------------------------------------
    # photos_search
    #
    # Searchs for image with tag:checksum (calls Flickr photos.search)
    #
    # Sample response:
    # <photos page="2" pages="89" perpage="10" total="881">
    #     <photo id="2636" owner="XXXX"
    #             secret="XXX" server="2" title="test_04"
    #             ispublic="1" isfriend="0" isfamily="0" />
    #     <photo id="2635" owner="XXXX"
    #         secret="XXX" server="2" title="test_03"
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

        @retry(attempts=3, waittime=3, randtime=False)
        def R_people_getPhotos(kwargs):
            return nuflickr.people.getPhotos(**kwargs)

        getPhotosResp = None
        try:
            getPhotosResp = R_people_getPhotos(dict(user_id="me",
                                                    per_page=1))

        except flickrapi.exceptions.FlickrError as ex:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='200',
                        CaughtMsg='Error in people.getPhotos',
                        exceptUse=True,
                        exceptCode=ex.code,
                        exceptMsg=ex,
                        NicePrint=True,
                        exceptSysInfo=True)
        except (IOError, httplib.HTTPException):
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='201',
                        CaughtMsg='Caught IO/HTTP Error in people.getPhotos')
        except BaseException:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='202',
                        CaughtMsg='Caught exception in people.getPhotos',
                        exceptSysInfo=True)
        finally:
            if getPhotosResp is None or not self.isGood(getPhotosResp):
                logging.error('getPhotosResp:[{!s}]'
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

        # Use a big random waitime to avoid errors in multiprocessing mode.
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
                np.niceprint('+++206: '
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

        if (ARGS.verbose):
            np.niceprint('   Setting Date:[{!s}] Id=[{!s}]'
                         .format(datetxt, photo_id))
        logging.warning('   Setting Date:[{!s}] Id=[{!s}]'
                        .format(datetxt, photo_id))

        @retry(attempts=3, waittime=15, randtime=True)
        def R_photos_setdates(kwargs):
            return nuflickr.photos.setdates(**kwargs)

        try:
            respDate = None
            respDate = R_photos_setdates(
                dict(photo_id=photo_id,
                     date_taken='{!s}'.format(datetxt),
                     date_taken_granularity=0))

            logging.debug('Output for {!s}:'.format('respDate'))
            logging.debug(xml.etree.ElementTree.tostring(
                respDate,
                encoding='utf-8',
                method='xml'))

            if (ARGS.verbose):
                np.niceprint(' Set Date Reply:[{!s}]'
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
        except (IOError, httplib.HTTPException):
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='211',
                        CaughtMsg='Caught IOError, HTTP exception'
                                  'on photos.setdates',
                        NicePrint=True)
        except BaseException:
            reportError(Caught=True,
                        CaughtPrefix='+++',
                        CaughtCode='212',
                        CaughtMsg='Caught exception on photos.setdates',
                        NicePrint=True,
                        exceptSysInfo=True)
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

    # -------------------------------------------------------------------------
    # rate4maddAlbumsMigrate
    #
    # Pace the calls to flickr on maddAlbumsMigrate
    #
    #   n   = for n calls per second  (ex. 3 means 3 calls per second)
    #   1/n = for n seconds per call (ex. 0.5 meand 4 seconds in between calls)
    @rate_limited.rate_limited(5)  # 5 calls per second
    def rate4maddAlbumsMigrate(self):
        """
        """
        logging.debug('rate_limit timestamp:[{!s}]'
                      .format(time.strftime('%T')))

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
            np.niceprint('ID:[{!s}] Path:[{!s}] Set:[{!s}] SetID:[{!s}]'
                         .format(str(f[0]), f[1], f[2], f[3]),
                         fname='addAlbumMigrate')

            # row[1] = path for the file from table files
            setName = self.getSetNameFromFile(f[1],
                                              xCfg.FILES_DIR,
                                              xCfg.FULL_SET_NAME)
            try:
                terr = False
                tfind, tid = self.photos_find_tag(
                    photo_id=f[0],
                    intag='album:{}'.format(f[2]
                                            if f[2] is not None
                                            else setName))
                np.niceprint('Found:[{!s}] TagId:[{!s}]'
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
                np.niceprint('Error processing Photo_id:[{!s}]. Continuing...'
                             .format(str(f[0])),
                             fname='addAlbumMigrate')

                terr = True

            if not terr and not tfind:
                res_add_tag = self.photos_add_tags(
                    f[0],
                    ['album:"{}"'.format(f[2]
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

        # ---------------------------------------------------------------------
        # Local Variables
        #
        #   mlockDB     = multiprocessing Lock for access to Database
        #   mmutex      = multiprocessing mutex for access to value mrunning
        #   mrunning    = multiprocessing Value to count processed photos
        mlockDB = None
        mmutex = None
        mrunning = None

        con = lite.connect(xCfg.DB_PATH)
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

            countTotal = len(existingMedia)
            # running in multi processing mode
            if (ARGS.processes and ARGS.processes > 0):
                logging.debug('Running Pool of [{!s}] processes...'
                              .format(ARGS.processes))
                logging.debug('__name__:[{!s}] to prevent recursive calling)!'
                              .format(__name__))

                # To prevent recursive calling, check if __name__ == '__main__'
                if __name__ == '__main__':
                    logging.debug('===Multiprocessing=== Setting up logger!')
                    multiprocessing.log_to_stderr()
                    logger = multiprocessing.get_logger()
                    logger.setLevel(xCfg.LOGGING_LEVEL)

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

                    sz = (len(existingMedia) // int(ARGS.processes)) \
                        if ((len(existingMedia) // int(ARGS.processes)) > 0) \
                        else 1

                    logging.debug('len(existingMedia):[{!s}] '
                                  'int(ARGS.processes):[{!s}] '
                                  'sz per process:[{!s}]'
                                  .format(len(existingMedia),
                                          int(ARGS.processes),
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
                        if (ARGS.verbose):
                            np.niceprint('===Job/Task Process: [{!s}] Started '
                                         'with pid:[{!s}]'
                                         .format(migrateTask.name,
                                                 migrateTask.pid))

                    # Check status of jobs/tasks in the Process Pool
                    if xCfg.LOGGING_LEVEL <= logging.DEBUG:
                        logging.debug('===Checking Processes launched/status:')
                        for j in migratePool:
                            np.niceprint('{!s}.is_alive = {!s}'
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
                            mTaskActive = p
                        logging.info('===Will wait for 60 on '
                                     '{!s}.is_alive = {!s}'
                                     .format(mTaskActive.name,
                                             mTaskActive.is_alive()))
                        if (ARGS.verbose_progress):
                            np.niceprint('===Will wait for 60 on '
                                         '{!s}.is_alive = {!s}'
                                         .format(mTaskActive.name,
                                                 mTaskActive.is_alive()))

                        mTaskActive.join(timeout=60)
                        logging.info('===Waited for 60s on '
                                     '{!s}.is_alive = {!s}'
                                     .format(mTaskActive.name,
                                             mTaskActive.is_alive()))
                        if (ARGS.verbose):
                            np.niceprint('===Waited for 60s on '
                                         '{!s}.is_alive = {!s}'
                                         .format(mTaskActive.name,
                                                 mTaskActive.is_alive()))

                    # Wait for join all jobs/tasks in the Process Pool
                    # All should be done by now!
                    for j in migratePool:
                        j.join()
                        if (ARGS.verbose):
                            np.niceprint('==={!s} '
                                         '(is alive: {!s}).exitcode = {!s}'
                                         .format(j.name,
                                                 j.is_alive(),
                                                 j.exitcode))

                    logging.warning('===Multiprocessing=== pool joined! '
                                    'All processes finished.')

                    # Will release (set to None) the nulockDB lock control
                    # this prevents subsequent calls to
                    # useDBLock( nuLockDB, False)
                    # to raise exception:
                    #   ValueError('semaphore or lock released too many times')
                    logging.info('===Multiprocessing=== pool joined! '
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
                count = 0
                countTotal = len(existingMedia)
                for row in existingMedia:
                    count += 1
                    # row[0] = files_id
                    # row[1] = path
                    # row[2] = set_name
                    # row[3] = set_id
                    np.niceprint('ID:[{!s}] Path:[{!s}] '
                                 'Set:[{!s}] SetID:[{!s}]'
                                 .format(str(row[0]), row[1],
                                         row[2], row[3]),
                                 fname='addAlbumMigrate')

                    # row[1] = path for the file from table files
                    setName = self.getSetNameFromFile(row[1],
                                                      xCfg.FILES_DIR,
                                                      xCfg.FULL_SET_NAME)
                    try:
                        tfind, tid = self.photos_find_tag(
                            photo_id=row[0],
                            intag='album:{}'.format(row[2]
                                                    if row[2] is not None
                                                    else setName))
                        np.niceprint('Found:[{!s}] TagId:[{!s}]'
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
                        np.niceprint('Error processing Photo_id:[{!s}]. '
                                     'Continuing...'
                                     .format(str(row[0])),
                                     fname='addAlbumMigrate')

                        self.niceprocessedfiles(count, countTotal, False)

                        continue

                    if not tfind:
                        res_add_tag = self.photos_add_tags(
                            row[0],
                            ['album:"{}"'.format(row[2]
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

        con = lite.connect(xCfg.DB_PATH)
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

            count = 0
            countTotal = len(badFiles)
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
        # Total Local photos count --------------------------------------------
        con = lite.connect(xCfg.DB_PATH)
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

        # Total Local badfiles photos count -----------------------------------
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

        # Total FLickr photos count: find('photos').attrib['total'] -----------
        countflickr = -1
        res = self.people_get_photos()
        logging.debug('Output for people_get_photos:')
        logging.debug(xml.etree.ElementTree.tostring(res,
                                                     encoding='utf-8',
                                                     method='xml'))
        if self.isGood(res):
            countflickr = format(res.find('photos').attrib['total'])
            logging.debug('Total photos on flickr: {!s}'.format(countflickr))

        # Total photos not on Sets/Albums on FLickr ---------------------------
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
        except BaseException:
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

            # Print total stats counters --------------------------------------
            np.niceprint('\n  Initial Found Files:[{!s:>6s}]\n'
                         '          - Bad Files:[{!s:>6s}] = [{!s:>6s}]\n'
                         '                 Note: some Bad files may no '
                         'longer exist!\n'
                         'Photos count:\n'
                         '                Local:[{!s:>6s}]\n'
                         '               Flickr:[{!s:>6s}]\n'
                         'Not in sets on Flickr:[{!s:>6s}]'
                         .format(str(InitialFoundFiles),
                                 str(BadFilesCount),
                                 str(InitialFoundFiles - BadFilesCount),
                                 str(countlocal),
                                 str(countflickr),
                                 str(countnotinsets)))

        # List pics not in sets (if within a parameter) -----------------------
        # Maximum allowed per_page by Flickr is 500.
        # Avoid going over in order not to have to handle multipl pages.
        if (ARGS.list_photos_not_in_set and
                ARGS.list_photos_not_in_set > 0 and
                countnotinsets > 0):
            np.niceprint('*****Listing Photos not in a set in Flickr******')
            # List pics not in sets (if within a parameter, default 10)
            # (per_page=min(ARGS.list_photos_not_in_set, 500):
            #       find('photos').attrib['total']
            res = self.photos_get_not_in_set(min(ARGS.list_photos_not_in_set,
                                                 500))
            logging.debug('Output for list get_not_in_set:')
            logging.debug(xml.etree.ElementTree.tostring(res,
                                                         encoding='utf-8',
                                                         method='xml'))

            if self.isGood(res):
                for count, row in enumerate(res.find('photos')
                                            .findall('photo')):
                    logging.info('Photo Not in Set: id:[{!s}] title:[{!s}]'
                                 .format(row.attrib['id'],
                                         StrUnicodeOut(row.attrib['title'])))
                    logging.debug(xml.etree.ElementTree.tostring(
                        row,
                        encoding='utf-8',
                        method='xml'))
                    np.niceprint('Photo get_not_in_set: id:[{!s}] title:[{!s}]'
                                 .format(row.attrib['id'],
                                         StrUnicodeOut(row.attrib['title'])))
                    logging.info('count=[{!s}]'.format(count))
                    if (count == 500) or \
                            (count >= (ARGS.list_photos_not_in_set - 1)) or \
                            (count >= (countnotinsets - 1)):
                        logging.info('Stopped at photo [{!s}] listing '
                                     'photos not in a set'.format(count))
                        break
            else:
                np.niceprint('Error in list get_not_in_set. No output.')

            np.niceprint('*****Completed Listing Photos not in a set '
                         'in Flickr******')


# -----------------------------------------------------------------------------
# parse_arguments
#
# This is the main method
#
def parse_arguments():
    """ parse_arguments

        Parse arguments and save results into global ARGS
    """

    global ARGS

    # Parse args --------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description='Upload files to Flickr. Uses uploadr.ini as config file.',
        epilog='by oPromessa, 2017, 2018'
    )

    # Configuration related options -------------------------------------------
    cgrpparser = parser.add_argument_group('Configuration related options')
    cgrpparser.add_argument('-C', '--config-file', action='store',
                            # dest='xINIfile',
                            metavar='filename.ini',
                            type=str,
                            # default=UPLDRConstants.INIfile,
                            help='Optional configuration file. '
                                 'Default is:[{!s}]'
                                 .format(UPLDRConstants.INIfile))
    # cgrpparser.add_argument('-C', '--config-file', action='store',
    #                         # dest='xINIfile',
    #                         metavar='filename.ini',
    #                         type=argparse.FileType('r'),
    #                         default=UPLDRConstants.INIfile,
    #                         help='Optional configuration file.'
    #                              'default is [{!s}]'
    #                              .format(UPLDRConstants.INIfile))

    # Verbose related options -------------------------------------------------
    vgrpparser = parser.add_argument_group('Verbose and dry-run options')
    vgrpparser.add_argument('-v', '--verbose', action='store_true',
                            help='Provides some more verbose output. '
                                 'See also -x option. '
                                 'See also LOGGING_LEVEL value in INI file.')
    vgrpparser.add_argument('-x', '--verbose-progress', action='store_true',
                            help='Provides progress indicator on each upload.'
                                 ' Normally used in conjunction with '
                                 '-v option. '
                                 'See also LOGGING_LEVEL value in INI file.')
    vgrpparser.add_argument('-n', '--dry-run', action='store_true',
                            help='Dry run. No changes are actually performed.')

    # Information related options ---------------------------------------------
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

    # Processing related options ----------------------------------------------
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
                                 'and exists on flickr prior to uploading. '
                                 'Use this option for faster INITIAL upload. '
                                 'Do not use it in subsequent uploads to '
                                 'prevent/recover orphan pics without a set.')
    # run in daemon mode uploading every X seconds
    pgrpparser.add_argument('-d', '--daemon', action='store_true',
                            help='Run forever as a daemon.'
                                 'Uploading every SLEEP_TIME seconds. Please '
                                 'note it only performs upload/replace.')

    # Bad files related options -----------------------------------------------
    # Cater for bad files. files in your Library that flickr does not recognize
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
                            help='Resets the badfiles table/list to allow a '
                            'new uploading attempt for bad files. Bad files '
                            'are files in your Library that flickr does not '
                            'recognize (Error 5) or are too large (Error 8). '
                            'Check also option -b.')
    # -s list the badfiles table
    bgrpparser.add_argument('-s', '--list-bad-files', action='store_true',
                            help='List the badfiles table/list.')
    # when you change EXCLUDED_FOLDERS setting
    bgrpparser.add_argument('-g', '--remove-excluded',
                            action='store_true',
                            help='Remove previously uploaded files, that are '
                                 'now being excluded due to change of the INI '
                                 'file configuration EXCLUDED_FOLDERS.'
                                 'NOTE: Option --remove-ignored was '
                                 'dropped in favor of --remove-excluded.')

    # Migration related options -----------------------------------------------
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

    ARGS = parser.parse_args()
    # Parse args --------------------------------------------------------------


# -----------------------------------------------------------------------------
# run_uploadr
#
# This is the main method
#
def run_uploadr():
    """ run_uploadr
    """
    # -------------------------------------------------------------------------

    global FLICK
    global ARGS

    # Print/show arguments
    if xCfg.LOGGING_LEVEL <= logging.INFO:
        np.niceprint('Output for arguments(ARGS):')
        pprint.pprint(ARGS)

    if ARGS.verbose:
        np.niceprint('FILES_DIR: [{!s}]'.format(StrUnicodeOut(xCfg.FILES_DIR)))

    logging.warning('FILES_DIR: [{!s}]'.format(StrUnicodeOut(xCfg.FILES_DIR)))

    if xCfg.FILES_DIR == "":
        np.niceprint('Please configure in the INI file [normally uploadr.ini],'
                     ' the name of the folder [FILES_DIR] '
                     'with media available to sync with Flickr.')
        sys.exit(8)
    else:
        if not os.path.isdir(xCfg.FILES_DIR):
            logging.critical('FILES_DIR: [{!s}] is not valid.'
                             .format(StrUnicodeOut(xCfg.FILES_DIR)))
            np.niceprint('Please configure the name of an existant folder '
                         'in the INI file [normally uploadr.ini] '
                         'with media available to sync with Flickr. '
                         'FILES_DIR: [{!s}] is not valid.'
                         .format(StrUnicodeOut(xCfg.FILES_DIR)))
            sys.exit(8)

    if xCfg.FLICKR["api_key"] == "" or xCfg.FLICKR["secret"] == "":
        logging.critical('Please enter an API key and secret in the '
                         'configuration '
                         'script file, normaly uploadr.ini (see README).')
        np.niceprint('Please enter an API key and secret in the configuration '
                     'script file, normaly uploadr.ini (see README).')
        sys.exit(9)

    # Instantiate class Uploadr
    logging.debug('Instantiating the Main class FLICK = Uploadr()')
    FLICK = Uploadr()

    # Setup the database
    FLICK.setupDB()
    if (ARGS.clean_bad_files):
        FLICK.cleanDBbadfiles()

    if ARGS.daemon:
        # Will run in daemon mode every SLEEP_TIME seconds
        logging.warning('Will run in daemon mode every {!s} seconds'
                        .format(xCfg.SLEEP_TIME))
        logging.warning('Make sure you have previously authenticated!')
        FLICK.run()
    else:
        np.niceprint('Checking if token is available... '
                     'if not will authenticate')
        if (not FLICK.checkToken()):
            FLICK.authenticate()

        if ARGS.add_albums_migrate:
            np.niceprint('Performing preparation for migration to 2.7.0',
                         fname='addAlbumsMigrate')

            if FLICK.addAlbumsMigrate():
                np.niceprint('Successfully added album tags to pics '
                             'on upload.',
                             fname='addAlbumsMigrate')
            else:
                logging.warning('Failed adding album tags to pics '
                                'on upload. '
                                'Please check logs, correct, and retry.')
                np.niceprint('Failed adding album tags to pics '
                             'on upload. '
                             'Please check logs, correct, and retry.',
                             fname='addAlbumsMigrate')
                sys.exit(10)
        elif ARGS.list_bad_files:
            np.niceprint('Listing badfiles: Start.',
                         fname='listBadFiles')
            FLICK.listBadFiles()
            np.niceprint('Listing badfiles: End. No more options will run.',
                         fname='listBadFiles')
        else:
            FLICK.removeUselessSetsTable()
            FLICK.getFlickrSets()
            FLICK.upload()
            FLICK.removeDeletedMedia()

            if ARGS.search_for_duplicates:
                FLICK.searchForDuplicates()

            if ARGS.remove_excluded:
                FLICK.removeExcludedMedia()

            FLICK.createSets()
            FLICK.printStat(UPLDRConstants.nuMediacount)
    # Run Uploadr -------------------------------------------------------------


# -----------------------------------------------------------------------------
# checkBaseDir_INIfile
#
# For use with flickrapi upload for showing callback progress information
# Check function FileWithCallback definition
# Uses global ARGS.verbose-progress parameter
#
def checkBaseDir_INIfile(baseDir, INIfile):
    """checkBaseDir_INIfile

    baseDir = Folder
    INIfile = INI File path
    """

    resultCheck = True
    try:
        if not ((baseDir == '' or os.path.isdir(baseDir)) and
                os.path.isfile(INIfile)):
            raise OSError('[Errno 2] No such file or directory')
    except Exception as err:
        resultCheck = False
        logging.critical(
            'Config folder [{!s}] and/or INI file: [{!s}] not found or '
            'incorrect format: [{!s}]!'
            .format(baseDir, INIfile, str(err)))
    finally:
        logging.debug('resultCheck=[{!s}]'.format(resultCheck))
        return resultCheck


# =============================================================================
# Global Variables
#
#   nutime       = for working with time module (import time)
#   nuflickr     = object for flickr API module (import flickrapi)
#   FLICK        = Class Uploadr (created in the Main code)
#   nulockDB     = multiprocessing Lock for access to Database
#   numutex      = multiprocessing mutex to control access to value nurunning
#   nurunning    = multiprocessing Value to count processed photos
#   retry        = alias for rate_limited.retry
#
# -----------------------------------------------------------------------------
nutime = time
nuflickr = None
nulockDB = None
numutex = None
nurunning = None
retry = rate_limited.retry
# -----------------------------------------------------------------------------

# =============================================================================
# Class UPLDRConstants
#
#   nuMediacount = Counter of total files to initially upload
#   baseDir      = Base configuration directory location
#   INIfile      = Configuration file
# -----------------------------------------------------------------------------
# UPLDRConstants = UPLDRConstantsClass.UPLDRConstants()
UPLDRConstants.nuMediacount = 0
# Base dir for config and support files.
#   Will use --config-file argument option
#   If not, first try sys.prefix/etc folder
#   If not, then try Current Working Directory
UPLDRConstants.baseDir = os.path.join(sys.prefix, 'etc')
UPLDRConstants.INIfile = os.path.join(UPLDRConstants.baseDir, "uploadr.ini")

if xCfg.LOGGING_LEVEL <= logging.DEBUG:
    logging.debug('       baseDir:[{!s}]'.format(UPLDRConstants.baseDir))
    logging.debug('           cwd:[{!s}]'.format(os.getcwd()))
    logging.debug('    prefix/etc:[{!s}]'.format(os.path.join(sys.prefix,
                                                              'etc')))
    logging.debug('   sys.argv[0]:[{!s}]'.format(os.path.dirname(sys.argv[0])))
    logging.debug('       INIfile:[{!s}]'.format(UPLDRConstants.INIfile))
# -----------------------------------------------------------------------------

# =============================================================================
# Functions aliases
#
#   StrUnicodeOut       = from niceprint module
#   isThisStringUnicode = from niceprint module
#   niceassert          = from niceprint module
#   reportError         = from niceprint module
# -----------------------------------------------------------------------------
np = niceprint.niceprint()
StrUnicodeOut = np.StrUnicodeOut
isThisStringUnicode = np.isThisStringUnicode
niceassert = np.niceassert
reportError = np.reportError
# -----------------------------------------------------------------------------

# =============================================================================
# Init code
#
# Python version must be greater than 2.7 for this script to run
#
if sys.version_info < (2, 7):
    sys.stderr.write('--------- (V' + UPLDRConstants.Version +
                     ') Error Init: ' + ' ---------\n')
    sys.stderr.write("This script requires Python 2.7 or newer.\n")
    sys.stderr.write("Current version: " + sys.version + "\n")
    sys.stderr.flush()
    sys.exit(1)
else:
    sys.stderr.write('--------- (V' + UPLDRConstants.Version +
                     ') Init: ' + ' ---------\n')
    sys.stderr.write('Python version on this system: ' + sys.version + '\n')
    sys.stderr.flush()
# -----------------------------------------------------------------------------


# =============================================================================
# Main code
#
np.niceprint('--------- (V{!s}) Start time: {!s} ---------(Log:{!s})'
             .format(UPLDRConstants.Version,
                     nutime.strftime(UPLDRConstants.TimeFormat),
                     xCfg.LOGGING_LEVEL))
if __name__ == "__main__":
    # Parse the argumens options
    parse_arguments()

    # Argument --config-file overrides configuration filename.
    if ARGS.config_file:
        UPLDRConstants.INIfile = ARGS.config_file
        logging.info('UPLDRConstants.INIfile:[{!s}]'
                     .format(StrUnicodeOut(UPLDRConstants.INIfile)))
        if not checkBaseDir_INIfile(UPLDRConstants.baseDir,
                                    UPLDRConstants.INIfile):
            reportError(Caught=True,
                        CaughtPrefix='+++ ',
                        CaughtCode='601',
                        CaughtMsg='Invalid -C parameter INI file. '
                                  'Exiting...',
                        NicePrint=True)
            sys.exit(2)
    else:
        # sys.argv[0]
        UPLDRConstants.baseDir = os.path.dirname(sys.argv[0])
        UPLDRConstants.INIfile = os.path.join(UPLDRConstants.baseDir,
                                              "uploadr.ini")

        if not checkBaseDir_INIfile(UPLDRConstants.baseDir,
                                    UPLDRConstants.INIfile):
            reportError(Caught=True,
                        CaughtPrefix='+++ ',
                        CaughtCode='602',
                        CaughtMsg='Invalid sys.argv INI file. '
                                  'Exiting...',
                        NicePrint=True)
            sys.exit(2)

    # Source configuration from INIfile
    xCfg.readconfig(UPLDRConstants.INIfile, ['Config'])
    if xCfg.processconfig():
        if xCfg.verifyconfig():
            pass
        else:
            raise ValueError('No config file found or incorrect config!')
    else:
        raise ValueError('No config file found or incorrect config!')

    # Update logging level as per LOGGING_LEVEL from INI file
    logging.getLogger().setLevel(xCfg.LOGGING_LEVEL)

    # CODING: Remove
    if xCfg.LOGGING_LEVEL <= logging.INFO:
        np.niceprint('Output for FLICKR Configuration:')
        pprint.pprint(xCfg.FLICKR)

    # Ensure that only one instance of this script is running
    f = open(xCfg.LOCK_PATH, 'w')
    try:
        # FileLocker is an alias to portalocker (if available) or fcntl
        FileLock(f, FileLocker.LOCK_EX | FileLocker.LOCK_NB)
    except IOError as e:
        if e.errno == errno.EAGAIN:
            sys.stderr.write('[{!s}] Script already running.\n'
                             .format(
                                 nutime.strftime(UPLDRConstants.TimeFormat)))
            sys.stderr.flush()
            sys.exit(-1)
        raise
    finally:
        run_uploadr()
np.niceprint('--------- (V{!s}) End time: {!s} -----------(Log:{!s})'
             .format(UPLDRConstants.Version,
                     nutime.strftime(UPLDRConstants.TimeFormat),
                     xCfg.LOGGING_LEVEL))
sys.stderr.write('--------- ' + 'End: ' + ' ---------\n')
sys.stderr.flush()
