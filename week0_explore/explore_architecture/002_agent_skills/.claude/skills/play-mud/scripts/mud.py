#!/usr/bin/env python3
"""
Drives a MUD session over a persistent tmux + netcat connection.

Why tmux: raw TCP game servers like this one are interactive and stateful —
the connection must stay open between commands, and the server sends
unsolicited output (other players' actions, combat rounds, etc.) at any time.
A one-off `nc` call per command would drop the connection and lose state.
Running `nc` inside a detached tmux session keeps the socket alive as a
background process, independent of any single shell command, so it survives
across separate tool calls. `tmux send-keys` / `capture-pane` become the
read/write interface to that live socket.

Subcommands:
  start           connect + log in (uses MUD_USER / MUD_PASS, defaults dummy/helloworld)
  send <command>  send one command line to the game and show what happened
  read            show the current screen without sending anything
  wait <pattern>  block until <pattern> appears on screen (useful after slow actions)
  stop            quit the game and kill the tmux session
  status          report whether a session is currently running
"""
import argparse
import os
import subprocess
import sys
import time

SESSION = os.environ.get("MUD_SESSION", "mud")
HOST = os.environ.get("MUD_HOST", "localhost")
PORT = os.environ.get("MUD_PORT", "4000")
USERNAME = os.environ.get("MUD_USER", "dummy")
PASSWORD = os.environ.get("MUD_PASS", "helloworld")


def tmux(*args, check=True):
    return subprocess.run(["tmux", *args], capture_output=True, text=True, check=check)


def session_exists():
    return tmux("has-session", "-t", SESSION, check=False).returncode == 0


def capture(scrollback=500):
    r = tmux("capture-pane", "-t", SESSION, "-p", "-S", f"-{scrollback}")
    return r.stdout


def trimmed_lines(scrollback=500):
    """Content lines with tmux's trailing blank padding stripped off.

    tmux pads a capture out to the full pane height, so the true last line of
    output is rarely the actual last line returned — trimming lets both the
    prompt-detection logic and the human-facing output agree on what "recent"
    means.
    """
    lines = capture(scrollback).splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def send_keys(text, enter=True):
    args = ["send-keys", "-t", SESSION, text]
    if enter:
        args.append("Enter")
    tmux(*args)


def wait_for_any(patterns, timeout=15, poll=0.2, tail_lines=6):
    """Poll the screen until one of `patterns` shows up near the bottom, or time out.

    Only the last `tail_lines` are checked, not the whole scrollback. Prompts like
    "PRESS RETURN" or "Make your choice" scroll off screen once superseded, but they
    stay in history forever — matching against full scrollback would keep re-firing
    on stale prompts long after the game has moved on, starving the caller from ever
    reaching the pattern that's actually current.
    """
    deadline = time.time() + timeout
    content_lines = []
    while time.time() < deadline:
        content_lines = trimmed_lines()
        tail = "\n".join(content_lines[-tail_lines:])
        for p in patterns:
            if p in tail:
                return p, "\n".join(content_lines)
        time.sleep(poll)
    return None, "\n".join(content_lines)


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def cmd_start(args):
    if session_exists():
        print(f"Session '{SESSION}' is already running. Try `mud.py read`, or `mud.py stop` first to reconnect fresh.")
        return

    tmux("new-session", "-d", "-s", SESSION, f"nc {HOST} {PORT}")

    matched, screen = wait_for_any(["By what name"], timeout=15)
    if not matched:
        die(f"Never reached the login prompt. Last screen:\n{screen}")
    send_keys(USERNAME)

    matched, screen = wait_for_any(["Password:"], timeout=10)
    if not matched:
        die(f"Never reached the password prompt. Last screen:\n{screen}")
    send_keys(PASSWORD)

    # After password, tbaMUD may show (in order, any of which can be skipped):
    #   - a "PRESS RETURN" MOTD pager
    #   - a numbered menu ("1) Enter the game.")
    # before finally dropping into the game world. Walk through whichever
    # combination shows up rather than assuming a fixed number of steps.
    for _ in range(5):
        matched, screen = wait_for_any(["PRESS RETURN", "Make your choice", ") >"], timeout=10)
        if matched == "PRESS RETURN":
            send_keys("")
        elif matched == "Make your choice":
            send_keys("1")
        elif matched == ") >":
            break
        else:
            die(f"Login stalled — unrecognized screen:\n{screen}")
        # Give the server a moment to react before polling again — otherwise the
        # next check can still see the same stale prompt and re-send a response
        # to a screen we already answered.
        time.sleep(0.7)

    print(f"Connected to {HOST}:{PORT} and logged in as '{USERNAME}'.\n")
    print("\n".join(trimmed_lines()[-30:]))


def cmd_send(args):
    if not session_exists():
        die("No active MUD session. Run `mud.py start` first.")
    send_keys(" ".join(args.command))
    time.sleep(args.wait)
    print("\n".join(trimmed_lines()[-args.lines:]))


def cmd_read(args):
    if not session_exists():
        die("No active MUD session. Run `mud.py start` first.")
    print("\n".join(trimmed_lines()[-args.lines:]))


def cmd_wait(args):
    if not session_exists():
        die("No active MUD session. Run `mud.py start` first.")
    matched, screen = wait_for_any([args.pattern], timeout=args.timeout)
    if not matched:
        die(f"Timed out waiting for {args.pattern!r}. Last screen:\n{screen}")
    print(screen)


def cmd_stop(args):
    if session_exists():
        send_keys("quit")
        time.sleep(1)
        tmux("kill-session", "-t", SESSION, check=False)
        print("Disconnected and stopped session.")
    else:
        print("No active session.")


def cmd_status(args):
    print("running" if session_exists() else "not running")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("start", help="connect and log in").set_defaults(func=cmd_start)

    sp = sub.add_parser("send", help="send a command to the game")
    sp.add_argument("command", nargs="+", help="the command text, e.g. look, north, kill rat")
    sp.add_argument("--wait", type=float, default=1.0, help="seconds to wait for a response before reading the screen")
    sp.add_argument("--lines", type=int, default=40, help="how many of the most recent output lines to show")
    sp.set_defaults(func=cmd_send)

    rp = sub.add_parser("read", help="show the current screen")
    rp.add_argument("--lines", type=int, default=40, help="how many of the most recent output lines to show")
    rp.set_defaults(func=cmd_read)

    wp = sub.add_parser("wait", help="block until a pattern appears on screen")
    wp.add_argument("pattern")
    wp.add_argument("--timeout", type=float, default=15)
    wp.set_defaults(func=cmd_wait)

    sub.add_parser("stop", help="quit and close the session").set_defaults(func=cmd_stop)
    sub.add_parser("status", help="is a session currently running?").set_defaults(func=cmd_status)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
