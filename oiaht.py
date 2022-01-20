import asyncio
import datetime
import random
import util
import os
import csv

metapath = "oiab-data.pkl"
consequence_path = "oiaht-consequences.csv"
consequence_data = "oiaht-consequences.pkl"

one_in_a = 100000

last_oiab_roll = datetime.datetime.utcfromtimestamp(0)
oiab_metadata = {"last_oiab_roll": None}
consequences = {}

def init(oiab_callback):
    global last_oiab_roll
    if os.path.exists(metapath):
        oiab_metadata = util.read_data(metapath)
        last_oiab_roll = oiab_metadata['last_oiab_roll']

    if os.path.exists(consequence_path):
        with open(consequence_path, 'r') as fp:
            reader = csv.reader(fp)
            for row in reader:
                consequences[int(row[0])] = row[1]

    if os.path.exists(consequence_data):
        store = util.read_data(consequence_data)
        for key in store:
            consequences[key] = store[key]

    loop = asyncio.get_event_loop()
    task = loop.create_task(oiab_task(oiab_callback))

async def roll_oiab(cb):
    global last_oiab_roll
    roll = random.randint(1, one_in_a)
    await cb(roll)
    last_oiab_roll = datetime.datetime.now()
    oiab_metadata['last_oiab_roll'] = last_oiab_roll
    util.save_data(metapath, oiab_metadata)

async def oiab_task(cb):
    global last_oiab_roll
    duration = datetime.datetime.now() - last_oiab_roll
    if (divmod(duration.total_seconds(), 86400)[0] > 1):
        await roll_oiab(cb)
    while True:
        next_roll = last_oiab_roll + datetime.timedelta(days=1)
        time_to_next_roll_in_s = (next_roll - datetime.datetime.now()).total_seconds()
        await asyncio.sleep(time_to_next_roll_in_s)
        print(f'sleep time: {time_to_next_roll_in_s}')
        await roll_oiab(cb)

def get_consequence(number):
    if number in consequences:
        return consequences[number], number
    sorted = list(consequences.keys())
    sorted.sort()
    lower = -float('inf')
    for k in sorted:
        if number > k:
            lower = k
            continue
        dist_low = number - lower
        dist_high = k - number
        if dist_low < dist_high:
            return lower
        return k

    return "Nothing happens... this time", False

def add_rule(args):
    try:
        number = int(args[0])
    except ValueError:
        print(f"Bad value {args[0]}")
        return -1
    if number in consequences:
        return 0
    if number < 0 or number >= one_in_a:
        return 2
    consequence = ' '.join(args[1:])
    consequences[number] = consequence
    util.save_data(consequence_data, consequences)
    return 1

def get_rules():
    return consequences

def get_rule_info():
    num_rules = len(consequences.keys())
    p = num_rules / one_in_a
    p_year = 1 - pow(1 - p, 365)

    today = datetime.datetime.now()
    next_year = datetime.datetime(today.year + 1, 1, 1)
    days_remaining = (next_year - today).days
    p_remaining = 1 - pow(1 - p, days_remaining)
    format_date = next_year.strftime("%d-%m-%y")
    return f"There are {num_rules} rules. The probability of at least one rule occuring by {format_date} is {p_remaining:.2f}"

def get_next_roll_time():
    next_roll = last_oiab_roll + datetime.timedelta(days=1)
    eta = next_roll - datetime.datetime.now()
    pretty_next = str(next_roll.strftime("%H:%M:%S"))
    pretty_eta = str(eta)
    if '.' in pretty_eta:
        pretty_eta = pretty_eta[:pretty_eta.index('.')]
    return pretty_next, pretty_eta