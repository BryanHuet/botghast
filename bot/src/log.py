"""
Logging setup of BotGhast: the shared 'botghast' logger, with Europe/Paris timestamps.
"""

import datetime
import logging

import pytz


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


logger = logging.getLogger('botghast')
logger.setLevel(logging.INFO)

# Guard against adding the handlers twice if the module is reloaded
if not logger.handlers:
    formatter = ParisTimeFormatter()
    for handler in (logging.StreamHandler(), logging.FileHandler('botghast.log', encoding='utf-8')):
        handler.setFormatter(formatter)
        logger.addHandler(handler)
