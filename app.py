from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask import Response, flash


app = Flask(__name__)
app.secret_key = "secret123"

# Database config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///meds_reminder.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# ------------------ MODELS ------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    medicines = db.relationship("Medicine", backref="user", lazy=True)

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50))
    time = db.Column(db.String(10))  # "HH:MM"
    start_date = db.Column(db.String(10))
    end_date = db.Column(db.String(10))
    status = db.Column(db.String(20), default="Pending")

# ------------------ USER ROUTES ------------------
@app.route('/')
def home():
    if 'user_id' in session:
        meds = Medicine.query.filter_by(user_id=session['user_id']).all()
        return render_template('dashboard.html', meds=meds)
    elif 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        if User.query.filter_by(email=email).first():
            flash("Email already registered!")
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        user = User(email=email, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful!")
        return redirect(url_for('login'))

    return render_template('register.html')

# ------------------ LOGIN ------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            # Simplified admin check
            if user.email == "sathya@gmail.com" and password == "admin":
                session['admin_id'] = user.id
                return redirect(url_for('admin_dashboard'))
            else:
                session['user_id'] = user.id
                return redirect(url_for('home'))

        flash("Invalid email or password")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('admin_id', None)
    return redirect(url_for('login'))

# ------------------ ADD / EDIT MEDICINE ------------------
@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    edit_id = request.args.get('edit_id')
    med = None
    if edit_id:
        med = db.session.get(Medicine, int(edit_id))
        if not med or med.user_id != session['user_id']:
            flash("Medicine not found!")
            return redirect(url_for('home'))

    if request.method == 'POST':
        name = request.form['name']
        dosage = request.form['dosage']
        time = request.form['time']
        start = request.form['start']
        end = request.form['end']

        if med:
            med.name = name
            med.dosage = dosage
            med.time = time
            med.start_date = start
            med.end_date = end
            db.session.commit()
            flash("Medicine updated!")
        else:
            new_med = Medicine(
                user_id=session['user_id'],
                name=name,
                dosage=dosage,
                time=time,
                start_date=start,
                end_date=end
            )
            db.session.add(new_med)
            db.session.commit()
            flash("Medicine added!")

        return redirect(url_for('home'))

    return render_template('add.html', med=med)

@app.route('/delete_medicine/<int:med_id>', methods=['POST'])
def delete_medicine(med_id):
    med = db.session.get(Medicine, med_id)
    if med and (med.user_id == session.get('user_id') or 'admin_id' in session):
        db.session.delete(med)
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404

@app.route('/update_status/<int:med_id>/<string:new_status>')
def update_status(med_id, new_status):
    med = db.session.get(Medicine, med_id)
    if med and med.user_id == session.get('user_id'):
        med.status = new_status
        db.session.commit()
    return redirect(url_for('home'))

@app.route("/check_reminder")
def check_reminder():
    now = datetime.now().strftime("%H:%M")
    meds = Medicine.query.filter_by(status="Pending").all()
    due_meds = [
        {"id": m.id, "name": m.name, "dosage": m.dosage}
        for m in meds
        if m.time == now and m.user_id == session.get('user_id')
    ]
    return jsonify(due_meds)

@app.route("/mark_taken/<int:med_id>", methods=["POST"])
def mark_taken(med_id):
    med = db.session.get(Medicine, med_id)
    if med and med.user_id == session.get('user_id'):
        med.status = "Taken"
        db.session.commit()
        return jsonify({"success": True})
    return jsonify({"success": False}), 404


# ------------------ ADMIN ROUTES ------------------
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    users = User.query.filter(User.email != "sathya@gmail.com").all()
    return render_template('admin_dashboard.html', users=users)


@app.route('/admin_user/<int:user_id>')
def admin_user(user_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, user_id)
    if not user:
        flash("User not found!")
        return redirect(url_for('admin_dashboard'))

    medicines = Medicine.query.filter_by(user_id=user.id).all()
    return render_template('admin_user.html', user=user, medicines=medicines)


@app.route('/admin_delete_user/<int:user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, user_id)
    if not user:
        flash("User not found!")
        return redirect(url_for('admin_dashboard'))

    # Delete all user's medicines first
    for med in user.medicines or []:
        db.session.delete(med)

    # Then delete the user
    db.session.delete(user)
    db.session.commit()

    flash("User deleted successfully!")
    return redirect(url_for('admin_dashboard'))



@app.route('/admin_edit_med/<int:med_id>', methods=['GET', 'POST'])
def admin_edit_med(med_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    med = db.session.get(Medicine, med_id)
    if not med:
        flash("Medicine not found!")
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        med.name = request.form['name']
        med.dosage = request.form['dosage']
        med.time = request.form['time']
        med.start_date = request.form['start']
        med.end_date = request.form['end']
        db.session.commit()
        flash("Medicine updated!")
        return redirect(url_for('admin_user', user_id=med.user_id))

    return render_template('admin_edit_med.html', med=med)
@app.route('/download_user_data/<int:user_id>')
def download_user_data(user_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, user_id)
    if not user:
        flash("User not found!")
        return redirect(url_for('admin_dashboard'))

    # Fetch medicines explicitly to avoid lazy-loading issues
    medicines = Medicine.query.filter_by(user_id=user.id).all()

    def generate():
        yield "Medicine ID,Name,Dosage,Time,Start Date,End Date,Status\n"
        for med in medicines:
            line = f"{med.id},{med.name},{med.dosage},{med.time},{med.start_date},{med.end_date},{med.status}\n"
            yield line

    return Response(generate(),
                    mimetype='text/csv',
                    headers={"Content-Disposition": f"attachment;filename=user_{user.id}_medicines.csv"})


# ------------------ MAIN ------------------
if __name__ == "__main__":
    if os.path.exists("meds_reminder.db"):
        os.remove("meds_reminder.db")
    with app.app_context():
        db.create_all()

        # Create default admin
        if not User.query.filter_by(email="sathya@gmail.com").first():
            admin_user = User(
                email="sathya@gmail.com",
                password=generate_password_hash("admin")
            )
            db.session.add(admin_user)
            db.session.commit()

    app.run(debug=True)
