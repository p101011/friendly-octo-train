from pickle import FALSE
import random
import os
import util
import datetime
import pytz
from discord import errors

datapath = "context-data.pkl"
csvpath = "context-data.csv"

data = {
    "timestamp": None,
    "quotes": {},
    "total_count": 0
}
last_random_quote = None, None

def add_message_to_log(message):
    global data
    add_message_to_dict(data, message)

def add_message_to_dict(d, message):
    author, body, reporter = process_quote(message)
    if 'quotes' not in d:
        d['quotes'] = {}
    if author not in d["quotes"]:
        d["quotes"][author] = []
    quote = {"body": body, "reporter": reporter, "time": message.created_at}
    d["quotes"][author].append(quote)
    return d

def process_quote(message):
    content = message.content
    sections = content.rsplit('-', 1)
    if len(sections) == 2:
        body = sections[0].strip()
        author = sections[1].strip().title()
    else:
        body = content
        author = "Bad {}".format(message.author.name)
    reporter = message.author.name
    return author, body, reporter

def invalid_message(message):
    content = message.content
    if '"' not in content and '“' not in content and '”' not in content:
        return True
    return False

async def init(ooc_channel):
    print("Looking for pre-existing datapack")
    global data
    if (os.path.exists(datapath)):
        print("Datapack found")
        data = util.read_data(datapath)
    else:
        print("No previous data available")
    last_updated = data["timestamp"]
    print("Last message in history is from {}".format(last_updated))
    last_message_id = data.get("last_message_id", None)
    new_data = await get_new_messages(ooc_channel, last_updated, last_message_id)
    data["total_count"] += new_data["count"]
    print(f"Data fetch complete: there are {new_data['count']} new messages and {data['total_count']} total messages")
    for author in new_data["quotes"].keys():
        if author not in data["quotes"]:
            data["quotes"][author] = []
        data["quotes"][author] += new_data["quotes"][author]
    data["timestamp"] = datetime.datetime.now(datetime.timezone.utc)
    data["last_message_id"] = new_data["last_message_id"]
    data = util.sanitize_data(data)
    util.save_data(datapath, data)
    util.write_data_csv(csvpath, data)
    print(f"Data load process complete")

async def get_new_messages(channel, timestamp, last_message_id):
    if timestamp is None:
        timestamp = datetime.datetime.utcfromtimestamp(0)
    if not channel:
        return {"quotes": {}, "count": 0}
    valid = []
    if last_message_id is None:
        last_message = None
    else:
        try:
            last_message = await channel.fetch_message(last_message_id)
        except errors.NotFound:
            last_message_id = None
            last_message = None
    after = timestamp if last_message is None else last_message
    messages = [x async for x in channel.history(limit=None, after=after)]
    for message in messages:
        message_time = message.created_at
        if message_time.tzinfo is None:
            message_time = pytz.UTC.localize(message_time)
        if message_time < timestamp or invalid_message(message):
            continue
        else:
            valid.append(message)
    output = {"quotes": {}, "count": len(valid)}
    for message in valid:
        add_message_to_dict(output, message)
    if len(valid) > 0:
        last_message = valid[0]
        output["last_message_id"] = last_message.id
    else:
        output["last_message_id"] = last_message_id
    return output

def select_random_quote():
    global last_random_quote
    author = random.choice(list(data['quotes'].keys()))
    quote = random.choice(data['quotes'][author])
    last_random_quote = quote, author
    return quote['body']

def check_quote_author(guess):
    global last_random_quote
    if last_random_quote[0] is None:
        return -1
    actual_person = last_random_quote[1]
    if guess.upper() in actual_person.upper():
        return 1
    else:
        return 0

def get_quote_author():
    global last_random_quote
    return last_random_quote[1]

def flush_random_quote():
    global last_random_quote
    last_random_quote = None, None

def dump_data():
    util.write_data_csv(csvpath, data)
    return csvpath