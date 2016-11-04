import asyncio
import discord
import feedparser
import logging
import time

class Reddit:
    def __init__(self, config):
        logging.info("Reddit::__init__")

        self.time_format = '%Y-%m-%d %H:%M:%S'

        self.subreddits = ()
        try:
            subreddits = config.get("reddit", "subreddits")
            self.subreddits = [(subreddit, time.gmtime()) for subreddit in subreddits.split(",")]
        except:
            logging.exception("Could not initialise reddit")

        self.update_frequency = config.getint("reddit", "update_frequency", fallback=300)

    async def check_feeds(self, client):
        logging.info("Reddit::check_feeds")

        await client.wait_until_ready()

        # Find all the channels to announce to
        self.channels = [channel for channel in client.get_all_channels() if channel.name == "general"]

        for channel in self.channels:
            logging.info("Announcing the subreddits {0} to server {1} ({2}), channel {3} ({4})".format(
                ",".join([subreddit[0] for subreddit in self.subreddits]),
                channel.server.name, channel.server.id,
                channel.name, channel.id
            ))

        while not client.is_closed:
            # Get a list of all the latest posts
            new_posts = []
            for i, (name, last_updated) in enumerate(self.subreddits):
                logging.debug("Checking for updated to {0} since {1}".format(name, time.strftime(self.time_format, last_updated)))

                # Grab the feeds
                try:
                    rss = feedparser.parse('https://rss.reddit.com/r/{0}/new'.format(name))

                    # Just work out the last update time, presume all the posts have already been seen
                    for entry in rss['entries'][::-1]:
                        entry_updated = entry['updated_parsed']
                        logging.debug('Comparing {0} to {1}'.format(time.strftime(self.time_format, entry_updated), time.strftime(self.time_format, last_updated)))
                        if entry_updated > last_updated:
                            logging.debug('Found entry {0}'.format(entry.title))
                            new_posts.append(entry)
                            last_updated = entry_updated

                    # Mark the subreddit as read
                    logging.debug('Marking {0} last entry as {1}'.format(name, time.strftime(self.time_format, last_updated)))
                    self.subreddits[i] = (name, last_updated)
                except:
                    logging.exception('Failed to get feed for {0}'.format(name))

            for channel in self.channels:
                for post in new_posts:
                    logging.debug('Sending post {0} to {1} ({2})'.format(post.link, channel.name, channel.id))

                    message = "New post by {0}\r\n{1}".format(post.author, post.link)

                    await client.send_message(channel, message)
            await asyncio.sleep(self.update_frequency)

