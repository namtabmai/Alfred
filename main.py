#!/bin/env python

import asyncio
from config import Config
import discord
import logging
import reddit

__version__ = '0.9'

if __name__ == "__main__":
    try:
        logging.basicConfig(format="%(asctime)s [%(levelname)-8s] [%(module)-8s] %(message)s", level=logging.INFO)
        logging.info("Starting Alfred version {0}".format(__version__))
        config = Config("alfred.db")

        token = config.get("token")

        loglevel = config.get("log_level", fallback="INFO")
        logging.getLogger().setLevel(loglevel)
        logFileHandler = logging.FileHandler("alfred.log")
        logFileHandler.setLevel(logging.DEBUG)
        logging.getLogger().addHandler(logFileHandler)


        logging.info("Starting discord client using token={0}, log_level={1}".format(token, loglevel))

        client = discord.Client()
        reddit = reddit.Reddit(config)
        client.loop.create_task(reddit.check_feeds(client))
        client.run(token)

    except Exception as err:
        logging.exception("Error reading configuration file.\r\n{0}\r\n".format(err))


