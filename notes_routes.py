import os
from dotenv import load_dotenv
load_dotenv()

import os
TINYMCE_API_KEY = os.getenv("TINYMCE_API_KEY")

from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import json
from openai import OpenAI
from datetime import datetime


from notes_storage import (
    load_notes, save_notes, save_feedback, load_feedback,
    get_last_saved, load_assignments, submit_assignment,
    is_assignment_submitted, load_inline_comments,
    get_all_note_users, count_note_submissions, save_assignment,
    save_to_thread
)

notes_bp = Blueprint('notes', __name__)
instructor_bp = Blueprint('instructor_dashboard', __name__)



DATA_DIR = "rubiqs_notes/data"

@notes_bp.route('/dashboard')
def instructor_dashboard():
    assignments = load_assignments()
    students = get_all_note_users()
    total_submissions = count_note_submissions()

    submission_map = {}
    for a in assignments:
        a_id = a.get('assignment_id') or a.get('id')
        submission_map[a_id] = {}
        for student_id in students:
            submitted = is_assignment_submitted(student_id, a_id)
            submission_map[a_id][student_id] = submitted

    return render_template(
        'notes_instructor_dashboard.html',
        tinymce_api_key=os.getenv("TINYMCE_API_KEY"),
        assignments=assignments,
        students=students,
        submission_map=submission_map,
        total_submissions=total_submissions
    )


@notes_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    user_id = request.args.get('user_id')
    feedback_text = request.form.get('feedback', '')
    save_feedback(user_id, feedback_text)
    return redirect(url_for('notes.view_student_notes', user_id=user_id))

@notes_bp.route('/instructor', methods=['GET', 'POST'])
def view_student_notes():
    user_id = request.args.get('user_id')
    assignment_id = request.args.get('assignment_id', '')

    if not user_id:
        return "Missing user ID", 400

    if request.method == 'POST':
        anchor_text = request.form.get("anchor_text")
        comment_text = request.form.get("comment")
        from notes_storage import save_inline_comment
        save_inline_comment(user_id, assignment_id, comment_text, anchor_text)

    saved_notes = load_notes(user_id, assignment_id)
    saved_feedback = load_feedback(user_id)
    comments = load_inline_comments(user_id, assignment_id)

    return render_template(
        'notes_instructor_view.html',
        tinymce_api_key=TINYMCE_API_KEY,
        user_id=user_id,
        saved_notes=saved_notes,
        saved_feedback=saved_feedback,
        assignment_id=assignment_id,
        comments=comments
    )

@notes_bp.route('/grade', methods=['GET'])
def grade_notes():
    user_id = request.args.get('user_id')
    assignment_id = request.args.get('assignment_id', '')

    raw_notes = load_notes(user_id, assignment_id)
    inline_comments = load_inline_comments(user_id, assignment_id)
    highlighted_notes = raw_notes

    for c in inline_comments:
        if c["anchor"] in highlighted_notes:
            comment_html = (
                f'<mark style="background-color: #fff3cd; padding: 0.2rem; border-radius: 4px;">'
                f'{c["anchor"]}</mark> '
                f'<span style="background: #fef9e7; border-left: 3px solid #f1c40f; padding: 0.25rem 0.5rem; margin-left: 0.5rem; border-radius: 4px; font-size: 0.9rem;">'
                f'💬 {c["comment"]}</span>'
            )
            highlighted_notes = highlighted_notes.replace(c["anchor"], comment_html, 1)

    response = OpenAI(api_key=os.getenv("OPENAI_API_KEY")).chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an educational writing assistant. Analyze the following student notes and provide helpful, rubric-aligned feedback."},
            {"role": "user", "content": f"Here are the student notes:\n\n{raw_notes}"}
        ]
    )

    ai_feedback = response.choices[0].message.content.strip()

    return render_template(
        'notes_grader_panel.html',
        tinymce_api_key=TINYMCE_API_KEY,
        user_id=user_id,
        assignment_id=assignment_id,
        highlighted_notes=highlighted_notes,
        ai_feedback=ai_feedback,
        comments=inline_comments
    )

@notes_bp.route('/submit-grade', methods=['POST'])
def submit_grade():
    user_id = request.form.get('user_id')
    assignment_id = request.form.get('assignment_id')
    score = request.form.get('score')
    ai_feedback = request.form.get('ai_feedback')

    if not all([user_id, assignment_id, score]):
        return "Missing data", 400

    grade_data = {
        "score": score,
        "feedback": ai_feedback,
        "timestamp": datetime.now().isoformat()
    }

    filename = f"{DATA_DIR}/{user_id}_{assignment_id}_grade.json"
    with open(filename, "w") as f:
        json.dump(grade_data, f)

    return redirect(url_for('assignment_review.assignment_review_dashboard'))

@notes_bp.route('/prompt-generate', methods=['POST'])
def prompt_generate():
    data = request.get_json()
    topic = data.get('query', '')
    prompt_type = data.get('type', 'study_guide')

    if not topic:
        return jsonify({'prompt': 'Please enter a topic to generate.'})

    if prompt_type == 'study_guide':
        instruction = "Create a study guide-style prompt or learning task."
    elif prompt_type == 'reflection_prompt':
        instruction = "Write a reflection-style question prompt for student journaling or discussion."
    elif prompt_type == 'rubric':
        instruction = "Generate a simple 3-criteria rubric with scoring descriptions for evaluating student work."
    else:
        instruction = "Create an instructional support prompt."

    response = OpenAI(api_key=os.getenv("OPENAI_API_KEY")).chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": f"You are Rubiqs Copilot, an instructional assistant. {instruction}"},
            {"role": "user", "content": f"Topic: {topic}"}
        ]
    )

    result = response.choices[0].message.content.strip()
    return jsonify({'prompt': result})


@notes_bp.route('/create-assignment', methods=['POST'])
def create_assignment():
    title = request.form.get('title')
    prompt = request.form.getlist('prompt[]')
    image_url = request.form.get('image_url', '')
    lms_assignment_id = request.form.get('lms_assignment_id', '')

    if image_url:
        prompt += f'<div style="margin-top: 1rem;"><img src="{image_url}" alt="Assignment Image" style="max-width: 100%; border-radius: 6px;" /></div>'

    save_assignment(title, prompt, image_url, lms_assignment_id)

    assignments = load_assignments()
    students = get_all_note_users()

    submission_map = {}
    for a in assignments:
        a_id = a.get('assignment_id') or a.get('id')
        submission_map[a_id] = {}
        for student_id in students:
            submitted = is_assignment_submitted(student_id, a_id)
            submission_map[a_id][student_id] = submitted

    return render_template(
        'notes_instructor_dashboard.html',
        tinymce_api_key=TINYMCE_API_KEY,
        assignments=assignments,
        students=students,
        submission_map=submission_map,
        total_submissions=count_note_submissions()
    )


@notes_bp.route('/feed-test')
def test_notes_feed():
    return render_template('notes_feed.html')
tinymce_api_key=TINYMCE_API_KEY,

@notes_bp.route('/add-note', methods=['POST'])
def add_note():
    user_id = request.args.get('user_id')
    note_text = request.form.get('note')

    if not note_text:
        return "Note is empty", 400

    from notes_storage import save_to_thread
    new_entry = {
        "type": "note",
        "text": note_text.strip(),
        "timestamp": datetime.now().isoformat()
    }
    save_to_thread(user_id, new_entry)

    return redirect(url_for('notes.view_feed', user_id=user_id))

@notes_bp.route('/feed')
def view_feed():
    user_id = request.args.get('user_id', 'test123')
    from notes_storage import load_thread

    thread = load_thread(user_id)

    # Build a map of responses by assignment_id
    response_map = {}
    filtered_thread = []

    for entry in thread:
        if entry.get("type") == "response":
            aid = entry.get("assignment_id")
            response_map[aid] = entry
        else:
            filtered_thread.append(entry)  # Keep only notes and assignments

    submitted_assignments = set(response_map.keys())

    return render_template(
        'notes_feed.html',
        tinymce_api_key=TINYMCE_API_KEY,
        user_id=user_id,
        thread=filtered_thread,
        response_map=response_map,
        submitted_assignments=submitted_assignments
    )


@notes_bp.route('/respond', methods=['POST'])
def submit_assignment_response():
    user_id = request.form.get('user_id')
    assignment_id = request.form.get('assignment_id')

    print("📤 DEBUG – Received form submission:")
    print("user_id:", user_id)
    print("assignment_id:", assignment_id)

    if not user_id or not assignment_id:
        return "Missing user ID or assignment ID", 400

    from notes_storage import save_to_thread, load_thread

    # Prevent resubmission if already answered
    thread = load_thread(user_id)
    for entry in thread:
        if entry.get("type") == "response" and entry.get("assignment_id") == assignment_id:
            return redirect(url_for('notes.view_feed', user_id=user_id))

    # Collect answers
    answers = {}
    for key, value in request.form.items():
        if key.startswith("q"):
            answers[key] = value.strip()

    # Save the response
    response_entry = {
        "type": "response",
        "assignment_id": assignment_id,
        "answers": answers,
        "submitted": True,
        "timestamp": datetime.now().isoformat()
    }

    save_to_thread(user_id, response_entry)
    return redirect(url_for('notes.view_feed', user_id=user_id))

@notes_bp.route('/view-thread/<user_id>')
def view_student_thread(user_id):
    from notes_storage import load_thread

    thread = load_thread(user_id)

    # Group responses by assignment_id
    response_map = {}
    filtered_thread = []
    for entry in thread:
        if entry.get("type") == "response":
            response_map[entry.get("assignment_id")] = entry
        else:
            filtered_thread.append(entry)

    submitted_assignments = set(response_map.keys())

    return render_template(
        'notes_feed.html',
        tinymce_api_key=TINYMCE_API_KEY,
        user_id=user_id,
        thread=filtered_thread,
        response_map=response_map,
        submitted_assignments=submitted_assignments,
        instructor_mode=True  # Optional: use to show instructor-only tools later
    )

def add_comment_to_note(user_id, note_timestamp, comment_text):
    filename = os.path.join(DATA_DIR, f"{user_id}_thread.json")
    if not os.path.exists(filename):
        return False

    with open(filename, "r") as f:
        thread = json.load(f)

    for entry in thread:
        if entry.get("type") == "note" and entry.get("timestamp") == note_timestamp:
            if "comments" not in entry:
                entry["comments"] = []
            entry["comments"].append({
                "author": "instructor",
                "text": comment_text,
                "timestamp": datetime.now().isoformat()
            })
            break

    with open(filename, "w") as f:
        json.dump(thread, f, indent=2)

    return True

@notes_bp.route('/comment', methods=['POST'])
def add_inline_comment():
    user_id = request.form.get('user_id')
    note_timestamp = request.form.get('note_timestamp')
    comment_text = request.form.get('comment')

    if not all([user_id, note_timestamp, comment_text]):
        return "Missing data", 400

    from notes_storage import add_comment_to_note
    success = add_comment_to_note(user_id, note_timestamp, comment_text)

    if success:
        return redirect(url_for('notes.view_student_thread', user_id=user_id))
    else:
        return "Note not found", 404

@notes_bp.route('/reply', methods=['POST'])
def reply_to_comment():
    user_id = request.form.get('user_id')
    note_timestamp = request.form.get('note_timestamp')
    comment_timestamp = request.form.get('comment_timestamp')
    reply_text = request.form.get('reply')

    if not all([user_id, note_timestamp, comment_timestamp, reply_text]):
        return "Missing data", 400

    from notes_storage import add_reply_to_comment
    success = add_reply_to_comment(user_id, note_timestamp, comment_timestamp, reply_text)

    if success:
        return redirect(url_for('notes.view_feed', user_id=user_id))
    else:
        return "Comment not found", 404

@notes_bp.route('/push-assignment/<assignment_id>', methods=['POST'])
def push_assignment_to_feed(assignment_id):
    from notes_storage import load_assignments, save_to_thread

    # For now, push only to test student
    user_id = "test123"
    assignments = load_assignments()

    assignment = next((a for a in assignments if a["id"] == assignment_id), None)
    if not assignment:
        return "Assignment not found", 404

    # Build thread entry
    thread_entry = {
        "type": "assignment",
        "assignment_id": assignment["id"],
        "title": assignment["title"],
        "prompt": assignment["prompt"] if isinstance(assignment["prompt"], list) else [assignment["prompt"]],
        "image": assignment.get("image_url"),
        "timestamp": datetime.now().isoformat()
    }

    save_to_thread(user_id, thread_entry)

    return redirect(url_for('instructor_dashboard.instructor_dashboard'))

@notes_bp.route('/update-note', methods=['POST'])
def update_note_route():
    print("✅ Reached update_note_route")

    if request.is_json:
        data = request.get_json()
        user_id = data.get('user_id')
        timestamp = data.get('timestamp')
        updated_text = data.get('updated_text')
        updated_title = data.get('updated_title') or ""

    else:
        user_id = request.form.get('user_id')
        timestamp = request.form.get('timestamp')
        updated_text = request.form.get('text')

    if not all([user_id, timestamp, updated_text]):
        return jsonify({'error': 'Missing data'}), 400

    path = f"{DATA_DIR}/{user_id}_thread.json"
    if not os.path.exists(path):
        return jsonify({'error': 'No thread found'}), 404

    with open(path, 'r') as f:
        thread = json.load(f)

    for entry in thread:
        if entry.get('type') == 'note' and entry.get('timestamp') == timestamp:
            entry['text'] = updated_text
            entry['title'] = updated_title

            break
    else:
        return jsonify({'error': 'Note not found'}), 404

    with open(path, 'w') as f:
        json.dump(thread, f, indent=2)

    return jsonify({'success': True})

@notes_bp.route('/student-notes', methods=['GET', 'POST'])
def student_notes_view():
    user_id = request.args.get('user_id', 'test-user')
    assignments = load_assignments()
    selected_assignment_id = request.args.get('assignment_id', '')
    assignment_prompt = ''

    if selected_assignment_id:
        for a in assignments:
            if a['id'] == selected_assignment_id:
                assignment_prompt = a['prompt']
                break

    if request.method == 'POST':
        action = request.form.get("action")
        if action == "submit":
            submit_assignment(user_id, selected_assignment_id)
        else:
            notes_text = request.form.get('notes', '')
            save_notes(user_id, selected_assignment_id, notes_text)
        return redirect(url_for('notes.launch_notes', user_id=user_id, assignment_id=selected_assignment_id))

    raw_notes = load_notes(user_id, selected_assignment_id)
    inline_comments = load_inline_comments(user_id, selected_assignment_id)
    highlighted_notes = raw_notes

    for c in inline_comments:
        if c["anchor"] in highlighted_notes:
            comment_html = (
                f'<span class="inline-comment-anchor">{c["anchor"]}</span>'
                f'<span class="inline-comment-bubble" onclick="this.classList.toggle(\'open\')">💬<span class="bubble-content">{c["comment"]}</span></span>'
            )
            highlighted_notes = highlighted_notes.replace(c["anchor"], comment_html, 1)

    saved_feedback = load_feedback(user_id)
    is_submitted = is_assignment_submitted(user_id, selected_assignment_id)

    return render_template(
        'notes_home.html',
        tinymce_api_key=TINYMCE_API_KEY,
        user_id=user_id,
        saved_notes=raw_notes,
        saved_feedback=saved_feedback,
        assignments=assignments,
        selected_assignment_id=selected_assignment_id,
        assignment_prompt=assignment_prompt,
        is_submitted=is_submitted,
        inline_comments=inline_comments,
        highlighted_notes=highlighted_notes
    )
