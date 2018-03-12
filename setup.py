#!/usr/bin/env python

from distutils.core import setup

setup(
      # Application name:
      name='Flickr-Uploader',

      # Version number (initial):
      version='2.7.1',
      description='Python Distribution Utilities',

      # Application author details:
      author='oPromessa',
      author_email='oPromessa@github.com',
      url='https://github.com/oPromessa/flickr-uploader/',

      # Packages
      packages=['uploadr'],

      # Include additional files into the package
      #include_package_data=True,

      # license="LICENSE.txt",

      # long_description=open("README.md").read(),

      # Dependent packages (distributions)
      install_requires=[
          "flickrapi",
      ],
)
