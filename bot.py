import os
import asyncio
import discord
from discord import app_commands
from discord.ext import commands

# Setup intents (Must enable Server Members in Developer Portal)
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Syncs slash commands globally
        await self.tree.sync()
        print("Slash commands synced successfully!")

bot = MyBot()

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    print("Bot is online and ready!")

@bot.tree.command(name="dmall", description="Send a DM to all members of this server.")
@app_commands.describe(message="The announcement message to send.")
async def dmall(interaction: discord.Interaction, message: str):
    # Restrict to Administrators only
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You must be an Administrator to use this command.", ephemeral=True)
        return

    await interaction.response.send_message("⏳ Starting mass DM process... This will take some time due to rate limits.", ephemeral=True)
    
    success_count = 0
    fail_count = 0

    # Loop through everyone in the server
    for member in interaction.guild.members:
        if member.bot:
            continue  # Skip other bots
        
        try:
            await member.send(message)
            success_count += 1
            # CRUCIAL: 4-second delay prevents Discord from banning the bot for spamming
            await asyncio.sleep(4)
        except discord.Forbidden:
            # Fails if the user has private DMs turned off or blocked the bot
            fail_count += 1
        except Exception as e:
            fail_count += 1

    print(f"Mass DM Finished. Sent: {success_count} | Failed: {fail_count}")

# Render uses environment variables to keep your token safe
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
