# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <markdowncell>

# * listing active projects
# * associate a tag with active projects
# * are thee tags all filed properly?
# 
# Parallel questions for inactive projects

# <codecell>

import logging

import settings
from evernote.api.client import EvernoteClient
import EvernoteWebUtil as ewu

reload(ewu)

# logging
LOG_FILENAME = 'active_and_inactive_GTD_projects.log'
logging.basicConfig(filename=LOG_FILENAME,
                    level=logging.DEBUG,
                    )


dev_token = settings.authToken
client = EvernoteClient(token=dev_token, sandbox=False)

userStore = client.get_user_store()
user = userStore.getUser()

print user.username

# <codecell>

# get all the notes in the :PROJECTS Notebook

import datetime
from itertools import islice

notes = list(islice(ewu.notes_metadata(includeTitle=True, 
                                  includeUpdated=True,
                                  includeUpdateSequenceNum=True,
                                  notebookGuid=ewu.notebook(name=':PROJECTS').guid), None))

# accumulate all the tags that begin with "+" associated with notes in :PROJECTS notebook
plus_tags_set = set()

for note in notes:
    tags = ewu.noteStore.getNoteTagNames(note.guid)
    plus_tags = [tag for tag in tags if tag.startswith("+")]
    
    plus_tags_set.update(plus_tags)
    print note.title, note.guid, note.updateSequenceNum, datetime.datetime.fromtimestamp(note.updated/1000.),  \
         len(plus_tags) == 1
        
        
    # TO DO: check that each note has one and only one tag that begins with "+"
    
    

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

for proj_name in (all_plus_tags - project_plus_tags):
    print proj_name[1:]

# <codecell>

# next step:  generate a note in the :PROJECTS notebook with the same tag name (minus the beginning "+")
# http://dev.evernote.com/doc/articles/creating_notes.php

import EvernoteWebUtil as ewu

from evernote.edam.type.ttypes import Note

# put the note into the :PROJECTS notebook
projects_nb_guid = ewu.notebook(name=':PROJECTS').guid


note_template = """<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
<en-note style="word-wrap: break-word; -webkit-nbsp-mode: space; -webkit-line-break: after-white-space;">
{0}
</en-note>"""


for tag_name in (all_plus_tags - project_plus_tags):
    proj_name = tag_name[1:]
    note = ewu.create_note(proj_name, " ", tagNames=[tag_name], notebook_guid=projects_nb_guid)


# <markdowncell>

# # utility for deactivating an active project
# 
# Steps:
# 
# * rename tag "+TagName" to "-TagName"  (checking for possible name collision)
# * move the new tag to be a child of the .Inactive Projects tag
# * move the note to Projects Retired

# <codecell>

# all children of ".Active Projects" tag

[tag for tag in ewu.all_tags() if tag.parentGuid == ewu.tag(name=".Active Projects").guid]

# <codecell>

# make sure that + tags have the right parent (.Active Projects)

active_projects_tag = ewu.tag(name=".Active Projects")
inactive_projects_tag = ewu.tag(name=".Inactive Projects")

wayward_plus_tags = [tag for tag in ewu.all_tags(refresh=True) if tag.name.startswith("+") and tag.parentGuid != active_projects_tag.guid]
for tag in wayward_plus_tags:
    print tag.name
    tag.parentGuid = active_projects_tag.guid
    ewu.noteStore.updateTag(tag)

# <codecell>

# get all the .When tags

from collections import defaultdict

when_tags = [tag for tag in ewu.all_tags(refresh=True) if tag.parentGuid == ewu.tag(name=".When").guid]
when_tags_guids = set([tag.guid for tag in when_tags])
when_tags_guids

note_tags = defaultdict(list)

action_notes = list(islice(ewu.notes_metadata(includeTitle=True, 
                                  includeUpdated=True,
                                  includeUpdateSequenceNum=True,
                                  includeTagGuids=True,
                                  notebookGuid=ewu.notebook(name='Action Pending').guid), None))

# tags that have no .When tags whatsover
# ideally -- each action has one and only one .When tag

for note in action_notes:
    tag_guids = note.tagGuids
    
    if tag_guids is None:
        tag_guids = []
        
    tag_names = [ewu.tag(guid=g).name for g in tag_guids]
    for tag_name in tag_names:
        note_tags[tag_name].append(note)
        
    if len(tag_guids) == 0:
        note_tags['__UNTAGGED__'].append(note)
        

note_tags.keys()
    

# <codecell>


# deal with untagged notes
# note_tags['__UNTAGGED__']


# look at tags that begin with "-"
# how to retire an action?

# let's do some stuff by hand and then look at programming


to_clean = [t for t in note_tags.keys() if t.startswith("-")]
to_clean

# <codecell>

# open up a local view with

#evnote.open_collection_window(**{'with_query_string':"Bach"})
evnote.open_collection_window(with_query_string = '''notebook:"Action Pending" tag:"{0}"'''.format(to_clean[5]))

# <markdowncell>

# # How to retire an action
# 
# * strip action of all .when tags
# * move action to Retired Action Notebook / Reference
# 

# <codecell>

# we can take the ids that come from AppleScript and get the local folder location
# /Users/raymondyee/Library/Application Support/Evernote/accounts/Evernote/rdhyee/content/p11026/content.html

#path = "/Users/raymondyee/Library/Application Support/Evernote/accounts/Evernote/rdhyee/content/{0}/content.enml".format(note.id().split("/")[-1])
#path

# <codecell>

# with the exact title, you can look up the note, though it won't necessarily be unique.

list(ewu.notes("summarizing my attempts so far to access race/ethnicity data from 2010 Census"))

# <codecell>


reload(ewu)

ewu.web_api_notes_from_selection()

# <codecell>

# take selection and strip out the when tags

reload(ewu)
    
ewu.strip_when_tags_move_to_ref_nb_for_selection()

# <codecell>

# look for stray actions: ones that are tied to retired projects or yet to be activated projects

action_notes = list(islice(ewu.notes_metadata(includeTitle=True, 
                                  includeUpdated=True,
                                  includeUpdateSequenceNum=True,
                                  notebookGuid=ewu.notebook(name='Action Pending').guid), None))

len(action_notes)

# accumulate tags and compute a dict of tag -> notes, including notes with no project tag


# <codecell>

list(ewu.actions_for_project("+ProgrammableWeb"))

# <codecell>

# grab active project tags of selected item 


ewu.project_tags_for_selected()

# <codecell>

# for each of the selected projects, print out actions

for proj_tag in ewu.project_tags_for_selected():
    print proj_tag
    for n in list(ewu.actions_for_project(proj_tag)):
        print n.title
    print 

# <codecell>

from itertools import islice
import appscript

for proj_tag in islice(ewu.project_tags_for_selected(),1):
    retire_project(proj_tag, ignore_actions=False)
    
    

# <codecell>

ewu.strip_when_tags_move_to_ref_nb_for_selection()

# <codecell>

def retire_project(tag_name,
                   ignore_actions=False,
                   dry_run=False, 
                   display_remaining_actions=True):
    
    """
    Retire the project represented by tag_name
    """
    tag = ewu.tag(name=tag_name)
    
    # make sure tag_name starts with "+"
    if not tag_name.startswith("+"):
        return tag
    
    # if ignore_actions is False, check whether are still associated actions for the project. 
    # if there are actions, then don't retire project.  Optionally display actions in Evernote
    if not ignore_actions:
        associated_actions = list(ewu.actions_for_project(tag_name))
        if len(associated_actions):
            if display_remaining_actions:
                from appscript import app
                evnote = app('Evernote')
                evnote.open_collection_window(with_query_string = '''notebook:"Action Pending" tag:"{0}"'''.format(tag_name))
                
            return tag_name
    
    
    # before just trying to turn the + to a -, check for existence of the new name.
    # if the new name exists, we would delete the + tag and apply the - tag to the notes tied to the
    # + tag
    
    # let's take care of the simple case first

    # do I have logic for finding all notes that have a given tag? 
    # tagging a set of notes with a given tag?

    retired_tag_name = "-" + tag_name[1:]
    
    if ewu.tag(retired_tag_name) is None:
        tag.name = retired_tag_name
    else:
        raise Exception("{0} already exists".format(retired_tag_name))

    # change parent reference
    tag.parentGuid = ewu.tag('.Inactive Projects').guid

    # move the project note (if it exists) from the project notebook to the retired project notebook

    project_notes = ewu.notes_metadata(includeTitle=True, includeNotebookGuid=True, 
                            tagGuids = [tag.guid],
                            notebookGuid=ewu.notebook(name=':PROJECTS').guid)

    # with NoteMetadata, how to make change to the corresponding note?
    # make use of 
    # http://dev.evernote.com/doc/reference/NoteStore.html#Fn_NoteStore_updateNote

    for note in project_notes:
        note.notebookGuid = ewu.notebook(name=":PROJECTS--RETIRED").guid
        ewu.noteStore.updateNote(note)
        
    # deal with the associated actions for the project

    # apply changes to tag
    ewu.noteStore.updateTag(tag)
    
    return tag


# <codecell>

# first the project note

project_notes = list(ewu.notes_metadata(includeTitle=True, includeNotebookGuid=True, 
                        tagGuids = [hackfsm_tag.guid],
                        notebookGuid=ewu.notebook(name=':PROJECTS').guid))

# with NoteMetadata, how to make change to the corresponding note?
# make use of 
# http://dev.evernote.com/doc/reference/NoteStore.html#Fn_NoteStore_updateNote

for note in project_notes:
    print note
    note.notebookGuid = ewu.notebook(name=":PROJECTS--RETIRED").guid
    

# <headingcell level=1>

# Practice making an :INBOX and moving it to :REFERENCE notebook

# <codecell>

# let's practice moving notes between notebooks.
# create a new note in :INBOX

reload(ewu)
import datetime

note = ewu.create_note(title="hello1: {0}".format(datetime.datetime.now().isoformat()), 
                       content = """I want some <b>bold</b> action. 
<div>I want some <i>italics</i> performance.</div>""",
                       tagNames= ['testing', 'ipynb-generated'],
                       notebookGuid=ewu.notebook(name=':INBOX').guid)

note

# <codecell>

# and then move it to :REFERENCE
# http://dev.evernote.com/doc/reference/NoteStore.html#Fn_NoteStore_updateNote

note.notebookGuid = ewu.notebook(name=':REFERENCE').guid
ewu.noteStore.updateNote(note)

# <codecell>

ewu.notebook(name=":PROJECTS--RETIRED")

