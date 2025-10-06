# URL Classifier Exceptions Manager

A comprehensive tool for managing URL classifier exceptions on Mozilla's RemoteSettings server. This tool automates the process of creating, deploying, and managing Enhanced Tracking Protection (ETP) exceptions based on Bugzilla reports.

## Features

- **Automated Exception Management**: Automatically generate and deploy URL classifier exceptions from Bugzilla reports
- **Multi-Environment Support**: Work with dev, stage, and production RemoteSettings servers
- **Bugzilla Integration**: Fetch bug data, close bugs, and send NeedInfo requests
- **Exception Lifecycle Management**: List, add, and remove exceptions with full CRUD operations

## Usage

The tool provides a command-line interface through the `uce-manager` command:

### Basic Commands

#### List Exceptions
```bash
uce-manager list --server <dev|stage|prod> --auth <auth-token> [--json]
```

#### Add Exceptions
```bash
uce-manager add <json-file> --server <dev|stage|prod> --auth <auth-token> [--force]
```

#### Remove Exceptions
```bash
uce-manager remove --server <dev|stage|prod> --auth <auth-token> [--all] [exception-ids...] [--force]
```

### Bugzilla Integration

#### Get Bug Information
```bash
uce-manager bz-info [--product "Web Compatibility"] [--component "Privacy: Site Reports"]
```

#### Close Bugs
```bash
uce-manager bz-close --bug-id <bug-id> --resolution <resolution> --message <message>
# Or with multiple bugs from file
uce-manager bz-close --bug-ids-file <file> --resolution <resolution> --message <message>
```

#### Send NeedInfo
```bash
uce-manager bz-ni --bug-id <bug-id> --message <message> --requestee <email>
# Or with multiple bugs from file
uce-manager bz-ni --bug-ids-file <file> --message <message> --requestee <email>
```

### Automated Exception Deployment

The script can deploy URL Classifier exceptions automatically based on Bugzilla bugs:

```bash
uce-manager auto --server <dev|stage|prod> --auth <auth-token> [--dry-run]
```

This command:
1. Fetches bugs from Bugzilla with `[privacy-team:diagnosed]` whiteboard tag
2. Filters bugs that need exceptions (based on whiteboard tags)
3. Creates appropriate exception entries for Firefox versions before and after 142.0a1
4. Deploys exceptions to RemoteSettings
5. Closes bugs that have exceptions deployed (production only)
6. Sends NeedInfo requests to bug creators

## Workflow

### Typical Workflow for Privacy Team

1. **Bug Analysis**: Privacy team diagnoses bugs and adds `[privacy-team:diagnosed]` whiteboard tag
2. **Exception Planning**: Add appropriate whiteboard tags (`[exception-baseline]` or `[exception-convenience]`)
3. **User Story**: Include `trackers-blocked:` and `classifier-features:` in the user story
4. **Automated Deployment**: Run `uce-manager auto` to automatically create and deploy exceptions
5. **Verification**: The tool automatically closes bugs and requests verification from bug reporters

### Example Bugzilla User Story Format

```
trackers-blocked: tracker1.com, tracker2.com
classifier-features: tracking-protection, emailtracking-protection
```
