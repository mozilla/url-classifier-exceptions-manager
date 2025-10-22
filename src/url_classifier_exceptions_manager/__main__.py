"""
URL Classifier Exceptions Manager

This script provides a command-line interface for managing URL classifier
exceptions. It supports listing, adding, and removing exceptions
with different server environments (dev, stage, prod). It also supports getting
the bug data from Bugzilla.
"""

import asyncio
import argparse
import json

from .bugzilla import fetch_bug_data, needInfo, close_bug
from .auto import auto_deploy_exceptions
from .remoteSettings import (
    list_exceptions,
    add_exceptions,
    remove_exceptions,
    print_exception,
)

from .constants import (
    DEV_SERVER_LOCATION,
    STAGE_SERVER_LOCATION,
    PROD_SERVER_LOCATION,
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
        "--server-location",
        help="The server location to list the exceptions from. If not provided, the default server location will be used."
    )
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
        "--server-location",
        help="The server location to add the exceptions to. If not provided, the default server location will be used."
    )
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
        "--server-location",
        help="The server location to remove the exceptions from. If not provided, the default server location will be used."
    )
    remove_parser.add_argument(
        "--auth",
        required=True,
        help="Authentication token for the RemoteSettings server")
    remove_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts")

    # Bugzilla list bugs info command
    bz_parser = subparsers.add_parser('bz-info', help='Get bug info from Bugzilla')
    bz_parser.add_argument(
        "--product",
        default="Web Compatibility",
        help="The product to get bug data for")
    bz_parser.add_argument(
        "--component",
        default="Privacy: Site Reports",
        help="The component to get bug data for")

    # Bugzilla NeedInfo command
    ni_parser = subparsers.add_parser('bz-ni', help='Send NeedInfo on Bugzilla')
    ni_parser.add_argument(
        "--bug-id",
        help="The Bugzilla bug ID to close"
    )
    ni_parser.add_argument(
        "--bug-ids-file",
        help="Path to file containing bug IDs to close"
    )
    ni_parser.add_argument(
        "--message",
        required=True,
        help="The message to test NeedInfo and Bugzilla"
    )
    ni_parser.add_argument(
        "--requestee",
        required=True,
        help="The requestee to test NeedInfo and Bugzilla"
    )

    # Bugzilla close bug command
    close_parser = subparsers.add_parser('bz-close', help='Close bugs on Bugzilla')
    close_parser.add_argument(
        "--bug-id",
        help="The Bugzilla bug ID to close"
    )
    close_parser.add_argument(
        "--bug-ids-file",
        help="Path to file containing bug IDs to close"
    )
    close_parser.add_argument(
        "--resolution",
        required=True,
        help="The resolution to close the bug"
    )
    close_parser.add_argument(
        "--message",
        required=True,
        help="The message to close the bug"
    )

    # Auto command
    auto_parser = subparsers.add_parser('auto', help='Automatically generate exceptions from Bugzilla')
    auto_parser.add_argument(
        "--server",
        choices=["dev", "stage", "prod"],
        required=True,
        type=lowercase_arg,
        help="The RemoteSettings server location (dev, stage, or prod)")
    auto_parser.add_argument(
        "--server-location",
        help="The server location to deploy the exceptions to. If not provided, the default server location will be used."
    )
    auto_parser.add_argument(
        "--auth",
        required=True,
        help="Authentication token for the RemoteSettings server")
    auto_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run the command"
    )
    auto_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    if args.command == 'list':
        if args.server_location:
            server_location = args.server_location
        else:
            server_location = get_server_location_from_args(args)
        auth_token = args.auth
        remote_exceptions = await list_exceptions(server_location, auth_token)

        if args.json:
            print(json.dumps(remote_exceptions, indent=2, sort_keys=True))
        else:
            print("\nURL Classifier Exceptions:")
            print("=" * 50)
            for exception in remote_exceptions:
                print_exception(exception)
            print("=" * 50)
            print(f"Total exceptions: {len(remote_exceptions)}")
    elif args.command == 'add':
        if args.server_location:
            server_location = args.server_location
        else:
            server_location = get_server_location_from_args(args)
        auth_token = args.auth
        with open(args.json_file, 'r') as f:
            new_exceptions = json.load(f)
        await add_exceptions(server_location, auth_token, new_exceptions, args.server == "dev", args.force)
    elif args.command == 'remove':
        if args.server_location:
            server_location = args.server_location
        else:
            server_location = get_server_location_from_args(args)
        auth_token = args.auth
        if args.all:
            await remove_exceptions(server_location, auth_token, remove_all=True, is_dev=args.server == "dev", force=args.force)
        elif not args.exception_ids:
            remove_parser.error("Either --all or at least one exception_id must be provided")
        else:
            await remove_exceptions(server_location, auth_token, args.exception_ids, is_dev=args.server == "dev", force=args.force)
    elif args.command == 'bz-info':
        bugs = fetch_bug_data(args.product, args.component)
        print(json.dumps(bugs, indent=2, sort_keys=True))
    elif args.command == 'auto':
        if args.server_location:
            server_location = args.server_location
        else:
            server_location = get_server_location_from_args(args)
        auth_token = args.auth

        await auto_deploy_exceptions(
            server_location, auth_token, args.server == "prod", args.dry_run, args.force)
    elif args.command == 'bz-close':
        # Validate that either --bug-id or --bug-ids-file is provided
        if not args.bug_id and not args.bug_ids_file:
            close_parser.error("Either --bug-id or --bug-ids-file must be provided")
        if args.bug_id and args.bug_ids_file:
            close_parser.error("Only one of --bug-id or --bug-ids-file can be provided")

        if args.bug_id:
            close_bug(args.bug_id, args.resolution, args.message)
        else:
            with open(args.bug_ids_file, 'r') as f:
                bug_ids = f.read().splitlines()
            for bug_id in bug_ids:
                close_bug(bug_id, args.resolution, args.message)
    elif args.command == 'bz-ni':
        if not args.bug_id and not args.bug_ids_file:
            ni_parser.error("Either --bug-id or --bug-ids-file must be provided")
        if args.bug_id and args.bug_ids_file:
            ni_parser.error("Only one of --bug-id or --bug-ids-file can be provided")

        if args.bug_id:
            needInfo(args.bug_id, args.message, args.requestee)
        else:
            with open(args.bug_ids_file, 'r') as f:
                bug_ids = f.read().splitlines()
            for bug_id in bug_ids:
                needInfo(bug_id, args.message, args.requestee)

def main():
    asyncio.run(execute())

if __name__ == "__main__":
    main()
