import re

class BugWhiteboard():
    def __init__(self, wb, user_story=None):
        reg = r"\[fxwebdiff:([^]]*)\]"
        match = re.search(reg, wb)

        if match:
            self.other_wb = wb[:match.span(0)[0]] + wb[match.span(0)[1]:]
            (self.status, self.diagnosis, self.error, self.module) = match.group(1).split(":")
        else:
            self.other_wb = wb
            (self.status, self.diagnosis, self.error, self.module) = ("","","","")

        self.updated = False

        self.user_story = []
        self.user_story_idx = None
        self.user_story_trackers_idx = None
        self.user_story_metadata = None
        self.user_story_trackers_metadata = None
        self.user_story_updated = False

        if user_story:
            self.user_story = user_story.splitlines()

            for (idx,line) in enumerate(self.user_story):
                if line.startswith("fxwebdiff:"):
                    self.user_story_idx = idx
                    (_, self.user_story_metadata) = line.split(":", 1)
                elif line.startswith("trackers-"):
                    self.user_story_trackers_idx = idx
                    (_, self.user_story_trackers_metadata) = line.split(":", 1)

    def update_fields(self, status="", diagnosis="", error="", module="", user_story_metadata=None, user_story_trackers_metadata=None):
        if self.status != status:
            self.status = status
            self.updated=True

        if self.diagnosis != diagnosis:
            self.diagnosis = diagnosis
            self.updated=True

        if self.error != error:
            self.error = error
            self.updated=True

        if self.module != module:
            self.module = module
            self.updated=True

        if self.user_story_metadata != user_story_metadata:
            self.user_story_metadata = user_story_metadata
            self.user_story_updated = True

        if self.user_story_trackers_metadata != user_story_trackers_metadata:
            self.user_story_trackers_metadata = user_story_trackers_metadata
            self.user_story_updated = True


        self.collapse()

    def collapse(self):
        return f"{self.other_wb}[fxwebdiff:{':'.join((self.status, self.diagnosis, self.error, self.module))}]"

    def collapse_user_story(self):
        if self.user_story_metadata is not None:
            user_story_str = f"fxwebdiff:{self.user_story_metadata}"

            if self.user_story_idx is not None:
                self.user_story[self.user_story_idx] = user_story_str
            else:
                self.user_story.append(user_story_str)

        if self.user_story_trackers_metadata is not None:
            user_story_trackers_str = f"trackers-blocked:{self.user_story_trackers_metadata}"

            if self.user_story_trackers_idx is not None:
                self.user_story[self.user_story_trackers_idx] = user_story_trackers_str
            else:
                self.user_story.append(user_story_trackers_str)

        return "\n".join(self.user_story)
