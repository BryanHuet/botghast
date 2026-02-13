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
import datetime
import pytz
from discord.ext import commands
from dotenv import load_dotenv
from setproctitle import setproctitle

setproctitle("BotGhast")
load_dotenv()

# Custom formatter for Europe/Paris timezone
class ParisTimeFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(fmt='%(asctime)s [%(levelname)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    def converter(self, timestamp):
        paris_tz = pytz.timezone('Europe/Paris')
        return datetime.datetime.fromtimestamp(timestamp, paris_tz)
    
    def formatTime(self, record, datefmt=None):
        dt = self.converter(record.created)
        if datefmt:
            return dt.strftime(datefmt)
        else:
            return dt.strftime('%Y-%m-%d %H:%M:%S')

# Enhanced logging configuration with Paris timezone
logger = logging.getLogger('botghast')
logger.setLevel(logging.INFO)

# Create handlers with Paris timezone formatter
stream_handler = logging.StreamHandler()
file_handler = logging.FileHandler('botghast.log', encoding='utf-8')

formatter = ParisTimeFormatter()
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)

intents = discord.Intents.default()
intents.message_content = True

PREFIX = os.getenv('BOT_PREFIX', '$')
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

gifs = os.getenv('GIFS_FILE', 'data/gifs.json')
quotes = os.getenv('QUOTES_FILE', 'data/quotes.json')

# Log bot initialization
logger.info(f"BotGhast initializing with prefix: {PREFIX}")
logger.info(f"GIFs file path: {gifs}")
logger.info(f"Quotes file path: {quotes}")


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
    logger.debug("Validating GIFs JSON structure")
    if not isinstance(data, dict) or 'gifs' not in data:
        logger.error("Invalid gifs.json structure: expected {'gifs': [...]}")
        raise ValueError("Invalid gifs.json structure: expected {'gifs': [...]}")
    if not isinstance(data['gifs'], list):
        logger.error("Invalid gifs.json structure: 'gifs' should be an array")
        raise ValueError("Invalid gifs.json structure: 'gifs' should be an array")
    logger.info(f"Successfully validated {len(data['gifs'])} GIFs")


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
    logger.debug("Validating quotes JSON structure")
    if not isinstance(data, list):
        logger.error("Invalid quotes.json structure: expected array of quotes")
        raise ValueError("Invalid quotes.json structure: expected array of quotes")
    for quote in data:
        if not isinstance(quote, dict) or 'citation' not in quote or 'author' not in quote:
            logger.error(f"Invalid quote structure: {quote}")
            raise ValueError(f"Invalid quote structure: {quote}")
    logger.info(f"Successfully validated {len(data)} quotes")


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
    logger.info(f"Command 'donneavis' invoked by {ctx.author} in channel {ctx.channel} on server {ctx.guild.name}")
    
    if not os.path.exists(gifs):
        logger.error(f"GIFs file not found: {gifs}")
        await ctx.reply("Le fichier de GIFs est introuvable.")
        return

    if not ctx.message.reference:
        logger.warning(f"No message reference found in donneavis command from {ctx.author} on server {ctx.guild.name}")
        await ctx.reply(
            "Aucun message sélectionné, tu veux que je réagisse à quoi là ???")
        return

    try:
        logger.debug(f"Fetching referenced message: {ctx.message.reference.message_id}")
        referenced_message = await ctx.message.channel.fetch_message(
            ctx.message.reference.message_id)
        # Validate message exists and is accessible
        if not referenced_message:
            logger.warning(f"Referenced message not found or not accessible on server {ctx.guild.name}")
            await ctx.reply("Le message référencé n'existe pas ou n'est pas accessible.")
            return
    except discord.NotFound:
        logger.warning(f"Referenced message not found: {ctx.message.reference.message_id} on server {ctx.guild.name}")
        await ctx.reply("Le message référencé n'a pas été trouvé.")
        return
    except discord.Forbidden:
        logger.warning(f"Permission denied accessing message: {ctx.message.reference.message_id} on server {ctx.guild.name}")
        await ctx.reply("Je n'ai pas la permission d'accéder à ce message.")
        return
    except Exception as e:
        logger.error(f"Error fetching referenced message: {e} on server {ctx.guild.name}")
        await ctx.reply("Une erreur est survenue lors de la récupération du message.")
        return

    try:
        logger.debug(f"Loading GIFs from file: {gifs}")
        with open(gifs, 'r', encoding='utf-8') as file:
            gifs_data = json.load(file)
        validate_gifs_json(gifs_data)
        gifs_list = gifs_data['gifs']
        random.shuffle(gifs_list)
        gif = random.choice(gifs_list)
        logger.info(f"Selected GIF: {gif}")
        response = f"""
        {gif}
        """
        await referenced_message.reply(response)


    except Exception as e:
        logger.error(f"Error in donneavis command: {e} on server {ctx.guild.name}")
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
    logger.info(f"Command 'citation' invoked by {ctx.author} in channel {ctx.channel} on server {ctx.guild.name}")
    
    if not os.path.exists(quotes):
        logger.error(f"Quotes file not found: {quotes}")
        await ctx.reply("Le fichier de citations est introuvable.")
        return
    
    if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        logger.error(f"Bot does not have permission to send messages in this channel on server {ctx.guild.name}")
        return

    try:
        logger.debug(f"Loading quotes from file: {quotes}")
        with open(quotes, 'r', encoding='utf-8') as file:
            data = json.load(file)
        validate_quotes_json(data)

        if not data:
            logger.warning(f"No quotes available in the database on server {ctx.guild.name}")
            await ctx.reply("Aucune citation disponible.")
            return

        random_quote = random.choice(data)
        logger.info(f"Selected quote: {random_quote['citation']} by {random_quote['author']}")

        # Validate quote structure
        if not isinstance(random_quote, dict):
            logger.error(f"Invalid quote format - not a dictionary on server {ctx.guild.name}")
            await ctx.reply("Format de citation invalide.")
            return
        
        if 'citation' not in random_quote or 'author' not in random_quote:
            logger.error(f"Invalid quote format - missing citation or author on server {ctx.guild.name}")
            await ctx.reply("Citation incomplète - format invalide.")
            return

        quote = f"{random_quote['citation']} ~ {random_quote['author']}"
        await ctx.send(quote)


    except json.JSONDecodeError as e:
        logger.error(f"JSON parsing error in quotes file: {e}")
        await ctx.reply("Erreur de format dans le fichier de citations.")
    except Exception as e:
        logger.error(f"Error in citation command: {e} on server {ctx.guild.name}")
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
    logger.info(f"Command 'aide' invoked by {ctx.author} in channel {ctx.channel} on server {ctx.guild.name}")
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
    logger.info(f"Command 'searchquote' invoked by {ctx.author} with keyword: '{keyword}' on server {ctx.guild.name}")
    
    if not keyword:
        logger.warning(f"Empty keyword provided in searchquote command on server {ctx.guild.name}")
        await ctx.reply("Veuillez fournir un mot-clé de recherche.")
        return
    
    if not os.path.exists(quotes):
        logger.error("Quotes file not found during search")
        await ctx.reply("Le fichier de citations est introuvable.")
        return

    try:
        logger.debug(f"Searching quotes for keyword: '{keyword}'")
        with open(quotes, 'r', encoding='utf-8') as file:
            quotes_data = json.load(file)
        validate_quotes_json(quotes_data)
        
        if not quotes_data:
            logger.warning("No quotes available for search")
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
        
        logger.info(f"Found {len(results)} results for keyword '{keyword}'")
        
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
        logger.error(f"Error in searchquote command: {e}")
        await ctx.reply("Erreur lors de la recherche de citations.")


if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set")
        raise ValueError("DISCORD_TOKEN environment variable is required")
    
    logger.info("Starting BotGhast...")
    logger.info(f"Using Discord token: {'*' * (len(TOKEN) - 4) + TOKEN[-4:]}")
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        logger.error(f"Bot failed to start: {e}")
        raise
