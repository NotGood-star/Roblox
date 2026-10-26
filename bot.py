import os
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

@bot.event
async def on_ready():
    print(f"Logged in successfully as {bot.user.name}")

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

# --- CRUCIAL RENDER PORT BINDING ROUTINE ---
async def handle_ping(request):
    return web.Response(text="Bot webserver is active!")

async def start_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render assigns the required port number dynamically via the PORT variable
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Web server successfully bound and listening on port {port}")

async def main():
    # Force the port scanner to satisfy Render immediately
    await start_server()
    
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_TOKEN is missing from your Environment Variables.")
        return
        
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
