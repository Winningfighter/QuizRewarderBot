import discord
import requests
import json
import os
import time
import mysql.connector
from dotenv import load_dotenv
from discord import app_commands


load_dotenv()

last_reward = {}

ALLOWED_GUILDS = os.getenv("ALLOWED_GUILDS")

if ALLOWED_GUILDS:
    ALLOWED_GUILDS = [int(g.strip()) for g in ALLOWED_GUILDS.split(",")]
else:
    ALLOWED_GUILDS = []

TOKEN = os.getenv("DISCORD_TOKEN")
UNBELIEVABOAT_TOKEN = os.getenv("UNBELIEVABOAT_TOKEN")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_PORT = os.getenv("MYSQL_PORT")
GUILD_ID = 1477933480380862585
CROSSQUIZ_BOT_ID = 1095313054390042666

db = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    port=MYSQL_PORT,
    password=MYSQL_PASSWORD,
    database=MYSQL_DATABASE
)

cursor = db.cursor(dictionary=True)

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

emoji_cache = {}

@client.event
async def on_ready():
    guild = discord.Object(id=GUILD_ID)
    synced = await tree.sync()
    print(f"Synced {len(synced)} commands to guild")
    print(f"Bot is online: {client.user}")

def load_config():
    try:
        with open("config.json", "r") as f:
            return json.load(f)
    except:
        return {}
    
def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=4)

config = load_config()


@tree.command(name="setup", description="CrossQuizRewareder Setup")
@app_commands.default_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)

    config[guild_id] = {
        "reward": 100,
        "cooldown": 10,
        "enabled": True
    }

    save_config(config)

    await interaction.response.send_message(
        "Saved Setup!", ephemeral=True
    )

    print(f"[Quiz-Rewarder] Server {interaction.guild.name} with ID {guild_id} has setup its bot.")


@tree.command(name="reward", description="Set ammount of coins per win")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(amount="Ammount of Coins")
async def reward(interaction: discord.Interaction, amount: int):
    guild_id = str(interaction.guild.id)

    if guild_id not in config:
        await interaction.response.send_message("❌ First execute /setup", ephemeral=True)
        return
    
    config[guild_id]["reward"] = amount
    save_config(config)
    
    await interaction.response.send_message(f"Reward is now {amount} Coins", ephemeral=True)
    print(f"[Quiz-Rewarder] Reward in {interaction.guild.name} is now on {amount} Coins.")
    


@tree.command(name="cooldown", description="Set cooldown between each win")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(amount="Amount of time (in seconds) between wins")
async def cooldown(interaction: discord.Interaction, amount: int):
    guild_id = str(interaction.guild.id)

    if guild_id not in config:
        await interaction.response.send_message("❌ First execute /setup", ephemeral=True)
        return
    
    config[guild_id]["cooldown"] = amount
    save_config(config)
    
    await interaction.response.send_message(f"Cooldown is now {amount} seconds", ephemeral=True)
    print(f"[Quiz-Rewarder] Cooldown in {interaction.guild.name} is now on {amount} seconds.")


@tree.command(name="enabled", description="Enable/Disable the rewarding system")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(enabled="Should the system be enabled? (True/False)")
async def enabled(interaction: discord.Interaction, enabled: bool):
    guild_id = str(interaction.guild.id)

    if guild_id not in config:
        await interaction.response.send_message("❌ First execute /setup", ephemeral=True)
        return
    
    config[guild_id]["enabled"] = enabled
    save_config(config)
    
    await interaction.response.send_message(f"Rewarding system is now {'**Enabled**' if enabled else '**Disabled**' }.", ephemeral=True)
    print(f"[Quiz-Rewarder] Rewarding system in {interaction.guild.name} is now {'**Enabled**' if enabled else '**Disabled**' }.")



@tree.command(name="showconfig", description="Show the bot configuration of this server")
@app_commands.default_permissions(administrator=True)
async def showconfig(interaction: discord.Interaction):
    guild_id = str(interaction.guild.id)
    if guild_id not in config:
        await interaction.response.send_message("❌ First execute /setup", ephemeral=True)
        return
    
    await interaction.response.send_message(
    f"📊 Config:\n"
    f"Reward: {config[guild_id]['reward']}\n"
    f"Cooldown: {config[guild_id]['cooldown']}\n"
    f"Enabled: {config[guild_id]['enabled']}",
    ephemeral=True
)
    
@tree.command(name="leaderboard")
async def leaderboard(interaction: discord.Interaction):
    view = LeaderboardView(interaction.guild.id)

    embed, _ = await build_embed(interaction.guild.id, 0, interaction)

    await interaction.response.send_message(embed=embed, view=view)


print([cmd.name for cmd in tree.get_commands()])



@client.event
async def on_raw_reaction_add(payload):
    if str(payload.emoji) != "✅":
        return
    
    if payload.guild_id is None:
        return
    
    if payload.guild_id not in ALLOWED_GUILDS:
        return

    if payload.user_id == client.user.id:
        return
    
    if payload.user_id != CROSSQUIZ_BOT_ID:
        return
    

    guild_id = str(payload.guild_id)

    if guild_id not in config:
        return
    
    if not config[guild_id]["enabled"]:
        return
    
    channel = await client.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)

    reaction = discord.utils.get(message.reactions, emoji="✅")
    if reaction is None:
        return
    
    users = [user async for user in reaction.users()]
    crossquiz_reacted = any(user.id == CROSSQUIZ_BOT_ID for user in users)

    if not crossquiz_reacted:
        return

    winner = message.author
    reward = config[guild_id]["reward"]
    cooldown = config[guild_id]["cooldown"]

    now = time.time()
    if winner.id in last_reward and now - last_reward[winner.id] < cooldown:
        return
    
    last_reward[winner.id] = now

    print(f"[Quiz-Rewarder] {winner} got {reward} coins in {guild_id}")

    add_coins(payload.guild_id, winner.id, reward)
    add_stats(payload.guild_id, winner.id, reward)

async def build_embed(guild_id, page, interaction):
    results, total = get_leaderboard(guild_id, page)

    total_pages = max(1, (total + 9) // 10)
    emoji = get_currency_emoji(guild_id)

    embed = discord.Embed(
        title="🏆 Leaderboard",
        color=0x2b2d31
    )

    text = ""

    for i, row in enumerate(results, start=1 + page * 10):
        user_id = row["user_id"]
        coins = row["coins"]

        try:
            user = await interaction.client.fetch_user(user_id)
            name = user.name
        except:
            name = f"User {user_id}"

        text += f"**{i}. {name}** • {emoji} {coins}\n"

    embed.description = text

    rank = get_user_rank(guild_id, interaction.user.id)

    embed.set_footer(
        text=f"Page {page+1}/{total_pages} • Your leaderboard rank: {rank}"
    )

    return embed, total_pages

class LeaderboardView(discord.ui.View):
    def __init__(self, guild_id):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.page = 0

    async def update(self, interaction):
        embed, total_pages = await build_embed(self.guild_id, self.page, interaction)

        self.previous.disabled = self.page == 0
        self.next.disabled = self.page >= total_pages -1

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous Page", style=discord.ButtonStyle.grey)
    async def previous(self, interaction: discord.Interaction, button):
        self.page -= 1
        await self.update(interaction)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button):
        self.page += 1
        await self.update(interaction)

def add_coins(guild_id, user_id, amount):
    url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}/users/{user_id}"
    
    headers = {
        "Authorization": UNBELIEVABOAT_TOKEN,
        "Content-Type": "application/json"
    }

    data = {
        "cash": amount
    }

    try:
        response = requests.patch(url, json=data, headers=headers)
        print(f"[Unbelievaboat API] Recieved status code {response.status_code} with message \"{response.text}\"")
    except Exception as e:
        print("[Unbelievaboat API] API Error:", e)


def add_stats(guild_id, user_id, amount):
    now = int(time.time())

    cursor.execute("""
    INSERT INTO stats (guild_id, user_id, coins, last_update)
    VALUES (%s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        coins = coins + VALUES(coins),
        last_update = VALUES(last_update)
    """, (guild_id, user_id, amount, now))

    db.commit()

def get_leaderboard(guild_id, page):
    limit = 10
    offset = page * limit

    cursor.execute("""
    SELECT user_id, coins
    FROM stats
    WHERE guild_id = %s
    ORDER BY coins DESC
    LIMIT %s OFFSET %s
    """, (guild_id, limit, offset))

    results = cursor.fetchall()

    cursor.execute("""
    SELECT COUNT(*) as total FROM stats WHERE guild_id = %s
    """, (guild_id,))

    total = cursor.fetchone()["total"]

    return results, total

def get_user_rank(guild_id, user_id):
    cursor.execute("""
    SELECT COUNT(*) + 1 as rank
    FROM stats
    WHERE guild_id = %s AND coins > (
        SELECT coins FROM stats WHERE guild_id = %s AND user_id = %s    
    )
    """, (guild_id, guild_id, user_id))

    return cursor.fetchone()["rank"]

def get_currency_emoji(guild_id):
    if guild_id in emoji_cache:
        return emoji_cache[guild_id]
    
    url = f"https://unbelievaboat.com/api/v1/guilds/{guild_id}"
    headers = {"Authorization": UNBELIEVABOAT_TOKEN}

    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        emoji = data["currency"]["emoji"]
    except:
        emoji = "🪙"

    emoji_cache[guild_id] = emoji
    return emoji


client.run(TOKEN)