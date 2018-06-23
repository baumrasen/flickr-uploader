#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
    by oPromessa, 2017, 2018
    Published on https://github.com/oPromessa/flickr-uploader/

    setup.py utility for flickr-uploader

    Note: To use the 'upload' functionality of this file, you must:
    $ pip install twine
"""

# =============================================================================
# Import section
import io
import os
import sys
import errno
from shutil import rmtree, copy

from setuptools import find_packages, setup, Command
# To access data_files uploadr.ini from egg resource package
from pkg_resources import Requirement, resource_filename

# Package meta-data.
NAME = 'flickr-uploader'
DESCRIPTION = 'Upload a directory of media (pics/videos) to Flickr for '\
    'showing off your pics on the WEB and as a backup of your local storage. '\
    'flickr-uploader designed primarly for Synology Devices. '\
    'Also works on Linux, Mac and Windows systems.'
URL = 'https://github.com/oPromessa/flickr-uploader/'

EMAIL = 'oPromessa@gmail.com'
AUTHOR = 'oPromessa'
REQUIRES_PYTHON = '>=2.7.*, >=3.6.*, <4'
LIB = 'lib'
VERSION = None  # Load from LIB/__version__.py dictionary

# What packages are required for this module to be executed?
REQUIRED = [
    'flickrapi',
    'portalocker;platform_system=="Windows"',
]
# What data_files are required for this applicaiton to be configured?
DATA_FILES = [('etc', ['uploadr.ini', 'uploadr.cron'])]

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you change the License, remember to change the Trove Classifier for that!

HERE = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this only works if 'README.rst' is present in your MANIFEST.in file!
with io.open(os.path.join(HERE, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = '\n' + f.read()

# Load the package's __version__.py module as a dictionary.
ABOUT = {}
if not VERSION:
    with open(os.path.join(HERE, LIB, '__version__.py')) as f:
        exec(f.read(), ABOUT)
else:
    ABOUT['__version__'] = VERSION


class UploadCommand(Command):
    """Support setup.py upload."""

    testpypi = False
    pypi_repository = ''
    description = 'Build and publish the package.'
    # Show options for 'python setup.py upload --help'
    user_options = [
        ('testpypi',
         None,
         'Use test PyPI repository.'),
    ]

    @staticmethod
    def bstatus(astr):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(astr))

    @staticmethod
    def status(astr):
        """Prints things."""
        print('{0}'.format(astr))

    def initialize_options(self):
        """initialize_options"""
        self.testpypi = False

    def finalize_options(self):
        """finalize_options"""
        pass

    def run(self):
        """run"""

        # Use with upload command for PYPI test url: test.pypi.org
        if self.testpypi:
            self.pypi_repository = '--repository-url '\
                'https://test.pypi.org/legacy/'
        else:
            self.pypi_repository = ''

        try:
            self.bstatus('Removing previous builds…')
            rmtree(os.path.join(HERE, 'dist'))
        except OSError:
            pass

        self.bstatus('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'
                  .format(sys.executable))

        self.bstatus('Uploading the package to PyPi via Twine... to [%s]'
                     % self.pypi_repository)
        # os.system('twine upload dist/*')
        os.system('twine upload {!s} dist/*'.format(self.pypi_repository))

        # upload to GitHub disabled for now
        # self.bstatus('Pushing git tags...')
        # os.system('git tag v{0}'.format(ABOUT['__version__']))
        # os.system('git push --tags')

        sys.exit()


class InstallCfg(Command):
    """
    Support setup.py install flickr-uploader configuration files:

    DATA_FILES   = list of configuration options files (.ini, .cron, etc)
    """

    folder = None
    # Show files to be coppied under 'python setup.py installcfg --help'
    str_user_options = ''
    dcnt = 0
    for atuple in DATA_FILES:
        dcnt += 1
        if dcnt > 1:
            str_user_options = str_user_options + ', '
        cfgdir = atuple[0]
        cnt = 0
        for cfgfile in atuple[1]:
            cnt += 1
            if cnt > 1:
                str_user_options = str_user_options + ', '
            str_user_options = str_user_options + \
                '"' + os.path.join(cfgdir, cfgfile) + '"'

    description = 'Custom install flickr-uploader configuration files'
    user_options = [
        ('folder=',
         None,
         'Folder location for ' + str_user_options + ' files.'),
    ]

    @staticmethod
    def bstatus(astr):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(astr))

    @staticmethod
    def status(astr):
        """Prints things."""
        print('{0}'.format(astr))

    def initialize_options(self):
        """initialize_options"""
        self.folder = os.path.join(sys.prefix, 'etc')

    def finalize_options(self):
        """finalize_options"""
        pass

    def run(self):
        """run"""
        self.bstatus('Installing config files into folder [%s]'
                     % str(self.folder))

        if self.folder:
            dst = self.folder

            try:
                os.makedirs(dst)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(dst):
                    pass
                else:
                    raise

            # Save file list to be copied within the run method.
            # Note: Does not account for files wihtin folders of the package!
            src = []
            for atuple in DATA_FILES:
                for cfgfile in atuple[1]:
                    src.append(resource_filename(Requirement.parse(NAME),
                                                 cfgfile))
            for f_to_copy in src:
                self.status("Copying [%s] into folder [%s]"
                            % (str(f_to_copy), str(dst)))
                if sys.version_info < (3, ):
                    copy(f_to_copy, dst)
                else:
                    copy(f_to_copy, dst, follow_symlinks=True)

        if self.folder:
            assert os.path.exists(self.folder), (
                'flickr-uploadr config folder {!s} does not exist.'
                .format(str(self.folder)))
            for f_to_check in src:
                assert os.path.exists(f_to_check), (
                    'flickr-uploadr config file {!s} does not exist.'
                    .format(str(f_to_check)))
            self.bstatus('Installed config files into folder [%s]'
                         % str(self.folder))

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=ABOUT['__version__'],
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author=AUTHOR,
    author_email=EMAIL,
    # Support for this feature is relatively recent.
    # Use at least version 24.2.0 of setuptools in order for the
    # python_requires argument to be recognized and the appropriate
    # metadata generated.
    # python_requires=REQUIRES_PYTHON,
    url=URL,
    packages=find_packages(exclude=('tests',)),
    # If your package is a single module, use this instead of 'packages':
    # py_modules=['mypackage'],

    # entry_points={
    #     'console_scripts': ['mycli=mymodule:cli'],
    # },
    install_requires=REQUIRED,
    include_package_data=True,
    scripts=['uploadr.py'],
    data_files=DATA_FILES,
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 4 - Beta',
        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6',
        'Topic :: Multimedia',
        'Topic :: System :: Archiving :: Backup',
        'Topic :: System :: Archiving :: Mirroring'
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
        'installcfg': InstallCfg,
    },
)
