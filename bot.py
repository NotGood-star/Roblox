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

# --- HELPER FUNCTIONS FOR PREMIUM EXPIRATION & STOCK ---
def load_premium_data():
    if not os.path.exists(PREMIUM_FILE):
        return {}
    try:
        with open(PREMIUM_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_premium_data(data):
    with open(PREMIUM_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_user_premium_status(interaction: discord.Interaction) -> bool:
    """Checks if the user qualifies for the premium high-tier stock."""
    if interaction.user.guild_permissions.administrator:
        return True

    data = load_premium_data()
    uid_str = str(interaction.user.id)
    if uid_str in data:
        exp_time = data[uid_str]
        if exp_time == 0:  # Infinite
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
    """Checks if the user has at least the free tier access."""
    if isinstance(interaction.user, discord.Member):
        role_ids = [role.id for role in interaction.user.roles]
        if FREE_ROLE_ID in role_ids:
            return True
    return False

def get_stock_item(filename):
    """Pulls the first line from a text stock file and removes it forever."""
    if not os.path.exists(filename):
        return None
    
    with open(filename, "r") as f:
        lines = f.readlines()
        
    if not lines:
        return None
    
    # Strip whitespace out of the pulled reward code
    pulled_item = lines[0].strip()
    
    # Immediately overwrite the file removing that specific item
    with open(filename, "w") as f:
        f.writelines(lines[1:])
        
    return pulled_item

def count_stock(filename):
    """Safely calculates the active line length inside a specific stock text file."""
    if not os.path.exists(filename):
        return 0
    with open(filename, "r") as f:
        return len([line for line in f.readlines() if line.strip()])


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


# --- ADMIN PRIVILEGE COMMANDS ---

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


@bot.tree.command(name="addstock", description="Add a new reward item line directly to a targeted stock tier.")
@app_commands.describe(
    item_type="Select the target item group.",
    tier="Select if this item lands inside Free or Premium storage.",
    code="The raw voucher token or full alt configuration credentials string."
)
@app_commands.choices(item_type=[
    app_commands.Choice(name="Nitro", value="nitro"),
    app_commands.Choice(name="Robux", value="robux"),
    app_commands.Choice(name="Minecraft (MCFA)", value="mcfa")
], tier=[
    app_commands.Choice(name="Free Stock", value="free"),
    app_commands.Choice(name="Premium Stock", value="premium")
])
async def addstock(interaction: discord.Interaction, item_type: app_commands.Choice[str], tier: app_commands.Choice[str], code: str):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an Administrator to run this command.", ephemeral=True)
        return

    filename = f"{tier.value}_{item_type.value}.txt"
    
    with open(filename, "a") as f:
        f.write(f"{code.strip()}\n")
        
    await interaction.response.send_message(f"📦 Successfully appended new item to **{filename}**!", ephemeral=True)


# --- GENERAL AVAILABILITY USER COMMANDS ---

@bot.tree.command(name="stock", description="Check the absolute item balance remaining inside all stock tiers.")
async def stock(interaction: discord.Interaction):
    # Public availability allows all members to execute this command visible to everyone
    embed = discord.Embed(
        title="📦 Current Generator Live Stock", 
        color=discord.Color.from_rgb(114, 137, 218),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="✨ Free Nitro", value=f"`{count_stock('free_nitro.txt')} left`", inline=True)
    embed.add_field(name="👑 Premium Nitro", value=f"`{count_stock('premium_nitro.txt')} left`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False) # Visual spacing break
    embed.add_field(name="🎮 Free Robux", value=f"`{count_stock('free_robux.txt')} left`", inline=True)
    embed.add_field(name="💎 Premium Robux", value=f"`{count_stock('premium_robux.txt')} left`", inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)
    embed.add_field(name="🟩 Free MCFA", value=f"`{count_stock('free_mcfa.txt')} left`", inline=True)
    embed.add_field(name="⚔️ Premium MCFA", value=f"`{count_stock('premium_mcfa.txt')} left`", inline=True)
    
    embed.set_footer(text="Stock counters update in real-time upon redemption claims.")
    await interaction.response.send_message(embed=embed, ephemeral=False)


# --- TIERED GENERATOR REDEMPTION LOOPS ---

@bot.tree.command(name="nitro", description="Generate a real Discord Nitro link from tiered stock.")
async def nitro(interaction: discord.Interaction):
    is_premium = is_user_premium_status(interaction)
    is_free = has_free_access(interaction)

    if not is_premium and not is_free:
        await interaction.response.send_message("❌ Access Denied. You need a generator role or active premium.", ephemeral=True)
        return

    filename = "premium_nitro.txt" if is_premium else "free_nitro.txt"
    tier_name = "Premium" if is_premium else "Free"

    reward = get_stock_item(filename)
    if not reward:
        await interaction.response.send_message(f"❌ Sorry, the {tier_name} Nitro generator is currently out of stock!", ephemeral=True)
        return

    link = f"https://discord.gift{reward}" if "discord.gift" not in reward else reward
    embed = discord.Embed(
        title=f"✨ {tier_name} Nitro Claimed", 
        description=f"Here is your working reward:\n`{link}`", 
        color=discord.Color.from_rgb(255, 115, 250)
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="robux", description="Generate a real Robux code from tiered stock.")
async def robux(interaction: discord.Interaction):
    is_premium = is_user_premium_status(interaction)
    is_free = has_free_access(interaction)

    if not is_premium and not is_free:
        await interaction.response.send_message("❌ Access Denied. You need a generator role or active premium.", ephemeral=True)
        return

    filename = "premium_robux.txt" if is_premium else "free_robux.txt"
    tier_name = "Premium" if is_premium else "Free"

    reward = get_stock_item(filename)
    if not reward:
        await interaction.response.send_message(f"❌ Sorry, the {tier_name} Robux generator is currently out of stock!", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🎮 {tier_name} Robux Code Claimed", 
        description=f"Your working Robux Card PIN:\n**`{reward}`**", 
        color=discord.Color.from_rgb(0, 162, 255)
