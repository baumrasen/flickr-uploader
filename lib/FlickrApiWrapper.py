"""
    by oPromessa, 2018
    Published on https://github.com/oPromessa/flickr-uploader/

    FlickrApiWrapper = Helper functions to call flickrapi from
                       FlickrUploadr.Uploadr class

    CODING:
    Return codes = None => Error
                   Generate Exceptions? No
                   True/False/Error status?
"""

# -----------------------------------------------------------------------------
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function,
#    unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1

# -----------------------------------------------------------------------------
# Import section
#
import logging
import multiprocessing
import time
import random
import sqlite3 as lite
from functools import wraps
import flickrapi
# -----------------------------------------------------------------------------
# Helper class and functions to print messages.
import lib.NicePrint as NicePrint
# -----------------------------------------------------------------------------
# Helper class and functions to rate/pace limiting function calls and run a
# function multiple attempts/times on error
import lib.rate_limited as rate_limited


# =============================================================================
# Functions aliases
#
#   NPR.niceprint = from niceprint module
# -----------------------------------------------------------------------------
NPR = NicePrint.NicePrint()
niceerror = NPR.niceerror
retry = rate_limited.retry


# -----------------------------------------------------------------------------
def nu_flickrapi_fn(fn_name,
                    **fn_kwargs,
                    attempts=3,
                    waittime=5,
                    randtime=False):
    """ nu_flickrapi_fn
    
        Runs flickrapi fn_name function handing over **kwargs.
        It retries attempts, waittime, randtime with @retry
        Checks results isGood and provides feedback accordingly.
        Captures flicrkapi or BasicException error situations.
        
    """

    @retry(attempts=attempts, waittime=waittime, randtime=randtime)
    def retry_flickrapi_fn(kwargs):
        return fn_name(**kwargs)

    logging.info('Obtaining Cached token')
    logging.debug('TOKEN_CACHE:[%s]', token_cache_location)

    fn_result = True
    try:
        flickrobj = flickrapi.FlickrAPI(dict(
            api_key,
            api_secret,
            token_cache_location=token_cache_location))
    except flickrapi.exceptions.FlickrError as ex:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='000',
                  caughtmsg='Error in flickrapi.FlickrAPI',
                  exceptuse=True,
                  exceptcode=ex.code,
                  exceptmsg=ex,
                  useniceprint=True,
                  exceptsysinfo=True)
        fn_result = True
        
    if not fn_result:
        return None False  # Error


# -----------------------------------------------------------------------------
def nu_get_cached_token(self,
                        api_key,
                        api_secret,
                        token_cache_location='token',
                        perms='delete',
                        attempts=3,
                        waittime=5,
                        randtime=False):
    """ nu_get_cached_token
    
        Attempts to get the flickr token from disk.
        
        api_key, api_secret, token_cache_location, perms
    
        Returns the flickrapi object.
        The actual token: flickrobj.token_cache.token
    """

    @retry(attempts=attempts, waittime=waittime, randtime=randtime)
    def retry_flickrapi(kwargs):
        return flickrapi.FlickrAPI(**kwargs)

    logging.info('Obtaining Cached token')
    logging.debug('TOKEN_CACHE:[%s]', token_cache_location)

    fn_result = True
    try:
        flickrobj = flickrapi.FlickrAPI(dict(
            api_key,
            api_secret,
            token_cache_location=token_cache_location))
    except flickrapi.exceptions.FlickrError as ex:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='000',
                  caughtmsg='Error in flickrapi.FlickrAPI',
                  exceptuse=True,
                  exceptcode=ex.code,
                  exceptmsg=ex,
                  useniceprint=True,
                  exceptsysinfo=True)
        fn_result = True
        
    if not fn_result:
        return None False  # Error
        
    
    try:
        # Check if token permissions are correct.
        if flickrobj.token_valid(perms=perms):
            logging.info('Cached token obtained: [%s]',
                         flickrobj.token_cache.token)
            return flickrobj  # flickrobj.token_cache.token
        else:
            logging.warning('Token Non-Existant.')
            return None  # None
    except BaseException:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='000',
                  caughtmsg='Unexpected error in token_valid',
                  exceptsysinfo=True)
        raise    


def nu_photos_add_tags(self, photo_id, tags):
    """ nu_photos_add_tags

        Local Wrapper for Flickr photos.addTags
    """

    logging.info('photos_add_tags: photo_id:[%s] tags:[%s]',
                 photo_id, tags)
    photos_add_tagsResp = self.nuflickr.photos.addTags(
        photo_id=photo_id,
        tags=tags)
    return photos_add_tagsResp


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                        '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()
