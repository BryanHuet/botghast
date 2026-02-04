"""
BotGhast - A Discord bot for sharing random GIFs and quotes.

This bot provides two main commands:
- donneavis: Reply to a referenced message with a random GIF
- citation: Send a random quote from a collection

Features:
- Configurable command prefix via BOT_PREFIX environment variable
- Configurable data file paths via GIFS_FILE and QUOTES_FILE environment variables
- JSON structure validation for data files
- Comprehensive error handling and logging
"""

import discord
import logging
import os
import json
import random
from discord.ext import commands
from dotenv import load_dotenv
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

PREFIX = os.getenv('BOT_PREFIX', '$')
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

gifs = os.getenv('GIFS_FILE', 'data/gifs.json')
quotes = os.getenv('QUOTES_FILE', 'data/quotes.json')


def validate_gifs_json(data):
    """
    Validate the structure of gifs.json file.
    
    Args:
        data: Parsed JSON data from gifs.json file
        
    Returns:
        None
        
    Raises:
        ValueError: If the JSON structure is invalid
        
    Expected structure:
        {
            "gifs": ["gif_url_1", "gif_url_2", ...]
        }
    """
    if not isinstance(data, dict) or 'gifs' not in data:
        raise ValueError("Invalid gifs.json structure: expected {'gifs': [...]}")
    if not isinstance(data['gifs'], list):
        raise ValueError("Invalid gifs.json structure: 'gifs' should be an array")


def validate_quotes_json(data):
    """
    Validate the structure of quotes.json file.
    
    Args:
        data: Parsed JSON data from quotes.json file
        
    Returns:
        None
        
    Raises:
        ValueError: If the JSON structure is invalid
        
    Expected structure:
        [
            {
                "citation": "quote text",
                "author": "author name"
            },
            ...
        ]
    """
    if not isinstance(data, list):
        raise ValueError("Invalid quotes.json structure: expected array of quotes")
    for quote in data:
        if not isinstance(quote, dict) or 'citation' not in quote or 'author' not in quote:
            raise ValueError(f"Invalid quote structure: {quote}")


@bot.command()
async def donneavis(ctx):
    """
    Reply to a referenced message with a random GIF.
    
    This command requires a message reference (reply to another message).
    It will reply to the referenced message with a random GIF from the gifs.json file.
    
    Args:
        ctx: discord.ext.commands.Context object containing message information
        
    Returns:
        None
        
    Raises:
        Exception: If file operations fail, JSON parsing fails, or no message is referenced
        
    Usage:
        Reply to any message with: $donneavis
    """
    if not os.path.exists(gifs):
        logging.error(f"Error: The file {gifs} does not exist.")
        return

    if not ctx.message.reference:
        await ctx.reply(
            "Aucun message sélectionné, tu veux que je réagisse à quoi là ???")
        return

    try:
        referenced_message = await ctx.message.channel.fetch_message(
            ctx.message.reference.message_id)
        # Validate message exists and is accessible
        if not referenced_message:
            await ctx.reply("Le message référencé n'existe pas ou n'est pas accessible.")
            return
    except discord.NotFound:
        await ctx.reply("Le message référencé n'a pas été trouvé.")
        return
    except discord.Forbidden:
        await ctx.reply("Je n'ai pas la permission d'accéder à ce message.")
        return
    except Exception as e:
        logging.error(f"Error fetching referenced message: {e}")
        await ctx.reply("Une erreur est survenue lors de la récupération du message.")
        return

    try:
        with open(gifs, 'r', encoding='utf-8') as file:
            gifs_data = json.load(file)
        validate_gifs_json(gifs_data)
        gifs_list = gifs_data['gifs']
        random.shuffle(gifs_list)
        gif = random.choice(gifs_list)
        response = f"""
        {gif}
        """
        await referenced_message.reply(response)

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        await ctx.send('J\'ai besoin de repos...')


@bot.command()
async def citation(ctx):
    """
    Send a random quote from the quotes collection.
    
    This command selects a random quote from the quotes.json file and sends it
    to the channel where the command was invoked.
    
    Args:
        ctx: discord.ext.commands.Context object containing message information
        
    Returns:
        None
        
    Raises:
        Exception: If file operations fail or JSON parsing fails
        
    Usage:
        $citation
        
    Quote format:
        "quote text" ~ author name
    """
    if not os.path.exists(quotes):
        logging.error(f"Error: The file {quotes} does not exist.")
        await ctx.reply("Le fichier de citations est introuvable.")
        return
    
    if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        logging.error("Bot does not have permission to send messages in this channel")
        return

    try:
        with open(quotes, 'r', encoding='utf-8') as file:
            data = json.load(file)
        validate_quotes_json(data)

        if not data:
            await ctx.reply("Aucune citation disponible.")
            return

        random_quote = random.choice(data)

        # Validate quote structure
        if not isinstance(random_quote, dict):
            await ctx.reply("Format de citation invalide.")
            return
        
        if 'citation' not in random_quote or 'author' not in random_quote:
            await ctx.reply("Citation incomplète - format invalide.")
            return

        quote = f"{random_quote['citation']} ~ {random_quote['author']}"
        await ctx.send(quote)

    except json.JSONDecodeError as e:
        logging.error(f"Error: Failed to parse JSON file. {e}")
        await ctx.reply("Erreur de format dans le fichier de citations.")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        await ctx.reply("Une erreur est survenue lors de la récupération de la citation.")




@bot.command(name='aide', help='Show available commands and usage')
async def help_command(ctx):
    """
    Display help information about available commands.
    
    Args:
        ctx: discord.ext.commands.Context object
        
    Returns:
        None
    """
    help_text = f"""
    **BotGhast Aide** - Préfixe de commande: `{PREFIX}`
    
    {PREFIX}aide - Afficher ce message d'aide
    {PREFIX}donneavis - Répondre à un message avec un GIF aléatoire
    {PREFIX}citation - Obtenir une citation philosophique aléatoire
    {PREFIX}searchquote <mot-clé> - Rechercher des citations par mot-clé
    
    Utilisez `{PREFIX}aide` pour voir cette liste à tout moment !
    """
    await ctx.send(help_text)





@bot.command(name='searchquote', help='Search quotes by keyword')
async def search_quote(ctx, *, keyword: str):
    """
    Search quotes by keyword in citation text or author name.
    
    Args:
        ctx: discord.ext.commands.Context object
        keyword: Search term to look for in quotes
        
    Returns:
        None
    """
    if not keyword:
        await ctx.reply("Veuillez fournir un mot-clé de recherche.")
        return
    
    if not os.path.exists(quotes):
        await ctx.reply("Le fichier de citations est introuvable.")
        return

    try:
        with open(quotes, 'r', encoding='utf-8') as file:
            quotes_data = json.load(file)
        validate_quotes_json(quotes_data)
        
        if not quotes_data:
            await ctx.reply("Aucune citation disponible.")
            return

        # Search in both citation text and author
        keyword_lower = keyword.lower()
        results = []
        
        for quote in quotes_data:
            citation_text = quote.get('citation', '').lower()
            author_text = quote.get('author', '').lower()
            
            if keyword_lower in citation_text or keyword_lower in author_text:
                results.append(quote)
        
        if not results:
            await ctx.reply(f"Aucune citation trouvée pour '{keyword}'.")
            return
        
        # Show first 3 results
        response = f"**Résultats pour '{keyword}':**\n"
        for i, quote in enumerate(results[:3], 1):
            response += f"{i}. {quote['citation']} ~ {quote['author']}\n"
        
        if len(results) > 3:
            response += f"... et {len(results) - 3} autres résultats."
        
        await ctx.send(response)

    except Exception as e:
        logging.error(f"Error searching quotes: {e}")
        await ctx.reply("Erreur lors de la recherche de citations.")


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)
