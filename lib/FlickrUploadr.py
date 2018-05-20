"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

    Helper FlickrUploadr class to upload pics/videos into Flickr.
"""

# -----------------------------------------------------------------------------
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function,
#    unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1

# -----------------------------------------------------------------------------
# Import section
#
import sys
import logging
# Check if required httplib: Used only on exception httplib.HTTPException
try:
    import httplib as httplib      # Python 2
except ImportError:
    import http.client as httplib  # Python 3
import mimetypes
import os
import os.path
import time
import sqlite3 as lite
import hashlib
import subprocess
import xml
# Prevents error "AttributeError: 'module' object has no attribute 'etree'"
try:
    DUMMYXML = xml.etree.ElementTree.tostring(
        xml.etree.ElementTree.Element('xml.etree'),
        encoding='utf-8',
        method='xml')
except AttributeError:
    try:
        import xml.etree.ElementTree
    except ImportError:
        raise
import pprint
from itertools import islice
import flickrapi
# -----------------------------------------------------------------------------
# Helper class and functions for UPLoaDeR Global Constants.
import lib.UPLDRConstants as UPLDRConstantsClass
# -----------------------------------------------------------------------------
# Helper class and functions to print messages.
import lib.NicePrint as NicePrint
# -----------------------------------------------------------------------------
# Helper class and functions to rate/pace limiting function calls and run a
# function multiple attempts/times on error
import lib.rate_limited as rate_limited
# -----------------------------------------------------------------------------
# Helper module function to split work accross functions in multiprocessing
import lib.mprocessing as mp
# -----------------------------------------------------------------------------
# Helper module functions to wrap FlickrAPI with retry/try/exception/debug
import lib.FlickrApiWrapper as faw


# =============================================================================
# Functions aliases
#
#   strunicodeout       = from NicePrint module
#   niceerror           = from NicePrint module
# -----------------------------------------------------------------------------
UPLDR_K = UPLDRConstantsClass.UPLDRConstants()
NP = NicePrint.NicePrint()
strunicodeout = NP.strunicodeout
niceerror = NP.niceerror

NUTIME = time
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# FileWithCallback class
#
# For use with flickrapi upload for showing callback progress information
# Check function callback definition
#
class FileWithCallback(object):
    """ FileWithCallback

        For use with flickrapi upload for showing callback progress information
        Check function callback definition
    """

    def __init__(self, filename, fn_callback, verbose_progress):
        """ class FileWithCallback __init__
        """
        self.file = open(filename, 'rb')
        self.callback = fn_callback
        self.verbose_progress = verbose_progress
        # the following attributes and methods are required
        self.len = os.path.getsize(filename)
        self.fileno = self.file.fileno
        self.tell = self.file.tell

    # -------------------------------------------------------------------------
    # class FileWithCallback read
    #
    def read(self, size):
        """ read

            Read file to upload into Flickr with FileWithCallback
        """
        if self.callback:
            self.callback(self.tell() * 100 // self.len, self.verbose_progress)
        return self.file.read(size)


# -----------------------------------------------------------------------------
# callback
#
# For use with flickrapi upload for showing callback progress information
# Check function FileWithCallback definition
# Set verbose-progress True to display progress
#
def callback(progress, verbose_progress):
    """ callback

        Print progress % while uploading into Flickr.
        Valid only if argument verbose_progress is True
    """
    # only print rounded percentages: 0, 10, 20, 30, up to 100
    # adapt as required
    # if (progress % 10) == 0:
    # if verbose_progress option is set
    if verbose_progress:
        if (progress % 40) == 0:
            print(progress)


# -----------------------------------------------------------------------------
# chunk
#
# Divides an iterable in slices/chunks of size size
#
def chunk(itlist, size):
    """ chunk

        Divides an iterable in slices/chunks of size size

        >>> for a in chunk([ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 3):
        ...     len(a)
        3
        3
        3
        1
    """
    itlist = iter(itlist)
    # lambda: creates a returning expression function
    # which returns slices
    # iter, with the second argument () stops creating
    # iterators when it reaches the end
    return iter(lambda: tuple(islice(itlist, size)), ())


# -----------------------------------------------------------------------------
# md5checksum
#
def md5checksum(afilepath):
    """ md5checksum

        Calculates the MD5 checksum for filePath
    """
    with open(afilepath, 'rb') as filehandler:
        calc_md5 = hashlib.md5()
        while True:
            data = filehandler.read(8192)
            if not data:
                break
            calc_md5.update(data)
        return calc_md5.hexdigest()


# -------------------------------------------------------------------------
# set_name_from_file
#
def set_name_from_file(afile, afiles_dir, afull_set_name):
    """set_name_from_file

       Return setName for a file path depending on FULL_SET_NAME True/False
       Example:
       File to upload: /home/user/media/2014/05/05/photo.jpg
            FILES_DIR: /home/user/media
        FULL_SET_NAME:
               False=> 05
                True=> 2014/05/05

        >>> set_name_from_file('/some/photos/Parent/Album/unique file.jpg',\
        '/some/photos', False)
        'Album'
        >>> set_name_from_file('/some/photos/Parent/Album/unique file.jpg',\
        '/some/photos', True)
        'Parent/Album'
    """

    assert afile, NP.niceassert('[{!s}] is empty!'
                                .format(strunicodeout(afile)))

    logging.debug('set_name_from_file in: '
                  'afile:[%s] afiles_dir=[%s] afull_set_name:[%s]',
                  strunicodeout(afile),
                  strunicodeout(afiles_dir),
                  strunicodeout(afull_set_name))
    if afull_set_name:
        asetname = os.path.relpath(os.path.dirname(afile), afiles_dir)
    else:
        _, asetname = os.path.split(os.path.dirname(afile))
    logging.debug('set_name_from_file out: '
                  'afile:[%s] afiles_dir=[%s] afull_set_name:[%s]'
                  ' asetname:[%s]',
                  strunicodeout(afile),
                  strunicodeout(afiles_dir),
                  strunicodeout(afull_set_name),
                  strunicodeout(asetname))

    return asetname


# -------------------------------------------------------------------------
# rate_5_callspersecond
#
@rate_limited.rate_limited(5)  # 5 calls per second
def rate_5_callspersecond():
    """ rate_5_callspersecond

        Pace the calls rate within a specific function

          n   = n calls per second  (ex. 3 means 3 calls per second)
          1/n = n seconds per call (ex. 0.5 means 4 seconds in between calls)
    """
    logging.debug('rate_limit timestamp:[%s]', time.strftime('%T'))


# -----------------------------------------------------------------------------
# Uploadr class
#
#   Main class for uploading of files.
#
class Uploadr(object):
    """ Uploadr class

    """

    # flickrapi.FlickrAPI object
    nuflickr = None
    # Flicrk connection authentication token
    token = None

    # -------------------------------------------------------------------------
    # class Uploadr __init__
    #
    def __init__(self, axCfg, args):
        """ class Uploadr __init__

            axCfg = Configuration (check lib.myconfig)
            args  = provides access to arguments values

            Gets FlickrAPI cached token, if available.
            Adds .3gp mimetime as video.
        """

        self.xcfg = axCfg
        self.args = args
        # get nuflickr/token from Cache file, if it exists
        self.nuflickr, self.token = self.getCachedToken()

        # Add mimetype .3gp to allow detection of .3gp as video
        logging.info('Adding mimetype "video/3gp"/".3gp"')
        mimetypes.add_type('video/3gpp', '.3gp')
        if not mimetypes.types_map['.3gp'] == 'video/3gpp':
            niceerror(caught=True,
                      caughtprefix='xxx',
                      caughtcode='001',
                      caughtmsg='Not able to add mimetype'
                      ' ''video/3gp''/''.3gp'' correctly',
                      useniceprint=True)
        else:
            logging.warning('Added mimetype "video/3gp"/".3gp" correctly.')

    # -------------------------------------------------------------------------
    # getCachedToken
    #
    # If available, obtains the flickrapi Cached Token from local file.
    # Returns the flickrapi object to be saved on the Class variable "nuflickr"
    # Returns the token to be saved on the Class variable "token"
    #
    def getCachedToken(self):
        """ getCachedToken

            Attempts to get the flickr token from disk.

            Returns the flickrapi object, token
        """

        logging.info('Obtaining Cached token')
        logging.debug('TOKEN_CACHE:[%s]', self.xcfg.TOKEN_CACHE)
        flickrobj = flickrapi.FlickrAPI(
            self.xcfg.FLICKR["api_key"],
            self.xcfg.FLICKR["secret"],
            token_cache_location=self.xcfg.TOKEN_CACHE)

        try:
            # Check if token permissions are correct.
            if flickrobj.token_valid(perms='delete'):
                logging.info('Cached token obtained: [%s]',
                             flickrobj.token_cache.token)
                return flickrobj, flickrobj.token_cache.token
            else:
                logging.warning('Token Non-Existant.')
                return None, None
        except BaseException:
            niceerror(caught=True,
                      caughtprefix='+++',
                      caughtcode='007',
                      caughtmsg='Unexpected error in token_valid',
                      exceptsysinfo=True)
            raise

    # -------------------------------------------------------------------------
    # check_token
    #
    # If available, obtains the flickrapi Cached Token from local file.
    #
    # Returns
    #   True: if self.token is defined and allows flicrk 'delete' operation
    #   False: if self.token is not defined or flicrk 'delete' is not allowed
    #
    def check_token(self):
        """ check_token

            flickr.auth.checkToken

            Returns the credentials attached to an authentication token.
        """
        result = False
        logging.warning(
            'check_token:(self.token is None):[%s]'
            'check_token:(nuflickr is None):[%s]'
            'check_token:(nuflickr.token_cache.token is None):[%s]',
            self.token is None,
            self.nuflickr is None,
            self.nuflickr.token_cache.token is None
            if self.nuflickr is not None
            else 'Not valid as nuflickr is None')

        if self.nuflickr is not None:
            result = self.nuflickr.token_cache.token is not None

        return result

    # -------------------------------------------------------------------------
    # authenticate
    #
    # Authenticates via flickrapi on flickr.com
    #
    def authenticate(self):
        """ authenticate

            Authenticate user so we can upload files.
            Assumes the cached token is not available or valid.
        """

        # Instantiate nuflickr for connection to flickr via flickrapi
        self.nuflickr = flickrapi.FlickrAPI(
            self.xcfg.FLICKR["api_key"],
            self.xcfg.FLICKR["secret"],
            token_cache_location=self.xcfg.TOKEN_CACHE)
        # Get request token
        NP.niceprint('Getting new token.')
        try:
            self.nuflickr.get_request_token(oauth_callback='oob')
        except Exception as ex:
            niceerror(caught=True,
                      caughtprefix='+++',
                      caughtcode='004',
                      caughtmsg='Exception on get_request_token. Exiting...',
                      exceptuse=True,
                      # exceptCode=ex.code,
                      exceptmsg=ex,
                      useniceprint=True,
                      exceptsysinfo=True)
            sys.exit(4)

        # Show url. Copy and paste it in your browser
        authorize_url = self.nuflickr.auth_url(perms=u'delete')
        NP.niceprint('Copy and paste following authorizaiton URL '
                     'in your browser to obtain Verifier Code.')
        print(authorize_url)

        # Prompt for verifier code from the user.
        verifier = unicode(raw_input(  # noqa
            'Verifier code (NNN-NNN-NNN): ')) \
            if sys.version_info < (3, ) \
            else input('Verifier code (NNN-NNN-NNN): ')

        logging.warning('Verifier: %s', verifier)

        # Trade the request token for an access token
        try:
            self.nuflickr.get_access_token(verifier)
        except flickrapi.exceptions.FlickrError as ex:
            niceerror(caught=True,
                      caughtprefix='+++',
                      caughtcode='005',
                      caughtmsg='Flickrapi exception on get_access_token. '
                      'Exiting...',
                      exceptuse=True,
                      exceptcode=ex.code,
                      exceptmsg=ex,
                      useniceprint=True,
                      exceptsysinfo=True)
            sys.exit(5)

        NP.niceprint('Check Authentication with [delete] permissions: {!s}'
                     .format(self.nuflickr.token_valid(perms='delete')))

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
        NP.niceprint('*****Removing files from Excluded Folders*****')

        if not self.check_token():
            # authenticate sys.exits in case of failure
            self.authenticate()
        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str

        with con:
            cur = con.cursor()
            cur.execute("SELECT files_id, path FROM files")
            rows = cur.fetchall()

            for row in rows:
                logging.debug('Checking file_id:[%s] file:[%s] '
                              'isFileExcluded?',
                              strunicodeout(row[0]),
                              strunicodeout(row[1]))
                logging.debug('type(row[1]):[%s]', type(row[1]))
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

        NP.niceprint('*****Completed files from Excluded Folders*****')

    # -------------------------------------------------------------------------
    # removeDeleteMedia
    #
    # Remove files deleted at the local source
    #
    def removeDeletedMedia(self):
        """ removeDeletedMedia

        Remove files deleted at the local source
            loop through database
            check if file exists
            if exists, continue
            if not exists, delete photo from fickr (flickr.photos.delete.html)
        """

        NP.niceprint('*****Removing deleted files*****')

        if not self.check_token():
            # authenticate sys.exits in case of failure
            self.authenticate()
        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str

        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT files_id, path FROM files")
                rows = cur.fetchall()
                NP.niceprint('[{!s:>6s}] will be checked for Removal...'
                             .format(str(len(rows))))
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='008',
                          caughtmsg='DB error on SELECT: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
                if con is not None:
                    con.close()
                return False

            count = 0
            for row in rows:
                if (not os.path.isfile(row[1].decode('utf-8')
                                       if NP.is_str_unicode(row[1])
                                       else row[1])):
                    # Running in single processing mode, no need for lock
                    success = self.deleteFile(row, cur)
                    logging.warning('deleteFile result: [%s]', success)
                    count = count + 1
                    if count % 3 == 0:
                        NP.niceprint('[{!s:>6s}] files removed...'
                                     .format(str(count)))
            if count % 100 > 0:
                NP.niceprint('[{!s:>6s}] files removed...'
                             .format(str(count)))

        # Closing DB connection
        if con is not None:
            con.close()

        NP.niceprint('*****Completed deleted files*****')

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
        # ---------------------------------------------------------------------
        # Local Variables
        #
        #   nulockDB     = multiprocessing Lock for access to Database
        #   numutex      = multiprocessing mutex for access to value srunning
        #   nrunning    = multiprocessing Value to count processed photos
        nulockDB = None
        numutex = None
        nurunning = None

        NP.niceprint("*****Uploading files*****")

        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str

        with con:
            # Search for  media files to load including raw files to convert
            allMedia, rawfiles = self.grabNewFiles()

            # If managing changes, consider all files
            if self.xcfg.MANAGE_CHANGES:
                logging.warning('MANAGE_CHANGES is True. Reviewing allMedia.')
                changedMedia = allMedia

            # If not, then get just the new and missing files
            else:
                logging.warning('MANAGE_CHANGES is False. Reviewing only '
                                'changedMedia.')
                cur = con.cursor()
                try:
                    cur.execute("SELECT path FROM files")
                    existingMedia = set(file[0] for file in cur.fetchall())
                    changedMedia = set(allMedia) - existingMedia
                except lite.Error as err:
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='015',
                              caughtmsg='DB error on DB select: [{!s}]'
                              .format(err.args[0]),
                              useniceprint=True,
                              exceptsysinfo=True)
                    changedMedia = allMedia

        changedMedia_count = len(changedMedia)
        UPLDRConstantsClass.media_count = changedMedia_count
        NP.niceprint('Found [{!s:>6s}] files to upload.'
                     .format(str(changedMedia_count)))

        # Convert Raw files
        self.convertRawFiles(rawfiles, changedMedia)

        if self.args.bad_files:
            # Cater for bad files
            con = lite.connect(self.xcfg.DB_PATH)
            con.text_factory = str
            with con:
                cur = con.cursor()
                cur.execute("SELECT path FROM badfiles")
                badMedia = set(file[0] for file in cur.fetchall())
                changedMedia = set(changedMedia) - badMedia
                logging.debug('len(badMedia)=[%s]', len(badMedia))

            changedMedia_count = len(changedMedia)
            NP.niceprint('Removing {!s} badfiles. Found {!s} files to upload.'
                         .format(len(badMedia),
                                 changedMedia_count))

        # running in multi processing mode
        if self.args.processes and self.args.processes > 0:
            logging.debug('Running [%s] processes pool.', self.args.processes)
            logging.debug('__name__:[%s] to prevent recursive calling)!',
                          __name__)

            con = lite.connect(self.xcfg.DB_PATH)
            con.text_factory = str
            cur = con.cursor

            # To prevent recursive calling, check if __name__ == '__main__'
            # if __name__ == '__main__':
            mp.mprocessing(self.args.verbose,
                           self.args.verbose_progress,
                           self.args.processes,
                           nulockDB,
                           nurunning,
                           numutex,
                           changedMedia,
                           self.uploadFileX,
                           cur)
            con.commit()

        # running in single processing mode
        else:
            count = 0
            for i, file in enumerate(changedMedia):
                logging.debug('file:[%s] type(file):[%s]',
                              file, type(file))
                # lock parameter not used (set to None) under single processing
                success = self.uploadFile(lock=None, file=file)
                if (self.args.drip_feed and
                        success and
                        i != changedMedia_count - 1):
                    NP.niceprint('Waiting [{!s}] seconds before next upload'
                                 .format(str(self.xcfg.DRIP_TIME)))
                    NUTIME.sleep(self.xcfg.DRIP_TIME)
                count = count + 1
                NP.niceprocessedfiles(count,
                                      UPLDRConstantsClass.media_count,
                                      False)

            # Show number of total files processed
            NP.niceprocessedfiles(count, UPLDRConstantsClass.media_count, True)

        # Closing DB connection
        if con is not None:
            con.close()
        NP.niceprint("*****Completed uploading files*****")

    # -------------------------------------------------------------------------
    # convertRawFiles
    #
    # Processes RAW files and adds the converted JPG files to the
    # finalMediafiles
    #
    def convertRawFiles(self, rawfiles, finalMediafiles):
        """ convertRawFiles

            rawfiles        = List with raw files
            finalMediafiles = Converted Raw files will be appended to this list
                              list will be sorted
        """

        if not self.xcfg.CONVERT_RAW_FILES:
            return

        NP.niceprint('*****Converting files*****')
        for fullpath in rawfiles:
            dirpath, f = os.path.split(fullpath)
            fnameonly = os.path.splitext(f)[0]
            ext = os.path.splitext(f)[1][1:].lower()

            if self.args.dry_run:
                NP.niceprint('Dry Run rawfile:[{!s}]...'
                             .format(strunicodeout(fullpath)))
                continue

            if self.convertRawFile(dirpath, f, ext, fnameonly):
                try:
                    okfilesize = True
                    filesize = os.path.getsize(
                        os.path.join(strunicodeout(dirpath),
                                     strunicodeout(fnameonly) + '.JPG'))
                    logging.debug('Converted .JPG file size=[%s]', filesize)
                except Exception:
                    okfilesize = False
                    niceerror(caught=True,
                              caughtprefix='+++',
                              caughtcode='009',
                              caughtmsg='Exception in size convertRawFiles',
                              useniceprint=False,
                              exceptsysinfo=True)

                if okfilesize and (filesize < self.xcfg.FILE_MAX_SIZE):
                    finalMediafiles.append(
                        os.path.normpath(
                            strunicodeout(dirpath) +
                            strunicodeout("/") +
                            strunicodeout(fnameonly).replace("'", "\'") +
                            strunicodeout('.JPG')))
                else:
                    NP.niceprint('Skipping file due to '
                                 'size restriction/issue: [{!s}]'
                                 .format(os.path.normpath(
                                     strunicodeout(dirpath) +
                                     strunicodeout('/') +
                                     strunicodeout(f))))
            else:
                NP.niceprint('Convert raw file failed. '
                             'Skipping file: [{!s}]'
                             .format(os.path.normpath(
                                 strunicodeout(dirpath) +
                                 strunicodeout('/') +
                                 strunicodeout(f))))
        finalMediafiles.sort()
        NP.niceprint('*****Completed converting files*****')

    # -------------------------------------------------------------------------
    # convertRawFile
    #
    # Converts a RAW file into JPG. Also copies tags from RAW file.
    # Uses external exiftool.
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
        # Prepare and executes the command for RAW file conversion.
        #
        def convertRawFileCommand(ConvertOrCopyTags):
            """ convertRawFileCommand

            ConvertOrCopyTags = 'Convert'  converts a raw file to JPG
                                'CopyTags' copy tags from raw file to JPG
            """

            assert ConvertOrCopyTags in ['Convert', 'CopyTags'],\
                NP.niceassert('convertRawFileCommand: wrong argument:[{!s}]'
                              .format(ConvertOrCopyTags))

            result_cmd = True
            if ConvertOrCopyTags == 'Convert':
                flag = "-PreviewImage" \
                       if Fext == 'cr2' else "-JpgFromRaw"
                command = os.path.join(strunicodeout(self.xcfg.RAW_TOOL_PATH),
                                       'exiftool') +\
                    " -b " + flag + " -w .JPG -ext " + Fext + " -r " +\
                    "'" + os.path.join(strunicodeout(Ddirpath),
                                       strunicodeout(Ffname)) + "'"
            elif ConvertOrCopyTags == 'CopyTags':
                command = os.path.join(strunicodeout(self.xcfg.RAW_TOOL_PATH),
                                       'exiftool') +\
                    " -overwrite_original_in_place -tagsfromfile " +\
                    "'" + os.path.join(strunicodeout(Ddirpath),
                                       strunicodeout(Ffname)) + "'" +\
                    " -r -all:all -ext JPG " +\
                    "'" + os.path.join(strunicodeout(Ddirpath),
                                       strunicodeout(Ffnameonly)) + ".JPG'"
            else:
                # Nothing to do
                return False

            logging.info(command)
            try:
                p_cmd = subprocess.call(command, shell=True)
            except BaseException:
                niceerror(caught=True,
                          caughtprefix='+++',
                          caughtcode='016',
                          caughtmsg='Error calling exiftool:[{!s}]'
                          .format(ConvertOrCopyTags),
                          useniceprint=True,
                          exceptsysinfo=True)
                result_cmd = False
            finally:
                if p_cmd is None:
                    del p_cmd

            return result_cmd
        # ---------------------------------------------------------------------

        if self.args.dry_run:
            return True

        NP.niceprint(' Converting raw:[{!s}]'
                     .format(strunicodeout(os.path.join(Ddirpath, Ffname))))
        logging.info(' Converting raw:[%s]',
                     strunicodeout(os.path.join(Ddirpath, Ffname)))
        success = False

        # fileExt = FFname's extension (without the ".")
        fileExt = os.path.splitext(Ffname)[-1][1:].lower()
        assert strunicodeout(Fext) == strunicodeout(fileExt),\
            NP.niceassert('File extensions differ:[{!s}]!=[{!s}]'
                          .format(strunicodeout(Fext),
                                  strunicodeout(fileExt)))

        if not os.path.exists(os.path.join(Ddirpath, Ffnameonly) + ".JPG"):
            logging.info('.....Create JPG:[%s] jpg:[%s] ext:[%s]',
                         strunicodeout(Ffname),
                         strunicodeout(Ffnameonly),
                         strunicodeout(fileExt))
            if convertRawFileCommand('Convert'):
                NP.niceprint('....Created JPG:[{!s}]'
                             .format(strunicodeout(Ffnameonly) + ".JPG"))
            else:
                NP.niceprint('.....raw failed:[{!s}]'.format(Ffname))
                return success
        else:
            NP.niceprint('raw: JPG exists:[{!s}]'
                         .format(strunicodeout(Ffnameonly) + ".JPG"))
            logging.warning('raw: JPG exists:[%s]',
                            strunicodeout(Ffnameonly) + ".JPG")
            return success

        if os.path.exists(strunicodeout(os.path.join(Ddirpath, Ffnameonly)) +
                          ".JPG"):
            NP.niceprint('...Copying tags:[{!s}]'
                         .format(strunicodeout(Ffname)))

            if convertRawFileCommand('CopyTags'):
                NP.niceprint('....Copied tags:[{!s}]'
                             .format(strunicodeout(Ffname)))
            else:
                NP.niceprint('raw tags failed:[{!s}]'.format(Ffname))
                return success
        else:
            NP.niceprint('.....raw failed:[{!s}]'.format(Ffname))
            logging.warning('.....raw failed:[%s]', Ffname)
            return success

        success = True
        NP.niceprint('  Converted raw:[{!s}]'.format(strunicodeout(Ffname)))
        logging.info('  Converted raw:[%s]', strunicodeout(Ffname))

        return success

    # -------------------------------------------------------------------------
    # grabNewFiles
    #
    # Select files and RAW files from FILES_DIR to be uploaded
    #
    def grabNewFiles(self):
        """ grabNewFiles

            Select files from FILES_DIR taking into consideration
            EXCLUDED_FOLDERS and IGNORED_REGEX filenames.
            Returns two sorted file lists:
                JPG files found
                RAW files found (if RAW conversion option is enabled)
        """

        files = []
        rawfiles = []
        for dirpath, dirnames, filenames in\
                os.walk(self.xcfg.FILES_DIR, followlinks=True):

            # Prevent walking thru files in the list of EXCLUDED_FOLDERS
            # Reduce time by not checking a file in an excluded folder
            logging.debug('Check for UnicodeWarning comparison '
                          'dirpath:[%s] type:[%s]',
                          strunicodeout(os.path.basename(
                              os.path.normpath(dirpath))),
                          type(os.path.basename(
                              os.path.normpath(dirpath))))
            if os.path.basename(os.path.normpath(dirpath)) \
                    in self.xcfg.EXCLUDED_FOLDERS:
                dirnames[:] = []
                filenames[:] = []
                logging.info('Folder [%s] on path [%s] excluded.',
                             strunicodeout(os.path.basename(
                                 os.path.normpath(dirpath))),
                             strunicodeout(os.path.normpath(dirpath)))

            for f in filenames:
                filePath = os.path.join(strunicodeout(dirpath),
                                        strunicodeout(f))
                # Ignore filenames wihtin IGNORED_REGEX
                if any(ignored.search(f)
                       for ignored in self.xcfg.IGNORED_REGEX):
                    logging.debug('File %s in IGNORED_REGEX:',
                                  strunicodeout(filePath))
                    continue
                ext = os.path.splitext(os.path.basename(f))[1][1:].lower()
                if ext in self.xcfg.ALLOWED_EXT:
                    filesize = os.path.getsize(os.path.join(
                        strunicodeout(dirpath), strunicodeout(f)))
                    if filesize < self.xcfg.FILE_MAX_SIZE:
                        files.append(
                            os.path.normpath(
                                strunicodeout(dirpath) +
                                strunicodeout("/") +
                                strunicodeout(f).replace("'", "\'")))
                    else:
                        NP.niceprint('Skipping file due to '
                                     'size restriction: [{!s}]'.format(
                                         os.path.normpath(
                                             strunicodeout(dirpath) +
                                             strunicodeout('/') +
                                             strunicodeout(f))))
                # Assumes xCFG.ALLOWED_EXT and xCFG.RAW_EXT are disjoint
                elif (self.xcfg.CONVERT_RAW_FILES and
                      (ext in self.xcfg.RAW_EXT)):
                    if not os.path.exists(
                            os.path.join(
                                strunicodeout(dirpath),
                                strunicodeout(os.path.splitext(f)[0])) +
                            ".JPG"):
                        logging.debug('rawfiles: including:[%s]',
                                      strunicodeout(f))
                        rawfiles.append(
                            os.path.normpath(
                                strunicodeout(dirpath) +
                                strunicodeout("/") +
                                strunicodeout(f).replace("'", "\'")))
                    else:
                        logging.warning('rawfiles: JPG exists. '
                                        'Not including:[%s]',
                                        strunicodeout(f))
        rawfiles.sort()
        files.sort()
        if self.xcfg.LOGGING_LEVEL <= logging.DEBUG:
            NP.niceprint('Pretty Print Output for [files]-------')
            pprint.pprint(files)
            NP.niceprint('Pretty Print Output for [rawfiles]----')
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
        for excluded_dir in self.xcfg.EXCLUDED_FOLDERS:
            logging.debug('type(excluded_dir):[%s]', type(excluded_dir))
            logging.debug('is excluded_dir unicode?[%s]',
                          NP.is_str_unicode(excluded_dir))
            logging.debug('type(filename):[%s]', type(filename))
            logging.debug('is filename unicode?[{%s]',
                          NP.is_str_unicode(filename))
            logging.debug('is os.path.dirname(filename) unicode?[%s]',
                          NP.is_str_unicode(os.path.dirname(filename)))
            logging.debug('excluded_dir:[%s] filename:[%s]',
                          strunicodeout(excluded_dir),
                          strunicodeout(filename))
            # Now everything should be in Unicode
            if excluded_dir in os.path.dirname(filename):
                logging.debug('Returning isFileExcluded:[True]')
                return True

        logging.debug('Returning isFileExcluded:[False]')
        return False

    # -------------------------------------------------------------------------
    # updatedVideoDate
    #
    # Update the video date taken based on last_modified time of file
    #
    def updatedVideoDate(self, xfile_id, xfile, xlast_modified):
        """ updatedVideoDate

            Update the video date taken based on last_modified time of file
        """
        # Update Date/Time on Flickr for Video files
        # Flickr doesn't read it from the video file itself.
        filetype = mimetypes.guess_type(xfile)
        logging.info('filetype is:[%s]', 'None'
                     if filetype is None
                     else filetype[0])

        # update video date/time TAKEN.
        # Flickr doesn't read it from the video file itself.
        if (not filetype[0] is None) and ('video' in filetype[0]):
            res_set_date = None
            video_date = NUTIME.strftime('%Y-%m-%d %H:%M:%S',
                                         NUTIME.localtime(xlast_modified))
            logging.info('video_date:[%s]', video_date)

            if self.args.verbose:
                NP.niceprint('   Setting Date:[{!s}] for file:[{!s}] Id=[{!s}]'
                             .format(video_date,
                                     strunicodeout(xfile),
                                     xfile_id))

            res_set_date = self.photos_set_dates(xfile_id,
                                                 str(video_date))

            if faw.is_good(res_set_date):
                NP.niceprint('Successful date:[{!s}] '
                             'for file:[{!s}]'
                             .format(strunicodeout(video_date),
                                     strunicodeout(xfile)))

        return True

    # -------------------------------------------------------------------------
    # uploadFileX
    #
    # uploadFile wrapper for multiprocessing purposes
    #
    def uploadFileX(self, lock, running, mutex, filelist, ctotal, cur):
        """ uploadFileX

            Wrapper function for multiprocessing support to call uploadFile
            with a chunk of the files.
            lock = for database access control in multiprocessing
            running = shared value to count processed files in multiprocessing
            mutex = for running access control in multiprocessing
        """

        for i, filepic in enumerate(filelist):
            logging.warning('===Current element of Chunk: [%s][%s]',
                            i, filepic)
            self.uploadFile(lock, filepic)

            # no need to check for
            # (self.args.processes and self.args.processes > 0):
            # as uploadFileX is already multiprocessing

            logging.debug('===Multiprocessing=== in.mutex.acquire(w)')
            mutex.acquire()
            running.value += 1
            xcount = running.value
            mutex.release()
            logging.warning('===Multiprocessing=== out.mutex.release(w)')

            # Show number of files processed so far
            NP.niceprocessedfiles(xcount, ctotal, False)

    # -------------------------------------------------------------------------
    # uploadFile
    #
    # uploads a file into flickr
    #   lock = parameter for multiprocessing control of access to DB.
    #          (if self.args.processes = 0 then lock can be None
    #          as it is not used)
    #   file = file to be uploaded
    #
    def uploadFile(self, lock, file):
        """ uploadFile
        uploads file into flickr

        May run in single or multiprocessing mode

        lock = parameter for multiprocessing control of access to DB.
               (if self.args.processes = 0 then lock may be None
               as it is not used)
        file = file to be uploaded
        """

        # ---------------------------------------------------------------------
        # dbInsertIntoFiles
        #
        def dbInsertIntoFiles(lock,
                              file_id, file, file_checksum, last_modified):
            """ dbInsertIntoFiles

            Insert into local DB files table.

            lock          = for multiprocessing access control to DB
            file_id       = pic id
            file          = filename
            file_checksum = md5 checksum
            last_modified = Last modified time
            """

            # Database Locked is returned often on this INSERT
            # Will try MAX_SQL_ATTEMPTS...
            for x in range(0, self.xcfg.MAX_SQL_ATTEMPTS):
                logging.info('BEGIN SQL:[%s]...[%s}/%s attempts].',
                             'INSERT INTO files',
                             x,
                             self.xcfg.MAX_SQL_ATTEMPTS)
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
                except lite.Error as err:
                    DBexception = True
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='030',
                              caughtmsg='DB error on INSERT: [{!s}]'
                              .format(err.args[0]),
                              useniceprint=True,
                              exceptsysinfo=True)
                finally:
                    con.commit()
                    # Release DBlock if in multiprocessing mode
                    self.useDBLock(lock, False)

                if DBexception:
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='031',
                              caughtmsg='Sleep 2 and retry SQL...'
                              '[{!s}/{!s} attempts]'
                              .format(x, self.xcfg.MAX_SQL_ATTEMPTS),
                              useniceprint=True)
                    NUTIME.sleep(2)
                else:
                    if x > 0:
                        niceerror(caught=True,
                                  caughtprefix='+++ DB',
                                  caughtcode='032',
                                  caughtmsg='Succeed at retry SQL...'
                                  '[{!s}/{!s} attempts]'
                                  .format(x, self.xcfg.MAX_SQL_ATTEMPTS),
                                  useniceprint=True)
                    logging.info(
                        'END SQL:[%s]...[%s/%s attempts].',
                        'INSERT INTO files',
                        x,
                        self.xcfg.MAX_SQL_ATTEMPTS)
                    # Break the cycle of SQL_ATTEMPTS and continue
                    break
        # ---------------------------------------------------------------------

        if self.args.dry_run:
            NP.niceprint('   Dry Run file:[{!s}]...'
                         .format(strunicodeout(file)))
            return True

        if self.args.verbose:
            NP.niceprint('  Checking file:[{!s}]...'
                         .format(strunicodeout(file)))

        setName = set_name_from_file(file,
                                     self.xcfg.FILES_DIR,
                                     self.xcfg.FULL_SET_NAME)

        success = False
        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str
        with con:
            cur = con.cursor()
            logging.debug('uploadFILE SELECT: {%s}: {%s}',
                          'SELECT rowid, files_id, path, '
                          'set_id, md5, tagged, '
                          'last_modified FROM '
                          'files WHERE path = ?',
                          file)

            try:
                # Acquire DB lock if running in multiprocessing mode
                self.useDBLock(lock, True)
                cur.execute('SELECT rowid, files_id, path, set_id, md5, '
                            'tagged, last_modified FROM files WHERE path = ?',
                            (file,))
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='035',
                          caughtmsg='DB error on SELECT: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
            finally:
                # Release DB lock if running in multiprocessing mode
                self.useDBLock(lock, False)

            row = cur.fetchone()
            logging.debug('row: %s', row)

            # use file modified timestamp to check for changes
            last_modified = os.stat(file).st_mtime
            file_checksum = None

            # Check if file is already loaded
            if self.args.not_is_already_uploaded:
                isLoaded = False
                isfile_id = None
                isNoSet = None
                logging.info('not_is_already_uploaded:[%s]', isLoaded)
            else:
                file_checksum = md5checksum(file)
                isLoaded, isCount, isfile_id, isNoSet = \
                    self.is_already_uploaded(file,
                                             file_checksum,
                                             setName)
                logging.info('is_already_uploaded:[%s] '
                             'count:[%s] pic:[%s] '
                             'row is None == [%s] '
                             'isNoSet:[%s]',
                             isLoaded,
                             isCount, isfile_id,
                             row is None,
                             isNoSet)
            # CODING: REUPLOAD deleted files from Flickr...
            # A) File loaded. Not recorded on DB. Update local DB.
            # B) Not loaded. Not recorded on DB. Upload file to FLickr.
            # C) File loaded. Recorded on DB. Look for changes...
            # D) Not loaded, Recorded on DB. Reupload.
            #    Handle D) like B)...
            #    or (not isLoaded and row is not None)
            #    ... delete from DB... run normally the (RE)upload process

            # A) File loaded. Not recorded on DB. Update local DB.
            if isLoaded and row is None:
                if file_checksum is None:
                    file_checksum = md5checksum(file)

                # Insert into DB files
                logging.warning(' Already loaded:[%s]...'
                                'On Album:[%s]... UPDATING LOCAL DATABASE.',
                                strunicodeout(file),
                                strunicodeout(setName))
                NP.niceprint(' Already loaded:[{!s}]...'
                             'On Album:[{!s}]... UPDATING LOCAL DATABASE.'
                             .format(strunicodeout(file),
                                     strunicodeout(setName)))
                dbInsertIntoFiles(lock, isfile_id, file,
                                  file_checksum, last_modified)

                # Update the Video Date Taken
                self.updatedVideoDate(isfile_id, file, last_modified)

                con.commit()

            # B) Not loaded. Not recorded on DB. Upload file to FLickr.
            elif row is None:
                if self.args.verbose:
                    NP.niceprint(' Uploading file:[{!s}]...'
                                 'On Album:[{!s}]...'
                                 .format(strunicodeout(file),
                                         strunicodeout(setName)))

                logging.warning(' Uploading file:[%s]... On Album:[%s]...',
                                strunicodeout(file), strunicodeout(setName))

                if file_checksum is None:
                    file_checksum = md5checksum(file)

                # Title Handling
                if self.args.title:
                    self.xcfg.FLICKR["title"] = self.args.title
                # Description Handling
                if self.args.description:
                    self.xcfg.FLICKR["description"] = self.args.description
                # Tags Handling
                if self.args.tags:  # Append a space to later add -t TAGS
                    self.xcfg.FLICKR["tags"] += " "
                    if self.args.verbose:
                        NP.niceprint('TAGS:[{} {}]'
                                     .format(self.xcfg.FLICKR["tags"],
                                             self.args.tags).replace(',', ''))

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
                if self.xcfg.FLICKR["title"] == "":
                    path_filename, title_filename = os.path.split(file)
                    logging.info('path:[%s] filename:[%s] ext=[%s]',
                                 path_filename,
                                 title_filename,
                                 os.path.splitext(title_filename)[1])
                    title_filename = os.path.splitext(title_filename)[0]
                    logging.info('title_name:[%s]', title_filename)
                else:
                    title_filename = self.xcfg.FLICKR["title"]
                    logging.info('title from INI file:[%s]', title_filename)

                # CODING: Check MAX_UPLOAD_ATTEMPTS. Replace with @retry?
                uploadResp = None
                photo_id = None
                ZuploadOK = False
                ZbadFile = False
                ZuploadError = False
                for x in range(0, self.xcfg.MAX_UPLOAD_ATTEMPTS):
                    # Reset variables on each iteration
                    uploadResp = None
                    photo_id = None
                    ZuploadOK = False
                    ZbadFile = False
                    ZuploadError = False
                    logging.warning('Up/Reuploading:[%s/%s attempts].',
                                    x, self.xcfg.MAX_UPLOAD_ATTEMPTS)
                    if x > 0:
                        NP.niceprint('    Reuploading:[{!s}] '
                                     '[{!s}/{!s} attempts].'
                                     .format(strunicodeout(file),
                                             x,
                                             self.xcfg.MAX_UPLOAD_ATTEMPTS))
                    # Upload file to Flickr
                    # replace commas from tags and checksum tags
                    # to avoid tags conflicts
                    try:
                        uploadResp = self.nuflickr.upload(
                            filename=file,
                            fileobj=FileWithCallback(
                                file,
                                callback,
                                self.args.verbose_progress),
                            title=title_filename
                            if self.xcfg.FLICKR["title"] == ""
                            else str(self.xcfg.FLICKR["title"]),
                            description=str(self.xcfg.FLICKR["description"]),
                            tags='{} checksum:{} album:"{}" {}'
                            .format(
                                self.xcfg.FLICKR["tags"],
                                file_checksum,
                                strunicodeout(setName),
                                self.args.tags if self.args.tags else '')
                            .replace(',', ''),
                            is_public=str(self.xcfg.FLICKR["is_public"]),
                            is_family=str(self.xcfg.FLICKR["is_family"]),
                            is_friend=str(self.xcfg.FLICKR["is_friend"])
                        )

                        logging.info('Output for uploadResp:[%s]',
                                     faw.is_good(uploadResp))
                        logging.debug(xml.etree.ElementTree.tostring(
                            uploadResp,
                            encoding='utf-8',
                            method='xml'))

                        if faw.is_good(uploadResp):
                            ZuploadOK = True
                            # Save photo_id returned from Flickr upload
                            photo_id = uploadResp.findall('photoid')[0].text
                            logging.info('  Uploaded file:[%s] '
                                         'Id=[%s]. Check for '
                                         'duplicates/wrong checksum...',
                                         strunicodeout(file),
                                         photo_id)
                            if self.args.verbose:
                                NP.niceprint('  Uploaded file:[{!s}] '
                                             'ID=[{!s}]. Check for '
                                             'duplicates/wrong checksum...'
                                             .format(strunicodeout(file),
                                                     photo_id))

                            break
                        else:
                            ZuploadError = True
                            raise IOError(uploadResp)

                    except (IOError, httplib.HTTPException):
                        niceerror(caught=True,
                                  caughtprefix='+++',
                                  caughtcode='038',
                                  caughtmsg='Caught IOError, HTTP exception',
                                  useniceprint=True,
                                  exceptsysinfo=True)
                        # CODING: Repeat also below on FlickError (!= 5 and 8)
                        # On error, check if exists a photo with
                        # file_checksum
                        logging.error('Sleep 10 and check if file is '
                                      'already uploaded')
                        NP.niceprint('Sleep 10 and check if file is '
                                     'already uploaded')
                        NUTIME.sleep(10)

                        ZisLoaded, ZisCount, photo_id, ZisNoSet = \
                            self.is_already_uploaded(
                                file,
                                file_checksum,
                                setName)
                        logging.warning('is_already_uploaded:[%s] '
                                        'Zcount:[%s] Zpic:[%s] '
                                        'ZisNoSet:[%s]',
                                        ZisLoaded,
                                        ZisCount, photo_id,
                                        ZisNoSet)

                        if ZisCount == 0:
                            ZuploadError = True
                            continue
                        elif ZisCount == 1:
                            ZuploadOK = True
                            ZuploadError = False
                            NP.niceprint('Found, '
                                         'continuing with next image.')
                            logging.warning('Found, '
                                            'continuing with next image.')
                            break
                        elif ZisCount > 1:
                            ZuploadError = True
                            NP.niceprint('More than one file with same '
                                         'checksum/album tag! '
                                         'Any collisions? File: [{!s}]'
                                         .format(strunicodeout(file)))
                            logging.error('More than one file with same '
                                          'checksum/album tag! '
                                          'Any collisions? File: [%s]',
                                          strunicodeout(file))
                            break

                    except flickrapi.exceptions.FlickrError as ex:
                        niceerror(caught=True,
                                  caughtprefix='+++',
                                  caughtcode='040',
                                  caughtmsg='Flickrapi exception on upload',
                                  exceptuse=True,
                                  exceptcode=ex.code,
                                  exceptmsg=ex,
                                  useniceprint=True,
                                  exceptsysinfo=True)
                        # Error code: [5]
                        # Error code: [Error: 5: Filetype was not recognised]
                        # Error code: [8]
                        # Error code: [Error: 8: Filesize was too large]
                        if (format(ex.code) == '5') or (
                                format(ex.code) == '8'):
                            # Badfile
                            ZbadFile = True
                            if not self.args.bad_files:
                                # Break for ATTEMPTS cycle
                                break

                            # self.args.bad_files is True
                            # Add to db the file NOT uploaded
                            # Set locking for when running multiprocessing
                            NP.niceprint('   Log Bad file:[{!s}] due to [{!s}]'
                                         .format(
                                             file,
                                             'Filetype was not recognised'
                                             if (format(ex.code) == '5')
                                             else 'Filesize was too large'))
                            logging.info('Bad file:[%s]', strunicodeout(file))

                            try:
                                self.useDBLock(lock, True)
                                # files_id is autoincrement. No need to mention
                                cur.execute(
                                    'INSERT INTO badfiles '
                                    '( path, md5, last_modified, tagged) '
                                    'VALUES (?, ?, ?, 1)',
                                    (file, file_checksum, last_modified))
                            except lite.Error as err:
                                niceerror(caught=True,
                                          caughtprefix='+++ DB',
                                          caughtcode='041',
                                          caughtmsg='DB error on INSERT: '
                                          '[{!s}]'
                                          .format(err.args[0]),
                                          useniceprint=True)
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
                            NP.niceprint('Sleep 10 and check if file is '
                                         'already uploaded')
                            NUTIME.sleep(10)

                            ZisLoaded, ZisCount, photo_id, ZisNoSet = \
                                self.is_already_uploaded(
                                    file,
                                    file_checksum,
                                    setName)
                            logging.warning('is_already_uploaded:[%s] '
                                            'Zcount:[%s] Zpic:[%s] '
                                            'ZisNoSet:[%s]',
                                            ZisLoaded,
                                            ZisCount, photo_id,
                                            ZisNoSet)

                            if ZisCount == 0:
                                ZuploadError = True
                                continue
                            elif ZisCount == 1:
                                ZuploadOK = True
                                ZuploadError = False
                                NP.niceprint('Found, '
                                             'continuing with next image.')
                                logging.warning('Found, '
                                                'continuing with next image.')
                                break
                            elif ZisCount > 1:
                                ZuploadError = True
                                NP.niceprint('More than one file with same '
                                             'checksum/album tag! '
                                             'Any collisions? File: [{!s}]'
                                             .format(strunicodeout(file)))
                                logging.error('More than one file with same '
                                              'checksum/album tag! '
                                              'Any collisions? File: [%s]',
                                              strunicodeout(file))
                                break

                    finally:
                        con.commit()

                logging.debug('After CYCLE '
                              'Up/Reuploading:[%s/%s attempts].',
                              x, self.xcfg.MAX_UPLOAD_ATTEMPTS)

                # Max attempts reached
                if (not ZuploadOK) and (
                        x == (self.xcfg.MAX_UPLOAD_ATTEMPTS - 1)):
                    NP.niceprint('Reached max attempts to upload. Skipping '
                                 'file: [{!s}]'.format(strunicodeout(file)))
                    logging.error('Reached max attempts to upload. Skipping '
                                  'file: [%s]', strunicodeout(file))
                # Error
                elif (not ZuploadOK) and ZuploadError:
                    NP.niceprint('Error occurred while uploading. Skipping '
                                 'file:[{!s}]'
                                 .format(strunicodeout(file)))
                    logging.error('Error occurred while uploading. Skipping '
                                  'file:[%s]',
                                  strunicodeout(file))
                # Bad file
                elif (not ZuploadOK) and ZbadFile:
                    NP.niceprint('       Bad file:[{!s}]'
                                 .format(strunicodeout(file)))
                # Successful update
                elif ZuploadOK:
                    NP.niceprint('Successful file:[{!s}]'
                                 .format(strunicodeout(file)))

                    assert photo_id is not None, NP.niceassert(
                        'photo_id None:[{!s}]'
                        .format(strunicodeout(file)))
                    # Save file_id: from uploadResp or is_already_uploaded
                    file_id = photo_id

                    # Insert into DB files
                    dbInsertIntoFiles(lock, file_id, file,
                                      file_checksum, last_modified)

                    # Update the Video Date Taken
                    self.updatedVideoDate(file_id, file, last_modified)

                    success = True

            # C) File loaded. Recorded on DB. Look for changes...
            elif self.xcfg.MANAGE_CHANGES:
                # We have a file from disk which is found on the database
                # and is also on flickr but its set on flickr is not defined.
                # So we need to reset the local datbase set_id so that it will
                # be later assigned once we run createSets()
                logging.debug('str(row[1]) == str(isfile_id:[%s])'
                              'row[1]:[%s]=>type:[%s] '
                              'isfile_id:[%s]=>type:[%s]',
                              str(row[1]) == str(isfile_id),
                              row[1], type(row[1]),
                              isfile_id, type(isfile_id))
                # C) File loaded. Recorded on DB. Manage changes & Flickr set.
                if (isLoaded and
                        isNoSet and
                        (row is not None) and
                        (str(row[1]) == str(isfile_id))):

                    logging.info('Will UPDATE files SET set_id = null '
                                 'for pic:[%s] ', row[1])
                    try:
                        self.useDBLock(lock, True)
                        cur.execute('UPDATE files SET set_id = null '
                                    'WHERE files_id = ?', (row[1],))
                    except lite.Error as err:
                        niceerror(caught=True,
                                  caughtprefix='+++ DB',
                                  caughtcode='045',
                                  caughtmsg='DB error on UPDATE: [{!s}]'
                                  .format(err.args[0]),
                                  useniceprint=True)
                    finally:
                        con.commit()
                        self.useDBLock(lock, False)

                    logging.info('Did UPDATE files SET set_id = null '
                                 'for pic:[%s]',
                                 row[1])

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
                    logging.warning('CHANGES row[6]=[%s-(%s)]',
                                    NUTIME.strftime(
                                        UPLDR_K.TimeFormat,
                                        NUTIME.localtime(row[6])),
                                    row[6])
                    if row[6] is None:
                        # Update db the last_modified time of file

                        # Control for when running multiprocessing set locking
                        self.useDBLock(lock, True)
                        cur.execute('UPDATE files SET last_modified = ? '
                                    'WHERE files_id = ?', (last_modified,
                                                           row[1]))
                        con.commit()
                        self.useDBLock(lock, False)

                    logging.warning('CHANGES row[6]!=last_modified: [%s]',
                                    row[6] != last_modified)
                    if row[6] != last_modified:
                        # Update db both the new file/md5 and the
                        # last_modified time of file by by calling replacePhoto

                        if file_checksum is None:
                            file_checksum = md5checksum(file)
                        if file_checksum != str(row[4]):
                            self.replacePhoto(lock, file, row[1], row[4],
                                              file_checksum, last_modified,
                                              cur, con)
                except lite.Error as err:
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='050',
                              caughtmsg='Error: UPDATE files '
                              'SET last_modified: [{!s}]'
                              .format(err.args[0]),
                              useniceprint=True)

                    self.useDBLock(lock, False)
                    if self.args.processes and self.args.processes > 0:
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
    #                     (if self.args.processes = 0 then lock can be None
    #                     as it is not used)
    #   file            = file to be uploaded to replace existing file
    #   file_id         = ID of the photo being replaced
    #   oldfile_md5     = Old file MD5 (required to update checksum tag
    #                     on Flikr)
    #   file_md5        = New file MD5
    #   last_modified   = date/time last modification of the file to update
    #                     database
    #   cur             = current cursor for updating Database
    #   con             = current DB connection
    #
    def replacePhoto(self, lock, file, file_id,
                     oldfile_md5, file_md5, last_modified, cur, con):
        """ replacePhoto
        lock            = parameter for multiprocessing control of access to DB
                          (if self.args.processes = 0 then lock can be None
                          as it is not used)
        file            = file to be uploaded to replace existing file
        file_id         = ID of the photo being replaced
        oldfile_md5     = Old file MD5 (required to update checksum tag
                          on Flikr)
        file_md5        = New file MD5
        last_modified   = date/time last modification of the file to update
                          database
        cur             = current cursor for updating Database
        con             = current DB connection
        """

        if self.args.dry_run:
            NP.niceprint('Dry Run Replace:[{!s}]...'
                         .format(strunicodeout(file)))
            return True

        if self.args.verbose:
            NP.niceprint(' Replacing file:[{!s}]...'
                         .format(strunicodeout(file)))

        success = False
        try:
            # nuflickr.replace accepts both a filename and a file object.
            # when using filenames with unicode characters
            #    - the flickrapi seems to fail with filename
            # so I've used photo FileObj and filename='dummy'
            photo = open(file.encode('utf-8'), 'rb')\
                if NP.is_str_unicode(file)\
                else open(file, 'rb')
            logging.debug('photo:[%s] type(photo):[%s]', photo, type(photo))

            for x in range(0, self.xcfg.MAX_UPLOAD_ATTEMPTS):
                res_add_tag = None
                res_get_info = None
                replaceResp = None

                try:
                    if x > 0:
                        NP.niceprint('   Re-Replacing:'
                                     '[{!s}]...[{!s}/{!s} attempts].'
                                     .format(strunicodeout(file),
                                             x,
                                             self.xcfg.MAX_UPLOAD_ATTEMPTS))

                    # Use fileobj with filename='dummy'to accept unicode file.
                    replaceResp = self.nuflickr.replace(
                        filename='dummy',
                        fileobj=photo,
                        # fileobj=FileWithCallback(
                        #     file, callback, self.args.verbose_progress),
                        photo_id=file_id
                    )

                    logging.debug('Output for replaceResp:')
                    logging.debug(xml.etree.ElementTree.tostring(
                        replaceResp,
                        encoding='utf-8',
                        method='xml'))
                    logging.info('replaceResp:[%s]', faw.is_good(replaceResp))

                    if faw.is_good(replaceResp):
                        # Add checksum tag with new md5
                        get_success, res_add_tag, get_errcode = \
                            faw.flickrapi_fn(
                                self.nuflickr.photos.addTags, (),
                                dict(photo_id=file_id,
                                     tags='checksum:{}'.format(file_md5)),
                                2, 2, False, caughtcode='055')

                        if get_success and get_errcode == 0:
                            # Gets Flickr file info to obtain all tags
                            # in order to delete checksum tag of old md5
                            gi_success, res_get_info, gi_errcode = \
                                faw.flickrapi_fn(
                                    self.nuflickr.photos.getInfo, (),
                                    dict(photo_id=file_id),
                                    2, 2, False, caughtcode='056')

                            if gi_success and gi_errcode == 0:
                                # find tag checksum with old md5 to delete it
                                tag_id = None
                                for tag in res_get_info\
                                    .find('photo')\
                                    .find('tags')\
                                        .findall('tag'):
                                    if (tag.attrib['raw'] ==
                                            'checksum:{}'.format(oldfile_md5)):
                                        tag_id = tag.attrib['id']
                                        logging.info('   Found tag_id:[%s]',
                                                     tag_id)
                                        break
                                if not tag_id:
                                    NP.niceprint(' Can\'t find tag:[{!s}]'
                                                 'for file [{!s}]'
                                                 .format(tag_id, file_id))
                                    # break from attempting to update tag_id
                                    break
                                else:
                                    # delete tag_id with old Md5
                                    logging.info('Removing tag_id:[%s]',
                                                 tag_id)
                                    if self.photos_remove_tag(tag_id):
                                        NP.niceprint('    Tag removed:[{!s}]'
                                                     .format(
                                                         strunicodeout(file)))
                                    else:
                                        NP.niceprint('Tag Not removed:[{!s}]'
                                                     .format(
                                                         strunicodeout(file)))

                    break
                # Exceptions for flickr.upload function call handled on the
                # outer try/except.
                except (IOError, ValueError, httplib.HTTPException):
                    niceerror(caught=True,
                              caughtprefix='+++',
                              caughtcode='060',
                              caughtmsg='Caught IOError, ValueError, '
                              'HTTP exception',
                              useniceprint=True,
                              exceptsysinfo=True)
                    logging.error('Sleep 10 and try to replace again.')
                    NP.niceprint('Sleep 10 and try to replace again.')
                    NUTIME.sleep(10)

                    if x == self.xcfg.MAX_UPLOAD_ATTEMPTS - 1:
                        raise ValueError('Reached maximum number of attempts '
                                         'to replace, skipping')
                    continue

            if (not faw.is_good(replaceResp)) or \
                (not faw.is_good(res_add_tag)) or \
                    (not faw.is_good(res_get_info)):
                NP.niceprint('Issue replacing:[{!s}]'
                             .format(strunicodeout(file)))
                logging.error('Issue replacing:[{!s}]'
                              .format(strunicodeout(file)))

            if not faw.is_good(replaceResp):
                raise IOError(replaceResp)

            if not faw.is_good(res_add_tag):
                raise IOError(res_add_tag)

            if not faw.is_good(res_get_info):
                raise IOError(res_get_info)

            NP.niceprint('  Replaced file:[{!s}].'
                         .format(strunicodeout(file)))
            logging.warning('  Replaced file:[{!s}].'
                            .format(strunicodeout(file)))

            # Update the db the file uploaded
            # Control for when running multiprocessing set locking
            self.useDBLock(lock, True)
            try:
                cur.execute('UPDATE files SET md5 = ?,last_modified = ? '
                            'WHERE files_id = ?',
                            (file_md5, last_modified, file_id))
                con.commit()
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='070',
                          caughtmsg='DB error on UPDATE: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
            finally:
                # Release DB lock if running in multiprocessing mode
                self.useDBLock(lock, False)

            # Update the Video Date Taken
            self.updatedVideoDate(file_id, file, last_modified)

            success = True

        except flickrapi.exceptions.FlickrError as ex:
            niceerror(caught=True,
                      caughtprefix='+++',
                      caughtcode='080',
                      caughtmsg='Flickrapi exception on upload(or)replace',
                      exceptuse=True,
                      exceptcode=ex.code,
                      exceptmsg=ex,
                      useniceprint=True,
                      exceptsysinfo=True)
            # Error: 8: Videos can't be replaced
            if ex.code == 8:
                NP.niceprint('..Video replace:[{!s}]'
                             .format(strunicodeout(file)),
                             fname='replace')
                logging.error('Videos can\'t be replaced, delete/uploading...')
                xrow = [file_id, file]
                logging.debug('delete/uploading '
                              'xrow[0].files_id=[%s]'
                              'xrow[1].file=[%s]',
                              xrow[0], strunicodeout(xrow[1]))
                if self.deleteFile(xrow, cur, lock):
                    NP.niceprint('..Video deleted:[{!s}]'
                                 .format(strunicodeout(file)),
                                 fname='replace')
                    logging.warning('Delete for replace succeed!')
                    if self.uploadFile(lock, file):
                        NP.niceprint('.Video replaced:[{!s}]'
                                     .format(strunicodeout(file)),
                                     fname='replace')
                        logging.warning('Upload for replace succeed!')
                    else:
                        NP.niceprint('..Failed upload:[{!s}]'
                                     .format(strunicodeout(file)),
                                     fname='replace')
                        logging.error('Upload for replace failed!')
                else:
                    NP.niceprint('..Failed delete:[{!s}]'
                                 .format(strunicodeout(file)),
                                 fname='replace')
                    logging.error('Delete for replace failed!')

        except lite.Error as err:
            niceerror(caught=True,
                      caughtprefix='+++ DB',
                      caughtcode='081',
                      caughtmsg='DB error: [{!s}]'.format(err.args[0]),
                      useniceprint=True)
            # Release the lock on error.
            self.useDBLock(lock, False)
            success = False
        except BaseException:
            niceerror(caught=True,
                      caughtprefix='+++',
                      caughtcode='082',
                      caughtmsg='Caught exception in replacePhoto',
                      exceptsysinfo=True)
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
            con = lite.connect(self.xcfg.DB_PATH)
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
                    if row is not None:
                        nucur.execute("SELECT set_id FROM files "
                                      "WHERE set_id = ?",
                                      (row[0],))
                        rows = nucur.fetchall()
                        if len(rows) == 1:
                            NP.niceprint('File is the last of the set, '
                                         'deleting the set ID: [{!s}]'
                                         .format(str(row[0])))
                            nucur.execute("DELETE FROM sets WHERE set_id = ?",
                                          (row[0],))
                    # Delete file record from the local db
                    logging.debug('deleteFile.dbDeleteRecordLocalDB: '
                                  'DELETE FROM files WHERE files_id = %s',
                                  file[0])
                    nucur.execute("DELETE FROM files WHERE files_id = ?",
                                  (file[0],))
                except lite.Error as err:
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='087',
                              caughtmsg='DB error on SELECT(or)DELETE: [{!s}]'
                              .format(err.args[0]),
                              useniceprint=True,
                              exceptsysinfo=True)
                except BaseException:
                    niceerror(caught=True,
                              caughtprefix='+++',
                              caughtcode='088',
                              caughtmsg='Caught exception in '
                              'dbDeleteRecordLocalDB',
                              useniceprint=True,
                              exceptsysinfo=True)
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

        if self.args.dry_run:
            NP.niceprint('Dry Run Deleting file:[{!s}]'
                         .format(strunicodeout(file[1])))
            return True

        NP.niceprint('  Deleting file:[{!s}]'.format(strunicodeout(file[1])))

        get_success, _, get_errcode = faw.flickrapi_fn(
            self.nuflickr.photos.delete, (),
            dict(photo_id=str(file[0])),
            2, 2, False, caughtcode='111')

        success = False
        if ((get_success and get_errcode == 0) or
                (not get_success and get_errcode == 1)):
            # Error: 1: File already removed from Flickr

            dbDeleteRecordLocalDB(lock, file)
            NP.niceprint('   Deleted file:[{!s}]'
                         .format(strunicodeout(file[1])))
            success = True
        else:
            niceerror(caught=True,
                      caughtprefix='xxx',
                      caughtcode='090',
                      caughtmsg='Failed to delete photo (deleteFile)',
                      useniceprint=True)

        return success

    # -------------------------------------------------------------------------
    # logSetCreation
    #
    #   Creates on flickrdb local database a SetName(Album)
    #
    def logSetCreation(self, lock, setId, setName, primaryPhotoId, cur, con):
        """ logSetCreation

        Creates on flickrdb local database a SetName(Album)
        with Primary photo Id.

        Assigns Primary photo Id to set on the local DB.

        Also updates photo DB entry with its set_id
        """

        logging.warning('  Add set to DB:[%s]', strunicodeout(setName))
        if self.args.verbose:
            NP.niceprint('  Add set to DB:[{!s}]'
                         .format(strunicodeout(setName)))

        try:
            # Acquire DBlock if in multiprocessing mode
            self.useDBLock(lock, True)
            cur.execute('INSERT INTO sets (set_id, name, primary_photo_id) '
                        'VALUES (?,?,?)',
                        (setId, setName, primaryPhotoId))
        except lite.Error as err:
            niceerror(caught=True,
                      caughtprefix='+++ DB',
                      caughtcode='094',
                      caughtmsg='DB error on INSERT: [{!s}]'
                      .format(err.args[0]),
                      useniceprint=True)
        finally:
            con.commit()
            # Release DBlock if in multiprocessing mode
            self.useDBLock(lock, False)

        try:
            # Acquire DBlock if in multiprocessing mode
            self.useDBLock(lock, True)
            cur.execute('UPDATE files SET set_id = ? WHERE files_id = ?',
                        (setId, primaryPhotoId))
        except lite.Error as err:
            niceerror(caught=True,
                      caughtprefix='+++ DB',
                      caughtcode='095',
                      caughtmsg='DB error on UPDATE: [{!s}]'
                      .format(err.args[0]),
                      useniceprint=True)
        finally:
            con.commit()
            # Release DBlock if in multiprocessing mode
            self.useDBLock(lock, False)

        return True

    # -------------------------------------------------------------------------
    # run
    #
    # run in daemon mode. runs upload every SLEEP_TIME
    #
    def run(self):
        """ run
            Run in daemon mode. runs upload every SLEEP_TIME seconds.
        """

        logging.warning('Daemon mode run.')
        NP.niceprint('Daemon mode run.')
        while True:
            NP.niceprint(' Daemon mode go:[{!s}]'
                         .format(NUTIME.strftime(
                             UPLDR_K.TimeFormat)))
            # run upload
            self.upload()
            NP.niceprint('Daemon mode out:[{!s}]'
                         .format(str(NUTIME.asctime(time.localtime()))))
            NP.niceprint('    Daemon wait:[{!s}] seconds.'
                         .format(self.xcfg.SLEEP_TIME))
            logging.warning('    Daemon wait:[%s] seconds.',
                            self.xcfg.SLEEP_TIME)
            NUTIME.sleep(self.xcfg.SLEEP_TIME)

    # ---------------------------------------------------------------------
    # fn_addFilesToSets
    #
    # Processing function for adding files to set in multiprocessing mode
    #
    def fn_addFilesToSets(self, lockDB, running, mutex, sfiles, cTotal, cur):
        """ fn_addFilesToSets
        """

        # CODING Use a different conn and cur to avoid error +++096
        fn_con = lite.connect(self.xcfg.DB_PATH)
        fn_con.text_factory = str

        with fn_con:
            acur = fn_con.cursor()
            for filepic in sfiles:
                # filepic[1] = path for the file from table files
                # filepic[2] = set_id from files table
                setName = set_name_from_file(filepic[1],
                                             self.xcfg.FILES_DIR,
                                             self.xcfg.FULL_SET_NAME)
                aset = None
                try:
                    # Acquire DBlock if in multiprocessing mode
                    self.useDBLock(lockDB, True)
                    acur.execute('SELECT set_id, name '
                                 'FROM sets WHERE name = ?',
                                 (setName,))
                    aset = acur.fetchone()
                except lite.Error as err:
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='098',
                              caughtmsg='DB error on DB create: [{!s}]'
                              .format(err.args[0]),
                              useniceprint=True,
                              exceptsysinfo=True)
                finally:
                    # Release DBlock if in multiprocessing mode
                    self.useDBLock(lockDB, False)

                if aset is not None:
                    setId = aset[0]

                    NP.niceprint('Add file to set:[{!s}] '
                                 'set:[{!s}] setId=[{!s}]'
                                 .format(strunicodeout(filepic[1]),
                                         strunicodeout(setName),
                                         setId))
                    self.addFileToSet(lockDB, setId, filepic, acur)
                else:
                    NP.niceprint('Not able to assign pic to set')
                    logging.error('Not able to assign pic to set')

                logging.debug('===Multiprocessing=== in.mutex.acquire(w)')
                mutex.acquire()
                running.value += 1
                xcount = running.value
                mutex.release()
                logging.info('===Multiprocessing=== out.mutex.release(w)')

                # Show number of files processed so far
                NP.niceprocessedfiles(xcount, cTotal, False)

        # Closing DB connection
        if fn_con is not None:
            fn_con.close()
    # -------------------------------------------------------------------------

    # -------------------------------------------------------------------------
    # createSets
    #
    def createSets(self):
        """ createSets

            Creates Sets (Album) in Flickr
        """
        # [FIND SETS] Find sets to be created
        # [PRIMARY PIC] For each set found, determine the primary picture
        # [CREATE SET] Create Sets wiht primary picture:
        #   CODING: what if it is not found?
        # [WORK THRU PICS] Split work and add files to set in multi-processing

        # ---------------------------------------------------------------------
        # Local Variables
        #
        #   slockDB     = multiprocessing Lock for access to Database
        #   smutex      = multiprocessing mutex for access to value srunning
        #   srunning    = multiprocessing Value to count processed photos
        slockDB = None
        smutex = None
        srunning = None

        NP.niceprint('*****Creating Sets*****')

        if self.args.dry_run:
            return True

        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str
        con.create_function("getSet", 3, set_name_from_file)
        # Enable traceback return from create_function.
        lite.enable_callback_tracebacks(True)

        with con:
            cur = con.cursor()

            try:
                # List of Sets to be created
                cur.execute('SELECT DISTINCT getSet(path, ?, ?) '
                            'FROM files WHERE getSet(path, ?, ?) '
                            'NOT IN (SELECT name FROM sets)',
                            (self.xcfg.FILES_DIR, self.xcfg.FULL_SET_NAME,
                             self.xcfg.FILES_DIR, self.xcfg.FULL_SET_NAME,))

                setsToCreate = cur.fetchall()
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='145',
                          caughtmsg='DB error on DB create: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True,
                          exceptsysinfo=True)
                raise

            for aset in setsToCreate:
                # aset[0] = setName
                # Find Primary photo
                setName = strunicodeout(aset[0])
                cur.execute('SELECT MIN(files_id), path '
                            'FROM files '
                            'WHERE set_id is NULL '
                            'AND getSet(path, ?, ?) = ?',
                            (self.xcfg.FILES_DIR,
                             self.xcfg.FULL_SET_NAME,
                             setName,))
                primaryPic = cur.fetchone()

                # primaryPic[0] = files_id from files table
                setId = self.createSet(slockDB,
                                       setName, primaryPic[0],
                                       cur, con)
                NP.niceprint('Created the set:[{!s}] '
                             'setId=[{!s}] '
                             'primaryId=[{!s}]'
                             .format(strunicodeout(setName),
                                     setId,
                                     primaryPic[0]))

            cur.execute('SELECT files_id, path, set_id '
                        'FROM files '
                        'WHERE set_id is NULL')
            files = cur.fetchall()
            cur.close()

            # running in multi processing mode
            if self.args.processes and self.args.processes > 0:
                logging.debug('Running [%s] processes pool.',
                              self.args.processes)
                logging.debug('__name__:[%s] to prevent recursive calling)!',
                              __name__)
                cur = con.cursor()

                # To prevent recursive calling, check if __name__ == '__main__'
                # if __name__ == '__main__':
                mp.mprocessing(self.args.verbose,
                               self.args.verbose_progress,
                               self.args.processes,
                               slockDB,
                               srunning,
                               smutex,
                               files,
                               self.fn_addFilesToSets,
                               cur)
                con.commit()

            # running in single processing mode
            else:
                cur = con.cursor()

                for filepic in files:
                    # filepic[1] = path for the file from table files
                    # filepic[2] = set_id from files table
                    setName = set_name_from_file(filepic[1],
                                                 self.xcfg.FILES_DIR,
                                                 self.xcfg.FULL_SET_NAME)

                    cur.execute('SELECT set_id, name '
                                'FROM sets WHERE name = ?',
                                (setName,))
                    aset = cur.fetchone()
                    if aset is not None:
                        setId = aset[0]

                        NP.niceprint('Add file to set:[{!s}] '
                                     'set:[{!s}] setId=[{!s}]'
                                     .format(strunicodeout(filepic[1]),
                                             strunicodeout(setName),
                                             setId))
                        self.addFileToSet(slockDB, setId, filepic, cur)
                    else:
                        NP.niceprint('Not able to assign pic to set')
                        logging.error('Not able to assign pic to set')

        # Closing DB connection
        if con is not None:
            con.close()
        NP.niceprint('*****Completed creating sets*****')

    # -------------------------------------------------------------------------
    # addFiletoSet
    #
    def addFileToSet(self, lock, setId, file, cur):
        """ addFileToSet

            Adds a file to set...

            lock  = for multiprocessing access control to DB
            setID = set
            file  = file is a list with file[0]=id, file[1]=path
            cur   = cursor for updating local DB
        """

        if self.args.dry_run:
            return True

        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str
        bcur = con.cursor()

        get_success, _, get_errcode = faw.flickrapi_fn(
            self.nuflickr.photosets.addPhoto, (),
            dict(photoset_id=str(setId),
                 photo_id=str(file[0])),
            2, 0, False, caughtcode='146')

        if get_success and get_errcode == 0:
            NP.niceprint(' Added file/set:[{!s}] setId:[{!s}]'
                         .format(strunicodeout(file[1]),
                                 strunicodeout(setId)))

            try:
                # Acquire DBlock if in multiprocessing mode
                self.useDBLock(lock, True)
                bcur.execute("UPDATE files SET set_id = ? "
                             "WHERE files_id = ?",
                             (setId, file[0]))
                con.commit()
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='096',
                          caughtmsg='DB error on UPDATE files: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
            finally:
                # Release DBlock if in multiprocessing mode
                self.useDBLock(lock, False)
        elif not get_success and get_errcode == 1:
            # Error: 1: Photoset not found
            NP.niceprint('Photoset not found, creating new set...')
            setName = set_name_from_file(file[1],
                                         self.xcfg.FILES_DIR,
                                         self.xcfg.FULL_SET_NAME)
            # CODING: cur vs bcur! Check!
            self.createSet(lock, setName, file[0], cur, con)
        elif not get_success and get_errcode == 3:
            # Error: 3: Photo already in set
            try:
                NP.niceprint('Photo already in set... updating DB'
                             'set_id=[{!s}] photo_id=[{!s}]'
                             .format(setId, file[0]))
                # Acquire DBlock if in multiprocessing mode
                self.useDBLock(lock, True)
                bcur.execute('UPDATE files SET set_id = ? '
                             'WHERE files_id = ?', (setId, file[0]))
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='110',
                          caughtmsg='DB error on UPDATE SET: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
            finally:
                con.commit()
                # Release DBlock if in multiprocessing mode
                self.useDBLock(lock, False)
        else:
            niceerror(caught=True,
                      caughtprefix='xxx',
                      caughtcode='097',
                      caughtmsg='Failed add photo to set (addFiletoSet)',
                      useniceprint=True)

        # Closing DB connection
        if con is not None and con in locals():
            niceerror(caught=True,
                      caughtprefix='+++ DB',
                      caughtcode='122',
                      caughtmsg='Closing DB connection on addFileToSet',
                      useniceprint=True)
            con.close()

    # -------------------------------------------------------------------------
    # createSet
    #
    # Creates an Album in Flickr.
    #
    def createSet(self, lock, setName, primaryPhotoId, cur, con):
        """ createSet

        Creates an Album in Flickr.
        Calls logSetCreation to create Album on local database.
        """

        logging.info('   Creating set:[%s]', strunicodeout(setName))
        NP.niceprint('   Creating set:[{!s}]'.format(strunicodeout(setName)))

        if self.args.dry_run:
            return True

        get_success, get_result, get_errcode = faw.flickrapi_fn(
            self.nuflickr.photosets.create, (),
            dict(title=setName,
                 primary_photo_id=str(primaryPhotoId)),
            3, 10, True, caughtcode='124')

        success = False
        if get_success and get_errcode == 0:
            logging.warning('get_result["photoset"]["id"]:[%s]',
                            get_result.find('photoset').attrib['id'])
            self.logSetCreation(lock,
                                get_result.find('photoset').attrib['id'],
                                setName,
                                primaryPhotoId,
                                cur,
                                con)
            return get_result.find('photoset').attrib['id']
        elif not get_success and get_errcode == 2:
            # Add to db the file NOT uploaded
            # A set on local DB (with primary photo) failed to be created on
            # FLickr because Primary Photo is not available.
            # Sets (possibly from previous runs) exist on local DB but the pics
            # are not loaded into Flickr.
            # FlickrError(u'Error: 2: Invalid primary photo id (nnnnnn)
            NP.niceprint('Primary photo [{!s}] for Set [{!s}] '
                         'does not exist on Flickr. '
                         'Probably deleted from Flickr but still '
                         'on local db and local file.'
                         .format(primaryPhotoId,
                                 strunicodeout(setName)))
            logging.error(
                'Primary photo [%s] for Set [%s] does not exist on Flickr.'
                ' Probably deleted from Flickr but still on local db '
                'and local file.',
                primaryPhotoId,
                strunicodeout(setName))
            success = False
        else:
            # CODING: Revise code/message output
            niceerror(exceptuse=False,
                      exceptcode=get_result['code']
                      if 'code' in get_result
                      else get_result,
                      exceptmsg=get_result['message']
                      if 'message' in get_result
                      else get_result,
                      useniceprint=True)
            success = False

        return success

    # -------------------------------------------------------------------------
    # setupDB
    #
    # Creates the control database
    #
    def setupDB(self):
        """ setupDB

            Creates the control database
        """

        NP.niceprint('Setting up database:[{!s}]'.format(self.xcfg.DB_PATH))
        con = None
        try:
            con = lite.connect(self.xcfg.DB_PATH)
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
            if row[0] == 0:
                # Database version 1 <=========================DB VERSION: 1===
                NP.niceprint('Adding last_modified column to database')
                cur = con.cursor()
                cur.execute('PRAGMA user_version="1"')
                cur.execute('ALTER TABLE files ADD COLUMN last_modified REAL')
                con.commit()
                # obtain new version to continue updating database
                cur = con.cursor()
                cur.execute('PRAGMA user_version')
                row = cur.fetchone()
            if row[0] == 1:
                # Database version 2 <=========================DB VERSION: 2===
                # Cater for badfiles
                NP.niceprint('Adding table badfiles to database')
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
            if row[0] == 2:
                NP.niceprint('Database version: [{!s}]'.format(row[0]))
                # Database version 3 <=========================DB VERSION: 3===
                NP.niceprint('Adding album tags to pics already uploaded... ')
                if self.addAlbumsMigrate():
                    NP.niceprint('Successfully added album tags to pics '
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
                    NP.niceprint('Failed adding album tags to pics '
                                 'on upload. Not updating Database version.'
                                 'Please check logs, correct, and retry.',
                                 fname='addAlbumsMigrate')

            if row[0] == 3:
                NP.niceprint('Database version: [{!s}]'.format(row[0]))
                # Database version 4 <=========================DB VERSION: 4===
                # ...for future use!
            # Closing DB connection
            if con is not None:
                con.close()
        except lite.Error as err:
            niceerror(caught=True,
                      caughtprefix='+++ DB',
                      caughtcode='145',
                      caughtmsg='DB error on DB create: [{!s}]'
                      .format(err.args[0]),
                      useniceprint=True)

            if con is not None:
                con.close()
            sys.exit(6)
        finally:
            # Closing DB connection
            if con is not None:
                con.close()

        NP.niceprint('Completed database setup')

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
        NP.niceprint('Cleaning up badfiles table from the database: [{!s}]'
                     .format(self.xcfg.DB_PATH))
        con = None
        try:
            con = lite.connect(self.xcfg.DB_PATH)
            con.text_factory = str
            cur = con.cursor()
            cur.execute('PRAGMA user_version')
            row = cur.fetchone()
            if row[0] >= 2:
                # delete from badfiles table and reset SEQUENCE
                NP.niceprint('Deleting from badfiles table. '
                             'Reseting sequence.')
                try:
                    cur.execute('DELETE FROM badfiles')
                    cur.execute('DELETE FROM SQLITE_SEQUENCE '
                                'WHERE name="badfiles"')
                    con.commit()
                except lite.Error as err:
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='147',
                              caughtmsg='DB error on SELECT FROM '
                              'badfiles: [{!s}]'
                              .format(err.args[0]),
                              useniceprint=True)
                    raise
            else:
                NP.niceprint('Wrong DB version. Expected 2 or higher '
                             'and not:[{!s}]'.format(row[0]))
            # Closing DB connection
            if con is not None:
                con.close()
        except lite.Error as err:
            niceerror(caught=True,
                      caughtprefix='+++ DB',
                      caughtcode='148',
                      caughtmsg='DB error on SELECT: [{!s}]'
                      .format(err.args[0]),
                      useniceprint=True)
            if con is not None:
                con.close()
            sys.exit(7)
        finally:
            NP.niceprint('Completed cleaning up badfiles table '
                         'from the database.')

        # Closing DB connection
        if con is not None:
            con.close()

    # -------------------------------------------------------------------------
    # removeUselessSetsTable
    #
    # Method to clean unused sets (Sets are Albums)
    #
    def removeUselessSetsTable(self):
        """ removeUselessSetsTable

        Remove unused Sets (Sets not listed on Flickr) form local DB
        """
        NP.niceprint('*****Removing empty Sets from DB*****')
        if self.args.dry_run:
            return True

        con = lite.connect(self.xcfg.DB_PATH)
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
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='150',
                          caughtmsg='DB error SELECT FROM sets: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
            finally:
                # Release DB lock if running in multiprocessing mode
                # self.useDBLock( lock, False)
                pass

            for row in unusedsets:
                if self.args.verbose:
                    NP.niceprint('Removing set [{!s}] ({!s}).'
                                 .format(strunicodeout(row[0]),
                                         strunicodeout(row[1])))

                try:
                    # Acquire DB lock if running in multiprocessing mode
                    # self.useDBLock( lock, True)
                    cur.execute("DELETE FROM sets WHERE set_id = ?", (row[0],))
                except lite.Error as err:
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='160',
                              caughtmsg='DB error DELETE FROM sets: [{!s}]'
                              .format(err.args[0]),
                              useniceprint=True)
                finally:
                    # Release DB lock if running in multiprocessing mode
                    # self.useDBLock( lock, False)
                    pass

            con.commit()

        # Closing DB connection
        if con is not None:
            con.close()
        NP.niceprint('*****Completed removing empty Sets from DB*****')

    # -------------------------------------------------------------------------
    # Display Sets
    #
    # CODING: Not being used!
    def displaySets(self):
        """ displaySets

        Prints the list of sets/albums recorded on the local database
        """
        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str
        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT set_id, name FROM sets")
                allsets = cur.fetchall()
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='163',
                          caughtmsg='DB error on SELECT FROM sets: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
            for row in allsets:
                NP.niceprint('Set: [{!s}] ({!s})'.format(str(row[0]), row[1]))

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
        """ getFlickrSets

            Gets list of FLickr Sets (Albums) and populates
            local DB accordingly
        """

        NP.niceprint('*****Adding Flickr Sets to DB*****')
        if self.args.dry_run:
            return True

        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str
        cur = con.cursor()

        get_success, get_result, get_errcode = faw.flickrapi_fn(
            self.nuflickr.photosets.getList, (),
            dict(),
            2, 0, False, caughtcode='166')

        # Output format of photosets_getList:
        #
        # sets.find('photosets').attrib['cancreate'] => '1'
        #
        # set0 = sets.find('photosets').findall('photoset')[0]
        # +-------------------------------+-----------+
        # | variable                      | value     |
        # +-------------------------------+-----------+
        # | set0.attrib['id']             | u'5'      |
        # | set0.attrib['primary']        | u'2483'   |
        # | set0.attrib['secret']         | u'abcdef' |
        # | set0.attrib['server']         | u'8'      |
        # | set0.attrib['photos']         | u'4'      |
        # | set0.title[0].text            | u'Test'   |
        # | set0.description[0].text      | u'foo'    |
        # | set0.find('title').text       | 'Test'    |
        # | set0.find('description').text | 'foo'     |
        # +-------------------------------+-----------+
        #
        # ... and similar for set1 ...

        if get_success and get_errcode == 0:
            for aset in get_result.find('photosets').findall('photoset'):
                logging.debug('Output for aset: %s',
                              xml.etree.ElementTree.tostring(aset,
                                                             encoding='utf-8',
                                                             method='xml'))
                setId = aset.attrib['id']
                setName = aset.find('title').text
                primaryPhotoId = aset.attrib['primary']

                if self.args.verbose:
                    NP.niceprint('  Add Set to DB:[{!s}] setId=[{!s}] '
                                 'primaryId=[{!s}]'
                                 .format('None'
                                         if setName is None
                                         else strunicodeout(setName),
                                         setId,
                                         primaryPhotoId))

                # On ocasions flickr returns a setName (title) as None.
                # For instance, while simultaneously performing massive
                # delete operation on flickr.
                logging.info('Searching on DB for setId:[%s] '
                             'setName:[%s] primaryPhotoId:[%s]',
                             setId,
                             'None'
                             if setName is None
                             else strunicodeout(setName),
                             primaryPhotoId)

                logging.debug('SELECT set_id FROM sets WHERE set_id = "%s"',
                              setId)
                try:
                    cur.execute("SELECT set_id FROM sets "
                                "WHERE set_id = '" + setId + "'")
                    foundSets = cur.fetchone()
                    logging.info('Output for foundSets is [%s]',
                                 'None' if foundSets is None else foundSets)
                except lite.Error as err:
                    niceerror(caught=True,
                              caughtprefix='+++ DB',
                              caughtcode='164',
                              caughtmsg='DB error on SELECT FROM '
                              'sets: [{!s}]'
                              .format(err.args[0]),
                              useniceprint=True)

                if foundSets is None:
                    logging.info('Adding set [%s] (%s) '
                                 'with primary photo [%s].',
                                 setId,
                                 'None'
                                 if setName is None
                                 else strunicodeout(setName),
                                 primaryPhotoId)
                    try:
                        logging.debug('INSERT INTO sets (set_id, name, '
                                      'primary_photo_id) VALUES (%s,%s,%s)',
                                      setId,
                                      strunicodeout(setName),
                                      primaryPhotoId)
                        cur.execute('INSERT INTO sets (set_id, name, '
                                    'primary_photo_id) VALUES (?,?,?)',
                                    (setId, setName, primaryPhotoId))
                        con.commit()

                    except lite.Error as err:
                        niceerror(caught=True,
                                  caughtprefix='+++ DB',
                                  caughtcode='165',
                                  caughtmsg='DB error on INSERT INTO '
                                  'sets: [{!s}]'
                                  .format(err.args[0]),
                                  useniceprint=True)
                else:
                    logging.info('Set found on DB:[%s]',
                                 strunicodeout(setName))
                    if self.args.verbose:
                        NP.niceprint('Set found on DB:[{!s}]'
                                     .format(strunicodeout(setName)))
        else:
            niceerror(caught=True,
                      caughtprefix='xxx',
                      caughtcode='089',
                      caughtmsg='Failed to list photosets (photosets.getList)',
                      exceptuse=True,
                      exceptcode=get_result['code']
                      if 'code' in get_result
                      else get_result,
                      exceptmsg=get_result['message']
                      if 'message' in get_result
                      else get_result,
                      useniceprint=True)

        # Closing DB connection
        if con is not None and con in locals():
            niceerror(caught=True,
                      caughtprefix='+++ DB',
                      caughtcode='121',
                      caughtmsg='Closing DB connection on photosets.getList',
                      useniceprint=True)
            con.close()

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

        returnIsPhotoUploaded = False
        returnPhotoUploaded = 0
        returnPhotoID = None
        returnUploadedNoSet = False

        logging.info('Is Already Uploaded:[checksum:%s] [album:%s]?',
                     xchecksum, strunicodeout(xsetName))

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
        #
        # Use a big random waitime to avoid errors in multiprocessing mode.
        get_success, searchIsUploaded, get_errcode = faw.flickrapi_fn(
            self.nuflickr.photos.search, (),
            dict(user_id="me",
                 tags='checksum:{}'.format(xchecksum),
                 extras='tags'),
            3, 20, False, caughtcode='180')

        if not (get_success and get_errcode == 0):
            # CODING: how to indicate an error... different from False?
            # Possibly raising an exception?
            # raise Exception('photos.search: Max attempts exhausted.')
            if self.args.verbose:
                NP.niceprint(' IS_UPLOADED:[ERROR#1]',
                             fname='isuploaded')
            logging.warning(' IS_UPLOADED:[ERROR#1]')

            return returnIsPhotoUploaded, returnPhotoUploaded, \
                returnPhotoID, returnUploadedNoSet

        # Number of pics with specified checksum
        # CODING: Protect issue #66. Flickr returns attrib == '' instead of 0
        # Set 'Number of pics with specified checksum' to 0 and return.
        if not searchIsUploaded.find('photos').attrib['total']:
            returnPhotoUploaded = 0
            logging.error(' IS_UPLOADED:[ERROR#3]: Invalid return. Confinuing')
            NP.niceprint(' IS_UPLOADED:[ERROR#3]: Invalid return. Confinuing',
                         fname='isuploaded')
        else:
            returnPhotoUploaded = int(searchIsUploaded
                                      .find('photos').attrib['total'])

        if returnPhotoUploaded == 0:
            # A) checksum,                             Count=0  THEN NOT EXISTS
            returnIsPhotoUploaded = False
        elif returnPhotoUploaded >= 1:
            logging.warning('+++#190: '
                            'Found [%s] images with checksum:[%s]',
                            returnPhotoUploaded, xchecksum)
            # Get title from filepath as filename without extension
            # NOTE: not compatible with use of the -i option
            xtitle_filename = os.path.split(xfile)[1]
            xtitle_filename = os.path.splitext(xtitle_filename)[0]
            logging.info('Title:[%s]', strunicodeout(xtitle_filename))

            # For each pic found on Flickr 1st check title and then Sets
            freturnPhotoUploaded = 0
            for pic in searchIsUploaded.find('photos').findall('photo'):
                freturnPhotoUploaded += 1
                logging.debug('idx=[%s] pic.id=[%s] '
                              'pic.title=[%s] pic.tags=[%s]',
                              freturnPhotoUploaded,
                              pic.attrib['id'],
                              strunicodeout(pic.attrib['title']),
                              strunicodeout(pic.attrib['tags']))

                # Use strunicodeout in comparison to avoid warning:
                #   "UnicodeWarning: Unicode equal comparison failed to
                #    convert both arguments to Unicode"
                logging.debug('xtitle_filename/type=[%s]/[%s] '
                              'pic.attrib[title]/type=[%s]/[%s]',
                              strunicodeout(xtitle_filename),
                              type(xtitle_filename),
                              strunicodeout(pic.attrib['title']),
                              type(pic.attrib['title']))
                logging.info('Compare Titles=[%s]',
                             (strunicodeout(xtitle_filename) ==
                              strunicodeout(pic.attrib['title'])))

                # if pic with checksum has a different title, continue
                if not (strunicodeout(xtitle_filename) ==
                        strunicodeout(pic.attrib['title'])):
                    logging.info('Different titles: File:[%s] Flickr:[%s]',
                                 strunicodeout(xtitle_filename),
                                 strunicodeout(pic.attrib['title']))
                    continue

                ctx_success, resp, ctx_errcode = faw.flickrapi_fn(
                    self.nuflickr.photos.getAllContexts, (),
                    dict(photo_id=pic.attrib['id']),
                    3, 8, True, caughtcode='195')

                if not (ctx_success and ctx_errcode == 0):
                    # CODING: how to indicate an error?
                    # Possibly raising an exception?
                    # raise Exception('photos_getAllContexts: '
                    #                 'Max attempts exhausted.')
                    if self.args.verbose:
                        NP.niceprint(' IS_UPLOADED:[ERROR#2]',
                                     fname='isuploaded')
                    logging.warning(' IS_UPLOADED:[ERROR#2]')

                    return returnIsPhotoUploaded, returnPhotoUploaded, \
                        returnPhotoID, returnUploadedNoSet

                logging.info('len(resp.findall(''set'')):[%s]',
                             len(resp.findall('set')))

                # B) checksum, title, empty setName,       Count=1
                #                 THEN EXISTS, ASSIGN SET IF tag album IS FOUND
                if not resp.findall('set'):
                    # CODING: Consider one additional result for PHOTO UPLOADED
                    # WITHOUT SET WITH ALBUM TAG when row exists on DB. Mark
                    # such row on the database files.set_id to null
                    # to force re-assigning to Album/Set on flickr.
                    tfind, _ = self.photos_find_tag(
                        photo_id=pic.attrib['id'],
                        intag='album:{}'
                        .format(xsetName))
                    if tfind:
                        if self.args.verbose:
                            NP.niceprint(' IS_UPLOADED:[UPLOADED WITHOUT'
                                         ' SET WITH ALBUM TAG]',
                                         fname='isuploaded')
                        logging.warning(' IS_UPLOADED:[UPLOADED WITHOUT'
                                        ' SET WITH ALBUM TAG]')
                        returnIsPhotoUploaded = True
                        returnPhotoID = pic.attrib['id']
                        returnUploadedNoSet = True
                        return returnIsPhotoUploaded, returnPhotoUploaded, \
                            returnPhotoID, returnUploadedNoSet
                    else:
                        if self.args.verbose_progress:
                            NP.niceprint('IS_UPLOADED:[UPLOADED WITHOUT'
                                         ' SET WITHOUT ALBUM TAG]',
                                         fname='isuploaded')
                        logging.warning('IS_UPLOADED:[UPLOADED WITHOUT'
                                        ' SET WITHOUT ALBUM TAG]')

                for setinlist in resp.findall('set'):
                    logging.warning('Output for setinlist:')
                    logging.warning(xml.etree.ElementTree.tostring(
                        setinlist,
                        encoding='utf-8',
                        method='xml'))

                    logging.warning(
                        '\nCheck : id=[%s] File=[%s]\n'
                        'Check : Title:[%s] Set:[%s]\n'
                        'Flickr: Title:[%s] Set:[%s] Tags:[%s]\n',
                        pic.attrib['id'],
                        strunicodeout(xfile),
                        strunicodeout(xtitle_filename),
                        strunicodeout(xsetName),
                        strunicodeout(pic.attrib['title']),
                        strunicodeout(setinlist.attrib['title']),
                        strunicodeout(pic.attrib['tags']))

                    logging.warning(
                        'Compare Sets=[%s]',
                        (strunicodeout(xsetName) ==
                         strunicodeout(setinlist.attrib['title'])))

                    # C) checksum, title, setName (1 or more), Count>=1
                    #                                               THEN EXISTS
                    if (strunicodeout(xsetName) ==
                            strunicodeout(setinlist.attrib['title'])):
                        if self.args.verbose:
                            NP.niceprint(' IS_UPLOADED:[TRUE WITH SET]',
                                         fname='isuploaded')
                        logging.warning(
                            ' IS_UPLOADED:[TRUE WITH SET]')
                        returnIsPhotoUploaded = True
                        returnPhotoID = pic.attrib['id']
                        returnUploadedNoSet = False
                        return returnIsPhotoUploaded, returnPhotoUploaded, \
                            returnPhotoID, returnUploadedNoSet
                    else:
                        # D) checksum, title, other setName,       Count>=1
                        #                                       THEN NOT EXISTS
                        if self.args.verbose_progress:
                            NP.niceprint(' IS_UPLOADED:[FALSE OTHER SET, '
                                         'CONTINUING SEARCH IN SETS]',
                                         fname='isuploaded')
                        logging.warning(' IS_UPLOADED:[FALSE OTHER SET, '
                                        'CONTINUING SEARCH IN SETS]')
                        continue

        return returnIsPhotoUploaded, returnPhotoUploaded, \
            returnPhotoID, returnUploadedNoSet

    # -------------------------------------------------------------------------
    # photos_find_tag
    #
    #   Determines if tag is assigned to a pic.
    #
    def photos_find_tag(self, photo_id, intag):
        """ photos_find_tag

            Determines if intag is assigned to a pic.
            Returns:
                found_tag = False/True
                tag_id    = tag_id if found
        """

        logging.info('find_tag: photo:[%s] intag:[%s]', photo_id, intag)

        tag_success, tagsResp, tag_errcode = faw.flickrapi_fn(
            self.nuflickr.tags.getListPhoto, (),
            dict(photo_id=photo_id),
            3, 15, True, caughtcode='205')

        if tag_success and tag_errcode == 0:

            tag_id = None
            for tag in tagsResp.find('photo').find('tags').findall('tag'):
                logging.info(tag.attrib['raw'])
                if (strunicodeout(tag.attrib['raw']) ==
                        strunicodeout(intag)):
                    tag_id = tag.attrib['id']
                    logging.info('Found tag_id:[%s] for intag:[%s]',
                                 tag_id, intag)
                    return True, tag_id

        return False, ''

    # -------------------------------------------------------------------------
    # photos_remove_tag
    #
    #   Local Wrapper for Flickr photos.removeTag
    #   The tag to remove from the photo. This parameter should contain
    #   a tag id, as returned by flickr.photos.getInfo.
    #
    def photos_remove_tag(self, tag_id):
        """ photos_remove_tag

            Local Wrapper for Flickr photos.removeTag

            The tag to remove from the photo. This parameter should contain
            a tag id, as returned by flickr.photos.getInfo.
        """

        logging.info('remove_tag: tag_id:[%s]', tag_id)

        get_success, _, _ = faw.flickrapi_fn(
            self.nuflickr.tags.removeTag, (),
            dict(tag_id=tag_id),
            3, 5, False, caughtcode='206')

        return get_success

    # -------------------------------------------------------------------------
    # photos_set_dates
    #
    # Update Date/Time Taken on Flickr for Video files
    #
    def photos_set_dates(self, photo_id, datetxt):
        """ photos_set_dates

            Update Date/Time Taken on Flickr for Video files
        """

        logging.warning('   Setting Date:[%s] Id=[%s]', datetxt, photo_id)

        get_success, respDate, get_errcode = faw.flickrapi_fn(
            self.nuflickr.photos.setdates, (),
            dict(photo_id=photo_id,
                 date_taken='{!s}'.format(datetxt),
                 date_taken_granularity=0),
            3, 15, True, caughtcode='210')

        if get_success and get_errcode == 0:
            logging.debug('Set Date Response: OK!')
        else:
            logging.error('Set Date Response: NOK!')

        return respDate

    # -------------------------------------------------------------------------
    # maddAlbumsMigrate
    #
    # maddAlbumsMigrate wrapper for multiprocessing purposes
    #
    def maddAlbumsMigrate(self, lock, running, mutex, filelist, cTotal, cur):
        """ maddAlbumsMigrate

            Wrapper function for multiprocessing support to call uploadFile
            with a chunk of the files.
            lock       = for database access control in multiprocessing
            running    = shared value to count processed files in
                         multiprocessing
            mutex      = for running access control in multiprocessing
            cur        = cursor
        """

        for i, f in enumerate(filelist):
            logging.warning('===Current element of Chunk: [%s][%s]', i, f)

            # f[0] = files_id
            # f[1] = path
            # f[2] = set_name
            # f[3] = set_id
            NP.niceprint('ID:[{!s}] Path:[{!s}] Set:[{!s}] SetID:[{!s}]'
                         .format(str(f[0]), f[1], f[2], f[3]),
                         fname='addAlbumMigrate')

            # row[1] = path for the file from table files
            setName = set_name_from_file(f[1],
                                         self.xcfg.FILES_DIR,
                                         self.xcfg.FULL_SET_NAME)
            tfind, tid = self.photos_find_tag(
                photo_id=f[0],
                intag='album:{}'.format(f[2]
                                        if f[2] is not None
                                        else setName))

            logging.warning('       Find Tag:[%s] TagId:[%s]',
                            tfind, tid)
            if self.args.verbose:
                NP.niceprint('       Find Tag::[{!s}] TagId:[{!s}]'
                             .format(tfind, tid))

            if not tfind:
                get_success, res_add_tag, get_errcode = faw.flickrapi_fn(
                    self.nuflickr.photos.addTags, (),
                    dict(photo_id=f[0],
                         tags='album:"{}"'.format(f[2]
                                                  if f[2] is not None
                                                  else setName)),
                    2, 2, False, caughtcode='214')

                a_result = get_success and get_errcode == 0
                logging.warning('%s: Photo_id:[%s]. ',
                                'Added album tag'
                                if a_result
                                else 'Failed tagging',
                                str(row[0]))
                NP.niceprint('{!s}: Photo_id:[{!s}]. '
                             .format(' Failed tagging'
                                     if a_result
                                     else 'Failed tagging',
                                     str(row[0])),
                             fname='addAlbumMigrate')
            else:
                logging.warning('      Found Tag:[%s] TagId:[{%s]',
                                tfind, tid)
                if self.args.verbose:
                    NP.niceprint('      Found Tag::[{!s}] TagId:[{!s}]'
                                 .format(tfind, tid))

            logging.debug('===Multiprocessing=== in.mutex.acquire(w)')
            mutex.acquire()
            running.value += 1
            xcount = running.value
            mutex.release()
            logging.info('===Multiprocessing=== out.mutex.release(w)')

            # Show number of files processed so far
            NP.niceprocessedfiles(xcount, cTotal, False)

            # Control pace (rate limit)of each proceess
            rate_5_callspersecond()

    # -------------------------------------------------------------------------
    # addAlbumsMigrate
    #
    # Prepare for version 2.7.0 Add album info to loaded pics
    #
    def addAlbumsMigrate(self):
        """ addAlbumsMigrate

            Adds tag:album to pics
        """

        # ---------------------------------------------------------------------
        # Local Variables
        #
        #   mlockDB     = multiprocessing Lock for access to Database
        #   mmutex      = multiprocessing mutex for access to value mrunning
        #   mrunning    = multiprocessing Value to count processed photos
        mlockDB = None
        mmutex = None
        mrunning = None

        if not self.check_token():
            # authenticate sys.exits in case of failure
            self.authenticate()
        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str
        with con:
            try:
                cur = con.cursor()
                cur.execute('SELECT files_id, path, sets.name, sets.set_id '
                            'FROM files LEFT OUTER JOIN sets ON '
                            'files.set_id = sets.set_id')
                existingMedia = cur.fetchall()
                logging.info('len(existingMedia)=[%s]',
                             len(existingMedia))
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='215',
                          caughtmsg='DB error on SELECT FROM sets: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
                return False

            countTotal = len(existingMedia)
            # running in multi processing mode
            if self.args.processes and self.args.processes > 0:
                logging.debug('Running [%s] processes pool.',
                              self.args.processes)
                logging.debug('__name__:[%s] to prevent recursive calling)!',
                              __name__)
                cur = con.cursor()

                # To prevent recursive calling, check if __name__ == '__main__'
                # if __name__ == '__main__':
                mp.mprocessing(self.args.verbose,
                               self.args.verbose_progress,
                               self.args.processes,
                               mlockDB,
                               mrunning,
                               mmutex,
                               existingMedia,
                               self.maddAlbumsMigrate,
                               cur)

                con.commit()

            # running in single processing mode
            else:
                count = 0
                countTotal = len(existingMedia)
                for row in existingMedia:
                    count += 1
                    # row[0] = files_id
                    # row[1] = path
                    # row[2] = set_name
                    # row[3] = set_id
                    NP.niceprint('ID:[{!s}] Path:[{!s}] '
                                 'Set:[{!s}] SetID:[{!s}]'
                                 .format(str(row[0]), row[1],
                                         row[2], row[3]),
                                 fname='addAlbumMigrate')

                    # row[1] = path for the file from table files
                    setName = set_name_from_file(row[1],
                                                 self.xcfg.FILES_DIR,
                                                 self.xcfg.FULL_SET_NAME)

                    tfind, tid = self.photos_find_tag(
                        photo_id=row[0],
                        intag='album:{}'.format(row[2]
                                                if row[2] is not None
                                                else setName))

                    logging.warning('       Find Tag:[%s] TagId:[%s]',
                                    tfind, tid)
                    if self.args.verbose:
                        NP.niceprint('       Find Tag::[{!s}] TagId:[{!s}]'
                                     .format(tfind, tid))

                    if not tfind:
                        get_success, res_add_tag, get_errcode = \
                            faw.flickrapi_fn(
                                self.nuflickr.photos.addTags, (),
                                dict(photo_id=row[0],
                                     tags='album:"{}"'
                                     .format(row[2]
                                             if row[2] is not None
                                             else setName)),
                                2, 2, False, caughtcode='218')

                        a_result = get_success and get_errcode == 0
                        logging.warning('%s: Photo_id:[%s]. ',
                                        'Added album tag'
                                        if a_result
                                        else 'Failed tagging',
                                        str(row[0]))
                        NP.niceprint('{!s}: Photo_id:[{!s}]. '
                                     .format(' Failed tagging'
                                             if a_result
                                             else 'Failed tagging',
                                             str(row[0])),
                                     fname='addAlbumMigrate')
                    else:
                        logging.warning('      Found Tag:[%s] TagId:[{%s]',
                                        tfind, tid)
                        if self.args.verbose:
                            NP.niceprint('      Found Tag::[{!s}] TagId:[{!s}]'
                                         .format(tfind, tid))

                    NP.niceprocessedfiles(count, countTotal, False)

                NP.niceprocessedfiles(count, countTotal, True)

        return True

    # -------------------------------------------------------------------------
    # listBadFiles
    #
    # List badfiles recorded on Local DB from previous loads
    #
    def listBadFiles(self):
        """ listBadFiles

            List badfiles recorded on Local DB from previous loads
        """

        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str
        with con:
            try:
                cur = con.cursor()
                cur.execute('SELECT files_id, path, set_id, md5, tagged, '
                            'last_modified '
                            'FROM badfiles ORDER BY path')
                badFiles = cur.fetchall()
                logging.info('len(badFiles)=[%s]', len(badFiles))
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='219',
                          caughtmsg='DB error on SELECT FROM sets: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)
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
                      .format(strunicodeout(str(row[0])),
                              strunicodeout(str(row[1])),
                              strunicodeout(str(row[2])),
                              strunicodeout(str(row[3])),
                              strunicodeout(str(row[4])),
                              NUTIME.strftime(UPLDR_K.TimeFormat,
                                              NUTIME.localtime(row[5]))))
                sys.stdout.flush()

            NP.niceprocessedfiles(count, countTotal, True)

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
        con = lite.connect(self.xcfg.DB_PATH)
        con.text_factory = str
        countlocal = 0
        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT Count(*) FROM files")
                countlocal = cur.fetchone()[0]
                logging.info('Total photos on local: %s', countlocal)
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='220',
                          caughtmsg='DB error on SELECT FROM files: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)

        # Total Local badfiles photos count -----------------------------------
        BadFilesCount = 0
        with con:
            try:
                cur = con.cursor()
                cur.execute("SELECT Count(*) FROM badfiles")
                BadFilesCount = cur.fetchone()[0]
                logging.info('Total badfiles count on local: %s',
                             BadFilesCount)
            except lite.Error as err:
                niceerror(caught=True,
                          caughtprefix='+++ DB',
                          caughtcode='230',
                          caughtmsg='DB error on SELECT FROM '
                          'badfiles: [{!s}]'
                          .format(err.args[0]),
                          useniceprint=True)

        # Total FLickr photos count: find('photos').attrib['total'] -----------
        get_success, get_result, get_errcode = faw.flickrapi_fn(
            self.nuflickr.people.getPhotos, (),
            dict(user_id="me", per_page=1),
            3, 3, False, caughtcode='390')

        if get_success and get_errcode == 0:
            countflickr = get_result.find('photos').attrib['total']
        else:
            countflickr = -1

        # Total FLickr photos not in set: find('photos').attrib['total'] ------
        get_success, get_result, get_errcode = faw.flickrapi_fn(
            self.nuflickr.photos.getNotInSet, (),
            dict(per_page=1),
            3, 3, False, caughtcode='400')

        if get_success and get_errcode == 0:
            countnotinsets = int(format(
                get_result.find('photos').attrib['total']))
        else:
            countnotinsets = 0

        # Print total stats counters ------------------------------------------
        NP.niceprint('\n  Initial Found Files:[{!s:>6s}]\n'
                     '          - Bad Files:[{!s:>6s}] = [{!s:>6s}]\n'
                     '                 Note: some Bad files may no '
                     'longer exist!\n'
                     'Photos count:\n'
                     '                Local:[{!s:>6s}]\n'
                     '               Flickr:[{!s:>6s}]\n'
                     'Not in sets on Flickr:[{!s:>6s}]'
                     .format(InitialFoundFiles,
                             BadFilesCount,
                             InitialFoundFiles - BadFilesCount,
                             countlocal,
                             countflickr,
                             countnotinsets))

        # List pics not in sets (if within a parameter) -----------------------
        # Maximum allowed per_page by Flickr is 500.
        # Avoid going over in order not to have to handle multipl pages.
        if (self.args.list_photos_not_in_set and
                self.args.list_photos_not_in_set > 0 and
                countnotinsets > 0):
            NP.niceprint('*****Listing Photos not in a set in Flickr******')

            # List pics not in sets (if within a parameter, default 10)
            # (per_page=min(self.args.list_photos_not_in_set, 500):
            #       find('photos').attrib['total']
            get_success, get_result, get_errcode = faw.flickrapi_fn(
                self.nuflickr.photos.getNotInSet, (),
                dict(per_page=min(self.args.list_photos_not_in_set, 500)),
                3, 3, False, caughtcode='410')

            if get_success and get_errcode == 0:
                for count, row in enumerate(get_result.find('photos')
                                            .findall('photo')):
                    logging.info('Photo Not in Set: id:[%s] title:[%s]',
                                 row.attrib['id'],
                                 strunicodeout(row.attrib['title']))
                    output_str = 'id={!s}|title={!s}|'.format(
                        row.attrib['id'],
                        strunicodeout(row.attrib['title']))

                    tags_success, tags_result, tags_errcode = faw.flickrapi_fn(
                        self.nuflickr.tags.getListPhoto, (),
                        dict(photo_id=row.attrib['id']),
                        2, 2, False, caughtcode='411')

                    if tags_success and tags_errcode == 0:
                        for tag in tags_result.find('photo')\
                                .find('tags').findall('tag'):
                            output_str += 'tag_attrib={!s}|'\
                                          .format(
                                              NP.strunicodeout(
                                                  tag.attrib['raw']))

                    NP.niceprint(output_str)

                    logging.info('count=[%s]', count)
                    if (count == 500 or
                            count >= (self.args.list_photos_not_in_set - 1) or
                            count >= (countnotinsets - 1)):
                        logging.info('Stopped at photo [%s] listing '
                                     'photos not in a set', count)
                        break
            else:
                NP.niceprint('Error in list get_not_in_set. No output.')

            NP.niceprint('*****Completed Listing Photos not in a set '
                         'in Flickr******')

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

        use_dblock_return = False

        logging.debug('Entering useDBLock with useDBoperation:[%s].',
                      useDBoperation)

        if useDBthisLock is None:
            logging.debug('useDBLock: useDBthisLock is [None].')
            return use_dblock_return

        logging.debug('useDBLock: useDBthisLock.semlock:[%s].',
                      useDBthisLock._semlock)

        if useDBoperation is None:
            return use_dblock_return

        if (self.args.processes is not None) and\
           (self.args.processes) and \
           (self.args.processes > 0):
            if useDBoperation:
                # Control for when running multiprocessing set locking
                logging.debug('===Multiprocessing=== -->[ ].lock.acquire')
                try:
                    if useDBthisLock.acquire():
                        use_dblock_return = True
                except BaseException:
                    niceerror(caught=True,
                              caughtprefix='+++ ',
                              caughtcode='002',
                              caughtmsg='Caught an exception lock.acquire',
                              useniceprint=True,
                              exceptsysinfo=True)
                    raise
                logging.info('===Multiprocessing=== --->[v].lock.acquire')
            else:
                # Control for when running multiprocessing release locking
                logging.debug('===Multiprocessing=== <--[ ].lock.release')
                try:
                    useDBthisLock.release()
                    use_dblock_return = True
                except BaseException:
                    niceerror(caught=True,
                              caughtprefix='+++ ',
                              caughtcode='003',
                              caughtmsg='Caught an exception lock.release',
                              useniceprint=True,
                              exceptsysinfo=True)
                    # Raise aborts execution
                    raise
                logging.info('===Multiprocessing=== <--[v].lock.release')

            logging.info('Exiting useDBLock with useDBoperation:[%s]. '
                         'Result:[%s]',
                         useDBoperation, use_dblock_return)
        else:
            use_dblock_return = True
            logging.warning('(No multiprocessing. Nothing to do) '
                            'Exiting useDBLock with useDBoperation:[%s]. '
                            'Result:[%s]',
                            useDBoperation, use_dblock_return)

        return use_dblock_return


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                        '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()
