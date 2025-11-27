from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from collections import defaultdict
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'ueldo_secret_key'

# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ueldo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# ==========================================
# DATABASE MODELS
# ==========================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(15), unique=True, nullable=False) 
    role = db.Column(db.String(20)) 
    
    # Identity & Trust
    organizer_type = db.Column(db.String(20)) # 'Club' or 'Individual'
    is_verified = db.Column(db.Boolean, default=False) 
    verification_status = db.Column(db.String(20), default='None')
    proof_doc = db.Column(db.String(200)) 

    # --- THE FIX: Link User to Competitions ---
    competitions = db.relationship('Competition', backref='organizer', lazy=True)

class Competition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100))
    category = db.Column(db.String(50))
    subcategory = db.Column(db.String(50))
    date = db.Column(db.String(50))
    venue = db.Column(db.String(100))
    map_link = db.Column(db.String(300))
    description = db.Column(db.Text)
    entry_fee = db.Column(db.Integer, default=0)
    prize_pool = db.Column(db.String(100))
    status = db.Column(db.String(20), default='Live')
    qr_code = db.Column(db.String(200))
    whatsapp_link = db.Column(db.String(300))
    
    # Metrics
    registrations = db.Column(db.Integer, default=0) 

class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id')) 
    competition_id = db.Column(db.Integer, db.ForeignKey('competition.id'))
    status = db.Column(db.String(20), default='Pending') 

with app.app_context():
    db.create_all()

# ==========================================
# HELPER: SAFE REDIRECT
# ==========================================
def route_by_role():
    if 'user_id' not in session: return redirect('/')
    
    user = User.query.get(session['user_id'])
    
    # Zombie Session Fix
    if not user:
        session.clear()
        return redirect('/')
        
    if user.role == 'organizer': return redirect('/organizer/dashboard')
    if user.role == 'participant': return redirect('/participant/feed')
    return redirect('/select_role')

# ==========================================
# AUTHENTICATION (PHONE + OTP)
# ==========================================

@app.route('/')
def login_page():
    if 'user_id' in session: return route_by_role()
    return render_template('login.html')

@app.route('/send_otp', methods=['POST'])
def send_otp():
    phone = request.form['phone']
    # Simulating OTP
    session['temp_phone'] = phone
    session['temp_otp'] = "1234"
    print(f"OTP for {phone}: 1234") 
    return render_template('login_otp.html', phone=phone)

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    user_otp = request.form['otp']
    if user_otp == session.get('temp_otp'):
        phone = session['temp_phone']
        
        user = User.query.filter_by(phone=phone).first()
        if not user:
            user = User(phone=phone, role=None)
            db.session.add(user)
            db.session.commit()
        
        session['user_id'] = user.id
        session.pop('temp_phone', None)
        session.pop('temp_otp', None)
        
        return route_by_role()
    else:
        return "Invalid OTP"

@app.route('/select_role')
def select_role_page():
    if 'user_id' not in session: return redirect('/')
    return render_template('role_selection.html')

@app.route('/set_role/<role>')
def set_role(role):
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect('/')

    user.role = role
    db.session.commit()
    return route_by_role()

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ==========================================
# ORGANIZER ROUTES
# ==========================================

@app.route('/organizer/dashboard')
def organizer_dashboard():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if not user: return redirect('/')

    my_competitions = Competition.query.filter_by(organizer_id=user.id).all()
    
    grouped_comps = defaultdict(list)
    pending_count = 0
    
    for comp in my_competitions:
        grouped_comps[comp.category].append(comp)
        pending_count += Registration.query.filter_by(competition_id=comp.id, status='Pending').count()
        
    grouped_comps = dict(grouped_comps)
    
    # Logic for Verification Popup
    comp_count = len(my_competitions)
    show_verification_prompt = False
    if comp_count >= 2 and user.verification_status == 'None':
        show_verification_prompt = True
    
    # Metrics
    live_count = sum(1 for c in my_competitions if c.status == 'Live')
    finished_count = sum(1 for c in my_competitions if c.status == 'Finished')
    total_earnings = sum(c.entry_fee * c.registrations for c in my_competitions)

    return render_template('organizer_dashboard.html', 
                           grouped_comps=grouped_comps,
                           pending_count=pending_count,
                           user=user,
                           live_count=live_count,
                           finished_count=finished_count,
                           total_earnings=total_earnings,
                           show_verification_prompt=show_verification_prompt,
                           comp_count=comp_count)

@app.route('/save_organizer_type', methods=['POST'])
def save_organizer_type():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    if user:
        user.organizer_type = request.form['orgType'] # 'Club' or 'Individual'
        db.session.commit()
    return redirect('/organizer/dashboard')

@app.route('/submit_verification', methods=['POST'])
def submit_verification():
    if 'user_id' not in session: return redirect('/')
    user = User.query.get(session['user_id'])
    
    if 'proofDoc' in request.files:
        file = request.files['proofDoc']
        if file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            user.proof_doc = filename
            user.verification_status = 'Submitted'
            db.session.commit()
        
    return redirect('/organizer/dashboard')

@app.route('/organizer/create')
def create_page():
    return render_template('organizer_create.html')

@app.route('/submit_competition', methods=['POST'])
def submit_competition():
    if 'user_id' not in session: return redirect('/')
    
    qr_filename = None
    if 'qrFile' in request.files:
        file = request.files['qrFile']
        if file.filename != '':
            qr_filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], qr_filename))

    try: fee = int(request.form['fee'])
    except: fee = 0

    new_comp = Competition(
        organizer_id=session['user_id'],
        name=request.form['compName'],
        category=request.form['category'],
        subcategory=request.form['subCat'],
        date=request.form['dateTime'],
        venue=request.form['venue'],
        map_link=request.form['mapLink'],
        description=request.form['description'],
        entry_fee=fee,
        prize_pool=request.form['prize'],
        qr_code=qr_filename,
        whatsapp_link=request.form.get('whatsappLink'),
        registrations=0
    )
    db.session.add(new_comp)
    db.session.commit()
    return redirect('/organizer/dashboard')

@app.route('/organizer/registrations/<int:comp_id>')
def view_registrations(comp_id):
    comp = Competition.query.get_or_404(comp_id)
    regs = Registration.query.filter_by(competition_id=comp_id).all()
    
    reg_data = []
    for r in regs:
        player = User.query.get(r.user_id)
        if player:
            reg_data.append({
                'reg_id': r.id,
                'phone': player.phone,
                'status': r.status
            })
        
    return render_template('organizer_registrations.html', reg_data=reg_data, comp=comp)

@app.route('/organizer/approve/<int:reg_id>')
def approve_payment(reg_id):
    reg = Registration.query.get(reg_id)
    reg.status = 'Approved'
    
    # Update count on competition
    comp = Competition.query.get(reg.competition_id)
    comp.registrations = Registration.query.filter_by(competition_id=comp.id, status='Approved').count()
    
    db.session.commit()
    return redirect(url_for('view_registrations', comp_id=reg.competition_id))

@app.route('/organizer/edit/<int:id>')
def edit_competition(id):
    if 'user_id' not in session: return redirect('/')
    comp = Competition.query.get_or_404(id)
    return render_template('organizer_edit.html', comp=comp)

@app.route('/organizer/update/<int:id>', methods=['POST'])
def update_competition(id):
    if 'user_id' not in session: return redirect('/')
    comp = Competition.query.get_or_404(id)
    
    if request.method == 'POST':
        try: fee = int(request.form['fee'])
        except: fee = 0

        comp.name = request.form['compName']
        comp.category = request.form['category']
        comp.subcategory = request.form['subCat']
        comp.date = request.form['dateTime']
        comp.venue = request.form['venue']
        comp.map_link = request.form['mapLink']
        comp.description = request.form['description']
        comp.entry_fee = fee
        comp.prize_pool = request.form['prize']
        
        if 'qrFile' in request.files:
            file = request.files['qrFile']
            if file.filename != '':
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                comp.qr_code = filename
        
        comp.whatsapp_link = request.form.get('whatsappLink')
        
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
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        return redirect('/')

    competitions = Competition.query.filter_by(status='Live').all()
    
    my_status = {}
    my_regs = Registration.query.filter_by(user_id=session['user_id']).all()
    for r in my_regs:
        my_status[r.competition_id] = r.status
        
    return render_template('participant_feed.html', competitions=competitions, my_status=my_status)

@app.route('/participant/pay/<int:comp_id>')
def pay_page(comp_id):
    comp = Competition.query.get_or_404(comp_id)
    return render_template('participant_pay.html', comp=comp)

@app.route('/participant/confirm_payment/<int:comp_id>', methods=['POST'])
def confirm_payment(comp_id):
    if 'user_id' not in session: return redirect('/')
    
    new_reg = Registration(user_id=session['user_id'], competition_id=comp_id, status='Pending')
    db.session.add(new_reg)
    db.session.commit()
    return redirect('/participant/feed')

if __name__ == "__main__":
    app.run(debug=True)