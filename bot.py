import os
import json
import datetime
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
from aiohttp import web

# Setup basic intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash commands synced successfully!")

bot = MyBot()

# --- CONFIGURATION CONSTANTS ---
BOOSTED_ROLE_ID = 1564608237767098409
FREE_ROLE_ID = 1564608237767098409
PREMIUM_FILE = "premium.json"

STOCK_FILES = {
    "free_nitro": "free_nitro.txt",
    "premium_nitro": "premium_nitro.txt",
    "free_robux": "free_robux.txt",
    "premium_robux": "premium_robux.txt",
    "free_mcfa": "free_mcfa.txt",
    "premium_mcfa": "premium_mcfa.txt"
}

# --- AUTO-INITIALIZATION SAFETY ROUTINE ---
if not os.path.exists(PREMIUM_FILE):
    with open(PREMIUM_FILE, "w") as f:
        json.dump({}, f)
else:
    try:
        with open(PREMIUM_FILE, "r") as f:
            json.load(f)
    except Exception:
        with open(PREMIUM_FILE, "w") as f:
            json.dump({}, f)

for file_path in STOCK_FILES.values():
    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            pass

def load_premium_data():
    try:
        with open(PREMIUM_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_premium_data(data):
    with open(PREMIUM_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_user_premium_status(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    data = load_premium_data()
    uid_str = str(interaction.user.id)
    if uid_str in data:
        exp_time = data[uid_str]
        if exp_time == 0:
            return True
        if datetime.datetime.utcnow().timestamp() < exp_time:
            return True
        else:
            del data[uid_str]
            save_premium_data(data)
    if isinstance(interaction.user, discord.Member):
        role_ids = [role.id for role in interaction.user.roles]
        if BOOSTED_ROLE_ID in role_ids:
            return True
    return False

def has_free_access(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    if isinstance(interaction.user, discord.Member):
        role_ids = [role.id for role in interaction.user.roles]
        if FREE_ROLE_ID in role_ids:
            return True
    return False

def count_stock(filename):
    if not os.path.exists(filename):
        return 0
    with open(filename, "r") as f:
        return len([line for line in f.readlines() if line.strip()])

def get_stock_item(filename):
    if not os.path.exists(filename):
        return None
    with open(filename, "r") as f:
        lines = f.readlines()
    cleaned_lines = [l.strip() for l in lines if l.strip()]
    if not cleaned_lines:
        return None
    
    pulled_item = cleaned_lines[0]
    
    with open(filename, "w") as f:
        for line in cleaned_lines[1:]:
            f.write(f"{line}\n")
    return pulled_item

def append_stock_item(filename, item):
    with open(filename, "a") as f:
        f.write(f"{item.strip()}\n")

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name}")

# --- COMMANDS ---
@bot.tree.command(name="dmall", description="Send a DM to all members of this server.")
@app_commands.describe(message="The announcement message to send.")
async def dmall(interaction: discord.Interaction, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an Administrator to run this command.", ephemeral=True)
        return
    await interaction.response.send_message("⏳ Starting mass DM process...", ephemeral=True)
    success_count, fail_count = 0, 0
    for member in interaction.guild.members:
        if member.bot:
            continue
        try:
            await member.send(message)
            success_count += 1
            await asyncio.sleep(4)
        except Exception:
            fail_count += 1
    print(f"Mass DM Complete. Sent: {success_count} | Failed: {fail_count}")

@bot.tree.command(name="givepremium", description="Grant premium generator access to a user.")
@app_commands.describe(user="The user receiving premium status.", days="Days of premium. Use 0 for infinite.")
async def givepremium(interaction: discord.Interaction, user: discord.User, days: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an Administrator to run this command.", ephemeral=True)
        return
    data = load_premium_data()
    uid_str = str(user.id)
    if days <= 0:
        data[uid_str] = 0
        duration_text = "Infinite"
    else:
        expiration = datetime.datetime.utcnow() + datetime.timedelta(days=days)
        data[uid_str] = expiration.timestamp()
        duration_text = f"{days} Day(s)"
    save_premium_data(data)
    await interaction.response.send_message(f"✅ Successfully granted **{duration_text} Premium** access to {user.mention}.", ephemeral=False)

@bot.tree.command(name="addstock", description="Add an item into a specific generator stock file.")
@app_commands.choices(tier=[
    app_commands.Choice(name="Free Tier", value="free"),
    app_commands.Choice(name="Premium Tier", value="premium")
], type=[
    app_commands.Choice(name="Nitro", value="nitro"),
    app_commands.Choice(name="Robux", value="robux"),
    app_commands.Choice(name="Minecraft Full Access", value="mcfa")
])
async def addstock(interaction: discord.Interaction, tier: app_commands.Choice[str], type: app_commands.Choice[str], code: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an Administrator to run this command.", ephemeral=True)
        return
    file_key = f"{tier.value}_{type.value}"
    filename = STOCK_FILES[file_key]
    append_stock_item(filename, code)
    await interaction.response.send_message(f"✅ Successfully appended item to `{filename}` stock list.", ephemeral=True)

@bot.tree.command(name="stock", description="Check current code stock amounts across all available categories.")
async def stock(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📦 Generator Active Stock Status",
        description="Current number of working rewards available in real-time:",
        color=discord.Color.from_rgb(0, 255, 170)
    )
    embed.add_field(name="✨ Premium Nitro", value=f"`{count_stock(STOCK_FILES['premium_nitro'])} item(s)`", inline=True)
    embed.add_field(name="🆓 Free Nitro", value=f"`{count_stock(STOCK_FILES['free_nitro'])} item(s)`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="🎮 Premium Robux", value=f"`{count_stock(STOCK_FILES['premium_robux'])} item(s)`", inline=True)
    embed.add_field(name="🆓 Free Robux", value=f"`{count_stock(STOCK_FILES['free_robux'])} item(s)`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    embed.add_field(name="🟩 Premium MCFA", value=f"`{count_stock(STOCK_FILES['premium_mcfa'])} item(s)`", inline=True)
    embed.add_field(name="🆓 Free MCFA", value=f"`{count_stock(STOCK_FILES['free_mcfa'])} item(s)`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=True)
    
    avatar_url = interaction.user.display_avatar.url if interaction.user.display_avatar else None
    embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=avatar_url)
    await interaction.response.send_message(embed=embed, ephemeral=False)

@bot.tree.command(name="gen", description="Generate a code/account reward from available stock.")
@app_commands.choices(tier=[
    app_commands.Choice(name="Free Tier", value="free"),
    app_commands.Choice(name="Premium Tier", value="premium")
], type=[
    app_commands.Choice(name="Nitro", value="nitro"),
    app_commands.Choice(name="Robux", value="robux"),
    app_commands.Choice(name="Minecraft Full Access", value="mcfa")
])
async def gen(interaction: discord.Interaction, tier: app_commands.Choice[str], type: app_commands.Choice[str]):
    if tier.value == "premium" and not is_user_premium_status(interaction):
        await interaction.response.send_message("❌ This is a **Premium Tier** command. Upgrade or boost the server to access!", ephemeral=True)
        return
    if tier.value == "free" and not has_free_access(interaction):
        await interaction.response.send_message("❌ You do not have the verified Free access role to use this generator.", ephemeral=True)
        return

    file_key = f"{tier.value}_{type.value}"
    filename = STOCK_FILES[file_key]
    reward = get_stock_item(filename)

    if not reward:
        await interaction.response.send_message(f"🚨 Out of stock! The `{tier.name}` category for `{type.name}` has no items left.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎁 Reward Generated Successfully!",
        description=f"Here is your generated {tier.name} - **{type.name}** reward item.",
        color=discord.Color.from_rgb(0, 190, 255)
    )
    embed.add_field(name="🔑 Your Code / Account Login:", value=f"`{reward}`", inline=False)
    embed.set_footer(text="Do not share this text with others.")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- AIOHTTP PING WEB SERVICE ---
async def handle(request):
    return web.Response(text="Web Service Port Verification Active")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
