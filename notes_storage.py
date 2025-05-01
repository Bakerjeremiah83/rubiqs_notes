import os
import json
import uuid
from datetime import datetime

# Base folder where all student/instructor data is saved
DATA_DIR = "rubiqs_notes/data"
ASSIGNMENTS_FILE = os.path.join(DATA_DIR, "assignments.json")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)



# --- Note and Feedback Handling ---

def save_notes(user_id, assignment_id, text):
    filename = f"{DATA_DIR}/{user_id}_{assignment_id}.json" if assignment_id else f"{DATA_DIR}/{user_id}.json"
    data = {
        "notes": text,
        "timestamp": datetime.now().isoformat()
    }
    with open(filename, "w") as f:
        json.dump(data, f)

def load_notes(user_id, assignment_id):
    filename = f"{DATA_DIR}/{user_id}_{assignment_id}.json" if assignment_id else f"{DATA_DIR}/{user_id}.json"
    try:
        with open(filename, "r") as f:
            return json.load(f).get("notes", "")
    except FileNotFoundError:
        return ""

def save_feedback(user_id, feedback_text):
    filename = f"{DATA_DIR}/{user_id}_feedback.json"
    with open(filename, "w") as f:
        json.dump({"feedback": feedback_text}, f)

def load_feedback(user_id):
    filename = f"{DATA_DIR}/{user_id}_feedback.json"
    try:
        with open(filename, "r") as f:
            return json.load(f).get("feedback", "")
    except FileNotFoundError:
        return ""

def get_last_saved(user_id):
    try:
        with open(f"{DATA_DIR}/{user_id}.json", "r") as f:
            return json.load(f).get("timestamp", "Unknown")
    except FileNotFoundError:
        return "Unknown"

def get_all_note_users():
    users = set()
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(".json") and "_" not in filename:
            users.add(filename.replace(".json", ""))
    return list(users)


def load_inline_comments(user_id):
    path = f"{DATA_DIR}/{user_id}__comments.json"
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_inline_comments(user_id, comments):
    path = f"{DATA_DIR}/{user_id}__comments.json"
    with open(path, "w") as f:
        json.dump(comments, f, indent=2)


# --- Assignment Logic ---

def load_assignments():
    if os.path.exists(ASSIGNMENTS_FILE):
        with open(ASSIGNMENTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_assignment(title, prompt, image_url, lms_assignment_id=""):
    assignments = load_assignments()
    assignment_id = f"a{len(assignments) + 1}"

    new_assignment = {
        "assignment_id": assignment_id,
        "title": title,
        "prompt": prompt if isinstance(prompt, list) else [prompt],
        "image_url": image_url,
        "lms_assignment_id": lms_assignment_id,
        "created_at": datetime.now().isoformat(),
        "type": "assignment"  # so it displays properly in the student feed
    }

    assignments.append(new_assignment)

    with open(ASSIGNMENTS_FILE, "w") as f:
        json.dump(assignments, f, indent=2)

    return assignment_id


def is_assignment_submitted(user_id, assignment_id):
    path = f"{DATA_DIR}/{user_id}_{assignment_id}_submitted.json"
    return os.path.exists(path)

def submit_assignment(user_id, assignment_id, answers):
    path = f"{DATA_DIR}/{user_id}_{assignment_id}_submitted.json"
    data = {
        "assignment_id": assignment_id,
        "answers": answers,
        "timestamp": datetime.now().isoformat()
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def load_thread(user_id):
    thread = []

    # Load base student note
    base_file = f"{DATA_DIR}/{user_id}.json"
    if os.path.exists(base_file):
        with open(base_file, "r") as f:
            content = json.load(f)
            thread.append({
                "type": "note",
                "text": content.get("notes", ""),
                "timestamp": content.get("timestamp", "")
            })

    # Load threaded notes (new entries)
    thread_file = f"{DATA_DIR}/{user_id}_thread.json"
    if os.path.exists(thread_file):
        with open(thread_file, "r") as f:
            thread.extend(json.load(f))

    # Add pushed assignments
    assignments = load_assignments()
    thread.extend(assignments)

    thread.sort(key=lambda x: x.get("timestamp", ""), reverse=False)

    return thread



def count_note_submissions():
    return len([f for f in os.listdir(DATA_DIR) if f.endswith("_submitted.json")])

def save_to_thread(user_id, entry):
    filename = f"{DATA_DIR}/{user_id}_thread.json"
    if os.path.exists(filename):
        with open(filename, "r") as f:
            thread = json.load(f)
    else:
        thread = []

    thread.append(entry)

    with open(filename, "w") as f:
        json.dump(thread, f, indent=2)


