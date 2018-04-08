# flickr-uploader: TO DO
* by oPromessa, 2017, V2.7.3
* Published on https://github.com/oPromessa/flickr-uploader/

## Pending improvements
-----------------------
* converRawFiles is not tested. Also requires an exif tool to be installed
  and configured as RAW_TOOL_PATH in INI file. Make sure to leave
  CONVERT_RAW_FILES = False in INI file or use at your own risk.
* Consider using python module exiftool?
* Would be nice to update ALL tags on replacePhoto and not only the
  mandatory checksum tag as FLICKR maintains the tags from the first load.
* Regular Output needs to be aligned/simplified to include:
   * successful uploads
   * successful update of date/time in videos
   * successful replacement of photos
* Change code to insert on database prior to upload and then update result.
* Test if it Re-upload or not pictures removed from flickr Web interface.
* Enhancement #7: Extend INI File settings control for appropriate values
  to all parameters
   * Check error:  DuplicateSectionError or DuplicateOptionError.
   * Check also: api_key. KeyError(key)
* Align try/except handling within functions like people_get_photos or outside
  like photos_get_not_in_set
* **[NOT FULLY TESTED YET]** You can try and run (Let me know if it works!)
   * `python3 setup.py install --prefix=~/apps/Python`
   * `python3 setup.py installcfg --folder=~/apps/Python` to install config
  Need to align this change with 1) uploadr.ini change from dirname to getcwd
  and 2) uploadr.py use baseDir as a getcwd()
* Error 040 on upload (issue #28) try/exception flickrapi is not triggered
  within the inner scope and it does not reupload. Only IOError. HTTPException.
  Move also upload to @retry control! This may be the cause to some files not
  being added to their sets. Although subsequent runs should find and deal
  with this pending assignment to set.
* Apply multiprocessing to Add pics to sets. For 50K pics takes a long time
  (enhancemente #11)
* updatedVideoDate fails on three attempts (is it 'cause Flickr is processing
  the video? and raises error caught on #210! Next run does not update video
  date.

## Known issues
---------------
* AVOID using uploadr when performing massive delete operations on flicr.
  While deleting many files on flickr some of the function calls return
  values like the title of a Set as empty(None). This prompts printing
  information to fail with TypeError: cannot concatenate 'str' and
  'NoneType' objects. Added specific control on function upload:
  setName if setName is not None else 'None'
  BUT worst than that is that one will be saving on the local database
  sets with name (title) empty which will cause other functions to fail.
* If local flickrdb is deleted it will run is_photo_already_uploaded to
  search for already loaded pics with checksum+Set and re-build the
  local database.
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
* Arguments not fully tested:
   * -z (not yet fully developed)
* Functions not migrated...
   * convertRawFiles
* Arguments are parsed with get/set (Python 2.7 and 3.6 compatible) and not
  dictionary like accesse (Python 3.6 compatible only)

## Update History
-----------------
* Check releases at [https://github.com/oPromessa/flickr-uploader/](https://github.com/oPromessa/flickr-uploader/)