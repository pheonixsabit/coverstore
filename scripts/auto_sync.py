import os
import sys
import time
import datetime
import subprocess
import argparse
import socket

# Ensure UTF-8 output on Windows consoles with immediate line flushing
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
        sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)
    except Exception:
        pass

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def run_git(cmd: list, cwd: str = WORKSPACE_ROOT) -> subprocess.CompletedProcess:
    """Executes a git command and returns CompletedProcess."""
    return subprocess.run(
        ["git"] + cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

def perform_sync(branch: str = "main", remote: str = "origin") -> bool:
    """
    Performs bidirectional git sync:
    1. Pull latest changes from remote with --rebase --autostash.
    2. Check if local working tree has uncommitted changes. If yes, stage, commit, and push.
    3. If local commits are ahead of remote, push to remote.
    """
    timestamp_str = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    hostname = socket.gethostname()
    print(f"\n[{timestamp_str}] [Sync] Starting 20-min synchronization on {hostname}...")

    # Step 1: Pull remote changes with autostash and rebase
    print(f"[*] Fetching & pulling remote changes ({remote}/{branch}) with --rebase --autostash...")
    pull_res = run_git(["pull", "--rebase", "--autostash", remote, branch])
    if pull_res.returncode != 0:
        print(f"[!] Warning: Git pull failed:\n{pull_res.stderr.strip() or pull_res.stdout.strip()}")
        # Check if rebase needs aborting
        if "rebase in progress" in pull_res.stderr.lower() or "conflict" in pull_res.stderr.lower():
            print("[!] Merge conflict detected. Aborting rebase to keep working tree safe.")
            run_git(["rebase", "--abort"])
            return False
    else:
        pull_output = pull_res.stdout.strip()
        if "Already up to date" in pull_output:
            print("    [✓] Remote is already up to date.")
        else:
            print(f"    [✓] Updated from remote:\n    {pull_output}")

    # Step 2: Check for uncommitted local changes
    status_res = run_git(["status", "--porcelain"])
    has_uncommitted = bool(status_res.stdout.strip())

    if has_uncommitted:
        print("[*] Local changes detected. Staging all files (git add .)...")
        run_git(["add", "."])

        commit_msg = f"chore: auto-sync {hostname} [{timestamp_str}]"
        print(f"[*] Committing changes: {commit_msg}")
        commit_res = run_git(["commit", "-m", commit_msg])
        if commit_res.returncode != 0:
            print(f"[!] Warning: Commit failed: {commit_res.stderr.strip()}")
            return False
        print("    [✓] Changes committed.")

    # Step 3: Check if local is ahead of remote and push
    rev_res = run_git(["rev-list", f"{remote}/{branch}..HEAD", "--count"])
    ahead_count = 0
    if rev_res.returncode == 0 and rev_res.stdout.strip().isdigit():
        ahead_count = int(rev_res.stdout.strip())

    if ahead_count > 0:
        print(f"[*] Local repository is {ahead_count} commit(s) ahead. Pushing to {remote}/{branch}...")
        push_res = run_git(["push", remote, branch])
        if push_res.returncode != 0:
            print(f"[!] Warning: Git push failed:\n{push_res.stderr.strip() or push_res.stdout.strip()}")
            return False
        print(f"    [✓] Successfully pushed {ahead_count} commit(s) to {remote}/{branch}!")
    else:
        print("    [✓] Local is in sync with remote. No push needed.")

    print(f"[{datetime.datetime.now().strftime('%I:%M:%S %p')}] [Sync] Completed successfully.\n")
    return True

def get_seconds_until_next_aligned(interval_minutes: int = 20) -> float:
    """Calculates seconds until the next clock-aligned minute (e.g., :00, :20, :40)."""
    now = datetime.datetime.now()
    minute = now.minute
    second = now.second
    microsecond = now.microsecond

    remainder = minute % interval_minutes
    minutes_to_add = interval_minutes - remainder
    next_time = (now + datetime.timedelta(minutes=minutes_to_add)).replace(second=0, microsecond=0)
    
    delta = (next_time - now).total_seconds()
    if delta <= 1:
        # If it's exactly on the mark, target the next one
        delta += interval_minutes * 60
    return delta

def run_scheduler(interval_minutes: int = 20):
    """Runs a continuous sync loop aligned to clock intervals."""
    print("="*65)
    print(f"  COVERSTORE AUTO-SYNC DAEMON")
    print(f"  Sync interval: every {interval_minutes} minutes (e.g. :00, :20, :40)")
    print(f"  Repository:    {WORKSPACE_ROOT}")
    print("="*65)

    # Perform initial sync on startup
    perform_sync()

    while True:
        wait_seconds = get_seconds_until_next_aligned(interval_minutes)
        next_run_dt = datetime.datetime.now() + datetime.timedelta(seconds=wait_seconds)
        print(f"[*] Next auto-sync scheduled for: {next_run_dt.strftime('%I:%M:%S %p')} (in {int(wait_seconds)} seconds)...")
        
        try:
            time.sleep(wait_seconds)
            perform_sync()
        except KeyboardInterrupt:
            print("\n[!] Auto-sync terminated by user.")
            break
        except Exception as e:
            print(f"[!] Error during auto-sync cycle: {e}")
            time.sleep(10)

def main():
    parser = argparse.ArgumentParser(description="Synchronize repository with GitHub every 20 minutes across multiple PCs.")
    parser.add_argument("--once", action="store_true", help="Run sync once immediately and exit.")
    parser.add_argument("--interval", type=int, default=20, help="Interval in minutes (default: 20).")
    args = parser.parse_args()

    if args.once:
        perform_sync()
    else:
        run_scheduler(interval_minutes=args.interval)

if __name__ == "__main__":
    main()
