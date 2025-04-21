from flask import Blueprint, render_template
from notes_storage import get_all_note_users, get_last_saved  # ✅ Required
import os

instructor_bp = Blueprint('instructor_dashboard', __name__)

@instructor_bp.route('/notes/dashboard')
def instructor_dashboard():
    users = get_all_note_users()
    timestamps = {user_id: get_last_saved(user_id) for user_id in users}

    # Mock summary stats and activity log
    total_assignments = 5
    total_submissions = 12
    total_feedback = 8
    recent_activity = [
        {"timestamp": "2025-04-19 10:15 AM", "message": "Comment added to Jane's note."},
        {"timestamp": "2025-04-18 4:32 PM", "message": "New assignment pushed: 'Reflection on Leadership'."},
    ]

    return render_template('notes_instructor_dashboard.html',
                           users=users,
                           timestamps=timestamps,
                           total_assignments=total_assignments,
                           total_submissions=total_submissions,
                           total_feedback=total_feedback,
                           recent_activity=recent_activity)


@instructor_bp.route('/notes/create-assignment', methods=['GET', 'POST'])
def create_assignment():
    if request.method == 'POST':
        title = request.form.get('title')
        prompt = request.form.get('prompt')
        save_assignment(title, prompt)
        return redirect(url_for('instructor_dashboard.instructor_dashboard'))

    return render_template('create_assignment.html')
