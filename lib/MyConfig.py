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
import lib.NicePrint as NicePrint


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

        >>> import lib.MyConfig as MyConfig
        >>> CFG = MyConfig.MyConfig()
        >>> CFG.processconfig()
        True
        >>> ELog = CFG.LOGGING_LEVEL
        >>> CFG.verifyconfig()
        True
        >>> CFG.LOGGING_LEVEL = 'a'
        >>> CFG.verifyconfig()
        True
        >>> CFG.LOGGING_LEVEL == ELog
        True
        >>> CFG.ROTATING_LOGGING_FILE_SIZE == 25*1024*1024
        True
        >>> CFG.ROTATING_LOGGING_FILE_COUNT == 3
        True

    """
    # =====================================================================
    # Functions aliases
    #
    #   strunicodeout = from niceprint module
    # ---------------------------------------------------------------------
    npr = NicePrint.NicePrint()
    strunicodeout = npr.strunicodeout
    niceerror = npr.niceerror
    is_str_unicode = npr.is_str_unicode

    # Config section ----------------------------------------------------------
    INISections = ['Config']
    # Default configuration keys/values pairs ---------------------------------
    ini_keys = [
        'FOLDER',
        'FILES_DIR',
        'FLICKR',
        'SLEEP_TIME',
        'DRIP_TIME',
        'DB_PATH',
        'LOCK_PATH',
        'TOKEN_CACHE',
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
        'LOGGING_LEVEL',
        'ROTATING_LOGGING',
        'ROTATING_LOGGING_PATH',
        'ROTATING_LOGGING_FILE_SIZE',
        'ROTATING_LOGGING_FILE_COUNT',
        'ROTATING_LOGGING_LEVEL'
    ]
    # Default configuration keys/values pairs ---------------------------------
    INIvalues = [
        # FOLDER
        "os.path.abspath(os.getcwd())",
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
        # "os.path.join(os.path.dirname(sys.argv[0]), 'flickrdb')",
        # LOCK_PATH
        "os.path.join(os.getcwd(), '.flickrlock')",
        # "os.path.join(os.path.dirname(sys.argv[0]), '.flickrlock')",
        # TOKEN_CACHE
        "os.path.join(os.getcwd(), 'token')",
        # "os.path.join(os.path.dirname(sys.argv[0]), 'token')",
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
        # LOGGING_LEVEL (30 = logging.ERROR). Note: Affects doctests results
        "40",
        # ROTATING_LOGGING
        "False",
        # ROTATING_LOGGING_PATH
        # "os.path.abspath(os.path.join(os.getcwd(), 'uploadr.err'))",
        "os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]), "
        "'uploadr.err'))",
        # ROTATING_LOGGING_FILE_SIZE
        "25*1024*1024",  # 25 MBytes
        # ROTATING_LOGGING_FILE_COUNT
        "3",
        # ROTATING_LOGGING_LEVEL
        "30"
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
        self.__dict__ = dict(zip(self.ini_keys, self.INIvalues))

        if logging.getLogger().getEffectiveLevel() <= logging.DEBUG:
            logging.debug('\t\t\t\tDefault INI key/values pairs...')
            for item in sorted(self.__dict__):
                logging.debug('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                              .format(item,
                                      type(self.__dict__[item]),
                                      self.strunicodeout(
                                          self.__dict__[item])))

    # -------------------------------------------------------------------------
    # MyConfig.readconfig
    #
    # Use readconfig to obtain configuration from uploadr.ini
    # Look for [Config] section file uploadr.ini file
    def readconfig(self, cfg_filename, cfg_sections):
        """ readconfig

            Look for cfg_sections (noramlly [Config]) section in INI file

            cfg_filname  = INI filename with configuration
            cfg_sections = list of Sections to look for.
                           eg: ['Config'] or ['Config', 'Additional']

        """

        # Look for Configuration INI file -------------------------------------
        config = ConfigParser.ConfigParser()
        config.optionxform = str  # make option names case sensitive
        try:
            ini_file = None
            ini_file = config.read(cfg_filename)
            # Parse Configuration file and overwrite any values
            for name in cfg_sections:
                self.__dict__.update(config.items(name))

            # Find incorrect config keys on INI File and delete them
            dropkeys = [key for key in self.__dict__.keys()
                        if key not in self.ini_keys]
            logging.debug('dropkeys:[%s]', dropkeys)
            for key in dropkeys:
                logging.debug('del key:[%s]', key)
                del self.__dict__[key]
        except Exception as err:
            logging.critical('INI file: [%s] not found or '
                             'incorrect format: [%s]! Will attempt to use '
                             'default INI values.',
                             cfg_filename,
                             str(err))
        finally:
            # Allow to continue with default values...
            if not ini_file:
                raise ValueError('No config file or unrecoverable error!')

        if logging.getLogger().getEffectiveLevel() <= logging.INFO:
            logging.info('\t\t\t\tActive INI key/values pairs...')
            for item in sorted(self.__dict__):
                logging.info('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                             .format(item,
                                     type(self.__dict__[item]),
                                     self.strunicodeout(
                                         self.__dict__[item])))

    # -------------------------------------------------------------------------
    # MyConfig.processconfig
    #
    def processconfig(self):
        """ processconfig

            Evaluates configuration items. Uses default values if not valid.
        """
        # Default types for keys/values pairs ---------------------------------
        ini_types = [
            'str',   # 'FOLDER',
            'str',   # 'FILES_DIR',
            'dict',  # 'FLICKR',
            'int',   # 'SLEEP_TIME',
            'int',   # 'DRIP_TIME',
            'str',   # 'DB_PATH',
            'str',   # 'LOCK_PATH',
            'str',   # 'TOKEN_CACHE',
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
            'int',   # 'LOGGING_LEVEL',
            'bool',  # ROTATING_LOGGING
            'str',   # ROTATING_LOGGING_PATH,
            'int',   # ROTATING_LOGGING_FILE_SIZE,
            'int',   # ROTATING_LOGGING_FILE_COUNT,
            'int'    # ROTATING_LOGGING_LEVEL
        ]
        ini_check = dict(zip(self.ini_keys, ini_types))
        if logging.getLogger().getEffectiveLevel() <= logging.INFO:
            logging.debug('\t\t\t\tDefault INI key/type pairs...')
            for item in sorted(ini_check):
                logging.debug('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                              .format(item,
                                      type(ini_check[item]),
                                      self.strunicodeout(ini_check[item])))
        # Evaluate values
        for item in sorted(self.__dict__):
            logging.debug('Eval for : [{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                          .format(item,
                                  type(self.__dict__[item]),
                                  self.strunicodeout(self.__dict__[item])))

            try:
                if ini_check[item] in ('list', 'int', 'bool', 'str', 'dict'):
                    logging.debug('isinstance=%s',
                                  isinstance(eval(self.__dict__[item]),
                                             eval(ini_check[item])))
                    if not(isinstance(eval(self.__dict__[item]),
                                      eval(ini_check[item]))):
                        raise ValueError('Incorrect config item:[{!s}]'
                                         .format(item))

                else:
                    raise ValueError('Incorrect config item:[{!s}]'
                                     .format(item))
            except Exception:
                self.niceerror(caught=True,
                               caughtprefix='+++ ',
                               caughtcode='800',
                               caughtmsg='Caught an exception ini_check',
                               exceptsysinfo=True)
                logging.critical(
                    'Invalid INI value for:[%s] Using default value:[%s]',
                    item,
                    self.INIvalues[self.ini_keys.index(str(item))])
                # Using default value to avoid exiting.
                # Use verifyconfig  to confirm valid values.
                self.__dict__.update(dict(zip(
                    [item],
                    [self.INIvalues[self.ini_keys.index(str(item))]])))
            finally:
                self.__dict__[item] = eval(self.__dict__[item])
                logging.debug('Eval done: [{!s:20s}]/type:[{!s:13s}] '
                              '= [{!s:10s}]'
                              .format(item,
                                      type(self.__dict__[item]),
                                      self.strunicodeout(
                                          self.__dict__[item])))

        if logging.getLogger().getEffectiveLevel() <= logging.INFO:
            logging.info('\t\t\t\tProcessed INI key/values pairs...')
            for item in sorted(self.__dict__):
                logging.info('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                             .format(item,
                                     type(self.__dict__[item]),
                                     self.strunicodeout(
                                         self.__dict__[item])))

        return True

    # -------------------------------------------------------------------------
    # MyConfig.verifyconfig
    #
    def verifyconfig(self):
        """ verifyconfig

            Verifies configuration. Must be called after processconfig().
        """

        def verify_logging_level():
            """ verify_logging_level

                Verifies Logging related option is set to a valid value.
            """

            # Further specific processing... LOGGING_LEVELs
            for level in ['LOGGING_LEVEL', 'ROTATING_LOGGING_LEVEL']:
                if self.__dict__[level] not in\
                        [logging.NOTSET,
                         logging.DEBUG,
                         logging.INFO,
                         logging.WARNING,
                         logging.ERROR,
                         logging.CRITICAL]:
                    self.__dict__[level] = logging.ERROR
                # Convert LOGGING_LEVEL into int() for use in conditionals
                self.__dict__[level] = int(str(self.__dict__[level]))

            return True

        def verify_files_dir():
            """ verify_files_dir

                Checks folder is valid and exists.
            """

            result = True
            # Further specific processing... FOLDER, FILES_DIR
            #     Check if dir exists. Unicode Support
            for item in ['FOLDER', 'FILES_DIR']:

                logging.debug('verifyconfig for [%s]', item)
                if not self.is_str_unicode(self.__dict__[item]):
                    self.__dict__[item] = unicode(  # noqa
                        self.__dict__[item],
                        'utf-8') \
                        if sys.version_info < (3, ) \
                        else str(self.__dict__[item])

                if not os.path.isdir(self.__dict__[item]):
                    logging.critical('%s: [%s] is not a valid folder.',
                                     item,
                                     self.strunicodeout(self.__dict__[item]))
                    result = False

            return result

        def verify_paths():
            """ verify_paths

                Checks parent folder for item (file) is valid and exists for:
                      DB_PATH
                      LOCK_PATH
                      TOKEN_CACHE
            """

            result = True
            for item in ['DB_PATH',  # Check if basedir exists. Unicode Support
                         'LOCK_PATH',
                         'TOKEN_CACHE']:

                logging.debug('verifyconfig for [%s]', item)
                if not self.is_str_unicode(self.__dict__[item]):
                    self.__dict__[item] = unicode(  # noqa
                        self.__dict__[item],
                        'utf-8') \
                        if sys.version_info < (3, ) \
                        else str(self.__dict__[item])

                if (os.path.dirname(self.__dict__[item]) and
                        not os.path.isdir(
                            os.path.dirname(self.__dict__[item]))):
                    logging.critical('%s:[%s] is not in a valid folder:[%s].',
                                     item,
                                     self.strunicodeout(self.__dict__[item]),
                                     self.strunicodeout(os.path.dirname(
                                         self.__dict__[item])))
                    result = False
            return result

        def verify_rotating_path():
            """ verify_rotating_path

                Checks parent folder for item (file) is valid and exists.
                      ROTATING_LOGGING_PATH
            """

            result = True
            if self.__dict__['ROTATING_LOGGING']:
                for item in ['ROTATING_LOGGING_PATH']:
                    logging.debug('verifyconfig for [%s]', item)
                    if not self.is_str_unicode(self.__dict__[item]):
                        self.__dict__[item] = unicode(  # noqa
                            self.__dict__[item],
                            'utf-8') \
                            if sys.version_info < (3, ) \
                            else str(self.__dict__[item])

                    if (os.path.dirname(self.__dict__[item]) and
                            not os.path.isdir(
                                os.path.dirname(self.__dict__[item]))):
                        logging.critical('%s:[%s] is not in '
                                         'a valid folder:[%s].',
                                         item,
                                         self.strunicodeout(
                                             self.__dict__[item]),
                                         self.strunicodeout(os.path.dirname(
                                             self.__dict__[item])))
                        result = False
            return result

        def verify_raw_files():
            """ verify_raw_files

                Verify raw related configuration.
            """

            result = True
            if self.__dict__['CONVERT_RAW_FILES']:
                for item in ['RAW_TOOL_PATH']:
                    logging.debug('verifyconfig for [%s]', item)
                    logging.debug('RAW_TOOL_PATH/exiftool=[%s]',
                                  os.path.join(self.__dict__[item],
                                               'exiftool'))

                    if not self.is_str_unicode(self.__dict__[item]):
                        self.__dict__[item] = unicode(  # noqa
                            self.__dict__[item],
                            'utf-8') \
                            if sys.version_info < (3, ) \
                            else str(self.__dict__[item])

                    if not os.path.isdir(self.__dict__[item]):
                        logging.critical('%s: [%s] is not a valid folder.',
                                         item,
                                         self.strunicodeout(
                                             self.__dict__[item]))
                        result = False
                    elif not (
                            os.path.isfile(os.path.join(self.__dict__[item],
                                                        'exiftool')) and
                            os.access(os.path.join(self.__dict__[item],
                                                   'exiftool'),
                                      os.X_OK)):
                        logging.critical('%s: [%s] is not a valid executable.',
                                         item,
                                         os.path.join(self.__dict__[item],
                                                      'exiftool'))
                        result = False
            else:
                logging.debug('verifyconfig: [%s] is False: bypass for [%s]',
                              'CONVERT_RAW_FILES', 'RAW_TOOL_PATH')

            return result

        def verify_excluded_folders():
            """ verify_excluded_folders

                Further specific processing... EXCLUDED_FOLDERS
                    Read EXCLUDED_FOLDERS and convert them into Unicode folders
            """

            logging.debug('verifyconfig for [%s]', 'EXCLUDED_FOLDERS')
            in_excluded_folders = self.__dict__['EXCLUDED_FOLDERS']
            logging.debug('inEXCLUDED_FOLDERS=[%s]', in_excluded_folders)
            out_excluded_folders = []
            for folder in in_excluded_folders:
                if not self.is_str_unicode(folder):
                    out_excluded_folders.append(
                        unicode(folder, 'utf-8')  # noqa
                        if sys.version_info < (3, )
                        else str(folder))
                else:
                    out_excluded_folders.append(str(folder))
                logging.debug('folder from EXCLUDED_FOLDERS:[%s] '
                              'type:[%s]\n',
                              self.strunicodeout(out_excluded_folders[
                                  len(out_excluded_folders) - 1]),
                              type(out_excluded_folders[
                                  len(out_excluded_folders) - 1]))
            logging.info('outEXCLUDED_FOLDERS=[%s]', out_excluded_folders)
            self.__dict__.update(dict(zip(
                ['EXCLUDED_FOLDERS'],
                [out_excluded_folders])))

            return True

        def verify_ignored_files():
            """ verify_excluded_folders

                Further specific processing... IGNORED_REGEX
                Consider Unicode Regular expressions
            """

            for item in ['IGNORED_REGEX']:
                logging.debug('verifyconfig for [%s]', item)
                self.__dict__[item] = [re.compile(regex, re.UNICODE)
                                       for regex in self.__dict__[item]]
                logging.info('Number of IGNORED_REGEX entries:[%s]\n',
                             len(self.__dict__[item]))

            return True

        # ---------------------------------------------------------------------
        returnverify = True
        if not verify_logging_level():
            returnverify = False
        elif not verify_files_dir():
            returnverify = False
        elif not verify_paths():
            returnverify = False
        elif not verify_rotating_path():
            returnverify = False
        elif not verify_raw_files():
            returnverify = False
        elif not verify_excluded_folders():
            returnverify = False
        elif not verify_ignored_files():
            returnverify = False

        if logging.getLogger().getEffectiveLevel() <= logging.INFO:
            logging.info('\t\t\t\tVerified INI key/values pairs...')
            for item in sorted(self.__dict__):
                logging.info('[{!s:20s}]/type:[{!s:13s}] = [{!s:10s}]'
                             .format(item,
                                     type(self.__dict__[item]),
                                     self.strunicodeout(
                                         self.__dict__[item])))

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

    def launch_myconfig_test():
        """ launch_myconfig_test():

            myconfig test function
        """

        mycfg = MyConfig()
        if mycfg.processconfig():
            if mycfg.verifyconfig():
                print('Test Myconfig: Ok')
            else:
                print('Test Myconfig: Not Ok')

    # launch test function
    launch_myconfig_test()
