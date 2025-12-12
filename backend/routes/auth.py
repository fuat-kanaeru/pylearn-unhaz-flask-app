# backend/routes/auth.py (Versi PostgreSQL dengan SQLAlchemy)
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from backend.models import db, User, Module, Lesson, Progress, Question

auth_bp = Blueprint('auth', __name__)

# -------------------------
# REGISTER
# -------------------------
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Halaman pendaftaran user baru."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        if not name or not email or not password:
            flash('Semua field harus diisi.', 'danger')
            return redirect(url_for('auth.register'))

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash('Email sudah terdaftar.', 'danger')
            return redirect(url_for('auth.register'))

        hashed = generate_password_hash(password)
        new_user = User(name=name, email=email, password=hashed, is_admin=False)
        db.session.add(new_user)
        db.session.commit()

        flash('Registrasi berhasil. Silakan login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')


# -------------------------
# LOGIN
# -------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Halaman login."""
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['is_admin'] = user.is_admin
            flash(f'Selamat datang, {user.name}!', 'success')
            return redirect(url_for('main.home'))
        else:
            flash('Email atau password salah.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('login.html')


# -------------------------
# LOGOUT
# -------------------------
@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))


# -------------------------
# PROFILE + PROGRES BELAJAR
# -------------------------
@auth_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Tampilkan profil dan progres belajar per pelajaran/sub-modul."""
    user_id = session.get('user_id')
    if not user_id:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        session.clear()
        flash('User tidak ditemukan.', 'danger')
        return redirect(url_for('auth.login'))

    # Ambil progres belajar (gabungan Module, Lesson, Progress)
    progress_data = (
        db.session.query(
            Module.title.label("module_title"),
            Lesson.title.label("lesson_title"),
            Lesson.id.label("lesson_id"),
            Progress.score,
            db.func.sum(Question.points).label("max_score"),
            Progress.completed
        )
        .join(Lesson, Lesson.module_id == Module.id)
        .outerjoin(Progress, (Progress.lesson_id == Lesson.id) & (Progress.user_id == user_id))
        .outerjoin(Question, Question.lesson_id == Lesson.id)
        .group_by(Module.id, Lesson.id, Progress.score, Progress.completed)
        .order_by(Module.id, Lesson.id)
        .all()
    )

    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        new_email = request.form.get('email', '').strip().lower()

        if not new_name or not new_email:
            flash('Nama dan email tidak boleh kosong.', 'danger')
            return redirect(url_for('auth.profile'))

        existing = User.query.filter(User.email == new_email, User.id != user_id).first()
        if existing:
            flash('Email sudah digunakan user lain.', 'danger')
            return redirect(url_for('auth.profile'))

        user.name = new_name
        user.email = new_email
        db.session.commit()
        session['user_name'] = new_name
        flash('Profil berhasil diperbarui.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('profile.html', user=user, progress_data=progress_data)


# -------------------------
# UPDATE PASSWORD
# -------------------------
@auth_bp.route('/update-password', methods=['POST'])
def update_password():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash('User tidak ditemukan.', 'danger')
        return redirect(url_for('auth.login'))

    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')

    if not old_password or not new_password:
        flash('Isi password lama dan baru.', 'danger')
        return redirect(url_for('auth.profile'))

    if not check_password_hash(user.password, old_password):
        flash('Password lama salah.', 'danger')
        return redirect(url_for('auth.profile'))

    user.password = generate_password_hash(new_password)
    db.session.commit()

    flash('Password berhasil diperbarui.', 'success')
    return redirect(url_for('auth.profile'))


# -------------------------
# FORGOT PASSWORD
# -------------------------
@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('new_password', '')

        if not email or not new_password:
            flash('Isi email dan password baru.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        user = User.query.filter_by(email=email).first()
        if not user:
            flash('Email tidak ditemukan.', 'danger')
            return redirect(url_for('auth.forgot_password'))

        user.password = generate_password_hash(new_password)
        db.session.commit()

        flash('Password berhasil direset. Silakan login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('forgot_password.html')


# -------------------------
# DELETE ACCOUNT
# -------------------------
@auth_bp.route('/delete-account', methods=['GET', 'POST'])
def delete_account():
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash('User tidak ditemukan.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        # Hapus progres & jawaban terkait
        Progress.query.filter_by(user_id=user.id).delete()
        db.session.delete(user)
        db.session.commit()
        session.clear()
        flash('Akun Anda telah dihapus.', 'info')
        return redirect(url_for('main.home'))

    return render_template('delete_account.html', user=user)
