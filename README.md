Create a Discord bot using Python (discord.py) that runs an automated Battle Royale–style tournament with a point system. Each round, all players play the same mini-game simultaneously. The bot uses slash commands (/), and only admins/moderators (or users they grant permission to) can start the tournament. Interactions for some games use Discord buttons for a modern and intuitive experience.

Core Concept
Players register once by clicking a button on the registration message.

The bot automatically manages all rounds.

Each round, the bot plays one mini‑game from a fixed list in order (not random). The list contains 6 games. Since there are 24 rounds total, the game order repeats 4 times (each game is played 4 times).

All registered players participate in the same game at the same time.

The bot determines the 3 fastest winners based on the order of correct answers/completions received during a 17‑second window.

Point system:

1st place: +5 points, given a reaction 🥇

2nd place: +3 points, given a reaction 🥈

3rd place: +2 points, given a reaction 🥉

4th place and above: +1 point, no special reaction

After each round, the bot displays a leaderboard, then waits 3 seconds before starting the next round.

The tournament runs for 24 rounds, then shows the final leaderboard.

Important Rules
Point‑based tournament, no elimination. All players continue every round.

If fewer than 3 players answer/complete correctly, only they receive points in order (e.g., if only 2 succeed: 1st +5, 2nd +3, no 3rd).

If nobody succeeds, no points are awarded for that round.

Each game has a ‑second timeout. After the timeout, all interactive components (buttons/modals) must be disabled and no longer accept input.

The bot must maintain game states: waiting, running, finished.

Players cannot join once the tournament has started.

Minimum players: 2.

Slash Commands & Permissions
The bot uses slash commands. Only users with admin/moderator roles (or those granted permission) may use them.

/battle start [rounds: integer] – Start a tournament with the given number of rounds (default 24). Only for authorized users.

/battle grant @user – Grant permission to a user (admin only).

/battle revoke @user – Revoke permission (admin only).

The bot stores a list of allowed user IDs in memory (or a file). Administrators (with administrator permission) are always allowed.

Game Flow
1. Player Registration (with Button)
After /battle start, the bot sends a message with a "✅ Register" button (using discord.ui.View). Every click adds the user to the player list. The button is disabled after 60 seconds or when the tournament starts.

2. Running Rounds
Each round, the bot selects the next game from the fixed order. For games that use buttons, it sends interactive components. For plain‑text games, it sends a normal message.

List of Mini‑Games (Played in Order, Repeating 4 Times)
The 6 games are played in this fixed order:
Round 1 = Game 1, Round 2 = Game 2, Round 3 = Game 3, Round 4 = Game 4, Round 5 = Game 5, Round 6 = Game 6,
Round 7 = Game 1, Round 8 = Game 2, … and so on up to 24 rounds.

Game 1 — Quick Trivia (Multiple‑Choice Buttons)
The bot sends a multiple‑choice question (e.g., "What is the capital of Indonesia?"). Below the question, 4 buttons labelled A, B, C, D appear. Players click a button to answer. The bot records the time and correctness. Only the first click per player counts (buttons should be disabled after use to prevent spam). Winners are determined by the order of correct clicks.

Game 2 — Memory Emoji Sequence (Buttons) — Length Increases Each Occurrence
This game tests visual memory. Every time this game is played during a tournament, the sequence length increases by 1. Because Game 2 appears every 6 rounds (rounds 2, 8, 14, 20), its length will grow progressively.

How it works:

The bot determines the sequence length for this round based on how many times Game 2 has been played already. First occurrence (round 2): length = 3. Second (round 8): length = 4. Third (round 14): length = 5. Fourth (round 20): length = 6.

The bot randomly picks a sequence of emojis from a predefined pool (e.g., 🍎, 🚗, 💡, 🔑, 🎸, 🐶, ☕, 📚, 🏀, 🎈). To keep it simple, the sequence should contain unique emojis (no repeats).

The bot sends a message showing the emoji sequence (e.g., 🍎 🚗 💡 for length 3). The message stays visible for 4 seconds, then the bot edits it to hide the emojis behind spoilers (using || around each emoji) or deletes it and sends a new message saying "The sequence has been hidden!".

Afterwards, the bot sends a view containing a row of buttons – one button for each emoji in the sequence, but in random order. Each button displays one of the emojis.

Players must press the buttons in the correct original order. The bot tracks each player's progress (current position) in a dictionary inside the view. Every time a player clicks a button, the bot checks if that emoji matches the expected one at their current position. If correct, their position advances; if wrong, they are marked as failed (they cannot continue, and all buttons are effectively disabled for them – by ignoring further interactions). If a player successfully presses all buttons in the correct order, they are marked as finished and their completion time is recorded.

All interactions happen within the same view. After the 20‑second timeout, the bot collects all players who finished, sorts them by completion time, and awards points to the top 3.

Game 3 — Quick Math (Plain Text)
The bot sends a simple math problem (e.g., 7 + 5 × 2 = ?). Players type the numeric answer in chat. The bot records the time of correct answers.

Game 4 — Scattergories (Plain Text, with Uniqueness Rule)
The bot picks a random letter (e.g., "R"). Players must type one object noun starting with that letter (e.g., "Radio").
Uniqueness rule: only unique answers count. If two players submit the same word, both are disqualified for that round (they cannot earn points). The bot collects all answers, filters out non‑unique ones, sorts the remaining by time, and awards points to the top 3 fastest unique answers.

Game 5 — The Bomb Defuser (Colour Buttons)
The bot sends an embed depicting a bomb with 4 coloured wires: 🔴 Red, 🔵 Blue, 🟡 Yellow, 🟢 Green. Below the embed, 4 buttons with matching colours appear. The bot randomly determines one wire as the "cut wire" (the correct one) and optionally one as the "trigger wire" (for dramatic effect – not used in scoring). Players click the colour button they believe is correct. The bot records the time of correct clicks. Buttons should be disabled after a click to prevent spamming. After the timeout (or when all players have answered), the bot announces the results and awards points to the users.

Game 6 — Who Am I? (Plain Text, Gradual Clues)
The bot gives three clues, one every 5 seconds (total 15 seconds). Players may answer at any time by typing in chat. The bot records all correct answers during the 20‑second round. Winners are determined by the order of correct answers (the first correct answer gets +5, second +3, third +2, and +1 for all correct). If no one answers correctly, no points are awarded.

Technical Implementation for Button‑Based Games
Use discord.ui.View and discord.ui.Button for games that need interactions.

For Game 2 (Memory), the view must store:

sequence: the correct list of emojis.

user_progress: a dictionary mapping user IDs to {"position": 0, "start_time": timestamp, "finished": None, "failed": False}.

When a user clicks a button, check if they are already finished/failed; if not, compare the clicked emoji with sequence[position]. If correct, advance position; if position reaches sequence length, mark finished and record completion time. If wrong, mark failed and ignore further clicks from that user.

After timeout, collect finished users, sort by completion time, award points.

For all button views, set timeout=20 and disable all children on timeout.

Leaderboard System
After each round, the bot posts an embed leaderboard:

text
🏆 LEADERBOARD (Round 3)
1. @PlayerA — 8 pts
2. @PlayerC — 6 pts
3. @PlayerB — 4 pts
...
After round 24, post the final leaderboard.

Tournament Data Structure
python
tournament = {
    "state": "waiting",          # waiting, running, finished
    "players": [],                # list of user IDs
    "points": {},                 # {user_id: points}
    "round": 0,
    "max_round": 24,
    "channel": channel_object,
    "registration_msg": None,
    "game_list": [game1_func, game2_func, game3_func, game4_func, game5_func, game6_func],  # game functions in order
    "memory_game_count": 0        # how many times Game 2 has been played (to determine sequence length)
}
For permissions:

python
allowed_users = set()  # user IDs allowed to use /battle start
# Admins (with administrator permission) are always allowed implicitly.
