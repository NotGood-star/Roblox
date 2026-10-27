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
    # Admins automatically get premium access
    if interaction.user.guild_permissions.administrator:
        return True

    # Check custom database premium status
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

    # Check for Boosted role status
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
    """Pulls the first line from a text stock file and removes it."""
    if not os.path.exists(filename):
        return None
    
    with open(filename, "r") as f:
        lines = f.readlines()
        
    if not lines:
        return None
    
    pulled_item = lines[0].strip()
    
    with open(filename, "w") as f:
        f.writelines(lines[1:])
        
    return pulled_item


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


# --- TIERED GENERATOR COMMANDS ---

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
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="mcfa", description="Generate a working Minecraft account from tiered stock.")
async def mcfa(interaction: discord.Interaction):
    is_premium = is_user_premium_status(interaction)
    is_free = has_free_access(interaction)

    if not is_premium and not is_free:
        await interaction.response.send_message("❌ Access Denied. You need a generator role or active premium.", ephemeral=True)
        return

    filename = "premium_mcfa.txt" if is_premium else "free_mcfa.txt"
    tier_name = "Premium" if is_premium else "Free"

    reward = get_stock_item(filename)
    if not reward:
        await interaction.response.send_message(f"❌ Sorry, the {tier_name} Minecraft generator is currently out of stock!", ephemeral=True)
        return

    embed = discord.Embed(
        title=f"🟩 {tier_name} Minecraft Full Access Combo Claimed", 
        description=f"Your active login credential:\n**`{reward}`**", 
        color=discord.Color.from_rgb(85, 255, 85)
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# --- CRUCIAL RENDER PORT BINDING ROUTINE ---
async def handle_ping(request):
    return web.Response(text="Bot webserver is active!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web server successfully bound and listening on port {port}")

async def main():
    await start_server()
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_TOKEN is missing from your Environment Variables.")
        return
        
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
