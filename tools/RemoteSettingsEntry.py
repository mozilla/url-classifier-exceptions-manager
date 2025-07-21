import json

from urllib.parse import urlparse

class RemoteSettingsEntry():
    def __init__(self, bug_id, tracker_domain, url=None, pbm_only=True):
        self.obj = {}

        self.obj["bugId"] = str(bug_id)
        self.obj["urlPattern"] = f"*://{tracker_domain}/*"
        self.obj["classifierFeatures"] = [ "tracking-protection", "emailtracking-protection" ]

        if url is not None:
            url = urlparse(url)
            self.obj["topLevelUrlPattern"] = f"*://{url.netloc}/*"

        self.obj["isPrivateBrowsingOnly"] = pbm_only
        self.obj["filterContentBlockingCategories"] = [ "standard" ]


    def toJSON(self):
        return json.dumps(self.obj, indent=2)

    def toObject(self):
        return self.obj

