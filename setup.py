from setuptools import setup
import sys, os

version = '1.0dev'

long_description = (
    open('README.txt').read()
    + '\n' +
    open('CHANGES.txt').read())

setup(name='pycounters',
      version=version,
      description='A Python based light weight manual instrumantion livrary',
      long_description=long_description,
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='PyCounters Developers',
      author_email='b.leskes@gmail.com',
      url='',
      license='apache',
      packages=['pycounters'],
      package_dir = {'': 'src'},
      include_package_data=True,
      zip_safe=False,
      install_requires=[
      	])