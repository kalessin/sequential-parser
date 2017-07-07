from distutils.core import setup
from setuptools import find_packages

import sequential_parser

setup(
  name = 'sequential-parser',
    packages = find_packages(),
    version = sequential_parser.__version__,
    description = 'Utility to extract structured text using text patterns and a state machine.',
    author = 'Martin Olveyra',
    author_email = 'molveyra@gmail.com',
    license = 'BSD',
    url = 'https://github.com/kalessin/sequential-parser',
    keywords = ['scraping', 'parsing'],
    classifiers = [
       'Intended Audience :: Developers',
       'Development Status :: 4 - Beta',
       'Operating System :: OS Independent',
       'License :: OSI Approved :: BSD License',
       'Programming Language :: Python :: 2.7',
       'Programming Language :: Python :: 3',
    ],
)
