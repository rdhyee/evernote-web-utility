"""
Wrapper for the Evernote Python SDK
"""

__all__ = ["client", "userStore",  "user", "noteStore", "all_notebooks", "notes_metadata", "sizes_of_notes",
           "all_tags", "tag", "tag_counts_by_name", "tags_by_guid"]

# https://github.com/evernote/evernote-sdk-python/blob/master/sample/client/EDAMTest.py

from time import sleep

import settings
from evernote.api.client import EvernoteClient

from evernote.edam.notestore.ttypes import (NoteFilter,
                                            NotesMetadataResultSpec,
                                           )

from evernote.edam.error.ttypes import (EDAMSystemException, EDAMErrorCode)

dev_token = settings.authToken


_client = EvernoteClient(token=dev_token, sandbox=False)

# first efforts at implementing strategy for handling rate limiting
# http://dev.evernote.com/doc/articles/rate_limits.php

def evernote_wait_try_again(f):
    """
    Wait until mandated wait and try again
    """
    
    def f2(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except EDAMSystemException, e:
            if e.errorCode == EDAMErrorCode.RATE_LIMIT_REACHED:
                sleep(e.rateLimitDuration)
                return f(*args, **kwargs)
    
    return f2


class RateLimitingEvernoteProxy(object):
    # based on http://code.activestate.com/recipes/496741-object-proxying/
    __slots__ = ["_obj"]
    def __init__(self, obj):
        object.__setattr__(self, "_obj", obj)
    
    def __getattribute__(self, name):
        return evernote_wait_try_again(getattr(object.__getattribute__(self, "_obj"), name))


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