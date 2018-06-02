# flickr-uploader: TO DO
* by oPromessa, 2017, V2.8.0
* Published on https://github.com/oPromessa/flickr-uploader/

## Pending improvements
-----------------------
* Test use of library https://github.com/jruere/multiprocessing-logging in Windows
* Pypi test install:
  `pip2.7 install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple flickr-uploader --prefix=~/apps/Python`
  Use flickr-uploader==2.8.6a1 to install a specific version (alpha1 in this case)
* python setup.py install: use --old-and-unmanageable option to data copy files.
  `python2.7 setup.py install --prefix=~/apps/Python --old-and-unmanageable`
* drop installcfg option? May still be usable to place files in a user specific folder
* Set PATHS based on a BASE Dir variable in INI file... all others to depend on this onw. How?
  os.path.abspath(os.path.join(os.getcwd(), os.path.pardir, "etc", "uploadr.ini"))
* Reconfirm the uploading sequence when -u option is set which
  affects isLoaded = False control variable
* "Check for duplicates/wrong checksum" on upload may not be working fully!
* Consider using python module exiftool?
* Would be nice to update ALL tags on replacePhoto and not only the
  mandatory checksum tag as FLICKR maintains the tags from the first load.
* Change code to insert on database prior to upload and then update result.
* CODING: REUPLOAD deleted files from Flickr...
  Test if it Re-uploads or not pictures removed/deleted from flickr Web
  interface; while they still exist on local filesystem and local DB.
  (without the -u option, it should find the file and update database).
  This should avoid errors on creating sets with invalid primarykey (photo id
  has changed while the actual checksum/album of the file is actually the same)
* Consider new option --remove-ignored to address IGNORED_REGEX changes
  similar to how --remove-excluded handles changes in EXCLUDED_FOLDERS.
* **[NOT FULLY TESTED YET]** You can try and run (Let me know if it works!)
   * pip install flickr-uploader --prefix=~/apps/Python
      * this will copy to 'PREFIX/etc' the data files uploadr.ini and uploadr.cron
      * uploadr.ini PATH setting must be switched from argv (as sys.prefix
      does not work!)...
   * `python3 setup.py install --prefix=~/apps/Python
   * `python3 setup.py installcfg --folder=~/apps/Python` to install config
  From v2.7.4 uploadr.ini is searched form CWD (current working directory)
  which allows to run upload.py form the --prefix/bin folder as it is
  installed wiht "python setup.py install". Note that uploadr.ini definition
  for DB_PATH, LOCK_PATH, TOKEN_CACHE and TOKEN_PATH as to be changed.
* When QPS (Queries per second) are very high during a certain period, Flickr
  does not provide back reliable information. For instance, photos.search
  may return X pics but not actually list them.
  ```python
  # CODING
        if (len(searchIsUploaded.find('photos').findall('photo')) == 0):
            logging.critical('xxx #E10 Error: '
                             'IndexError: searchIsUploaded yields '
                             'Index out of range. '
                             'Manually check file:[{!s}] '
                             'Flickr possibly overloaded!!! '
                             'Continuing with next image.'
                             .format(xfile))
             raise IOError('Unreliable FLickr return info')
  ```

## Known issues
---------------
* Performance (with options: "-u -p 30"):
         upload: 340 pics/min ~= 20.000 pics/hour.
   addfiletoset: ~1000 albums/65000pic = 17.000 pics/hour
  migrateAlbums: 300 pics/min ˜= 18.000 pics/hour
* AVOID using uploadr when performing massive delete operations on flicr.
  While deleting many files on flickr some of the function calls return
  values like the title of a Set as empty(None). This prompts printing
  information to fail with TypeError: cannot concatenate 'str' and
  'NoneType' objects. Added specific control on function upload:
  setName if setName is not None else 'None'
  BUT worst than that is that one will be saving on the local database
  sets with name (title) empty which will cause other functions to fail.
* In multiprocessing mode, when uploading additional files to your library
  the work is divided into sorted chunks by each process and it may occur
  that some processes have more work than others defeating the purpose
  of multiprocessing. When loading from scratch a big Library it works
  like a charm.
* If one changes the FILES_DIR folder and do not DELETE all from flickr,
  uploadr WILL not delete the files.
* If you reduce FILE_MAX_SIZE in settings, the previously loaded files
  (over such size) are not removed.
* If you change IGNORED_REGEX in settings, the previously loaded files
  (which match such regular expression) are not removed.

## Update History
-----------------
* Check releases at [https://github.com/oPromessa/flickr-uploader/releases](https://github.com/oPromessa/flickr-uploader/releases)
