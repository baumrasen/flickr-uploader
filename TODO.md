# flickr-uploader: TO DO 
* by oPromessa, 2017, V2.7.1
* Published on https://github.com/oPromessa/flickr-uploader/

## Pending improvements/Known issues
------------------------------------
* AVOID using uploadr when performing massive delete operations on flicr.
  While deleting many files on flickr some of the function calls return
  values like the title of a Set as empty(None). This prompts printing
  information to fail with TypeError: cannot concatenate 'str' and
  'NoneType' objects. Added specific control on function upload:
  setName if setName is not None else 'None'
  BUT worst than that is that one will be saving on the local database
  sets with name (title) empty which will cause other functions to fail.
* converRawFiles is not tested. Also requires an exif tool to be installed
  and configured as RAW_TOOL_PATH in INI file. Make sure to leave
  CONVERT_RAW_FILES = False in INI file or use at your own risk.
* Consider using python module exiftool?
* Would be nice to update ALL tags on replacePhoto and not only the
  mandatory checksum tag as FLICKR maintains the tags from the first load.
* If local flickrdb is deleted it will re-upload entire local Library.
  It would be interesting to attempt to rebuild local database. With the
  exception of tags (would require use of exiftool) almost all other
  information could be obtained. On V2.6.8, the function
  is_photo_already_uploaded would already search pics with checksum+Set
  and, if it finds it it will update the local DB.
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
* Regular Output needs to be aligned/simplified to include:
   * successful uploads
   * successful update of date/time in videos
   * successful replacement of photos
* Change code to insert on database prior to upload and then update result.
* On first authenticate... removedeletemedia seems to fail
* Test if it Re-upload or not pictures removed from flickr Web interface.
* CODING: Should extend this control to other parameters (Enhancement #7)
   * Check error:  DuplicateSectionError or DuplicateOptionError.
   * Check also: api_key. KeyError(key)   
   
## Update History
* Functions to be migrated...
   * convertRawFiles