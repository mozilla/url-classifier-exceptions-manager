import json

from urllib.parse import urlparse

from .bugzilla import (
    fetch_bug_data,
    close_bug,
    needInfo,
    fetch_bug_creator,
    fetch_bug
)
from .remoteSettings import (
    list_exceptions,
    add_exceptions,
    remove_exceptions,
    request_review_exceptions,
    get_deployed_records
)
from .exceptionEntry import ExceptionEntry

from .constants import (
    PROD_SERVER_LOCATION,
)

def is_exempted_by_global_exceptions(host, exceptions):
    for e in exceptions:
        if e.isGlobalException() is False:
            continue

        if e.isBlockingEntry() is False:
            continue

        if e.obj["urlPattern"] == f"*://{host}/*":
            print(f"Warning: {host} is exempted by global exception {e.obj}")
            return True

    return False

def is_already_in_exception(entries, exceptions):
    """
    Check whether all given entries already exist in the given exceptions.

    entries: list of ExceptionEntry objects to check.
    exceptions: list of existing ExceptionEntry objects.
    """
    existing_signatures = {exc.entry_signature() for exc in exceptions}
    for entry in entries:
        if entry.entry_signature() not in existing_signatures:
            return False
    return True

def find_entries_by_bug_id(bug_id, exceptions):
    """
    Find entries whose bugIds list contains only the given bug ID.
    """
    entries = []
    for exception in exceptions:
        bug_ids = exception.obj.get("bugIds", [])
        if len(bug_ids) == 1 and str(bug_id) == str(bug_ids[0]):
            entries.append(exception)
    return entries


async def auto_deploy_exceptions(server_location, auth_token, is_prod_server, dry_run=False, force=False):

    print(f"Executing auto deploy exceptions for server {server_location} with is_prod_server {is_prod_server} and dry_run {dry_run} and force {force}")

    bugs_data = fetch_bug_data("Web Compatibility", "Privacy: Site Reports")
    rs_records = await list_exceptions(server_location, auth_token)
    deployed_records = await get_deployed_records("prod" if is_prod_server else "stage")

    # Create a list of ExceptionEntry objects from the RemoteSettings records
    current_exceptions = []
    for record in rs_records:
        entry = ExceptionEntry()
        entry.fromRSRecord(record)
        current_exceptions.append(entry)

    deployed_exceptions = []
    for record in deployed_records:
        entry = ExceptionEntry()
        entry.fromRSRecord(record)
        deployed_exceptions.append(entry)

    bugs_need_exception = []
    bugs_have_exception = []
    new_exceptions = []

    for entry in sorted(bugs_data["bugs"], key=lambda x: x["id"], reverse=True):
        bug_id = entry["id"]
        url = entry["url"]
        whiteboard = entry["whiteboard"]
        user_story = entry["cf_user_story"]

        # Skip if the bug is not diagnosed by the privacy team
        if "[privacy-team:diagnosed]" not in whiteboard:
            continue

        # Skip if the category hasn't been set.
        if "[exception-baseline]" not in whiteboard and "[exception-convenience]" not in whiteboard:
            continue

        url = entry["url"]
        if not url or not url.startswith("http"):
            print(f"Warning: Ignoring Bug {bug_id}, bad URL? {url}")
            continue

        url = f"*://{urlparse(url).netloc}/*"

        # Get the category from the whiteboard tag
        category = "convenience"
        if "[exception-baseline]" in whiteboard:
            category = "baseline"
        elif "[exception-convenience]" in whiteboard:
            category = "convenience"

        classifierFeatures = ["tracking-protection", "emailtracking-protection"]
        domains_to_fix = []

        # Parse the user story to find the necessary fix domains and classifier
        # features
        for (idx,line) in enumerate(user_story.splitlines()):
            if line.startswith("trackers-blocked:"):
                (_, hosts) = line.split(":", 2)
                domains_to_fix = hosts.split(",")

                # Filter out domains that are exempted by global exceptions
                domains_to_fix = [host for host in domains_to_fix if not is_exempted_by_global_exceptions(host, current_exceptions)]

                if not domains_to_fix:
                    print(f"Warning: Ignoring Bug {bug_id}, covered by global exceptions?")
                    continue

                domains_to_fix = [f"*://{domain.strip()}/*" for domain in domains_to_fix]

            if line.startswith("classifier-features:"):
                (_, features) = line.split(":", 2)
                classifierFeatures = features.split(",")

        if not domains_to_fix:
            continue

        exceptions_to_add = []
        for domain in domains_to_fix:
            entryAfter142 = ExceptionEntry()
            entryAfter142.fromArguments(
                bugIds=[str(bug_id)],
                urlPattern=domain,
                classifierFeatures=classifierFeatures,
                category=category,
                topLevelUrlPattern=url,
                filter_expression='env.version|versionCompare("142.0a1") >= 0'
            )
            exceptions_to_add.append(entryAfter142)
            entryBefore142 = ExceptionEntry()
            entryBefore142.fromArguments(
                bugIds=[str(bug_id)],
                urlPattern=domain,
                classifierFeatures=classifierFeatures,
                category="convenience",
                topLevelUrlPattern=url,
                isPrivateBrowsingOnly=True,
                filterContentBlockingCategories=["standard"],
                filter_expression='env.version|versionCompare("142.0a1") < 0'
            )
            exceptions_to_add.append(entryBefore142)

        # Skip if the entries are already in the RemoteSettings server. Also
        # record bugs that have exceptions deployed.
        if is_already_in_exception(exceptions_to_add, current_exceptions):
            if is_prod_server and is_already_in_exception(exceptions_to_add, deployed_exceptions):
                bugs_have_exception.append(bug_id)
            continue

        # The bug is reopened with the [privacy-team:diagnosed] tag. So, we need
        # to remove the exceptions before adding new ones.
        if entry["status"] == "REOPENED":
            entries = find_entries_by_bug_id(bug_id, current_exceptions)
            if entries:
                entries_ids = [entry.obj["id"] for entry in entries]
                if dry_run is False:
                    await remove_exceptions(server_location, auth_token, entries_ids, False, force=force)
                else:
                    print(f"Would remove exceptions for Bug {bug_id}: {entries_ids}")

        # Record bugs that need exceptions deployed.
        bugs_need_exception.append(bug_id)
        new_exceptions.extend(exceptions_to_add)

    new_exceptions_objects = [exc.toObject() for exc in new_exceptions]

    print("New exceptions:")
    print(json.dumps(new_exceptions_objects, indent=2))

    print("Bugs that will get exceptions deployed:")
    print(bugs_need_exception)

    if dry_run is False:
        print("Adding exceptions to the RemoteSettings server...")
        is_dev = server_location == "dev"
        await add_exceptions(
            server_location, auth_token, new_exceptions_objects,
            is_dev=is_dev, force=force)
        await request_review_exceptions(server_location, auth_token, is_dev=is_dev)

    # If the server is not prod, we are done here.
    if is_prod_server is False:
        return

    print("Closing bugs that have exceptions deployed...")
    print(bugs_have_exception)
    # Start closing bugs that have exceptions deployed.
    await auto_close_bugs(bugs_have_exception, dry_run)

    print("Needinfo bugs that have exceptions deployed...")
    # Start needinfo bugs that have exceptions deployed.
    await auto_ni_bugs(bugs_have_exception, dry_run)

async def auto_close_bugs(bug_list, dry_run=False):
    # First, fetch the RemoteSettings records. We need them to check if the
    # Record for the bug is already in the RemoteSettings server.
    # We only check against the prod server for closing bugs.
    rs_records = await get_deployed_records("prod")

    for bug_id in bug_list:
        # Find all entries that contain this bug_id
        matching_entries = []
        for record in rs_records:
            entry = ExceptionEntry()
            entry.fromRSRecord(record)
            # Remove the id field from the entry object. This field is not
            # necessary for the message body.
            if "id" in entry.obj:
                del entry.obj["id"]
            # Check if the bug_id is in the entry.bugIds list.
            if str(bug_id) in entry.obj["bugIds"]:
                matching_entries.append(entry)

        if not matching_entries:
            print(f"Warning: Bug {bug_id} not found in the RemoteSettings server.")
            continue

        # Construct the message to close the bug.
        message = f"Enhanced Tracking Protection (ETP) exceptions have been deployed to address this issue.\n"
        message += f"You can view all current exceptions for this bug in the ETP exceptions dashboard: https://etp-exceptions.mozilla.org/?bug_id={bug_id}\n\n"
        message += f"We have deployed the following exceptions:\n"
        message += f"```json\n"
        for entry in matching_entries:
            message += f"{entry.toJSON()}\n"
        message += f"```\n"

        bug_data = fetch_bug(bug_id, "whiteboard")
        whiteboard = bug_data["bugs"][0]["whiteboard"]

        # Strip the [privacy-team:diagnosed] tag from the whiteboard.
        whiteboard = whiteboard.replace("[privacy-team:diagnosed]", "")
        whiteboard = whiteboard.strip()

        if dry_run:
            print(f"---- Closing Bug {bug_id} ----")
            print(message)
            print(f"------------------------------")
        else:
            close_bug(bug_id, "FIXED", message, whiteboard)

async def auto_ni_bugs(bug_list, dry_run=False):
    for bug_id in bug_list:
        message = "Would you please verify if the issue is resolved by the ETP exceptions? You can verify by testing in private browsing mode or in [ETP-strict with exceptions enabled](https://support.mozilla.org/en-US/kb/manage-enhanced-tracking-protection-exceptions). Please set bug status to VERIFIED or REOPENED depending on whether this problem is still reproducible. Really appreciate your help.\n"

        if dry_run:
            print(f"---- NeedInfo Bug {bug_id} to {fetch_bug_creator(bug_id)} ----")
            print(message)
            print(f"------------------------------")
        else:
            needInfo(bug_id, message, fetch_bug_creator(bug_id))
