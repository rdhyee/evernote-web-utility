from appscript import app, k
import applescript

__all__ = ['EvernoteASWrapper']

ascript = """
on evernote_tag_exists(tag_name)
    tell application "Evernote"
        return (tag named tag_name exists)
    end tell
end evernote_tag_exists

on assign_note_tag(note_link, tag_name)
    tell application "Evernote"
        set note_ to find note note_link
        assign tag tag_name to note_
        set modification date of note_ to current date
    end tell
    
    return note_
end assign_note_tag

on unassign_note_tag(note_link, tag_name)
    tell application "Evernote"
        set note_ to find note note_link
        unassign tag tag_name from note_
        set modification date of note_ to current date
    end tell
    
    return note_
end unassign_note_tag

on touch_mod_date(note_link)

   tell application "Evernote"
        set note_ to find note note_link
        set modification date of note_ to current date
    end tell

    return note_

end touch_mod_date
"""



class EvernoteASWrapper(object):
    def __init__(self):
        self.evnote = app('Evernote')
        self.scpt = applescript.AppleScript(ascript)
    def app_info(self):
        return [(account.name(), account.account_type(), account.upload_limit(), account.upload_reset_date(),
                 account.upload_used()) for account in self.evnote.accounts()]
    def __notebook_exists(self,name):
        return self.evnote.notebooks[name].exists()
    def notebooks(self):
        return [(notebook.name(), notebook.notebook_type(), notebook.default()) for notebook in self.evnote.notebooks()]
    def make_notebook(self,name):
        return self.evnote.make(new=k.notebook, with_properties={k.name: name})
    def rename_notebook(self,oldname,newname):
        return self.evnote.notebooks[oldname].name.set(newname)
    def delete_notebook(self,name):
        return self.evnote.notebooks[name].delete()
    def notes_for_notebook(self, name):
        return [(note.title(), note.creation_date(), note.modification_date(), note.subject_date(), note.source_URL(),
                 note.latitude(), note.longitude(), note.altitude(), note.ENML_content(), note.HTML_content(),
                 note.tags()) for note in self.evnote.notebooks[name].notes()]
    def create_text_note(self, notebook_name, title, text):
        return self.evnote.create_note(with_text=text, title=title, notebook=app.notebooks[notebook_name])
    def create_html_note(self, notebook_name, title, html):
        self.evnote.create_note(with_html=html, title=title, notebook=app.notebooks[notebook_name])
    def create_url_note(self,notebook_name, title, url):
        self.evnote.create_note(notebook=app.notebooks[notebook_name], title=title, from_url=url)
    def create_file_note(self,notebook_name,title,fname):
        self.evnote.create_note(notebook=app.notebooks[u":INBOX"], 
                                from_file=u'//Users/raymondyee/Music/iTunes/iTunes Music/Simone Dinnerstein/Bach_ Goldberg Variations/01 Bach_ Goldberg Variations, BWV 988 - Aria.mp3', title=u'Note 4')
    def synchronize(self):
        return self.evnote.synchronize()
    def evernote_tag_exists(self, tag_name):
        return self.scpt.call('evernote_tag_exists', tag_name)
    def assign_note_tag(self, note_link, tag_name):
        return self.scpt.call('assign_note_tag', note_link, tag_name)
    def unassign_note_tag(self, note_link, tag_name):
        return self.scpt.call('unassign_note_tag', note_link, tag_name)
    def touch_mod_date(self, note_link):
        return self.scpt.call('touch_mod_date', note_link)
    