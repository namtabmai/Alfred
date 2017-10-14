import asyncio
import discord
import feedparser
import logging

class Reddit:
    def __init__(self, config):
        logging.info("Reddit::__init__")

        self.config = config

        self.update_frequency = 300
        try:
            self.update_frequency = self.config.get("reddit_update_frequency", fallback=300)
        except:
            logging.exception("Could not initialise reddit")

        logging.info("Update frequency {0}".format(self.update_frequency))

    def get_rss_posts(self, subreddit):
        logging.debug("Reddit::get_rss_posts")

        new_posts = []
        try:
            rss = feedparser.parse('https://rss.reddit.com/r/{0}/new'.format(subreddit))

            last_updated = [reddit.last_updated for reddit in self.config.get_reddit() if reddit.subreddit == subreddit][0]
            logging.debug("Checking for updated to {0} since {1}".format(subreddit, last_updated))

            # Just work out the last update time, presume all the posts have already been seen
            for entry in rss['entries'][::-1]:
                entry_updated = entry['updated']
                logging.debug('Comparing {0} to {1}'.format(entry_updated, last_updated))
                if entry_updated > last_updated:
                    logging.debug('Found entry {0}'.format(entry.title))
                    new_posts.append(entry)
                    last_updated = entry_updated

            # Mark the subreddit as read
            logging.debug('Marking {0} last entry as {1}'.format(subreddit, last_updated))

            self.config.update_reddit(subreddit, last_updated)
        except:
            logging.exception('Failed to get feed for {0}'.format(subreddit))

        return new_posts

    async def send_reddit_link(self, client, channel, post):
        logging.debug('Sending post {0} to server {1} ({2}) - channel {3} ({4})'.format(post.link, channel.server.name, channel.server.id, channel.name, channel.id))

        # Apparently the rss feed returned deleted posts. Great.
        author = post.get("author", "deleted")
        #post_type = "shit post" if author[3:].lower() in self.shit_posters else "post"
        post_type = "post"
        message = "New {0} by {1}\r\n{2}".format(post_type, author, post.link)

        await client.send_message(channel, message)

    async def check_feeds(self, client):
        logging.info("Reddit::check_feeds")

        await client.wait_until_ready()

        for r in self.config.get_reddit():
            logging.info("Announcing the subreddit {0} to server {1} ({2}), channel {3} ({4})".format(
                r.subreddit,
                r.server['name'],
                r.server['discord_id'],
                r.channel['name'],
                r.channel['discord_id']
            ))

        while not client.is_closed:
            # Grab a copy of the data at the start, incase someone tries to update while
            # we are running
            reddit_data = self.config.get_reddit()

            # Loop through all the rss feeds that have been updated
            for subreddit in {r.subreddit for r in reddit_data}:
                # Get all the latest posts for the subreddit
                new_posts = self.get_rss_posts(subreddit)
                if not new_posts:
                    continue

                for channel in [client.get_channel(reddit.channel['discord_id']) for reddit in reddit_data if reddit.subreddit == subreddit]:
                    logging.debug("Posting all new posts for subreddit {0} to {1}:{2}".format(subreddit, channel.server.name, channel.name))
                    for post in new_posts:
                        await self.send_reddit_link(client, channel, post)
            await asyncio.sleep(self.update_frequency)

