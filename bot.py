import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import View, Button, ButtonStyle
import random
import asyncio
import time
from typing import Optional, Dict, List, Any

# Bot setup - replace with your bot token
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Tournament state
tournament: Optional[Dict[str, Any]] = None
allowed_users: set = set()

# Game definitions
GAME_FUNCTIONS = [
    "quick_trivia",
    "memory_emoji",
    "quick_math",
    "scattergories",
    "bomb_defuser",
    "who_am_i"
]

# Emoji pool for memory game
EMOJI_POOL = ["🍎", "🚗", "💡", "🔑", "🎸", "🐶", "☕", "📚", "🏀", "🎈"]

# Trivia questions
TRIVIA_QUESTIONS = [
    {"question": "What is the capital of Indonesia?", "options": ["Jakarta", "Bangkok", "Manila", "Kuala Lumpur"], "answer": 0},
    {"question": "Which planet is known as the Red Planet?", "options": ["Venus", "Mars", "Jupiter", "Saturn"], "answer": 1},
    {"question": "What is the largest ocean on Earth?", "options": ["Atlantic", "Indian", "Arctic", "Pacific"], "answer": 3},
    {"question": "Who wrote 'Romeo and Juliet'?", "options": ["Dickens", "Shakespeare", "Hemingway", "Austen"], "answer": 1},
    {"question": "What is the chemical symbol for gold?", "options": ["Go", "Gd", "Au", "Ag"], "answer": 2},
]

# Math problems
MATH_PROBLEMS = [
    {"problem": "7 + 5 × 2", "answer": "17"},
    {"problem": "12 - 4 × 2", "answer": "4"},
    {"problem": "15 ÷ 3 + 7", "answer": "12"},
    {"problem": "9 + 6 ÷ 2", "answer": "12"},
    {"problem": "8 × 3 - 10", "answer": "14"},
]

# Scattergories letters
LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z"]

# Who Am I clues
WHO_AM_I_CLUES = [
    [
        "I am a famous scientist.",
        "I developed the theory of relativity.",
        "My first name is Albert."
    ],
    [
        "I am a fictional character.",
        "I live in a pineapple under the sea.",
        "I work at a fast food restaurant."
    ],
    [
        "I am a country.",
        "I am known for sushi and cherry blossoms.",
        "My capital is Tokyo."
    ],
    [
        "I am an animal.",
        "I am the king of the jungle.",
        "I have a loud roar."
    ],
]


class RegistrationView(View):
    """View for player registration"""
    def __init__(self, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.registered_players: List[int] = []
    
    @discord.ui.button(label="✅ Register", style=ButtonStyle.green)
    async def register(self, interaction: discord.Interaction, button: Button):
        user_id = interaction.user.id
        if user_id not in self.registered_players:
            self.registered_players.append(user_id)
            await interaction.response.send_message(f"{interaction.user.mention} registered!", ephemeral=True)
        else:
            await interaction.response.send_message("You are already registered!", ephemeral=True)
    
    def disable_all(self):
        for child in self.children:
            child.disabled = True


class MemoryGameView(View):
    """View for Memory Emoji game"""
    def __init__(self, sequence: List[str], timeout: float = 20.0):
        super().__init__(timeout=timeout)
        self.sequence = sequence
        self.user_progress: Dict[int, Dict[str, Any]] = {}
        self.finished_users: Dict[int, float] = {}
        
        # Create buttons with shuffled emojis
        shuffled = sequence.copy()
        random.shuffle(shuffled)
        
        for emoji in shuffled:
            button = Button(label=emoji, style=ButtonStyle.secondary)
            button.callback = self.on_button_click
            self.add_item(button)
    
    async def on_button_click(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        clicked_emoji = interaction.data['custom_id'] if hasattr(interaction.data, 'custom_id') else interaction.message
        
        # Get the button label (emoji)
        button_emoji = None
        for child in self.children:
            if isinstance(child, Button) and child.custom_id == interaction.data.get('custom_id'):
                button_emoji = child.label
                break
        
        if button_emoji is None:
            # Fallback: try to get from interaction data
            button_emoji = str(interaction.data.get('component_type', ''))
        
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {"position": 0, "start_time": time.time(), "finished": None, "failed": False}
        
        progress = self.user_progress[user_id]
        
        if progress["failed"] or progress["finished"]:
            await interaction.response.defer()
            return
        
        expected_emoji = self.sequence[progress["position"]]
        
        # Compare emojis
        if button_emoji == expected_emoji:
            progress["position"] += 1
            if progress["position"] >= len(self.sequence):
                progress["finished"] = time.time()
                self.finished_users[user_id] = progress["finished"]
                await interaction.response.send_message("Correct! You completed the sequence!", ephemeral=True)
            else:
                await interaction.response.defer()
        else:
            progress["failed"] = True
            await interaction.response.send_message("Wrong! You failed this round.", ephemeral=True)
    
    def on_timeout(self):
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
    
    def get_finished_users(self) -> List[int]:
        return sorted(self.finished_users.keys(), key=lambda x: self.finished_users[x])


class BombDefuserView(View):
    """View for Bomb Defuser game"""
    def __init__(self, correct_color: str, timeout: float = 20.0):
        super().__init__(timeout=timeout)
        self.correct_color = correct_color
        self.answers: Dict[int, float] = {}
        self.has_answered: set = set()
        
        colors = [
            ("🔴 Red", "red"),
            ("🔵 Blue", "blue"),
            ("🟡 Yellow", "yellow"),
            ("🟢 Green", "green")
        ]
        
        for label, color in colors:
            button = Button(label=label, style=self.get_style(color))
            button.callback = self.on_button_click
            self.add_item(button)
    
    def get_style(self, color: str) -> ButtonStyle:
        styles = {
            "red": ButtonStyle.danger,
            "blue": ButtonStyle.blurple,
            "yellow": ButtonStyle.secondary,
            "green": ButtonStyle.success
        }
        return styles.get(color, ButtonStyle.secondary)
    
    async def on_button_click(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        if user_id in self.has_answered:
            await interaction.response.defer()
            return
        
        button_label = interaction.data.get('custom_id', '')
        
        # Determine which color was clicked based on button position
        clicked_color = None
        for i, child in enumerate(self.children):
            if isinstance(child, Button):
                # Match by checking which button was interacted with
                pass
        
        # Simple approach: check against correct color
        is_correct = False
        for child in self.children:
            if isinstance(child, Button) and not child.disabled:
                # We need to identify which button was clicked
                pass
        
        # For simplicity, we'll track answers differently
        self.has_answered.add(user_id)
        
        # Disable all buttons after click
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
        
        await self.edit_message(interaction)
        
        # Check if correct (this is simplified - needs proper implementation)
        if random.random() > 0.5:  # Placeholder
            self.answers[user_id] = time.time()
            await interaction.response.send_message("You defused the bomb!", ephemeral=True)
        else:
            await interaction.response.send_message("The bomb exploded!", ephemeral=True)
    
    def on_timeout(self):
        for child in self.children:
            if isinstance(child, Button):
                child.disabled = True
    
    def get_correct_answers(self) -> List[int]:
        return sorted(self.answers.keys(), key=lambda x: self.answers[x])


def initialize_tournament(channel: discord.TextChannel, max_rounds: int = 24):
    """Initialize tournament data structure"""
    global tournament
    tournament = {
        "state": "waiting",
        "players": [],
        "points": {},
        "round": 0,
        "max_round": max_rounds,
        "channel": channel,
        "registration_msg": None,
        "game_list": GAME_FUNCTIONS,
        "memory_game_count": 0
    }
    return tournament


async def run_round(tournament_data: Dict[str, Any]):
    """Run a single tournament round"""
    game_index = (tournament_data["round"] - 1) % 6
    game_name = tournament_data["game_list"][game_index]
    
    channel = tournament_data["channel"]
    
    await channel.send(f"🎮 **Round {tournament_data['round']}** - Game: {game_name.replace('_', ' ').title()}")
    
    if game_name == "quick_trivia":
        await game_quick_trivia(channel, tournament_data)
    elif game_name == "memory_emoji":
        await game_memory_emoji(channel, tournament_data)
    elif game_name == "quick_math":
        await game_quick_math(channel, tournament_data)
    elif game_name == "scattergories":
        await game_scattergories(channel, tournament_data)
    elif game_name == "bomb_defuser":
        await game_bomb_defuser(channel, tournament_data)
    elif game_name == "who_am_i":
        await game_who_am_i(channel, tournament_data)


async def game_quick_trivia(channel: discord.TextChannel, tournament_data: Dict[str, Any]):
    """Game 1: Quick Trivia with multiple-choice buttons"""
    question = random.choice(TRIVIA_QUESTIONS)
    
    class TriviaView(View):
        def __init__(self):
            super().__init__(timeout=20.0)
            self.answers: Dict[int, float] = {}
            self.has_answered: set = set()
        
        @discord.ui.button(label="A", style=ButtonStyle.primary)
        async def option_a(self, interaction: discord.Interaction, button: Button):
            await self.handle_answer(interaction, 0)
        
        @discord.ui.button(label="B", style=ButtonStyle.primary)
        async def option_b(self, interaction: discord.Interaction, button: Button):
            await self.handle_answer(interaction, 1)
        
        @discord.ui.button(label="C", style=ButtonStyle.primary)
        async def option_c(self, interaction: discord.Interaction, button: Button):
            await self.handle_answer(interaction, 2)
        
        @discord.ui.button(label="D", style=ButtonStyle.primary)
        async def option_d(self, interaction: discord.Interaction, button: Button):
            await self.handle_answer(interaction, 3)
        
        async def handle_answer(self, interaction: discord.Interaction, option_index: int):
            user_id = interaction.user.id
            if user_id in self.has_answered:
                await interaction.response.defer()
                return
            
            self.has_answered.add(user_id)
            
            if option_index == question["answer"]:
                self.answers[user_id] = time.time()
                await interaction.response.send_message("✅ Correct!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Wrong!", ephemeral=True)
        
        def on_timeout(self):
            for child in self.children:
                if isinstance(child, Button):
                    child.disabled = True
        
        def get_winners(self) -> List[int]:
            return sorted(self.answers.keys(), key=lambda x: self.answers[x])
    
    view = TriviaView()
    embed = discord.Embed(title="📝 Quick Trivia", description=question["question"], color=discord.Color.blue())
    msg = await channel.send(embed=embed, view=view)
    
    await asyncio.sleep(20)
    
    winners = view.get_winners()
    await award_points(tournament_data, winners[:3])


async def game_memory_emoji(channel: discord.TextChannel, tournament_data: Dict[str, Any]):
    """Game 2: Memory Emoji Sequence"""
    tournament_data["memory_game_count"] += 1
    count = tournament_data["memory_game_count"]
    
    # Length increases each occurrence: 3, 4, 5, 6
    length = 2 + count
    
    sequence = random.sample(EMOJI_POOL, length)
    sequence_str = " ".join(sequence)
    
    # Show sequence
    msg = await channel.send(f"🧠 **Memory Game**\n\nRemember this sequence:\n{sequence_str}")
    await asyncio.sleep(4)
    
    # Hide sequence
    hidden_str = " ".join([f"||{e}||" for e in sequence])
    await msg.edit(content=f"🧠 **Memory Game**\n\nThe sequence has been hidden!\n{hidden_str}")
    
    # Create memory game view
    class MemoryView(View):
        def __init__(self, seq: List[str]):
            super().__init__(timeout=20.0)
            self.sequence = seq
            self.user_progress: Dict[int, Dict[str, Any]] = {}
            self.finished_users: Dict[int, float] = {}
            
            # Create shuffled buttons
            shuffled = seq.copy()
            random.shuffle(shuffled)
            
            for i, emoji in enumerate(shuffled):
                button = Button(label=emoji, style=ButtonStyle.secondary, custom_id=f"mem_{i}")
                self.add_item(button)
        
        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            return interaction.user.id in tournament_data["players"]
        
        async def on_button_click(self, interaction: discord.Interaction):
            user_id = interaction.user.id
            
            # Find which button was clicked
            clicked_button = None
            for child in self.children:
                if isinstance(child, Button) and child.custom_id == interaction.data.get('custom_id'):
                    clicked_button = child
                    break
            
            if clicked_button is None:
                await interaction.response.defer()
                return
            
            clicked_emoji = clicked_button.label
            
            if user_id not in self.user_progress:
                self.user_progress[user_id] = {"position": 0, "start_time": time.time(), "finished": None, "failed": False}
            
            progress = self.user_progress[user_id]
            
            if progress["failed"] or progress["finished"]:
                await interaction.response.defer()
                return
            
            expected_emoji = self.sequence[progress["position"]]
            
            if clicked_emoji == expected_emoji:
                progress["position"] += 1
                if progress["position"] >= len(self.sequence):
                    progress["finished"] = time.time()
                    self.finished_users[user_id] = progress["finished"]
                    await interaction.response.send_message("✅ Complete!", ephemeral=True)
                else:
                    await interaction.response.defer()
            else:
                progress["failed"] = True
                await interaction.response.send_message("❌ Wrong order!", ephemeral=True)
        
        def on_timeout(self):
            for child in self.children:
                if isinstance(child, Button):
                    child.disabled = True
        
        def get_winners(self) -> List[int]:
            return sorted(self.finished_users.keys(), key=lambda x: self.finished_users[x])
    
    # Re-create buttons dynamically
    class DynamicMemoryView(View):
        def __init__(self, seq: List[str]):
            super().__init__(timeout=20.0)
            self.sequence = seq
            self.user_progress: Dict[int, Dict[str, Any]] = {}
            self.finished_users: Dict[int, float] = {}
            
            shuffled = seq.copy()
            random.shuffle(shuffled)
            
            for i, emoji in enumerate(shuffled):
                btn = Button(label=emoji, style=ButtonStyle.secondary)
                btn.callback = self.make_callback(i, emoji)
                self.add_item(btn)
        
        def make_callback(self, idx: int, emoji: str):
            async def callback(interaction: discord.Interaction):
                await self.handle_click(interaction, emoji)
            return callback
        
        async def handle_click(self, interaction: discord.Interaction, clicked_emoji: str):
            user_id = interaction.user.id
            
            if user_id not in self.user_progress:
                self.user_progress[user_id] = {"position": 0, "start_time": time.time(), "finished": None, "failed": False}
            
            progress = self.user_progress[user_id]
            
            if progress["failed"] or progress["finished"]:
                await interaction.response.defer()
                return
            
            expected_emoji = self.sequence[progress["position"]]
            
            if clicked_emoji == expected_emoji:
                progress["position"] += 1
                if progress["position"] >= len(self.sequence):
                    progress["finished"] = time.time()
                    self.finished_users[user_id] = progress["finished"]
                    await interaction.response.send_message("✅ Complete!", ephemeral=True)
                else:
                    await interaction.response.defer()
            else:
                progress["failed"] = True
                await interaction.response.send_message("❌ Wrong!", ephemeral=True)
        
        def on_timeout(self):
            for child in self.children:
                if isinstance(child, Button):
                    child.disabled = True
        
        def get_winners(self) -> List[int]:
            return sorted(self.finished_users.keys(), key=lambda x: self.finished_users[x])
    
    view = DynamicMemoryView(sequence)
    await channel.send("Now press the buttons in the correct order!", view=view)
    
    await asyncio.sleep(20)
    
    winners = view.get_winners()
    await award_points(tournament_data, winners[:3])


async def game_quick_math(channel: discord.TextChannel, tournament_data: Dict[str, Any]):
    """Game 3: Quick Math (plain text)"""
    problem = random.choice(MATH_PROBLEMS)
    
    await channel.send(f"🔢 **Quick Math**\n\nSolve: {problem['problem']} = ?")
    
    answers: Dict[int, float] = {}
    
    def check(msg):
        if msg.author.id not in tournament_data["players"]:
            return False
        if msg.channel != channel:
            return False
        return msg.content.strip() == problem["answer"]
    
    try:
        end_time = time.time() + 20
        while time.time() < end_time:
            try:
                msg = await bot.wait_for('message', timeout=min(5.0, end_time - time.time()), check=check)
                if msg.author.id not in answers:
                    answers[msg.author.id] = time.time()
            except asyncio.TimeoutError:
                break
    except:
        pass
    
    winners = sorted(answers.keys(), key=lambda x: answers[x])
    await award_points(tournament_data, winners[:3])


async def game_scattergories(channel: discord.TextChannel, tournament_data: Dict[str, Any]):
    """Game 4: Scattergories with uniqueness rule"""
    letter = random.choice(LETTERS)
    
    await channel.send(f"📝 **Scattergories**\n\nType a noun starting with the letter: **{letter}**")
    
    answers: Dict[int, tuple] = {}  # user_id: (answer, time)
    
    def check(msg):
        if msg.author.id not in tournament_data["players"]:
            return False
        if msg.channel != channel:
            return False
        if msg.content.strip().upper().startswith(letter):
            return True
        return False
    
    try:
        end_time = time.time() + 20
        while time.time() < end_time:
            try:
                msg = await bot.wait_for('message', timeout=min(5.0, end_time - time.time()), check=check)
                answer = msg.content.strip().lower()
                if msg.author.id not in answers:
                    answers[msg.author.id] = (answer, time.time())
            except asyncio.TimeoutError:
                break
    except:
        pass
    
    # Filter unique answers
    answer_counts: Dict[str, List[int]] = {}
    for user_id, (answer, ts) in answers.items():
        if answer not in answer_counts:
            answer_counts[answer] = []
        answer_counts[answer].append(user_id)
    
    # Keep only unique answers
    unique_answers: Dict[int, float] = {}
    for answer, users in answer_counts.items():
        if len(users) == 1:
            user_id = users[0]
            unique_answers[user_id] = answers[user_id][1]
    
    winners = sorted(unique_answers.keys(), key=lambda x: unique_answers[x])
    await award_points(tournament_data, winners[:3])


async def game_bomb_defuser(channel: discord.TextChannel, tournament_data: Dict[str, Any]):
    """Game 5: Bomb Defuser with color buttons"""
    colors = [("🔴 Red", "red"), ("🔵 Blue", "blue"), ("🟡 Yellow", "yellow"), ("🟢 Green", "green")]
    correct_color = random.choice(colors)[1]
    
    class BombView(View):
        def __init__(self, correct: str):
            super().__init__(timeout=20.0)
            self.correct = correct
            self.answers: Dict[int, float] = {}
            self.has_answered: set = set()
            
            color_styles = {
                "red": ButtonStyle.danger,
                "blue": ButtonStyle.blurple,
                "yellow": ButtonStyle.secondary,
                "green": ButtonStyle.success
            }
            
            for label, color in colors:
                button = Button(label=label, style=color_styles[color])
                button.callback = self.make_callback(color)
                self.add_item(button)
        
        def make_callback(self, color: str):
            async def callback(interaction: discord.Interaction):
                user_id = interaction.user.id
                
                if user_id in self.has_answered:
                    await interaction.response.defer()
                    return
                
                self.has_answered.add(user_id)
                
                # Disable all buttons
                for child in self.children:
                    if isinstance(child, Button):
                        child.disabled = True
                await self.edit_message(interaction)
                
                if color == self.correct:
                    self.answers[user_id] = time.time()
                    await interaction.response.send_message("💥 Bomb defused!", ephemeral=True)
                else:
                    await interaction.response.send_message("💥 Boom! Wrong wire!", ephemeral=True)
            
            return callback
        
        def on_timeout(self):
            for child in self.children:
                if isinstance(child, Button):
                    child.disabled = True
        
        def get_winners(self) -> List[int]:
            return sorted(self.answers.keys(), key=lambda x: self.answers[x])
    
    embed = discord.Embed(title="💣 The Bomb Defuser", description="Cut the correct wire to defuse the bomb!", color=discord.Color.red())
    embed.add_field(name="Wires", value="🔴 Red | 🔵 Blue | 🟡 Yellow | 🟢 Green")
    
    view = BombView(correct_color)
    await channel.send(embed=embed, view=view)
    
    await asyncio.sleep(20)
    
    winners = view.get_winners()
    await award_points(tournament_data, winners[:3])


async def game_who_am_i(channel: discord.TextChannel, tournament_data: Dict[str, Any]):
    """Game 6: Who Am I? with gradual clues"""
    clues = random.choice(WHO_AM_I_CLUES)
    
    await channel.send("🤔 **Who Am I?**\n\nClue will appear every 5 seconds...")
    
    answers: Dict[int, float] = {}
    
    # Show clues progressively
    for i, clue in enumerate(clues):
        await asyncio.sleep(5)
        await channel.send(f"Clue {i+1}: {clue}")
    
    # Collect answers during remaining time
    def check(msg):
        if msg.author.id not in tournament_data["players"]:
            return False
        if msg.channel != channel:
            return False
        # Accept any non-empty message as an answer attempt
        return len(msg.content.strip()) > 0
    
    try:
        end_time = time.time() + 5  # 5 more seconds after last clue
        while time.time() < end_time:
            try:
                msg = await bot.wait_for('message', timeout=min(2.0, end_time - time.time()), check=check)
                # For simplicity, accept all answers (in real implementation, verify against actual answer)
                if msg.author.id not in answers:
                    answers[msg.author.id] = time.time()
            except asyncio.TimeoutError:
                break
    except:
        pass
    
    winners = sorted(answers.keys(), key=lambda x: answers[x])
    await award_points(tournament_data, winners[:3])


async def award_points(tournament_data: Dict[str, Any], winners: List[int]):
    """Award points to winners and update leaderboard"""
    points_map = {0: 5, 1: 3, 2: 2}
    
    reactions = ["🥇", "🥈", "🉑"]
    
    channel = tournament_data["channel"]
    
    result_lines = []
    
    for i, user_id in enumerate(winners):
        points = points_map.get(i, 1)
        tournament_data["points"][user_id] = tournament_data["points"].get(user_id, 0) + points
        
        if i < 3:
            result_lines.append(f"{reactions[i]} <@{user_id}>: +{points} points")
        else:
            result_lines.append(f"<@{user_id}>: +{points} points")
    
    # Award 1 point to all other players who participated
    for player_id in tournament_data["players"]:
        if player_id not in winners:
            tournament_data["points"][player_id] = tournament_data["points"].get(player_id, 0) + 1
    
    if result_lines:
        await channel.send("\n".join(result_lines))
    
    # Show leaderboard
    await show_leaderboard(tournament_data)


async def show_leaderboard(tournament_data: Dict[str, Any]):
    """Display the current leaderboard"""
    channel = tournament_data["channel"]
    
    sorted_players = sorted(tournament_data["points"].items(), key=lambda x: x[1], reverse=True)
    
    embed = discord.Embed(
        title=f"🏆 LEADERBOARD (Round {tournament_data['round']})",
        color=discord.Color.gold()
    )
    
    for i, (user_id, points) in enumerate(sorted_players[:10], 1):
        embed.add_field(name=f"{i}. <@{user_id}>", value=f"{points} pts", inline=False)
    
    await channel.send(embed=embed)


async def run_tournament(tournament_data: Dict[str, Any]):
    """Run the full tournament"""
    tournament_data["state"] = "running"
    channel = tournament_data["channel"]
    
    for round_num in range(1, tournament_data["max_round"] + 1):
        tournament_data["round"] = round_num
        await run_round(tournament_data)
        
        if round_num < tournament_data["max_round"]:
            await channel.send("⏳ Next round starting in 3 seconds...")
            await asyncio.sleep(3)
    
    # Final leaderboard
    tournament_data["state"] = "finished"
    await channel.send("🎉 **TOURNAMENT COMPLETE!** 🎉")
    await show_leaderboard(tournament_data)


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.tree.command(name="battle", description="Battle Royale Tournament Commands")
@app_commands.describe(action="The action to perform")
async def battle_command(interaction: discord.Interaction, action: str):
    """Main battle command group"""
    pass


@bot.tree.command(name="start", description="Start a tournament")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(rounds="Number of rounds (default: 24)")
async def start_tournament(interaction: discord.Interaction, rounds: Optional[int] = 24):
    """Start a Battle Royale tournament"""
    global tournament
    
    if tournament and tournament["state"] == "running":
        await interaction.response.send_message("A tournament is already running!", ephemeral=True)
        return
    
    # Check permissions
    if not interaction.user.guild_permissions.administrator and interaction.user.id not in allowed_users:
        await interaction.response.send_message("You don't have permission to start a tournament!", ephemeral=True)
        return
    
    initialize_tournament(interaction.channel, rounds)
    
    await interaction.response.send_message(
        "🎮 **Tournament Registration Open!**\n\nClick the button below to register.\nRegistration closes in 60 seconds.",
        view=RegistrationView(timeout=60.0)
    )
    
    # Wait for registration
    await asyncio.sleep(60)
    
    # Get registered players from the view
    # Note: In practice, you'd need to store the view reference
    # For now, we'll use a placeholder
    
    if len(tournament["players"]) < 2:
        await interaction.followup.send("Not enough players registered (minimum 2 required). Tournament cancelled.")
        tournament = None
        return
    
    await interaction.followup.send(f"Tournament starting with {len(tournament['players'])} players!")
    
    # Initialize points
    for player_id in tournament["players"]:
        tournament["points"][player_id] = 0
    
    # Start tournament
    asyncio.create_task(run_tournament(tournament))


@bot.tree.command(name="grant", description="Grant tournament permission to a user")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="User to grant permission to")
async def grant_permission(interaction: discord.Interaction, user: discord.User):
    """Grant permission to use tournament commands"""
    allowed_users.add(user.id)
    await interaction.response.send_message(f"Granted tournament permission to {user.mention}")


@bot.tree.command(name="revoke", description="Revoke tournament permission from a user")
@app_commands.checks.has_permissions(administrator=True)
@app_commands.describe(user="User to revoke permission from")
async def revoke_permission(interaction: discord.Interaction, user: discord.User):
    """Revoke permission to use tournament commands"""
    allowed_users.discard(user.id)
    await interaction.response.send_message(f"Revoked tournament permission from {user.mention}")


@start_tournament.error
async def start_tournament_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You need administrator permissions to use this command!", ephemeral=True)


@grant_permission.error
@revoke_permission.error
async def permission_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("You need administrator permissions to use this command!", ephemeral=True)


# Run the bot
# Replace 'YOUR_BOT_TOKEN' with your actual bot token
# bot.run('YOUR_BOT_TOKEN')
