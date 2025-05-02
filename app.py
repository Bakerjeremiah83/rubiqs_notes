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
        print("❌ Missing login parameters")
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

    print("🔁 Redirecting to:", redirect_url)

    return redirect(redirect_url)


if __name__ == '__main__':
    app.run(debug=True)
