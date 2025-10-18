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

gods = 'data/gods.json'
@commands.command()
async def donneavis(ctx):
    if not os.path.exists(gods):
        print(f"Error: The file {instructions} does not exist.")
        return
    
    if not ctx.message.reference:
        await ctx.reply("Aucun message sélectionné, tu veux que je répondre à quoi là ???")
        return
    
    referenced_message = await ctx.message.channel.fetch_message(ctx.message.reference.message_id)
    replied_text = referenced_message.content

    try:
        with open(gods, 'r', encoding='utf-8') as file:
            gods_list = json.load(file)
        random.shuffle(gods_list)
        god = random.choice(gods_list)
        random.shuffle(gods_list)

        god_instruct = f"Tu es le dieu {god['name']} de la {god['mythology']}. Voici son profil: {god['characteristics']}"
        prompt = f"""
{god_instruct}

**Instructions** : Tu es un dieu et répondez à ce message en adoptant l'attitude émotionnelle de ce dieu. Commencez votre réponse en indiquant le dieu choisi (ex. : "Zeus parle:"). La reponse ne doit pas etre longue, au maximum 5 lignes. Donnez votre avis sur le message suivant, ne pas le prendre personellement mais comme un dieu exterieur a la conversation : {replied_text}
"""



        response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
        )
        message = f"{god['emoji']} {response.text}"
        await ctx.reply(message)

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        await ctx.send('Les dieux sont au repos...')



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


