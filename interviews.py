import os
import random
import util

interview_data_dir = "InterviewData"
interview_history_path = "history.pkl"

interview_data = {}
interview_history = []
filtered_data = {}

def init():
    global interview_history, filtered_data
    for file in os.listdir(interview_data_dir):
        if os.path.isdir(file):
            continue
        role_author = os.path.splitext(file)[0]
        interview_data[role_author] = []
        with open(os.path.join(interview_data_dir, file), 'r') as fp:
            interview_data[role_author] = [x.title().strip() for x in fp.readlines()]
        if len (interview_data[role_author]) < 1:
            print(f"WARNING: {role_author} has a file but does not have any interview roles!")

    if os.path.exists(interview_history_path):
        interview_history = util.read_data(interview_history_path)

    filtered_data = interview_data
    for author, role in interview_history:
        add_data_to_filter(author, role)

def add_data_to_filter(author, role):
    global filtered_data
    filtered_data[author].remove(role)
    if len(filtered_data[author]) == 0:
        filtered_data.pop(author)
    if len(filtered_data.keys()) == 0:
        print(f"INFO: Reshuffling the interview deck")
        filtered_data = interview_data

def add_data_to_history(author, role):
    interview_history.append((author, role))
    add_data_to_filter(author, role)
    util.save_data(interview_history_path, interview_history)

def get_interview_role(interviewee):
    if len(filtered_data.keys()) < 1:
        print(f"ERROR: Can't retrieve a role because there is no data!")
        return None
    if len(filtered_data.keys()) < 2 and interviewee in filtered_data:
        print(f"ERROR: Can't retrieve a role because the interviewee is the only author!")
        return None
    valid_authors = [x for x in list(filtered_data.keys()) if x != interviewee]
    author = random.choice(valid_authors)
    role = random.choice(filtered_data[author])
    add_data_to_history(author, role)
    return role