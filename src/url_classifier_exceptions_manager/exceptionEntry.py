import json

class ExceptionEntry():
    def __init__(self):
        self.obj = {}

    def fromRSRecord(self, record):
        bugIds = []
        if "bugIds" in record:
            bugIds = record["bugIds"]
        elif "bugId" in record:
            bugIds = [record["bugId"]]

        # Set the values from the required fields of the record
        self.obj["bugIds"] = bugIds
        self.obj["id"] = record["id"]
        self.obj["urlPattern"] = record["urlPattern"]
        self.obj["classifierFeatures"] = record["classifierFeatures"]
        self.obj["category"] = record["category"]

        # Add optional fields only if they exist in the source record
        if "topLevelUrlPattern" in record:
            self.obj["topLevelUrlPattern"] = record["topLevelUrlPattern"]

        if "isPrivateBrowsingOnly" in record:
            self.obj["isPrivateBrowsingOnly"] = record["isPrivateBrowsingOnly"]

        if "filterContentBlockingCategories" in record:
            self.obj["filterContentBlockingCategories"] = record["filterContentBlockingCategories"]

        if "filter_expression" in record:
            self.obj["filter_expression"] = record["filter_expression"]

    def fromArguments(self, bugIds, urlPattern, classifierFeatures,
                      category = "convenience", topLevelUrlPattern=None,
                      isPrivateBrowsingOnly=None,
                      filterContentBlockingCategories=None,
                      filter_expression=None):
        # Set the necessary fields
        self.obj["bugIds"] = bugIds
        self.obj["urlPattern"] = urlPattern
        self.obj["classifierFeatures"] = classifierFeatures
        self.obj["category"] = category

        # Add optional fields only if they are not None
        if topLevelUrlPattern is not None:
            self.obj["topLevelUrlPattern"] = topLevelUrlPattern
        if isPrivateBrowsingOnly is not None:
            self.obj["isPrivateBrowsingOnly"] = isPrivateBrowsingOnly
        if filterContentBlockingCategories is not None:
            self.obj["filterContentBlockingCategories"] = filterContentBlockingCategories
        if filter_expression is not None:
            self.obj["filter_expression"] = filter_expression

    def toJSON(self):
        return json.dumps(self.obj, indent=2)

    def toObject(self):
        return self.obj

    def isGlobalException(self):
        return "topLevelUrlPattern" not in self.obj

    def isEntryAfter142(self):
        return "filter_expression" in self.obj and self.obj["filter_expression"] == 'env.version|versionCompare("142.0a1") >= 0'

    def isBlockingEntry(self):
        for feature in self.obj["classifierFeatures"]:
            if feature.endswith("-protection"):
                return True
        return False