from bugsy import Bugsy
import sys
import json
import os
import time

bugsy = Bugsy()

def get_bugs():

  params = {
    "product": "Web Compatibility",
    "component": "Privacy: Site Reports",
    "resolution": "---",
    "query_format": "advanced",
    "include_fields": "id,last_change_time,summary,platform,url,whiteboard,status,resolution,severity,priority,cf_user_story,comments",
  }

  return bugsy.request("bug", params=params)

cache = get_bugs()
with open("bz-cache.json", 'w') as fd:
    json.dump(fp=fd, obj=cache)
