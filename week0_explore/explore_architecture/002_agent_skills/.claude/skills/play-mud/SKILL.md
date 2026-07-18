---
name: play-mud
description: Connect to and play the local tbaMUD text-adventure server at localhost:4000 (login dummy/helloworld) — walk around, fight, talk to NPCs, manage inventory, or otherwise act as the player in the game. Use this skill any time the user asks to play the MUD, log into the MUD, explore the game world, check character stats, fight a monster, or issue any in-game command, even if they just say something like "what's around me?" or "attack the rat" without mentioning the MUD explicitly, as long as the context is clearly this game session. Also use it to check whether a game session is currently connected before assuming one exists. Remembers character state, world knowledge, and longer-running goals (e.g. "get to level 7", "kill the rat king") across separate conversations via data/player.md and data/world.md — use it for those follow-up asks too, even without an active session.
---

# Playing the tbaMUD

This is a raw-TCP text MUD (tbaMUD) running at `localhost:4000`. It's an
interactive, stateful protocol: the connection must stay open between
commands, and the server can push unsolicited output at any time (other
players' actions, combat rounds, room descriptions). A one-off `nc` or
`curl`-style call per command won't work — it would reconnect and lose all
game state every time.

To solve this, `scripts/mud.py` keeps the connection alive inside a detached
`tmux` session running `nc`, independent of any single Bash tool call, so it
persists across your separate commands in this conversation. Drive the game
entirely through this script rather than reaching for raw `nc`/`tmux` calls —
it already handles the login sequence's quirks (see below).

## Commands

Run these from the skill's `scripts/` directory (or give the full path):

```
python3 mud.py start              # connect + log in (only if not already connected)
python3 mud.py send <command...>  # e.g. `mud.py send look`, `mud.py send kill rat`
python3 mud.py read               # show the current screen without sending anything
python3 mud.py wait <text>        # block until <text> appears (for slow multi-part actions)
python3 mud.py status             # is a session currently connected?
python3 mud.py stop               # quit the game and close the session
```

`send` prints the most recent output after the command (default last 40
lines; pass `--lines N` for more, e.g. a long `inventory` or `who` listing).
It also waits 1 second by default before reading — pass `--wait N` for
commands you know take longer to resolve (e.g. entering a new area that
triggers a scripted event).

## Persistent memory: player.md and world.md

The tmux session (and the connection inside it) is only as durable as this
machine's uptime — but even when it survives, a fresh conversation still
starts with no memory of what happened last time. `data/player.md` and
`data/world.md`, next to this skill's `scripts/`, are how continuity actually
happens: real files that outlive both the tmux session and the conversation,
so a goal like "get to level 7" or "kill the rat king" can span many separate
sessions instead of resetting every time.

- **`data/player.md`** — the character: current stats (from `score`),
  equipment/inventory, and a **Goals** section (Active / Completed) that is
  the actual driver for longer-running asks. Also a short newest-first
  session log — level-ups, deaths, goal progress, one or two lines each, not
  a transcript.
- **`data/world.md`** — everything about the world that's worth not
  rediscovering: rooms visited and their exits, guild/shop locations, monster
  and danger notes, and mechanics learned (commands, how shops work, how
  guilds gate entry, etc.).

**Read both files before doing anything else** — before or right alongside
`status`/`start` — so you know the character's level, gold, condition, active
goals, and what's already been mapped, instead of re-exploring or re-asking
the user things already answered in a previous session.

**Write updates at natural checkpoints**, not after every command — a
level-up, a death/respawn, arriving somewhere new and notable, making or
finishing progress on a goal, or wrapping up before ending a play session.
Keep entries terse, structured, and additive: append to the room table or
goals list rather than rewriting the file's prose, since these files are
meant to accumulate accurately over many sessions, not read beautifully in
any one of them.

## Workflow

1. **Check first, don't assume.** Run `status` before `start` — if a session
   is already running (e.g. left over from earlier in the conversation),
   `start` will just tell you so and do nothing; there's no need to restart
   it. Reuse the existing session so you don't lose the character's current
   location and state. Read the memory files regardless of whether a session
   is already running — they carry context the live session can't show you.
2. **Log in once per session**, then issue as many `send` calls as the task
   needs — one call per game command, reading the response each time before
   deciding the next action. Don't chain multiple game commands into one
   `send` call; the MUD processes and echoes one line at a time; batching
   commands makes the output hard to attribute and easy to misread.
3. **Read before acting.** MUD commands are contextual (what you see in the
   room, in your inventory, in the exits list, determines what's valid to do
   next) — read the output of each `send` before issuing the next command,
   the same way a human player would read the screen before typing.
4. **Leave the session open** when done with a single task unless the user
   asks to disconnect — logging out and back in re-triggers the whole login
   sequence and menu, which is slower than just leaving the character
   standing where they are. Only call `stop` when the user is done playing
   for now.
5. **Checkpoint the memory files before you stop responding** — even if the
   session stays open, the next conversation won't see this one's reasoning,
   only what's on disk.

## Working toward long-running goals

When the user hands you a goal that won't finish in one exchange — "get to
level 7", "go kill the rat king" — this is meant to be driven mostly
autonomously rather than one action at a time:

1. Record the goal in `player.md`'s Active Goals immediately, so it survives
   even if the session is interrupted right after this message.
2. Loop: check status (`score`, and `read` if unsure what's on screen — these
   are free checks, not actions) → if badly hurt, heal/rest before doing
   anything risky → pick a target appropriate to current level using
   `world.md`'s monster/danger notes (don't repeatedly throw a level-1
   character at something already flagged as dangerous or unknown) → act →
   re-check status → repeat. Hunger and thirst are a slow drain, not an
   emergency — a broke character has no way to "resolve that first" since
   food costs gold, so it's fine to fight for starting gold/exp before
   dealing with them; don't treat them as a blocker that stalls the loop.
3. Checkpoint `player.md` on every level-up and roughly every 15-20 real
   `send` actions during a long grind (status/read checks don't count) so an
   interruption mid-grind doesn't lose the whole session's progress.
4. Fold anything newly learned into `world.md` as you go — a new room, a
   monster's actual difficulty, a mechanic you had to figure out by trial —
   so the next goal (or the next session on this one) doesn't rediscover it.
5. **Stop and surface to the user** rather than continuing to grind blindly
   when: the goal is complete; you've died repeatedly (2+ times) without
   making progress; you can't locate the goal's target after a reasonable
   search; or you hit a decision only the user should make (spending
   significant gold, picking a guild/alignment path, etc.). Update the memory
   files with what you learned either way — a dead end recorded in
   `world.md` saves the next attempt from repeating it.

## Login sequence quirks (handled automatically by `start`)

If you ever need to debug connection issues by hand, note that this server's
login isn't a single prompt-response — it's a short chain, and each step's
prompt text must be matched exactly, not assumed to happen after a fixed
delay (server response time varies):

1. `By what name do you wish to be known?` → send username
2. `Password:` → send password
3. Then, in any combination: a `*** PRESS RETURN:` MOTD pager (send a blank
   line to continue) and a numbered menu ending in `Make your choice:`
   (send `1` for "Enter the game"). Skip straight past whichever of these the
   server doesn't show.

`mud.py start` already loops through this, matching on live prompt text
rather than fixed sleeps, and only inspects the last few non-blank lines of
the screen so it doesn't misfire on a prompt that already scrolled past.
Credentials and connection target default to `dummy` / `helloworld` on
`localhost:4000`, overridable via the `MUD_USER`, `MUD_PASS`, `MUD_HOST`,
`MUD_PORT`, and `MUD_SESSION` environment variables if ever needed.
