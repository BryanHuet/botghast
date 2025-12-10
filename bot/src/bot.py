import discord
import logging
import os
import json
import random
from datetime import datetime
from discord.ext import commands
from dotenv import load_dotenv
from google import genai
from setproctitle import setproctitle

setproctitle("BotGhast")
load_dotenv()

logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s %(message)s]",
        handlers=[
            logging.StreamHandler()
            ]
        )

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="$", intents=intents)

client = genai.Client()

gifs = 'data/gifs.json'
@commands.command()
async def donneavis(ctx):
    if not os.path.exists(gifs):
        print(f"Error: The file {instructions} does not exist.")
        return
    
    if not ctx.message.reference:
        await ctx.reply("Aucun message sélectionné, tu veux que je réagisse à quoi là ???")
        return
    
    referenced_message = await ctx.message.channel.fetch_message(ctx.message.reference.message_id)
    replied_text = referenced_message.content

    try:
        with open(gifs, 'r', encoding='utf-8') as file:
            gifs_list = json.load(file)['gifs']
        random.shuffle(gifs_list)
        gif = random.choice(gifs_list)
       
        response = f"""
        {gif}
        """
        
        await referenced_message.reply(response)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await ctx.send('J\'ai besoin de repos...')



quotes = 'data/quotes.json'
@commands.command()
async def citation(ctx):
    if not os.path.exists(quotes):
        print(f"Error: The file {quotes} does not exist.")
    else:
        try:
            with open(quotes, 'r', encoding='utf-8') as file:
                data = json.load(file)

            random_quote = random.choice(data)

            quote = f"{random_quote['citation']} ~ {random_quote['author']}"
            await ctx.send(quote)

        except json.JSONDecodeError as e:
            print(f"Error: Failed to parse JSON file. {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


bot.add_command(donneavis)
bot.add_command(citation)

if __name__=="__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)


