import os
import util
import random
import story_util
import grammar_parse
from story_constants import *
from story_element import History

babel_library = "story-data.txt"
MARKOV_LENGTH = 3
babel_store = f"tobor-dict-{MARKOV_LENGTH}.pkl"

word_bank = {}
length_sentence_map = {
    'short': SHORT_STORY_SENT_COUNT,
    'medium': MED_STORY_SENT_COUNT,
    'long': LONG_STORY_SENT_COUNT
}

def init():
    global word_bank
    if os.path.exists(babel_store):
        word_bank = util.read_data(babel_store)

def generate_story(length, chunk_size):
    length = length_sentence_map[length]
    story, score, history = generate_story_of_length(length)
    return chunk_story(story.split(), chunk_size)

# takes as input a list of actions, the history, and a bool indicating whether to penalize incomplete actions
# returns a tuple fits_history, novel_elements
# misfits_history is an integer measure of the number of actions/elements which disagree with history/rules
# novel_elements is an integer measure of the number of new elements not in history
def score_actions(actions, history, reject_incomplete):
    misfits_history = 0
    novel_elements = 0
    for action in actions:
        valid_action = action.validate(reject_incomplete)
        if not valid_action:
            print("Action '{}' failed to validate".format(action))
            misfits_history += 1
        for action_element in action.elements:
            if not history.contains_element(action_element):
                novel_elements += 1
    return misfits_history, novel_elements

# this is the most important function for tobor - this tells him how good a sentence is
# we want to strongly encourage sentences having actions (for obvious reasons)
# we want to increase the penalty for adding novel elements as the story gets longer
# we also want to discourage overly long or short sentences
def score_sentence(sentence, history, reject_incomplete=True):
    actions = grammar_parse.sentence_to_actions(' '.join([x for x in sentence if x is not None]))
    misfits_history, novel_elements = score_actions(actions, history, reject_incomplete)
    novel_penalty = float(len(history.unique_elements)) / 10
    ideal_length = 18
    distance = abs(len(sentence) - ideal_length) / ideal_length
    return (len(actions) / (misfits_history + (novel_penalty * novel_elements) + (distance * len(actions)) + 1))

# this takes part of a sentence and figures out what word best comes next
# returns the word and score associated with the sentence having added that word
def get_next_word(sentence, key, chain, depth, history, last_sentence):
    if depth == 0:
        # yep, this is recursion
        # this means that we've looked a few words into the future, and we want to evaluate how good this future is
        # we don't care what words are here (we'll calculate those later), but we want to know how good the sentence is
        # in this case, we might not be done building the sentence, so we won't penalize an incomplete action (i.e. 'Jack gives...' would be penalized otherwise)
        return None, score_sentence(sentence, history, reject_incomplete=False)
    if last_sentence:
        # save a little bit of time here - if it's the last sentence, and we've finished it, we don't need to look into the future of sentences we can't generate
        if len(sentence) > 0 and util.is_terminal_word(sentence[-1]):
            return None, score_sentence(sentence, history, reject_incomplete=True)
    # if, for whatever reason, the sequence of words we have never shows up in the text tobor has been fed, then we just stop the generation
    # this should be a rare (maybe even impossible) case
    if key not in chain:
        return None, score_sentence(sentence, history, reject_incomplete=True)
    # we're now interested in figuring out which of the possible words fits best
    max_score = -float('inf')
    max_word = None
    # print("Getting word from key: {} and bank: {}".format(key, chain[key]))
    for word in chain[key]:
        # for every possible word, we make a copy of the starting sentence and add the word to it
        temp_sentence = list(sentence)
        temp_sentence.append(word)
        # we then recurse on this new sentence to get the best estimated score this word can lead us to
        temp_key = key[1:] + (word,)
        _, score = get_next_word(temp_sentence, temp_key, chain, depth - 1, history, last_sentence)
        # if the best score from this word is better than our current best, we update our max score and remember this word
        if score > max_score:
            max_score = score
            max_word = word
        elif score == max_score:
            # we want to avoid getting stuck in loops if all words have equal scores
            roll = random.random()
            if roll > 0.5:
                max_word = word
    # and now we return whichever word was best as well as the score it will give us
    return max_word, max_score

# this generates a new sentence based on the words before it
def generate_sentence(chain, key, history, is_first_sentence, is_last_sentence):
    if is_first_sentence:
        # our key is actually part of the first sentence.
        sentence = list(key)
    else:
        sentence = []
    score = -1

    while len(sentence) == 0 or not story_util.is_terminal_word(sentence[-1]) and len(sentence) < MAX_SENTENCE_LENGTH:
        # while our sentence isn't finished (note the syntax sentence[-1] is the same as saying the last word of the sentence)
        # we get the next word in the sentence (using the above function) and add it to the sentence
        next_word, score = get_next_word(sentence, key, chain, SEARCH_DEPTH, history, is_last_sentence)
        sentence.append(next_word)
        # we update the key to be the last 'n' words of the sentence again
        # we get the last n-1 elements of the key, then add the last word onto it
        key = key[1:] + (next_word,)
    actions = grammar_parse.sentence_to_actions(' '.join([s for s in sentence if s is not None]))
    score = score_sentence(sentence, history, reject_incomplete=True)
    print("Sentence: {} - Score: {}".format(sentence, score))
    return sentence, actions, score

def generate_story_of_length(length):
    if len(word_bank.keys()) == 0:
        # this is what happens if tobor doesn't have any info
        return "No data", 0, None
    # we start our story with a random batch of words from the lookup table
    first_phrase = random.choice(list(word_bank.keys()))
    while first_phrase[0].islower() or not first_phrase[0].isalpha():
        # we have enough data that we can look for chunks where the first word is uppercase
        first_phrase = random.choice(list(word_bank.keys()))
    key = first_phrase
    sentences = []
    history = History()
    total_score = 0
    for i in range(length + 1):
        # get a sentence
        next_sentence, actions, score = generate_sentence(word_bank, key, history, i == 0,  i == length - 1)
        # if i > 0:
        #     test_set = set(next_sentence + sentences[-1])
        #     if len(test_set) < len(next_sentence) / 2:
        #         x = 10
        if len(next_sentence) == 0:
            # if the sentence is empty, then something went wrong - we're done with the story as is
            break
        for action in actions:
            history.add_action(action, i)
        sentences.append(next_sentence)
        total_score += score
        n = MARKOV_LENGTH
        # now we need to figure out what the key is for the next sentence
        if len(next_sentence) >= n:
            # if the new sentence we have has at least n words in it, we can just use the last n words of the sentence as the key
            key = tuple(next_sentence[-n:])
        else:
            # otherwise we do some fun stuff to get the last n words of the total story for the key
            key = []
            # current_sentence tracks which sentence we're looking at for the words
            current_sentence = len(sentences) - 1
            while len(key) < n:
                # while the key isn't long enough:
                for word in reversed(sentences[current_sentence]):
                    # we look at the sentence in reverse, so that we get the last words first
                    if not len(key) < n:
                        # if we've added enough words to the key, we're done
                        break
                    # we add the next word (again, going backwards) to the key
                    key.insert(0, word)
                # we might not have enough words in the sentence, so we keep going back through the sentences
                current_sentence -= 1
            # assert means that it will error out if the key isn't the appropriate length
            assert len(key) == n
            # we convert the key to a tuple from a list
            key = tuple(key)
    # this uses python features to join every word in every sentence with a space, then joins the sentences with a space as well
    sentences = " ".join([" ".join([s for s in x if s is not None]) for x in sentences])
    return sentences, total_score, history

def chunk_story(story, chunk_size):
    # discord tts can only speak up to 200 characters at once (but 200 doesn't seem to be accurate)
    story_fragments = [""]
    char_count = 0
    frag_count = 0
    for word in story:
        if char_count + len(word) + 1 < chunk_size:
            # if the word is short enough to fit within the limit, we just add it
            char_count += len(word) + 1
            story_fragments[frag_count] += word + ' '
        else:
            # otherwise we have to put the word into a new block of its own
            frag_count += 1
            char_count = len(word) + 1
            story_fragments.append("")
            story_fragments[frag_count] += word + ' '
    # we clear out any extra white space from the fragments and return them
    story_fragments = [x.strip() for x in story_fragments]
    return story_fragments

def feed_generator(input):
    # we write the text we were given out to the text file for my records
    with open(babel_library, 'a', encoding='utf-8') as datafile:
        datafile.write(f'\n{input}')
    # we now split up the input text into words by whitespace
    cleaned = input.split()
    # we get all of the word chunks
    for words, tail in story_util.get_word_combos(cleaned, n=MARKOV_LENGTH):
        if words in word_bank:
            # if the word chunk is already in the database:
            if tail in word_bank[words]:
                # and the tail is already an option which can follow the chunk, we just increment the count of that tail (used to prevent super long lists)
                word_bank[words][tail] += 1
            else:
                # otherwise, we just add the tail word as another option which can follow the chunk
                word_bank[words][tail] = 1
        else:
            # otherwise, we add the chunk to the database
            word_bank[words] = { tail: 1 }
    # we figure out where we're saving the data to and save it out to disk
    util.save_data(babel_store, word_bank)