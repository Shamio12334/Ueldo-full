from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'ueldo_secret_key' # Required for login sessions

# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ueldo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Models ---

# 1. The User Table (New)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    role = db.Column(db.String(20)) # 'organizer' or 'participant' or None

# 2. The Competition Table (Existing)
class Competition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    subcategory = db.Column(db.String(50))
    date = db.Column(db.String(50))
    venue = db.Column(db.String(100))
    description = db.Column(db.Text)
    entry_fee = db.Column(db.Integer, default=0)
    prize_pool = db.Column(db.String(100))
    registrations = db.Column(db.Integer, default=0) 
    status = db.Column(db.String(20), default='Live') 

with app.app_context():
    db.create_all()

# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/')
def login_page():
    # If already logged in, check role and redirect
    if 'user_id' in session:
        return check_role_and_redirect()
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    phone = request.form['phone']
    
    # Check if user exists
    user = User.query.filter_by(phone=phone).first()
    
    if not user:
        # Auto-Signup: Create new user if they don't exist
        user = User(phone=phone, role=None)
        db.session.add(user)
        db.session.commit()
    
    # Log them in (Save to Session)
    session['user_id'] = user.id
    return check_role_and_redirect()

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# Helper function to decide where to send the user
def check_role_and_redirect():
    user = User.query.get(session['user_id'])
    
    if user.role == 'organizer':
        return redirect('/organizer/dashboard')
    elif user.role == 'participant':
        return redirect('/participant/feed')
    else:
        # Role is None -> Send to Selection Screen
        return redirect('/select_role')

# ==========================================
# ROLE SELECTION (The Fork)
# ==========================================

@app.route('/select_role')
def select_role_page():
    if 'user_id' not in session: return redirect('/')
    return render_template('role_selection.html')

@app.route('/set_role/<role>')
def set_role(role):
    if 'user_id' not in session: return redirect('/')
    
    # Update User Role in DB
    user = User.query.get(session['user_id'])
    user.role = role
    db.session.commit()
    
    return check_role_and_redirect()

# ==========================================
# ORGANIZER ROUTES
# ==========================================

@app.route('/organizer/dashboard')
def organizer_dashboard():
    if 'user_id' not in session: return redirect('/')
    
    competitions = Competition.query.all()
    live_count = sum(1 for c in competitions if c.status == 'Live')
    finished_count = sum(1 for c in competitions if c.status == 'Finished')
    total_earnings = sum(c.entry_fee * c.registrations for c in competitions)

    return render_template('organizer_dashboard.html', 
                           competitions=competitions,
                           live_count=live_count,
                           finished_count=finished_count,
                           total_earnings=total_earnings)

@app.route('/organizer/create')
def create_page():
    if 'user_id' not in session: return redirect('/')
    return render_template('organizer_create.html')

@app.route('/submit_competition', methods=['POST'])
def submit_competition():
    try:
        fee_val = int(request.form['fee'])
    except:
        fee_val = 0

    new_comp = Competition(
        name=request.form['compName'],
        category=request.form['category'],
        subcategory=request.form['subCat'],
        date=request.form['dateTime'],
        venue=request.form['venue'],
        description=request.form['description'],
        entry_fee=fee_val,
        prize_pool=request.form['prize']
    )
    db.session.add(new_comp)
    db.session.commit()
    return redirect('/organizer/dashboard')

@app.route('/mark_finished/<int:id>')
def mark_finished(id):
    comp = Competition.query.get_or_404(id)
    comp.status = 'Finished'
    db.session.commit()
    return redirect('/organizer/dashboard')

# ==========================================
# PARTICIPANT ROUTES
# ==========================================

@app.route('/participant/feed')
def participant_feed():
    if 'user_id' not in session: return redirect('/')
    competitions = Competition.query.filter_by(status='Live').all()
    return render_template('participant_feed.html', competitions=competitions)

@app.route('/participant/register/<int:id>')
def register_participant(id):
    comp = Competition.query.get_or_404(id)
    comp.registrations += 1
    db.session.commit()
    return redirect('/participant/feed')

if __name__ == "__main__":
    app.run(debug=True)