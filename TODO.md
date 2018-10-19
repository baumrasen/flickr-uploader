# flickr-uploader: TO DO
* by oPromessa, 2017, V2.8.0
* Published on https://github.com/oPromessa/flickr-uploader/

## Pending improvements
-----------------------

* Check open development issues at: https://github.com/oPromessa/flickr-uploader/issues
* Check CODING References within code
* Review/adjust pylint warnings/errors
* setup.py: drop installcfg option? May still be usable to place files in a user specific folder

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
  `setName if setName is not None else 'None'`
  BUT worst than that is that one will be saving on the local database
  sets with name (title) empty which will cause other functions to fail.
* When QPS (Queries per second) are very high during a certain period, Flickr
  does not provide back reliable information. For instance, photos.search
  may return X pics but not actually list them. Some controls are applied in the code
  to allow to circunvent this situation:
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
* In multiprocessing mode, when uploading additional files to your library
  the work is divided into sorted chunks by each process and it may occur
  that some processes have more work than others defeating the purpose
  of multiprocessing. When loading from scratch a big Library it works
  like a charm.

## Update History
-----------------
* Check releases at [https://github.com/oPromessa/flickr-uploader/releases](https://github.com/oPromessa/flickr-uploader/releases)
