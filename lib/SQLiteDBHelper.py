"""
    by oPromessa, 2018
    Published on https://github.com/oPromessa/flickr-uploader/

    Helper module functions to wrap sqlite3 DB operations

    Recognition to:
    https://sebastianraschka.com/Articles/2014_sqlite_in_python_tutorial.html

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
import sqlite3 as lite
# -----------------------------------------------------------------------------
# Helper class and functions to print messages.
import lib.NicePrint as NicePrint
# -----------------------------------------------------------------------------
# Helper module function to split work accross functions in multiprocessing
import lib.mprocessing as mp

# =============================================================================
# Functions aliases
#
#   NPR     = NicePrint.NicePrin
# -----------------------------------------------------------------------------
NPR = NicePrint.NicePrint()
# -----------------------------------------------------------------------------


def connect(sqlite_file):
    """ connect

        Make connection to an SQLite database file
        Configures connection.text_factory = str
        Returns the connection and a cursor to be used in subsequent queries
    """

    logging.debug('Open DB [%s]', sqlite_file)
    conn = lite.connect(sqlite_file)
    conn.text_factory = str

    acursor = conn.cursor()
    logging.debug('Opened DB [%s]', sqlite_file)

    return conn, acursor


def execute(qry_name, adb_lock, nprocs,
            cursor, statement, qmarkargs=(),
            caughtcode='000'):
    """
        qry_name  = Query Name
        adb_lock  = lock to be used
        nprocs    = >0 when in multiprocessing mode
        cursor    = Cursor to use
        statement = SQL Statement to execute

        >>> import lib.SQLiteDBHelper as litedb
        >>> con, cur = litedb.connect("file::memory:?cache=shared")
        >>> litedb.execute('CREATE', None, 0, cur,
        ...                'CREATE TABLE IF NOT EXISTS files '
        ...                '(files_id INT, path TEXT, set_id INT, '
        ...                'md5 TEXT, tagged INT)')
        >>> litedb.execute('PRAGMA', None,0, cur, 'PRAGMA user_version="1"')
        >>> litedb.execute('ALTER', None, 0, cur,
        ...                'ALTER TABLE files ADD COLUMN last_modified REAL')
        >>> litedb.execute('INSERT', None, 0, cur,
        ...                'INSERT INTO files '
        ...                '(files_id, path, md5, '
        ...                'last_modified, tagged) '
        ...                 'VALUES (?, ?, ?, CURRENT_TIMESTAMP, 1)',
        ...                 qmarkargs=(1001, 'filepath', '0x1001'))
        >>> litedb.execute('SELECT', None, 0, cur,
        ...                'SELECT count(*) FROM %s' % 'files')
        >>> cur.fetchall()
        [(1,)]
        >>> litedb.close(con)
        >>> if con is not None:
        ...     con.close()

    """

    logging.debug('DBHelper.execute [%s] '
                  'statement:[%s] qmarkargs:[%s] type(qmarkargs):[%s]',
                  qry_name,
                  statement, qmarkargs, type(qmarkargs))
    assert isinstance(qmarkargs, tuple), NPR.niceassert(
        'DBHelper.execute [{!s}] {!s} is not a tuple!!'
        .format(qry_name, 'qmarkargs'))

    try:
        # Acquire DB lock if running in multiprocessing mode
        mp.use_lock(adb_lock, True, nprocs)
        cursor.execute(statement, qmarkargs)
    except lite.Error as err:
        NPR.niceerror(caught=True,
                      caughtprefix='+++ DB',
                      caughtcode=caughtcode,
                      caughtmsg='DB error on [{!s}]: [{!s}]'
                      .format(qry_name, err.args[0]),
                      useniceprint=True)
    finally:
        # Release DB lock if running in multiprocessing mode
        mp.use_lock(adb_lock, False, nprocs)


def close(conn):
    """ Commit changes and close connection to the database """
    # conn.commit()
    conn.close()


def total_rows(cursor, table_name, print_out=False):
    """ Returns the total number of rows in the database """
    cursor.execute('SELECT COUNT(*) FROM {}'.format(table_name))
    count = cursor.fetchall()
    if print_out:
        print('\nTotal rows: {}'.format(count[0][0]))
    return count[0][0]


# -----------------------------------------------------------------------------
# If called directly run doctests
#
if __name__ == "__main__":

    logging.basicConfig(level=logging.WARNING,
                        format='[%(asctime)s]:[%(processName)-11s]' +
                        '[%(levelname)-8s]:[%(name)s] %(message)s')

    import doctest
    doctest.testmod()
