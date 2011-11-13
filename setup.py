from setuptools import setup, find_packages

version = '0.4dev'

long_description = (
    open('README.txt').read()
    + '\n' +
    open('CHANGES.txt').read())

setup(name='pycounters',
      version=version,
      description='PyCounters is a light weight library to monitor performance and events in production systems',
      long_description=long_description,
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='PyCounters Developers',
      author_email='b.leskes@gmail.com',
      url='http://pycounters.readthedocs.org',
      license='apache',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      include_package_data=True,
      zip_safe=False,
      install_requires=[
      	])