# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# * listing active projects
# * associate a tag with active projects
# * are thee tags all filed properly?
# 
# Parallel questions for inactive projects

# <codecell>

import settings
from evernote.api.client import EvernoteClient
import EvernoteWebUtil as ewu

reload(ewu)


dev_token = settings.authToken
client = EvernoteClient(token=dev_token, sandbox=False)

userStore = client.get_user_store()
user = userStore.getUser()

print user.username

# <codecell>

ewu.notebook(name=":PROJECTS")

# <codecell>

# get all the notes in this notebook...

import datetime

from itertools import islice
notes = list(islice(ewu.notes_metadata(includeTitle=True, 
                                  includeUpdated=True,
                                  includeUpdateSequenceNum=True,
                                  notebookGuid=ewu.notebook(name=':PROJECTS').guid), None))

plus_tags_set = set()

for note in notes:
    tags = ewu.noteStore.getNoteTagNames(note.guid)
    plus_tags = [tag for tag in tags if tag.startswith("+")]
    
    plus_tags_set.update(plus_tags)
    print note.title, note.updateSequenceNum, datetime.datetime.fromtimestamp(note.updated/1000.),  \
         len(plus_tags) == 1
        
        
    # check that each note has one and only one tag that begins with "+"
    
    

# <codecell>

len(plus_tags_set)

# <codecell>

ewu.all_tags()

# <codecell>

[tag for tag in ewu._tags_by_name.keys() if tag.startswith("+")]

# <codecell>

len(_)

# <codecell>

# consolidate into one -- calculate "+" tags that are not covered in :PROJECTS notebook

import EvernoteWebUtil as ewu
reload(ewu)

import datetime
from itertools import islice


all_plus_tags = set(filter(lambda tag: tag.startswith("+"), 
                       [tag.name for tag in ewu.all_tags(refresh=False)]))


projects_notes = list(islice(ewu.notes_metadata(includeTitle=True, 
                                  includeUpdated=True,
                                  includeUpdateSequenceNum=True,
                                  notebookGuid=ewu.notebook(name=':PROJECTS').guid), None))

project_plus_tags = set()
for note in projects_notes:
    tags = ewu.noteStore.getNoteTagNames(note.guid)
    plus_tags = [tag for tag in tags if tag.startswith("+")]
    
    project_plus_tags.update(plus_tags)    

    
all_plus_tags - project_plus_tags

# <codecell>


