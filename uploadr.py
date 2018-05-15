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
import time
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
import lib.UPLDRConstants as UPLDRConstantsClass
# -----------------------------------------------------------------------------
# Helper class and functions to print messages.
import lib.NicePrint as NicePrint
# -----------------------------------------------------------------------------
# Helper class and functions to load, process and verify INI configuration.
import lib.MyConfig as MyConfig


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
my_cfg = MyConfig.MyConfig()
# Get LOGGING_LEVEL defaul configuration
my_cfg.LOGGING_LEVEL = int(str(my_cfg.LOGGING_LEVEL))
# Update logging level as per LOGGING_LEVEL from default config
logging.getLogger().setLevel(my_cfg.LOGGING_LEVEL)
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
def my_excepthook(exc_class, exc_value, exc_tb):
    """ my_excepthook

        Exception handler to be installed over sys.excepthook to allow
        traceback reporting information to be reported back to logging file
    """
    logging.critical('Uncaught exception: {0}: {1}'
                     .format(exc_class, exc_value))
    logging.critical(''.join(traceback.format_tb(exc_tb)))


# -----------------------------------------------------------------------------
# parse_arguments
#
# This is the main method
#
def parse_arguments():
    """ parse_arguments

        Parse arguments and return results.
    """

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
                            # default=UPLDRConstants.ini_file,
                            help='Optional configuration file. '
                                 'Default is:[{!s}]'
                            .format(UPLDRConstants.ini_file))
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
                            help='Number of photos to upload simultaneously. '
                                 'Number of process to assign pics to sets.')
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
                                 'note it only performs '
                                 'upload/raw convert/replace.')

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

    return parser.parse_args()
    # Parse args --------------------------------------------------------------


# -----------------------------------------------------------------------------
# run_uploadr
#
# This is the main method
#
def run_uploadr(args):
    """ run_uploadr

        args = parameters
    """
    # -------------------------------------------------------------------------
    # Local Variables
    #
    #   FLICK        = Class Uploadr (created in the Main code)

    # Print/show arguments
    if my_cfg.LOGGING_LEVEL <= logging.INFO:
        NPR.niceprint('Output for arguments(args):')
        pprint.pprint(args)

    if args.verbose:
        NPR.niceprint('FILES_DIR: [{!s}]'
                      .format(NPR.strunicodeout(my_cfg.FILES_DIR)))

    logging.warning('FILES_DIR: [%s]', NPR.strunicodeout(my_cfg.FILES_DIR))

    if my_cfg.FILES_DIR == "":
        NPR.niceprint('Please configure in the INI file [normally uploadr.ini]'
                      ' the name of the folder [FILES_DIR] '
                      'with media available to sync with Flickr.')
        sys.exit(8)
    else:
        if not os.path.isdir(my_cfg.FILES_DIR):
            logging.critical('FILES_DIR: [%s] is not valid.',
                             NPR.strunicodeout(my_cfg.FILES_DIR))
            NPR.niceprint('Please configure the name of an existant folder '
                          'in the INI file [normally uploadr.ini] '
                          'with media available to sync with Flickr. '
                          'FILES_DIR: [{!s}] is not valid.'
                          .format(NPR.strunicodeout(my_cfg.FILES_DIR)))
            sys.exit(8)

    if my_cfg.FLICKR["api_key"] == "" or my_cfg.FLICKR["secret"] == "":
        logging.critical('Please enter an API key and secret in the '
                         'configuration '
                         'script file, normaly uploadr.ini (see README).')
        NPR.niceprint('Please enter an API key and secret in the configuration'
                      ' script file, normaly uploadr.ini (see README).')
        sys.exit(9)

    # Instantiate class Uploadr. getCachedToken is called on __init__
    logging.debug('Instantiating the Main class FLICK = Uploadr()')
    FLICK = FlickrUploadr.Uploadr(my_cfg, args)

    # Setup the database
    FLICK.setupDB()
    if args.clean_bad_files:
        FLICK.cleanDBbadfiles()

    if args.daemon:
        # Will run in daemon mode every SLEEP_TIME seconds
        if FLICK.check_token():
            logging.warning('Will run in daemon mode every [%s] seconds',
                            my_cfg.SLEEP_TIME)
            logging.warning('Make sure you have previously authenticated!')
            NPR.niceprint('Will run in daemon mode every [{!s}] seconds'
                          .format(my_cfg.SLEEP_TIME))
            FLICK.run()
        else:
            logging.warning('Not able to connect to Flickr.'
                            'Make sure you have previously authenticated!')
            NPR.niceprint('Not able to connect to Flickr.'
                          'Make sure you have previously authenticated!')
            sys.exit(8)
    else:
        NPR.niceprint('Checking if token is available... '
                      'if not will authenticate')
        if not FLICK.check_token():
            # authenticate sys.exits in case of failure
            FLICK.authenticate()

        if args.add_albums_migrate:
            NPR.niceprint('Performing preparation for migration to 2.7.0',
                          fname='addAlbumsMigrate')

            if FLICK.addAlbumsMigrate():
                NPR.niceprint('Successfully added album tags to pics '
                              'on upload.',
                              fname='addAlbumsMigrate')
            else:
                logging.warning('Failed adding album tags to pics '
                                'on upload. '
                                'Please check logs, correct, and retry.')
                NPR.niceprint('Failed adding album tags to pics '
                              'on upload. '
                              'Please check logs, correct, and retry.',
                              fname='addAlbumsMigrate')
                sys.exit(10)
        elif args.list_bad_files:
            NPR.niceprint('Listing badfiles: Start.',
                          fname='listBadFiles')
            FLICK.listBadFiles()
            NPR.niceprint('Listing badfiles: End. No more options will run.',
                          fname='listBadFiles')
        else:
            FLICK.removeUselessSetsTable()
            FLICK.getFlickrSets()
            FLICK.upload()
            FLICK.removeDeletedMedia()

            if args.search_for_duplicates:
                FLICK.searchForDuplicates()

            if args.remove_excluded:
                FLICK.removeExcludedMedia()

            FLICK.createSets()
            FLICK.printStat(UPLDRConstantsClass.media_count)
    # Run Uploadr -------------------------------------------------------------


# -----------------------------------------------------------------------------
# checkBaseDir_INIfile
#
# Check if base_dir folder exists and ini_file exists and is a file
#
def checkBaseDir_INIfile(base_dir, ini_file):
    """checkBaseDir_INIfile

    base_dir = Folder
    ini_file = INI File path
    """

    result_check = True
    try:
        if not ((base_dir == '' or os.path.isdir(base_dir)) and
                os.path.isfile(ini_file)):
            raise OSError('[Errno 2] No such file or directory')
    except Exception as err:
        result_check = False
        logging.critical(
            'Config folder [%s] and/or INI file: [%s] not found or '
            'incorrect format: [%s]!', base_dir, ini_file, str(err))

    logging.debug('result_check=[{%s]', result_check)
    return result_check


# =============================================================================
# Global Variables
#
#   NUTIME = for working with time module (import time)
#
# -----------------------------------------------------------------------------
NUTIME = time
# -----------------------------------------------------------------------------

# =============================================================================
# Class UPLDReConstants
#
#   media_count = Counter of total files to initially upload
#   base_dir      = Base configuration directory location
#   ini_file      = Configuration file
# -----------------------------------------------------------------------------
# UPLDRConstants = UPLDRConstantsClass.UPLDRConstants()
UPLDRConstants.media_count = 0
# Base dir for config and support files.
#   Will use --config-file argument option
#   If not, first try sys.prefix/etc folder
#   If not, then try Current Working Directory
UPLDRConstants.base_dir = os.path.join(sys.prefix, 'etc')
UPLDRConstants.ini_file = os.path.join(UPLDRConstants.base_dir, "uploadr.ini")

if my_cfg.LOGGING_LEVEL <= logging.DEBUG:
    logging.debug('      base_dir:[%s]', UPLDRConstants.base_dir)
    logging.debug('           cwd:[%s]', os.getcwd())
    logging.debug('    prefix/etc:[%s]', os.path.join(sys.prefix, 'etc'))
    logging.debug('   sys.argv[0]:[%s]', os.path.dirname(sys.argv[0]))
    logging.debug('      ini_file:[%s]', UPLDRConstants.ini_file)
# -----------------------------------------------------------------------------

# =============================================================================
# Functions aliases
#
#   NPR  = NicePrint.NicePrint
# -----------------------------------------------------------------------------
NPR = NicePrint.NicePrint()
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
NPR.niceprint('--------- (V{!s}) Start time: {!s} ---------(Log:{!s})'
              .format(UPLDRConstants.Version,
                      NUTIME.strftime(UPLDRConstants.TimeFormat),
                      my_cfg.LOGGING_LEVEL))
# Install exception handler
sys.excepthook = my_excepthook

if __name__ == "__main__":
    # Parse the argumens options
    PARSED_ARGS = parse_arguments()

    # Argument --config-file overrides configuration filename.
    if PARSED_ARGS.config_file:
        UPLDRConstants.ini_file = PARSED_ARGS.config_file
        logging.info('UPLDRConstants.ini_file:[%s]',
                     NPR.strunicodeout(UPLDRConstants.ini_file))
        if not checkBaseDir_INIfile(UPLDRConstants.base_dir,
                                    UPLDRConstants.ini_file):
            NPR.niceerror(caught=True,
                          caughtprefix='+++ ',
                          caughtcode='601',
                          caughtmsg='Invalid -C parameter INI file. '
                          'Exiting...',
                          useniceprint=True)
            sys.exit(2)
    else:
        # sys.argv[0]
        UPLDRConstants.base_dir = os.path.dirname(sys.argv[0])
        UPLDRConstants.ini_file = os.path.join(UPLDRConstants.base_dir,
                                               'uploadr.ini')

        if not checkBaseDir_INIfile(UPLDRConstants.base_dir,
                                    UPLDRConstants.ini_file):
            NPR.niceerror(caught=True,
                          caughtprefix='+++ ',
                          caughtcode='602',
                          caughtmsg='Invalid sys.argv INI file. Exiting...',
                          useniceprint=True)
            sys.exit(2)

    # Write DEBUG messages or higher to err_file
    flogging = None
    if not (UPLDRConstants.base_dir == ''
            or os.path.isdir(UPLDRConstants.base_dir)):
        NPR.niceerror(caught=True,
                      caughtprefix='+++ ',
                      caughtcode='603',
                      caughtmsg='Invalid sys.argv ERR file '
                      'prevents output to file.',
                      useniceprint=True)
    else:
        # Define a Handler which writes DEBUG messages or higher to err_file
        flogging = logging.handlers.RotatingFileHandler(
            UPLDRConstants.err_file,
            maxBytes=25*1024*1024,  # 25 MBytes
            backupCount=3)
        # Define the Logging level logging.DEBUG
        flogging.setLevel(logging.DEBUG)
        # Tell the handler to use this format
        flogging.setFormatter(
            logging.Formatter(fmt='[' + str(UPLDRConstants.Run) + ']' +
                              '[%(asctime)s]:[%(processName)-11s]' +
                              '[%(levelname)-8s]:[%(name)s] %(message)s',
                              datefmt=UPLDRConstants.TimeFormat))
        # add the handler to the root logger
        logging.getLogger().addHandler(flogging)

    # Source configuration from ini_file
    my_cfg.readconfig(UPLDRConstants.ini_file, ['Config'])
    if my_cfg.processconfig():
        if my_cfg.verifyconfig():
            pass
        else:
            raise ValueError('No config file found or incorrect config!')
    else:
        raise ValueError('No config file found or incorrect config!')

    # Update logging level as per LOGGING_LEVEL from INI file
    logging.getLogger().setLevel(my_cfg.LOGGING_LEVEL)
    if flogging is not None:
        flogging.setLevel(logging.DEBUG)

    if my_cfg.LOGGING_LEVEL <= logging.INFO:
        NPR.niceprint('Output for FLICKR Configuration:')
        pprint.pprint(my_cfg.FLICKR)

    # Ensure that only one instance of this script is running
    try:
        # FileLocker is an alias to portalocker (if available) or fcntl
        FILELOCK(open(my_cfg.LOCK_PATH, 'w'),
                 FileLocker.LOCK_EX | FileLocker.LOCK_NB)
    except IOError as err:
        if err.errno == errno.EAGAIN:
            logging.critical('Script already running.')
            sys.exit(-1)
        raise
    finally:
        pass

    # Run uploader
    run_uploadr(PARSED_ARGS)

NPR.niceprint('--------- (V{!s}) End time: {!s} -----------(Log:{!s})'
              .format(UPLDRConstants.Version,
                      NUTIME.strftime(UPLDRConstants.TimeFormat),
                      my_cfg.LOGGING_LEVEL))
sys.stderr.write('--------- ' + 'End: ' + ' ---------\n')
sys.stderr.flush()
