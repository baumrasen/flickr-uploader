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
try:
    import httplib as httplib      # Python 2
except ImportError:
    import http.client as httplib  # Python 3
import xml
# Avoids error on some systems:
#    AttributeError: 'module' object has no attribute 'etree'
#    on logging.info(xml.etree.ElementTree.tostring(...
try:
    DUMMYXML = xml.etree.ElementTree.tostring(
        xml.etree.ElementTree.Element('xml.etree'),
        encoding='utf-8',
        method='xml')
except AttributeError:
    try:
        import xml.etree.ElementTree
    except ImportError:
        raise
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
# isGood
#
# Checks if res.attrib['stat'] == "ok"
#
def isGood(res):
    """ isGood

        Check res is not None and res.attrib['stat'] == "ok" for XML object
    """
    if res is None:
        return False
    elif not res == "" and res.attrib['stat'] == "ok":
        return True
    else:
        return False


# -----------------------------------------------------------------------------
def nu_flickrapi_fn(fn_name,
                    fn_args=(),
                    fn_kwargs=dict(),
                    attempts=3,
                    waittime=5,
                    randtime=False,
                    caughtcode='000'):
    """ nu_flickrapi_fn

        Runs flickrapi fn_name function handing over **fn_kwargs.
        It retries attempts, waittime, randtime with @retry
        Checks results isGood and provides feedback accordingly.
        Captures flicrkapi or BasicException error situations.
        caughtcode to report on exception error.

        Returns:
            fn_success = True/False
            fn_result  = Actual flickrapi function call result
            fn_errcode = error reported by flickrapi exception
    """

    @retry(attempts=attempts, waittime=waittime, randtime=randtime)
    def retry_flickrapi_fn(kwargs):
        return fn_name(**kwargs)

    logging.info('fn:[%s] attempts:[%s] waittime:[%s] randtime:[%s]',
                 fn_name.__name__, attempts, waittime, randtime)

    if logging.getLogger().getEffectiveLevel() <= logging.INFO:
        for i, arg in enumerate(fn_args):
            logging.info('fn:[%s] arg[%s]={%s}', fn_name.__name__, i, arg)
        for name, value in fn_kwargs.items():
            logging.info('fn:[%s] kwarg[%s]=[%s]',
                         fn_name.__name__, name, value)

    fn_success = False
    fn_result = None
    fn_errcode = 0
    try:
        fn_result = retry_flickrapi_fn(fn_kwargs)
    except flickrapi.exceptions.FlickrError as flickr_ex:
        fn_errcode = flickr_ex.code
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode=caughtcode,
                  caughtmsg='Flickrapi exception on [{!s}]'
                  .format(fn_name.__name__),
                  exceptuse=True,
                  exceptcode=flickr_ex.code,
                  exceptmsg=flickr_ex,
                  useniceprint=True,
                  exceptsysinfo=True)
    except (IOError, httplib.HTTPException):
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode=caughtcode,
                  caughtmsg='Caught IO/HTTP Error on [{!s}]'
                  .format(fn_name.__name__))
    except Exception as exc:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode=caughtcode,
                  caughtmsg='Exception on [{!s}]'.format(fn_name.__name__),
                  exceptuse=True,
                  exceptmsg=exc,
                  useniceprint=True,
                  exceptsysinfo=True)
    except BaseException:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode=caughtcode,
                  caughtmsg='BaseException on [{!s}]'.format(fn_name.__name__),
                  exceptsysinfo=True)
    finally:
        pass

    if isGood(fn_result):
        fn_success = True

        logging.info('fn:[%s] Output for fn_result:',
                     fn_name.__name__)
        logging.info(xml.etree.ElementTree.tostring(
            fn_result,
            encoding='utf-8',
            method='xml'))
    else:
        logging.error('fn:[%s] isGood(fn_result):[%s]',
                      fn_name.__name__,
                      'None'
                      if fn_result is None
                      else isGood(fn_result))
        fn_result = None

    logging.info('fn:[{!s}] success:[{!s}] result:[{!s}] errcode:[{!s}]'
                 .format(fn_name.__name__, fn_success, fn_result, fn_errcode))

    return fn_success, fn_result, fn_errcode


# -----------------------------------------------------------------------------
# nu_authenticate
#
# Authenticates via flickrapi on flickr.com
#
def nu_authenticate(api_key,
                    secret,
                    token_cache_location):
    """ nu_authenticate
    Authenticate user so we can upload files.
    Assumes the cached token is not available or valid.

    api_key, secret, token_cache_location, perms

    Returns an instance object for the class flickrapi
    """

    # Instantiate flickr for connection to flickr via flickrapi
    logging.info(' Authentication: Connecting...')

    fn_result = True
    try:
        flickrobj = flickrapi.FlickrAPI(
            api_key,
            secret,
            token_cache_location=token_cache_location)
    except flickrapi.exceptions.FlickrError as ex:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='001',
                  caughtmsg='Error in flickrapi.FlickrAPI',
                  exceptuse=True,
                  exceptcode=ex.code,
                  exceptmsg=ex,
                  useniceprint=True,
                  exceptsysinfo=True)
        fn_result = False

    if not fn_result:
        return None   # Error

    logging.info(' Authentication: Connected. Getting new token...')

    fn_result = True
    try:
        flickrobj.get_request_token(oauth_callback='oob')
    except flickrapi.exceptions.FlickrError as ex:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='002',
                  caughtmsg='Error in flickrapi.FlickrAPI',
                  exceptuse=True,
                  exceptcode=ex.code,
                  exceptmsg=ex,
                  useniceprint=True,
                  exceptsysinfo=True)
        fn_result = False
        sys.exit(4)
    except Exception as ex:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='003',
                  caughtmsg='Unexpected error in token_valid',
                  useniceprint=True,
                  exceptsysinfo=True)
        fn_result = False
        raise

    # Show url. Copy and paste it in your browser
    # Adjust parameter "perms" to to your needs
    authorize_url = flickrobj.auth_url(perms=u'delete')
    print('Copy and paste following authorizaiton URL '
          'in your browser to obtain Verifier Code.')
    print(authorize_url)

    # Prompt for verifier code from the user.
    # Python 2.7 and 3.6
    # use "# noqa" to bypass flake8 error notifications
    verifier = unicode(raw_input(  # noqa
        'Verifier code (NNN-NNN-NNN): ')) \
        if sys.version_info < (3, ) \
        else input('Verifier code (NNN-NNN-NNN): ')

    print('Verifier: {!s}'.format(verifier))

    # Trade the request token for an access token
    try:
        flickrobj.get_access_token(verifier)
    except flickrapi.exceptions.FlickrError as ex:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='004',
                  caughtmsg='Error in flickrapi.get_access_token',
                  exceptuse=True,
                  exceptcode=ex.code,
                  exceptmsg=ex,
                  useniceprint=True,
                  exceptsysinfo=True)
        sys.exit(5)

    NPR.niceprint('{!s} with {!s} permissions: {!s}'
                  .format('Check Authentication',
                          'delete',
                          flickrobj.token_valid(perms='delete')))

    # Some debug...
    logging.info('Token Cache: [{!s}]', flickrobj.token_cache.token)

    return flickrobj


# -----------------------------------------------------------------------------
def nu_get_cached_token(api_key,
                        secret,
                        token_cache_location='token',
                        perms='delete'):
    """ nu_get_cached_token

        Attempts to get the flickr token from disk.

        api_key, secret, token_cache_location, perms

        Returns the flickrapi object.
        The actual token is: flickrobj.token_cache.token
    """

    # Instantiate flickr for connection to flickr via flickrapi
    logging.info('   Cached token: Connecting...')

    fn_result = True
    try:
        flickrobj = flickrapi.FlickrAPI(
            api_key,
            secret,
            token_cache_location=token_cache_location)
    except flickrapi.exceptions.FlickrError as ex:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='010',
                  caughtmsg='Error in flickrapi.FlickrAPI',
                  exceptuse=True,
                  exceptcode=ex.code,
                  exceptmsg=ex,
                  useniceprint=True,
                  exceptsysinfo=True)
        fn_result = False

    if not fn_result:
        return None   # Error

    logging.info('   Cached token: Connected. Looking in TOKEN_CACHE:[%s]',
                 token_cache_location)

    fn_result = True
    try:
        # Check if token permissions are correct.
        if flickrobj.token_valid(perms=perms):
            logging.info('   Cached token: Success: [%s]',
                         flickrobj.token_cache.token)
        else:
            fn_result = False
            logging.warning('   Cached token: Token Non-Existant.')
    except flickrapi.exceptions.FlickrError as ex:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='011',
                  caughtmsg='Error in flickrapi.token_valid',
                  exceptuse=True,
                  exceptcode=ex.code,
                  exceptmsg=ex,
                  useniceprint=True,
                  exceptsysinfo=True)
        fn_result = False
    except BaseException:
        niceerror(caught=True,
                  caughtprefix='+++Api',
                  caughtcode='012',
                  caughtmsg='Unexpected error in token_valid',
                  useniceprint=True,
                  exceptsysinfo=True)
        fn_result = False
        raise

    if fn_result:
        return flickrobj  # flickrobj.token_cache.token
    else:
        return None   # Error


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                        '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()

    import os
    import sys

    # Define two variables within your OS environment (api_key, secret)
    # to access flickr:
    #
    # export api_key=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    # export secret=YYYYYYYYYYYYYYYY
    #
    flickr_config = {'api_key': os.environ['api_key'],
                     'secret': os.environ['secret'],
                     'TOKEN_CACHE': os.path.join(
                         os.path.dirname(sys.argv[0]), 'token')}

    NPR.niceprint('-----------------------------------Connecting to Flickr...')
    flickr = None
    flickr = nu_get_cached_token(
        flickr_config['api_key'],
        flickr_config['secret'],
        token_cache_location=flickr_config['TOKEN_CACHE'])

    if flickr is None:
        flickr = nu_authenticate(
            flickr_config['api_key'],
            flickr_config['secret'],
            token_cache_location=flickr_config['TOKEN_CACHE'])

    if flickr is not None:
        NPR.niceprint('-----------------------------------Number of Photos...')
        get_success, get_result, get_errcode = nu_flickrapi_fn(
            flickr.people.getPhotos,
            (),
            dict(user_id="me", per_page=1),
            2, 10, True)

        if get_success and get_errcode == 0:
            NPR.niceprint('Number of Photos=[{!s}]'
                          .format(get_result.find('photos').attrib['total']))
