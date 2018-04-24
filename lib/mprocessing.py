"""
    by oPromessa, 2018
    Published on https://github.com/oPromessa/flickr-uploader/

    mprocessing  = Helper function to run function calls in multiprocessing
                   mode with Python Decorators.
"""
# CODING EXTREME ARGS.verbose = ARGS_verbose
# CODING EXTREME ARGS.verbose_progress = ARGS_verbose_progress

# -----------------------------------------------------------------------------
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function,
#    unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1

# -----------------------------------------------------------------------------
# Import section
#
import sys
import logging
import multiprocessing
from functools import wraps
from itertools import islice
from . import niceprint as npc

# CODING EXTREME
ARGS_verbose = True
ARGS_verbose_progress = True

# -------------------------------------------------------------------------
# niceprocessedfiles
#
# Nicely print number of processed files
#
def niceprocessedfiles(count, cTotal, total):
    """
    niceprocessedfiles

    count  = Nicely print number of processed files rounded to 100's
    cTotal = Shows also the total number of items to be processed
    total  = if true shows the final count (use at the end of processing)
    """

    if not total:
        if (int(count) % 100 == 0):
            np.niceprint('Files Processed:[{!s:>6s}] of [{!s:>6s}]'
                         .format(count, cTotal))
    else:
        if (int(count) % 100 > 0):
            np.niceprint('Files Processed:[{!s:>6s}] of [{!s:>6s}]'
                         .format(count, cTotal))

    sys.stdout.flush()

np = npc.niceprint()

# -----------------------------------------------------------------------------
# mprocessing
#
# Helper function to run function calls in multiprocessing mode
# with Python Decorators.
def mprocessing(nprocs, lockDB, running, mutex, itemslist, countTotal):
    """ mprocessing Function Decorator

    nprocs     = Numper of processes to launch
    lockDB     = lock for access to Database
    running    = Value to count processed items
    mutex      = mutex for access to value running
    itemslist  = list of items to be processed
    countTotal = Total counter of items. to distributeplay progress
    """
    # procPool = Local variable procPool for Pool of processes
    # LOGlevel = LOGlevel
    def wrapper_fn(f):
        @wraps(f)
        def new_wrapper(*args, **kwargs):

            LOGlevel = logging.getLogger().getEffectiveLevel()
            if LOGlevel <= logging.WARNING:
                logging.info('===mprocessing f():[{!s}] nprocs:[{!s}]'
                             .format(f.__name__, nprocs))
                if args is not None:
                    for i, a in enumerate(args):
                        logging.info('===mprocessing f():[{!s}] arg[{!s}]={!s}'
                                     .format(f.__name__, i, a))

            logging.info('new_wrapper=[{!s}]'.format(__name__))

            # if __name__ == '__main__':
            if True:
                logging.debug('===Multiprocessing=== Setting up logger!')
                multiprocessing.log_to_stderr()
                logger = multiprocessing.get_logger()
                logger.setLevel(LOGlevel)

                logging.debug('===Multiprocessing=== Logging defined!')

                def chunk(it, size):
                    """
                        Divides an iterable in slices/chunks of size size
                    """
                    it = iter(it)
                    # lambda: creates a returning expression function
                    # which returns slices
                    # iter, with the second argument () stops creating
                    # iterators when it reaches the end
                    return iter(lambda: tuple(islice(it, size)), ())

                procPool = []
                lockDB = multiprocessing.Lock()
                running = multiprocessing.Value('i', 0)
                mutex = multiprocessing.Lock()

                sz = (len(itemslist) // int(nprocs)) \
                    if ((len(itemslist) // int(nprocs)) > 0) \
                    else 1

                logging.debug('len(itemslist):[{!s}] '
                              'int(nprocs):[{!s}] '
                              'sz per process:[{!s}]'
                              .format(len(itemslist),
                                      int(nprocs),
                                      sz))

                # Split itemslist in chunks to distribute accross Processes
                for splititemslist in chunk(itemslist, sz):
                    logging.warning('===Actual/Planned Chunk size: '
                                    '[{!s}]/[{!s}]'
                                    .format(len(splititemslist), sz))
                    logging.debug('===type(splititemslist)=[{!s}]'
                                  .format(type(splititemslist )))
                    logging.debug('===Job/Task Process: Creating...')
                    pTask = multiprocessing.Process(
                        target=f,  # argument to wrapper_fn
                        args=(lockDB,
                              running,
                              mutex,
                              splititemslist,
                              countTotal,))
                    procPool.append(pTask)
                    logging.debug('===Job/Task Process: Starting...')
                    pTask.start()
                    logging.debug('===Job/Task Process: Started')
                    if (ARGS_verbose):
                        np.niceprint('===Job/Task Process: [{!s}] Started '
                                     'with pid:[{!s}]'
                                     .format(pTask.name,
                                             pTask.pid))

                # Check status of jobs/tasks in the Process Pool
                if LOGlevel <= logging.DEBUG:
                    logging.debug('===Checking Processes launched/status:')
                    for j in procPool:
                        np.niceprint('{!s}.is_alive = {!s}'
                                     .format(j.name, j.is_alive()))

                # Regularly print status of jobs/tasks in the Process Pool
                # Prints status while there are processes active
                # Exits when all jobs/tasks are done.
                while (True):
                    if not (any(multiprocessing.active_children())):
                        logging.debug('===No active children Processes.')
                        break
                    for p in multiprocessing.active_children():
                        logging.debug('==={!s}.is_alive = {!s}'
                                      .format(p.name, p.is_alive()))
                        procTaskActive = p
                    logging.info('===Will wait for 60 on '
                                 '{!s}.is_alive = {!s}'
                                 .format(procTaskActive.name,
                                         procTaskActive.is_alive()))
                    if (ARGS_verbose_progress):
                        np.niceprint('===Will wait for 60 on '
                                     '{!s}.is_alive = {!s}'
                                     .format(procTaskActive.name,
                                             procTaskActive.is_alive()))

                    procTaskActive.join(timeout=60)
                    logging.info('===Waited for 60s on '
                                 '{!s}.is_alive = {!s}'
                                 .format(procTaskActive.name,
                                         procTaskActive.is_alive()))
                    if (ARGS_verbose):
                        np.niceprint('===Waited for 60s on '
                                     '{!s}.is_alive = {!s}'
                                     .format(procTaskActive.name,
                                             procTaskActive.is_alive()))

                # Wait for join all jobs/tasks in the Process Pool
                # All should be done by now!
                for j in procPool:
                    j.join()
                    if (ARGS_verbose):
                        np.niceprint('==={!s} '
                                     '(is alive: {!s}).exitcode = {!s}'
                                     .format(j.name,
                                             j.is_alive(),
                                             j.exitcode))

                logging.warning('===Multiprocessing=== pool joined! '
                                'All processes finished.')

                # Will release (set to None) the nulockDB lock control
                # this prevents subsequent calls to
                # useDBLock( nuLockDB, False)
                # to raise exception:
                #   ValueError('semaphore or lock released too many times')
                logging.info('===Multiprocessing=== pool joined! '
                             'What happens to lockDB is None:[{!s}]? '
                             'It seems not, it still has a value! '
                             'Setting it to None!'
                             .format(lockDB is None))
                lockDB = None

                # Show number of total files processed
                niceprocessedfiles(running.value,
                                   countTotal,
                                   True)

            return True
            # f(*args, **kwargs) # What will this do?
                                      # Do I next a wrapper function
                                      # Or simply get function as argument

        return new_wrapper
    return wrapper_fn
# -----------------------------------------------------------------------------
# Samples
# @mprocessing(nprocs, lock, running, mutex, filelist, countTotal):
# def maddAlbumsMigrate  # Some function similar...
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


def xmprocessing(nprocs, lockDB, running, mutex, itemslist, countTotal, f):
    """ mprocessing Function Decorator

    nprocs     = Numper of processes to launch
    lockDB     = lock for access to Database
    running    = Value to count processed items
    mutex      = mutex for access to value running
    itemslist  = list of items to be processed
    countTotal = Total counter of items. to distributeplay progress
    """
    # procPool = Local variable procPool for Pool of processes
    # LOGlevel = LOGlevel

    LOGlevel = logging.getLogger().getEffectiveLevel()
    if LOGlevel <= logging.WARNING:
        logging.info('===mprocessing f():[{!s}] nprocs:[{!s}]'
                     .format(f.__name__, nprocs))
        # if args is not None:
        #     for i, a in enumerate(args):
        #         logging.info('===mprocessing f():[{!s}] arg[{!s}]={!s}'
        #                      .format(f.__name__, i, a))

    logging.info('new_wrapper=[{!s}]'.format(__name__))

    # if __name__ == '__main__':
    if True:
        logging.debug('===Multiprocessing=== Setting up logger!')
        multiprocessing.log_to_stderr()
        logger = multiprocessing.get_logger()
        logger.setLevel(LOGlevel)

        logging.debug('===Multiprocessing=== Logging defined!')

        def chunk(it, size):
            """
                Divides an iterable in slices/chunks of size size
            """
            it = iter(it)
            # lambda: creates a returning expression function
            # which returns slices
            # iter, with the second argument () stops creating
            # iterators when it reaches the end
            return iter(lambda: tuple(islice(it, size)), ())

        procPool = []
        lockDB = multiprocessing.Lock()
        running = multiprocessing.Value('i', 0)
        mutex = multiprocessing.Lock()

        sz = (len(itemslist) // int(nprocs)) \
            if ((len(itemslist) // int(nprocs)) > 0) \
            else 1

        logging.debug('len(itemslist):[{!s}] '
                      'int(nprocs):[{!s}] '
                      'sz per process:[{!s}]'
                      .format(len(itemslist),
                              int(nprocs),
                              sz))

        # Split itemslist in chunks to distribute accross Processes
        for splititemslist in chunk(itemslist, sz):
            logging.warning('===Actual/Planned Chunk size: '
                            '[{!s}]/[{!s}]'
                            .format(len(splititemslist), sz))
            logging.debug('===type(splititemslist)=[{!s}]'
                          .format(type(splititemslist )))
            logging.debug('===Job/Task Process: Creating...')
            pTask = multiprocessing.Process(
                target=f,  # argument to wrapper_fn
                args=(lockDB,
                      running,
                      mutex,
                      splititemslist,
                      countTotal,))
            procPool.append(pTask)
            logging.debug('===Job/Task Process: Starting...')
            pTask.start()
            logging.debug('===Job/Task Process: Started')
            if (ARGS_verbose):
                np.niceprint('===Job/Task Process: [{!s}] Started '
                             'with pid:[{!s}]'
                             .format(pTask.name,
                                     pTask.pid))

        # Check status of jobs/tasks in the Process Pool
        if LOGlevel <= logging.DEBUG:
            logging.debug('===Checking Processes launched/status:')
            for j in procPool:
                np.niceprint('{!s}.is_alive = {!s}'
                             .format(j.name, j.is_alive()))

        # Regularly print status of jobs/tasks in the Process Pool
        # Prints status while there are processes active
        # Exits when all jobs/tasks are done.
        while (True):
            if not (any(multiprocessing.active_children())):
                logging.debug('===No active children Processes.')
                break
            for p in multiprocessing.active_children():
                logging.debug('==={!s}.is_alive = {!s}'
                              .format(p.name, p.is_alive()))
                procTaskActive = p
            logging.info('===Will wait for 60 on '
                         '{!s}.is_alive = {!s}'
                         .format(procTaskActive.name,
                                 procTaskActive.is_alive()))
            if (ARGS_verbose_progress):
                np.niceprint('===Will wait for 60 on '
                             '{!s}.is_alive = {!s}'
                             .format(procTaskActive.name,
                                     procTaskActive.is_alive()))

            procTaskActive.join(timeout=60)
            logging.info('===Waited for 60s on '
                         '{!s}.is_alive = {!s}'
                         .format(procTaskActive.name,
                                 procTaskActive.is_alive()))
            if (ARGS_verbose):
                np.niceprint('===Waited for 60s on '
                             '{!s}.is_alive = {!s}'
                             .format(procTaskActive.name,
                                     procTaskActive.is_alive()))

        # Wait for join all jobs/tasks in the Process Pool
        # All should be done by now!
        for j in procPool:
            j.join()
            if (ARGS_verbose):
                np.niceprint('==={!s} '
                             '(is alive: {!s}).exitcode = {!s}'
                             .format(j.name,
                                     j.is_alive(),
                                     j.exitcode))

        logging.warning('===Multiprocessing=== pool joined! '
                        'All processes finished.')

        # Will release (set to None) the nulockDB lock control
        # this prevents subsequent calls to
        # useDBLock( nuLockDB, False)
        # to raise exception:
        #   ValueError('semaphore or lock released too many times')
        logging.info('===Multiprocessing=== pool joined! '
                     'What happens to lockDB is None:[{!s}]? '
                     'It seems not, it still has a value! '
                     'Setting it to None!'
                     .format(lockDB is None))
        lockDB = None

        # Show number of total files processed
        niceprocessedfiles(running.value,
                           countTotal,
                           True)

    return True

# -----------------------------------------------------------------------------
# If called to have multiprocessing running under main!
#
def main():
    logging.info('mprocessing.MAIN=[{!s}]'.format(__name__))