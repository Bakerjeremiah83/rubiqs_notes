# rubiqs_notes/assignment_review_routes.py
from flask import Blueprint, render_template
from notes_storage import load_assignments, get_all_note_users, is_assignment_submitted

review_bp = Blueprint('assignment_review', __name__)

@review_bp.route('/notes/assignment-review')
def assignment_review_dashboard():
    assignments = load_assignments()
    students = get_all_note_users()

    # Build a dictionary of submissions: { assignment_id: { student_id: submitted_bool } }
    submission_map = {}
    for a in assignments:
        a_id = a['id']
        submission_map[a_id] = {}
        for student_id in students:
            submitted = is_assignment_submitted(student_id, a_id)
            submission_map[a_id][student_id] = submitted

    return render_template('assignment_review_dashboard.html',
                           assignments=assignments,
                           students=students,
                           submission_map=submission_map)
