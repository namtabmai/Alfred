-- DROP TABLE IF EXISTS server;
CREATE TABLE server(
  id INTEGER PRIMARY KEY,
  discord_id TEXT NOT NULL,
  name TEXT UNIQUE
);

-- DROP TABLE IF EXISTS channel;
CREATE TABLE channel(
  id INTEGER PRIMARY KEY,
  discord_id TEXT NOT NULL,
  server_id INTEGER NOT NULL,
  name TEXT NOT NULL,
  UNIQUE(server_id, name),
  FOREIGN KEY(server_id) REFERENCES server(id)
);

-- DROP TABLE IF EXISTS configuration;
CREATE TABLE configuration(
  id INTEGER PRIMARY KEY,
  server_id INTEGER NULL,
  name TEXT NOT NULL,
  value TEXT NOT NULL,
  UNIQUE(server_id, name),
  FOREIGN KEY(server_id) REFERENCES server(id)
);

-- DROP TABLE IF EXISTS reddit;
CREATE TABLE reddit(
  id INTEGER PRIMARY KEY,
  channel_id INTEGER NOT NULL,
  subreddit TEXT NOT NULL,
  last_updated DATETIME DEFAULT(STRFTIME('%Y-%m-%d %H:%M:%f', 'NOW')) NOT NULL,
  UNIQUE(channel_id, subreddit),
  FOREIGN KEY(channel_id) REFERENCES channel(id)
);

