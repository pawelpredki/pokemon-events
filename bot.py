import os
import json
import datetime as dt
from typing import List, Dict, Any
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from flask import Flask
import os
from threading import Thread

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_USER_IDS = [330055279699820554]  # Replace with your Discord ID

# Timezone (CET/CEST for Poland)
TIMEZONE = ZoneInfo("Europe/Warsaw")

# Color scheme for event types
EVENT_COLORS = {
    "Luźne": 0x00FF00,      # Green
    "Challenge": 0xFFAA00,  # Orange
    "Cup": 0xFF0000,        # Red
    "Prerelease": 0xAA00FF, # Purple
    "Puchar": 0x0099FF      # Blue
}

# Add emoji mapping at top with EVENT_COLORS
EVENT_EMOJIS = {
    "Luźne": "🍹",
    "Challenge": "⚔️",
    "Cup": "🏆",
    "Puchar": "⛵",
    "Prerelease": "📅"
}

def load_events() -> List[Dict[str, Any]]:
    try:
        with open("events.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_events(events: List[Dict[str, Any]]):
    with open("events.json", "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)

EVENTS = load_events()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    # FORCE SYNC TO YOUR SERVER (replace YOUR_GUILD_ID)
    guild = discord.Object(id=662272782129954817)  # Your server ID
    bot.tree.copy_global_to(guild=guild)
    synced = await bot.tree.sync(guild=guild)
    
    print(f"✅ Synced {len(synced)} commands to your server!")
    print(f"Logged in as {bot.user}")

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_USER_IDS

def parse_date(date_str: str = None) -> dt.datetime:
    """Parse YYYY-MM-DD or use now() - naive datetime (CET assumed)"""
    if date_str:
        dt_obj = dt.datetime.strptime(date_str, "%Y-%m-%d")
        return dt_obj.replace(hour=12, minute=0, second=0)  # All at 12:00
    return dt.datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)

def get_events_in_range(start_date: dt.datetime, days: int = 5) -> List[Dict[str, Any]]:
    """Get events from start_date for 'days' days, sorted by date/time"""
    end_date = start_date + dt.timedelta(days=days)
    filtered = []
    
    for event in EVENTS:
        event_dt = dt.datetime.strptime(f"{event['date']} {event['time']}", "%Y-%m-%d %H:%M")
        if start_date.date() <= event_dt.date() < end_date.date():
            filtered.append(event)
    
    # Sort by date + time
    filtered.sort(key=lambda e: dt.datetime.strptime(f"{e['date']} {e['time']}", "%Y-%m-%d %H:%M"))
    return filtered


def format_public_event(event: Dict[str, Any]) -> str:
    """Format event for public display"""
    types = "/".join(event["type"])
    time = event["time"]
    date = event["date"]
    extra = event.get("extra", "")
    return f"**{types}** • {date} {time} {extra}".strip()

@bot.tree.command(name="granie", description="Nadchodzące turnieje Pokémon")
@app_commands.describe(od="Data startowa YYYY-MM-DD (domyślnie dziś)", do="Data końcowa YYYY-MM-DD (domyślnie +7 dni)")
async def granie(interaction: discord.Interaction, od: str = None, do: str = None):
    # Parse dates
    start_date = parse_date(od)
    if do:
        end_date = parse_date(do)
    else:
        end_date = start_date + dt.timedelta(days=7)
    
    events = get_events_in_range(start_date, (end_date - start_date).days + 1)
    
    if not events:
        await interaction.response.send_message(f"❌ Brak turniejów od {start_date.strftime('%d.%m')} do {end_date.strftime('%d.%m')}.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎲 Nadchodzące turnieje Pokémon", 
        color=0x5865F2
    )

    # Send multiple embeds (max 10 per message)
    embeds = []
    for event in events:
        primary_type = event["type"][0]
        emoji = EVENT_EMOJIS.get(primary_type, "🎾")
        color = EVENT_COLORS.get(primary_type, 0xFFFFFF)
        
        types = "/".join(event["type"])
        extra_part = f" 🗒️ {event.get('extra', '')}" if event.get('extra') else ""
        
        embed = discord.Embed(
            title=f"{emoji} {types}",
            description=f"📅 {event['date']} {event['time']}\r\n\r\n📍 **{event['place']}**",
            color=color
        )
        embed.set_footer(text=f"{extra_part}")
        embeds.append(embed)
    
    # Send first embed, then followups (Discord limit: 10 embeds/message)
    await interaction.response.send_message(embed=embeds[0])
    for embed in embeds[1:]:
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    # for event in events:
    #     # Get emoji for primary type (first type)
    #     primary_type = event["type"][0]
    #     emoji = EVENT_EMOJIS.get(primary_type, "🎾")
    #     color = EVENT_COLORS.get(primary_type, 0xFFFFFF)
        
    #     # Format event line with emoji
    #     types = "/".join(event["type"])
    #     base_line = f"{emoji} **{types}**"
    #     extra_part = f" • {event.get('extra', '')}" if event.get('extra') else ""
    #     event_line = base_line + extra_part
        
    #     embed.add_field(
    #         name=f"{event['date']} {event['time']} - {event['place']}",
    #         value=event_line,
    #         inline=False
    #     )
    
    # date_range = f"{start_date.strftime('%d.%m')} - {end_date.strftime('%d.%m')}"
    # embed.set_footer(text=f"Turnieje: {date_range} | {len(events)} wydarzeń")
    
    # await interaction.response.send_message(embed=embed)

@bot.tree.command(name="list_events", description="Lista wydarzeń z ID (admin only)")
@app_commands.describe(od="Data startowa YYYY-MM-DD (domyślnie dziś)", do="Data końcowa YYYY-MM-DD (domyślnie +7 dni)")
async def list_events(interaction: discord.Interaction, od: str = None, do: str = None):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Tylko admini!", ephemeral=True)
        return
    
    # Parse dates (same logic as granie)
    start_date = parse_date(od)
    if do:
        end_date = parse_date(do)
    else:
        end_date = start_date + dt.timedelta(days=7)
    
    events = get_events_in_range(start_date, (end_date - start_date).days + 1)
    
    if not events:
        date_range = f"{start_date.strftime('%d.%m')} do {end_date.strftime('%d.%m')}"
        await interaction.response.send_message(f"Brak wydarzeń od {date_range}.", ephemeral=True)
        return
    
    content = f"**Lista wydarzeń (ID | Data | Miejsce | Typy)**\n*od {start_date.strftime('%d.%m')} do {end_date.strftime('%d.%m')}*\n\n"
    
    for e in events:
        types = "/".join(e["type"])
        extra = f" | {e.get('extra', '')}".strip() if e.get('extra') else ""
        content += f"`{e['id']:2d}` | {e['date']} {e['time']} | {e['place']}{extra} | {types}\n"
    
    await interaction.response.send_message(content, ephemeral=True)


@bot.tree.command(name="add_event", description="Add event as JSON (admin only)")
@app_commands.describe(json_data="Event JSON: {\"date\":\"YYYY-MM-DD\",\"time\":\"hh:mm\",\"place\":\"Basestack\",\"type\":[\"Luźne\"],\"extra\":\"\"}")
async def add_event(interaction: discord.Interaction, json_data: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Tylko admini!", ephemeral=True)
        return
    
    try:
        event = json.loads(json_data)
        
        # Validate required fields
        required = ["date", "place", "type"]
        missing = [field for field in required if field not in event]
        if missing:
            await interaction.response.send_message(f"❌ Brakujące pola: {', '.join(missing)}", ephemeral=True)
            return
        
        # Set ID and default time ONLY if missing
        event["id"] = max([e.get("id", 0) for e in EVENTS], default=0) + 1
        if "time" not in event:
            event["time"] = "12:00"
        
        EVENTS.append(event)
        save_events(EVENTS)
        await interaction.response.send_message(f"✅ Dodano wydarzenie ID `{event['id']}`", ephemeral=True)
    except json.JSONDecodeError:
        await interaction.response.send_message("❌ Błędny JSON!", ephemeral=True)


@bot.tree.command(name="remove_event", description="Remove event by ID (admin only)")
@app_commands.describe(event_id="Event ID")
async def remove_event(interaction: discord.Interaction, event_id: int):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Tylko admini!", ephemeral=True)
        return
    
    global EVENTS
    EVENTS = [e for e in EVENTS if e["id"] != event_id]
    save_events(EVENTS)
    await interaction.response.send_message(f"✅ Usunięto ID `{event_id}`", ephemeral=True)

@bot.tree.command(name="edit_event", description="Edit event by ID (admin only)")
@app_commands.describe(event_id="Event ID", json_data="New data JSON")
async def edit_event(interaction: discord.Interaction, event_id: int, json_data: str):
    if not is_admin(interaction.user.id):
        await interaction.response.send_message("❌ Tylko admini!", ephemeral=True)
        return
    
    try:
        new_data = json.loads(json_data)
        for event in EVENTS:
            if event["id"] == event_id:
                event.update(new_data)
                save_events(EVENTS)
                await interaction.response.send_message(f"✅ Edytowano ID `{event_id}`", ephemeral=True)
                return
        await interaction.response.send_message(f"❌ ID `{event_id}` nie istnieje!", ephemeral=True)
    except json.JSONDecodeError:
        await interaction.response.send_message("❌ Błędny JSON!", ephemeral=True)

if __name__ == "__main__":
    bot.run(TOKEN)

app = Flask('')

@app.route('/')
def home():
    return "Pokémon Bot online! /granie"

def run_flask():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)

if __name__ == "__main__":
    # Start Flask in background
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Start Discord bot
    bot.run(TOKEN)
