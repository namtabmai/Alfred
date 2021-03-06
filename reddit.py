import asyncio
import discord
import feedparser
import logging
import html2text
import random
import re

class Reddit:
    def __init__(self, config):
        logging.info('Reddit::__init__')

        self.config = config

        self.update_frequency = 300
        try:
            self.update_frequency = int(self.config.get('reddit_update_frequency', fallback=300))
        except:
            logging.exception('Could not initialise reddit')

        logging.info('Update frequency {0}'.format(self.update_frequency))

    def get_rss_posts(self, subreddit):
        logging.debug('Reddit::get_rss_posts')

        new_posts = []
        try:
            rss = feedparser.parse('https://rss.reddit.com/r/{0}/new'.format(subreddit))

            last_updated = [reddit.last_updated for reddit in self.config.get_reddit() if reddit.subreddit == subreddit][0]
            logging.debug('Checking for updated to {0} since {1}'.format(subreddit, last_updated))

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

    def add_image(self, content, embed):
        # find an image, if there is one
        logging.debug('Looking for image: {0}'.format(content))
        matches = re.search(r'(src|href)="([^"]+?\.(png|gif|jpg|jpeg))"', content)
        if matches is not None:
            logging.debug('Found image: {0}'.format(matches.group(2)))
            url = matches.group(2)
        else:
            url = 'https://www.redditstatic.com/icon.png'

        embed.set_thumbnail(url=url)

    def add_user(self, post, embed):
        author = post.get('author', 'deleted')
        author = author if author == 'deleted' else post.author_detail.name[3:]

        shit_post = True if author.lower() in self.config.get('shit_posters', '').split(',') else False

        name = 'New shit post by' if shit_post else 'New post by'
        link = '' if author == 'deleted' else '[{0}]({1})'.format(author, post.author_detail.href)

        if shit_post:
            embed.add_field(name='Shit post level', value=':poop:'*random.randint(1,5))

        embed.add_field(name=name, value=link, inline=False)

    def add_subreddit(self, subreddit, embed):
        embed.add_field(name="To", value='[{0}](https://www.reddit.com/r/{1})'.format(subreddit.subreddit, subreddit.subreddit))

    def format_post(self, subreddit, post):
        # Convert the HTML to markdown, ignore images, no line breaks
        h = html2text.HTML2Text()
        h.ignore_images = True
        h.body_width = 0

        synopsisWordCount = int(self.config.get('reddit_synopsis_word_count', 26))

        description = h.handle(post.summary)
        # Strip out the comments link
        description = re.sub(r'\[\[comments\]\]\([^)]+\)', '', description)
        # Strip out the link
        description = re.sub(r'\[\[link\]\]\([^)]+\)', '', description)
        # Strip out the submitter link
        description = re.sub(r'submitted by (\[[^\]]+]\([^\)]+\))', '', description)

        # Take the first 27 words from the summary
        description = ' '.join(description.split()[0:synopsisWordCount])
        if len(description) is not 0:
            description = description + '...'

        colour = int(subreddit.colour, 0) if subreddit.colour is not None else discord.Embed.Empty

        embed = discord.Embed(title=post.title, url=post.link, description=description, color=colour)

        self.add_image(post.summary, embed)
        self.add_user(post, embed)
        self.add_subreddit(subreddit, embed)

        return embed

    def filter_posts(self, reddit, posts):
        logging.debug('Filtering posts for {0} with filter_regex {1}'.format(reddit.subreddit, reddit.filter_regex))

        if reddit.filter_regex is None:
            logging.debug('No filter regex defined')
            return posts

        filtered_posts = []

        regex = re.compile(reddit.filter_regex, re.IGNORECASE)

        for post in posts:
            logging.debug('Checking for match against {0}'.format(post.title))

            if regex.search(post.title) is not None or regex.search(post.description) is not None:
                logging.debug('Found matching filtered post {0}'.format(post.title))
                filtered_posts.append(post)

        return filtered_posts

    async def send_reddit_link(self, client, channel, subreddit, post):
        logging.debug('Sending post {0} to server {1} ({2}) - channel {3} ({4})'.format(post.link, channel.server.name, channel.server.id, channel.name, channel.id))

        message = self.format_post(subreddit, post)

        temp_message = await client.send_message(channel, embed=message)

        client.get_message(channel, temp_message.id)

    async def check_feeds(self, client):
        logging.info('Reddit::check_feeds')

        await client.wait_until_ready()

        for r in self.config.get_reddit():
            logging.info('Announcing the subreddit {0} to server {1} ({2}), channel {3} ({4})'.format(
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
            for subreddit in reddit_data:
                # Get all the latest posts for the subreddit
                new_posts = self.get_rss_posts(subreddit.subreddit)

                for reddit, channel in [[reddit, client.get_channel(reddit.channel['discord_id'])] for reddit in reddit_data if reddit.subreddit == subreddit.subreddit]:
                    filtered_posts = self.filter_posts(reddit, new_posts)

                    if not filtered_posts:
                        continue

                    logging.debug('Posting new posts for subreddit {0} to {1}:{2}'.format(subreddit.subreddit, channel.server.name, channel.name))
                    for post in filtered_posts:
                        await self.send_reddit_link(client, channel, subreddit, post)

            await asyncio.sleep(self.update_frequency)

