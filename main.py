import os
from flask import Flask, request, redirect, session, jsonify 
import discord
from discord.ext import commands
from discord.ui import Button, View
from discord import app_commands
import asyncio
import random
import re
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from discord.ui import Select, View
from googletrans import Translator, LANGUAGES
import qrcode
from io import BytesIO
import string
import matplotlib.pyplot as plt
from googletrans import Translator
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from discord import FFmpegPCMAudio
import requests
import aiohttp
import json
import os
from flask import Flask, request, jsonify
from threading import Thread
from googleapiclient.discovery import build
from captcha.image import ImageCaptcha
from io import BytesIO
from twitchAPI.twitch import Twitch
from PIL import Image  # Add this import
import sympy as sp
from discord import app_commands, ButtonStyle
import json
from async_timeout import timeout
from functools import partial

intents = discord.Intents.default()
intents.members = True
intents.voice_states = True
intents.typing = False
intents.presences = False
intents.messages = True
intents.guilds = True
intents.message_content = True
intents.guild_messages = True  # Enable guild message events
intents.guilds = True  # Enable guild even
intents.members = True  # Enable member intents
intents.guilds = True
intents.voice_states = True  # Enable voice state intents
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

YOUR_BOT_OWNER_ID = 1022181741848428654
@bot.event
async def on_ready():
    await bot.tree.sync()
    check_mutes.start()
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('Velion is now online!')


# Moderation Commands
@bot.tree.command(name="ban", description="Bans a user from the server.")
@app_commands.describe(user="The user to ban", reason="Reason for banning the user")
async def ban(interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("You don't have permission to ban members.", ephemeral=True)
        return

    await interaction.guild.ban(user, reason=reason)
    embed = discord.Embed(
        title="User Banned",
        description=f"{user.mention} has been banned.",
        color=discord.Color.red()
    )
    embed.add_field(name="Reason", value=reason)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="kick", description="Kicks a user from the server.")
@app_commands.describe(user="The user to kick", reason="Reason for kicking the user")
async def kick(interaction: discord.Interaction, user: discord.User, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("You don't have permission to kick members.", ephemeral=True)
        return

    await interaction.guild.kick(user, reason=reason)
    embed = discord.Embed(
        title="User Kicked",
        description=f"{user.mention} has been kicked.",
        color=discord.Color.orange()
    )
    embed.add_field(name="Reason", value=reason)
    await interaction.response.send_message(embed=embed)


def load_mutes():
    try:
        with open('mutes.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_mutes(mutes):
    with open('mutes.json', 'w') as f:
        json.dump(mutes, f, indent=4)

mutes = load_mutes()

@bot.tree.command(name="mute", description="Mutes a user for a specified duration.")
async def mute(interaction: discord.Interaction, user: discord.Member, duration: int, reason: str):
    await interaction.response.defer()  # Defer the interaction to give more time for processing

    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if not mute_role:
        mute_role = await interaction.guild.create_role(name="Muted")

    for channel in interaction.guild.channels:
        await channel.set_permissions(mute_role, send_messages=False, speak=False)

    await user.add_roles(mute_role)

    end_time = datetime.utcnow() + timedelta(minutes=duration)
    mutes[str(user.id)] = {"end_time": end_time.isoformat(), "guild_id": interaction.guild.id}
    save_mutes(mutes)

    # Embed for the server
    embed = discord.Embed(
        title="User Muted",
        description=f"{user.mention} has been muted for {duration} minutes.",
        color=discord.Color.purple()
    )
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)

    if interaction.guild.icon:
        embed.set_footer(text=f"Muted by {interaction.guild.name}", icon_url=interaction.guild.icon.url)
    else:
        embed.set_footer(text=f"Muted by {interaction.guild.name}")

    await interaction.followup.send(embed=embed)  # Use followup after deferring the interaction

    # DM to the muted user
    dm_embed = discord.Embed(
        title="You Have Been Muted",
        description=f"You have been muted in {interaction.guild.name} for {duration} minutes.",
        color=discord.Color.red()
    )
    dm_embed.add_field(name="Reason", value=reason, inline=False)
    dm_embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
    dm_embed.add_field(name="Mute Duration", value=f"{duration} minutes", inline=False)

    if interaction.guild.icon:
        dm_embed.set_thumbnail(url=interaction.guild.icon.url)

    dm_embed.set_footer(text=f"Muted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

    try:
        await user.send(embed=dm_embed)
    except discord.Forbidden:
        await interaction.followup.send(f"Could not send DM to {user.mention}.", ephemeral=True)

@bot.tree.command(name="unmute", description="Unmutes a muted user.")
async def unmute(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.defer()

    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
    if mute_role in user.roles:
        await user.remove_roles(mute_role)

        if str(user.id) in mutes:
            del mutes[str(user.id)]
            save_mutes(mutes)

        embed = discord.Embed(
            title="User Unmuted",
            description=f"{user.mention} has been unmuted.",
            color=discord.Color.green()
        )

        if interaction.guild.icon:
            embed.set_footer(text=f"Unmuted by {interaction.guild.name}", icon_url=interaction.guild.icon.url)
        else:
            embed.set_footer(text=f"Unmuted by {interaction.guild.name}")

        await interaction.followup.send(embed=embed)

        # DM to the unmuted user
        dm_embed = discord.Embed(
            title="You Have Been Unmuted",
            description=f"You have been unmuted in {interaction.guild.name}.",
            color=discord.Color.green()
        )

        if interaction.guild.icon:
            dm_embed.set_thumbnail(url=interaction.guild.icon.url)

        dm_embed.set_footer(text=f"Unmuted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

        try:
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.followup.send(f"Could not send DM to {user.mention}.", ephemeral=True)
    else:
        await interaction.followup.send(f"{user.mention} is not muted.", ephemeral=True)

@tasks.loop(minutes=1)
async def check_mutes():
    current_time = datetime.utcnow()
    to_unmute = []

    for user_id, mute_data in mutes.items():
        end_time = datetime.fromisoformat(mute_data["end_time"])
        if current_time >= end_time:
            guild = bot.get_guild(mute_data["guild_id"])
            
            if guild is None:  # Handle the case where the guild is not found
                to_unmute.append(user_id)
                continue  # Skip to the next user

            user = guild.get_member(int(user_id))
            if user:
                mute_role = discord.utils.get(guild.roles, name="Muted")
                if mute_role in user.roles:
                    await user.remove_roles(mute_role)

                    # Notify the server and the user
                    embed = discord.Embed(
                        title="User Unmuted",
                        description=f"{user.mention} has been automatically unmuted.",
                        color=discord.Color.green()
                    )
                    if guild.icon:
                        embed.set_footer(text=f"Unmuted by {guild.name}", icon_url=guild.icon.url)
                    else:
                        embed.set_footer(text=f"Unmuted by {guild.name}")

                    channel = guild.system_channel or discord.utils.get(guild.text_channels, name='general')
                    if channel:
                        await channel.send(embed=embed)

                    dm_embed = discord.Embed(
                        title="You Have Been Unmuted",
                        description=f"You have been automatically unmuted in {guild.name}.",
                        color=discord.Color.green()
                    )

                    if guild.icon:
                        dm_embed.set_thumbnail(url=guild.icon.url)

                    dm_embed.set_footer(text=f"Unmuted at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")

                    try:
                        await user.send(embed=dm_embed)
                    except discord.Forbidden:
                        pass

            to_unmute.append(user_id)

    for user_id in to_unmute:
        del mutes[user_id]

    save_mutes(mutes)




@bot.tree.command(name="meme", description="Get a random meme")
async def meme(interaction: discord.Interaction):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://meme-api.com/gimme") as response:
                if response.status == 200:
                    data = await response.json()
                    meme_url = data["url"]
                    embed = discord.Embed(title="Here's a meme for you!", color=discord.Color.random())
                    embed.set_image(url=meme_url)
                    await interaction.response.send_message(embed=embed)
                else:
                    await interaction.response.send_message("Failed to retrieve a meme. The API might be down or returning an unexpected response.")
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {str(e)}")


# Error handling
@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    try:
        await interaction.followup.send("An error occurred while processing the command.Please try again or later.", ephemeral=True)
    except discord.errors.NotFound:
        # If interaction is expired, log the error instead
        print(f"Error: {error}")

afk_file = "afk_users.json"

# Load AFK data from JSON
def load_afk_data():
    if os.path.exists(afk_file):
        with open(afk_file, "r") as file:
            return json.load(file)
    return {}

# Save AFK data to JSON
def save_afk_data(data):
    with open(afk_file, "w") as file:
        json.dump(data, file, indent=4)

# Initialize the AFK users dictionary from the JSON file
afk_users = load_afk_data()

@bot.tree.command(name="afk", description="Set your status as AFK.")
async def afk(interaction: discord.Interaction, *, reason: str = "AFK"):
    afk_users[str(interaction.user.id)] = reason
    save_afk_data(afk_users)
    
    embed = discord.Embed(
        title="🚶 AFK",
        description=f"{interaction.user.mention} is now AFK.\nReason: **{reason}**",
        color=discord.Color.purple()
    )

    # Check if the guild has an icon before setting it
    if interaction.guild.icon:
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.guild.icon.url)
    else:
        embed.set_footer(text=f"Requested by {interaction.user.name}")

    await interaction.response.send_message(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Check if the message mentions someone who is AFK
    for mention in message.mentions:
        if str(mention.id) in afk_users:
            reason = afk_users[str(mention.id)]
            embed = discord.Embed(
                title="🚶 AFK",
                description=f"{mention.mention} is currently AFK.\nReason: **{reason}**",
                color=discord.Color.orange()
            )
            embed.set_footer(text="AFK System", icon_url=message.guild.icon.url if message.guild.icon else None)
            await message.channel.send(embed=embed)

    # If the author is AFK, remove their AFK status when they send a message
    if str(message.author.id) in afk_users:
        del afk_users[str(message.author.id)]
        save_afk_data(afk_users)
        
        embed = discord.Embed(
            title="🚶 Back from AFK",
            description=f"{message.author.mention} is no longer AFK.",
            color=discord.Color.green()
        )
        embed.set_footer(text="AFK System", icon_url=message.guild.icon.url if message.guild.icon else None)
        await message.channel.send(embed=embed)

    # Continue processing commands after the AFK check
    await bot.process_commands(message)

@bot.tree.command(name="warn", description="Issues a warning to a user.")
@app_commands.describe(user="The user to warn", reason="Reason for the warning")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to warn members.", ephemeral=True)
        return

    embed = discord.Embed(
        title="User Warned",
        description=f"{user.mention} has been warned.",
        color=discord.Color.yellow()
    )
    embed.add_field(name="Reason", value=reason)
    await interaction.response.send_message(embed=embed)

active_pings = {}

@bot.tree.command(name='ping', description='Shows the latency of the bot and server')
async def ping(interaction: discord.Interaction):
    user_id = interaction.user.id

    if user_id in active_pings:
        await interaction.response.send_message("Please wait until the current ping check finishes before using the command again.", ephemeral=True)
        return

    active_pings[user_id] = True

    # Initial response with the first latency calculation
    await interaction.response.send_message(embed=create_ping_embed(bot, interaction))
    
    # Fetch the initial response message to edit it later
    message = await interaction.original_response()

    # Update the message every second for 30 seconds
    for _ in range(30):
        await message.edit(embed=create_ping_embed(bot, interaction))
        await asyncio.sleep(1)  # Update every second

    # Remove the user from the active pings list after 30 seconds
    del active_pings[user_id]

def create_ping_embed(bot, interaction):
    bot_latency = round(bot.latency * 100, 2)  # Convert latency to milliseconds
    
    
    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.purple())
    embed.add_field(name="Bot Latency", value=f"{bot_latency} ms")
    embed.add_field(name="API Latency", value=f"{round(interaction.client.latency * 1000, 2)} ms")
    return embed




@bot.tree.command(name="giveawaystart", description="Start a giveaway")
@app_commands.describe(prize="The prize for the giveaway", instruction="Instructions for the giveaway", time="Time in hours")

async def giveawaystart(interaction: discord.Interaction, prize: str, instruction: str, time: int):
    guild_id = str(interaction.guild_id)
    giveaway_role = discord.utils.get(interaction.guild.roles, name="Giveaway")
    """
    Start a new giveaway with the given prize and instructions.

    Args:
        prize (str): The prize for the giveaway.
        instruction (str): Instructions for the giveaway.
        time (int): The time in hours for the giveaway to last.

    Returns:
        None
    """
    # Get the guild ID from the interaction (the server where the command was used)
    if not giveaway_role:

    # Check if the "Giveaway" role already exists in the guild
    # If it doesn't, create it
        giveaway_role = await interaction.guild.create_role(name="Giveaway")

    embed = discord.Embed(title="🎉 Giveaway 🎉", description=instruction, color=discord.Color.purple())
    embed.add_field(name="Prize", value=prize, inline=False)
    # Create an embed message with the prize, instructions, and time
    embed = discord.Embed(title=" Giveaway ", description=instruction, color=discord.Color.purple())
    embed.add_field(name="Ends in", value=f"{time} hour(s)", inline=False)

    button = Button(label="Enter Giveaway", style=discord.ButtonStyle.green)
    
    participants = []

    async def button_callback(interaction: discord.Interaction):
        if giveaway_role not in interaction.user.roles:
            await interaction.user.add_roles(giveaway_role)
            participants.append(interaction.user)
            await interaction.response.send_message("You have entered the giveaway!", ephemeral=True)
        else:
            await interaction.response.send_message("You are already entered in the giveaway.", ephemeral=True)

    button.callback = button_callback

    view = View()
    view.add_item(button)
    
    await interaction.response.send_message(embed=embed, view=view)
    await asyncio.sleep(time * 3600)

    if participants:
        winner = random.choice(participants)
        await interaction.channel.send(f"Congratulations {winner.mention}, you won the giveaway for **{prize}**!")
    else:
        await interaction.channel.send("No one entered the giveaway.")

    for user in participants:
        await user.remove_roles(giveaway_role)

# /Define command
@bot.tree.command(name="define", description="Define a word")
@app_commands.describe(word="The word to define")
async def define(interaction: discord.Interaction, word: str):
    api_url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()[0]
        definition = data['meanings'][0]['definitions'][0]['definition']
        part_of_speech = data['meanings'][0]['partOfSpeech']
        example = data['meanings'][0]['definitions'][0].get('example', 'No example available')

        embed = discord.Embed(title=f"Definition of {word}", color=discord.Color.purple())
        embed.add_field(name="Part of Speech", value=part_of_speech, inline=False)
        embed.add_field(name="Definition", value=definition, inline=False)
        embed.add_field(name="Example", value=example, inline=False)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Word not found!", ephemeral=True)

@bot.tree.command(name="purge", description="Clears a specified number of messages in a channel.")
@app_commands.describe(amount="Number of messages to delete")
async def clear(interaction: discord.Interaction, amount: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You don't have permission to clear messages.", ephemeral=True)
        return

    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"Cleared {amount} messages.", ephemeral=True)


# User Management Commands
@bot.tree.command(name="role", description="Assigns or removes a role from a user.")
@app_commands.describe(user="The user to modify", role="The role to assign or remove")
async def role(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("You don't have permission to manage roles.", ephemeral=True)
        return

    if role in user.roles:
        await user.remove_roles(role)
        await interaction.response.send_message(f"Removed {role.name} from {user.mention}.")
    else:
        await user.add_roles(role)
        await interaction.response.send_message(f"Assigned {role.name} to {user.mention}.")


@bot.tree.command(name="nickname", description="Changes a user's nickname.")
@app_commands.describe(user="The user to change the nickname", nickname="The new nickname")
async def nickname(interaction: discord.Interaction, user: discord.Member, nickname: str):
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("You don't have permission to manage nicknames.", ephemeral=True)
        return

    await user.edit(nick=nickname)
    await interaction.response.send_message(f"Changed nickname for {user.mention} to {nickname}.")


@bot.tree.command(name="avatar", description="Displays a user's avatar.")
@app_commands.describe(user="The user whose avatar you want to display")
async def avatar(interaction: discord.Interaction, user: discord.Member):
    embed = discord.Embed(
        title=f"{user}'s Avatar",
        color=discord.Color.purple()
    )
    embed.set_image(url=user.avatar.url)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="userinfo", description="Shows information about a user.")
@app_commands.describe(user="The user to get information about")
async def userinfo(interaction: discord.Interaction, user: discord.Member):
    embed = discord.Embed(
        title=f"User Information - {user}",
        color=discord.Color.teal()
    )
    embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="ID", value=user.id)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d"))
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="serverinfo", description="Displays information about the server.")
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title=f"Server Information - {guild.name}",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Server ID", value=guild.id)
    embed.add_field(name="Owner", value=guild.owner.mention)
    embed.add_field(name="Member Count", value=guild.member_count)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%Y-%m-%d"))
    await interaction.response.send_message(embed=embed)

def load_lockdown_data():
    if os.path.exists('lockdown.json'):
        try:
            with open('lockdown.json', 'r') as f:
                data = json.load(f)
                # Convert 'lockdown_end' back to datetime object
                for guild_id, info in data.items():
                    if isinstance(info, dict) and 'lockdown_end' in info:
                        info['lockdown_end'] = datetime.fromisoformat(info['lockdown_end'])
                return data
        except json.JSONDecodeError:
            print("Error: lockdown.json is corrupted. Resetting the file.")
            return {}
    else:
        return {}

# Global variable to store lockdown data
lockdown_data = {}

# Save lockdown data to JSON file
def save_lockdown_data(data):
    # Ensure that the 'lockdown_end' is a datetime object
    if isinstance(data['lockdown_end'], str):
        data['lockdown_end'] = datetime.fromisoformat(data['lockdown_end'])
    data['lockdown_end'] = data['lockdown_end'].isoformat()

    # Save the data to a file
    with open("lockdown_data.json", "w") as f:
        json.dump(data, f)

# Lockdown command
@bot.tree.command(name="lockdown", description="Lock down the server for a specified duration.")
@app_commands.describe(duration="Duration in hours", reason="Reason for lockdown")
async def lockdown(interaction: discord.Interaction, duration: int, reason: str):
    # Only allow administrators to use this command
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Store the lockdown data
    global lockdown_data
    lockdown_data = {
        "duration": duration,
        "reason": reason,
        "lockdown_end": datetime.now() + timedelta(hours=duration)
    }

    # Create the confirmation buttons
    class ConfirmView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=180)

        @discord.ui.button(label="Confirm", style=discord.ButtonStyle.danger)
        async def confirm_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.defer()  # Defer to prevent unknown interaction error

            # Check if the user is an administrator
            if interaction.user.guild_permissions.administrator:
                for channel in interaction.guild.channels:
                    overwrite = discord.PermissionOverwrite(send_messages=False)
                    await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

                # Send confirmation message in embed
                embed = discord.Embed(
                    title="🔒 Server Lockdown",
                    description=f"The server has been locked down for {duration} hours for the reason: {reason}.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)

                # Disable the buttons after confirmation
                button.disabled = True
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)

                # Save the lockdown data
                save_lockdown_data(lockdown_data)
            else:
                await interaction.followup.send("You do not have permission to confirm this action.", ephemeral=True)

        @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
        async def cancel_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.send_message("Lockdown cancelled.", ephemeral=True)

            # Disable buttons after cancellation
            button.disabled = True
            for item in self.children:
                item.disabled = True
            await interaction.message.edit(view=self)

    # Send the confirmation message with buttons
    await interaction.response.send_message(
        f"Are you sure you want to lock down the server for {duration} hours for the reason: {reason}?",
        view=ConfirmView()
    )

# Error handling for the bot
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.errors.NotFound):
        return  # Ignore NotFound error
    await interaction.followup.send("An error occurred while processing the command.", ephemeral=True)

# Remove lockdown command
@bot.tree.command(name="rlockdown", description="Remove the server lockdown.")
async def rlockdown(interaction: discord.Interaction):
    # Only allow administrators to use this command
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    # Reset the permissions in all channels
    for channel in interaction.guild.channels:
        overwrite = discord.PermissionOverwrite(send_messages=True)
        await channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    # Send a confirmation message
    await interaction.response.send_message("The lockdown has been removed.", ephemeral=True)



@bot.tree.command(name="serveranalytics", description="Get server analytics and information (Premium Feature)")
async def analytics(interaction: discord.Interaction):
    if not is_premium(interaction.guild.id, interaction.user.id):
        await interaction.response.send_message("This is a premium feature.", ephemeral=True)
        return

    guild = interaction.guild
    owner = await bot.fetch_user(guild.owner_id)

    # Collect server information
    banned_members = [entry async for entry in guild.bans()]
    joined_count = premium_data["analytics"].get(str(guild.id), {}).get("joined", 0)
    left_count = premium_data["analytics"].get(str(guild.id), {}).get("left", 0)
    stayed_count = guild.member_count

    # Create Embed
    embed = discord.Embed(title=f"{guild.name}'s Information", color=discord.Color.blue())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else discord.Embed.Empty)

    # About Section
    embed.add_field(name="About", value=f"**Name:** {guild.name}\n**ID:** {guild.id}\n**Owner:** {owner} ({owner.id})\n**Created At:** {guild.created_at.strftime('%Y-%m-%d')}\n**Members:** {guild.member_count}\n**Banned:** {len(banned_members)}", inline=False)
    
    # Extras Section
    embed.add_field(name="Extras", value=f"**Verification Level:** {guild.verification_level.name}\n**Upload Limit:** {guild.filesize_limit / (1024 * 1024):.2f} MB\n**Inactive Channel:** {guild.afk_channel}\n**Inactive Timeout:** {guild.afk_timeout // 60} mins\n**System Messages Channel:** {guild.system_channel}\n**System Welcome Messages:** {'Enabled' if guild.system_channel_flags.join_notifications else 'Disabled'}\n**System Boost Messages:** {'Enabled' if guild.system_channel_flags.premium_subscriptions else 'Disabled'}\n**Default Notifications:** {guild.default_notifications.name}\n**Explicit Media Content Filter:** {guild.explicit_content_filter.name}\n**2FA Requirement:** {'Enabled' if guild.mfa_level else 'Disabled'}\n**Boost Bar Enabled:** {'Enabled' if guild.premium_tier else 'Disabled'}", inline=False)
    
    # Features Section
    embed.add_field(name="Features", value=f"**Application Command Permissions V2:** {'✅' if 'APPLICATION_COMMAND_PERMISSIONS_V2' in guild.features else '❌'}", inline=False)
    
    # Premium Status
    embed.add_field(name="Premium Status", value="✅" if is_premium(str(guild.id), interaction.user.id) else "❌", inline=False)

    # Member Stats
    embed.add_field(name="Member Stats", value=f"**Joined:** {joined_count}\n**Left:** {left_count}\n**Stayed:** {stayed_count}", inline=False)

    await interaction.response.send_message(embed=embed)


class CaptchaGame:
    def __init__(self):
        self.image = ImageCaptcha(width=280, height=90)
        self.text = self._generate_text()

    def _generate_text(self):
        letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        return ''.join(random.choice(letters) for i in range(6))

    def generate_image(self):
        data = self.image.generate(self.text)
        image = Image.open(data)
        byte_arr = BytesIO()
        image.save(byte_arr, format='PNG')
        byte_arr.seek(0)
        return byte_arr

if os.path.exists("scores.json"):
    with open("scores.json", "r") as f:
        scores = json.load(f)
else:
    scores = {}

# Function to save scores to JSON
def save_scores():
    with open("scores.json", "w") as f:
        json.dump(scores, f, indent=4)

# Define the API URL
TRIVIA_API_URL = "https://opentdb.com/api.php"

# Helper function to get a trivia question
async def get_trivia_question():
    async with aiohttp.ClientSession() as session:
        async with session.get(TRIVIA_API_URL, params={"amount": 1, "type": "multiple"}) as response:
            data = await response.json()
            if data["response_code"] != 0:
                return None, None, None

            question_data = data["results"][0]
            question = question_data["question"]
            correct_answer = question_data["correct_answer"]
            all_answers = question_data["incorrect_answers"] + [correct_answer]
            random.shuffle(all_answers)
            return question, correct_answer, all_answers

# Trivia command
@bot.tree.command(name='trivia', description='Starts a trivia game')
async def start_trivia(interaction: discord.Interaction):
    question, correct_answer, all_answers = await get_trivia_question()
    if question:
        options = {
            "Option 1": all_answers[0],
            "Option 2": all_answers[1],
            "Option 3": all_answers[2],
            "Option 4": all_answers[3],
        }

        embed = discord.Embed(title="Trivia Time!", description=question, color=discord.Color.purple())
        for option, answer in options.items():
            embed.add_field(name=option, value=answer, inline=False)

        await interaction.response.send_message(embed=embed)

        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel

        try:
            msg = await bot.wait_for('message', timeout=30.0, check=check)
            selected_option = msg.content.strip()
            if selected_option in options:
                selected_answer = options[selected_option]
                if selected_answer == correct_answer:
                    scores[interaction.user.id] = scores.get(interaction.user.id, 0) + 1
                    save_scores()
                    await interaction.followup.send(f"Correct! Your score is now {scores[interaction.user.id]}.")
                else:
                    await interaction.followup.send(f"Wrong! The correct answer was: {correct_answer}.")
            else:
                await interaction.followup.send("Invalid option selected. Please use one of the provided options.")
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to answer!")
    else:
        await interaction.response.send_message("Failed to fetch trivia question. Please try again later.")

# Scores command
@bot.tree.command(name="scores", description="Check your game scores")
async def check_scores(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    if user_id in scores:
        score = scores[user_id]
        embed = discord.Embed(title="Your Scores", description=f"You have won {score} trivia games.", color=discord.Color.purple())
    else:
        embed = discord.Embed(title="Your Scores", description="You haven't played any trivia games yet!", color=discord.Color.purple())

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="translate", description="Translate text to another language")
@app_commands.describe(text="The text to translate", target_language="The target language code")
async def translate(interaction: discord.Interaction, text: str, target_language: str):


    translator = Translator()
    translated = translator.translate(text, dest=target_language)
    embed = discord.Embed(title="Translation", color=discord.Color.purple())
    embed.add_field(name="Original", value=text)
    embed.add_field(name="Translated", value=translated.text)
    embed.add_field(name="Language", value=translated.dest)

    await interaction.response.send_message(embed=embed)
@bot.tree.command(name="captcha", description="Start a CAPTCHA game")
@app_commands.describe(difficulty="Select CAPTCHA difficulty: easy, medium, hard")
async def captcha(interaction: discord.Interaction, difficulty: str):
    if difficulty.lower() not in ["easy", "medium", "hard"]:
        await interaction.response.send_message("Invalid difficulty. Choose from easy, medium, or hard.")
        return

    captcha_game = CaptchaGame()
    captcha_image = captcha_game.generate_image()
    difficulty_multiplier = {"easy": 1, "medium": 2, "hard": 3}
    timeout = 30 * difficulty_multiplier[difficulty.lower()]

    await interaction.response.send_message(
        f"Solve this CAPTCHA (difficulty: {difficulty}). You have {timeout} seconds.",
        file=discord.File(fp=captcha_image, filename="captcha.png")
    )

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for('message', timeout=timeout, check=check)
        if msg.content.strip() == captcha_game.text:
            await msg.reply("Correct! You've solved the CAPTCHA.")
        else:
            await msg.reply("Incorrect. Better luck next time!")
    except asyncio.TimeoutError:
        await interaction.followup.send(f"Time's up! The correct answer was: {captcha_game.text}")

@bot.tree.command(name="roles", description="Lists all roles in the server.")
async def roles(interaction: discord.Interaction):
    roles = ", ".join([role.name for role in interaction.guild.roles])
    embed = discord.Embed(
        title="Server Roles",
        description=roles,
        color=discord.Color.dark_blue()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have the required permissions to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("An error occurred while processing the command.", ephemeral=True)
        print(f"Error: {error}")

@bot.tree.command(name="generate_qr", description="Generate a QR code for a given link")
async def generate_qr(interaction: discord.Interaction, link: str):
    """
    Generates a QR code for the provided link and sends it as an embedded image.
    """
    # Generate the QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert the QR code image to bytes
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # Create an embed message with the QR code image
    embed = discord.Embed(
        title="QR Code Generator",
        description=f"Here is the QR code for [this link]({link}):",
        color=discord.Color.purple()
    )
    file = discord.File(buf, filename="qrcode.png")
    embed.set_image(url="attachment://qrcode.png")

    # Define a button that links to the original URL
    class LinkButton(discord.ui.View):
        def __init__(self, link: str):
            super().__init__()
            self.add_item(discord.ui.Button(label="Go to Link", style=discord.ButtonStyle.link, url=link))

    # Send the embed with the QR code and the button
    await interaction.response.send_message(embed=embed, file=file, view=LinkButton(link))
@bot.tree.command(name="create_role", description="Creates a role by the name.")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_roles=True)
async def create_role(interaction: discord.Interaction, role_name: str):
    guild = interaction.guild
    await guild.create_role(name=role_name)
    await interaction.response.send_message(f"Role '{role_name}' created successfully.")

@bot.tree.command(name="delete_role", description="Deletes a role by the name" )
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_roles=True)
async def delete_role(interaction: discord.Interaction, role_name: str):
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=role_name)
    if role:
        await role.delete()
        await interaction.response.send_message(f"Role '{role_name}' deleted successfully.")
    else:
        await interaction.response.send_message(f"Role '{role_name}' not found.")



@bot.tree.command(name="dice_roll", description="Rolls a dice for you.")
async def dice_roll(interaction: discord.Interaction):
    result = random.randint(1, 6)
    await interaction.response.send_message(f"🎲 You rolled a {result}!")

@bot.tree.command(name="coinflip", description="Flips a coin for you.")
async def coinflip(interaction: discord.Interaction):
    result = random.choice(["Heads", "Tails"])
    await interaction.response.send_message(f"🪙 The coin landed on {result}!")



@bot.tree.command(name="cat", description="Sents a picture or GIF of a cat.")
async def cat(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.thecatapi.com/v1/images/search") as response:
            data = await response.json()
            cat_url = data[0]["url"]
            await interaction.response.send_message(cat_url)

@bot.tree.command(name="dog", description="Sents a picture or GIF of a dog.")
async def dog(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://dog.ceo/api/breeds/image/random") as response:
            data = await response.json()
            dog_url = data["message"]
            await interaction.response.send_message(dog_url)

@bot.tree.command(name="echo", description="Repeats the message which you have sent.")
async def echo(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)

@bot.tree.command(name="echoembed", description="Repeats the message which you have sent in embed.")
async def echoembed(interaction: discord.Interaction, message: str):
    embed = discord.Embed(description=message, color=discord.Color.purple())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="eightball", description="Answer the magic 8ball question.")
async def eightball(interaction: discord.Interaction, question: str):
    responses = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes – definitely.",
                 "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.",
                 "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.",
                 "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.",
                 "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.",
                 "Very doubtful."]
    response = random.choice(responses)
    await interaction.response.send_message(f"🎱 {response}")

@bot.tree.command(name="fact", description="Sends a fact.")
async def fact(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://uselessfacts.jsph.pl/random.json?language=en") as response:
            data = await response.json()
            fact = data["text"]
            await interaction.response.send_message(f"📘 {fact}")

@bot.tree.command(name="joke", description="Sends a joke.")
async def joke(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://official-joke-api.appspot.com/random_joke") as response:
            data = await response.json()
            joke = f"{data['setup']} - {data['punchline']}"
            await interaction.response.send_message(f"😂 {joke}")

@bot.tree.command(name="quote", description="Sends a quote.")
async def quote(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("https://api.quotable.io/random") as response:
            data = await response.json()
            quote = f"{data['content']} - {data['author']}"
            await interaction.response.send_message(f"📜 {quote}")
@bot.event
async def on_guild_join(guild):
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="Welcome to Velion Bot!",
                description=(
                    "Thank you for inviting me to your server. Here are some of my features:\n\n"
                    "**Bot Features:**\n"
                    "• `/addkeyword`: Adds a keyword to the list of keywords to watch for.\n"
                    "• `/afk`: Sets the AFK status with an optional message.\n"
                    "• `/ban`: Bans a member from the server.\n"
                    "• `/botinvite`: Generates an invite link for the bot.\n"
                    "• `/cat`: Displays a random cat image.\n"
                    "• `/purge`: Deletes a specified number of messages from the channel.\n"
                    "• `/coinflip`: Flips a coin and shows the result.\n"
                    "• `/create_channel`: Creates a new text channel.\n"
                    "• `/create_role`: Creates a new role.\n"
                    "• `/delete_channel`: Deletes a text channel.\n"
                    "• `/delete_role`: Deletes a role.\n"
                    "• Many More. Use `/help` for more information.\n\n"
                    "**Important Links:**\n"
                    "[Bot Website](https://velion.vercel.app/)\n"
                    "[Official Server](https://discord.gg/8qUUFUwSxD)\n"
                    "**Don't forget to keep the Velion Bot role at the top of the role list!**"
                ),
                color=discord.Color.purple()
            )
            await channel.send(embed=embed)
            break


@bot.command()
@commands.is_owner()
async def sync(ctx):
    await bot.tree.sync()
    await ctx.send("Commands synced.")
    scores = {}

@bot.tree.command(name="channelinfo", description="Shows details about a specific channel.")
@app_commands.describe(channel="The channel to get information about")
async def channelinfo(interaction: discord.Interaction, channel: discord.TextChannel):
    embed = discord.Embed(
        title=f"Channel Information - {channel.name}",
        color=discord.Color.green()
    )
    embed.add_field(name="ID", value=channel.id)
    embed.add_field(name="Category", value=channel.category.name if channel.category else "None")
    embed.add_field(name="Created On", value=channel.created_at.strftime("%Y-%m-%d"))
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="weather", description="Get weather information")
@app_commands.describe(place="The place to get the weather for")
async def weather(interaction: discord.Interaction, place: str):
    url = f"https://wttr.in/{place}?format=j1"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        current_condition = data['current_condition'][0]
        weather_description = current_condition['weatherDesc'][0]['value']
        temp_c = current_condition['temp_C']
        feels_like_c = current_condition['FeelsLikeC']
        humidity = current_condition['humidity']
        wind_speed_kmph = current_condition['windspeedKmph']
        
        embed = discord.Embed(title=f"Weather in {place}", color=discord.Color.purple())
        embed.add_field(name="Description", value=weather_description)
        embed.add_field(name="Temperature (°C)", value=temp_c)
        embed.add_field(name="Feels Like (°C)", value=feels_like_c)
        embed.add_field(name="Humidity (%)", value=humidity)
        embed.add_field(name="Wind Speed (km/h)", value=wind_speed_kmph)
        embed.set_footer(text=f"Requested by {interaction.user.name}", icon_url=interaction.user.avatar.url)

        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("Could not retrieve weather data. Please check the place name.", ephemeral=True)


@bot.tree.command(name="whois", description="Retrieves detailed information about a user.")
@app_commands.describe(user="The user to retrieve information about")
async def whois(interaction: discord.Interaction, user: discord.Member):
    embed = discord.Embed(
        title=f"Who is {user}?",
        color=discord.Color.dark_red()
    )
    embed.set_thumbnail(url=user.avatar.url)
    embed.add_field(name="ID", value=user.id)
    embed.add_field(name="Top Role", value=user.top_role.name)
    embed.add_field(name="Joined Server", value=user.joined_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Account Created", value=user.created_at.strftime("%Y-%m-%d"))
    embed.add_field(name="Status", value=str(user.status).title())
    embed.add_field(name="Activity", value=f"{user.activity.name}" if user.activity else "None")
    embed.add_field(name="Roles", value=", ".join([role.name for role in user.roles if role != interaction.guild.default_role]))

    await interaction.response.send_message(embed=embed)

import discord
from discord import app_commands

@bot.tree.command(name="velion", description="Provides comprehensive information about Velion and its creators.")
async def velion(interaction: discord.Interaction):
    # Create the embed with detailed information
    embed = discord.Embed(
        title="About Velion",
        description=("Velion is a sophisticated and versatile Discord bot designed to enhance your server experience "
                     "with an extensive array of features. Whether you need robust moderation tools, streamlined "
                     "user management, engaging interactions, or just some fun, Velion delivers exceptional performance "
                     "and flexibility to meet your needs. Explore the various functionalities Velion brings to your server!"),
        color=discord.Color.purple()
    )
    
    embed.add_field(name="🔧 **Key Features**", value=(
        "- **Advanced Moderation**: Effortlessly manage your server with commands for banning, kicking, muting, and more.\n"
        "- **Comprehensive User Management**: Assign and remove roles, change nicknames, view user info, and more.\n"
        "- **Engaging Interaction**: Welcome new members, conduct giveaways, create polls, and set reminders.\n"
        "- **Fun & Utility**: Enjoy games, jokes, weather updates, translation, and more to keep your community entertained."
    ))

    embed.add_field(name="📈 **Benefits**", value=(
        "- **Enhanced Security**: Protect your server with powerful moderation tools.\n"
        "- **Efficient Management**: Easily manage roles and user information with simple commands.\n"
        "- **Increased Engagement**: Keep your community active and engaged with fun and interactive features.\n"
        "- **Customizable Experience**: Tailor Velion's features to suit your server's unique needs and preferences."
    ))

    embed.add_field(name="🔗 **How to Use**", value=(
        "- **Prefix Commands**: Use `!command` for traditional commands or `/command` for app commands.\n"
        "- **Permissions**: Ensure you have the necessary permissions to use certain commands.\n"
        "- **Customization**: Adjust settings and features using available configuration commands."
    ))

    embed.add_field(name="👥 **Owners**", value="The dedicated creators behind Velion are HaiCLOP and RxDevelopment.")

    # Attach the local image file
    file = discord.File("logo.png", filename="logo.png")
    embed.set_image(url="attachment://logo.png")

    await interaction.response.send_message(embed=embed, file=file)

@bot.tree.command(name="poll", description="Creates a poll with up to 10 options.")
@app_commands.guild_only()
async def poll(interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None, option5: str = None, option6: str = None, option7: str = None, option8: str = None, option9: str = None, option10: str = None):
    options = [option1, option2, option3, option4, option5, option6, option7, option8, option9, option10]
    options = [opt for opt in options if opt]

    if len(options) < 2:
        await interaction.response.send_message("A poll must have at least two options.", ephemeral=True)
        return
    if len(options) > 10:
        await interaction.response.send_message("A poll can have at most 10 options.", ephemeral=True)
        return

    embed = discord.Embed(title=question, color=discord.Color.purple())
    reactions = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    description = ""
    for i, option in enumerate(options):
        description += f"{reactions[i]} {option}\n"
    embed.description = description
    
    await interaction.response.send_message("Poll created!", ephemeral=True)
    message = await interaction.followup.send(embed=embed)
    for i in range(len(options)):
        await message.add_reaction(reactions[i])


@bot.tree.command(name="presult", description="Displays the results of a poll.")
@app_commands.guild_only()
async def presult(interaction: discord.Interaction, message_id: str):
    try:
        message_id = int(message_id)
        message = await interaction.channel.fetch_message(message_id)
    except (discord.NotFound, ValueError):
        await interaction.response.send_message("Message not found or invalid message ID.", ephemeral=True)
        return

    if not message.embeds:
        await interaction.response.send_message("No poll found in the specified message.", ephemeral=True)
        return

    embed = message.embeds[0]
    reactions = message.reactions

    poll_results = {}
    for reaction in reactions:
        if reaction.emoji in ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']:
            poll_results[reaction.emoji] = reaction.count - 1

    results = ""
    for field in embed.description.split('\n'):
        if field:
            emoji = field.split(' ')[0]
            option = field.split(' ', 1)[1]
            count = poll_results.get(emoji, 0)
            results += f"{emoji} {option}: {count} votes\n"

    await interaction.response.send_message(f"Poll results:\n{results}")

@bot.tree.command(name="lock_channel", description="Locks the current channel, preventing everyone from sending messages.")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels=True)
async def lock_channel(interaction: discord.Interaction):
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    embed = discord.Embed(
        title="Channel Locked 🔒",
        description=f"{interaction.channel.name} has been locked. Only users with permission can send messages.",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unlock_channel", description="Unlocks the current channel, allowing everyone to send messages again.")
@app_commands.guild_only()
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock_channel(interaction: discord.Interaction):
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = True
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

    embed = discord.Embed(
        title="Channel Unlocked 🔓",
        description=f"{interaction.channel.name} has been unlocked. Everyone can now send messages.",
        color=discord.Color.purple()
    )
    await interaction.response.send_message(embed=embed)

# Constants
RAID_THRESHOLD = 5
SPAM_THRESHOLD = 5
SPAM_TIME = 5  # Seconds
NUKE_THRESHOLD = 10  # Messages
NUKE_TIME = 10  # Seconds

# Variables
recent_joins = []
message_times = {}
link_permissions = {}

# Anti-Raid Feature
@bot.event
async def on_member_join(member):
    current_time = datetime.utcnow()
    recent_joins.append(current_time)

    if len(recent_joins) == RAID_THRESHOLD and (current_time - recent_joins[0]) < timedelta(seconds=10):
        # Notify admins
        view = discord.ui.View()  # Define the view here

        # Lockdown Button
        class LockdownButton(discord.ui.Button):
            def __init__(self):
                super().__init__(label="Lockdown", style=discord.ButtonStyle.danger)

            async def callback(self, interaction):
                await interaction.response.send_message("Enter duration in minutes for the lockdown:", ephemeral=True)

                def check(m):
                    return m.author == interaction.user and m.content.isdigit()

                try:
                    msg = await bot.wait_for('message', check=check, timeout=60)
                    duration = int(msg.content)
                    lockdown_until = datetime.utcnow() + timedelta(minutes=duration)
                    await member.guild.edit(reason="Lockdown initiated", verification_level=discord.VerificationLevel.high)
                    await interaction.followup.send(f"Lockdown initiated for {duration} minutes.", ephemeral=True)

                    await asyncio.sleep(duration * 60)
                    await member.guild.edit(reason="Lockdown ended", verification_level=discord.VerificationLevel.medium)
                    await interaction.followup.send("Lockdown ended.", ephemeral=True)
                except asyncio.TimeoutError:
                    await interaction.followup.send("Lockdown command timed out.", ephemeral=True)

        # No Action Button
        class NoActionButton(discord.ui.Button):
            def __init__(self):
                super().__init__(label="No Action", style=discord.ButtonStyle.secondary)

            async def callback(self, interaction):
                await interaction.response.send_message("No action taken.", ephemeral=True)

        # Adding buttons to the view
        view.add_item(LockdownButton())
        view.add_item(NoActionButton())

        for admin in member.guild.members:
            if admin.guild_permissions.administrator:
                embed = discord.Embed(
                    title="🚨 Raid Detection",
                    description="A potential raid has been detected. Would you like to initiate a lockdown?",
                    color=discord.Color.purple(),
                )
                embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
                embed.add_field(name="New Members", value=f"{len(recent_joins)} in 10 seconds", inline=False)
                
                await admin.send(embed=embed, view=view)  # Now the view is defined and used here

# Nuke Protection Feature
@bot.event
async def on_message_delete(message):
    if message.guild:
        if message.author.bot:
            return

        current_time = datetime.utcnow()
        user = message.author

        if user.id not in message_times:
            message_times[user.id] = []

        message_times[user.id].append(current_time)

        # Check for a nuke
        if len(message_times[user.id]) > NUKE_THRESHOLD and (current_time - message_times[user.id][0]) < timedelta(seconds=NUKE_TIME):
            admin_role = discord.utils.get(message.guild.roles, name="Admin")
            if admin_role:
                for admin in message.guild.members:
                    if admin_role in admin.roles:
                        await admin.send(
                            embed=discord.Embed(
                                title="🚨 Nuke Detection",
                                description="A potential nuke has been detected. Immediate action required.",
                                color=discord.Color.purple()
                            ).add_field(name="Deleted Messages", value=f"{len(message_times[user.id])}", inline=False)
                        )

            # Lockdown with button
            view = discord.ui.View()
            
            class LockdownButton(discord.ui.Button):
                def __init__(self):
                    super().__init__(label="Lockdown", style=discord.ButtonStyle.danger)

                async def callback(self, interaction):
                    await interaction.response.send_message("Enter duration in minutes for the lockdown:", ephemeral=True)

                    def check(m):
                        return m.author == interaction.user and m.content.isdigit()

                    try:
                        msg = await bot.wait_for('message', check=check, timeout=60)
                        duration = int(msg.content)
                        lockdown_until = datetime.utcnow() + timedelta(minutes=duration)
                        await message.guild.edit(reason="Lockdown initiated", verification_level=discord.VerificationLevel.high)
                        await interaction.followup.send(f"Lockdown initiated for {duration} minutes.", ephemeral=True)

                        await asyncio.sleep(duration * 60)
                        await message.guild.edit(reason="Lockdown ended", verification_level=discord.VerificationLevel.medium)
                        await interaction.followup.send("Lockdown ended.", ephemeral=True)
                    except asyncio.TimeoutError:
                        await interaction.followup.send("Lockdown command timed out.", ephemeral=True)

            class NoActionButton(discord.ui.Button):
                def __init__(self):
                    super().__init__(label="No Action", style=discord.ButtonStyle.secondary)

                async def callback(self, interaction):
                    await interaction.response.send_message("No action taken.", ephemeral=True)

            view.add_item(LockdownButton())
            view.add_item(NoActionButton())

            for admin in message.guild.members:
                if admin.guild_permissions.administrator:
                    embed = discord.Embed(
                        title="🚨 Nuke Detection",
                        description="A potential nuke has been detected. Would you like to initiate a lockdown?",
                        color=discord.Color.purple(),
                    )
                    embed.set_thumbnail(url=message.guild.icon.url if message.guild.icon else None)
                    embed.add_field(name="Deleted Messages", value=f"{len(message_times[user.id])}", inline=False)
                    
                    await admin.send(embed=embed, view=view)  # Send embed with buttons

            message_times[user.id] = []




# File to store welcome data
WELCOME_DATA_FILE = 'welcome_data.json'

# Load welcome data from JSON file
def load_welcome_data():
    if os.path.exists(WELCOME_DATA_FILE):
        with open(WELCOME_DATA_FILE, 'r') as file:
            return json.load(file)
    return {}

# Save welcome data to JSON file
def save_welcome_data(data):
    with open(WELCOME_DATA_FILE, 'w') as file:
        json.dump(data, file, indent=4)

# Load welcome data on startup
welcome_data = load_welcome_data()

rules = [
    "1. Be respectful to all members.",
    "2. No spamming or flooding the chat.",
    "3. No hate speech or discriminatory language.",
    "4. No harassment or bullying.",
    "5. Keep content appropriate for all ages.",
    "6. No NSFW content.",
    "7. No self-promotion or advertisements without permission.",
    "8. Use channels for their intended purposes.",
    "9. Respect others' privacy.",
    "10. No sharing of personal information.",
    "11. Follow the instructions of the moderators.",
    "12. Do not impersonate others.",
    "13. No illegal activities.",
    "14. No sharing of pirated content.",
    "15. No disruptive behavior.",
    "16. Report any rule violations to the moderators.",
    "17. No excessive use of bots or commands.",
    "18. Keep discussions civil and on-topic.",
    "19. Follow Discord's [Terms of Service](https://discord.com/terms) and [Privacy Policy](https://discord.com/privacy).",
    "20. Have fun and enjoy your time here!"
]

@bot.tree.command(name="rules", description="Displays the server rules.")
@app_commands.guild_only()
async def rules_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Server Rules",
        description="Please make sure to follow these rules to ensure a friendly and respectful community.",
        color=discord.Color.purple()
    )
    
    for rule in rules:
        embed.add_field(name="\u200b", value=rule, inline=False)
    
    embed.set_thumbnail(url=interaction.guild.icon.url)
    embed.set_footer(text=f"By joining this server, you agree to these rules.")

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Command to setup the welcome message
@bot.tree.command(name='welcome', description='Setup a custom welcome message for new members')
@app_commands.guild_only()
@app_commands.checks.has_permissions(administrator=True)
async def welcome(interaction: discord.Interaction):
    # Create a select menu for choosing a channel
    channel_select = discord.ui.Select(
        placeholder="Select a channel...",
        options=[
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in interaction.guild.text_channels
        ]
    )
    
    # Create a view to hold the select menu
    view = discord.ui.View()
    view.add_item(channel_select)

    # Ask for the custom message
    async def select_channel_callback(interaction: discord.Interaction):
        selected_channel_id = int(channel_select.values[0])
        selected_channel = interaction.guild.get_channel(selected_channel_id)
        
        # Ask for custom message
        def check(msg):
            return msg.author == interaction.user and msg.channel == interaction.channel

        await interaction.response.send_message("Please enter your custom welcome message. Use `{user}` to tag the user and `{count}` for member count.", ephemeral=True)
        try:
            message = await bot.wait_for('message', timeout=60.0, check=check)
            custom_message = message.content
            await interaction.followup.send(f"Custom message set: {custom_message}", ephemeral=True)

            welcome_data[str(interaction.guild.id)] = {
                "channel_id": selected_channel_id,
                "custom_message": custom_message
            }
            save_welcome_data(welcome_data)
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to respond. The setup has been cancelled.", ephemeral=True)

    # Assign callback to the select menu
    channel_select.callback = select_channel_callback

    await interaction.response.send_message("Please select a channel for welcome messages:", view=view, ephemeral=True)

# Event when a new member joins
@bot.event
async def on_member_join(member: discord.Member):
    guild_id = str(member.guild.id)
    if guild_id in welcome_data:
        channel_id = welcome_data[guild_id]["channel_id"]
        custom_message = welcome_data[guild_id]["custom_message"]
        
        channel = member.guild.get_channel(channel_id)
        if custom_message:
            message = custom_message.replace("{user}", member.mention).replace("{count}", str(len(member.guild.members)))
            embed = discord.Embed(title="Welcome!", description=message, color=discord.Color.purple())
            await channel.send(embed=embed)
        else:
            default_message = f"Welcome {member.mention}! You are member #{len(member.guild.members)} in this server."
            embed = discord.Embed(title="Welcome!", description=default_message, color=discord.Color.purple())
            await channel.send(embed=embed)

 


@bot.tree.command(name="rolerm", description="Remove a role from a user")
@app_commands.describe(user="The user to remove the role from", role="The role to remove")
async def rrm(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    if interaction.user.guild_permissions.manage_roles:
        try:
            await user.remove_roles(role)
            await interaction.response.send_message(f"Role {role.mention} has been removed from {user.mention}")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}")
    else:
        await interaction.response.send_message("You do not have permission to manage roles.", ephemeral=True)

@bot.tree.command(name="roll", description="It rolls a number from min number to max number.")
async def roll(interaction: discord.Interaction, min: int, max: int):
    if min >= max:
        await interaction.response.send_message("The minimum value must be less than the maximum value.")
        return
    result = random.randint(min, max)
    await interaction.response.send_message(f"🎲 You rolled a {result}!")

@bot.tree.command(name='list', description='List all servers where the bot is present (Owner only)')
async def list_servers(interaction: discord.Interaction):
    # Ensure the command can only be used by the bot owner
    if interaction.user.id != YOUR_BOT_OWNER_ID:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)  # Acknowledge the interaction

    for guild in bot.guilds:
        # Create an embed for each server
        embed = discord.Embed(title="Server Info", color=discord.Color.purple())
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.add_field(name="Server Name", value=guild.name, inline=False)
        embed.add_field(name="Server ID", value=guild.id, inline=False)
        embed.add_field(name="Owner", value=guild.owner.mention, inline=False)
        embed.add_field(name="Member Count", value=guild.member_count, inline=False)

        # Send a follow-up message for each server
        try:
            await interaction.followup.send(embed=embed)
        except discord.errors.NotFound:
            print(f"Failed to send message for server {guild.name} ({guild.id})")

@bot.event
async def on_guild_join(guild):
    channel = bot.get_channel(1277953214205001739)  # Replace with your actual channel ID
    
    if channel is None:
        print(f"Channel with ID 1277953214205001739 not found or bot doesn't have access.")
        return  # Exit if the channel isn't found

    # Create the invite link
    if guild.system_channel and guild.system_channel.permissions_for(guild.me).create_instant_invite:
        invite = await guild.system_channel.create_invite(max_age=0, max_uses=0)
    else:
        invite = "Invite link couldn't be generated."

    # Prepare the embed with server details
    embed = discord.Embed(title="New Server Joined!", color=discord.Color.purple())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Server Name", value=guild.name, inline=False)
    embed.add_field(name="Server ID", value=guild.id, inline=False)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=False)
    embed.add_field(name="Invite Link", value=invite, inline=False)
    
    # Send the embed to the specific channel
    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to send message: {e}")


PREMIUM_FILE = 'premium_data.json'
BOT_OWNER_ID = 1022181741848428654
BOT_TEAM_USER_ID = 1215953214172561449

# Load premium data
if os.path.exists(PREMIUM_FILE):
    with open(PREMIUM_FILE, 'r') as f:
        premium_data = json.load(f)
else:
    premium_data = {
        "keys": {},
        "premium_guilds": {},
        "premium_users": {}
    }

# Check if a guild or user is premium
def is_premium(guild_id, user_id):
    return (str(guild_id) in premium_data["premium_guilds"]) or (str(user_id) in premium_data["premium_users"])

# Save premium data to JSON
def save_premium_data():
    with open(PREMIUM_FILE, 'w') as f:
        json.dump(premium_data, f, indent=4)

# Check if user is bot owner or team member
def is_bot_owner_or_team(user: discord.User):
    return user.id in [BOT_OWNER_ID, BOT_TEAM_USER_ID]

# Generate a premium key with the format "VELION-RANDOMNUMBER"
def generate_key():
    return f"VELION-{''.join(random.choices(string.ascii_uppercase + string.digits, k=16))}"

# Get expiration date based on selected duration
def get_expiration_date(days):
    if days == "lifetime":
        return "infinite"
    return (datetime.now() + timedelta(days=int(days))).strftime('%Y-%m-%d %H:%M:%S')

# Command to create a premium key

# Create a select menu for the duration
class DurationSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="1 Day", value="1"),
            discord.SelectOption(label="3 Days", value="3"),
            discord.SelectOption(label="7 Days", value="7"),
            discord.SelectOption(label="14 Days", value="14"),
            discord.SelectOption(label="30 Days", value="30"),
            discord.SelectOption(label="60 Days", value="60"),
            discord.SelectOption(label="120 Days", value="120"),
            discord.SelectOption(label="365 Days", value="365"),
            discord.SelectOption(label="Lifetime", value="lifetime")
        ]
        super().__init__(placeholder="Select premium duration...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        days = self.values[0]
        if not is_bot_owner_or_team(interaction.user):
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return

        key = generate_key()
        expiration_date = get_expiration_date(days)
        premium_data["keys"][key] = expiration_date
        save_premium_data()

        embed = discord.Embed(
            title="Premium Key Created",
            description=f"🔑 Premium key created: {key}\nDuration: {days} days",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Command to create a premium key with select menu
@bot.tree.command(name="create_key", description="Create a premium key")
async def create_key(interaction: discord.Interaction):
    if not is_bot_owner_or_team(interaction.user):
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    select = DurationSelect()
    view = View()
    view.add_item(select)

    await interaction.response.send_message("Select the duration for the premium key:", view=view, ephemeral=True)


utility_commands = [
    {"name": "ping", "description": "Shows the latency of the bot and server.", "emoji": "🏓"},
    {"name": "purge", "description": "Clears a specified number of messages in a channel.", "emoji": "🧹"},
    {"name": "role", "description": "Assigns or removes a role from a user.", "emoji": "🎭"},
    {"name": "nickname", "description": "Changes a user's nickname.", "emoji": "📛"},
    {"name": "avatar", "description": "Displays a user's avatar.", "emoji": "🖼️"},
    {"name": "userinfo", "description": "Shows information about a user.", "emoji": "ℹ️"},
    {"name": "serverinfo", "description": "Displays information about the server.", "emoji": "🏠"},
    {"name": "define", "description": "Define a word.", "emoji": "📖"},
    {"name": "weather", "description": "Get weather information.", "emoji": "☀️"},
    {"name": "translate", "description": "Translate text to another language.", "emoji": "🌐"},
    {"name": "generate_qr", "description": "Generate a QR code for a given link.", "emoji": "📷"},
    {"name": "create_role", "description": "Creates a role by the name.", "emoji": "➕"},
    {"name": "delete_role", "description": "Deletes a role by the name.", "emoji": "➖"},
    {"name": "roles", "description": "Lists all roles in the server.", "emoji": "🎭"},
    {"name": "whois", "description": "Retrieves detailed information about a user.", "emoji": "🔍"},
    {"name": "channelinfo", "description": "Shows details about a specific channel.", "emoji": "📺"},
]

fun_commands = [
    {"name": "trivia", "description": "Starts a trivia game.", "emoji": "❓"},
    {"name": "scores", "description": "Check your game scores.", "emoji": "🏆"},
    {"name": "captcha", "description": "Start a CAPTCHA game.", "emoji": "🔐"},
    {"name": "dice_roll", "description": "Rolls a dice for you.", "emoji": "🎲"},
    {"name": "coinflip", "description": "Flips a coin for you.", "emoji": "🪙"},
    {"name": "cat", "description": "Sends a picture or GIF of a cat.", "emoji": "🐱"},
    {"name": "dog", "description": "Sends a picture or GIF of a dog.", "emoji": "🐶"},
    {"name": "echo", "description": "Repeats the message which you have sent.", "emoji": "🔁"},
    {"name": "echoembed", "description": "Repeats the message which you have sent in embed.", "emoji": "🔂"},
    {"name": "fact", "description": "Sends a fact.", "emoji": "🧠"},
    {"name": "joke", "description": "Sends a joke.", "emoji": "😂"},
    {"name": "quote", "description": "Sends a quote.", "emoji": "💬"},
]

moderation_commands = [
    {"name": "ban", "description": "Bans a user from the server.", "emoji": "🔨"},
    {"name": "kick", "description": "Kicks a user from the server.", "emoji": "👢"},
    {"name": "mute", "description": "Mutes a user for a specified duration.", "emoji": "🔇"},
    {"name": "unmute", "description": "Unmutes a muted user.", "emoji": "🔊"},
    {"name": "warn", "description": "Issues a warning to a user.", "emoji": "⚠️"},
    {"name": "lockdown", "description": "Lock down the server for a specified duration.", "emoji": "🔒"},
    {"name": "rlockdown", "description": "Remove the server lockdown.", "emoji": "🔓"},
    {"name": "lock_channel", "description": "Locks the current channel, preventing everyone from sending messages.", "emoji": "🔒"},
    {"name": "unlock_channel", "description": "Unlocks the current channel, allowing everyone to send messages again.", "emoji": "🔓"},
    {"name": "rolerm", "description": "Remove a role from a user.", "emoji": "🚫"},
    {"name": "rules", "description": "Displays the server rules.", "emoji": "📜"},
    {"name": "welcome", "description": "Setup a custom welcome message for new members.", "emoji": "👋"},
]

premium_commands = [
    {"name": "serveranalytics", "description": "Get server analytics and information (Premium Feature).", "emoji": "📊"},
    {"name": "use_key", "description": "Use a premium key to activate premium features.", "emoji": "🔑"},
    {"name": "premium_status", "description": "Check your premium status.", "emoji": "💎"},
]

def create_embed(commands, title, color):
    embed = discord.Embed(title=title, color=color)
    for cmd in commands:
        embed.add_field(name=f"{cmd['emoji']} /{cmd['name']}", value=cmd['description'], inline=False)
    return embed

@bot.tree.command(name="help", description="Shows all commands.")
async def help(interaction: discord.Interaction):
    # Send each category of commands as separate embeds
    await interaction.response.send_message(embed=create_embed(utility_commands, "Utility Commands", discord.Color.purple()), ephemeral=True)
    await interaction.followup.send(embed=create_embed(fun_commands, "Fun Commands", discord.Color.purple()), ephemeral=True)
    await interaction.followup.send(embed=create_embed(moderation_commands, "Moderation Commands", discord.Color.purple()), ephemeral=True)
    await interaction.followup.send(embed=create_embed(premium_commands, "Premium Commands", discord.Color.gold()), ephemeral=True)



@bot.tree.command(name="use_key", description="Use a premium key to activate premium features")
@app_commands.describe(key="The premium key")
async def use_key(interaction: discord.Interaction, key: str):
    if key not in premium_data["keys"]:
        embed = discord.Embed(
            title="Invalid Key",
            description="❌ The key you provided is invalid. Please check and try again.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    expiration_date = premium_data["keys"].pop(key)
    if interaction.guild:
        guild_id = str(interaction.guild.id)
        premium_data["premium_guilds"][guild_id] = {
            "expiration": expiration_date,
            "activated_by": interaction.user.id,
            "activation_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_premium_data()
        embed = discord.Embed(
            title="Premium Activated",
            description="🎉 Premium features activated for this server.",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        user_id = str(interaction.user.id)
        premium_data["premium_users"][user_id] = {
            "expiration": expiration_date,
            "activation_date": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        save_premium_data()
        embed = discord.Embed(
            title="Premium Activated",
            description="🎉 Premium features activated for your server.",
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Command to check premium status
@bot.tree.command(name="premium_status", description="Check your premium status")
async def premium_status(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id) if interaction.guild else None
    status = None

    if guild_id and guild_id in premium_data["premium_guilds"]:
        status = premium_data["premium_guilds"][guild_id]
        embed = discord.Embed(title="Premium Status for Server", color=discord.Color.gold())
        embed.add_field(name="Activated By", value=f"<@{status['activated_by']}>")
        embed.add_field(name="Activation Date", value=status["activation_date"])
        embed.add_field(name="Expiration Date", value=status["expiration"])
    elif user_id in premium_data["premium_users"]:
        status = premium_data["premium_users"][user_id]
        embed = discord.Embed(title="Premium Status for User", color=discord.Color.gold())
        embed.add_field(name="Activation Date", value=status["activation_date"])
        embed.add_field(name="Expiration Date", value=status["expiration"])
    else:
        embed = discord.Embed(title="No Premium Status", description="You do not have any active premium status.", color=discord.Color.red())

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Expiration check task
@tasks.loop(hours=24)
async def check_expiration():
    now = datetime.now()
    expired_guilds = []
    expired_users = []

    # Check guild expirations
    for guild_id, data in premium_data["premium_guilds"].items():
        expiration_date = data.get("expiration")
        if expiration_date != "infinite" and datetime.strptime(expiration_date, '%Y-%m-%d %H:%M:%S') < now:
            expired_guilds.append(guild_id)

    # Remove expired guilds
    for guild_id in expired_guilds:
        del premium_data["premium_guilds"][guild_id]

    # Check user expirations
    for user_id, data in premium_data["premium_users"].items():
        expiration_date = data.get("expiration")
        if expiration_date != "infinite" and datetime.strptime(expiration_date, '%Y-%m-%d %H:%M:%S') < now:
            expired_users.append(user_id)

    # Remove expired users
    for user_id in expired_users:
        del premium_data["premium_users"][user_id]

    # Save updated data
    save_premium_data()

# Function to save premium data
def save_premium_data():
    with open(PREMIUM_FILE, 'w') as f:
        json.dump(premium_data, f, indent=4)


bot.run("")
