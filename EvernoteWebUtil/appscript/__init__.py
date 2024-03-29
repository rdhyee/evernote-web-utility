from appscript import app, k
import applescript
import datetime
import json

__all__ = ["EvernoteASWrapper", "EvernoteGTDWrapper"]

ascript = """
on evernote_tag_exists(tag_name)
    tell application "Evernote Legacy"
        return (tag named tag_name exists)
    end tell
end evernote_tag_exists

on assign_note_tag(note_link, tag_name)
    tell application "Evernote Legacy"
        set note_ to find note note_link
        assign tag tag_name to note_
        set modification date of note_ to current date
    end tell

    return note_
end assign_note_tag

on unassign_note_tag(note_link, tag_name)
    tell application "Evernote Legacy"
        set note_ to find note note_link
        unassign tag tag_name from note_
        set modification date of note_ to current date
    end tell

    return note_
end unassign_note_tag

on touch_mod_date(note_link)
   tell application "Evernote Legacy"
        set note_ to find note note_link
        set modification date of note_ to current date
    end tell

    return note_
end touch_mod_date

on assign_tag_parent(tag_name, parent_tag_name)
    tell application "Evernote Legacy"
        set tag_ to tag tag_name
        set tag_'s parent to tag parent_tag_name
    end tell
    return tag_
end assign_tag_parent

on rename_tag(from_name, to_name)
    tell application "Evernote Legacy"
        set tag_ to tag from_name
        set name of tag_ to to_name
    end tell
end rename_tag

on every_tag()
    tell application "Evernote Legacy"
        set results to name of every tag
        return results
    end tell
end every_tag

on every_tag_with_parent()
    tell application "Evernote Legacy"
        set results to {}
        repeat with tag_ in every tag
            try
                set pname to name of parent of tag_
            on error errMsg
                set pname to ""
            end try
            set end of results to {tname:name of tag_, pname:pname}
        end repeat
        return results
    end tell
end every_tag_with_parent
"""


def project_info(note):
    """
    for a given note, pull out:

    * is it the project note (or a note not in the project folder,
    but associated with a project)
    * associated actions
    * associated non-action notes
    """

    notebook_name = note.notebook().name()
    plus_tags = [tag.name() for tag in note.tags() if tag.name().startswith("+")]

    return {
        "title": note.title(),
        "note_link": note.note_link(),
        "created": note.creation_date(),
        "modified": note.modification_date(),
        "notebook_name": notebook_name,
        "is_project_note": notebook_name == ":PROJECTS",
        "plus_tags": plus_tags,
    }


def monday_of_week(date_):
    return date_ - datetime.timedelta(days=date_.weekday())


class EvernoteASWrapper(object):
    def __init__(self, app_name="Evernote Legacy"):
        # app_name used to be "Evernote"
        self.evnote = app(app_name)
        self.scpt = applescript.AppleScript(ascript)

    def app_info(self):
        return [
            (
                account.name(),
                account.account_type(),
                account.upload_limit(),
                account.upload_reset_date(),
                account.upload_used(),
            )
            for account in self.evnote.accounts()
        ]

    def __notebook_exists(self, name):
        return self.evnote.notebooks[name].exists()

    def notebooks(self):
        return [
            (notebook.name(), notebook.notebook_type(), notebook.default())
            for notebook in self.evnote.notebooks()
        ]

    def make_notebook(self, name):
        return self.evnote.make(new=k.notebook, with_properties={k.name: name})

    def rename_notebook(self, oldname, newname):
        return self.evnote.notebooks[oldname].name.set(newname)

    def delete_notebook(self, name):
        return self.evnote.notebooks[name].delete()

    def notes_for_notebook(self, name):
        return [
            (
                note.title(),
                note.creation_date(),
                note.modification_date(),
                note.subject_date(),
                note.source_URL(),
                note.latitude(),
                note.longitude(),
                note.altitude(),
                note.ENML_content(),
                note.HTML_content(),
                note.tags(),
            )
            for note in self.evnote.notebooks[name].notes()
        ]

    def create_text_note(self, notebook_name, title, text):
        return self.evnote.create_note(
            with_text=text, title=title, notebook=app.notebooks[notebook_name]
        )

    def create_html_note(self, notebook_name, title, html):
        return self.evnote.create_note(
            with_html=html, title=title, notebook=app.notebooks[notebook_name]
        )

    def create_url_note(self, notebook_name, title, url):
        return self.evnote.create_note(
            notebook=app.notebooks[notebook_name], title=title, from_url=url
        )

    def create_file_note(self, notebook_name, title, fname):
        return self.evnote.create_note(
            notebook=app.notebooks[notebook_name], from_file=fname, title=title
        )

    def create_enml_note(self, notebook_name, title, enml):
        return self.evnote.create_note(
            with_enml=enml, title=title, notebook=app.notebooks[notebook_name]
        )

    def synchronize(self):
        return self.evnote.synchronize()

    def evernote_tag_exists(self, tag_name):
        return self.scpt.call("evernote_tag_exists", tag_name)

    def assign_note_tag(self, note_link, tag_name):
        return self.scpt.call("assign_note_tag", note_link, tag_name)

    def unassign_note_tag(self, note_link, tag_name):
        return self.scpt.call("unassign_note_tag", note_link, tag_name)

    def touch_mod_date(self, note_link):
        return self.scpt.call("touch_mod_date", note_link)

    def assign_tag_parent(self, tag_name, parent_tag_name):
        return self.scpt.call("assign_tag_parent", tag_name, parent_tag_name)

    def rename_tag(self, from_name, to_name):
        return self.scpt.call("rename_tag", from_name, to_name)

    def display_notes(self, notes):
        for note in notes:
            print(note.title())

    def get_or_create_note(self, title, tag=None, notebook_name=":INBOX", text=" "):

        q_tag = " tag:{} ".format(json.dumps(tag)) if tag is not None else ""

        q = "intitle:{} notebook:{} {}".format(
            json.dumps(title), json.dumps(notebook_name), q_tag
        )

        results = self.evnote.find_notes(q)
        if len(results) == 1:
            return results[0]
        elif len(results) > 1:
            raise Exception("Note title/tag/notebook is not unique")
        else:
            note_ = self.create_text_note(notebook_name, title, text)
            if tag is not None:
                self.assign_note_tag(note_.note_link(), tag)
            return note_

    def every_tag(self):
        return self.scpt.call("every_tag")

    def every_tag_with_parent(self):
        return self.scpt.call("every_tag_with_parent")


when_tags = [
    "#0-Daily",
    "#1-Now",
    "#2-Next",
    "#3-Soon",
    "#4-Later",
    "#5-Someday",
    "#6-Waiting",
    "#7-Never",
]


class EvernoteGTDWrapper(EvernoteASWrapper):
    def retire_action(self, notes, destination="Completed"):
        for note in notes:
            self.evnote.move(note, to=self.evnote.notebooks[destination])
            for tag in note.tags():
                if tag.name() in when_tags:
                    self.unassign_note_tag(note.note_link(), tag.name())

    def retire_project(self, tag_name):

        # look for the project note corresponding to tag_name
        # there should be one and only one such note

        q = """notebook::PROJECTS tag:"{}" """.format(tag_name)
        results = self.evnote.find_notes(q)

        if len(results) == 1:
            project_note = self.evnote.find_notes(q)[0]

            # move the project note to :PROJECTS--RETIRED notebook
            self.evnote.move(
                project_note, to=self.evnote.notebooks[":PROJECTS--RETIRED"]
            )

            # retire the actions for the project
            q = """notebook:"Action Pending" tag:"{}" """.format(tag_name)
            results = self.evnote.find_notes(q)
            self.retire_action(results)

            # now rename project tag
            neg_tag = tag_name.replace("+", "-", 1)
            self.rename_tag(tag_name, neg_tag)

            # move the tag to be a child of inactive projects
            self.assign_tag_parent(neg_tag, ".Inactive Projects")

    def retire_selection(self, destination="Completed"):
        """
        if a selected note is a project one, retire it and associated actions
        otherwise, just retire action note
        """

        sel = self.evnote.selection()

        for note in sel:
            note_info = project_info(note)

            # check to see whether a given selected note is a project note.
            if note_info["is_project_note"]:
                plus_tag = note_info["plus_tags"][0]
                self.retire_project(plus_tag)
            elif note_info["notebook_name"] == "Action Pending":
                self.retire_action([note], destination=destination)

    def put_into_maybe(self, notes):
        for note in notes:
            # move to Action Pending
            self.evnote.move(note, to=self.evnote.notebooks["Action Pending"])
            # strip when tags
            for tag in note.tags():
                if tag.name() in when_tags:
                    self.unassign_note_tag(note.note_link(), tag.name())
            # assign someday
            ev.assign_note_tag(note.note_link(), "#5-Someday")

    def mark_reminder_done(self, notes):
        for note in notes:
            if note.reminder_order() != k.missing_value:
                now = datetime.datetime.utcnow()
                note.reminder_done_time.set(now)

    def create_review_planning_notes(self, date_=None):
        if date_ is None:
            date_ = datetime.date.today()

        # calculate the Monday of last week
        this_monday = monday_of_week(date_)
        last_monday = this_monday - datetime.timedelta(days=7)

        weekly_plan_title = "Weekly Plan {}".format(this_monday.strftime("%Y.%m.%d"))
        weekly_review_title = "Weekly Review {}".format(
            last_monday.strftime("%Y.%m.%d")
        )

        return (
            self.get_or_create_note(weekly_plan_title, "Weekly Plan", "Planning", " "),
            self.get_or_create_note(
                weekly_review_title, "Weekly Review", "Review", " "
            ),
        )

    def active_projects(self, sort_key="modified", reverse=True):
        name = ":PROJECTS"

        projects_info = []

        for note in self.evnote.notebooks[name].notes():
            projects_info.append(project_info(note))

        # print them out by reverse last-modified

        for proj in sorted(projects_info, key=lambda p: p[sort_key], reverse=reverse):
            yield (proj)

    def generate_project_starter_notes(self):

        projects_tags = set([p["plus_tags"][0] for p in self.active_projects()])

        every_tag = self.every_tag_with_parent()
        plus_tags = set(
            [tag_["tname"] for tag_ in every_tag if tag_["tname"].startswith("+")]
        )
        notes = []

        for tag_name in plus_tags - projects_tags:
            proj_name = tag_name[1:]
            note = self.get_or_create_note(
                proj_name, tag=tag_name, notebook_name=":PROJECTS", text=" "
            )
            # move the tag to be a child of active projects
            self.assign_tag_parent(tag_name, ".Active Projects")

            notes.append(note)

        return notes
