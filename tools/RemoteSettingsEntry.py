import json

from urllib.parse import urlparse

class RemoteSettingsEntry():
    def __init__(self, bug_id, tracker_domain, url=None, pbm_only=True, category="convenience", filterContentBlockingCategories = "", filter_expression=None):
        self.obj = {}

        self.obj["bugIds"] = [str(bug_id)]
        self.obj["urlPattern"] = f"*://{tracker_domain}/*"
        self.obj["classifierFeatures"] = [ "tracking-protection", "emailtracking-protection" ]

        if url is not None:
            url = urlparse(url)
            self.obj["topLevelUrlPattern"] = f"*://{url.netloc}/*"

        if pbm_only:
            self.obj["isPrivateBrowsingOnly"] = pbm_only

        self.obj["filterContentBlockingCategories"] = filterContentBlockingCategories
        self.obj["category"] = category

        if filter_expression is not None:
            self.obj["filter_expression"] = filter_expression


    def toJSON(self):
        return json.dumps(self.obj, indent=2)

    def toObject(self):
        return self.obj

