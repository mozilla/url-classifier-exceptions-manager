#!/usr/bin/env python3
import argparse
import bugsy
import os
import sys
import logging
import json
from http.client import HTTPConnection


def setup_logging(debug=False):
    """Configure logging based on debug flag"""
    if debug:
        HTTPConnection.debuglevel = 1
        
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        logging.getLogger().setLevel(logging.DEBUG)
        requests_log = logging.getLogger("requests.packages.urllib3")
        requests_log.setLevel(logging.DEBUG)
        requests_log.propagate = True


def get_message(message_type):
    """Get predefined message based on type"""
    messages = {
        "no_impact": "This bug does not impact website functionality and is therefore closed. If this automated assessment is incorrect, please edit the bug description in comment 0 accordingly or open another bug.",
        "404": "The URL specified in this bug is returning error code 404. If you can still reproduce the issue with by altering the URL, please update the URL field and reopen the bug.",
        "site_down": "Site seems down. Feel free to reopen if this becomes reproducible again.",
        "fixed_pi": "This bug has been fixed by a permanent intervention.\n\nThis is an automated assessment, if this bug still reproduces for you in the most recent Nightly version, please reopen.",
    }
    return messages.get(message_type, messages["fixed_pi"])


def close_bug(bugzilla, bug_id, resolution, message, dry_run=False, debug=False):
    """Close a bug with the specified resolution and message"""
    json_data = {
        "status": "RESOLVED",
        "resolution": resolution,
        "comment": {"body": message}
    }
    
    if dry_run:
        print(f"[DRY RUN] Would close bug {bug_id} as {resolution}")
        if debug:
            print(f"[DEBUG] Raw JSON that would be sent:")
            print(json.dumps(json_data, indent=2))
        return
    
    try:
        bugzilla.request(
            f"bug/{bug_id}", 'PUT',
            json=json_data
        )
        print(f"Bug {bug_id} has been closed as {resolution} with a comment.")
    except Exception as e:
        print(f"Error closing bug {bug_id}: {e}", file=sys.stderr)
        if debug:
            logging.exception("Full exception details:")


def main():
    parser = argparse.ArgumentParser(
        description="Close bugs in Bugzilla with predefined messages"
    )
    
    parser.add_argument(
        "bug_ids",
        nargs="+",
        help="Bug IDs to close"
    )
    
    parser.add_argument(
        "--resolution",
        default="FIXED",
        choices=["FIXED", "INVALID", "WONTFIX", "DUPLICATE", "WORKSFORME", "INCOMPLETE"],
        help="Resolution status for the bugs (default: FIXED)"
    )
    
    parser.add_argument(
        "--message",
        default="fixed_pi",
        choices=["no_impact", "404", "site_down", "service_workers", "fixed_pi"],
        help="Predefined message type to use (default: fixed_pi)"
    )
    
    parser.add_argument(
        "--custom-message",
        help="Custom message to use instead of predefined ones"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without actually closing bugs"
    )
    
    args = parser.parse_args()
    
    # Setup logging if debug is enabled
    setup_logging(args.debug)
    
    # Check for API key
    api_key = os.getenv("BZ_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: BZ_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    # Connect to Bugzilla
    if not args.dry_run:
        try:
            bugzilla = bugsy.Bugsy(api_key=api_key)
        except Exception as e:
            print(f"Error connecting to Bugzilla: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        bugzilla = None
    
    # Get the message to use
    message = args.custom_message if args.custom_message else get_message(args.message)
    
    # Process each bug
    for bug_id in args.bug_ids:
        close_bug(bugzilla, bug_id, args.resolution, message, args.dry_run, args.debug)


if __name__ == "__main__":
    main()
