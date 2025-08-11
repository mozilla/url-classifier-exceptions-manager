import os
import sys
import json
import subprocess
import re
import argparse

from GlobalExceptions import GlobalExceptions
from RemoteSettingsEntry import RemoteSettingsEntry


def main():
    parser = argparse.ArgumentParser(description='Process annotated bugs and generate remote settings')
    parser.add_argument('bugs_file', help='Bugzilla Cache File (JSON)')
    parser.add_argument('exceptions_file', help='File containing current global exceptions')
    args = parser.parse_args()

    with open(args.bugs_file, "r") as fd:
        data = json.load(fd)

    global_exceptions = GlobalExceptions(args.exceptions_file)

    ok_cnt=0

    affected_bugs = []
    remote_settings = []

    for entry in sorted(data["bugs"], key=lambda x: x["id"], reverse=True):
        bug_id = entry["id"]
        url = entry["url"]
        comments = entry["comments"]

        whiteboard = entry["whiteboard"]
        user_story = entry["cf_user_story"]

        if "[privacy-team:diagnosed]" not in whiteboard:
            continue

        if entry["severity"] == "S4" or entry["severity"] == "S3":
            continue

        url = entry["url"]
        if not url or not url.startswith("http"):
            print(f"Warning: Ignoring Bug {bug_id}, bad URL? {url}")
            continue

        category = "convenience"
        if "[exception-baseline]" in whiteboard:
            category = "baseline"
        elif "[exception-convenience]" in whiteboard:
            category = "convenience"

        for (idx,line) in enumerate(user_story.splitlines()):
            if line.startswith("trackers-blocked:"):
                (_, hosts) = line.split(":", 2)
                necessary_fix_domains = global_exceptions.filter_global_exceptions(hosts)

                if not necessary_fix_domains:
                    print(f"Warning: Ignoring Bug {bug_id}, covered by global exceptions?")
                    continue

                print(f"Bug {bug_id}: {necessary_fix_domains}")


                if not category:
                    print(f"Warning: Ignoring Bug {bug_id}, no category found")
                else:
                    affected_bugs.append(bug_id)
                    for fix_domain in necessary_fix_domains:
                        remote_settings.append(RemoteSettingsEntry(
                            bug_id, fix_domain, url, False, category,
                            "", 'env.version|versionCompare("142.0a1") >= 0').toObject())
                        remote_settings.append(RemoteSettingsEntry(
                            bug_id, fix_domain, url, True, "convenience",
                            "standard", 'env.version|versionCompare("142.0a1") < 0').toObject())

    print(affected_bugs)
    print(json.dumps(remote_settings, indent=2))

if __name__ == "__main__":
    main()
