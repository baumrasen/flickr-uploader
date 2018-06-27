# flickr-uploader
-----------------
by oPromessa, 2017, V2.8.6 [![Master Build Status](https://travis-ci.org/oPromessa/flickr-uploader.svg?branch=master)](https://travis-ci.org/oPromessa/flickr-uploader) [![Coverage Status](https://coveralls.io/repos/github/oPromessa/flickr-uploader/badge.svg)](https://coveralls.io/github/oPromessa/flickr-uploader)
* Published on [https://github.com/oPromessa/flickr-uploader/](https://github.com/oPromessa/flickr-uploader/)

## Description
--------------
* Upload a directory of media (pics/videos) to Flickr for showing off your pics
on the WEB and as a backup of your local storage.
* Check Features, Requirements and Setup remarks.
* flickr-uploader designed primarly for Synology Devices. 
   * Also works on Linux, Mac and Windows systems.

## Features
-----------
* Uploads both images and movies (JPG, PNG, GIF, AVI, MOV, 3GP files)
   * Personnaly I avoid PNG files which do not support EXIF info
* Multiple loadings in parallel is available (check -p option)
* Stores image information locally using a simple SQLite database
* Creates Flickr "Sets" (Albums) based on the folder name the media is in
  (getting existing sets from Flickr is managed also)
* Ignores unwanted directories (like ".picasabackup" for Picasa users or
  "@eaDir" for Synology NAS users) and you can easily add/configure more
  yourself. Check uploadr.ini config file.
* Allows specific files to be ignored (via regular expressions)
* Skips files that are over a configurable size (max flickr size is about 900MB)
* Reuploads modified images as well as Videos (via delete/upload).
* Automatically removes images from Flickr when they are removed from your
  local hard drive
* Optionally convert RAW files (with use of external tool: [exiftool by Phil Harvey](https://sno.phy.queensu.ca/~phil/exiftool/)).

THIS SCRIPT IS PROVIDED WITH NO WARRANTY WHATSOEVER.
PLEASE REVIEW THE SOURCE CODE TO MAKE SURE IT WILL WORK FOR YOUR NEEDS.
IF YOU FIND A BUG, PLEASE REPORT IT.

### How it works! An example...
#### Sample file structure
Consider this example to explain how files are uploaded into Sets/Albums on Flickr.

If you have the following folders and pics  (the name of the flickr Sets/Albums depends on the uploadr.ini file setting FULL_SET_NAME, but I normally use it as False):
```
/home/user/media/pic00.jpg
/home/user/media/Album1/pic01.jpg
/home/user/media/Album2/pic02.jpg
/home/user/media/Album3/pic03.jpg
/home/user/media/folder/Album4/pic04.jpg
/home/user/media/folder/Album4/Sub/pic041.jpg
/home/user/media/newfolder/Album4/pic042.jpg
/home/user/media/folderAlbum5/pic01.jpg
/home/user/media/folderAlbum5/Sub/pic051.jpg
```
#### Setting your source folder with  FILES_DIR
And you setup FILES_DIR
```bash
FILES_DIR=/home/user/media
```
You should get the following depending on how the setting FULL_SET_NAME is set:

| FilePathName | Set/Album Name (FULL_SET_NAME=False) | Set/Album Name (FULL_SET_NAME=True) | Pic | Remarks |
| ------------- | ------------- | ------------- | ------------- | ------------- |
| /home/user/media/pic00.jpg | media | . | pic00 | |
| /home/user/media/Album1/pic01.jpg | Album1 |  Album1 | pic01 | |
| /home/user/media/Album2/pic02.jpg | Album2 |  Album2 | pic02 | |
| /home/user/media/Album3/pic03.jpg | Album3 |  Album3 | pic03 | |
| /home/user/media/folder/Album4/pic04.jpg | Album4 | folder/Album4 | pic04 | |
| /home/user/media/folder/Album4/Sub/pic041.jpg | Sub  | folder/Album4/Sub  | pic041 | |
| /home/user/media/newfolder/Album4/pic042.jpg | Album4 | newfolder/Album4 | pic042 | |
| /home/user/media/Album5/pic01.jpg | Album5 |  Album5 | pic01 | Same pic as in Album01 is loaded twice as it's part of a different Album |
| /home/user/media/Album5/Sub/pic051.jpg | Sub |  Album5/Sub | pic051 | With FULL_SET_NAME=False it will go into Album "Sub" |

## Requirements
---------------
* Python 2.7+ (should work on DSM from Synology (v6.1), Windows and MAC)
* Also compatile with Python 3.6
* flicrkapi module. May need to install get-pip.py. (Instructions for
  Synology DSM below.)
* portalocker module for Windows systems. Not mandatory for Synology.
* File write access (for the token and local database)
* Flickr API key (free)
* exiftool, **only** if you intend to convert RAW files to JPG. [Install instructions here.](https://sno.phy.queensu.ca/%7Ephil/exiftool/install.html). Note: You need to also install the DSM Package Perl.

## Setup on Synology
--------------------
- Might work on other platforms like Windows also.
- *Side note:* don't be overwhelmed with this setup. They are quite straitghtforward.
- Summary steps:

1. Enable SSH access to Synology DSM Server. (Optionally) install Python 3.
2. Prepare a local folder location for Python modules install
3. Download and install pip
4. Download and install flickrapi
5. Download and install flickr-uploader

### 1.Enable SSH access to Synology DSM Server. (Optionally) install Python 3.
- Enable and access your Synology DSM via SSH with an admin user.
- Avoid the use of root for security reasons.
- (Optionally) install via the Synology DSM Packages the "Python 3" package (corresponds to version 3.5)

### 2. Prepare a local folder location for Python modules install.
- **IMPORTANT NOTE: To avoid messing up with the system files.**
- Create a local install destination directory/folder define and export PYTHONPATH variable (ex: for Python 2.7):
```bash
$ cd
$ mkdir apps
$ mkdir apps/Python
$ export PYTHONPATH=~/apps/Python/lib/python2.7/site-packages
```
- Or, for Python 3.5:
``` bash
$ export PYTHONPATH=~/apps/Python/lib/python3.5/site-packages
```
- Create also a `dev` directory/folder to use as working area where to download/extract the files/packages prior to intstallation:
```bash
$ cd
$ mkdir dev
dev$ cd dev
```
### 3. Download and install pip
- **IMPORTANT NOTE: pip allows you to more easily install python related modules/applications.**
- **Download** get-pip.py
- **Extract to** ~/dev
- And then **install** by running `python get-pip.py --prefix=~/apps/Python`
- Follow [these guidelines for PIP installation](https://pip.pypa.io/en/latest/installing/).
- **IMPORTANT NOTE: Make sure to use the --prefix parameter**
```bash
$ cd
$ cd dev
dev$ curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100 1603k  100 1603k    0     0  3828k      0 --:--:-- --:--:-- --:--:-- 3827k
dev$ python get-pip.py --prefix=~/apps/Python
Collecting pip
    Downloading pip-9.0.1-py2.py3-none-any.whl (1.3MB)
        100%  1.3MB 495kB/s
Collecting setuptools
    Downloading setuptools-36.6.0-py2.py3-none-any.whl (481kB)
        100%  481kB 1.3MB/s
Collecting wheel
    Downloading wheel-0.30.0-py2.py3-none-any.whl (49kB)
        100%  51kB 4.1MB/s
Installing collected packages: pip, setuptools, wheel
    Successfully installed pip setuptools wheel
```
### 4. Download and install flickrapi (2.4.0)

#### 4.1 OPTION #1 (recommended): With PIP (installed in step #3 above)
```bash
$ cd
$ cd dev
dev$ export PYTHONPATH=~/apps/Python/lib/python2.7/site-packages
dev$ pip install flickrapi --prefix=~/apps/Python
```

#### 4.2 OPTION #2: Mannually
- **Download** flickrapi-2.4.tar.gz from [PyPi.Python.Org](https://pypi.python.org/pypi/flickrapi).
- **Extract to** ~/dev and run `python setup.py install --prefix=~/apps/Python`
- **Make sure to use the --prefix parameter**
```bash
$ cd dev
dev$ wget https://files.pythonhosted.org/packages/b1/f1/d10fa0872e4f781c2ed47e94e728ecd3c1998f8c8d12e78c7329a25d0727/flickrapi-2.4.0.tar.gz
dev$ tar tzvf flickrapi-2.4.0.tar.gz
flickrapi-2.4.0/
flickrapi-2.4.0/CHANGELOG.md
flickrapi-2.4.0/MANIFEST.in
flickrapi-2.4.0/.coveragerc
flickrapi-2.4.0/LICENSE.txt
flickrapi-2.4.0/tox.ini
flickrapi-2.4.0/README.md
(...)
dev$ cd flickrapi-2.4.0
dev/flickrapi-2.4.0$ python setup.py install --prefix=~/apps/Python
python setup.py install --prefix=~/apps/Python
running install
running bdist_egg
running egg_info
writing requirements to flickrapi.egg-info/requires.txt
writing flickrapi.egg-info/PKG-INFO
(...)
zip_safe flag not set; analyzing archive contents...
Moving chardet-3.0.4-py2.7.egg to /xxx/xxx/xxx/apps/Python/lib/python2.7/site-packages
Adding chardet 3.0.4 to easy-install.pth file
Installing chardetect script to /xxx/xxx/xxx/apps/Python/bin

Installed /xxxx/xxx/xxx/apps/Python/lib/python3.5/site-packages/certifi-2018.4.16-py3.5.egg
Finished processing dependencies for flickrapi==2.4.0
```

###  5. Download and install flickr-uploader
#### 5.1 OPTION #1 (recommended): With PIP (installed in step #3 above)
- Now available on Pypi.org for installation also via PIP.
```bash
$ cd
$ cd dev
dev$ export PYTHONPATH=~/apps/Python/lib/python2.7/site-packages
dev$ pip install flickr-uploader --prefix=~/apps/Python
```
   * Installation also copies to '~/apps/Python/etc' folder the data files `uploadr.ini` and `uploadr.cron`

#### 5.2 OPTION #2: Mannually to be run from local folder
- Download mannually from GitHub [flickr-uploader/releases/latest](https://github.com/oPromessa/flickr-uploader/releases/latest).
- You can find under **Assets**:
   * the source code packages;
   * a distribution package Published on [https://github.com/oPromessa/flickr-uploader/releases/latest](https://github.com/oPromessa/flickr-uploader/releases/latest)
- Extract the contents of the elected tar file.
   * You can then run it from the current folder.
   * Edit the uploadr.ini as appropriate (check Configuration section)
```bash
$ cd
$ cd apps
apps$ wget https://github.com/oPromessa/flickr-uploader/releases/download/2.8.5/flickr-uploader-2.8.5.tar.gz
apps$ tar xzvf flickr-uploader-2.8.5.tar.gz
apps$ cd flickr-uploader-2.8.5
apps$ ./uploadr.py -a
```

#### 5.3 OPTION #3: Mannually to be run from `~/apps/Python/bin`
- Download mannually from GitHub [flickr-uploader/releases/latest](https://github.com/oPromessa/flickr-uploader/releases/latest).
- You can find under **Assets**:
   * the source code packages;
   * a distribution package Published on [https://github.com/oPromessa/flickr-uploader/releases/latest](https://github.com/oPromessa/flickr-uploader/releases/latest)
- Extract the contents of the elected tar file.
   * You can then run it from the current folder.
   * Edit the uploadr.ini as appropriate (check Configuration section)
```bash
$ cd
$ cd apps
apps$ wget https://github.com/oPromessa/flickr-uploader/releases/download/2.8.5/flickr-uploader-2.8.5.tar.gz
apps$ tar xzvf flickr-uploader-2.8.5.tar.gz
apps$ cd flickr-uploader-2.8.5
apps$ python2.7 setup.py install --prefix=~/apps/Python --old-and-unmanageable
```
   * Installation also copies to '~/apps/Python/etc' folder the data files `uploadr.ini` and `uploadr.cron`

## Configuration
----------------
Go to http://www.flickr.com/services/apps/create/apply and apply for an API
key.
* Edit the following variables in the uploadr.ini
```
FILES_DIR = "YourDir"
FLICKR = {
        "title"                 : "",
        "description"           : "",
        "tags"                  : "auto-upload",
        "is_public"             : "0",
        "is_friend"             : "0",
        "is_family"             : "0",
        "api_key"               : "Yourkey",
        "secret"                : "YourSecret"
        }
FLICKR["api_key"] = ""
FLICKR["secret"] = ""
EXCLUDED_FOLDERS = ["@eaDir","#recycle"]
IGNORED_REGEX = ['*[Ii][Gg][Nn][Oo][Rr][Ee]*', 'Private*']
ALLOWED_EXT = ["jpg","png","avi","mov","mpg","mp4","3gp"]
MANAGE_CHANGES = True
FULL_SET_NAME = False
```

Refer to https://www.flickr.com/services/api/upload.api.html for what each
of the upload arguments above correspond to for Flickr's API.

- Before running uploadr.py make sure you run the command below:
  - To avoid running this command exerytime you log-in into your system, follow the [notes on this link](https://scipher.wordpress.com/2010/05/10/setting-your-pythonpath-environment-variable-linuxunixosx/) to edit file ~/.bashrc and place this command there.
```bash
$  export PYTHONPATH=~/apps/Python/lib/python2.7/site-packages
```
- On the **first run** you need to authenticate the applicaiton against Flickr.
   - use the `-a` option
   - uploadr.py will provide you a URL/link which you need to run
```bash
$ cd dev
dev$ uploadr.py -a
Importing xml.etree.ElementTree...done. Continuing.
--------- (V2.7.7) Init:  ---------
Python version on this system: 3.6.3 (default, Oct  3 2017, 21:45:48)
[GCC 7.2.0]
[2965][2018.04.16 23:55:09]:[12758      ][PRINT   ]:[uploadr] --------- (V2.7.7) Start time: 2018.04.16 23:55:09 ---------(Log:40)
[2965][2018.04.16 23:55:09]:[12758      ][PRINT   ]:[uploadr] Setting up database:[/home/user/dev/flickrdb]
[2965][2018.04.16 23:55:09]:[12758      ][PRINT   ]:[uploadr] Database version: [3]
[2965][2018.04.16 23:55:09]:[12758      ][PRINT   ]:[uploadr] Completed database setup
[2965][2018.04.16 23:55:09]:[12758      ][PRINT   ]:[uploadr] Checking if token is available... if not will authenticate
[2965][2018.04.16 23:55:09]:[12758      ][PRINT   ]:[uploadr] Getting new token.
[2965][2018.04.16 23:55:09]:[12758      ][PRINT   ]:[uploadr] Copy and paste following authorizaiton URL in your browser to obtain Verifier Code.
https://www.flickr.com/services/oauth/authorize?oauth_token=xxxxxxxxxxxxxxxxx-xxxxxxxxxxxxxxxx&perms=delete
Verifier code (NNN-NNN-NNN):
```

- Following **runs** can be launched unattended:
```
 dev$ ./uploadr.py -v
```

## Usage/Arguments/Options
--------------------------
Place the file uploadr.py in any directory and run via ssh
(execution privs required).
It will crawl through all the files from the FILES_DIR directory and begin
the upload process.
```bash
$ ./uploadr.py
```
To check what files uploadr.py would upload and delete you can run the
script with option `--dry-run`:
```bash
$ ./uploadr.py --dry-run
```
Run `./uploadr.py --help` for up to the minute information on arguments:
```bash
[910][2018.06.22 01:58:57]:[5834       ][PRINT   ]:[uploadr] ----------- (V2.8.6) Start -----------(Log:40)
usage: uploadr.py [-h] [-C filename.ini] [-a] [-v] [-x] [-n] [-i TITLE]
                  [-e DESCRIPTION] [-t TAGS] [-l N] [-r] [-p P] [-u] [-d] [-b]
                  [-c] [-s] [-g] [--add-albums-migrate]

Upload files to Flickr. Uses uploadr.ini as config file.

optional arguments:
  -h, --help            show this help message and exit

Configuration related options:
  -C filename.ini, --config-file filename.ini
                        Optional configuration file. Default
                        is:[/home/ruler/Documents/GitHub/flickr-
                        uploader/uploadr.ini]
  -a, --authenticate    Performs/Verifies authentication with Flickr. To be
                        run on initial setup.Does not run any other option.

Verbose and dry-run options:
  -v, --verbose         Verbose output. Use -vv for more verbosity. See also
                        LOGGING_LEVEL value in INI file.
  -x, --verbose-progress
                        Provides progress indicator on each upload. See also
                        LOGGING_LEVEL value in INI file.
  -n, --dry-run         Dry run. No changes are actually performed.

Information options:
  -i TITLE, --title TITLE
                        Title for uploaded files. Overwrites title set in INI
                        config file. If not specified and not set in INI file,
                        it uses filename as title (*Recommended).
  -e DESCRIPTION, --description DESCRIPTION
                        Description for uploaded filesOverwrites description
                        set in INI file.
  -t TAGS, --tags TAGS  Space-separated tags for uploaded files. It appends to
                        the tags defined in INI file.
  -l N, --list-photos-not-in-set N
                        List as many as N photos (with tags) not in set.
                        Maximum listed photos is 500.

Processing related options:
  -r, --drip-feed       Wait a bit between uploading individual files.
  -p P, --processes P   Number of photos to upload simultaneously. Number of
                        process to assign pics to sets.
  -u, --not-is-already-uploaded
                        Do not check if file is already uploaded and exists on
                        flickr prior to uploading. Use this option for faster
                        INITIAL upload. Do not use it in subsequent uploads to
                        prevent/recover orphan pics without a set.
  -d, --daemon          Run forever as a daemon.Uploading every SLEEP_TIME
                        seconds. Please note it only performs upload/raw
                        convert/replace.

Handling bad and excluded files:
  -b, --bad-files       Save on database bad files to prevent continuous
                        uploading attempts. Bad files are files in your
                        Library that flickr does not recognize (Error 5) or
                        are too large (Error 8). Check also option -c.
  -c, --clean-bad-files
                        Resets the badfiles table/list to allow a new
                        uploading attempt for bad files. Bad files are files
                        in your Library that flickr does not recognize (Error
                        5) or are too large (Error 8). Check also option -b.
  -s, --list-bad-files  List the badfiles table/list.
  -g, --remove-excluded
                        Remove previously uploaded files, that are now being
                        excluded due to change of the INI file configuration
                        EXCLUDED_FOLDERS.NOTE: Option --remove-ignored was
                        dropped in favor of --remove-excluded.

Migrate to v2.7.0:
  --add-albums-migrate  From v2.7.0 onwards, uploadr adds to Flickr an album
                        tag to each pic. This option adds such tag to
                        previously loaded pics. uploadr v2.7.0 will perform
                        automatically such migration upon first run This
                        option is *only* available to re-run it, should it be
                        necessary.

by oPromessa, 2017, 2018
```

## Task Scheduler (cron)
------------------------
### On Synology systems, run with Task Scheduler (Synology/Control Panel)
- Log into your Synology system via Web interface.
   - Go to Control Panel-> Task Scheduler
   - Create a new "User Defined Script"
   - Adjust the run schedule settings, the email notifications
   - Under "Run Command" include a reference to the uploadr.cron file
`/full/path/to/uploadr.cron`
- Use sample file uploadr.cron added to the distribution and adapt to your needs.
- [Synology Help Article on Task Scheduler](https://www.synology.com/en-global/knowledgebase/DSM/help/DSM/AdminCenter/system_taskscheduler) may also be helpful.
- IMPORTANT: Do not use crontab directly. Having Task Scheduler replaces crontab.

### On Linux/Unix/Mac based systems, run via crontab
- Use  upload.cron added to the distribution and adapt to your needs.
- Use either "crontab -e" or vi /etc/crontab according to your system.
```bash
# cron entry (runs at the top of every hour)
0  *  *  *  * /full/path/to/uploadr.cron > /dev/null 2>&1
```

### Launch from the command line in Daemon mode (-d option).
- Recommendation is to use Task Scheduler or cron.
- With -d option it runs in daemon mode and checks for files every SLEEP_TIME seconds (as configured on uploadr.ini)
- It simply loads the files. It does not create Albums/Sets.
- SLEEP_TIME is only used in this case.
```bash
$ ./uploadr.py -v -d
```

## Recognition
--------------
Inspired by:
* https://github.com/sybrenstuvel/flickrapi
* http://micampe.it/things/flickruploadr
* https://github.com/joelmx/flickrUploadr

Makes dynamic use of the following libraries:
* https://github.com/jruere/multiprocessing-logging under **GNU LESSER GENERAL PUBLIC LICENSE**

## Final remarks
---------------
You may use this code however you see fit in any form whatsoever.
And enjoy!!!

## Questions & Answers
----------------------
* Q: Who is this script designed for?
   - Those people comfortable with the command line that want to backup their media on Flickr in full resolution.

* Q: Why don't you use OAuth?
   - I do! As of November 2017

* Q: Are you a python ninja?
   - No, sorry. I just picked up the language to write this script because python can easily be installed on a Synology Diskstation.

* Q: Is this script feature complete and fully tested?
   - Nope. It's a work in progress. I've tested it as needed for my needs, but it's possible to build additional features by contributing to the script.

* Q: How to automate it with a Synology NAS ?
   - First you will need to run script at least one time in a ssh client to get the token file.
     Refer to the "Task Scheduler (cron)" section above.
     Then with DSM 6.1, create an automate task, make it run once a day for example, and put this in the textbox without quotes "path_to_your_python_program path_to_your_script". For example, assuming you installed Python package from Synocommunity, command should look like "/usr/local/python/bin/python /volume1/script/flickr-uploader/uploadr.py".

* Q: What if I have different folders to sync?
   - the standard mode of operation should be to sync always the same main folder structure with all your subfolder/pics.
   - syncing different folders on each run *does work* and uploads new pics; but uploadr was not originally designed for that.
      - What happens to previously loaded pics depends if they still exist and Uploadr can still find them (depending if FILES_DIR was set as an absolute folder or relative folder path)
         - File to upload: /home/user/media/2014/05/05/photo.jpg
         - FULL_SET_NAME:
            - False: 05
            - True: 2014/05/05
   - Uploadr saves the (full or relative depending on FILES_DIR) path name for the pics loaded. So, event though you provide a new origin folder, if the previously loaded pics still exist on their original locations, they are not deleted. If they are deleted from such original location or uploadr has no access to them, then they will be deleted from flickr.
   - If using relative FILES_DIR and two files exist on the same subfolder, it will not be re-uploaded.
   - So, in a nutshell, too many issues if you play around changing the FILES_DIR location.


* Q: "my understanding is that this is a sync script, which means when I later delete a pic from a synced folder, it will get deleted from Flickr"
   - Yes a file removed locally will be deleted from Flickr.
   - *Remark*: I'm assuming in between each run you keep the contents of the flickrdb control database and do not remove it.

* Q: "What about previously existing folders (they didn't seem to get deleted)"
   - If all files from a folder (and corresponding Album on flickr) are deleted, then the actual Album will be also eliminated. Again, if you do not chnage the FILES_DIR in between runs.

* Q: What about when I sync a folder with the same name of a previously existing folder? (you mention
getting existing sets from Flickr is managed also
   - hmmm... if you mean "sync a folder" via setting FILES_DIR... it would depend if you use full or relative pathname on FILES_DIR. Check the section "Clarification" above. It will delete the files he cannot find locally.
   - hmmm... if you mean two subfolders with the same name, to which Set/Album will be added depends on the setting FULL_SET_NAME. Check the section "Clarification" above for example pic042.

* Q: What about when I run the script on ~/pictures/parent_folder/folder_A and then later on ~/pictures/parentfolder will the script recongize the folder_A within parentfolder as being the one it uploaded before becaues its content will have matching checksums?
   - Again it depends on FULL_SET_NAME setting and FILE_DIR being an absolute or relative path and the match is initially done by full pathname + filename. So, in your example ~/pictures will expand to a full path so it would recognize the same files and not upload them again.

* Q: I thought I read a mention of checksum as a way to detect file modification: what about the same file in 2 different folders, is it then upoad each time (in a set with the folder name) or only once?
   - same file on two folders loads up twice. Check example above with Album5/pic02.jpg

* Q: How to read the final report:
   - Initial Found Files: Number of files found for processing.
      - Bad Files:
         - Files which failed to load previously due to Flickr error 5 ("type not recognized") or 8 ("file to large")
         - Check explanation on "-b" and "-c" options.
         - The remark "some Bad files may no longer exist!" indicates that previously recorded badfiles may already been deleted from the local filesystem. Check possible use of "-c" option.
   - Photos count:
      - Local: Number of local pics found.
      - Flickr: Number of pics indicated by Flickr (may be off by 1)
      - Not in sets on Flickr: Indicates just that. It may indicate errors if it is bigger than 0, as all uploaded pics by uploadr should be on an Album. What I do normally, is to delete such pics from Flickr directly from the flickr/organize interface. But I've seen other users which have other tools uploading pics to Flickr to ignore this number.
```
 Initial Found Files:[   757]
          - Bad Files:[     7] = [   750]
          Note: some Bad files may no longer exist!
Photos count:
                Local:[   750]
               Flickr:[   750]
Not in sets on Flickr:[     0]
```

* Q: What happens if the local control Database (flickrdb) is deleted?
  - By re-running the program **without the -u opiotn** it will go thru your local files and check/search for already loaded pics with same checksum+Set and re-builds the local database.