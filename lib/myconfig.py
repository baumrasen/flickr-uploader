"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

    Helper class and functions to load, process and verify INI configuration.


    MyConfiguration = Helper class and functions to load, process and
                      verify INI configuration.

    processconfig   = Helper function ...
    verifyconfig    = Helper function ...
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
import os
import logging
import re
try:
    import ConfigParser as ConfigParser  # Python 2
except ImportError:
    import configparser as ConfigParser  # Python 3
from . import niceprint

# =============================================================================
# Functions aliases
#
#   StrUnicodeOut       = from niceprint module
# -----------------------------------------------------------------------------
np = niceprint.niceprint()
StrUnicodeOut = np.StrUnicodeOut
reportError = np.reportError


# -----------------------------------------------------------------------------
# class MyConfiguration to hangle Config file uploadr.ini for flickr-uploadr.
#
# Inits with default configuration values.
# Refer to contents of uploadr.ini for explanation on configuration
# parameters.
# Set default LOGGING_LEVEL value on INIValues based on:
#     Level     Numeric value
#     CRITICAL  50
#     ERROR     40
#     WARNING   30
#     INFO      20
#     DEBUG     10
#     NOTSET    0
#
class MyConfig(object):
    """ MyConfig

        Loads default configuration files. Overwrites with any specific values
        found on INI config file.

        >>> import lib.myconfig as myconfig
        >>> Cfg = myconfig.MyConfig()
        >>> Cfg.processconfig()
        True
        >>> ELog = Cfg.LOGGING_LEVEL
        >>> Cfg.verifyconfig()
        True
        >>> Cfg.verifyconfig()
        True
        >>> Cfg.LOGGING_LEVEL = 'a'
        >>> Cfg.verifyconfig()
        True
        >>> Cfg.LOGGING_LEVEL == ELog
        True

    """
    # Config section ----------------------------------------------------------
    INISections = ['Config']
    # Default configuration keys/values pairs ---------------------------------
    INIkeys = [
        'FILES_DIR',
        'FLICKR',
        'SLEEP_TIME',
        'DRIP_TIME',
        'DB_PATH',
        'LOCK_PATH',
        'TOKEN_CACHE',
        'TOKEN_PATH',
        'EXCLUDED_FOLDERS',
        'IGNORED_REGEX',
        'ALLOWED_EXT',
        'CONVERT_RAW_FILES',
        'RAW_EXT',
        'RAW_TOOL_PATH',
        'FILE_MAX_SIZE',
        'MANAGE_CHANGES',
        'FULL_SET_NAME',
        'MAX_SQL_ATTEMPTS',
        'MAX_UPLOAD_ATTEMPTS',
        'LOGGING_LEVEL'
    ]
    # Default configuration keys/values pairs ---------------------------------
    INIvalues = [
        # FILES_DIR
        "'.'",  # Other possible default: "'photos'",
        # FLICKR
        "{ 'title'       : '',\
           'description' : '',\
           'tags'        : 'auto-upload',\
           'is_public'   : '0',\
           'is_friend'   : '0',\
           'is_family'   : '0',\
           'api_key'     : 'api_key_not_defined',\
           'secret'      : 'secret_not_defined'\
        }",
        # SLEEP_TIME
        "1 * 60",
        # DRIP_TIME
        "1 * 60",
        #  DB_PATH
        "os.path.join(os.getcwd(), 'flickrdb')",
        # LOCK_PATH
        "os.path.join(os.getcwd(), '.flickrlock')",
        # TOKEN_CACHE
        "os.path.join(os.getcwd(), 'token')",
        # TOKEN_PATH
        "os.path.join(os.getcwd(), '.flickrToken')",
        # EXCLUDED_FOLDERS (need to process for unicode support)
        "['@eaDir','#recycle','.picasaoriginals','_ExcludeSync',\
          'Corel Auto-Preserve','Originals',\
          'Automatisch beibehalten von Corel']",
        # IGNORED_REGEX
        "[ ]",
        # "['IMG_[0-8]', '.+Ignore.+']",
        # ALLOWED_EXT
        "['jpg','png','avi','mov','mpg','mp4','3gp']",
        # CONVERT_RAW_FILES
        "False",
        # RAW_EXT
        "['3fr', 'ari', 'arw', 'bay', 'crw', 'cr2', 'cap', 'dcs',\
          'dcr', 'dng', 'drf', 'eip', 'erf', 'fff', 'iiq', 'k25',\
          'kdc', 'mdc', 'mef', 'mos', 'mrw', 'nef', 'nrw', 'obm',\
          'orf', 'pef', 'ptx', 'pxn', 'r3d', 'raf', 'raw', 'rwl',\
          'rw2', 'rwz', 'sr2', 'srf', 'srw', 'x3f' ]",
        # RAW_TOOL_PATH
        "'/usr/bin/'",
        # FILE_MAX_SIZE
        "50000000",
        # MANAGE_CHANGES
        "True",
        # FULL_SET_NAME
        "False",
        #  MAX_SQL_ATTEMPTS
        "3",
        # MAX_UPLOAD_ATTEMPTS
        "10",
        # LOGGING_LEVEL (40 = logging.ERROR)
        "40"
    ]

    # -------------------------------------------------------------------------
    # MyConfig.__init__
    #
    # Inits with default configuration values.
    #
    def __init__(self):
        """__init__
        """

        # Assume default values into class dictionary of values ---------------
        self.__dict__ = dict(zip(self.INIkeys, self.INIvalues))

        if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
            logging.debug('\t\t\t\tDefault INI key/values pairs...')
            for item in sorted(self.__dict__):
                logging.debug('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                              .format(item,
                                      type(self.__dict__[item]),
                                      StrUnicodeOut(self.__dict__[item])))

    # -------------------------------------------------------------------------
    # MyConfig.readconfig
    #
    # Use readconfig to obtain configuration from uploadr.ini
    # Look for [Config] section file uploadr.ini file
    def readconfig(self, cfg_filename, cfg_Sections=INISections):
        """ readconfig
        """

        # Look for Configuration INI file -------------------------------------
        config = ConfigParser.ConfigParser()
        config.optionxform = str  # make option names case sensitive
        try:
            INIFile = None
            INIFile = config.read(cfg_filename)
            for name in cfg_Sections:
                self.__dict__.update(config.items(name))

            # Find incorrect config keys on INI File and delete them
            dropkeys = [key for key in self.__dict__.keys()
                        if key not in self.INIkeys]
            logging.debug('dropkeys:[{!s}]'.format(dropkeys))
            for key in dropkeys:
                logging.debug('del key:[{!s}]'.format(key))
                del self.__dict__[key]
        except Exception as err:
            logging.critical('INI file: [{!s}] not found or '
                             'incorrect format: [{!s}]! Will attempt to use '
                             'default INI values.'
                             .format(cfg_filename, str(err)))
        finally:
            # Allow to continue with default values...
            if not INIFile:
                raise ValueError('No config file or unrecoverable error!')

        # Parse Configuration file and overwrite any values -------------------
        # pprint.pprint(config.items(cfg_Sections[0]))

        if logging.getLogger().getEffectiveLevel() <= logging.INFO:
            logging.info('\t\t\t\tActive INI key/values pairs...')
            for item in sorted(self.__dict__):
                logging.info('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                             .format(item,
                                     type(self.__dict__[item]),
                                     StrUnicodeOut(self.__dict__[item])))

    # -------------------------------------------------------------------------
    # MyConfig.processconfig
    #
    def processconfig(self):
        """ processconfig
        """
        # Default types for keys/values pairs ---------------------------------
        INItypes = [
            'str',   # 'FILES_DIR',
            'dict',  # 'FLICKR',
            'int',   # 'SLEEP_TIME',
            'int',   # 'DRIP_TIME',
            'str',   # 'DB_PATH',
            'str',   # 'LOCK_PATH',
            'str',   # 'TOKEN_CACHE',
            'str',   # 'TOKEN_PATH',
            'list',  # 'EXCLUDED_FOLDERS',
            'list',  # 'IGNORED_REGEX',
            'list',  # 'ALLOWED_EXT',
            'bool',  # 'CONVERT_RAW_FILES',
            'list',  # 'RAW_EXT',
            'str',   # 'RAW_TOOL_PATH',
            'int',   # 'FILE_MAX_SIZE',
            'bool',  # 'MANAGE_CHANGES',
            'bool',  # 'FULL_SET_NAME',
            'int',   # 'MAX_SQL_ATTEMPTS',
            'int',   # 'MAX_UPLOAD_ATTEMPTS',
            'int'    # 'LOGGING_LEVEL'
        ]
        INIcheck = dict(zip(self.INIkeys, INItypes))
        if logging.getLogger().getEffectiveLevel() <= logging.INFO:
            logging.debug('\t\t\t\tDefault INI key/type pairs...')
            for item in sorted(INIcheck):
                logging.debug('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                              .format(item,
                                      type(INIcheck[item]),
                                      StrUnicodeOut(INIcheck[item])))
        # Evaluate values
        for item in sorted(self.__dict__):
            logging.debug('Eval for : [{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                          .format(item,
                                  type(self.__dict__[item]),
                                  StrUnicodeOut(self.__dict__[item])))

            try:
                if INIcheck[item] in ('list', 'int', 'bool', 'str', 'dict'):
                    logging.debug('isinstance={!s}'
                                  .format(
                                      isinstance(eval(self.__dict__[item]),
                                                 eval(INIcheck[item]))))
                    if not(isinstance(eval(self.__dict__[item]),
                                      eval(INIcheck[item]))):
                        raise
                else:
                    raise
            except BaseException:
                reportError(Caught=True,
                            CaughtPrefix='+++ ',
                            CaughtCode='999',
                            CaughtMsg='Caught an exception INIcheck',
                            exceptSysInfo=True)
                logging.critical('Invalid INI value for:[{!s}] '
                                 'Using default value:[{!s}]'
                                 .format(item,
                                         self.INIvalues[
                                             self.INIkeys.index(str(item))]))
                # Use default value or exit...
                self.__dict__.update(dict(zip(
                    [item],
                    [self.INIvalues[self.INIkeys.index(str(item))]])))
            finally:
                self.__dict__[item] = eval(self.__dict__[item])
                logging.debug('Eval done: [{!s:20s}]/type:[{!s:13s}] '
                              '= [{!s:10s}]'
                              .format(item,
                                      type(self.__dict__[item]),
                                      StrUnicodeOut(self.__dict__[item])))

        if logging.getLogger().getEffectiveLevel() <= logging.INFO:
            logging.info('\t\t\t\tProcessed INI key/values pairs...')
            for item in sorted(self.__dict__):
                logging.info('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                             .format(item,
                                     type(self.__dict__[item]),
                                     StrUnicodeOut(self.__dict__[item])))

        return True

    # -------------------------------------------------------------------------
    # MyConfig.verifyconfig
    #
    def verifyconfig(self):
        """ verifyconfig
        """

        returnverify = True
        # Further specific processing... LOGGING_LEVEL
        if self.__dict__['LOGGING_LEVEL'] not in\
                [logging.NOTSET,
                 logging.DEBUG,
                 logging.INFO,
                 logging.WARNING,
                 logging.ERROR,
                 logging.CRITICAL]:
            self.__dict__['LOGGING_LEVEL'] = logging.ERROR
        # Convert LOGGING_LEVEL into int() for later use in conditionals
        self.__dict__['LOGGING_LEVEL'] = int(str(
            self.__dict__['LOGGING_LEVEL']))

        # Further specific processing... FILES_DIR
        for item in ['FILES_DIR']:  # Check if dir exists. Unicode Support
            logging.debug('verifyconfig for [{!s}]'.format(item))
            if not(np.isThisStringUnicode(self.__dict__[item])):
                self.__dict__[item] = unicode(  # noqa
                                          self.__dict__[item],
                                          'utf-8') \
                                      if sys.version_info < (3, ) \
                                      else str(self.__dict__[item])
            if not os.path.isdir(self.__dict__[item]):
                logging.critical('{!s}: [{!s}] is not a valid folder.'
                                 .format(item,
                                         StrUnicodeOut(self.__dict__[item])))
                returnverify = False

        # Further specific processing...
        #       DB_PATH
        #       LOCK_PATH
        #       TOKEN_CACHE
        #       TOKEN_PATH
        for item in ['DB_PATH',  # Check if basedir exists. Unicode Support
                     'LOCK_PATH',
                     'TOKEN_CACHE',
                     'TOKEN_PATH']:
            logging.debug('verifyconfig for [{!s}]'.format(item))
            if not(np.isThisStringUnicode(self.__dict__[item])):
                self.__dict__[item] = unicode(  # noqa
                                          self.__dict__[item],
                                          'utf-8') \
                                      if sys.version_info < (3, ) \
                                      else str(self.__dict__[item])
            if not os.path.isdir(os.path.dirname(self.__dict__[item])):
                logging.critical('{!s}:[{!s}] is not in a valid folder:[{!s}].'
                                 .format(item,
                                         StrUnicodeOut(self.__dict__[item]),
                                         StrUnicodeOut(os.path.dirname(
                                             self.__dict__[item]))
                                         ))
                returnverify = False

        if self.__dict__['CONVERT_RAW_FILES'] == True:
            for item in ['RAW_TOOL_PATH']:
                logging.debug('verifyconfig for [{!s}]'.format(item))
                logging.debug('RAW_TOOL_PATH/exiftool=[{!s}]'
                              .format(os.path.join(self.__dict__[item],
                                                   'exiftool')))

                if not(np.isThisStringUnicode(self.__dict__[item])):
                    self.__dict__[item] = unicode(  # noqa
                                              self.__dict__[item],
                                              'utf-8') \
                                          if sys.version_info < (3, ) \
                                          else str(self.__dict__[item])

                if not os.path.isdir(self.__dict__[item]):
                    logging.critical('{!s}:[{!s}] is not a valid folder.'
                                     .format(item,
                                             StrUnicodeOut(
                                                self.__dict__[item])))
                    returnverify = False
                elif not (
                    os.path.isfile(os.path.join(self.__dict__[item],
                                                'exiftool'))
                    and os.access(os.path.join(self.__dict__[item],
                                               'exiftool'),
                                  os.X_OK)):
                    logging.critical('{!s}: [{!s}] is not a valid executable.'
                                     .format(item,
                                             os.path.join(self.__dict__[item],
                                                          'exiftool')))
                    returnverify = False
        else:
            logging.debug('verifyconfig: [{!s}] is False: bypass for [{!s}]'
                          .format('CONVERT_RAW_FILES', 'RAW_TOOL_PATH'))

        # Further specific processing... EXCLUDED_FOLDERS
        #     Read EXCLUDED_FOLDERS and convert them into Unicode folders
        logging.debug('verifyconfig for [{!s}]'.format('EXCLUDED_FOLDERS'))
        inEXCLUDED_FOLDERS = self.__dict__['EXCLUDED_FOLDERS']
        logging.debug('inEXCLUDED_FOLDERS=[{!s}]'
                      .format(inEXCLUDED_FOLDERS))
        outEXCLUDED_FOLDERS = []
        for folder in inEXCLUDED_FOLDERS:
            if not(np.isThisStringUnicode(folder)):
                outEXCLUDED_FOLDERS.append(unicode(folder, 'utf-8')  # noqa
                                           if sys.version_info < (3, )
                                           else str(folder))
            else:
                outEXCLUDED_FOLDERS.append(str(folder))
            logging.debug('folder from EXCLUDED_FOLDERS:[{!s}] '
                          'type:[{!s}]\n'
                          .format(
                              StrUnicodeOut(outEXCLUDED_FOLDERS[
                                  len(outEXCLUDED_FOLDERS) - 1]),
                              type(outEXCLUDED_FOLDERS[
                                  len(outEXCLUDED_FOLDERS) - 1])))
        logging.info('outEXCLUDED_FOLDERS=[{!s}]'
                     .format(outEXCLUDED_FOLDERS))
        self.__dict__.update(dict(zip(
            ['EXCLUDED_FOLDERS'],
            [outEXCLUDED_FOLDERS])))

        # Further specific processing... IGNORED_REGEX
        # Consider Unicode Regular expressions
        for item in ['IGNORED_REGEX']:
            logging.debug('verifyconfig for [{!s}]'.format(item))
            self.__dict__[item] = [re.compile(regex, re.UNICODE)
                                   for regex in self.__dict__[item]]
            logging.info('Number of IGNORED_REGEX entries:[{!s}]\n'
                         .format(len(self.__dict__[item])))

        # ---------------------------------------------------------------------
        if logging.getLogger().getEffectiveLevel() <= logging.INFO:
            logging.info('\t\t\t\tVerified INI key/values pairs...')
            for item in sorted(self.__dict__):
                logging.info('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                             .format(item,
                                     type(self.__dict__[item]),
                                     StrUnicodeOut(self.__dict__[item])))

        return returnverify


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                               '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()

    # Comment following line to allow further debugging/testing
    # sys.exit(0)

    import lib.myconfig as myconfig

    Cfg = myconfig.MyConfig()
    if Cfg.processconfig():
        if Cfg.verifyconfig():
            print('Test Myconfig: Ok')
        else:
            print('Test Myconfig: Not Ok')
