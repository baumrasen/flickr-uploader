"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

    rate_limited = Helper class and functions to rate limiting function calls
                   with Python Decorators.
                   Inspired by: https://gist.github.com/gregburek/1441055

    retry        = Helper function to run function calls multiple times on
                   error with Python Decorators.
"""

# ----------------------------------------------------------------------------
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function, unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1

# ----------------------------------------------------------------------------
# Import section
#
import sys
import logging
import multiprocessing
import time
import random
import sqlite3 as lite
import flickrapi
from functools import wraps
from . import niceprint

# -----------------------------------------------------------------------------
# class LastTime to be used with rate_limited
#
class LastTime:
    """
        >>> import lib.rate_limited as rt
        >>> a = rt.LastTime()
        ...
        >>> a.add_cnt()
        >>> a.add_cnt()
        >>> a.get_cnt()
        2
    """
    # -------------------------------------------------------------------------
    # class LastTime __init__
    #
    def __init__(self, name='LT'):
        # Init variables to None
        self.name = name
        self.ratelock = None
        self.cnt = None
        self.last_time_called = None

        # Instantiate control variables
        self.ratelock = multiprocessing.Lock()
        self.cnt = multiprocessing.Value('i', 0)
        self.last_time_called = multiprocessing.Value('d', 0.0)

        logging.debug('\t__init__: name=[{!s}]'.format(self.name))

    def acquire(self):
        self.ratelock.acquire()

    def release(self):
        self.ratelock.release()

    def set_last_time_called(self):
        self.last_time_called.value = time.time()

    def get_last_time_called(self):
        return self.last_time_called.value

    def add_cnt(self):
        self.cnt.value += 1

    def get_cnt(self):
        return self.cnt.value

    def debug(self, debugname='LT'):
        now=time.time()
        logging.debug('___Rate name:[{!s}] '
                      'debug=[{!s}] '
                      '\n\t        cnt:[{!s}] '
                      '\n\tlast_called:{!s} '
                      '\n\t  timenow():{!s} '
                      .format(self.name,
                              debugname,
                              self.cnt.value,
                              time.strftime(
                                '%T.{}'
                                .format(str(self.last_time_called.value -
                                            int(self.last_time_called.value))
                                            .split('.')[1][:3]),
                                time.localtime(self.last_time_called.value)),
                              time.strftime(
                                '%T.{}'
                                .format(str(now -
                                            int(now))
                                            .split('.')[1][:3]),
                                time.localtime(now))))


# -----------------------------------------------------------------------------
# rate_limited
#
# retries execution of a function
def rate_limited(max_per_second):

    min_interval = 1.0 / max_per_second
    LT = LastTime('rate_limited')
    np = niceprint.niceprint()

    def decorate(func):
        LT.acquire()
        if LT.get_last_time_called() == 0:
            LT.set_last_time_called()
        # LT.debug('DECORATE')
        LT.release()

        @wraps(func)
        def rate_limited_function(*args, **kwargs):

            logging.info('___Rate_limited f():[{!s}]: '
                         'Max_per_Second:[{!s}]'
                         .format(func.__name__, max_per_second))

            try:
                LT.acquire()
                LT.add_cnt()
                xfrom = time.time()

                elapsed = xfrom - LT.get_last_time_called()
                left_to_wait = min_interval - elapsed
                logging.debug('___Rate f():[{!s}] '
                              'cnt:[{!s}] '
                              '\n\tlast_called:{!s} '
                              '\n\t time now():{!s} '
                              'elapsed:{:6.2f} '
                              'min:{!s} '
                              'to_wait:{:6.2f}'
                              .format(func.__name__,
                                      LT.get_cnt(),
                                      time.strftime(
                                            '%T',
                                            time.localtime(
                                                LT.get_last_time_called())),
                                      time.strftime('%T',
                                                    time.localtime(xfrom)),
                                      elapsed,
                                      min_interval,
                                      left_to_wait))
                if left_to_wait > 0:
                    time.sleep(left_to_wait)

                ret = func(*args, **kwargs)

                LT.debug('OVER')
                LT.set_last_time_called()
                LT.debug('NEXT')

            except Exception as ex:
                # CODING: To be changed once reportError is on a module
                # sys.stderr.write('+++000 '
                #                  'Exception on rate_limited_function: [{!s}]\n'
                #                  .format(ex))
                # sys.stderr.flush()
                np.reportError(Caught=True,
                               CaughtPrefix='+++',
                               CaughtCode='000',
                               CaughtMsg='Exception on rate_limited_function',
                               exceptUse=True,
                               # exceptCode=ex.code,
                               exceptMsg=ex,
                               NicePrint=False,
                               exceptSysInfo=True)
                raise
            finally:
                LT.release()
            return ret

        return rate_limited_function

    return decorate
# -----------------------------------------------------------------------------
# Samples
#@rate_limited(5) # 5 calls per second
# def print_num(num):
#     print (num )


# -----------------------------------------------------------------------------
# retry
#
# retries execution of a function
#
def retry(attempts=3, waittime=5, randtime=False):
    """
    Catches exceptions while running a supplied function
    Re-runs it for times while sleeping X seconds in-between
    outputs 3 types of errors (coming from the parameters)

    attempts = Max Number of Attempts
    waittime = Wait time in between Attempts
    randtime = Randomize the Wait time from 1 to randtime for each Attempt

    >>> import lib.rate_limited as rt
    >>> @rt.retry(attempts=3, waittime=3, randtime=True)
    ... def f():
    ...     print(x)
    ...
    >>> f()
    Traceback (most recent call last):
    NameError: ...
    """
    def wrapper_fn(f):
        @wraps(f)
        def new_wrapper(*args, **kwargs):

            rtime = time
            error = None

            if logging.getLogger().getEffectiveLevel() <= logging.WARNING:
                if args is not None:
                    logging.info('___Retry f():[{!s}] '
                                 'Max:[{!s}] Delay:[{!s}] Rnd[{!s}]'
                                 .format(f.__name__, attempts,
                                         waittime, randtime))
                    for i, a in enumerate(args):
                        logging.info('___Retry f():[{!s}] arg[{!s}]={!s}'
                                     .format(f.__name__, i, a))
            for i in range(attempts if attempts > 0 else 1):
                try:
                    logging.info('___Retry f():[{!s}]: '
                                 'Attempt:[{!s}] of [{!s}]'
                                 .format(f.__name__, i+1, attempts))
                    return f(*args, **kwargs)
                except Exception as e:
                    logging.error('___Retry f():[{!s}]: Error code A: [{!s}]'
                                  .format(f.__name__, e))
                    error = e
                except flickrapi.exceptions.FlickrError as ex:
                    logging.error('___Retry f():[{!s}]: Error code B: [{!s}]'
                                  .format(f.__name__, ex))
                except lite.Error as e:
                    logging.error('___Retry f():[{!s}]: Error code C: [{!s}]'
                                  .format(f.__name__, e))
                    error = e
                    # Release the lock on error.
                    # CODING: Check how to handle this particular scenario.
                    # flick.useDBLock(nulockDB, False)
                    # self.useDBLock( lock, True)
                except:
                    logging.error('___Retry f():[{!s}]: Error code D: Catchall'
                                  .format(f.__name__))

                logging.warning('___Function:[{!s}] Waiting:[{!s}] Rnd:[{!s}]'
                                .format(f.__name__, waittime, randtime))
                if randtime:
                    rtime.sleep(random.randrange(0,
                                                 (waittime+1)
                                                 if waittime >= 0
                                                 else 1))
                else:
                    rtime.sleep(waittime if waittime >= 0 else 0)
            logging.error('___Retry f():[{!s}] '
                            'Max:[{!s}] Delay:[{!s}] Rnd[{!s}]: Raising ERROR!'
                            .format(f.__name__, attempts,
                                    waittime, randtime))
            raise error
        return new_wrapper
    return wrapper_fn
# -----------------------------------------------------------------------------
# Samples
# @retry(attempts=3, waittime=2)
# def retry_divmod(argslist):
#     return divmod(*argslist)
# print retry_divmod([5, 3])
# try:
#     print(retry_divmod([5, 'H']))
# except:
#     logging.error('Error Caught (Overall Catchall)...')
# finally:
#     logging.error('...Continuing')
# nargslist=dict(Caught=True, CaughtPrefix='+++')
# retry_reportError(nargslist)


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                               '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()

    # Comment following line to allow further debugging/testing
    sys.exit(0)

    # n for n calls per second  (ex. 3 means 3 calls per second)
    # 1/n for n seconds per call (ex. 0.5 meand 4 seconds in between calls)
    @rate_limited(1)
    def print_num(prc, num):
        """
        """
        print('\t\t***prc:[{!s}] num:[{!s}] '
              'rate_limit timestamp:[{!s}]'
              .format(prc, num, time.strftime('%T')))

    print('-------------------------------------------------Single Processing')
    for process in range(1, 3):
        for j in range(1, 2):
            print_num(process, j)

    print('-------------------------------------------------Multi Processing')
    def fmulti(x, prc):

        for i in range(1,x):
            r = random.randrange(6)
            print('\t\t[prc:{!s}] [{!s}]'
                  '->- WORKing {!s}s----[{!s}]'
                  .format(prc, i, r, time.strftime('%T')))
            time.sleep(r)
            print('\t\t[prc:{!s}] [{!s}]--> Before:---[{!s}]'
                  .format(prc, i, time.strftime('%T')))
            print_num(prc, i)
            print('\t\t[prc:{!s}] [{!s}]<-- After----[{!s}]'
                  .format(prc, i, time.strftime('%T')))

    TaskPool = []

    for j in range(1,4):
        Task = multiprocessing.Process(target=fmulti, args=(5,j))
        TaskPool.append(Task)
        Task.start()

    for j in TaskPool:
        print('{!s}.is_alive = {!s}'.format(j.name, j.is_alive()))

    while (True):
        if not (any(multiprocessing.active_children())):
            print('===No active children Processes.')
            break
        for p in multiprocessing.active_children():
            print('==={!s}.is_alive = {!s}'.format(p.name, p.is_alive()))
            uploadTaskActive = p
        print('===Will wait for 60 on {!s}.is_alive = {!s}'
              .format(uploadTaskActive.name,
                      uploadTaskActive.is_alive()))
        uploadTaskActive.join(timeout=60)
        print('===Waited for 60s on {!s}.is_alive = {!s}'
              .format(uploadTaskActive.name,
                      uploadTaskActive.is_alive()))

    # Wait for join all jobs/tasks in the Process Pool
    # All should be done by now!
    for j in TaskPool:
        j.join()
        print('==={!s} (is alive: {!s}).exitcode = {!s}'
              .format(j.name, j.is_alive(), j.exitcode))
