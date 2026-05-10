---
description: "Sync KroWork apps across devices via cloud folders"
disable-model-invocation: false
allowedTools: mcp__krowork__krowork_sync_configure, mcp__krowork__krowork_sync_push, mcp__krowork__krowork_sync_pull, mcp__krowork__krowork_sync_status, mcp__krowork__krowork_sync_list_remote, mcp__krowork__krowork_list_apps
---

# KroWork: Sync

Sync KroWork apps across devices using a user-owned cloud folder.

## How It Works

KroWork syncs apps via a shared folder that both devices can access:
- **OneDrive**: `C:\Users\you\OneDrive\KroWork`
- **Dropbox**: `C:\Users\you\Dropbox\Apps\KroWork`
- **Google Drive**: `G:\My Drive\KroWork`
- **坚果云 / Synology / Nextcloud**: Any WebDAV-mounted folder
- **Network share**: `\\NAS\shared\KroWork`

All data stays in the user's own cloud account. KroWork never uploads to its own servers.

## Workflow

### Step 1: Configure (First Time)

The user input `$ARGUMENTS` should specify the sync folder path.

Use `krowork_sync_configure` with:
- `target_dir`: The cloud folder path
- `device_name`: Optional device identifier (e.g., "office-laptop", "home-pc")

Example: `/krowork:sync configure C:\Users\hacki\OneDrive\KroWork`

### Step 2: Check Status

Use `krowork_sync_status` to see:
- Which apps need to be pushed (new or updated locally)
- Which apps need to be pulled (new or updated remotely)
- Any conflicts

### Step 3: Push or Pull

- **Push** (`krowork_sync_push`): Export local apps to the sync folder
  - Only exports changed apps (incremental)
  - Use `force: true` to push all apps

- **Pull** (`krowork_sync_pull`): Import apps from the sync folder
  - Only imports newer versions
  - Use `overwrite: true` to force overwrite local changes

### Step 4: Resolve Conflicts

If both devices modified the same app:
1. The conflict will be reported in `krowork_sync_status`
2. Explain the conflict to the user
3. Ask which version to keep (local or remote)
4. Use `overwrite: true` on push or pull to resolve

## Typical Usage

```
# On Device A (laptop):
/krowork:sync configure ~/OneDrive/KroWork
/krowork:sync push

# On Device B (desktop):
/krowork:sync configure ~/OneDrive/KroWork
/krowork:sync pull
```

## Tips

- Configure the same folder on all devices
- Push from the device where you create/modify apps
- Pull on other devices to get updates
- Check status before pushing to avoid conflicts
