import asyncio
import discord
import feedparser
import logging
from datetime import datetime
import time

class Reddit:
    def __init__(self, config):
        logging.info("Reddit::__init__")

        self.time_format = '%Y-%m-%d %H:%M:%S'
        self.config = config

        self.load_settings()

    def load_settings(self):
        self.update_frequency = 300
        self.subreddits = ()
        self.shit_posters = []

        try:
            self.update_frequency = self.config.get("reddit_update_frequency", fallback=300)
            self.reddit = self.config.get_reddit()
            subreddits = {r.subreddit for r in self.reddit}
            self.subreddits = [subreddit for subreddit in subreddits]
        except:
            logging.exception("Could not initialise reddit")

        logging.info("Update frequency {0}".format(self.update_frequency))

    def get_rss_posts(self, subreddit):
        logging.debug("Reddit::get_rss_posts")

        new_posts = []
        try:
            rss = feedparser.parse('https://rss.reddit.com/r/{0}/new'.format(subreddit))

            last_updated = [reddit.last_updated for reddit in self.reddit if reddit.subreddit == subreddit][0]
            logging.debug("Checking for updated to {0} since {1}".format(subreddit, time.strftime(self.time_format, last_updated)))

            # Just work out the last update time, presume all the posts have already been seen
            for entry in rss['entries'][::-1]:
                entry_updated = entry['updated_parsed']
                logging.debug('Comparing {0} to {1}'.format(time.strftime(self.time_format, entry_updated), time.strftime(self.time_format, last_updated)))
                if entry_updated > last_updated:
                    logging.debug('Found entry {0}'.format(entry.title))
                    new_posts.append(entry)
                    last_updated = entry_updated

            # Mark the subreddit as read
            logging.debug('Marking {0} last entry as {1}'.format(subreddit, time.strftime(self.time_format, last_updated)))

            self.config.update_reddit(subreddit, time.gmtime())
        except:
            logging.exception('Failed to get feed for {0}'.format(subreddit))

        return new_posts

    async def send_reddit_link(self, client, channel, post):
        logging.debug('Sending post {0} to server {1} ({2}) - channel {3} ({4})'.format(post.link, channel.server.name, channel.server.id, channel.name, channel.id))

        post_type = "shit post" if post.author[3:].lower() in self.shit_posters else "post"
        message = "New {0} by {1}\r\n{2}".format(post_type, post.author, post.link)

        await client.send_message(channel, message)

    async def check_feeds(self, client):
        logging.info("Reddit::check_feeds")

        await client.wait_until_ready()

        for r in self.reddit:
            logging.info("Announcing the subreddit {0} to server {1} ({2}), channel {3} ({4})".format(
                r.subreddit,
                r.server['name'],
                r.server['discord_id'],
                r.channel['name'],
                r.channel['discord_id']
            ))

        while not client.is_closed:
            # Loop through all the rss feeds that have been updated
            for subreddit in self.subreddits:
                # Get all the latest posts for the subreddit
                new_posts = self.get_rss_posts(subreddit)

                # Loop through all the channels we need to post this update to
                for channel in [reddit.channel for reddit in self.reddit if reddit.subreddit is subreddit]:
                    # get the discord channel from our channel
                    discord_channels = [dc for dc in client.get_all_channels() if dc.id == channel['discord_id']]
                    for dc in discord_channels:
                        for post in new_posts:
                            await self.send_reddit_link(client, dc, post)
            await asyncio.sleep(self.update_frequency)

