# -*- coding: utf-8 -*-

from setuptools import setup

import re

from pandoc_source_exec import __version__

REPOSITORY = 'https://github.com/shoeffner/pandoc-source-exec'

README = ''
with open('README.rst', 'r') as f:
    README = f.read()
README = re.sub(r' _(.+): ([^(http)].+)', r' _\1: {}/blob/master/\2'
                .format(REPOSITORY), README)

setup(
  name='pandoc-source-exec',
  version=__version__,
  description='A pandoc filter for executing (python) code and including the results.',  # noqa
  long_description=README,
  entry_points={'console_scripts': ['pandoc-source-exec = pandoc_source_exec:main']},  # noqa
  scripts=['./pandoc_source_exec/pandoc-source-exec.py'],
  author='Sebastian Höffner',
  author_email='info@sebastian-hoeffner.de',
  url=REPOSITORY,
  download_url='{}/tarball/{}'.format(REPOSITORY, __version__),
  packages=['pandoc_source_exec'],
  classifiers=[
      'Development Status :: 3 - Alpha',
      'Intended Audience :: Science/Research',
      'License :: OSI Approved :: MIT License',
      'Natural Language :: English',
      'Programming Language :: Python :: 3.6',
      'Topic :: Text Processing :: Filters',
  ],
  install_requires=['panflute>=1.10.3', 'pexpect>=4.2.1',
                    'matplotlib2tikz>=0.6.6'],
  license='MIT',
  keywords=['pandoc', 'filter', 'code', 'execution'],
)
