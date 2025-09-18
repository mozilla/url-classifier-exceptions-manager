import json
import uuid
import aiohttp

from kinto_http import AsyncClient, KintoException
from .constants import (
    REMOTE_SETTINGS_BUCKET,
    REMOTE_SETTINGS_COLLECTION,
    PROD_RECORDS_LOCATION,
    STAGE_RECORDS_LOCATION,
)

def confirm_action(action_description, force=False):
    """
    Prompt the user for confirmation before proceeding with an action.

    Args:
        action_description: A description of the action to be performed
        force: If True, skip confirmation and proceed automatically

    Returns:
        Boolean indicating whether the action should proceed
    """
    if force:
        return True

    confirmation = input(f"\nAre you sure you want to {action_description}? (y/n): ")
    return confirmation.lower() in ('y', 'yes')

def print_exception(exception):
    """
    Print a single exception in JSON format.

    Args:
        exception: The exception record to print
    """
    print(json.dumps(exception, indent=2, sort_keys=True))
    print("-" * 50)

def parse_rs_record(record):
    """
    Parse a RemoteSettings record into a standardized format.
    
    Args:
        record: The raw record from RemoteSettings

    Returns:
        A dictionary containing the parsed record with standardized fields.
        Optional fields are only included if they exist in the source record.
    """
    # Start with the required fields
    bugIds = []
    if "bugIds" in record:
        bugIds = record["bugIds"]
    elif "bugId" in record:
        bugIds = [record["bugId"]]
    parsed_record = {
        "id": record["id"],
        "bugIds": bugIds,
        "urlPattern": record["urlPattern"],
        "classifierFeatures": record["classifierFeatures"],
        "category": record.get("category", "convenience"),
    }

    # Add optional fields only if they exist in the source record
    if "topLevelUrlPattern" in record:
        parsed_record["topLevelUrlPattern"] = record["topLevelUrlPattern"]

    if "isPrivateBrowsingOnly" in record:
        parsed_record["isPrivateBrowsingOnly"] = record["isPrivateBrowsingOnly"]

    if "filterContentBlockingCategories" in record:
        parsed_record["filterContentBlockingCategories"] = record["filterContentBlockingCategories"]

    if "filter_expression" in record:
        parsed_record["filter_expression"] = record["filter_expression"]

    return parsed_record

async def update_records(async_client, records):
    """
    Update or create records in the RemoteSettings server.
    
    Args:
        async_client: The AsyncClient instance for the server
        records: List of records to update or create

    Returns:
        The response from the server if successful, None otherwise
    """
    try:
        for data in records:
            # Remove bugId if present, always use bugIds
            if "bugId" in data:
                del data["bugId"]
            # Ensure category is present
            if "category" not in data:
                data["category"] = "convenience"
            rec_resp = await async_client.update_record(id=data['id'],
                data=data)
            if not rec_resp:
                print('Failed to create/update record for %s. Error: %s' %
                    (data['Name'], rec_resp.content.decode()))
                return rec_resp
    except KintoException as e:
        print('Failed to create/update record for {0}. Error: {1}'
            .format(data['Name'], e))

async def request_review(async_client, is_dev):
    """
    Request a review for changes made to the RemoteSettings collection.

    Args:
        async_client: The AsyncClient instance for the server
        is_dev: Boolean indicating if the server is a development server
    """
    rs_collection = await async_client.get_collection()

    if rs_collection:
        # If any data was published, we want to request review for it
        # status can be one of "work-in-progress", "to-sign" (approve), "to-review" (request review)
        if rs_collection['data']['status'] == "work-in-progress":
            if is_dev:
                print("\n*** Dev server does not require a review, approving changes ***\n")
                # review not enabled in dev, approve changes
                await async_client.patch_collection(data={"status": "to-sign"});
            else:
                print("\n*** Requesting review for updated/created records ***\n")
                await async_client.patch_collection(data={"status": "to-review"});
        else:
            print("\n*** No changes were made, no new review request is needed ***\n")
    else:
        print("\n*** Error while fetching collection status ***\n")

def get_async_client(server_location, auth_token):
    """
    Create an asynchronous client for interacting with RemoteSettings.

    Args:
        server_location: The URL of the RemoteSettings server
        auth_token: Authentication token for the server

    Returns:
        An AsyncClient instance configured for the specified server
    """
    return AsyncClient(
        server_url=server_location,
        auth=auth_token,
        bucket=REMOTE_SETTINGS_BUCKET,
        collection=REMOTE_SETTINGS_COLLECTION,
    )

async def get_exceptions(server_location, auth_token):
    """
    Retrieve all exceptions from the RemoteSettings server.

    Args:
        server_location: The URL of the RemoteSettings server
        auth_token: Authentication token for the server

    Returns:
        A list of parsed exception records
    """
    async_client = get_async_client(server_location, auth_token)

    records = await async_client.get_records()
    remote_exceptions = [parse_rs_record(r) for r in records]
    return remote_exceptions

async def list_exceptions(server_location, auth_token):
    """
    List all exceptions from the RemoteSettings server.

    Args:
        server_location: The URL of the RemoteSettings server
        auth_token: Authentication token for the server
        json_output: If True, output only the JSON data without decorative text
    """
    return await get_exceptions(server_location, auth_token)

async def add_exceptions(server_location, auth_token, new_exceptions, is_dev, force=False):
    """
    Add new exceptions or update existing ones from a JSON file.

    Args:
        server_location: The URL of the RemoteSettings server
        auth_token: Authentication token for the server
        new_exceptions: List of exceptions to add
        is_dev: Boolean indicating if the server is a development server
        force: If True, skip confirmation prompts
    """
    async_client = get_async_client(server_location, auth_token)
    remote_exceptions = await get_exceptions(server_location, auth_token)

    to_create = []
    to_update = []

    for exception in new_exceptions:
        # Initialize variable to track if we find a matching exception
        matching_remote = None
        # Search through existing remote exceptions
        for remote_exception in remote_exceptions:
            # Match exceptions. If the id is the same, it's a match. Otherwise,
            # we check urlPattern, bugIds, and classifierFeatures to determine if
            # it's a match.
            if "id" in exception and exception["id"] == remote_exception["id"]:
                matching_remote = remote_exception
                break
            elif (
                exception["urlPattern"] == remote_exception["urlPattern"] and
                set(exception["bugIds"]) == set(remote_exception["bugIds"]) and
                set(exception["classifierFeatures"]) == set(remote_exception["classifierFeatures"]) and
                set(exception["filterContentBlockingCategories"]) == set(remote_exception["filterContentBlockingCategories"])
            ):
                matching_remote = remote_exception
                break

        if matching_remote:
            # For existing exceptions, copy the ID and add to update list
            exception["id"] = matching_remote["id"]
            to_update.append(exception)
        else:
            # For new exceptions, add to create list
            exception["id"] = str(uuid.uuid4())
            to_create.append(exception)

    # Check if there are any exceptions to create or update
    if not to_create and not to_update:
        print(f"\nAll exceptions in the file already exist and are up-to-date.\n")
        return

    # Display exceptions that will be added
    if to_create:
        print("\nExceptions to be added:")
        print("=" * 50)
        for exception in to_create:
            print_exception(exception)

    # Display exceptions that will be updated
    if to_update:
        print("\nExceptions to be updated:")
        print("=" * 50)
        for exception in to_update:
            print_exception(exception)

    action_description = f"add new exceptions and update existing ones"
    if not confirm_action(action_description, force):
        print("Operation cancelled.")
        return

    await update_records(async_client, to_update)
    await update_records(async_client, to_create)

    await request_review(async_client, is_dev)
    print(f"\nSummary: {len(to_create)} to create, {len(to_update)} to update")

async def remove_exceptions(server_location, auth_token, exception_ids=None, remove_all=False, is_dev=False, force=False):
    """
    Remove exceptions from the RemoteSettings server.

    Args:
        server_location: The URL of the RemoteSettings server
        auth_token: Authentication token for the server
        exception_ids: List of exception IDs to remove (optional)
        remove_all: If True, remove all exceptions
        is_dev: Boolean indicating if the server is a development server
        force: If True, skip confirmation prompts
    """
    async_client = get_async_client(server_location, auth_token)

    if remove_all:
        # Get all records and delete them
        action_description = "remove ALL exceptions from the server"
        if not confirm_action(action_description, force):
            print("Operation cancelled.")
            return

        try:
            await async_client.delete_records()
        except KintoException as e:
            print(f"Error removing all exceptions: {e}")
            return

        print(f"Successfully removed all exceptions")
    else:
        action_description = f"remove {len(exception_ids)} exception(s)"
        if not confirm_action(action_description, force):
            print("Operation cancelled.")
            return

        try:
            for exception_id in exception_ids:
                await async_client.delete_record(id=exception_id)
        except KintoException as e:
            print(f"Error removing exceptions: {e}")
            return
        print(f"Successfully removed {len(exception_ids)} exception(s)")

    await request_review(async_client, is_dev)

async def get_deployed_records(server):
    """
    Download and return production records from the PROD_RECORDS_LOCATION.
    
    Returns:
        A list of production exception records
    """
    if server == "prod":
        records_location = PROD_RECORDS_LOCATION
    elif server == "stage":
        records_location = STAGE_RECORDS_LOCATION
    else:
        raise Exception(f"Invalid server: {server}")


    async with aiohttp.ClientSession() as session:
        async with session.get(records_location) as response:
            if response.status == 200:
                data = await response.json()
                records = data["data"]
                remote_exceptions = [parse_rs_record(r) for r in records]
                return remote_exceptions
            else:
                raise Exception(f"Failed to fetch production records. Status: {response.status}")
