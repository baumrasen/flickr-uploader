#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Note: To use the 'upload' functionality of this file, you must:
#   $ pip install twine

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
DESCRIPTION = 'Upload a directory of media to Flickr to use as a backup to '
'your local storage. flickr-uploader designed primarly for Synology Devices.'
URL = 'https://github.com/oPromessa/flickr-uploader/',

EMAIL = 'oPromessa@github.com'
AUTHOR = 'oPromessa'
REQUIRES_PYTHON = '>=2.7.*, >=3.6.*, <4'
LIB = 'lib'
VERSION = None  # Load from LIB/__version__.py dictionary

# What packages are required for this module to be executed?
REQUIRED = [
    'flickrapi',
]

# The rest you shouldn't have to touch too much :)
# ------------------------------------------------
# Except, perhaps the License and Trove Classifiers!
# If you change the License, remember to change the Trove Classifier for that!

here = os.path.abspath(os.path.dirname(__file__))

# Import the README and use it as the long-description.
# Note: this only works if 'README.rst' is present in your MANIFEST.in file!
with io.open(os.path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = '\n' + f.read()

# Load the package's __version__.py module as a dictionary.
about = {}
if not VERSION:
    with open(os.path.join(here, LIB, '__version__.py')) as f:
        exec(f.read(), about)
else:
    about['__version__'] = VERSION


class UploadCommand(Command):
    """Support setup.py upload."""

    description = 'Build and publish the package.'
    user_options = []

    @staticmethod
    def bstatus(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    @staticmethod
    def status(s):
        """Prints things."""
        print('{0}'.format(s))

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        try:
            self.bstatus('Removing previous builds…')
            rmtree(os.path.join(here, 'dist'))
        except OSError:
            pass

        self.bstatus('Building Source and Wheel (universal) distribution…')
        os.system('{0} setup.py sdist bdist_wheel --universal'
                  .format(sys.executable))

        # Upload disabled for now
        # self.bstatus('Uploading the package to PyPi via Twine...')
        # os.system('twine upload dist/*')

        # upload to GitHub disbled for now
        # self.bstatus('Pushing git tags...')
        # os.system('git tag v{0}'.format(about['__version__']))
        # os.system('git push --tags')

        sys.exit()


class InstallCfg(Command):
    """
    Support setup.py install flickr-uploader configuration files:

    uploadr.ini  = configuration options files
    uploadr.cron = used for CRON
    """

    description = 'Custom install flickr-uploader configuration files'
    user_options = [
           ('folder=',
            None,
            'Folder location for uploadr.ini and uploadr.cron'),
    ]

    @staticmethod
    def bstatus(s):
        """Prints things in bold."""
        print('\033[1m{0}\033[0m'.format(s))

    @staticmethod
    def status(s):
        """Prints things."""
        print('{0}'.format(s))

    def initialize_options(self):
        self.folder = os.path.join(sys.prefix, 'etc')

    def finalize_options(self):
        pass

    def run(self):

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
            src = []
            src.append(resource_filename(Requirement.parse(NAME),
                                         "uploadr.ini"))
            src.append(resource_filename(Requirement.parse(NAME),
                                         "uploadr.cron"))
            for f in src:
                self.status("Copying [%s] into folder [%s]"
                            % (str(f), str(dst)))
                copy(f, dst) if sys.version_info < (3, ) \
                    else copy(f, dst, follow_symlinks=True)

        if self.folder:
            assert os.path.exists(self.folder), (
                'flickr-uploadr config folder %s does not exist.'
                .format(str(self.folder)))
            for f in src:
                assert os.path.exists(f), (
                    'flickr-uploadr config file %s does not exist.'
                    .format(str(f)))
            self.bstatus('Installed config files into folder [%s]'
                         % str(self.folder))

        sys.exit()


# Where the magic happens:
setup(
    name=NAME,
    version=about['__version__'],
    description=DESCRIPTION,
    long_description=long_description,
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
    data_files=[('', ['uploadr.ini', 'uploadr.cron'])],
    license='MIT',
    classifiers=[
        # Trove classifiers
        # Full list: https://pypi.python.org/pypi?%3Aaction=list_classifiers
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.6'
    ],
    # $ setup.py publish support.
    cmdclass={
        'upload': UploadCommand,
        'installcfg': InstallCfg,
    },
)
