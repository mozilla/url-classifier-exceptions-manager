from bugsy import Bugsy
import sys
import os

def fetch_bug_data(product, component):
    bugsy = Bugsy()

    params = {
        "product": product,
        "component": component,
        "resolution": "---",
        "query_format": "advanced",
        "include_fields": "id,last_change_time,summary,platform,url,whiteboard,status,resolution,severity,priority,cf_user_story,comments",
    }

    return bugsy.request("bug", params=params)

def fetch_bug_creator(bugId):
    bugsy = Bugsy()

    params = {
        "include_fields": "creator",
    }

    data = bugsy.request(f"bug/{bugId}", params=params)

    if "bugs" in data:
        return data["bugs"][0]["creator"]
    else:
        return None

def close_bug(bugId, resolution, message):
    api_key = os.getenv("BZ_API_KEY")
    bugsy = Bugsy(api_key=api_key)

    json_data = {
        "status": "RESOLVED",
        "resolution": resolution,
        "comment": {"body": message}
    }

    try:
        bugsy.request(
            f"bug/{bugId}", 'PUT',
            json=json_data
        )
        print(f"Bug {bugId} closed successfully")
    except Exception as e:
        print(f"Error closing bug {bugId}: {e}", file=sys.stderr)

def needInfo(bugId, message, requestee):
    api_key = os.getenv("BZ_API_KEY")
    bugsy = Bugsy(api_key=api_key)

    json_data = {
       "flags": [
           {
               "name": "needinfo",
               "status": "?",
               "requestee": requestee,
           }
       ],
       "comment": {"body": message}
    }

    try:
        bugsy.request(
            f"bug/{bugId}", 'PUT',
            json=json_data
        )
        print(f"NeedInfo {requestee} for Bug {bugId} successfully")
    except Exception as e:
        print(f"Error needInfo {requestee} for bug {bugId}: {e}", file=sys.stderr)

