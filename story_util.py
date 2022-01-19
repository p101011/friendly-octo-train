from story_constants import *
import os
import pickle
import story_element

def get_discord_token():
    if os.path.exists(TOKEN_FILE_PATH):
        with open(TOKEN_FILE_PATH, 'r', encoding='utf-8') as token_file:
            return token_file.read()
    return None

def convert_bank(bank, new_n):
    old_n = len(next(iter(bank.keys())))
    print("Mapping from n={} to n={}".format(old_n, new_n))
    if old_n == new_n:
        return bank
    new_bank = {}
    if old_n > new_n:
        for key in bank.keys():
            if len(new_key) != new_n + 1:
                continue
            print("Mapping key {}".format(key))
            new_key = key[:new_n]
            new_val = key[new_n]
            if new_key in new_bank:
                new_bank[new_key].append(new_val)
            else:
                new_bank[new_key] = [new_val]
    else:
        num_blanks = new_n - old_n + 1
        for key in bank.keys():
            print("Mapping key {}".format(key))
            # num_blanks = max(0, new_n + i + 1 - old_n)
            # new_key = key[i:min(new_n + i, old_n) + 1]
            # how many empty spots will we have to lookup?
            # takes the head of a key and fills it appropriately - returns a list of all possible keys with that head
            new_keys = fill_blanks(key, bank, num_blanks, old_n)
            for new_key in new_keys:
                if len(new_key) != new_n + 1:
                    continue
                new_val = new_key[-1]
                new_key = new_key[:-1]
                if new_key in new_bank:
                    new_bank[new_key].append(new_val)
                else:
                    new_bank[new_key] = [new_val]
    print("Switched from chain with {} entries to chain with {} entries".format(len(bank.keys()), len(new_bank.keys())))
    return new_bank

# this function is used when converting banks
# say you have a key with two words in it, but you need a key with four words
# this function will look up all of the possible fourword keys which can start with those two words
# if there aren't any, then it will use 'None' (or 'null') in their place. None values are used to indicate the end of a text.
def fill_blanks(key, bank, to_fill, old_n):
    if to_fill == 0:
        # this key is already properly filled - we don't need to add anything
        return [key]
    # filled_keys is where we'll store all of the keys we fill up
    filled_keys = []
    # the table we have has keys of length old_n - consider the case where we're converting a table of length 2 to length 3
    # old_n is 2, and n is 3
    # because this function is recursive, we don't tell it explicitly what n is, rather, we tell it how many words it needs (so n - old_n)
    # lookup_key is then the last old_n elements in the key we've built - we're looking for all the words in the bank of length old_n which can follow the key we've got
    lookup_key = key[-old_n:]
    # permutations is just the list of the words which can follow what we have
    permutations = bank[lookup_key]
    for p in permutations:
        if p is None:
            # this case means that there are no words that follow the key we have
            # in this case, we just fill in the rest of the key with 'None' values
            # neat syntax here: key is a tuple, like a coordinate: (x, y). In python, you can add two tuples together
            # so, knowing that p = None, we put p into a tuple, then multiply that tuple by the number of 'None's we need so that we get a tuple with that many Nones in it
            # then we add the two tuples together
            new_key = key + ((p,) * to_fill)
            filled_keys += [new_key]
        else:
            # in this case, p is an actual word
            # we add it to the key
            new_key = key + (p,)
            # then we call this function again with our new, slightly longer, key. Notice that we tell it we need one less spot filled - eventually, this number will equal 0, and we'll return the full key
            # this pattern is called recursion, and it's a bit of a mindfuck sometimes
            new_keys = fill_blanks(new_key, bank, to_fill - 1, old_n)
            # anyways, new_keys will eventually be a list of all possible keys following the given key + the new word 'p', so we add those to the overall list of keys
            filled_keys += new_keys
    # and we return all of the keys which we have found
    return filled_keys


# this function is used when tobor is fed new data
# it takes the raw text which has been fed, broken up by white spaces (this means that line breaks, spaces, or other gaps are removed), as well as a chain length
# it breaks it up into chunks of 'n' words a piece, then includes the word following that chunk
def get_word_combos(text, n):
    # for most of the text, this is a simple task
    # it's only the last chunk of words, with length is less than or equal to n, which gets weird
    for i in range(len(text) - n):
        # for most of the words, we just get the chunk, and the word following the chunk, and return it
        # note that yield is a fancy method of returning which is asynchronous - this means tobor can still react to commands while processing text
        yield (tuple(text[i:i+n]), text[i+n])
    for i in range(max(0, len(text) - n), len(text)):
        # for the last chunk of words, we grab as many as we can
        words = text[i:]
        # if there are fewer words than we need, we slap a 'None' on there so we know that's the end of the key
        if len(words) < n:
            words.append(None)
        # and we just say that nothing follows the last chunk
        yield (tuple(words), None)



# this is a little function which takes a word and tells tobor if it's the last word in a sentence
# remember when we break the input text up, we only know when the entire entry is ended, not individual sentences
def is_terminal_word(word):
    # these are all the punctuation marks which I consider to be ending marks
    terminal_punctuation = ".?!"
    # *super* incomplete list
    nonterminal_sequences = [
        'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Jr.', 'Sr.', 'i.e.', 'e.g.', '...', 'etc.', 'Ave.', 'Mon.', 'Tues.', 'Wed.', 'Thurs.',
        'Fri.', 'Sat.', 'Sun.', 'D.C.', 'B.C.', 'B.C.E.', 'a.m.', 'p.m.', 'St.'
    ]
    # if the word is None, it's obviously the end of a sentence
    if word is None:
        return True
    if word[-1] in terminal_punctuation:
        # if the last character in the word is one of the ending marks:
        if word in nonterminal_sequences:
            # some words have periods, but aren't actually the last word in a sentence
            return False
        # otherwise, the word is terminal
        return True
    # if the word is part of a quote, then it could still be terminal
    if word[-1] == '"' or word[-1] == '”':
        # we check to see if the character before the quote mark is terminal
        if len(word) > 1 and word[-2] in terminal_punctuation:
            return True
    return False


# this saves the bank out to a file on my computer
def save_bank(path, word_bank):
    with open(path, 'wb+') as fp:
        # pickle is a tool which can convert python objects to pure binary
        pickle.dump(word_bank, fp, protocol=pickle.HIGHEST_PROTOCOL)

# and this reads data from the file into tobor's memory - this is how he remembers what he's been fed after he's been closed
def read_bank(path):
        with open(path, 'rb') as fp:
            return pickle.load(fp)