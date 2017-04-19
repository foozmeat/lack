import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="lack",
    version="1.0",
    author="James Moore",
    author_email="hello@jmoore.me",
    description=("A curses-based slack client"),
    license="MIT",
    keywords="curses slack async",
    url="",
    packages=['lack'],
    long_description=read('README.md'),
    classifiers=[
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
    ],
    install_requires=[
        'slackclient',
        'sortedcontainers',
        'pytz',
    ]
)
