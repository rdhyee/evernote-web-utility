#!/bin/env python

import pytest

import datetime
import logging
import settings

import EvernoteWebUtil as ewu

from itertools import islice
from evernote.api.client import EvernoteClient

# logging
LOG_FILENAME = 'ewu_test.log'
logging.basicConfig(filename=LOG_FILENAME,
                    level=logging.DEBUG,
                    )

dev_token = settings.authToken
ewu.init(dev_token, sandbox=False)

client = ewu.client
userStore = client.get_user_store()
user = userStore.getUser()


def test_username():
    assert user.username is not None




