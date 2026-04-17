import discord
import requests
import json
import os
import time
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
GUILD_ID = 1477933480380862585
CROSSQUIZ_BOT_ID = 1095313054390042666

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


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

print([cmd.name for cmd in tree.get_commands()])

@client.event
async def on_raw_reaction_add(payload):
    if str(payload.emoji) != "✅":
        return
    
    if payload.guild_id not in ALLOWED_GUILDS:
        return

    if payload.user_id == client.user.id:
        return
    
    if payload.user_id != CROSSQUIZ_BOT_ID:
        return
    
    if payload.guild_id is None:
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
    


client.run(TOKEN)