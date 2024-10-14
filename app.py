from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
import traceback
from forms import LoginForm, SignUpForm  # Import the forms from forms.py
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Change this to a random secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///visionx.db'  # Add this line
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Add this line

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = SQLAlchemy(app)  # Change this line

# Dummy user database (replace with a real database in production)
users = {}

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

@login_manager.user_loader
def load_user(user_id):
    if user_id not in users:
        return None
    user = User()
    user.id = user_id
    return user

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('home'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        existing_user = db.session.query(User).filter_by(email=form.email.data).first()
        if existing_user:
            flash('Email address already exists', 'warning')
            return redirect(url_for('login'))
        
        hashed_password = generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        flash('Account created successfully. Welcome!', 'success')
        return redirect(url_for('home'))
    
    return render_template('signup.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('index'))

@app.route('/')
def home():
    return render_template('index.html')

# Initialize the OpenAI client
#client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))

# Check if the API key is set
#if not client.api_key:
#    print("Warning: OPENAI_API_KEY is not set in the environment variables.")


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/image-editing', methods=['GET', 'POST'])
@login_required
def image_editing():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'image' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        file = request.files['image']
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                # Here you would process the image
                # For now, we'll just return the uploaded image path
                edited_image_url = f"/static/uploads/{filename}"
                
                return render_template('image_editing.html', edited_image=edited_image_url)
            except Exception as e:
                app.logger.error(f"An error occurred: {str(e)}")
                app.logger.error(traceback.format_exc())
                return jsonify({'error': str(e)}), 500
        else:
            return jsonify({'error': 'File type not allowed'}), 400
    else:
        return render_template('image_editing.html')

@app.route('/animation')
@login_required
def animation():
    return render_template('animation.html')

@app.route('/video-generation')
@login_required
def video_generation():
    return render_template('video_generation.html')


@app.route('/audio-processing')
@login_required
def audio_processing():
    return render_template('audio_processing.html')


@app.route('/text-generation', methods=['GET', 'POST'])
@login_required
def text_generation():
    generated_text = None
    if request.method == 'POST':
        user_input = request.form['user_input']
        if not client.api_key:
            generated_text = "Error: OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable."
        else:
            try:
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",  # Changed from "gpt-4" to "gpt-3.5-turbo"
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": user_input}
                    ]
                )
                generated_text = response.choices[0].message.content
            except Exception as e:
                generated_text = f"Error: {str(e)}"
    return render_template('text_generation.html', generated_text=generated_text)


# Route to handle OpenAI API requests
@app.route('/ask', methods=['POST'])
@login_required
def ask_openai():
    if not client.api_key:
        return jsonify({'error': 'OpenAI API key is not set. Please set the OPENAI_API_KEY environment variable.'}), 500

    user_input = request.json.get('message')
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Changed from "gpt-4" to "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        answer = response.choices[0].message.content

        # Return the response to the client (as JSON)
        return jsonify({'response': answer})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/explore-features')
def explore_features():
    if current_user.is_authenticated:
        # If user is logged in, redirect to the features page
        return redirect(url_for('features'))
    else:
        # If user is not logged in, redirect to login page with a next parameter
        flash('Please log in to explore our features.')
        return redirect(url_for('login', next=url_for('features')))

@app.route('/features')
#@login_required
def features():
    # This is the actual features page, only accessible to logged-in users
    return render_template('features.html')

if __name__ == '__main__':
    with app.app_context():  # Add this block
        db.create_all()
    app.run(debug=True)
