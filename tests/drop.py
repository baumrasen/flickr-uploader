"""
    adapted by oPromessa, 2018

    Backs up and restores a settings file to Dropbox.
    This is an example app for API v2.
"""

# -----------------------------------------------------------------------------
# Import section for Python 2 and 3 compatible code
# from __future__ import absolute_import, division, print_function,
#    unicode_literals
from __future__ import division    # This way: 3 / 2 == 1.5; 3 // 2 == 1

# -----------------------------------------------------------------------------
# Import section
#
import sys
import argparse
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError, AuthError

# Add OAuth2 access token here.
# You can generate one for yourself in the App Console.
# See <https://blogs.dropbox.com/developers/2014/05/
# generate-an-access-token-for-your-own-account/>
TOKEN = ''
LOCALFILE = 'my-file.txt'
BACKUPPATH = '/my-file-backup.txt'


def backup():
    """ backups

        Uploads contents of LOCALFILE to Dropbox
    """
    with open(LOCALFILE, 'rb') as fobj:
        # We use WriteMode=overwrite to make sure that the settings
        # in the file are changed on upload
        print("Uploading [" +
              LOCALFILE +
              "] to Dropbox as [" +
              BACKUPPATH
              + "]...")
        try:
            DBX.files_upload(fobj.read(),
                             BACKUPPATH,
                             mode=WriteMode('overwrite'))
        except ApiError as err:
            # This checks for the specific error where a user doesn't have
            # enough Dropbox space quota to upload this file
            if (err.error.is_path() and
                    err.error.get_path().reason.is_insufficient_space()):
                sys.exit("ERROR: Cannot back up; insufficient space.")
            elif err.user_message_text:
                print(err.user_message_text)
                sys.exit()
            else:
                print(err)
                sys.exit()
        except BaseException:
            sys.stderr.write(str(sys.exc_info()))
            sys.stderr.flush()


def restore(rev=None):
    """ restore

        Restore the local and Dropbox files to a certain revision
        Restore the file on Dropbox to a certain revision
    """
    print("Restoring [" +
          BACKUPPATH +
          "] to revision [" +
          rev +
          "] on Dropbox...")
    DBX.files_restore(BACKUPPATH, rev)

    # Download the specific revision of the file at BACKUPPATH to LOCALFILE
    print("Downloading current [" +
          BACKUPPATH +
          "] from Dropbox, overwriting ["
          +
          LOCALFILE
          + "]...")
    DBX.files_download_to_file(LOCALFILE, BACKUPPATH, rev)


# Look at all of the available revisions on Dropbox, and return the oldest one
def select_revision():
    """ select_revision

        Get the revisions for a file (and sort by the datetime object,
        "server_modified")
    """
    print("Finding available revisions on Dropbox...")
    entries = DBX.files_list_revisions(BACKUPPATH, limit=30).entries
    revisions = sorted(entries, key=lambda entry: entry.server_modified)

    for revision in revisions:
        print(revision.rev, revision.server_modified)

    # Return the oldest revision (first entry, because revisions was sorted
    # oldest:newest)
    return revisions[0].rev


if __name__ == '__main__':
    PARSER = argparse.ArgumentParser(description='upload a file to Dropbox')
    PARSER.add_argument('file', action='store', default='my-file.txt',
                        help='Source file name to upload to your Dropbox. '
                        'Default value is Downloads')
    PARSER.add_argument('dstfolder', nargs='?', default='Downloads',
                        help='Destination folder name in your Dropbox')
    PARSER.add_argument('--token', default=TOKEN,
                        help='Access token '
                        '(see https://www.dropbox.com/developers/apps)')
    ARGS = PARSER.parse_args()

    TOKEN = ARGS.token
    LOCALFILE = ARGS.file
    BACKUPPATH = '/' + ARGS.dstfolder + '/' + LOCALFILE
    # Check for an access token
    if not TOKEN:
        sys.exit("ERROR: Looks like you didn't provide your access token "
                 "via --token argument.")

    # Create an instance of a Dropbox class,
    # which can make requests to the API.
    print("Creating a Dropbox object...")
    DBX = dropbox.Dropbox(TOKEN)

    # Check that the access token is valid
    try:
        DBX.users_get_current_account()
    except AuthError as err:
        sys.exit("ERROR: Invalid access token; try re-generating an "
                 "access token from the app console on the web.")

    # Create a backup of the current settings file
    backup()

    print("Done!")
