"""
Wrapper for the Evernote Python SDK
"""

__all__ = ["client", "userStore",  "user", "noteStore", "all_notebooks", "notes_metadata", "sizes_of_notes",
           "all_tags", "tag", "tag_counts_by_name", "tags_by_guid", "init", "project_notes_and_tags",
           "projects_to_df", "all_actions", "actions_to_df", "non_project_plus_tags",
           'fix_wayward_plus_tags', 'action_note_tags', 'retire_project']

from itertools import islice

import logging
logger = logging.getLogger(__name__)

# https://github.com/evernote/evernote-sdk-python/blob/master/sample/client/EDAMTest.py

import datetime
from time import sleep
import arrow

from evernote.api.client import EvernoteClient
from evernote.edam.type.ttypes import Note
from evernote.edam.notestore.ttypes import (NoteFilter,
                                            NotesMetadataResultSpec
                                           )
from evernote.edam.error.ttypes import (EDAMSystemException, EDAMErrorCode)

from pandas import DataFrame
from collections import defaultdict



def init(auth_token, sandbox=False):
    """
    enable auth_token to be set
    """
    global _client, client, userStore, noteStore, user
    global _notebooks, _notebook_name_dict, _notebook_guid_dict
    global _tags, _tag_counts, _tags_by_name, _tags_by_guid, _tag_counts_by_name
    global _when_tags, _when_tags_guids

    _client = EvernoteClient(token=auth_token, sandbox=sandbox)
    client = RateLimitingEvernoteProxy(_client)

    userStore = client.get_user_store()
    noteStore = client.get_note_store()

    user = userStore.getUser()

    _notebooks = None
    _notebook_name_dict = None
    _notebook_guid_dict = None

    _tags = None
    _tag_counts = None
    _tags_by_name = None
    _tags_by_guid = None
    _tag_counts_by_name = None

    _when_tags = [t for t in all_tags() if t.parentGuid == tag(name=".When").guid]
    _when_tags_guids = set([t.guid for t in _when_tags])


def evernote_wait_try_again(f):
    """
    Wait until mandated wait and try again
    http://dev.evernote.com/doc/articles/rate_limits.php
    """

    def f2(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except EDAMSystemException, e:
            if e.errorCode == EDAMErrorCode.RATE_LIMIT_REACHED:
                logger.info( "rate limit: {0} s. wait".format(e.rateLimitDuration))
                sleep(e.rateLimitDuration)
                logger("wait over")
                return f(*args, **kwargs)

    return f2

class RateLimitingEvernoteProxy(object):
    # based on http://code.activestate.com/recipes/496741-object-proxying/
    __slots__ = ["_obj"]
    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)

    def __getattribute__(self, name):
        return evernote_wait_try_again(getattr(object.__getattribute__(self, "_obj"), name))

def all_notebooks(refresh=False):
    # List all of the notebooks in the user's account

    global _notebooks, _notebook_guid_dict, _notebook_name_dict

    if _notebooks is None or refresh:
        _notebooks = noteStore.listNotebooks()
        _notebook_guid_dict = dict([(nb.guid, nb) for nb in _notebooks])
        _notebook_name_dict = dict([(nb.name, nb) for nb in _notebooks])
    return _notebooks

def notebook(name=None, guid=None, refresh=False):

    global _notebooks, _notebook_guid_dict, _notebook_name_dict

    if _notebooks is None or refresh:
        nb = all_notebooks(refresh)

    if name is not None:
        return _notebook_name_dict.get(name)
    elif guid is not None:
        return _notebook_guid_dict.get(guid)
    else:
        return None

def all_tags(refresh=False):

    global _tags, _tag_counts, _tags_by_name, _tags_by_guid, _tag_counts_by_name, _tag_counts

    if _tags is None or refresh:
        _tags = noteStore.listTags()
        _tag_counts = noteStore.findNoteCounts(NoteFilter(), False)

        _tags_by_name = dict([(tag.name, tag) for tag in _tags])
        _tags_by_guid = dict([(tag.guid, tag) for tag in _tags])

        _tag_counts_by_name = dict([(_tags_by_guid[guid].name, count) for (guid, count) in _tag_counts.tagCounts.items()])

    return _tags

def tag (name=None, guid=None, refresh=False):

    if _tags is None or refresh:
        tags = all_tags(refresh)

    # add count if available
    if name is not None:
        _tag = _tags_by_name.get(name)
        if _tag is not None:
            _tag.count = _tag_counts_by_name.get(name, 0)
        return _tag
    elif guid is not None:
        _tag = _tags_by_guid.get(guid)
        if _tag is not None:
            _tag.count = _tag_counts_by_name.get(_tag.name, 0)
        return _tag
    else:
        return None

def tag_counts_by_name(refresh=False):

    if _tags is None or refresh:
        tags = all_tags(refresh)

    return _tag_counts_by_name

def tags_by_guid(refresh=False):

    if _tags is None or refresh:
        tags = all_tags(refresh)

    return _tags_by_guid

def display_notebooks():
    notebooks = all_notebooks()
    for (i, notebook) in enumerate(notebooks):
        print i, notebook.name, notebook.guid

def notebookcounts():
    """ return a dict of notebook guid -> number of notes in notebook"""
    # http://dev.evernote.com/documentation/reference/NoteStore.html#Fn_NoteStore_findNoteCounts

    counts = noteStore.findNoteCounts(NoteFilter(), False)
    return counts.notebookCounts

def notes_metadata(**input_kw):
    """ """
    # http://dev.evernote.com/documentation/reference/NoteStore.html#Fn_NoteStore_findNotesMetadata

    # pull out offset and page_size value if supplied
    offset = input_kw.pop("offset", 0)
    page_size = input_kw.pop("page_size", 100)

    # let's update any keywords that are updated
    # http://dev.evernote.com/documentation/reference/NoteStore.html#Struct_NotesMetadataResultSpec

    include_kw = {
        'includeTitle':False,
        'includeContentLength':False,
        'includeCreated':False,
        'includeUpdated':False,
        'includeDeleted':False,
        'includeUpdateSequenceNum':False,
        'includeNotebookGuid':False,
        'includeTagGuids':False,
        'includeAttributes':False,
        'includeLargestResourceMime':False,
        'includeLargestResourceSize':False
    }

    include_kw.update([(k, input_kw[k]) for k in set(input_kw.keys()) & set(include_kw.keys())])

    # keywords aimed at NoteFilter
    # http://dev.evernote.com/documentation/reference/NoteStore.html#Struct_NoteFilter
    filter_kw_list = ('order', 'ascending', 'words', 'notebookGuid', 'tagGuids', 'timeZone', 'inactive', 'emphasized')
    filter_kw = dict([(k, input_kw[k]) for k in set(filter_kw_list) & set(input_kw.keys())])

    # what possible parameters are aimed at NoteFilter
    #order	i32		optional
    #ascending	bool		optional
    #words	string		optional
    #notebookGuid	Types.Guid		optional
    #tagGuids	list<Types.Guid>		optional
    #timeZone	string		optional
    #inactive   bool
    #emphasized string

    more_nm = True

    while more_nm:

        # grab a page of data
        note_meta = noteStore.findNotesMetadata(NoteFilter(**filter_kw), offset, page_size,
                                    NotesMetadataResultSpec(**include_kw))

        # yield each individually
        for nm in note_meta.notes:
            yield nm

        # grab next page if there is more to grab
        if len(note_meta.notes):
            offset += len(note_meta.notes)
        else:
            more_nm = False

def sizes_of_notes():
    """a generator for note sizes"""
    return (nm.contentLength for nm in notes_metadata(includeContentLength=True))

def notes(title=None):
    return notes_metadata(includeTitle=True,
                          includeUpdated=True,
                          includeUpdateSequenceNum=True,
                          words='intitle:"{0}"'.format(title))

def get_note(guid,
            withContent=False,
            withResourcesData=False,
            withResourcesRecognition=False,
            withResourcesAlternateData=False):

    # https://dev.evernote.com/doc/reference/NoteStore.html#Fn_NoteStore_getNote
    return noteStore.getNote(guid, withContent, withResourcesData,
                                 withResourcesRecognition, withResourcesAlternateData)


def create_note(title, content, tagNames=None, notebookGuid=None):

    # put the note into the :INBOX notebook by default
    inbox_nb_guid = notebook(name=':INBOX').guid

    note_template = u"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
    <en-note style="word-wrap: break-word; -webkit-nbsp-mode: space; -webkit-line-break: after-white-space;">
    {0}
    </en-note>"""

    note = Note()

    note.title = title.encode('utf-8')
    note.content = note_template.format(content).encode('utf-8')
    if tagNames is None:
        note.tagNames = []
    else:
        note.tagNames = tagNames

    if notebookGuid is None:
        note.notebookGuid = inbox_nb_guid
    else:
        note.notebookGuid = notebookGuid

    note = noteStore.createNote(note)
    return note


def update_note(note, title=None, content=None, tagNames=None, notebookGuid=None,
                    updated=None):
    
    """
    With the exception of the note's title and guid, fields that are not being changed 
    do not need to be set. If the content is not being modified, note.content should be 
    left unset. If the list of resources is not being modified, note.resources 
    should be left unset.
    """

    note_template = u"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
    <!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">
    <en-note style="word-wrap: break-word; -webkit-nbsp-mode: space; -webkit-line-break: after-white-space;">
    {0}
    </en-note>"""

    if title is not None:
        note.title = title.encode('utf-8')
    
    if content is not None:
        note.content = note_template.format(content).encode('utf-8')
        
    if tagNames is not None:
        note.tagNames = tagNames

    if notebookGuid is not None:
        note.notebookGuid = notebookGuid
        
    if updated is None:
        note.updated = arrow.utcnow().timestamp*1000

    note = noteStore.updateNote(note)
    return note


def set_notebook_for_note(note, notebook_name):
    """
    Place the given note in the notebook of name notebook_name
    """
    new_nb_guid = notebook(name=notebook_name).guid
    if note.notebookGuid != new_nb_guid:
        note.notebookGuid = new_nb_guid
        noteStore.updateNote(note)
    return note

def web_api_notes_from_selection():
    from appscript import app
    evnote = app('Evernote')
    return [get_note(sel_note.note_link().split("/")[-3]) for sel_note in evnote.selection()]

def all_actions():
    actions = list(islice(notes_metadata(includeTitle=True,
                                  includeUpdated=True,
                                  includeCreated=True,
                                  includeUpdateSequenceNum=True,
                                  includeTagGuids=True,
                                  notebookGuid=notebook(name='Action Pending').guid), None))
    return actions

def actions_to_df(actions):

    def j_(items):
        return ",".join(items)

    actions_data = []

    for note in actions:
        tags = [tag(guid=tagGuid).name for tagGuid in note.tagGuids] if note.tagGuids is not None else []
        plus_tags = [tag_ for tag_ in tags if tag_.startswith("+")]
        context_tags = [tag_ for tag_ in tags if tag_.startswith("@")]
        when_tags = [tag_ for tag_ in tags if tag_.startswith("#")]
        other_tags = [tag_ for tag_ in tags if tag_[0] not in ['+', '@', '#']]


        actions_data.append(dict([('title',note.title),
                                ('guid',note.guid),
                                ('created', datetime.datetime.fromtimestamp(note.created/1000.)),
                                ('updated', datetime.datetime.fromtimestamp(note.updated/1000.)),
                                ('plus', j_(plus_tags)),
                                ('context', j_(context_tags)),
                                ('when', j_(when_tags)),
                                ('other', j_(other_tags))
                                ])
        )

    actions_df = DataFrame(actions_data,
                  columns=['title','guid','created','updated','plus', 'context', 'when', 'other'])

    return actions_df

def actions_for_project(tag_name,
                        includeTitle=True,
                        includeUpdated=True,
                        includeUpdateSequenceNum=True,
                        includeTagGuids=True ):

    notes = notes_metadata(includeTitle=includeTitle,
                                  includeUpdated=includeUpdated,
                                  includeUpdateSequenceNum=includeUpdateSequenceNum,
                                  includeTagGuids=includeTagGuids,
                                  tagGuids = [tag(tag_name).guid],
                                  notebookGuid=notebook(name='Action Pending').guid)
    return notes

def strip_when_tags(note):
    """
    remove any tagGuids that are when tags from note
    """
    guids_new_tag_set = set(note.tagGuids) - _when_tags_guids
    note.tagGuids = list(guids_new_tag_set)
    noteStore.updateNote(note)
    return note

def strip_when_tags_move_to_ref_nb_for_selection():

    from appscript import app
    evnote = app('Evernote')

    notes = web_api_notes_from_selection()
    notes = [strip_when_tags(note) for note in notes]

    # move note to the :REFERENCE Notebook
    notes = [set_notebook_for_note(note, ":REFERENCE") for note in notes]

    evnote.synchronize()

def projects_to_df(notes):

    df = DataFrame([dict([('title',note.title),
                            ('guid',note.guid),
                            ('created', datetime.datetime.fromtimestamp(note.created/1000.)),
                            ('updated', datetime.datetime.fromtimestamp(note.updated/1000.))
                            ]) for note in notes],
              columns=['title','guid','created','updated'])

    return df

def project_notes_and_tags():
    """
    get all the notes in the :PROJECTS Notebook
    """

    notes = list(islice(notes_metadata(includeTitle=True,
                                  includeUpdated=True,
                                  includeCreated=True,
                                  includeUpdateSequenceNum=True,
                                  includeTagGuids=True,
                                  notebookGuid=notebook(name=':PROJECTS').guid), None))

    # accumulate all the tags that begin with "+" associated with notes in :PROJECTS notebook
    plus_tags_set = set()

    for note in notes:
        tags = [tag(guid=tagGuid).name for tagGuid in note.tagGuids] if note.tagGuids is not None else []
        plus_tags = [tag_ for tag_ in tags if tag_.startswith("+")]

        plus_tags_set.update(plus_tags)

    return (notes, plus_tags_set)

def project_tags_for_selected():

    project_tags = set()

    for note in web_api_notes_from_selection():
        project_tags |= set(filter(lambda s: s.startswith("+"), [tag(guid=g).name for g in note.tagGuids]))

    return project_tags

def non_project_plus_tags():

    all_plus_tags = set(filter(lambda tag_: tag_.startswith("+"),
                       [tag_.name for tag_ in all_tags(refresh=False)]))

    projects_notes = list(islice(notes_metadata(includeTitle=True,
                                  includeUpdated=True,
                                  includeUpdateSequenceNum=True,
                                  notebookGuid=notebook(name=':PROJECTS').guid), None))

    project_plus_tags = set()
    for note in projects_notes:
        tags = noteStore.getNoteTagNames(note.guid)
        plus_tags = [tag_ for tag_ in tags if tag_.startswith("+")]
        project_plus_tags.update(plus_tags)


    return (all_plus_tags - project_plus_tags)

def generate_project_starter_notes():

    projects_nb_guid = notebook(name=':PROJECTS').guid

    notes = []

    for tag_name in non_project_plus_tags():
        proj_name = tag_name[1:]
        note = create_note(proj_name, " ", tagNames=[tag_name],
                               notebookGuid=projects_nb_guid)
        notes.append(note)

    return notes

def fix_wayward_plus_tags():

    active_projects_tag = tag(name=".Active Projects")
    inactive_projects_tag = tag(name=".Inactive Projects")

    wayward_plus_tags = [tag_ for tag_ in all_tags(refresh=True) if tag_.name.startswith("+") and tag_.parentGuid != active_projects_tag.guid]
    for tag_ in wayward_plus_tags:
        tag_.parentGuid = active_projects_tag.guid
        noteStore.updateTag(tag_)

    return [tag_.name for tag_ in wayward_plus_tags]

def action_note_tags():

    when_tags = [tag_ for tag_ in all_tags(refresh=True) if tag_.parentGuid == tag(name=".When").guid]
    when_tags_guids = set([tag_.guid for tag_ in when_tags])

    note_tags_dict = defaultdict(list)

    action_notes = list(islice(notes_metadata(includeTitle=True,
                                      includeUpdated=True,
                                      includeUpdateSequenceNum=True,
                                      includeTagGuids=True,
                                      notebookGuid=notebook(name='Action Pending').guid), None))

    # tags that have no .When tags whatsover
    # ideally -- each action has one and only one .When tag

    for note in action_notes:
        tag_guids = note.tagGuids

        if tag_guids is None:
            tag_guids = []

        tag_names = [tag(guid=g).name for g in tag_guids]
        for tag_name in tag_names:
            note_tags_dict[tag_name].append(note)

        if len(tag_guids) == 0:
            note_tags_dict['__UNTAGGED__'].append(note)


    return note_tags_dict

def retire_project(tag_name,
    ignore_actions=False,
    dry_run=False,
    display_remaining_actions=True):
    """
    Retire the project represented by tag_name
    """
    tag_ = tag(name=tag_name)

    # make sure tag_name starts with "+"
    if not tag_name.startswith("+"):
        return tag_

    # if ignore_actions is False, check whether are still associated actions for the project.
    # if there are actions, then don't retire project.  Optionally display actions in Evernote
    if not ignore_actions:
        associated_actions = list(actions_for_project(tag_name))
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

    if tag(retired_tag_name) is None:
        tag_.name = retired_tag_name
    else:
        raise Exception("{0} already exists".format(retired_tag_name))

    # change parent reference
    tag_.parentGuid = tag('.Inactive Projects').guid

    # move the project note (if it exists) from the project notebook to the retired project notebook

    project_notes = notes_metadata(includeTitle=True, includeNotebookGuid=True,
                            tagGuids = [tag_.guid],
                            notebookGuid=notebook(name=':PROJECTS').guid)

    # with NoteMetadata, how to make change to the corresponding note?
    # make use of
    # http://dev.evernote.com/doc/reference/NoteStore.html#Fn_NoteStore_updateNote

    for note in project_notes:
        note.notebookGuid = notebook(name=":PROJECTS--RETIRED").guid
        noteStore.updateNote(note)

    # deal with the associated actions for the project

    # apply changes to tag
    noteStore.updateTag(tag_)

    return tag_
