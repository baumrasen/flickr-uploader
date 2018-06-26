"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/

    rate_limited = Helper class and functions to rate limiting function calls
                   with Python Decorators.
                   Inspired by: https://gist.github.com/gregburek/1441055

    retry        = Helper function to run function calls multiple times on
                   error with Python Decorators.
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
import lib.NicePrint as NicePrint

# =============================================================================
# Functions aliases
#
#   NPR.niceprint = from niceprint module
# -----------------------------------------------------------------------------
NPR = NicePrint.NicePrint()


# -----------------------------------------------------------------------------
# class LastTime to be used with rate_limited
#
class LastTime:
    """
        >>> import lib.rate_limited as rt
        >>> arate = rt.LastTime()
        ...
        >>> arate.add_cnt()
        >>> arate.add_cnt()
        >>> arate.get_cnt()
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

    def acquire(self):
        """ acquire
        """
        self.ratelock.acquire()

    def release(self):
        """ release
        """
        self.ratelock.release()

    def set_last_time_called(self):
        """ set_last_time_called
        """
        self.last_time_called.value = time.time()

    def get_last_time_called(self):
        """ get_last_time_called
        """
        return self.last_time_called.value

    def add_cnt(self):
        """ add_cnt
        """
        self.cnt.value += 1

    def get_cnt(self):
        """ get_cnt
        """
        return self.cnt.value

    def debug(self, debugname='LT'):
        """ debug
        """
        now = time.time()
        logging.debug('___Rate name:[%s] '
                      'debug=[%s] '
                      '\n\t        cnt:[%s]'
                      '\n\tlast_called:[%s]'
                      '\n\t  timenow():[%s]',
                      self.name,
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
                          time.localtime(now)))


# -----------------------------------------------------------------------------
# rate_limited
#
# Controls the rate of execution of a function.
# Applicable to throttle API function calls
def rate_limited(max_per_second):
    """ rate_limited

    Controls the rate of execution of a function.
    Applicable to throttle API function calls
    """

    min_interval = 1.0 / max_per_second
    last_time = LastTime('rate_limited')

    def decorate(func):
        """ decorate
        """
        last_time.acquire()
        if last_time.get_last_time_called() == 0:
            last_time.set_last_time_called()
        # last_time.debug('DECORATE')
        last_time.release()

        @wraps(func)
        def rate_limited_function(*args, **kwargs):
            """ rate_limited_function

                Controls the rate of execution of a function.
                Applicable to throttle API function calls
            """

            logging.info('___Rate_limited f():[%s]: '
                         'Max_per_Second:[%s]',
                         func.__name__, max_per_second)

            try:
                last_time.acquire()
                last_time.add_cnt()
                xfrom = time.time()

                elapsed = xfrom - last_time.get_last_time_called()
                left_to_wait = min_interval - elapsed
                logging.debug('___Rate f():[%s] '
                              'cnt:[%s] '
                              '\n\tlast_called:%s '
                              '\n\t time now():%s '
                              'elapsed:%6.2f '
                              'min:%s '
                              'to_wait:%6.2f',
                              func.__name__,
                              last_time.get_cnt(),
                              time.strftime(
                                  '%T',
                                  time.localtime(
                                      last_time.get_last_time_called())),
                              time.strftime('%T',
                                            time.localtime(xfrom)),
                              elapsed,
                              min_interval,
                              left_to_wait)
                if left_to_wait > 0:
                    time.sleep(left_to_wait)

                ret = func(*args, **kwargs)

                last_time.debug('OVER')
                last_time.set_last_time_called()
                last_time.debug('NEXT')

            except Exception as ex:
                NPR.niceerror(caught=True,
                              caughtprefix='+++Rate',
                              caughtcode='001',
                              caughtmsg='Exception on rate_limited_function',
                              exceptuse=True,
                              # exceptCode=ex.code,
                              exceptmsg=ex,
                              useniceprint=False,
                              exceptsysinfo=True)
                raise
            finally:
                last_time.release()
            return ret

        return rate_limited_function

    return decorate
# -----------------------------------------------------------------------------
# Samples
# @rate_limited(5) # 5 calls per second
# def print_num(num):
#     print (num )


# -----------------------------------------------------------------------------
# retry
#
# retries execution of a function
def retry(attempts=3, waittime=5, randtime=False):
    """
    Catches exceptions while running a supplied function
    Re-runs it for "attempts" while sleeping "waittime" seconds in-between
    "waititme" is randomized if "randtime" is True.
    Outputs 3 types of errors (coming from the parameters)

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
    def wrapper_fn(a_fn):
        """ wrapper_fn

            Wrapper function for @retry
        """
        @wraps(a_fn)
        def new_wrapper(*args, **kwargs):
            """ new_wrapper

                new_wrapper function for @retry
            """
            rtime = time
            error = None

            if logging.getLogger().getEffectiveLevel() <= logging.INFO:
                if args is not None:
                    logging.info('___Retry f():[%s] '
                                 'Max:[%s] Delay:[%s] Rnd[%s]',
                                 a_fn.__name__, attempts,
                                 waittime, randtime)
                    for i, arg in enumerate(args):
                        logging.debug('___Retry f():[%s] arg[%s]=[%s]',
                                      a_fn.__name__, i, arg)
            for i in range(attempts if attempts > 0 else 1):
                try:
                    logging.info('___Retry f():[%s]: '
                                 'Attempt:[%s] of [%s]',
                                 a_fn.__name__, i + 1, attempts)
                    return a_fn(*args, **kwargs)
                except flickrapi.exceptions.FlickrError as exc:
                    logging.error('___Retry f():[%s]: Error code A: [%s]',
                                  a_fn.__name__, exc)
                    error = exc
                except lite.Error as err:
                    logging.error('___Retry f():[%s]: Error code B: [%s]',
                                  a_fn.__name__, err)
                    error = err
                    # CODING: Release existing locks on error?
                    # Check how to handle this particular scenario.
                except Exception as err:
                    logging.error('___Retry f():[%s]: Error code C: Catchall',
                                  a_fn.__name__)
                    error = err

                logging.warning('___Function:[%s] Waiting:[%s] Rnd:[%s]',
                                a_fn.__name__, waittime, randtime)
                if randtime:
                    rtime.sleep(random.randrange(0,
                                                 (waittime + 1)
                                                 if waittime >= 0
                                                 else 1))
                else:
                    rtime.sleep(waittime if waittime >= 0 else 0)
            logging.error('___Retry f():[%s] '
                          'Max:[%s] Delay:[%s] Rnd[%s]: Raising ERROR!',
                          a_fn.__name__, attempts, waittime, randtime)
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


# -------------------------------------------------------------------------
# rate_5_callspersecond
#
@rate_limited(5)  # 5 calls per second
def rate_5_callspersecond():
    """ rate_5_callspersecond

        Pace the calls rate within a specific function

          n   = n calls per second  (ex. 3 means 3 calls per second)
          1/n = n seconds per call (ex. 0.5 means 4 seconds in between calls)
    """
    logging.debug('rate_limit (5 calls/s) timestamp:[%s]', time.strftime('%T'))


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                        '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()

    # n for n calls per second  (ex. 3 means 3 calls per second)
    # 1/n for n seconds per call (ex. 0.5 meand 4 seconds in between calls)
    @rate_limited(1)
    def print_num(prc, num):
        """ print_num

            Fake function for testing. Print activity and timestamp.
        """
        print('\t\t***prc:[{!s}] num:[{!s}] '
              'rate_limit timestamp:[{!s}]'
              .format(prc, num, time.strftime('%T')))

    print('-------------------------------------------------Single Processing')
    for process in range(1, 3):
        for j in range(1, 2):
            print_num(process, j)

    print('-------------------------------------------------Multi Processing')

    def fmulti(n_cycles, prc):
        """ fmulti

            Function to iterate in multiprocessing mode.
        """

        for i in range(1, n_cycles):
            rnd_sleep = random.randrange(6)
            print('\t\t[prc:{!s}] [{!s}]'
                  '->- WORKing {!s}s----[{!s}]'
                  .format(prc, i, rnd_sleep, time.strftime('%T')))
            time.sleep(rnd_sleep)
            print('\t\t[prc:{!s}] [{!s}]--> Before rate_limited----[{!s}]'
                  .format(prc, i, time.strftime('%T')))
            print_num(prc, i)
            print('\t\t[prc:{!s}] [{!s}]<-- After rate_limited-----[{!s}]'
                  .format(prc, i, time.strftime('%T')))

    def launch_multiprocessing(fn_tolaunch, n_prc):
        """ launch_multiprocessing

            Test Launches a function in multiprocessing mode

            fn_launch= function to launch accepting two args: n_cycles, prcid)
            n_prc     = number of processes to launch
        """

        task_pool = []
        for prcid in range(1, n_prc):
            task = multiprocessing.Process(target=fn_tolaunch, args=(5, prcid))
            task_pool.append(task)
            task.start()

        for prc in task_pool:
            print('{!s}.is_alive = {!s}'.format(prc.name, prc.is_alive()))

        while True:
            if not any(multiprocessing.active_children()):
                print('===No active children Processes.')
                break
            for prc in multiprocessing.active_children():
                print('==={!s}.is_alive = {!s}'
                      .format(prc.name, prc.is_alive()))
                active_task = prc
            print('===Will wait for 60 on {!s}.is_alive = {!s}'
                  .format(active_task.name, active_task.is_alive()))
            active_task.join(timeout=60)
            print('===Waited for 60s on {!s}.is_alive = {!s}'
                  .format(active_task.name, active_task.is_alive()))

        # Wait for join all jobs/tasks in the Process Pool
        # All should be done by now!
        for prc in task_pool:
            prc.join()
            print('==={!s} (is alive: {!s}).exitcode = {!s}'
                  .format(prc.name, prc.is_alive(), prc.exitcode))

    # launch 4 processes for function fmulti
    launch_multiprocessing(fmulti, 4)
