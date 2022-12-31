import os
import pickle
import csv

TOKEN_FILE_PATH = "token.txt"

def get_discord_token():
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, 'r', encoding='utf-8') as token_file:
            return token_file.read()
    return None

def get_guild_id(guild_name):
    guild_map = {
        'junkyard': 683022810649854032,
        'rgg': 404728187591852032
    }
    if guild_name in guild_map:
        return guild_map[guild_name]
    return guild_map['junkyard']

def get_channel_id(channel_name, is_testing):
    prod_channel_map = {
        "outofcontext": 706339863850647642,
        "oneinahundredthousand": 869745416307101712,
        "dream-graveyard": 686986026815717429,
        "general": 404728187591852034,
    }
    testing_channel_map = {
        "outofcontext": 706339863850647642,
        "oneinahundredthousand": 683022810654048293,
        "dream-graveyard": 683022810654048293,
        "general": 683022810654048293,
    }
    channel_map = testing_channel_map if is_testing else prod_channel_map
    if channel_name in channel_map:
        return channel_map[channel_name]
    print(f"ERROR: Unrecognized channel '{channel_name}'")
    return 683022810654048293 # 101011's Junk Graveyard General Chat

def get_channel_id_from_mention(mention: str):
    if not mention.startswith('<#') or not mention.endswith('>'):
        return None
    return int(mention.replace('<#', '').replace('>', ''))

# this saves a python struct out to a file on my computer
def save_data(path, data):
    with open(path, 'wb+') as fp:
        # pickle is a tool which can convert python objects to pure binary
        pickle.dump(data, fp, protocol=pickle.HIGHEST_PROTOCOL)

# and this reads data from the file into tobor's memory - this is how he remembers what he's been fed after he's been closed
def read_data(path):
    with open(path, 'rb') as fp:
        return pickle.load(fp)

def sanitize_data(data):
    return data

def write_data_csv(path, data):
    csv_output = []
    for author in data["quotes"].keys():
        for quote in data["quotes"][author]:
            q = quote['body']
            r = quote['reporter']
            t = quote['time']
            csv_output.append({"Quote":q, "Author":author, "Reporter": r, "Date": t.date()})
    with open(path, 'w', encoding='utf-16', newline='') as fp:
        writer = csv.DictWriter(fp, fieldnames=['Quote', 'Author', 'Reporter', 'Date'], dialect='excel-tab')
        writer.writeheader()
        writer.writerows(csv_output)