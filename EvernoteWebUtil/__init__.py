"""
Wrapper for the Evernote Python SDK
"""

__all__ = ["client", "userStore",  "user", "noteStore", "all_notebooks", "notes_metadata", "sizes_of_notes",
           "all_tags", "tag", "tag_counts_by_name", "tags_by_guid", "init"]

import logging
logger = logging.getLogger(__name__)

# https://github.com/evernote/evernote-sdk-python/blob/master/sample/client/EDAMTest.py

from time import sleep

from evernote.api.client import EvernoteClient
from evernote.edam.type.ttypes import Note
from evernote.edam.notestore.ttypes import (NoteFilter,
                                            NotesMetadataResultSpec
                                           )
from evernote.edam.error.ttypes import (EDAMSystemException, EDAMErrorCode)


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

def update_note(note, title=None, content=None, tagNames=None, notebookGuid=None):
    
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

def project_tags_for_selected():

    project_tags = set()

    for note in web_api_notes_from_selection():
        project_tags |= set(filter(lambda s: s.startswith("+"), [tag(guid=g).name for g in note.tagGuids]))

    return project_tags
