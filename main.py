#!/bin/env python

import asyncio
import configparser
import discord
import logging
import reddit

__version__ = '0.2'

if __name__ == "__main__":
    try:
        logging.basicConfig(format="%(asctime)s %(levelname)-8s %(message)s", level=logging.INFO)
        logging.info("Starting Alfred version {0}".format(__version__))
        config = configparser.ConfigParser()
        config.read("alfred.ini")

        token = config.get("main", "token")

        loglevel = config.get("main", "log_level", fallback="INFO")
        logging.basicConfig(level=loglevel)

        logging.info("Starting discord client using token={0}".format(token))

        client = discord.Client()
        reddit = reddit.Reddit(config)
        client.loop.create_task(reddit.check_feeds(client))
        client.run(token)

    except (KeyError, configparser.NoSectionError, configparser.NoOptionError) as err:
        logging.exception("Error reading configuration file.\r\n{0}\r\n".format(err))





