"""
    by oPromessa, 2018
    Published on https://github.com/oPromessa/flickr-uploader/

    mprocessing  = Helper function to run function in multiprocessing mode
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
from itertools import islice
from . import niceprint

# =============================================================================
# Functions aliases
#
#   NP.niceprint = from niceprint module
# -----------------------------------------------------------------------------
NP = niceprint.niceprint()


# -----------------------------------------------------------------------------
# mprocessing
#
def mprocessing(args_verbose, args_verbose_progress,
                nprocs, lockDB, running, mutex, itemslist, a_fn, cur):
    """ mprocessing Function

    verbose    = verbose info
    verbose_progress = further verbose
    nprocs     = Number of processes to launch
    lockDB     = lock for access to Database
    running    = Value to count processed items
    mutex      = mutex for access to value running
    itemslist  = list of items to be processed
    a_fn       = a function which is the target of the multiprocessing
    cur        = cursor variable for DB access
    """
    # proc_pool   = Local variable proc_pool for Pool of processes
    # log_level   = log_level
    # count_total = Total counter of items to distribute/play/indicate progress
    #               len(itemslist)

    log_level = logging.getLogger().getEffectiveLevel()
    if log_level <= logging.WARNING:
        logging.info('===mprocessing f():[{!s}] nprocs:[{!s}]'
                     .format(a_fn.__name__, nprocs))
        # if args is not None:
        #     for i, arg in enumerate(args):
        #         logging.info('===mprocessing f():[{!s}] arg[{!s}]={!s}'
        #                      .format(a_fn.__name__, i, arg))

    logging.info('new_wrapper=[{!s}]'.format(__name__))

    # if __name__ == '__main__':
    logging.debug('===Multiprocessing=== Setting up logger!')
    multiprocessing.log_to_stderr()
    logger = multiprocessing.get_logger()
    logger.setLevel(log_level)

    logging.debug('===Multiprocessing=== Logging defined!')

    # ---------------------------------------------------------
    # chunk
    #
    # Divides an iterable in slices/chunks of size size
    #
    def chunk(iter_list, size):
        """
            Divides an iterable in slices/chunks of size size
        """
        iter_list = iter(iter_list)
        # lambda: creates a returning expression function
        # which returns slices
        # iter, with the second argument () stops creating
        # iterators when it reaches the end
        return iter(lambda: tuple(islice(iter_list, size)), ())

    proc_pool = []
    lockDB = multiprocessing.Lock()
    running = multiprocessing.Value('i', 0)
    mutex = multiprocessing.Lock()
    count_total = len(itemslist)

    size = (len(itemslist) // int(nprocs)) \
        if ((len(itemslist) // int(nprocs)) > 0) \
        else 1

    logging.debug('len(itemslist):[{!s}] '
                  'int(nprocs):[{!s}] '
                  'size per process:[{!s}]'
                  .format(len(itemslist),
                          int(nprocs),
                          size))

    # Split itemslist in chunks to distribute accross Processes
    for splititemslist in chunk(itemslist, size):
        logging.warning('===Actual/Planned Chunk size: '
                        '[{!s}]/[{!s}]'
                        .format(len(splititemslist), size))
        logging.debug('===type(splititemslist)=[{!s}]'
                      .format(type(splititemslist)))
        logging.debug('===Job/Task Process: Creating...')
        proc_task = multiprocessing.Process(
            target=a_fn,  # argument function
            args=(lockDB,
                  running,
                  mutex,
                  splititemslist,
                  count_total,
                  cur,))
        proc_pool.append(proc_task)
        logging.debug('===Job/Task Process: Starting...')
        proc_task.start()
        logging.debug('===Job/Task Process: Started')
        if args_verbose:
            NP.niceprint('===Job/Task Process: [{!s}] Started '
                         'with pid:[{!s}]'
                         .format(proc_task.name,
                                 proc_task.pid))

    # Check status of jobs/tasks in the Process Pool
    if log_level <= logging.DEBUG:
        logging.debug('===Checking Processes launched/status:')
        for j in proc_pool:
            NP.niceprint('{!s}.is_alive = {!s}'
                         .format(j.name, j.is_alive()))

    # Regularly print status of jobs/tasks in the Process Pool
    # Prints status while there are processes active
    # Exits when all jobs/tasks are done.
    while True:
        if not any(multiprocessing.active_children()):
            logging.debug('===No active children Processes.')
            break
        for prc in multiprocessing.active_children():
            logging.debug('==={!s}.is_alive = {!s}'
                          .format(prc.name, prc.is_alive()))
            proc_task_active = prc
        logging.info('===Will wait for 60 on '
                     '{!s}.is_alive = {!s}'
                     .format(proc_task_active.name,
                             proc_task_active.is_alive()))
        if args_verbose_progress:
            NP.niceprint('===Will wait for 60 on '
                         '{!s}.is_alive = {!s}'
                         .format(proc_task_active.name,
                                 proc_task_active.is_alive()))

        proc_task_active.join(timeout=60)
        logging.info('===Waited for 60s on '
                     '{!s}.is_alive = {!s}'
                     .format(proc_task_active.name,
                             proc_task_active.is_alive()))
        if args_verbose:
            NP.niceprint('===Waited for 60s on '
                         '{!s}.is_alive = {!s}'
                         .format(proc_task_active.name,
                                 proc_task_active.is_alive()))

    # Wait for join all jobs/tasks in the Process Pool
    # All should be done by now!
    for j in proc_pool:
        j.join()
        if args_verbose_progress:
            NP.niceprint('==={!s} '
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
    NP.niceprocessedfiles(running.value,
                          count_total,
                          True)

    return True
