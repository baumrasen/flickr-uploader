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
logging.getLogger().setLevel(logging.DEBUG)
# define a Handler which writes WARNING messages or higher to the sys.stderr
CONSOLE_LOGGING = logging.StreamHandler()
CONSOLE_LOGGING.setLevel(logging.WARNING)
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


# -----------------------------------------------------------------------------
def my_excepthook(exc_class, exc_value, exc_tb):
    """ my_excepthook

        Exception handler to be installed over sys.excepthook to allow
        traceback reporting information to be reported back to logging file
    """
    logging.critical('Exception: %s: %s', exc_class, exc_value)
    logging.critical('%s', ''.join(traceback.format_tb(exc_tb)))


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
                            metavar='filename.ini',
                            type=str,
                            help='Optional configuration file. '
                                 'Default is:[{!s}]'
                            .format(UPLDR_K.ini_file))
    cgrpparser.add_argument('-a', '--authenticate', action='store_true',
                            help='Performs/Verifies authentication with '
                                 'Flickr. To be run on initial setup.'
                                 'Does not run any other option.')

    # Verbose related options -------------------------------------------------
    vgrpparser = parser.add_argument_group('Verbose and dry-run options')
    vgrpparser.add_argument('-v', '--verbose', action='count',
                            help='Verbose output. Use -vv for more verbosity. '
                                 'See also LOGGING_LEVEL value in INI file.')
    vgrpparser.add_argument('-x', '--verbose-progress', action='store_true',
                            help='Provides progress indicator on each upload. '
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
    # used in pics_status function
    igrpparser.add_argument('-l', '--list-photos-not-in-set',
                            metavar='N', type=int,
                            help='List as many as N photos (with tags) '
                                 'not in set. Maximum listed photos is 500.')

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
    #   myflick        = Class Uploadr (created in the Main code)

    def check_files_dir():
        """ check_files_dir

            Confirms setting MYCFG.FILES_DIR is defined and a valid folder.
            Exits from program otherwise.
        """
        logging.warning('FILES_DIR: [%s]', NPR.strunicodeout(MY_CFG.FILES_DIR))
        NPR.niceprint('FILES_DIR: [{!s}]'
                      .format(NPR.strunicodeout(MY_CFG.FILES_DIR)),
                      verbosity=1)

        if MY_CFG.FILES_DIR == "":
            NPR.niceerror(
                caught=True,
                caughtprefix='xxx',
                caughtcode='630',
                caughtmsg='Please configure in INI file [normally uploadr.ini]'
                ' the name of the folder [FILES_DIR] '
                'with media available to sync with Flickr.',
                useniceprint=True)

            sys.exit(8)
        else:
            if not os.path.isdir(MY_CFG.FILES_DIR):
                NPR.niceerror(
                    caught=True,
                    caughtprefix='xxx',
                    caughtcode='631',
                    caughtmsg='FILES_DIR: [{!s}] is not valid.'
                    'Please configure the name of an existant folder'
                    ' in INI file [normally uploadr.ini] '
                    'with media available to sync with Flickr. '
                    .format(NPR.strunicodeout(MY_CFG.FILES_DIR)),
                    useniceprint=True)

                sys.exit(8)

    def check_flickr_key_secret():
        """ def check_flickr_key_secret():

            Confirms the configuration for api_key and secret is defined.
            Exits from program otherwise.
        """

        if MY_CFG.FLICKR["api_key"] == "" or MY_CFG.FLICKR["secret"] == "":
            NPR.niceerror(
                caught=True,
                caughtprefix='xxx',
                caughtcode='635',
                caughtmsg='Please enter an API key and secret in the '
                'configuration file [normaly uploadr.ini] (see README).',
                useniceprint=True)

            sys.exit(9)

    def check_token_authenticate():
        """ check_token_authenticate

            Checks if token is available... if not will authenticate
        """
        NPR.niceprint('Checking if token is available... '
                      'if not will authenticate')
        if not myflick.check_token():
            # authenticate sys.exits in case of failure
            myflick.authenticate()
        else:
            logging.info('Token is available.')
            NPR.niceprint('Token is available.')

    # Initial checks
    check_files_dir()
    check_flickr_key_secret()

    # Instantiate class Uploadr. getCachedToken is called on __init__
    logging.debug('Instantiating the Main class myflick = Uploadr()')
    myflick = FlickrUploadr.Uploadr(MY_CFG, args)

    # Setup the database. Clean badfiles entries if asked
    myflick.setup_db()
    if args.clean_bad_files:
        myflick.cleanDBbadfiles()

    if args.authenticate:
        check_token_authenticate()
    elif args.daemon:
        # Will run in daemon mode every SLEEP_TIME seconds
        if myflick.check_token():
            logging.warning('Will run in daemon mode every [%s] seconds'
                            'Make sure you have previously authenticated!',
                            MY_CFG.SLEEP_TIME)
            NPR.niceprint('Will run in daemon mode every [{!s}] seconds'
                          'Make sure you have previously authenticated!'
                          .format(MY_CFG.SLEEP_TIME))
            myflick.run()
        else:
            NPR.niceerror(
                caught=True,
                caughtprefix='xxx',
                caughtcode='641',
                caughtmsg='Not able to connect to Flickr.'
                'Make sure you have previously authenticated!',
                useniceprint=True)

            sys.exit(8)
    else:
        check_token_authenticate()

        if args.add_albums_migrate:
            NPR.niceprint('Preparation migration to 2.7.0',
                          fname='addAlbumsMigrate')

            if myflick.addAlbumsMigrate():
                NPR.niceprint('Successfully added album tags to pics '
                              'on upload.',
                              fname='addAlbumsMigrate')
            else:
                NPR.niceerror(
                    caught=True,
                    caughtprefix='xxx',
                    caughtcode='642',
                    caughtmsg='Failed adding album tags to pics uploaded. '
                    'Please check logs, correct, and retry.',
                    useniceprint=True)

                sys.exit(10)
        elif args.list_bad_files:
            myflick.list_bad_files()
        else:
            myflick.remove_useless_sets_table()
            myflick.getFlickrSets()
            myflick.upload()
            myflick.remove_deleted_media()

            if args.remove_excluded:
                myflick.remove_excluded_media()

            myflick.createSets()
            myflick.pics_status(KonstantsClass.media_count)
    # Run Uploadr -------------------------------------------------------------


# -----------------------------------------------------------------------------
# check_base_ini_file
#
# Check if base_dir folder exists and ini_file exists and is a file
#
def check_base_ini_file(base_dir, ini_file):
    """ check_base_ini_file

    Returns True if base_dir is a directory and ini_file is a regular file.

    base_dir = Folder
    ini_file = INI File path
    """

    logging.info('check_base_ini_file: base_dir=[%s] ini_file=[%s]',
                 NPR.strunicodeout(base_dir),
                 NPR.strunicodeout(ini_file))

    result_check = True
    try:
        if not ((base_dir == '' or os.path.isdir(base_dir)) and
                os.path.isfile(ini_file)):
            raise OSError('[Errno 2] No such file or directory')
    except OSError as err:
        result_check = False
        logging.critical(
            'Config folder [%s] and/or INI file: [%s] not found or '
            'incorrect format: [%s]!', base_dir, ini_file, str(err))

    logging.debug('check_base_ini_file: result=[%s]', result_check)
    return result_check


# -----------------------------------------------------------------------------
# logging_close_handlers
#
# Close logging handlers
#
def logging_close_handlers():
    """ logging_close_handlers

    Close logging handlers

    """
    handlers = logging.getLogger().handlers[:]
    for handler in handlers:
        handler.close()
        logging.getLogger().removeHandler(handler)


# =============================================================================
# Global Variables
#
# -----------------------------------------------------------------------------
# Class UPLDReConstants
#
#   base_dir    = Base configuration directory location
#   ini_file    = Configuration file
#   media_count = Counter of total files to initially upload
# -----------------------------------------------------------------------------
# Base_dir set to os.path.abspat(os.path.dirname(sys.argv[0]))
# INI file config:
#   1. Use --config-file argument option [after PARSED_ARGS]
#   2. If not, os.path.dirname(sys.argv[0])
#   3. If not, os.path.dirname(sys.argv[0]), '..', 'etc', 'uploadr.ini'
# Set appropriate configuration within INI file for support files
UPLDR_K.base_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
UPLDR_K.ini_file = os.path.abspath(os.path.join(UPLDR_K.base_dir,
                                                'uploadr.ini'))
UPLDR_K.etc_ini_file = os.path.abspath(
    os.path.join(UPLDR_K.base_dir, os.path.pardir, 'etc', 'uploadr.ini'))
UPLDR_K.media_count = 0
# -----------------------------------------------------------------------------
# Debug folder locations and INI files
logging.debug('      base_dir:[%s]', UPLDR_K.base_dir)
logging.debug('           cwd:[%s]', os.getcwd())
logging.debug('sys.prefix/etc:[%s]', os.path.join(sys.prefix, 'etc'))
logging.debug('  abs(argv[0]):[%s]',
              os.path.abspath(os.path.dirname(sys.argv[0])))
logging.debug(' abs(__file__):[%s]',
              os.path.abspath(os.path.dirname(__file__)))
logging.debug('argv[0]/../etc:[%s]',
              os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                           os.path.pardir,
                                           'etc',
                                           'uploadr.ini')))
logging.debug('      ini_file:[%s]', UPLDR_K.ini_file)
logging.debug('  etc_ini_file:[%s]', UPLDR_K.etc_ini_file)
# -----------------------------------------------------------------------------

# =============================================================================
# Functions aliases
#
#   NPR  = NicePrint.NicePrint
# -----------------------------------------------------------------------------
NPR = NicePrint.NicePrint()
# -----------------------------------------------------------------------------


# =============================================================================
# Main code
#
NPR.niceprint('----------- (V{!s}) Start -----------(Log:{!s})'
              .format(UPLDR_K.Version,
                      MY_CFG.LOGGING_LEVEL))
# Install exception handler
sys.excepthook = my_excepthook

if __name__ == "__main__":
    # Parse the arguments options
    PARSED_ARGS = parse_arguments()

    # Set verbosity level as per -v count
    NPR.set_verbosity(PARSED_ARGS.verbose)

    # Print/show arguments
    logging.info('Output for arguments(args):\n%s',
                 pprint.pformat(PARSED_ARGS))
    NPR.niceprint('Output for arguments(args):\n{!s}'
                  .format(pprint.pformat(PARSED_ARGS)),
                  verbosity=3)

    # INI file config (1/3)
    #   1. Use --config-file argument option [after PARSED_ARGS]
    if PARSED_ARGS.config_file:
        if not check_base_ini_file(UPLDR_K.base_dir, PARSED_ARGS.config_file):
            NPR.niceerror(caught=True,
                          caughtprefix='+++ ',
                          caughtcode='661',
                          caughtmsg='Invalid -C argument INI file [{!s}]. '
                          'Exiting...'.format(UPLDR_K.ini_file),
                          useniceprint=True)
            sys.exit(2)
        else:
            UPLDR_K.ini_file = PARSED_ARGS.config_file
    # INI file config (2/3)
    #   2. If not, os.path.dirname(sys.argv[0])
    else:
        if not check_base_ini_file(UPLDR_K.base_dir, UPLDR_K.ini_file):
            NPR.niceerror(caught=True,
                          caughtprefix='+++ ',
                          caughtcode='662',
                          caughtmsg='Invalid sys.argv INI file [{!s}].'
                          .format(UPLDR_K.ini_file),
                          useniceprint=True)
            # INI file config (3/3)
            #   3. If not, os.path.dirname(sys.argv[0]), '../etc/uploadr.ini'
            if not check_base_ini_file(UPLDR_K.base_dir, UPLDR_K.etc_ini_file):
                NPR.niceerror(caught=True,
                              caughtprefix='+++ ',
                              caughtcode='663',
                              caughtmsg='Invalid sys.argv/etc INI file [{!s}].'
                              ' Exiting...'.format(UPLDR_K.etc_ini_file),
                              useniceprint=True)
                sys.exit(2)
            else:
                UPLDR_K.ini_file = UPLDR_K.etc_ini_file

    # Source configuration from ini_file
    logging.critical('FINAL ini_file:[%s]', UPLDR_K.ini_file)
    MY_CFG.readconfig(UPLDR_K.ini_file, ['Config'])
    if MY_CFG.processconfig():
        if MY_CFG.verifyconfig():
            pass
        else:
            raise ValueError('No config file found or incorrect config!')
    else:
        raise ValueError('No config file found or incorrect config!')

    # Rotating LOGGING level to err_file
    if MY_CFG.ROTATING_LOGGING:
        ROTATING_LOGGING = None
        if not os.path.isdir(os.path.dirname(MY_CFG.ROTATING_LOGGING_PATH)):
            NPR.niceerror(caught=True,
                          caughtprefix='+++ ',
                          caughtcode='663',
                          caughtmsg='Invalid ROTATING_LOGGING_PATH config.',
                          useniceprint=True)
        else:
            # Define a rotating file Handler which writes DEBUG messages
            # or higher to err_file
            ROTATING_LOGGING = logging.handlers.RotatingFileHandler(
                MY_CFG.ROTATING_LOGGING_PATH,
                maxBytes=MY_CFG.ROTATING_LOGGING_FILE_SIZE,
                backupCount=MY_CFG.ROTATING_LOGGING_FILE_COUNT)
            # Update rotating logging level as per LOGGING_LEVEL from INI file
            ROTATING_LOGGING.setLevel(MY_CFG.ROTATING_LOGGING_LEVEL)
            ROTATING_LOGGING.setFormatter(logging.Formatter(
                fmt='[' + str(UPLDR_K.Run) + ']' +
                '[%(asctime)s]:[%(processName)-11s]' +
                '[%(levelname)-8s]:[%(name)s] %(message)s',
                datefmt=UPLDR_K.TimeFormat))
            logging.getLogger().addHandler(ROTATING_LOGGING)

            # Allow multiprocessing rotating logging into a single file
            # CODING: may not work on Windows
            if PARSED_ARGS.processes and PARSED_ARGS.processes > 0:
                logging.debug('multiprocessing logging handler: Activating...')
                multiprocessing_logging.install_mp_handler()
                logging.info('multiprocessing logging handler: Activated.')

            logging.warning('----------- (V%s) Init Rotating '
                            '-----------(Log:%s)\n'
                            'Python version on this system: [%s]',
                            UPLDR_K.Version,
                            MY_CFG.LOGGING_LEVEL,
                            sys.version)

    # Update console logging level as per LOGGING_LEVEL from INI file
    CONSOLE_LOGGING.setLevel(MY_CFG.LOGGING_LEVEL)
    logging.warning('CONSOLE_LOGGING.setLevel=[%s] '
                    'ROTATING_LOGGING.setLevel/enabled?=[%s/%s] '
                    'MY_CFG.LOGGING_LEVEL=[%s]',
                    MY_CFG.LOGGING_LEVEL,
                    MY_CFG.ROTATING_LOGGING_LEVEL,
                    MY_CFG.ROTATING_LOGGING,
                    MY_CFG.LOGGING_LEVEL)

    logging.info('Output for FLICKR Configuration:\n%s',
                 pprint.pformat(MY_CFG.FLICKR))
    NPR.niceprint('Output for FLICKR Configuration:\n{!s}'
                  .format(pprint.pformat(MY_CFG.FLICKR)),
                  verbosity=3)

    # Ensure that only one instance of this script is running
    try:
        # FileLocker is an alias to portalocker (if available) or fcntl
        FILELOCK(open(MY_CFG.LOCK_PATH, 'w'),
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

NPR.niceprint('----------- (V{!s}) End -----------(Log:{!s})'
              .format(UPLDR_K.Version,
                      MY_CFG.LOGGING_LEVEL))
logging.warning('----------- (V%s) End -----------(Log:%s)',
                UPLDR_K.Version,
                MY_CFG.LOGGING_LEVEL)

logging_close_handlers()
