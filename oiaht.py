import asyncio
import datetime
import random
import util
import os
import csv
import numpy as np
from matplotlib import pyplot as plt

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
                number = int(row[0])
                if number > (one_in_a - 1) or number < 0:
                    continue
                consequences[number] = row[1]

    if os.path.exists(consequence_data):
        store = util.read_data(consequence_data)
        for key in store:
            if key > (one_in_a - 1) or key < 0:
                continue
            consequences[key] = store[key]

    loop = asyncio.get_event_loop()
    task = loop.create_task(oiab_task(oiab_callback))

async def roll_oiab(cb):
    global last_oiab_roll
    current_time = datetime.datetime.now()
    time_since_last_roll = current_time - last_oiab_roll
    if time_since_last_roll < datetime.timedelta(days=1):
        print("Uh-oh, scoob!")
        return
    last_oiab_roll = current_time
    oiab_metadata['last_oiab_roll'] = last_oiab_roll
    roll = random.randint(1, one_in_a)
    await cb(roll)
    util.save_data(metapath, oiab_metadata)

async def oiab_task(cb):
    global last_oiab_roll
    duration = datetime.datetime.now() - last_oiab_roll
    if (divmod(duration.total_seconds(), 86400)[0] > 1):
        await roll_oiab(cb)
    while True:
        next_roll = last_oiab_roll + datetime.timedelta(days=1, seconds=3)
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
            return "Nothing happens... this time", lower
        return "Nothing happens... this time", k

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

def get_formatted_ruleinfo(number):
    if number not in consequences:
        return f"There is no rule '{number}' at present"
    return f"Rule {number}: {consequences[number]}"

def how_many_numbers_within(n=5):
    rule_numbers = list(consequences.keys())
    for number in consequences.keys():
        for i in range(-n, n + 1):
            if number + i not in rule_numbers:
                rule_numbers.append(number + i)
    return len(rule_numbers)

def get_rule_distribution_plot(arguments):
    output_filename = "tempplt.png"
    def cleanup():
        if os.path.exists(output_filename):
            os.remove(output_filename)
    if len(arguments) == 0:
        bins = 10
    else:
        try:
            bins = int(arguments[0])
        except:
            return False
    if bins > 1000:
        bins = 1000
    plt.clf()
    plt.figure(figsize=(5,5))
    _, _, bars = plt.hist(consequences.keys(), bins)
    # plt.bar_label(bars)
    plt.xlabel("Rule Number (10000's)")
    plt.xticks(np.arange(0, one_in_a, one_in_a / 10), np.arange(0, int(one_in_a / (one_in_a / 10))))
    plt.title("OiaHT Rule Distribution Histogram")
    plt.savefig(output_filename, dpi=200)
    return output_filename, cleanup