# https://realpython.com/how-to-make-a-discord-bot-python/#how-to-make-a-discord-bot-in-the-developer-portal
import util
import oiaht
import interviews
import context as ooc
import struct

from discord.ext import commands

if struct.calcsize("P") * 8 == 64:
    import story
    X64 = True
else:
    X64 = False

# this gets the API token from the file - this is essentially a password for Tobor which I give to the discord server
token = util.get_discord_token()

prefix = "tobor"
bot = commands.Bot(command_prefix=f'!{prefix} ')
rgg_ooc_channel_id = 706339863850647642 # ooc
rgg_oiaht_channel_id = 869745416307101712 # oiaht
rgg_dg_channel_id = 686986026815717429 # dream-graveyard
rgg_gen_channel_id = 404728187591852034 # general
junk_gen_channel_id = 683022810654048293 # testing
last_messaged_user = None

# this method is called when tobor is started
@bot.event
async def on_ready():
    async def record_oiaht_result(result):
        oiaht_channel = bot.get_channel(rgg_oiaht_channel_id)
        gen_channel = bot.get_channel(rgg_gen_channel_id)
        # oiaht_channel = bot.get_channel(junk_gen_channel_id)
        # gen_channel = bot.get_channel(junk_gen_channel_id)
        consequence, hit = oiaht.get_consequence(result)
        await oiaht_channel.send(f"Today's One-In-A-Hundred-Thousand roll is: *{result}*\nThe Consequence is:\n{consequence}")
        if hit:
            await gen_channel.send(f"Better buy a lottery ticket: OiaHT hit something!")


    for guild in bot.guilds:
        print(f'{bot.user} lives in {guild}')
    channel = bot.get_channel(rgg_ooc_channel_id)
    await ooc.init(channel)
    oiaht.init(record_oiaht_result)
    interviews.init()
    if X64:
        story.init()

@bot.event
async def on_message(message):
    global last_messaged_user
    last_messaged_user = message.author
    if message.author != bot.user and message.channel == "outofcontext":
        ooc.add_message_to_log(message)
    await bot.process_commands(message)

# the main event
@bot.command(name='story', help="Weaves tales of grief and sorrow")
async def tell_story(context, *args):
    if context.message.channel.id != rgg_dg_channel_id:
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

@bot.command(name='metrics', help="Gross")
async def print_metrics(context, *args):
    await context.send("I'm still sleeping (wait for it)")

@bot.command(name='quote', help="Provides a random quote")
async def select_quote(context, *args):
    await context.send(ooc.select_random_quote())

@bot.command(name='guess', help="Who wrote the quote")
async def user_guess_quote(context, *args):
    result = ooc.check_quote_author(args)
    if result == -1:
        message = f"No quote to guess for - use '!{prefix} guess' to generate one"
    elif result == 0:
        message = f"Incorrect"
    elif result == 1:
        message = f"Correct"
    await context.send(message)

@bot.command(name='answer', help="Who actually wrote it")
async def get_quote_author(context, *args):
    author = ooc.get_quote_author()
    if author is None:
        await context.send("There's no quote to answer for!")
        return
    await context.send(f"The last message was said by {author}")
    ooc.flush_random_quote()

@bot.command(name='interview', help="This will select a random job position for which someone has to interview")
async def select_interview_position(context, *args):
    if len(args) > 0:
        interviewee = args[0]
    else:
        interviewee = None
    role = interviews.get_interview_role(interviewee)
    if interviewee is None:
        interviewee = "an unspecified person"
    await last_messaged_user.send(f"You are interviwing {interviewee} for the position of '{role}'")

@bot.command(name='rule', help="Add a rule to the One-In-A-Hundred-Thousand game")
async def add_oiaht_rule(context, *args):
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
async def list_oiaht_rules(context, *args):
    def format_rules(rule_list):
        output = "```"
        rule_iter = list(rule_list.keys())
        rule_iter.sort()
        max_line_width = 60
        while len(rule_iter) > 0:
            line = ""
            while len(rule_iter) > 0 and len(line) + len(str(rule_iter[0])) + 2 < max_line_width:
                line += f"{rule_iter[0]}, "
                rule_iter = rule_iter[1:]
            output += f"{line[:-2]}\n"
        output = output[:-1] + "```"
        return output
    await context.send(format_rules(oiaht.get_rules()))

@bot.command(name='ruleinfo', help="Get the information for a OiaHT rule by number")
async def get_oiaht_rule(context, *args):
    if len(args) < 1:
        await context.send(oiaht.get_rule_info())
        return
    try:
        number = int(args[0])
    except ValueError:
        await context.send(oiaht.get_rule_info())
        return
    rules = oiaht.get_rules()
    if number not in rules:
        await context.send(f"There is no rule '{number}' at present")
        return
    await context.send(f"Rule {number}: {rules[number]}")

@bot.command(name='feed', help="Tobor craves information")
async def feed_story_generator(context, *, args):
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
async def get_oiaht_roll_time(context, *args):
    time, eta = oiaht.get_next_roll_time()
    await context.send(f"The next roll will occur in {eta} at {time}")


print("Starting Tobor")
bot.run(token)
print("Closing Tobor")