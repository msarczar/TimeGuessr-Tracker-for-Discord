import discord
from discord.ext import commands
import re
import datetime
from collections import defaultdict
import asyncio
import os # For environment variables

import database # Your database.py file

# --- Configuration ---
# Your Discord Bot Token will be loaded from Replit's "Secrets" environment variables.
TOKEN = os.getenv('DISCORD_BOT_TOKEN') 

# The ID of the specific channel on your *new* Discord server where TimeGuessr scores will be posted.
# When you invite the bot to the new server, go to that server's score channel,
# right-click -> Copy ID (Developer Mode must be enabled in Discord settings).
# Then, replace this placeholder with that actual channel ID (as a number, NO QUOTES).
SCORE_CHANNEL_ID = 1391639706416054323 # <<< REPLACE THIS!

# Enable Message Content Intent in your Discord Developer Portal -> Bot -> Privileged Gateway Intents
intents = discord.Intents.default()
intents.message_content = True
# If you want !my_stats to work across servers (using display_name for consistency),
# and get member objects for all users, you might need:
# intents.members = True # Ensure this is enabled in Dev Portal -> Bot -> Privileged Gateway Intents

bot = commands.Bot(command_prefix='!', intents=intents)

# --- Streak Tracking Logic ---
def calculate_streaks(guild_id, player_id):
    """
    Calculates the current consecutive daily streak for a player within a specific guild.
    A streak means posting a score every day for N consecutive days, ending today or yesterday.
    """
    player_scores = database.get_scores(guild_id=guild_id, player_id=player_id)
    
    if not player_scores:
        return 0, 0, "No scores yet."

    posted_dates_str = sorted(list(set([score[3] for score in player_scores])))
    posted_dates = [datetime.datetime.strptime(d, '%Y-%m-%d').date() for d in posted_dates_str]

    if not posted_dates:
        return 0, 0, "No scores found for streak calculation."

    current_streak = 0
    longest_streak = 0
    
    today = datetime.date.today()
    
    if posted_dates[-1] == today:
        current_streak = 1
        for i in range(len(posted_dates) - 2, -1, -1):
            if (posted_dates[i+1] - posted_dates[i]).days == 1:
                current_streak += 1
            else:
                break
    elif posted_dates[-1] == today - datetime.timedelta(days=1):
        current_streak = 1
        for i in range(len(posted_dates) - 2, -1, -1):
            if (posted_dates[i+1] - posted_dates[i]).days == 1:
                current_streak += 1
            else:
                break
    else:
        current_streak = 0

    temp_longest_streak = 0
    if posted_dates:
        temp_longest_streak = 1
        for i in range(1, len(posted_dates)):
            if (posted_dates[i] - posted_dates[i-1]).days == 1:
                temp_longest_streak += 1
            else:
                longest_streak = max(longest_streak, temp_longest_streak)
                temp_longest_streak = 1
        longest_streak = max(longest_streak, temp_longest_streak)

    current_streak_status = ""
    if current_streak == 0:
        current_streak_status = "No active streak."
    elif today in posted_dates:
        current_streak_status = f"Currently on a {current_streak}-day streak! 🎉"
    elif (today - datetime.timedelta(days=1)) in posted_dates and today not in posted_dates:
        current_streak_status = f"Had a {current_streak}-day streak, but it ended yesterday."
    else:
        current_streak_status = "No active streak."

    return current_streak, longest_streak, current_streak_status


# --- Initialize the database when the bot starts ---
@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    database.init_db()

# --- Automatic Score Ingestion (on_message event) ---
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    if message.guild is None: # Ignore DMs
        await bot.process_commands(message)
        return

    # ONLY process messages in the designated score channel for this server.
    # If you want the bot to listen for scores in *any* channel it can see on this server,
    # you can remove this 'if' block.
    if message.channel.id != SCORE_CHANNEL_ID:
        await bot.process_commands(message)
        return

    # Regex to find "TimeGuessr #<num> <score>/<max_score>"
    pattern = r"TimeGuessr #(\d+)\s+(\d{1,3}(?:,\d{3})*)/(\d{1,3}(?:,\d{3})*)"

    match = re.search(pattern, message.content)

    if match:
        try:
            game_number = int(match.group(1))
            score_str = match.group(2).replace(',', '') 
            max_score_str = match.group(3).replace(',', '') 

            score = int(score_str)
            max_score = int(max_score_str)

            guild_id = str(message.guild.id)
            player_id = str(message.author.id)
            player_name = message.author.display_name 
            game_date = message.created_at.strftime('%Y-%m-%d')
            message_id = str(message.id)

            if database.add_score(guild_id, player_id, player_name, game_date, score, max_score, game_number, message_id):
                await message.channel.send(f"✅ TimeGuessr score from **{player_name}** ({score}/{max_score}) recorded!")
                current_streak, longest_streak, streak_status = calculate_streaks(guild_id, player_id)
                if current_streak > 0 and "Currently on a" in streak_status:
                    await message.channel.send(f"➡️ **{player_name}**: {streak_status}")

            else:
                pass 
        except ValueError as ve:
            print(f"Error parsing TimeGuessr score: {ve} in message: {message.content}")
            await message.channel.send("Hmm, I detected a TimeGuessr score but couldn't parse the numbers. Please ensure they are in the format `SCORE/MAX_SCORE` (e.g., `46,415/50,000`).")
        except Exception as e:
            print(f"An unexpected error occurred during score recording: {e}")
            await message.channel.send(f"An unexpected error occurred while recording the score. Error: {e}")

    await bot.process_commands(message)

# --- Helper function to format leaderboards ---
def format_leaderboard(scores_data, title, mode='average'):
    if not scores_data:
        return f"No TimeGuessr scores found for {title}."

    player_stats = defaultdict(lambda: {'total_score': 0, 'games_played': 0, 'best_score': 0, 'worst_score': float('inf'), 'player_name': ''})
    for player_id, player_name, score, _ in scores_data:
        player_stats[player_id]['player_name'] = player_name
        player_stats[player_id]['total_score'] += score
        player_stats[player_id]['games_played'] += 1
        player_stats[player_id]['best_score'] = max(player_stats[player_id]['best_score'], score)
        player_stats[player_id]['worst_score'] = min(player_stats[player_id]['worst_score'], score)
    
    if mode == 'average':
        sorted_players = sorted(player_stats.items(), key=lambda item: item[1]['total_score'] / item[1]['games_played'], reverse=True)
        leaderboard_msg = f"🏆 **TimeGuessr Leaderboard - {title} (Average Score)** 🏆\n"
        for i, (player_id, stats) in enumerate(sorted_players):
            avg_score = stats['total_score'] / stats['games_played']
            leaderboard_msg += f"{i+1}. **{stats['player_name']}**: Average {avg_score:.2f} ({stats['games_played']} games)\n"
    elif mode == 'daily_high': 
        daily_highs = {}
        for player_id, player_name, score, _ in scores_data:
            if player_id not in daily_highs or score > daily_highs[player_id]['score']:
                daily_highs[player_id] = {'player_name': player_name, 'score': score}
        
        sorted_daily_highs = sorted(daily_highs.items(), key=lambda item: item[1]['score'], reverse=True)
        leaderboard_msg = f"🌟 **TimeGuessr Scores - {title} (Highest Today)** 🌟\n"
        for i, (player_id, data) in enumerate(sorted_daily_highs):
            leaderboard_msg += f"{i+1}. **{data['player_name']}**: {data['score']}\n"

    return leaderboard_msg

# --- Discord Commands ---

@bot.command(name='leaderboard', aliases=['lb', 'overall'])
async def overall_leaderboard(ctx):
    """Shows the overall TimeGuessr leaderboard (average score) for this server."""
    if ctx.guild is None:
        await ctx.send("This command can only be used in a Discord server.")
        return
    scores = database.get_scores(guild_id=str(ctx.guild.id))
    msg = format_leaderboard(scores, "All Time", mode='average')
    await ctx.send(msg)

@bot.command(name='today', aliases=['daily'])
async def daily_scores(ctx):
    """Shows all TimeGuessr scores posted today for this server."""
    if ctx.guild is None:
        await ctx.send("This command can only be used in a Discord server.")
        return
    today = datetime.date.today().isoformat()
    scores = database.get_scores(guild_id=str(ctx.guild.id), start_date=today, end_date=today)
    msg = format_leaderboard(scores, "Today", mode='daily_high')
    await ctx.send(msg)

@bot.command(name='week', aliases=['weekly'])
async def weekly_leaderboard(ctx):
    """Shows the TimeGuessr leaderboard for the past 7 days (average score) for this server."""
    if ctx.guild is None:
        await ctx.send("This command can only be used in a Discord server.")
        return
    today = datetime.date.today()
    one_week_ago = today - datetime.timedelta(days=6)
    
    start_date = one_week_ago.isoformat()
    end_date = today.isoformat()

    scores = database.get_scores(guild_id=str(ctx.guild.id), start_date=start_date, end_date=end_date)
    msg = format_leaderboard(scores, "Past 7 Days", mode='average')
    await ctx.send(msg)

@bot.command(name='month', aliases=['monthly'])
async def monthly_leaderboard(ctx):
    """Shows the TimeGuessr leaderboard for the past 30 days (average score) for this server."""
    if ctx.guild is None:
        await ctx.send("This command can only be used in a Discord server.")
        return
    today = datetime.date.today()
    thirty_days_ago = today - datetime.timedelta(days=29)
    
    start_date = thirty_days_ago.isoformat()
    end_date = today.isoformat()

    scores = database.get_scores(guild_id=str(ctx.guild.id), start_date=start_date, end_date=end_date)
    msg = format_leaderboard(scores, "Past 30 Days", mode='average')
    await ctx.send(msg)

@bot.command(name='my_stats', aliases=['mystats', 'stats'])
async def my_stats(ctx):
    """Shows your personal TimeGuessr statistics, including streaks, for this server."""
    if ctx.guild is None:
        await ctx.send("This command can only be used in a Discord server.")
        return
    player_id = str(ctx.author.id)
    player_name = ctx.author.display_name
    guild_id = str(ctx.guild.id)
    
    scores = database.get_scores(guild_id=guild_id, player_id=player_id)
    
    if not scores:
        await ctx.send(f"No TimeGuessr scores found for **{player_name}** in this server. Start posting to see your stats!")
        return

    total_score = sum(s[2] for s in scores)
    games_played = len(scores)
    average_score = total_score / games_played
    best_score = max(s[2] for s in scores)
    worst_score = min(s[2] for s in scores)

    current_streak, longest_streak, streak_status_msg = calculate_streaks(guild_id, player_id)

    stats_msg = f"📊 **{player_name}'s TimeGuessr Statistics (This Server)** 📊\n"
    stats_msg += f"• Games Played: {games_played}\n"
    stats_msg += f"• Overall Average Score: {average_score:.2f}\n"
    stats_msg += f"• Personal Best: {best_score}\n"
    stats_msg += f"• Personal Worst: {worst_score}\n"
    stats_msg += f"• Current Streak: {current_streak} days\n"
    stats_msg += f"• Longest Streak: {longest_streak} days\n"
    stats_msg += f"  *({streak_status_msg})*\n"
    
    today = datetime.date.today()
    seven_days_ago = today - datetime.timedelta(days=6)
    recent_scores = database.get_scores(guild_id=guild_id, player_id=player_id, start_date=seven_days_ago.isoformat(), end_date=today.isoformat())
    if recent_scores:
        recent_avg = sum(s[2] for s in recent_scores) / len(recent_scores)
        stats_msg += f"• Last 7 Days Average: {recent_avg:.2f} ({len(recent_scores)} games)\n"

    await ctx.send(stats_msg)


@bot.command(name='import_history', aliases=['synchistory', 'importscores'])
@commands.has_permissions(manage_guild=True) 
async def import_history(ctx, limit: int = 500):
    """
    Imports TimeGuessr scores from the current channel's history into the database.
    Usage: !import_history [limit] (default limit is 500 messages, max 10000)
    Only callable by users with 'Manage Server' permission.
    """
    if ctx.guild is None:
        await ctx.send("This command can only be used in a Discord server.")
        return

    if limit > 10000:
        limit = 10000
        await ctx.send("Import limit capped at 10000 messages per run. For more, run multiple times.")
    
    status_message = await ctx.send(f"Starting to import TimeGuessr scores from the last {limit} messages in this channel. This may take a moment...")

    imported_count = 0
    skipped_duplicates = 0
    skipped_non_scores = 0
    
    guild_id = str(ctx.guild.id)
    
    pattern = r"TimeGuessr #(\d+)\s+(\d{1,3}(?:,\d{3})*)/(\d{1,3}(?:,\d{3})*)"
    
    messages_fetched = 0
    
    async for message in ctx.channel.history(limit=limit, oldest_first=True): 
        messages_fetched += 1
        if message.author == bot.user:
            continue
        if message.guild is None:
            continue

        match = re.search(pattern, message.content)
        if match:
            try:
                game_number = int(match.group(1))
                score_str = match.group(2).replace(',', '')
                max_score_str = match.group(3).replace(',', '')
                score = int(score_str)
                max_score = int(max_score_str)

                player_id = str(message.author.id)
                player_name = message.author.display_name
                game_date = message.created_at.strftime('%Y-%m-%d')
                message_id = str(message.id)

                if database.add_score(guild_id, player_id, player_name, game_date, score, max_score, game_number, message_id):
                    imported_count += 1
                else:
                    skipped_duplicates += 1
            except ValueError:
                skipped_non_scores += 1
            except Exception as e:
                print(f"Error processing historical message {message.id}: {e}")
                skipped_non_scores += 1
        else:
            skipped_non_scores += 1

        if messages_fetched % 100 == 0: 
            await status_message.edit(content=f"Importing... Processed {messages_fetched}/{limit} messages. Found {imported_count} scores so far.")
        
        await asyncio.sleep(0.1) 

    await status_message.edit(content=f"✅ History import complete! Processed {messages_fetched} messages. Imported {imported_count} new scores. Skipped {skipped_duplicates} duplicates and {skipped_non_scores} non-score messages.")

@import_history.error
async def import_history_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have permission to run this command. You need 'Manage Server' permission.")
    elif isinstance(error, commands.TooManyArguments):
        await ctx.send("Too many arguments for !import_history. Usage: `!import_history [limit]`")
    else:
        await ctx.send(f"An error occurred while importing history: {error}")

# Removed the if __name__ == '__main__': block, as main.py will handle bot.run(TOKEN)