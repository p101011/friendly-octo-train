import os
import pickle
import csv

TOKEN_FILE_PATH = "D:\\Repos\\p101011\\context-bot\\token.txt"

def get_discord_token():
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, 'r', encoding='utf-8') as token_file:
            return token_file.read()
    return None

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