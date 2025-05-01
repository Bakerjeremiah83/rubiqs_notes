from flask import Flask
from notes_routes import notes_bp
from instructor_dashboard_routes import instructor_bp
from assignment_review_routes import review_bp

app = Flask(__name__)
app.secret_key = "your_secret_key"

app.register_blueprint(notes_bp, url_prefix='/notes')
app.register_blueprint(instructor_bp, url_prefix='/instructor')
app.register_blueprint(review_bp, url_prefix='/review')




if __name__ == '__main__':
    app.run(debug=True)
