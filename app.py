from flask import Flask
from notes_routes import notes_bp
from instructor_dashboard_routes import instructor_bp
from assignment_review_routes import review_bp

app = Flask(__name__)
app.secret_key = "your_secret_key"

app.register_blueprint(notes_bp, url_prefix='/notes')
app.register_blueprint(instructor_bp, url_prefix='/instructor')
app.register_blueprint(review_bp, url_prefix='/review')

@app.route('/login', methods=['POST'])
def login():
    from flask import request, redirect
    from utils.lti_platforms import PLATFORMS

    iss = request.form.get("iss")
    login_hint = request.form.get("login_hint")
    target_link_uri = request.form.get("target_link_uri")
    client_id = request.form.get("client_id")
    lti_message_hint = request.form.get("lti_message_hint")

    if not all([iss, login_hint, target_link_uri, client_id]):
        return "Missing login parameters", 400

    platform = PLATFORMS.get("moodle")

    redirect_url = (
        f"{platform['auth_login_url']}?"
        f"scope=openid&"
        f"response_type=id_token&"
        f"client_id={client_id}&"
        f"redirect_uri={target_link_uri}&"
        f"login_hint={login_hint}&"
        f"lti_message_hint={lti_message_hint}&"
        f"response_mode=form_post&"
        f"prompt=none"
    )

    return redirect(redirect_url)

@app.route('/launch', methods=['POST'])
def lti_launch():
    from flask import request, session, render_template
    import jwt
    import os
    from notes_storage import (
        load_notes, load_feedback, load_assignments,
        is_assignment_submitted, load_inline_comments,
        get_all_note_users, count_note_submissions
    )

    TINYMCE_API_KEY = os.getenv("TINYMCE_API_KEY")

    id_token = request.form.get("id_token")
    if not id_token:
        return "Missing ID token", 400

    decoded = jwt.decode(id_token, options={"verify_signature": False})
    user_name = decoded.get("name", "Anonymous")
    user_id = decoded.get("sub", "test-user")
    roles = decoded.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])

    session["user"] = user_name
    session["roles"] = roles

    # ✅ If instructor, show dashboard
    if any(role.lower() in r.lower() for r in roles for role in ["instructor", "teacher"]):
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

    # ✅ Otherwise, render student notes view
    assignments = load_assignments()
    selected_assignment_id = ""
    assignment_prompt = ""

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
        "notes_home.html",
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

if __name__ == '__main__':
    app.run(debug=True)
