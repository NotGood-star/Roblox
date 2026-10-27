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

# File mappings to keep stock paths clean
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

# --- HELPER FUNCTIONS FOR PREMIUM EXPIRATION & STOCK ---
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
    """Checks if the user qualifies for premium high-tier stock commands."""
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
    """Checks if the user has free tier role access."""
    if isinstance(interaction.user, discord.Member):
        role_ids = [role.id for role in interaction.user.roles]
        if FREE_ROLE_ID in role_ids:
            return True
    return False

def count_stock(filename):
    """Returns the line count of a file securely."""
    if not os.path.exists(filename):
        return 0
    with open(filename, "r") as f:
        return len([line for line in f.readlines() if line.strip()])

def get_stock_item(filename):
    """Pulls the top line from a text stock file and removes it permanently."""
    if not os.path.exists(filename):
        return None
    
    with open(filename, "r") as f:
        lines = f.readlines()
        
    cleaned_lines = [l for l in lines if l.strip()]
    if not cleaned_lines:
        return None
    
    pulled_item = cleaned_lines[0].strip()
    
    with open(filename, "w") as f:
        f.writelines(cleaned_lines[1:])
        
    return pulled_item

def append_stock_item(filename, item):
    """Appends a new line item to a stock text file safely."""
    with open(filename, "a") as f:
        f.write(f"{item}\n")


@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name}")


# --- YOUR ORIGINAL DM ALL COMMAND (UNTOUCHED) ---
@bot.tree.command(name="dmall", description="Send a DM to all members of this server.")
@app_commands.describe(message="The announcement message to send.")
async def dmall(interaction: discord.Interaction, message: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an Administrator to run this command.", ephemeral=True)
        return

    await interaction.response.send_message("⏳ Starting mass DM process...", ephemeral=True)
    
    success_count = 0
    fail_count = 0

    for member in interaction.guild.members:
        if member.bot:
            continue
        try:
            await member.send(message)
            success_count += 1
            await asyncio.sleep(4)  # Safety delay to prevent Discord anti-spam bans
        except discord.Forbidden:
            fail_count += 1
        except Exception:
            fail_count += 1

    print(f"Mass DM Complete. Sent: {success_count} | Failed: {fail_count}")


# --- GIVEPREMIUM ADMIN COMMAND ---
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


# --- STOCK MANAGEMENT COMMANDS ---

@bot.tree.command(name="addstock", description="Add an item into a specific generator stock file.")
@app_commands.describe(
    tier="Choose between Free or Premium file tracking.",
    type="The specific reward category.",
    code="The reward code or account login line string."
)
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
    
    embed.set_footer(text="Rewards are automatically consumed on generation.")
    await interaction.response.send_message(embed=embed, ephemeral=False)


# --- INDIVIDUAL PREMIUM GENERATORS ---

@bot.tree.command(name="premium_nitro", description="Claim a premium tier Nitro link.")
async def premium_nitro(interaction: discord.Interaction):
    if not is_user_premium_status(interaction):
        await interaction.response.send_message("❌ Access Denied. You need premium tracking or the Boosted role.", ephemeral=True)
        return
    reward = get_stock_item(STOCK_FILES["premium_nitro"])
    if not reward:
        await interaction.response.send_message("❌ Out of Stock! Premium Nitro files are empty.", ephemeral=True)
        return
    link = f"https://discord.gift{reward}" if "discord.gift" not in reward else reward
    await interaction.response.send_message(f"✨ **Premium Nitro Claimed:**\n`{link}`", ephemeral=True)

@bot.tree.command(name="premium_robux", description="Claim a premium tier Robux code.")
async def premium_robux(interaction: discord.Interaction):
    if not is_user_premium_status(interaction):
        await interaction.response.send_message("❌ Access Denied. You need premium tracking or the Boosted role.", ephemeral=True)
        return
    reward = get_stock_item(STOCK_FILES["premium_robux"])
    if not reward:
        await interaction.response.send_message("❌ Out of Stock! Premium Robux files are empty.", ephemeral=True)
        return

