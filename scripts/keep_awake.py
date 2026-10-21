import os
import sys
import time
import datetime
import argparse
import ctypes

# Windows Execution State Flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002
ES_AWAYMODE_REQUIRED = 0x00000040

def set_execution_state(keep_display: bool = False) -> bool:
    """Invokes Win32 SetThreadExecutionState to keep system awake without physical interaction."""
    if sys.platform != "win32":
        return False
    flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED
    if keep_display:
        flags |= ES_DISPLAY_REQUIRED
    try:
        res = ctypes.windll.kernel32.SetThreadExecutionState(flags)
        return res != 0
    except Exception as e:
        print(f"[!] Warning: SetThreadExecutionState failed: {e}")
        return False

def reset_execution_state():
    """Restores default Windows sleep behavior."""
    if sys.platform == "win32":
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            pass

def main():
    parser = argparse.ArgumentParser(description="Keep Windows PC awake during remote Antigravity operations.")
    parser.add_argument("--display", action="store_true", help="Also prevent monitor / display from sleeping.")
    args = parser.parse_args()

    mode_str = "System + Display" if args.display else "System & AwayMode (Monitors may turn off, CPU/Network stays awake)"
    print("=" * 65)
    print("  COVERSTORE WORKSTATION KEEP-AWAKE DAEMON")
    print(f"  Mode: {mode_str}")
    print("  Status: ACTIVE (Windows sleep & hibernation blocked)")
    print("  Press Ctrl+C to terminate and restore normal sleep behavior.")
    print("=" * 65)

    set_execution_state(keep_display=args.display)

    try:
        while True:
            # Re-assert every 60 seconds to guard against external policy resets
            time.sleep(60)
            set_execution_state(keep_display=args.display)
    except KeyboardInterrupt:
        print("\n[*] Restoring default Windows power state...")
        reset_execution_state()
        print("[✓] Restored. Exiting.")

if __name__ == "__main__":
    main()
