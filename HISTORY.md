Release History
===============

# "2.8.7"
    published_at: "2018-10-01T12:40:26Z"
* V2.8.7 Features: Masking sensitive data in logs. No delete option. Fixes & Refactoring. Code coverage and Python 3.7 testing.
        
## Fixes/Features
- Setup via PyPi
- Fixed #73: Weird issue on Synology with python installed from default packages (DO NOT INSTALL IT) . Updated README.
- Fixed #74: Initial logging has an erratic behaviour (Low priority)
- Fixed/Feature: uploadr.cron: Proper use of PREFIX and PATH settings
- Feature: At the end prints the total for (countflickr - countlocal) for easier reading.
- Feature #71: Suggestion: no.delete: New option `--no-delete-from-flickr` (under testing.Use at your own risk for now!)
- Feature #78: Enhancement: Mask sensitive data (like file name and Albums) on Logs. New option: `-m`/`-mask-sensitive`
- Cleaned up debugging of external modules namely multiprocessing logging.
- Testing with python 2.7, 3.6 and 3.7
- Refactored all DB function calls. Protected by error code hangling and lock usage whenm applicable

## Setup options:
   - (For alpha versions like this one) You can install from pip:
`pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple flickr-uploader==2.8.7a36 --prefix=~/apps/Python/ --no-cache-dir`
   - (For regular versions) You can install from pip:
`pip install flickr-uploader --prefix=~/apps/Python`
   - You can download and run install with command:
`python3 setup.py install --prefix=~/apps/Python --old-and-unmanageable`
   - You can download and run from local folder.
- uploadr.ini: **Note that uploadr.ini definition for path search** is changed:
   - Sets base folder with `FOLDER = os.path.abspath(os.getcwd())`
   - DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH are now relative to FOLDER, for example: `os.path.join(%(FOLDER)s, \"flickrdb\")`
- From v2.8.6 onwards it looks for `uploadr.ini` as follows:
   1. Use `--config-file` argument option to indicate where to find the file. Example `--config_file uploadr.ini`
   1. If not, `os.path.dirname(sys.argv[0])`. Example: ~/apps/Python/bin/uploadr.ini or ./uploadr.ini
   1. If not, `os.path.dirname(sys.argv[0]), '..', 'etc', 'uploadr.ini'`. Example: ~/apps/Python/etc/uploadr.ini

## Output Messages
- Adjustments on output and logging messages.
- As a reference from version 2.8.6: New set of options related to Rotating Error Logging added to uploadr.ini:
```
################################################################################
#   Output logging information into a rotating set of log file(s).
#       ROTATING_LOGGING to Enable/Disable
#       ROTATING_LOGGING_PATH location of folder/main logging filename
#       ROTATING_LOGGING_FILE_SIZE for maximum file size of each log file
#       ROTATING_LOGGING_FILE_COUNT for maximum count of old log files to keep
#       ROTATING_LOGGING_LEVEL Level Logging 
#           Check LOGGING_LEVEL setting for options.
#           Normally set ROTATING_LOGGING_LEVELto lower than LOGGING_LEVEL
################################################################################
ROTATING_LOGGING = True
ROTATING_LOGGING_PATH = os.path.join(os.path.dirname(sys.argv[0]), \"logs\", \"uploadr.err\")
ROTATING_LOGGING_FILE_SIZE = 25*1024*1024  # 25 MBytes
ROTATING_LOGGING_FILE_COUNT = 3
ROTATING_LOGGING_LEVEL = 30
```

## Environment and Coding
- Python 2.7 + 3.6 + 3.7 compatibility: use of \"# noqa\" as applicable
- Development now use coveralls.io to check source code coverage
- autopep8, PEP8, flakes and pylint3 (not all!) adjustments. Several pylint reaching now a rating of 9.45/10.00.
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- For installation: 
  - pip install flickr-uploader
  - setup.py (**optional use**)
  - or manual
- NicePrint:
   - use of staticmethods
   - New argument logalso
  - niceprocessedfiles new argument for adaptable output message 
- On upload failure: sleep for(configured on Konstants.py)  20s (instead of 10) to avoid duplicated uploaded files."
# "2.8.7.a36"
    published_at: "2018-09-23T20:52:57Z"
* "V2.8.7-alpha36 Features: Masking sensitive data in logs. No delete option. Fixes & Refactoring. Code coverage and Python 3.7 testing."
        
## Fixes/Features
- Setup via PyPi
- Fixed #73: Weird issue on Synology with python installed from default packages (DO NOT INSTALL IT) . Updated README.
- Fixed #74: Initial logging has an erratic behaviour (Low priority)
- Fixed/Feature: uploadr.cron: Proper use of PREFIX and PATH settings
- Feature: At the end prints the total for (countflickr - countlocal) for easier reading.
- Feature #71: Suggestion: no.delete: New option `--no-delete-from-flickr` (under testing.Use at your own risk for now!)
- Feature #78: Enhancement: Mask sensitive data (like file name and Albums) on Logs. New option: `-m`/`-mask-sensitive`
- Cleaned up debugging of external modules namely multiprocessing logging.
- Testing with python 2.7, 3.6 and 3.7
- Refactored all DB function calls. Protected by error code hangling and lock usage whenm applicable
- NicePrint use of staticmethods

## Setup options:
   - (For alpha versions like this one) You can install from pip:
`pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple flickr-uploader==2.8.7a36 --prefix=~/apps/Python/ --no-cache-dir`
   - (For regular versions) You can install from pip:
`pip install flickr-uploader --prefix=~/apps/Python`
   - You can download and run install with command:
`python3 setup.py install --prefix=~/apps/Python --old-and-unmanageable`
   - You can download and run from local folder.
- uploadr.ini: **Note that uploadr.ini definition for path search** is changed:
   - Sets base folder with `FOLDER = os.path.abspath(os.getcwd())`
   - DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH are now relative to FOLDER, for example: `os.path.join(%(FOLDER)s, \"flickrdb\")`
- From v2.8.6 onwards it looks for `uploadr.ini` as follows:
   1. Use `--config-file` argument option to indicate where to find the file. Example `--config_file uploadr.ini`
   1. If not, `os.path.dirname(sys.argv[0])`. Example: ~/apps/Python/bin/uploadr.ini or ./uploadr.ini
   1. If not, `os.path.dirname(sys.argv[0]), '..', 'etc', 'uploadr.ini'`. Example: ~/apps/Python/etc/uploadr.ini

## Output Messages
- Adjustments on output and logging messages.
- As a reference from version 2.8.6: New set of options related to Rotating Error Logging added to uploadr.ini:
```
################################################################################
#   Output logging information into a rotating set of log file(s).
#       ROTATING_LOGGING to Enable/Disable
#       ROTATING_LOGGING_PATH location of folder/main logging filename
#       ROTATING_LOGGING_FILE_SIZE for maximum file size of each log file
#       ROTATING_LOGGING_FILE_COUNT for maximum count of old log files to keep
#       ROTATING_LOGGING_LEVEL Level Logging 
#           Check LOGGING_LEVEL setting for options.
#           Normally set ROTATING_LOGGING_LEVELto lower than LOGGING_LEVEL
################################################################################
ROTATING_LOGGING = False
ROTATING_LOGGING_PATH = os.path.join(os.path.dirname(sys.argv[0]), \"logs\", \"uploadr.err\")
ROTATING_LOGGING_FILE_SIZE = 25*1024*1024  # 25 MBytes
ROTATING_LOGGING_FILE_COUNT = 3
ROTATING_LOGGING_LEVEL = 30
```

## Environment and Coding
- Python 2.7 + 3.6 + 3.7 compatibility: use of \"# noqa\" as applicable
- Development now use coveralls.io to check source code coverage
- autopep8, PEP8, flakes and pylint3 (not all!) adjustments. Several pylint reaching now a rating of 9.45/10.00.
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- For installation: 
  - pip install flickr-uploader
  - setup.py (**optional use**)
  - or mannual"
#  "2.8.6"
    published_at: "2018-06-23T16:37:36Z"
* "V2.8.6 Features: install via PyPi. New settings on uploadr.ini. Under the hood improvements/refactoring."
        
## Fixes/Features
- Setup via PyPi
- Several under the hood code refactoring, pylint3 check and more. 
   - Drop unused setting TOKEN_PATH.
   - Added verbosity control with argument (-v, -vv, etc...) on NicePrint class.
- Fix #46 Use current working directory to look for INI (uploadr.ini) file
- Now support for multiprocessing for feature: #68 Option to have Rotating Error Log written to files to keep size under control.
- Setup options:
   - You can install from pip:
`pip install flickr-uploader --prefix=~/apps/Python`
   - You can download and run install with command:
`python3 setup.py install --prefix=~/apps/Python --old-and-unmanageable`
   - You can download and run from local folder.
- uploadr.ini: **Note that uploadr.ini definition for path search** is changed:
   - Sets base folder with `FOLDER = os.path.abspath(os.getcwd())`
   - DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH are now relative to FOLDER, for example: `os.path.join(%(FOLDER)s, \"flickrdb\")`
- From v2.8.6 onwards it looks for `uploadr.ini` as follows:
   1. Use `--config-file` argument option to indicate where to find the file. Example `--config_file uploadr.ini`
   1. If not, `os.path.dirname(sys.argv[0])`. Example: ~/apps/Python/bin/uploadr.ini or ./uploadr.ini
   1. If not, `os.path.dirname(sys.argv[0]), '..', 'etc', 'uploadr.ini'`. Example: ~/apps/Python/etc/uploadr.ini

## Output Messages
- Adjustments on output and logging messages.
- Feature: #68 Option to have Rotating Error Log written to files to keep size under control.
- New set of options related to Rotating Error Logging added to uploadr.ini:
```
################################################################################
#   Output logging information into a rotating set of log file(s).
#       ROTATING_LOGGING to Enable/Disable
#       ROTATING_LOGGING_PATH location of folder/main logging filename
#       ROTATING_LOGGING_FILE_SIZE for maximum file size of each log file
#       ROTATING_LOGGING_FILE_COUNT for maximum count of old log files to keep
#       ROTATING_LOGGING_LEVEL Level Logging 
#           Check LOGGING_LEVEL setting for options.
#           Normally set ROTATING_LOGGING_LEVELto lower than LOGGING_LEVEL
################################################################################
ROTATING_LOGGING = False
ROTATING_LOGGING_PATH = os.path.join(os.path.dirname(sys.argv[0]), \"logs\", \"uploadr.err\")
ROTATING_LOGGING_FILE_SIZE = 25*1024*1024  # 25 MBytes
ROTATING_LOGGING_FILE_COUNT = 3
ROTATING_LOGGING_LEVEL = 30
```

## Environment and Coding
- Python 2.7 + 3.6 compatibility: use of \"# noqa\" as applicable
- autopep8, PEP8, flakes and pylint3 (not all!) adjustments
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- For installation: 
  - pip install flickr-uploader
  - setup.py (**optional use**)
  - or mannual"
#  "2.8.5"
    published_at: "2018-05-27T19:24:57Z"
* "V2.8.5 Features: authentication, rotating, FlickrAPI wrapper module, setup. Under the hood improvements/refactoring."
        
## Fixes/Features
- Several under the hood code refactoring, pylint3 check and more.
- Fix: #66 fix Flickr error: \"ValueError: invalid literal for int() with base 10\"
- Feature: #60 Initial authentication option (-a)
- Internal improvement: #64 Isolate and wrap around retry and try/except sequence to flickrapi function calls
- Feature: #68 Option to have Rotating Error Log written to files to keep size under control.
- Setup (**optional**):
   - You can run install with command:
`python3 setup.py install --prefix=~/apps/Python`
   - You can run installcfg to copy config files (.ini and .cron) to a designated folder with command:
`python3 setup.py installcfg --folder ~/apps/flickr-uploader`
- From v2.7.6 `uploadr.ini` configuration is searched from:
   -  `--config-file` argument
   - from the sys.argv[0] path (compatible with previous versions)

## Questions & Answers
- **Note that uploadr.ini definition for path search** of DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH still uses sys.argv[0] location as a basis.
- (to be) Updated installation notes on Readme.

## Output Messages
- Adjustments on output and logging messages.
- Feature: #68 Option to have Rotating Error Log written to files to keep size under control.
   - New set of options related to Rotating Error Logging added to uploadr.ini:
```
################################################################################
#   Output logging information into a rotating set of log file(s).
#       ROTATING_LOGGING to Enable/Disable
#       ROTATING_LOGGING_PATH location of folder/main logging filename
#       ROTATING_LOGGING_FILE_SIZE for maximum file size of each log file
#       ROTATING_LOGGING_FILE_COUNT for maximum count of old log files to keep
#       ROTATING_LOGGING_LEVEL Level Logging 
#           Check LOGGING_LEVEL setting for options.
#           Normally set ROTATING_LOGGING_LEVELto lower than LOGGING_LEVEL
################################################################################
ROTATING_LOGGING = False
ROTATING_LOGGING_PATH = os.path.join(os.path.dirname(sys.argv[0]), \"logs\", \"uploadr.err\")
ROTATING_LOGGING_FILE_SIZE = 25*1024*1024  # 25 MBytes
ROTATING_LOGGING_FILE_COUNT = 3
ROTATING_LOGGING_LEVEL = 30
```

## Environment and Coding
- Python 2.7 + 3.6 compatibility: use of \"# noqa\" as applicable
- autopep8, PEP8, flakes and pylint3 (not all!) adjustments
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- setup.py (**optional use**)
- setup.py installcfg (**optional use**)"
#  "2.8.1"
    published_at: "2018-05-06T16:18:20Z"
* "V2.8.1 Under the hood improvements/refactoring. Standardize multiprocessing processes."
        
## Fixes/Features
- Several under the hood code refactoring, avoid use of globals, use of (more) modules, pylint3 check, order of imports, remove unused import, docstrs, use logging % instead of .format; and more.
- #61 Use mprocessing function to setup multiprocessing and simplify code.
- Setup (**optional**):
   - You can run install with `python3 setup.py install --prefix=~/apps/Python`
- From v2.7.6 `uploadr.ini` configuration is searched from:
   -  `--config-file` argument
   - from the sys.argv[0] path (compatible with previous versions)
- Initial lock control (Linux/Windows compatible) to ensure only one copy is running was corrected.
- Exception handling on (more) sql functions.

## Questions & Answers
- **Note that uploadr.ini definition for path search** of DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH still uses sys.argv[0] location as a basis.
- (to be) Updated installation notes on Readme.

## Output Messages
- Adjustments on output and logging messages.

## Environment and Coding
- Python 2.7 + 3.6 compatibility: use of \"# noqa\" as applicable
- autopep8, PEP8, flakes and pylint3 (not all!) adjustments
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- setup.py (**optional use**)"
#  "2.8.0"
    published_at: "2018-04-27T17:11:03Z"
* "V2.8.0 Improved performance on Add Pics to Sets/Albums running in Multiprocessing mode"
        
## Fixes/Features
- #11  Added feature to improve performance on Add Pics to Sets(Albums)
- #57 Used control of closing connection to Database.
- Setup CONVERT_RAW_FILES to **True** on `uploadr.ini` configuration file. 
   - Uses external tool: [exiftool by Phil Harvey](https://sno.phy.queensu.ca/~phil/exiftool/).
- Dry run option (-n) also works wit convert RAW files.
- Setup (**optional**):
   - You can run install with `python3 setup.py install --prefix=~/apps/Python`
- From v2.7.6 `uploadr.ini` configuration is searched from:
   -  `--config-file` argument
   - from the sys.argv[0] path (compatible with previous versions)
- moved niceprocessedfiles function to niceprint module
- created mprocessing function for multiprocessing scenarios
- initial lock control to ensure only one copy is running was corrected
- exception handling on (more) sql functions

## Questions & Answers
- **Note that uploadr.ini definition for path search** of DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH still uses sys.argv[0] location as a basis.
- (to be) Updated installation notes on Readme.

## Output Messages
- Small adjustments on output messages.

## Environment and Coding
- Python 2.7 + 3.6 compatibility: use of \"# noqa\" as applicable
- autopep8, PEP8, flakes adjustments
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- Created setup.py (**optional use**)"
#  "2.7.8"
    published_at: "2018-04-22T18:03:33Z"
* "V2.7.8 convert Raw Files option with exiftool"
        
## Fixes/Features
- Added feature to allow convert RAW files into JPG for loading.
- Setup CONVERT_RAW_FILES to **True** on `uploadr.ini` configuration file. 
   - Uses external tool: [exiftool by Phil Harvey](https://sno.phy.queensu.ca/~phil/exiftool/).
- Dry run option (-n) also works wit convert RAW files.
- Setup (**optional**):
   - You can run install with `python3 setup.py install --prefix=~/apps/Python`
- From v2.7.6 `uploadr.ini` configuration is searched from:
   -  `--config-file` argument
   - from the sys.argv[0] path (compatible with previous versions)

## Questions & Answers
- **Note that uploadr.ini definition for path search** of DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH still uses sys.argv[0] location as a basis.
- (to be) Updated installation notes on Readme.

## Output Messages
- Small adjustments on output messages.

## Environment and Coding
- Python 2.7 + 3.6 compatibility: use of \"# noqa\" as applicable
- autopep8, PEP8, flakes adjustments
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- Created setup.py (**optional use**)"
#  "2.7.7"
    published_at: "2018-04-17T21:59:15Z"
* "V2.7.7 Compatibility with Windows (use of portalocker, if available), Fix #56"
        
## Fixes/Features
- For locking on Windows: portalocker (when available) for added compatibility (For Windows support). Use fcntl otherwise (thanks @belidzs and others!!)
- Fix for #56 (3 attempts to load file with exception \"038\".... aborts!)
- Setup (**optional**):
   - You can run install with `python3 setup.py install --prefix=~/apps/Python`
- From v2.7.6 `uploadr.ini` configuration is searched from:
   -  `--config-file` argument
   - from the sys.argv[0] path (compatible with previsous versions)

## Questions & Answers
- **Note that uploadr.ini definition for path search** of DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH still uses sys.argv[0] location as a basis.
- (to be) Updated installation notes on Readme.

## Output Messages
- Small adjustments on output messages.

## Environment and Coding
- Python 2.7 + 3.6 compatibility: use of \"# noqa\" as applicable
- autopep8, PEP8, flakes adjustments
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- Created setup.py (**optional use**)"
#  "2.7.6"
    published_at: "2018-04-15T16:29:20Z"
* "V2.7.6 Enhanced control on INI parameters. Improved UploadFile function. New setup.py (optional)"
        
## Fixes/Features
- Enhancement #7 apply further control on INI parameters. New configuration mechanism. Default values are included in the app. Ignores wrong values in INI file. Except for *api_key* and *secret* which you have to adjust, all others are preset.
- Enhancement #28 Revise upload sequence.
- More clear output messages on execution progress.
- Setup (**optional**):
   - You can run install with `python3 setup.py install --prefix=~/apps/Python`
- From v2.7.6 `uploadr.ini` configuration is searched from:
   -  `--config-file` argument
   - from the sys.argv[0] path (compatible with previsous versions)

## Questions & Answers
- **Note that uploadr.ini definition for path search** of DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH still uses sys.argv[0] location as a basis.
- (to be) Updated installation notes on Readme.

## Output Messages
- More clear output messages on excution progress.

## Environment and Coding
- Python 2.7 + 3.6 compatibility: use of \"# noqa\" as applicable
- autopep8, PEP8, flakes adjustments
- pytest --flakes & pytest --doctest-modules
- Runs several unittests
- Created setup.py (**optional**)"
#  "V2.7.3"
    published_at: "2018-03-29T23:02:46Z"
* "V2.7.3 Replace Video (#45), Code cleanup (autopep8, flakes adjustments, use of lib modules)"
        
## Fixes/Features
- I'm including a distribution tarball flickr-uploader-2.7.3.tar.gz for faster/easier download with the essential files and no test related files. The full; source code is still available of course!
- From v2.7.0 onwards, uploadr adds to Flickr an album tag to each pic. uploadr v2.7.0 will automatically update the previously loaded pics with such album tag, upon first run.
   - Version 2.7.1, 2.7.2 and 2.7.3 run in multiprocessing mode (use option -p) to add album tag. It limits function calls to flickr to 5 per second to avoid reaching the 3600 requests/hour of Flickr.
   - New option: --add-albums-migrate is *only* available to re-run assigning album tags to previously uploaded pics, should it be necessary and in case the automated process fails.
   - **PLEASE NOTE FOR LARGE LIBRARIES THIS 1st RUN:**
      - **MAY TAKE A WHILE. IN MY CASE ABOUT 10min FOR EACH 1000 PICS OR SO...**
      - **MAY SURPASS THE Flickr 3600 requests/hour LIMIT. SIMPLY RESTART AFTER SOME TIME & UNTIL COMPLETION**
- Confirmed resolution of issue #28
- #45 Delete/Upload to be able to replace Videos on Flickr

## Questions & Answers
- Updated installation notes on Readme.
- Readme includes master test result status (from travisCI)

## Output Messages
- Removed (some) multiprocessing messages from verbose

## Environment and Coding
- Python 2.7 + 3.6 compatibility: use of \"# nova\" as applicable
- autopep8, PEP8, flakes adjustments (thank you @cpb8010 for your sugestions)
- pytest --flakes & pytest --doctest-modules
- Reorganized order of Init message and import.
- Moved sections from file (uploadr.py) into CONTRIBUTING, TODO, README
- Included LICENSE.txt
- Version number defined in lib/__version__.py
- Created classes lib/niceprint.py, lib/UPLDRConstants.py, lib/rate_limited.py
- Setup several unittests
- Created setup.py (in trial)
- Addressed #23 (split into modules)"
#  "2.7.1"
    published_at: "2018-03-05T21:58:32Z"
* "V2.7.1 List bad files. Album tag on uploaded pics. Several performance, control and fixes."
## Fixes/Features
- New option (--list-bad-files)to list badfiles recorded no the Database (feature #27)
- Include Album as a PIC tag. To facilitate finding failed load pics (feature #29).
- From v2.7.0 onwards, uploadr adds to Flickr an album tag to each pic. uploadr v2.7.0 will automatically update the previously loaded pics with such album tag, upon first run.
   - Version 2.7.1 runs in multiprocessing mode (use option -p) to add album tag. It limits function calls to flickr to 5 per second to avoid reaching the 3600 requests/hour of Flickr.
   - New option: --add-albums-migrate is *only* available to re-run assigning album tags to previously uploaded pics, should it be necessary and in case the automated process fails.
   - **PLEASE NOTE FOR LARGE LIBRARIES THIS 1st RUN:**
      - **MAY TAKE A WHILE. IN MY CASE ABOUT 10min FOR EACH 1000 PICS OR SO...**
      - **MAY SURPASS THE Flickr 3600 requests/hour LIMIT. SIMPLY RESTART AFTER SOME TIME & UNTIL COMPLETION**
- Updated uploadr.cron file with more details. Adapt the previous file you currently already have working on your system.
- Handle orphanated PICs previously loaded without a Set.
- Register on badfiles also files to large reported by Flickrt on upload (feature #37).
- Reduce file system scannig time by not checking a file in an excluded folder (feature #36. Thanks @malys).
- To confirm full resolution on: Revise try/except on upload around except error '040' (issue #28).

## Questions & Answers
- Added several clarifications to Readme and Q&A section (issue #31 and #38. Thanks @ze6killer).

## Output Messages
- Display current vs total number of files processed.
- Adjusted niceprint of multiprocessing messages to apply only with verbose option.

## Environment and Coding
- Python 2.7 + 3.6 compatibility.
- Python 3.7-dev: Initial tests only.
- Imports module xml.etree.ElementTree in case is required to use function 'xml.etree.ElementTree.tostring' (feature #41)
- Helper class rate_limited and functions to rate limiting function calls with Python Decorators on external module (V2.7.1).
- Use flickrapi 2.4 on TravisCI tests (V2.7.1)
- Reorganized order of Init message and import.
- Reordered sys.exit codes.
- Additional protection on LOGGING_LEVEL definition.
- Function is_photo_already_uploaded: one additional result for PHOTO UPLOADED WITHOUT SET WITH ALBUM TAG when row exists on DB. Mark such row on the database files.set_id to null to force re-assigning to Album/Set on flickr.
- Addresses deleted file from local which is also deleted from flickr
- Created function getSetNameFromFile (V2.7.0)
- Adapted niceprint to print function name on new optional parameter (V2.7.0).
- Enhanced is_photo_already_uploaded function (V2.7.0).
"
#  "2.7.0"
    published_at: "2018-02-18T22:44:57Z"
* "Version 2.7.0 Tag pics with their album (similar to checksum)"
## Fixes/Features
- Include Album as a PIC tag. to facilitate finding failed load pics (feature #29).
- From v2.7.0 onwards, uploadr adds to Flickr an album tag to each pic. uploadr v2.7.0 will automatically update the previously loaded pics with such album tag, upon first run.
   -  **PLEASE NOTE FOR LARGE LIBRARIES THIS 1st RUN MAY TAKE A WHILE. IN MY CASE ABOUT 10min FOR EACH 1000 PICS OR SO...**
   - **AFTER A FEW HOURS RUNNING I'm getting \"flickrapi.exceptions.FlickrError: Error: 0: Sorry, the Flickr API service is not currently available.\" from FLICKR. I suppose caused by too many requests to the FLickr API. Simply restart until completion**
- New option: --add-albums-migrate is *only* available to re-run it, should it be necessary and in case the autoamted process fails.
- Handle orphanated PICs previously loaded without a Set.
- Register on badfiles also files to large reported by Flickrt on upload (feature #37).
- Display current vs total number of files processed.
- Reduce file system scannig time by not checking a file in an excluded folder (feature #36. Thanks @malys).
- To confirm full resolution on: Revise try/except on upload around except error '040' (issue #28).

## Questions & Answers
- Added several clarifications to Readme and Q&A section (issue #31 and #38. Thanks @ze6killer).

## Output Messages
- Display current vs total number of files processed.

## Environment and Coding
- Python 2.7 + 3.6 compatibility.
- Python 3.7-dev: Initial tests only. 
- Created function getSetNameFromFile.
- Adapted nuceprint to print function name on new otional parameter.
- Enhanced is_photo_already_uploaded function."
#  "2.6.7"
    published_at: "2018-02-03T14:56:01Z"
* "Version 2.6.7 (faster runs after 1st execution)"
## Fixes/Features
- Optimize calling md5Cecksum which results in huge gains in runs after the 1st one.
- README updated with further clarifications explanation on file structure and loading/replace/delete logic and more FAQs
- flush on printing progress information when in paralell processing to ensure ordered output.
- Enhancement #33: New option -u --not-is-already-uploaded to disable checking if file is already actually loaded on flickr

## Output Messages
- flush on printing progress information when in paralell processing to ensure ordered output of processed pics counter

## Environment and Coding
- Python 2 + 3 compatibility"
#  "2.6.6"
    published_at: "2018-01-20T15:27:46Z"
* "V2.6.6 Stable release fixes #26, #28, #31. Python 2 and 3 compatibility."
## Fixes/Features
- Clarified use of Task Scheduler/crontab/SLEEP_TIME on instructions
- adjusted some remarks
- Solved #26
- Solved #31
- retry function:
- fixed: function retry... wrong use of variable \"a\" not set in some cases... like error 121
- adjusted messages wiht prefix \"___\"
- logging.error on error ...instead of warning
uploadPhoto function fixes:
- more focused try/exception
- 1st attempt at #28: Revise try/except on upload around except error '040'
- better message on uploaded

## Output Messages
- Error messages and output messages adjustments

## Environment and Coding
- Python 2 + 3 compatibility
- Python 3 testing scenarios"
#  "2.6.5"
    published_at: "2018-01-01T19:52:11Z"
* "V2.6.5 Stability with more testing, Python 2 and 3 compatibility "
## Fixes/Features
- 2.6.4 plus fix for #26 logging level for error \"190\" 
- Enhancement #24 Python 2.7 and 3.6 compatibility.
- Test EXCLUDED_FOLDER and -f option. Included one more pic and album for testing.
- Fixes on cachedtoken
- Removed unused perms variable
- Added one more SQL SELECT error control

## Output Messages
- Corrected DB error messages and output messages adjustments
- Corrected and aligned the error codes.

## Environment and Coding
- Python 2 + 3 compatibility
- Python 3 testing scenarios
- Fixed several comments
- RemoveIgnoredMedia function with unicode Python 2/3
- Further testing options. Added uploadr_excluded.ini file for testing. .travis.yml adjusted"
#  "2.6.3"
    published_at: "2017-12-14T21:26:03Z"
* "Do not load duplicates, retry on error, fix output messages. Use of TravisCI for testing."
## Fixes/Features
- doctest isthisStringUnicode
- fixed wrong indent on replacePhoto
- check if exists compare unicode setname
- unicode character in pics and albums
- Avoid duplicated images in between loads (#15)
- retry on photosets.create
- retry on addPhoto
- corrected handling of return from addPhoto (via exception; via <err code xml> to be removed)

## Output Messages
- corrected DB error messages and output messages adjustments
- Corrected and aligned the error codes.
- Added function StrOutisThisStringUnicode
- IGNORED_REGEX will work with unicode file names
- uploadr.ini examples for use of IGNORED_REGEX
- added mimetype video/3gp

## Environment and Coding
- added use ot travisCI for continuous integration tests
- Heroku deployment plus Python 2+3 compatible exception handling
- included about 160 test images for upkloading into Flickr
- PEP8 adjustments
- handling null createResp
- Use of a wrapper function to repeat calls on flickr related functions: @retry 
- fix on Run identification
- edited function is_photo_already_uploaded"
#  "2.5.11"
    published_at: "2017-11-12T19:15:11Z"
* "V2.5.11 More Stable. good for testing."
- fixed replacePhoto to use fileobj instead of filename to cater for unicode file names.
- should fix issue #14 
- 1st step to address enhancement #15: debugging for duplicated photos (same checksum/md5, same title, same set name). Still does not fully prevent loading duplicates which namely occur due to errors. In princicple many loading errors are being avoided anyhow!
- created simplified function updatedVideoDat
- extended the use of reportError2 function (to be later renamed to reportError)
- protected more DB accesses with try/exception
- under testing.
- \"-s\" parameter to search for duplicates not operational yet"
#  "2.5.10"
    published_at: "2017-11-09T02:53:05Z"
* "V2.5.10 Good for testing. (I've ran with 28K pics)"
- addressed issue #12 and #13
- niceprint a + b -> niceprint a .format(b)
- niceprint error -> logging.error
- more error codes
- unicode on EXCLUDED_FOLDERS definition"
#  "2.4.4"
    published_at: "2017-11-01T12:03:06Z"
* "Fix for issue #5"
Template uploadr.ini file was wrong. Please load up this new uploadr.ini and reconfigure. Sorry!"
#  "2.4.1"
    published_at: "2017-11-01T04:25:43Z"
* "Enhanced  Multiprocessing mode to show number of loaded photos"
Addresses enhancement #3 
Fixes issue #4 "
#  "2.3.1"
    published_at: "2017-11-01T01:35:01Z"
* "Fix for  issue #2"
Database is now properly updated to PRAGMA user_version 2."
#  "V2.3.0"
    published_at: "2017-11-01T01:15:58Z"
* "Upload a directory of media to Flickr to use as a backup to your local storage"
by oPromessa, 2017, V2.02

* flickr-uploader designed for Synology Devices (will probably work on Windows, MAC and UNIX flavours)
* Upload a directory of media to Flickr to use as a backup to your local storage.
* Check Features, Requirements and Setup remarks on README.md

more info on https://github.com/oPromessa/flickr-uploader"
