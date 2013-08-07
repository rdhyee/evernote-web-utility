__all__ = ["client", "userStore",  "user", "noteStore", "all_notebooks", "notes_metadata", "sizes_of_notes"]

# https://github.com/evernote/evernote-sdk-python/blob/master/sample/client/EDAMTest.py

import settings
from evernote.api.client import EvernoteClient

from evernote.edam.notestore.ttypes import NoteFilter
from evernote.edam.notestore.ttypes import NotesMetadataResultSpec

dev_token = settings.authToken

client = EvernoteClient(token=dev_token, sandbox=False)

userStore = client.get_user_store()
noteStore = client.get_note_store()

user = userStore.getUser()

def all_notebooks():
    # List all of the notebooks in the user's account     
    notebooks = noteStore.listNotebooks()
    return notebooks

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
