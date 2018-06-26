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

# =========================================================================
# Functions aliases
#
#   NPR.NicePrint = from NicePrint module
# -------------------------------------------------------------------------
NPR = NicePrint.NicePrint()


# -------------------------------------------------------------------------
# use_lock
#
# Control use of DB lock. acquire/release
#
def use_lock(adb_lock, operation, nprocs=0):
    """ use_lock

        adb_lock  = lock to be used
        operation = True => Lock
                  = False => Release
        nprocs    = >0 when in multiprocessing mode

        >>> alock = multiprocessing.Lock()
        >>> use_lock(alock, True, 2)
        True
        >>> use_lock(alock, False, 2)
        True
    """

    use_dblock_return = False

    logging.debug('Entering use_lock with operation:[%s].', operation)

    if adb_lock is None:
        logging.debug('use_lock: adb_lock is [None].')
        return use_dblock_return

    logging.debug('use_lock: adb_lock.semlock:[%s].', adb_lock._semlock)

    if operation is None:
        return use_dblock_return

    if (nprocs is not None) and (nprocs) and (nprocs > 0):
        if operation:
            # Control for when running multiprocessing set locking
            logging.debug('===Multiprocessing=== -->[ ].lock.acquire')
            try:
                if adb_lock.acquire():
                    use_dblock_return = True
            except Exception:
                NPR.niceerror(caught=True,
                              caughtprefix='+++ ',
                              caughtcode='002',
                              caughtmsg='Caught an exception lock.acquire',
                              useniceprint=True,
                              exceptsysinfo=True)
                raise
            logging.info('===Multiprocessing=== --->[v].lock.acquire')
        else:
            # Control for when running multiprocessing release locking
            logging.debug('===Multiprocessing=== <--[ ].lock.release')
            try:
                adb_lock.release()
                use_dblock_return = True
            except Exception:
                NPR.niceerror(caught=True,
                              caughtprefix='+++ ',
                              caughtcode='003',
                              caughtmsg='Caught an exception lock.release',
                              useniceprint=True,
                              exceptsysinfo=True)
                # Raise aborts execution
                raise
            logging.info('===Multiprocessing=== <--[v].lock.release')

        logging.info('Exiting use_lock with operation:[%s]. Result:[%s]',
                     operation, use_dblock_return)
    else:
        use_dblock_return = True
        logging.warning('(No multiprocessing. Nothing to do) '
                        'Exiting use_lock with operation:[%s]. Result:[%s]',
                        operation, use_dblock_return)

    return use_dblock_return


# -----------------------------------------------------------------------------
# mprocessing
#
def mprocessing(nprocs, lockdb, running, mutex, itemslist, a_fn, cur):
    """ mprocessing Function

    nprocs           = Number of processes to launch (int)
    lockdb           = lock for access to Database (lock obj to be created)
    running          = Value to count processed items (count obj to be created)
    mutex            = mutex for access to value running (obj to be created)
    itemslist        = list of items to be processed
    a_fn             = a function which is the target of the multiprocessing
                       a_fn must cater the following arguments
                            lockdb
                            running
                            mutex
                            splititemslist = partial splitted list
                            count_total    = len(itemslist)
                            cur
    cur              = cursor variable for DB access
    """
    # proc_pool   = Local variable proc_pool for Pool of processes
    # log_level   = log_level
    # count_total = Total counter of items to distribute/play/indicate progress
    #               len(itemslist)

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

            >>> for a in chunk([ 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 3):
            ...     len(a)
            3
            3
            3
            1
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

    logging.debug('len(itemslist):[%s] int(nprocs):[%s] size per process:[%s]',
                  len(itemslist), int(nprocs), size)

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
        NPR.niceprint('===Job/Task Process: [{!s}] Started '
                      'with pid:[{!s}]'
                      .format(proc_task.name,
                              proc_task.pid),
                      verbosity=3)

    # Check status of jobs/tasks in the Process Pool
    if log_level <= logging.DEBUG:
        logging.debug('===Checking Processes launched/status:')
        NPR.niceprint('===Checking Processes launched/status:', verbosity=3)
        for j in proc_pool:
            NPR.niceprint('{!s}.is_alive = {!s}'.format(j.name, j.is_alive()),
                          verbosity=3)
            logging.debug('%s.is_alive = %s', j.name, j.is_alive())

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
        NPR.niceprint('===Will wait for 60 on {!s}.is_alive = {!s}'
                      .format(proc_task_active.name,
                              proc_task_active.is_alive()),
                      verbosity=3)

        proc_task_active.join(timeout=60)
        logging.info('===Waited for 60s on %s.is_alive = %s',
                     proc_task_active.name,
                     proc_task_active.is_alive())
        NPR.niceprint('===Waited for 60s on '
                      '{!s}.is_alive = {!s}'
                      .format(proc_task_active.name,
                              proc_task_active.is_alive()),
                      verbosity=3)

    # Wait for join all jobs/tasks in the Process Pool
    # All should be done by now!
    for j in proc_pool:
        j.join()
        NPR.niceprint('==={!s} (is alive: {!s}).exitcode = {!s}'
                      .format(j.name, j.is_alive(), j.exitcode),
                      verbosity=2)

    logging.warning('===Multiprocessing=== pool joined! '
                    'All processes finished.')

    # Will release (set to None) the lockdb lock control
    # this prevents subsequent calls to
    # use_lock( nuLockDB, False)
    # to raise exception:
    #   ValueError('semaphore or lock released too many times')
    logging.info('===Multiprocessing=== pool joined! '
                 'Is lockdb  None? [%s]. Setting lockdb to None anyhow.',
                 lockdb is None)
    lockdb = None

    # Show number of total files processed
    NPR.niceprocessedfiles(running.value, count_total, True)

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
