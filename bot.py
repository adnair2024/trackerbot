"""
Author: Ashwin Nair
Date: 2025-08-22
Project name: bot.py
Summary: Enter summary here.
"""

import os
import sqlite3
import discord
from discord.ext import commands

TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Discord bot setup
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# SQLite connection
conn = sqlite3.connect("anime_manga.db")
c = conn.cursor()

# Utility: create/get user
def get_or_create_user(discord_user):
    c.execute("SELECT user_id FROM users WHERE discord_id=?", (discord_user.id,))
    row = c.fetchone()
    if row:
        return row[0]
    else:
        c.execute("INSERT INTO users (discord_id, display_name) VALUES (?, ?)",
                  (discord_user.id, discord_user.display_name))
        conn.commit()
        return c.lastrowid

# --- Events ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

# --- Commands ---
@bot.command()
async def add(ctx, media_type: str, *, title: str):
    """Add an anime or manga to your list."""
    user_id = get_or_create_user(ctx.author)

    if media_type.lower() == "anime":
        c.execute("INSERT OR IGNORE INTO anime (title) VALUES (?)", (title,))
        c.execute("SELECT anime_id FROM anime WHERE title=?", (title,))
        media_id = c.fetchone()[0]
    elif media_type.lower() == "manga":
        c.execute("INSERT OR IGNORE INTO manga (title) VALUES (?)", (title,))
        c.execute("SELECT manga_id FROM manga WHERE title=?", (title,))
        media_id = c.fetchone()[0]
    else:
        await ctx.send("❌ Use `anime` or `manga`.")
        return

    c.execute("""INSERT INTO user_library (user_id, media_type, media_id, status) 
                 VALUES (?, ?, ?, ?)""",
              (user_id, media_type.lower(), media_id, "completed"))
    conn.commit()

    await ctx.send(f"✅ Added {title} to your {media_type} list!")

@bot.command()
async def rate(ctx, media_type: str, title: str, rating: int):
    """Rate an anime or manga."""
    user_id = get_or_create_user(ctx.author)

    if media_type.lower() == "anime":
        c.execute("SELECT anime_id FROM anime WHERE title=?", (title,))
    else:
        c.execute("SELECT manga_id FROM manga WHERE title=?", (title,))
    row = c.fetchone()

    if not row:
        await ctx.send("❌ That title isn’t in the database yet. Use `!add` first.")
        return

    media_id = row[0]
    c.execute("""UPDATE user_library 
                 SET rating=? 
                 WHERE user_id=? AND media_type=? AND media_id=?""",
              (rating, user_id, media_type.lower(), media_id))
    conn.commit()

    await ctx.send(f"⭐ You rated {title} a {rating}/10!")

@bot.command()
async def status(ctx, media_type: str, title: str, new_status: str):
    """Update status (reading/watching, dropped, planned, completed)."""
    user_id = get_or_create_user(ctx.author)

    if new_status.lower() not in ("completed", "reading", "dropped", "planned"):
        await ctx.send("❌ Status must be: completed, reading, dropped, or planned.")
        return

    if media_type.lower() == "anime":
        c.execute("SELECT anime_id FROM anime WHERE title=?", (title,))
    else:
        c.execute("SELECT manga_id FROM manga WHERE title=?", (title,))
    row = c.fetchone()

    if not row:
        await ctx.send("❌ That title isn’t in the database yet. Use `!add` first.")
        return

    media_id = row[0]
    c.execute("""UPDATE user_library 
                 SET status=? 
                 WHERE user_id=? AND media_type=? AND media_id=?""",
              (new_status.lower(), user_id, media_type.lower(), media_id))
    conn.commit()

    await ctx.send(f"📌 Status for {title} updated to **{new_status}**.")

@bot.command()
async def profile(ctx, member: discord.Member = None):
    """Show a user's profile with badges."""
    member = member or ctx.author
    user_id = get_or_create_user(member)

    # Count anime & manga
    c.execute("SELECT COUNT(*) FROM user_library WHERE user_id=? AND media_type='anime'", (user_id,))
    anime_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM user_library WHERE user_id=? AND media_type='manga'", (user_id,))
    manga_count = c.fetchone()[0]

    # Badge system (based on manga read)
    if manga_count >= 100:
        badge = "👑 Legend"
    elif manga_count >= 51:
        badge = "🏆 Veteran"
    elif manga_count >= 11:
        badge = "📚 Reader"
    elif manga_count >= 1:
        badge = "📘 Beginner"
    else:
        badge = "❌ No manga yet"

    # Currently reading/watching
    c.execute("""SELECT a.title 
                 FROM user_library l
                 JOIN anime a ON l.media_id = a.anime_id
                 WHERE l.user_id=? AND l.media_type='anime' AND l.status='reading'""", (user_id,))
    current_anime = [row[0] for row in c.fetchall()]

    c.execute("""SELECT m.title 
                 FROM user_library l
                 JOIN manga m ON l.media_id = m.manga_id
                 WHERE l.user_id=? AND l.media_type='manga' AND l.status='reading'""", (user_id,))
    current_manga = [row[0] for row in c.fetchall()]

    embed = discord.Embed(title=f"{member.display_name}'s Profile", color=0x00ff99)
    embed.add_field(name="📺 Anime Watched", value=str(anime_count), inline=True)
    embed.add_field(name="📖 Manga Read", value=str(manga_count), inline=True)
    embed.add_field(name="🏅 Badge", value=badge, inline=False)

    if current_anime:
        embed.add_field(name="▶️ Currently Watching", value=", ".join(current_anime), inline=False)
    if current_manga:
        embed.add_field(name="📖 Currently Reading", value=", ".join(current_manga), inline=False)

    await ctx.send(embed=embed)

@bot.command()
async def leaderboard(ctx, category: str):
    """Show leaderboard for anime or manga."""
    if category.lower() not in ("anime", "manga"):
        await ctx.send("❌ Use `anime` or `manga`.")
        return

    c.execute("""SELECT u.display_name, COUNT(*) as count
                 FROM user_library l
                 JOIN users u ON l.user_id = u.user_id
                 WHERE l.media_type=?
                 GROUP BY u.user_id
                 ORDER BY count DESC
                 LIMIT 10""", (category.lower(),))
    rows = c.fetchall()

    leaderboard = "\n".join([f"{i+1}. {name} — {count}" for i,(name,count) in enumerate(rows)])
    await ctx.send(f"📊 **{category.capitalize()} Leaderboard** 📊\n{leaderboard}")

@bot.command()
async def helpme(ctx):
    """Custom help command."""
    embed = discord.Embed(title="📖 Anime/Manga Bot Commands", color=0x7289DA)
    embed.add_field(name="!add [anime|manga] <title>", value="Add a title to your list", inline=False)
    embed.add_field(name="!rate [anime|manga] <title> <rating>", value="Rate something 0–10", inline=False)
    embed.add_field(name="!status [anime|manga] <title> <status>", value="Update status (reading, dropped, planned, completed)", inline=False)
    embed.add_field(name="!leaderboard [anime|manga]", value="Show top readers/watchers", inline=False)
    embed.add_field(name="!profile [@user]", value="Show your profile (with badges)", inline=False)
    embed.add_field(name="!helpme", value="Show this help menu", inline=False)

    await ctx.send(embed=embed)

# Run bot
bot.run(TOKEN)

