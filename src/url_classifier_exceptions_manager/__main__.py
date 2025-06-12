"""
URL Classifier Exceptions Manager

This script provides a command-line interface for managing URL classifier exceptions
on a RemoteSettings server. It supports listing, adding, and removing exceptions
with different server environments (dev, stage, prod).
"""

import asyncio
import argparse
import json
import uuid

from kinto_http import AsyncClient, KintoException

from .constants import (
    DEV_SERVER_LOCATION,
    STAGE_SERVER_LOCATION,
    PROD_SERVER_LOCATION,
    REMOTE_SETTINGS_BUCKET,
    REMOTE_SETTINGS_COLLECTION,
)

def lowercase_arg(value):
    """Convert argument to lowercase for case-insensitive comparison."""
    return value.lower()

def get_server_location_from_args(args):
    """
    Determine the server location based on command line arguments.
    
    Args:
        args: Command line arguments containing the server selection
        
    Returns:
        The URL of the selected server (dev, stage, or prod)
    """
    if args.server == "stage":
        server_location = STAGE_SERVER_LOCATION
    elif args.server == "prod":
        server_location = PROD_SERVER_LOCATION
    else:
        server_location = DEV_SERVER_LOCATION
    return server_location

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
    parsed_record = {
        "id": record["id"],
        "bugId": record["bugId"],
        "urlPattern": record["urlPattern"],
        "classifierFeatures": record["classifierFeatures"],
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

def print_exception(exception):
    """
    Print a single exception in JSON format.

    Args:
        exception: The exception record to print
    """
    print(json.dumps(exception, indent=2, sort_keys=True))
    print("-" * 50)

async def list_exceptions(server_location, auth_token, json_output=False):
    """
    List all exceptions from the RemoteSettings server.
    
    Args:
        server_location: The URL of the RemoteSettings server
        auth_token: Authentication token for the server
        json_output: If True, output only the JSON data without decorative text
    """
    remote_exceptions = await get_exceptions(server_location, auth_token)
    if json_output:
        print(json.dumps(remote_exceptions, indent=2, sort_keys=True))
    else:
        print("\nURL Classifier Exceptions:")
        print("=" * 50)
        for exception in remote_exceptions:
            print_exception(exception)
        print("=" * 50)
        print(f"Total exceptions: {len(remote_exceptions)}")

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

async def add_exceptions(server_location, auth_token, json_file, is_dev, force=False):
    """
    Add new exceptions or update existing ones from a JSON file.
    
    Args:
        server_location: The URL of the RemoteSettings server
        auth_token: Authentication token for the server
        json_file: Path to the JSON file containing exceptions
        is_dev: Boolean indicating if the server is a development server
        force: If True, skip confirmation prompts
    """
    try:
        with open(json_file, 'r') as f:
            new_exceptions = json.load(f)
    except Exception as e:
        print(f"Import JSON Error: {str(e)}")
        return

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
            # we check urlPattern, bugId, and classifierFeatures to determine if
            # it's a match.
            if "id" in exception and exception["id"] == remote_exception["id"]:
                matching_remote = remote_exception
                break
            elif (exception["urlPattern"] == remote_exception["urlPattern"] and
                exception["bugId"] == remote_exception["bugId"] and
                set(exception["classifierFeatures"]) == set(remote_exception["classifierFeatures"])):  # Order-independent comparison
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

async def execute():
    """
    Main execution function that parses command line arguments and executes the appropriate command.
    """
    parser = argparse.ArgumentParser(description="Tool to manage UrlClassifier exceptions on the RemoteSetting server")
    
    # Create subparsers first
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # List command
    list_parser = subparsers.add_parser('list', help='List all exceptions')
    list_parser.add_argument(
        "--server",
        choices=["dev", "stage", "prod"],
        required=True,
        type=lowercase_arg,
        help="The RemoteSettings server location (dev, stage, or prod)")
    list_parser.add_argument(
        "--auth",
        required=True,
        help="Authentication token for the RemoteSettings server")
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format only (no decorative text)")

    # Add command
    add_parser = subparsers.add_parser('add', help='Add exceptions from a JSON file')
    add_parser.add_argument('json_file', help='Path to JSON file containing exception(s)')
    add_parser.add_argument(
        "--server",
        choices=["dev", "stage", "prod"],
        required=True,
        type=lowercase_arg,
        help="The RemoteSettings server location (dev, stage, or prod)")
    add_parser.add_argument(
        "--auth",
        required=True,
        help="Authentication token for the RemoteSettings server")
    add_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts")

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove specific exceptions')
    remove_parser.add_argument(
        'exception_ids', 
        nargs='*',  # Changed from '+' to '*' to make it optional
        help='ID(s) of exceptions to remove')
    remove_parser.add_argument(
        "--all",
        action="store_true",
        help="Remove all exceptions")
    remove_parser.add_argument(
        "--server",
        choices=["dev", "stage", "prod"],
        required=True,
        type=lowercase_arg,
        help="The RemoteSettings server location (dev, stage, or prod)")
    remove_parser.add_argument(
        "--auth",
        required=True,
        help="Authentication token for the RemoteSettings server")
    remove_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    server_location = get_server_location_from_args(args)
    auth_token = args.auth

    if args.command == 'list':
        await list_exceptions(server_location, auth_token, args.json)
    elif args.command == 'add':
        await add_exceptions(server_location, auth_token, args.json_file, args.server == "dev", args.force)
    elif args.command == 'remove':
        if args.all:
            await remove_exceptions(server_location, auth_token, remove_all=True, is_dev=args.server == "dev", force=args.force)
        elif not args.exception_ids:
            remove_parser.error("Either --all or at least one exception_id must be provided")
        else:
            await remove_exceptions(server_location, auth_token, args.exception_ids, is_dev=args.server == "dev", force=args.force)

def main():
    asyncio.run(execute())

if __name__ == "__main__":
    main()
