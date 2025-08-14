import bot # Import your bot.py file

# This block ensures the bot starts when Replit runs main.py
if __name__ == '__main__':
    # Check if the token is set (it will be None if not found in Replit Secrets)
    if bot.TOKEN is None:
        print("FATAL ERROR: DISCORD_BOT_TOKEN environment variable not set in Replit Secrets.")
        print("Please go to the 'Secrets' tab (padlock icon) on Replit and add 'DISCORD_BOT_TOKEN' with your bot's actual token as the value.")
    else:
        print(f"Starting bot with token: {bot.TOKEN[:5]}...") # Print first 5 chars for verification
        bot.bot.run(bot.TOKEN) # Run the bot instance from the 'bot' module