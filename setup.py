#!/usr/bin/env python
# -*- coding: utf-8 -*-


try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


setup(name='EvernoteWebUtil',
      version='0.0.12.9',
      packages=['EvernoteWebUtil', 'EvernoteWebUtil.appscript'],
      )
