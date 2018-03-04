"""
    by oPromessa, 2017
    Published on https://github.com/oPromessa/flickr-uploader/
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
from functools import wraps


# -----------------------------------------------------------------------------
# class LastTime to be used with rate_limited
#
class LastTime:

    def __init__(self, name):
        self.name = name
        self.ratelock = None
        self.cnt = None
        self.last_time_called = None

        logging.debug('\t__init__: name=[{!s}]'.format(self.name))

    def start(self):
        self.ratelock = multiprocessing.Lock()
        self.cnt = multiprocessing.Value('i', 0)
        self.last_time_called = multiprocessing.Value('d', 0.0)

    def acquire(self):
        self.ratelock.acquire()

    def release(self):
        self.ratelock.release()

    def set_last_time_called(self):
        xtime=time.time()
        logging.debug('Set xtime last_time_called:[{!s}]/[{!s}]'
                      .format(time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(xtime)),
                              xtime))
        self.last_time_called.value = xtime
        logging.debug('Set real last_time_called:[{!s}]/[{!s}]'
                      .format(time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(
                                                self.last_time_called.value)),
                              self.last_time_called.value))
        # self.debug('set_last_time_called')

    def get_last_time_called(self):
        return self.last_time_called.value

    def add_cnt(self):
        self.cnt.value += 1

    def get_cnt(self):
        return self.cnt.value

    def debug(self, debugname):
        logging.debug('___Rate name:[{!s}] '
                      'debug=[{!s}] '
                      'cnt:[{!s}] '
                      'last_called:{!s} '
                      'timenow():{!s} '
                      .format(self.name,
                              debugname,
                              self.cnt.value,
                              time.strftime('%T',
                                            time.localtime(
                                                self.last_time_called.value)),
                              time.strftime('%T')))


# -----------------------------------------------------------------------------
# rate_limited
#
# retries execution of a function
def rate_limited(max_per_second):

    min_interval = 1.0 / max_per_second
    LT = LastTime('rate_limited')
    LT.start()

    def decorate(func):
        LT.acquire()
        logging.debug('1st decorate: last_time_called=[{!s}]'
                      .format(time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(
                                                LT
                                                .last_time_called.value))))
        if LT.get_last_time_called() == 0:
            LT.set_last_time_called()
            logging.debug('Setting last_time_called time to approx:[{!s}]'
                          .format(time.strftime('%Y-%m-%d %H:%M:%S')))
        logging.debug('2nd decorate: last_time_called=[{!s}]'
                      .format(time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(
                                                LT.get_last_time_called()))))
        LT.release()

        @wraps(func)
        def rate_limited_function(*args, **kwargs):

            logging.warning('___Rate_limited f():[{!s}]: '
                            'Max_per_Second:[{!s}]'
                            .format(func.__name__, max_per_second))

            try:
                # CODING: xfrom before acquire will ensure rate limt is
                # respected accross processes. If not all process will
                # execute at the same time. OR NOT??
                LT.acquire()
                LT.add_cnt()
                xfrom = time.time()

                elapsed = xfrom - LT.get_last_time_called()
                left_to_wait = min_interval - elapsed
                logging.debug('___Rate f():[{!s}] '
                              'cnt:[{!s}] '
                              'last_called:{!s} '
                              'time():{!s} '
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

                LT.set_last_time_called()
                LT.debug('OVER')
            except Exception as ex:
                # CODING: To be changed once reportError is on a module
                sys.stderr.write('+++000 '
                                 'Exception on rate_limited_function')
                sys.stderr.flush()
                # reportError(Caught=True,
                #              CaughtPrefix='+++',
                #              CaughtCode='000',
                #              CaughtMsg='Exception on rate_limited_function',
                #              exceptUse=True,
                #              # exceptCode=ex.code,
                #              exceptMsg=ex,
                #              NicePrint=False,
                #              exceptSysInfo=True)
                raise
            finally:
                LT.release()
            return ret

        return rate_limited_function

    return decorate
# -----------------------------------------------------------------------------
# Samples
# @rate_limited(5) # 5 calls per second
# def print_num(num):
#     print (num )
