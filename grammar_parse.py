import spacy
from story_constants import *
from story_element import *

nlp = spacy.load("en_core_web_sm")

# utility function which gets verbs from a sentence using spacy
# not actually used directly by tobor
def get_verbs(text):
    doc = nlp(text)
    verb_pos = {spacy.symbols.VERB, spacy.symbols.AUX}
    excluded_tags = {'WP'}

    verbs = set()
    for token in doc:
        if token.dep == spacy.symbols.nsubj:
            if token.head.pos in verb_pos:
                verbs.add(token.head.lemma_)

    return verbs

# takes a string sentence
# returns a list of actions, each action acting on elements within the story
# this has to handle incomplete sentences due to sentence generation, which makes it a little messy
def sentence_to_actions(sentence, should_render=False):
    if sentence == '' or sentence == []:
        return []
    doc = nlp(sentence)

    if should_render:
        render = spacy.displacy.render(doc)
        with open('./render.html', 'w', encoding='utf-8') as fp:
            fp.write(render)

    # get the basic parts of speech out of the sentence

    verb_pos = {spacy.symbols.VERB, spacy.symbols.AUX}
    noun_pos = {spacy.symbols.NOUN, spacy.symbols.PROPN, spacy.symbols.PRON}
    adj_pos = {spacy.symbols.ADJ}
    subj_dep = { spacy.symbols.nsubj }
    obj_dep = {spacy.symbols.pobj, spacy.symbols.dobj}
    excluded_tags = {'WP'}

    subjects = set()
    verbs = set()
    objects = set()
    adjectives = set()
    for token in doc:
        if token.dep in subj_dep:
            if token.head.pos in verb_pos:
                verbs.add(token.head)
            if token.tag_ not in excluded_tags:
                subjects.add(token)
        elif token.dep in obj_dep and token.tag_ not in excluded_tags:
            objects.add(token)
        elif token.pos in noun_pos:
            if token.dep == spacy.symbols.conj:
                if token.tag_ in excluded_tags:
                    continue
                # conjunct noun, look to parent to see whether subj or obj
                head = token.head
                if head.dep in subj_dep:
                    subjects.add(token)
                elif head.dep in obj_dep:
                    objects.add(token)
            elif token.dep in subj_dep and token.tag_ not in excluded_tags:
                subjects.add(token)
            elif token.dep_ == 'dative' and token.tag_ not in excluded_tags:
                # for example, Frank gave *Alice* a frog - Alice.dep_ == dative
                objects.add(token)
        if token.pos in adj_pos:
            adjectives.add(token)

    # I have run into cases where a sentence is erroneously classified as not having a subject
    if not any(subjects) or not any(verbs):
        return []

    # break up the components into their associated actions
    noun_dicts = {}
    action_dicts = {}

    for verb in verbs:
        action_dicts[verb] = {
            "subjects": [],
            "objects": { "direct": [], "indirect": [] }
        }
    for noun in subjects:
        noun_dicts[noun] = []
    for noun in objects:
        noun_dicts[noun] = []

    for adjective in adjectives:
        noun_head = adjective.head
        while noun_head.pos not in noun_pos and noun_head.dep_ != "ROOT":
            noun_head = noun_head.head
        if noun_head in noun_dicts:
            noun_dicts[noun_head].append(adjective)

    for subject in subjects:
        verb_head = subject.head
        while verb_head.pos not in verb_pos and verb_head.dep_ != "ROOT":
            verb_head = verb_head.head
        if verb_head in action_dicts:
            action_dicts[verb_head]["subjects"].append((subject, noun_dicts[subject]))

    for o in objects:
        verb_head = o.head
        while verb_head.pos not in verb_pos and verb_head.dep_ != "ROOT":
            verb_head = verb_head.head
        if verb_head in action_dicts:
            category = 'indirect'
            if o.dep == spacy.symbols.dobj:
                category = 'direct'
            elif o.dep == spacy.symbols.conj:
                # this is conjugate, so might be either category
                if o.head.dep == spacy.symbols.dobj:
                    category = 'direct'
            action_dicts[verb_head]["objects"][category].append((o, noun_dicts[o]))



    actions = []
    for verb, nouns in action_dicts.items():
        act_subj = []
        for noun, descriptors in nouns["subjects"]:
            act_subj.append(StoryElement(noun, descriptors=descriptors))
        act_obj = { "direct": [], "indirect": [] }
        for object_type in nouns["objects"]:
            for noun, descriptors in nouns["objects"][object_type]:
                act_obj[object_type].append((StoryElement(noun, descriptors=descriptors)))
        action = build_action(verb.lemma_, act_subj, act_obj)
        actions.append(action)
    return actions

def build_action(verb, subjects, objects):
    args = (verb, subjects, objects)
    if verb == 'give':
        return GiveAction(*args)
    elif verb == 'move':
        return MoveAction(*args)
    elif verb == 'emplace':
        return EmplaceAction(*args)
    elif verb == 'take':
        return TakeAction(*args)
    elif verb == 'destroy':
        return DestroyAction(*args)
    elif verb == 'free':
        return FreeAction(*args)
    else:
        return Action(*args)

