import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import re
import asyncio
from collections import defaultdict
from datetime import datetime

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# User warning tracking
user_warnings = defaultdict(int)

# Racism patterns - immediate ban
RACISM_PATTERNS = [
    r'\b(n[i1]gg[aer]+)\b',
    r'\b(f[a@]gg[o0]t)\b', 
    r'\b(ch[i1]nk)\b',
    r'\b(sp[i1]c)\b',
    r'\b(k[i1]ke)\b',
    r'\b(raghead)\b',
    r'\b(towelhead)\b'
]

# Swearing patterns - warnings
SWEARING_PATTERNS = [
    r'\b(fuck|shit|damn|bitch|ass|hell|crap)\b',
    r'\b(fucking|shitting|damned|bitchy)\b'
]

# Compile patterns for better performance
racism_regex = [re.compile(pattern, re.IGNORECASE) for pattern in RACISM_PATTERNS]
swearing_regex = [re.compile(pattern, re.IGNORECASE) for pattern in SWEARING_PATTERNS]

# URL pattern
url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')

@bot.event
async def on_ready():
    print(f'{bot.user} is online and monitoring!')
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Activity(type=discord.ActivityType.watching, name="for rule violations")
    )

@bot.event
async def on_message(message):
    # Ignore bot messages and DMs
    if message.author.bot or not message.guild:
        return
    
    # Skip if user is admin
    if message.author.guild_permissions.administrator:
        return
    
    # Get owner (you)
    owner = bot.get_user(bot.owner_id) or message.guild.owner
    
    content = message.content.lower()
    
    # Check for racism - instant ban
    if check_racism(content):
        await handle_racism(message, owner)
        return
    
    # Check for NSFW links or any links - instant restriction
    if url_pattern.search(message.content):
        await handle_links(message, owner)
        return
    
    # Check for swearing - 2 warnings then restriction
    if check_swearing(content):
        await handle_swearing(message, owner)
        return

def check_racism(content):
    """Check if message contains racist content"""
    for pattern in racism_regex:
        if pattern.search(content):
            return True
    return False

def check_swearing(content):
    """Check if message contains swearing"""
    for pattern in swearing_regex:
        if pattern.search(content):
            return True
    return False

async def handle_racism(message, owner):
    """Handle racist content - instant ban"""
    try:
        # Delete message
        await message.delete()
        
        # Ban user
        await message.author.ban(reason="Racist content - automatic ban")
        
        # Notify owner
        embed = discord.Embed(
            title="🚨 AUTOMATIC BAN - Racism",
            description=f"**User:** {message.author.mention} ({message.author.id})\n"
                       f"**Channel:** {message.channel.mention}\n"
                       f"**Action:** Permanently banned",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Message Content", value=f"```{message.content}```", inline=False)
        
        if owner:
            try:
                await owner.send(embed=embed)
            except:
                # If can't DM owner, try to find a log channel
                for channel in message.guild.text_channels:
                    if 'log' in channel.name.lower() or 'mod' in channel.name.lower():
                        await channel.send(f"{owner.mention if owner else 'Owner'}", embed=embed)
                        break
        
    except Exception as e:
        print(f"Error handling racism: {e}")

async def handle_links(message, owner):
    """Handle links - instant restriction with ticket"""
    try:
        # Delete message
        await message.delete()
        
        # Create restriction and ticket
        ticket_channel = await create_restriction_and_ticket(message, "NSFW/Links", owner)
        
        # Notify owner
        embed = discord.Embed(
            title="🔗 LINK VIOLATION - Instant Restriction",
            description=f"**User:** {message.author.mention} ({message.author.id})\n"
                       f"**Channel:** {message.channel.mention}\n"
                       f"**Action:** Access restricted, ticket created\n"
                       f"**Ticket:** {ticket_channel.mention if ticket_channel else 'Failed to create'}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Message Content", value=f"```{message.content}```", inline=False)
        
        if owner:
            try:
                await owner.send(embed=embed)
            except:
                # Try to send to a log channel if DM fails
                for channel in message.guild.text_channels:
                    if 'log' in channel.name.lower() or 'mod' in channel.name.lower():
                        await channel.send(f"{owner.mention if owner else 'Owner'}", embed=embed)
                        break
        
    except Exception as e:
        print(f"Error handling links: {e}")

async def handle_swearing(message, owner):
    """Handle swearing - 2 warnings then restriction"""
    try:
        # Delete message
        await message.delete()
        
        user_id = message.author.id
        user_warnings[user_id] += 1
        warnings = user_warnings[user_id]
        
        if warnings >= 2:
            # Create restriction and ticket
            ticket_channel = await create_restriction_and_ticket(message, "Excessive Swearing", owner)
            
            # Reset warnings
            user_warnings[user_id] = 0
            
            # Notify owner
            embed = discord.Embed(
                title="🤬 SWEARING LIMIT REACHED - Restriction Applied",
                description=f"**User:** {message.author.mention} ({message.author.id})\n"
                           f"**Channel:** {message.channel.mention}\n"
                           f"**Warnings:** {warnings}/2 (LIMIT REACHED)\n"
                           f"**Action:** Access restricted, ticket created\n"
                           f"**Ticket:** {ticket_channel.mention if ticket_channel else 'Failed to create'}",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
        else:
            # Just a warning
            embed = discord.Embed(
                title="⚠️ SWEARING WARNING",
                description=f"**User:** {message.author.mention} ({message.author.id})\n"
                           f"**Channel:** {message.channel.mention}\n"
                           f"**Warnings:** {warnings}/2\n"
                           f"**Action:** Warning issued",
                color=discord.Color.yellow(),
                timestamp=datetime.utcnow()
            )
        
        embed.add_field(name="Message Content", value=f"```{message.content}```", inline=False)
        
        if owner:
            try:
                await owner.send(embed=embed)
            except:
                # Try to send to a log channel if DM fails
                for channel in message.guild.text_channels:
                    if 'log' in channel.name.lower() or 'mod' in channel.name.lower():
                        await channel.send(f"{owner.mention if owner else 'Owner'}", embed=embed)
                        break
        
    except Exception as e:
        print(f"Error handling swearing: {e}")

async def create_restriction_and_ticket(message, violation_type, owner):
    """Create restriction role and ticket channel"""
    try:
        guild = message.guild
        member = message.author
        
        # Create or get restricted role
        restricted_role = discord.utils.get(guild.roles, name="Restricted")
        if not restricted_role:
            try:
                restricted_role = await guild.create_role(
                    name="Restricted",
                    color=discord.Color.red(),
                    reason="Auto-moderation restriction"
                )
                
                # Set permissions for all channels
                for channel in guild.channels:
                    try:
                        await channel.set_permissions(
                            restricted_role,
                            view_channel=False,
                            send_messages=False,
                            add_reactions=False,
                            speak=False
                        )
                    except:
                        continue
            except:
                print("Failed to create restricted role - missing permissions")
                return None
        
        # Apply restricted role
        try:
            # Remove other roles (keep @everyone)
            roles_to_remove = [role for role in member.roles if role != guild.default_role and not role.permissions.administrator]
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason=f"Auto-restriction: {violation_type}")
            
            # Add restricted role
            await member.add_roles(restricted_role, reason=f"Auto-restriction: {violation_type}")
        except:
            print("Failed to apply restricted role - missing permissions")
        
        # Create ticket channel
        try:
            ticket_name = f"appeal-{member.display_name}-{violation_type.lower().replace('/', '-')}"
            
            # Create ticket category if it doesn't exist
            ticket_category = discord.utils.get(guild.categories, name="Appeals")
            if not ticket_category:
                try:
                    ticket_category = await guild.create_category("Appeals")
                    
                    # Set category permissions
                    await ticket_category.set_permissions(guild.default_role, view_channel=False)
                    await ticket_category.set_permissions(guild.me, view_channel=True, manage_channels=True)
                    
                    # Add owner permissions if possible
                    if owner and isinstance(owner, discord.Member) and owner.guild == guild:
                        await ticket_category.set_permissions(owner, view_channel=True, send_messages=True)
                except:
                    ticket_category = None
            
            # Create the ticket channel
            ticket_channel = await guild.create_text_channel(
                name=ticket_name,
                category=ticket_category,
                topic=f"Appeal for {member.display_name} - {violation_type}"
            )
            
            # Set ticket channel permissions
            await ticket_channel.set_permissions(guild.default_role, view_channel=False)
            await ticket_channel.set_permissions(member, view_channel=True, send_messages=True)
            await ticket_channel.set_permissions(guild.me, view_channel=True, send_messages=True)
            
            # Add owner permissions if possible
            if owner and isinstance(owner, discord.Member) and owner.guild == guild:
                await ticket_channel.set_permissions(owner, view_channel=True, send_messages=True)
            
            # Send ticket message
            embed = discord.Embed(
                title=f"🎫 Appeal Ticket - {violation_type}",
                description=f"Hello {member.mention},\n\n"
                           f"Your access has been restricted due to: **{violation_type}**\n\n"
                           f"You can explain your case here and wait for review.\n"
                           f"Only you and server administrators can see this channel.",
                color=discord.Color.orange()
            )
            await ticket_channel.send(embed=embed)
            
            return ticket_channel
            
        except Exception as e:
            print(f"Failed to create ticket channel: {e}")
            return None
            
    except Exception as e:
        print(f"Error in create_restriction_and_ticket: {e}")
        return None

if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: DISCORD_BOT_TOKEN not found!")
    else:
        bot.run(token)