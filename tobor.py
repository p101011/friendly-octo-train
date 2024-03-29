# https://realpython.com/how-to-make-a-discord-bot-python/#how-to-make-a-discord-bot-in-the-developer-portal
import asyncio
import random
import util
import oiaht
import interviews
import context as ooc
import struct
import sys
import discord

from discord import file
from discord import app_commands
from discord.ext import commands
from util import get_channel_id_from_mention, get_guild_id

# TODO: story relies on spacy, which is currently broken due to a CUDA version mismatch
if struct.calcsize("P") * 8 == 64 and False:
    import story
    X64 = True
else:
    X64 = False

IS_DEVENV = 'debug' in sys.argv

def get_channel_id(channel_name):
    return util.get_channel_id(channel_name, IS_DEVENV)

def get_discord_guilds(guild_name):
    if isinstance(guild_name, list):
        return [discord.Object(util.get_guild_id(x)) for x in guild_name]
    return discord.Object(util.get_guild_id(guild_name))

# this gets the API token from the file - this is essentially a password for Tobor which I give to the discord server
token = util.get_discord_token()

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
# client = discord.Client(intents=intents)
# tree = app_commands.CommandTree(client)

prefix = "tobor"
bot = commands.Bot(command_prefix=f'!{prefix} ', intents=intents)
last_messaged_user = None

# this method is called when tobor is started
@bot.event
async def on_ready():
    async def record_oiaht_result(result):
        if 'debug' in sys.argv:
            return
        oiaht_channel = bot.get_channel(get_channel_id('oneinahundredthousand'))
        gen_channel = bot.get_channel(get_channel_id('general'))
        consequence, closest = oiaht.get_consequence(result)
        hit = closest == result
        print(f"Closest: {closest} | Result: {result}")
        await oiaht_channel.send(f"Today's One-In-A-Hundred-Thousand roll is: *{result}*\nThe Consequence is:\n{consequence}")
        if hit:
            await gen_channel.send(f"Better buy a lottery ticket: OiaHT hit something!")
        else:
            closest_higher = closest > result
            if closest_higher:
                sign = '+'
            else:
                sign = '-'
            await oiaht_channel.send(f"The nearest rule is: *{closest}* ({sign}{abs(result - closest)})\n\t{oiaht.get_rules()[closest]}")


    for guild in bot.guilds:
        print(f'{bot.user} lives in {guild}')
    channel = bot.get_channel(get_channel_id('outofcontext'))
    await ooc.init(channel)

    num_rolls = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    await oiaht.init(record_oiaht_result, num_rolls)
    interviews.init()
    if X64:
        story.init()

@bot.event
async def on_message(message):
    global last_messaged_user
    last_messaged_user = message.author
    if message.author == bot.user:
        return
    if message.channel == "outofcontext":
        ooc.add_message_to_log(message)
    await bot.process_commands(message)

@bot.command(name='story', description="Weaves tales of grief and sorrow", guild=get_discord_guilds('junkyard'))
async def tell_story(context: commands.Context, *args):
    if context.message.channel.id != get_channel_id('dream-graveyard'):
        return

    if not X64:
        await context.send("Tobor is running on an old machine and can't remember how to tell stories")
        return

    use_tts = 'tts' in args
    if len(args) == 0:
        length = 'medium'
    else:
        if args[0] == 'tts' and len(args) > 1:
            args = args[1:]
        length = args[0]
        if length not in ['short', 'medium', 'long']:
            await context.send(f"I don't know how to tell a {length} story.")
            return

    if use_tts:
        chunk_size = 190
    else:
        chunk_size = 1900

    story_chunks = story.generate_story(length, chunk_size)
    for chunk in story_chunks:
        await context.send(chunk, tts=use_tts)

@bot.command(name='quote', description="Provides a random quote")
async def select_quote(interaction: discord.Interaction):
    await interaction.response.send_message(ooc.select_random_quote())

@bot.command(name='guess', help="Who wrote the quote")
async def user_guess_quote(context: commands.Context, *args):
    if len(args) == 0:
        await context.send(f"You have to guess who wrote the selected quote!")
        return
    result = ooc.check_quote_author(args[0])
    if result == -1:
        message = f"No quote to guess for - use '!{prefix} quote' to generate one"
    elif result == 0:
        message = f"Incorrect"
    elif result == 1:
        message = f"Correct"
        ooc.flush_random_quote()
    await context.send(message)

@bot.command(name='answer', help="Who actually wrote it")
async def get_quote_author(context: commands.Context, *args):
    author = ooc.get_quote_author()
    if author is None:
        await context.send("There's no quote to answer for!")
        return
    await context.send(f"The last message was said by {author}")
    ooc.flush_random_quote()

@bot.command(name='interview', help="This will select a random job position for which someone has to interview")
async def select_interview_position(context: commands.Context, *args):
    if len(args) > 0:
        interviewee = args[0]
    else:
        interviewee = None
    role = interviews.get_interview_role(interviewee)
    if interviewee is None:
        interviewee = "an unspecified person"
    await last_messaged_user.send(f"You are interviwing {interviewee} for the position of '{role}'")

@bot.command(name='rule', help="Add a rule to the One-In-A-Hundred-Thousand game")
async def add_oiaht_rule(context: commands.Context, *args):
    res = oiaht.add_rule(args)
    if res == 1:
        await context.send("Rule added successfully")
    elif res == 0:
        await context.send(f"Failed to add rule - rule {args[0]} already exists")
    elif res == 2:
        await context.send(f"Failed to add rule - rule must be between 0 and {oiaht.one_in_a - 1}")
    else:
        await context.send("Failed to add rule - make sure the format is <number> <rule>")

@bot.command(name='rulelist', help="Lists all of the active OiaHT rules")
async def list_oiaht_rules(context: commands.Context, *args):
    def format_rules(rule_list):
        rule_iter = list(rule_list.keys())
        rule_iter.sort()
        max_line_width = 60
        max_char_count = 1800
        chunks = [[""]]
        for rule in rule_iter:
            str_rule = str(rule)

            len_chunk = len(chunks[-1]) + sum([len(x) for x in chunks[-1]])
            if len(str_rule) + len_chunk > max_char_count:
                chunks[-1][-1] = chunks[-1][-1][:-2]
                chunks.append([""])

            len_line = len(chunks[-1][-1])
            if len(str_rule) + len_line > max_line_width:
                chunks[-1][-1] = chunks[-1][-1][:-2]
                chunks[-1].append("")

            chunks[-1][-1] += f"{str_rule}, "

        chunks[-1][-1] = chunks[-1][-1][:-2]
        chunks = ["```" + '\n'.join(x) + "```" for x in chunks]
        return chunks

    for chunk in format_rules(oiaht.get_rules()):
        await context.send(chunk)

@bot.command(name='ruleinfo', help="Get the information for a OiaHT rule by number")
async def get_oiaht_rule(context: commands.Context, *args):
    if len(args) < 1:
        await context.send(oiaht.get_rule_info())
        return
    try:
        number = int(args[0])
    except ValueError:
        await context.send(oiaht.get_rule_info())
        return
    await context.send(oiaht.get_formatted_ruleinfo(number))

@bot.command(name='feed', help="Tobor craves information")
async def feed_story_generator(context: commands.Context, *, args):
    if not X64:
        await context.send("Tobor can't tell stories")
        return
    if args == 'file':
        # we've been given a text file
        try:
            # we read the attached file with the encoding utf-8
            msg = await context.message.attachments[0].read()
            args = msg.decode('utf-8')
        except:
            await context.send("Failed to read attachment as utf-8 text file")
            return
    story.feed_generator(args)
    await context.send("Mmm, tasty")

@bot.command(name='nextroll', help="Shows the next OiaHT roll occurrence")
async def get_oiaht_roll_time(context: commands.Context, *args):
    time, eta = oiaht.get_next_roll_time()
    await context.send(f"The next roll will occur in {eta} at {time}")

@bot.command(name='metrics', help="Display metrics relating to the OiaHT ruleset")
async def get_oiaht_metrics(context: commands.Context, *args):
    rule_map = {
        "distro": oiaht.get_rule_distribution_plot
    }
    if (len(args) == 0):
        await context.send(f"You must specify a metric type. Available options are:\n{', '.join(rule_map.keys())}")
        return
    metricType, args = args[0], args[1:]
    if (metricType in rule_map):
        result = rule_map[metricType](args)
        if not result:
            await context.send(f"Make sure you enter a number for bin size")
            return
        output, cleanupCB = result
    else:
        available_types = '\n'.join(rule_map.keys())
        await context.send(f"Unrecognized metric type. Available options are:\n{available_types}")
        return
    await context.send(file=file.File(output))
    cleanupCB()

@bot.command(name='teams', help="Distribute the players in your voice chat into *n* evenly-split random teams")
async def build_random_teams(context: commands.Context, *args):
    if context.author.voice is None:
        await context.send(f"For our next team-building exercise, let's all make fun of {context.author.display_name} for trying to use this command outside of a voice channel!")
        return

    team_count = 2
    channels = None

    if len(args) > 0:
        try:
            team_count = int(args[0])
            if team_count > 10:
                await context.send(f"You don't need more than 10 teams!")
                return
        except:
            channels = [bot.get_channel(get_channel_id_from_mention(arg)) for arg in args]
            team_count = len(channels) + 1

    channel = context.author.voice.channel
    players = channel.members
    random.shuffle(players)
    teams = [players[i::team_count] for i in range(team_count)]

    if channels is None:
        team_count = '\n'.join([] + [', '.join([player.display_name for player in team]) for team in teams])
        await context.send(team_count.strip())
        return

    exception = False
    for i, team in enumerate(teams[1:]):
        for player in team:
            try:
                await player.move_to(channels[i], reason=f"Building teams")
            except:
                exception = True

    if exception:
        team_count = '\n'.join([', '.join([player.display_name for player in team]) for team in teams])
        await context.send(team_count.strip())

@bot.command(name='dump', help="Export the out of context data as a CSV file")
async def build_random_teams(context: commands.Context, *args):
    filepath = ooc.dump_data()
    with open(filepath, mode='rb') as fp:
        file = discord.File(fp)
        await context.send('Out of Context data', file=file)

if __name__ == "__main__":
    print("Starting Tobor")
    bot.run(token)
    print("Closing Tobor")