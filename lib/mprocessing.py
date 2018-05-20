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
import lib.NicePrint as NicePrint


# -----------------------------------------------------------------------------
# mprocessing
#
def mprocessing(args_verbose, args_verbose_progress,
                nprocs, lockdb, running, mutex, itemslist, a_fn, cur):
    """ mprocessing Function

    verbose          = verbose info
    verbose_progress = further verbose
    nprocs           = Number of processes to launch
    lockdb           = lock for access to Database
    running          = Value to count processed items
    mutex            = mutex for access to value running
    itemslist        = list of items to be processed
    a_fn             = a function which is the target of the multiprocessing
    cur              = cursor variable for DB access
    """
    # proc_pool   = Local variable proc_pool for Pool of processes
    # log_level   = log_level
    # count_total = Total counter of items to distribute/play/indicate progress
    #               len(itemslist)

    # =========================================================================
    # Functions aliases
    #
    #   npr.NicePrint = from NicePrint module
    # -------------------------------------------------------------------------
    npr = NicePrint.NicePrint()

    log_level = logging.getLogger().getEffectiveLevel()
    logging.info('===mprocessing [%s] target_fn():[%s] nprocs:[%s]',
                 __name__, a_fn.__name__, nprocs)
    # if log_level <= logging.WARNING:
    #     if args is not None:
    #         for i, arg in enumerate(args):
    #             logging.info('===mprocessing f():[%s] arg[%s]={%s}',
    #                          a_fn.__name__, i, arg)

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

            >>> for a in chunk([ 1, 2, 3, 4, 5, 6], 2):
            ...     len(a)
            2
            2
            3
        """
        iter_list = iter(iter_list)
        # lambda: creates a returning expression function
        # which returns slices
        # iter, with the second argument () stops creating
        # iterators when it reaches the end
        return iter(lambda: tuple(islice(iter_list, size)), ())

    proc_pool = []
    lockdb = multiprocessing.Lock()
    running = multiprocessing.Value('i', 0)
    mutex = multiprocessing.Lock()
    count_total = len(itemslist)

    size = (len(itemslist) // int(nprocs)) \
        if ((len(itemslist) // int(nprocs)) > 0) \
        else 1

    logging.debug('len(itemslist):[%s] '
                  'int(nprocs):[%s] '
                  'size per process:[%s]',
                  len(itemslist),
                  int(nprocs),
                  size)

    # Split itemslist in chunks to distribute accross Processes
    for splititemslist in chunk(itemslist, size):
        logging.warning('===Actual/Planned Chunk size: [%s]/[%s]',
                        len(splititemslist), size)
        logging.debug('===type(splititemslist)=[%s]', type(splititemslist))
        logging.debug('===Job/Task Process: Creating...')
        proc_task = multiprocessing.Process(
            target=a_fn,  # argument function
            args=(lockdb,
                  running,
                  mutex,
                  splititemslist,
                  count_total,
                  cur,))
        proc_pool.append(proc_task)
        logging.debug('===Job/Task Process: Starting...')
        proc_task.start()
        logging.debug('===Job/Task Process:  [%s] Started with pid:[%s]',
                      proc_task.name,
                      proc_task.pid)
        if args_verbose_progress:
            npr.niceprint('===Job/Task Process: [{!s}] Started '
                          'with pid:[{!s}]'
                          .format(proc_task.name,
                                  proc_task.pid))

    # Check status of jobs/tasks in the Process Pool
    if log_level <= logging.DEBUG:
        logging.debug('===Checking Processes launched/status:')
        for j in proc_pool:
            npr.niceprint('{!s}.is_alive = {!s}'.format(j.name, j.is_alive()))

    # Regularly print status of jobs/tasks in the Process Pool
    # Prints status while there are processes active
    # Exits when all jobs/tasks are done.
    while True:
        if not any(multiprocessing.active_children()):
            logging.debug('===No active children Processes.')
            break
        for prc in multiprocessing.active_children():
            logging.debug('===%s.is_alive = %s', prc.name, prc.is_alive())
            proc_task_active = prc
        logging.info('===Will wait for 60 on %s.is_alive = %s',
                     proc_task_active.name,
                     proc_task_active.is_alive())
        if args_verbose_progress:
            npr.niceprint('===Will wait for 60 on '
                          '{!s}.is_alive = {!s}'
                          .format(proc_task_active.name,
                                  proc_task_active.is_alive()))

        proc_task_active.join(timeout=60)
        logging.info('===Waited for 60s on %s.is_alive = %s',
                     proc_task_active.name,
                     proc_task_active.is_alive())
        if args_verbose:
            npr.niceprint('===Waited for 60s on '
                          '{!s}.is_alive = {!s}'
                          .format(proc_task_active.name,
                                  proc_task_active.is_alive()))

    # Wait for join all jobs/tasks in the Process Pool
    # All should be done by now!
    for j in proc_pool:
        j.join()
        if args_verbose_progress:
            npr.niceprint('==={!s} (is alive: {!s}).exitcode = {!s}'
                          .format(j.name, j.is_alive(), j.exitcode))

    logging.warning('===Multiprocessing=== pool joined! '
                    'All processes finished.')

    # Will release (set to None) the lockdb lock control
    # this prevents subsequent calls to
    # useDBLock( nuLockDB, False)
    # to raise exception:
    #   ValueError('semaphore or lock released too many times')
    logging.info('===Multiprocessing=== pool joined! '
                 'Is lockdb  None? [%s]. Setting lockdb to None anyhow.',
                 lockdb is None)
    lockdb = None

    # Show number of total files processed
    npr.niceprocessedfiles(running.value, count_total, True)

    return True


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                        '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()
