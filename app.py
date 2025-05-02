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
    from flask import request, redirect, session
    from utils.lti_platforms import PLATFORMS
    import jwt

    id_token = request.form.get("id_token")
    if not id_token:
        return "Missing ID token", 400

    print("✅ /launch route hit. Token received.")

    decoded = jwt.decode(id_token, options={"verify_signature": False})
    print("✅ Decoded token:")
    print(decoded)

    session["user"] = decoded.get("name", "Anonymous")
    session["roles"] = decoded.get("https://purl.imsglobal.org/spec/lti/claim/roles", [])

    return redirect("/notes/student-notes")



if __name__ == '__main__':
    app.run(debug=True)
