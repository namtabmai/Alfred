from datetime import datetime
import sqlite3
import time

class Config:
    class Reddit:
        def __init__(self, row):
            self.server = {
                    'discord_id': row['server_discord_id'],
                    'name': row['server_name']
                }
            self.channel = {
                    'discord_id': row['channel_discord_id'],
                    'name': row['channel_name']
            }
            self.subreddit = row['subreddit']
            self.last_updated = datetime.fromtimestamp(row['last_updated']).timetuple()

    def __init__(self, filename):
        self.db = sqlite3.Connection(filename)
        self.db.row_factory = sqlite3.Row

    def get(self, name, fallback = None, server_id = None):
        cur = self.db.execute('''
            SELECT value
            FROM configuration
            WHERE name = :name
                AND (server_id = :server_id
                OR server_id is null)
            ORDER BY server_id DESC
        ''', {"name": name, "server_id": server_id})

        res = cur.fetchone()
        if res is None:
            return fallback
        else:
            return res['value']

    def get_reddit(self):
        cur = self.db.execute('''
            SELECT server.discord_id AS server_discord_id, server.name AS server_name,
                channel.discord_id AS channel_discord_id, channel.name AS channel_name,
                subreddit, last_updated
            FROM reddit
            LEFT JOIN channel ON reddit.channel_id = channel.id
            LEFT JOIN server ON channel.server_id = server.id
        ''')

        reddit_config = []

        for row in cur:
            reddit_config.append(self.Reddit(row))

        return reddit_config

    def update_reddit(self, subreddit, last_update):
        self.db.execute('''
            UPDATE reddit SET last_updated = :last_update WHERE subreddit = :subreddit
        ''', {"subreddit": subreddit, "last_update": time.mktime(last_update)})
        self.db.commit()


