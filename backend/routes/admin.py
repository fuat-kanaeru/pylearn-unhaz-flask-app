# backend/routes/admin.py
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from backend.models import db, Module, Lesson, Question, Progress, UserAnswer, User, ContactMessage 
from backend.utils.google_drive import upload_to_drive
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# ============================================================
# Middleware: Hanya Admin yang Boleh Masuk
# ============================================================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Akses ditolak. Anda bukan administrator.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# Dashboard Admin
# ============================================================
@admin_bp.route('/')
@admin_required
def dashboard():
    modules = Module.query.order_by(Module.id).all()
    lessons = Lesson.query.join(Module).add_columns(
        Lesson.id,
        Lesson.title,
        Module.title.label('module_title'),
        Lesson.pdf_url
    ).order_by(Module.id, Lesson.id).all()
    return render_template('admin_dashboard.html', modules=modules, lessons=lessons)


# ============================================================
# 🚨 FITUR BARU 1: TAMBAH AKUN USER BARU (NON-ADMIN)
# ============================================================
@admin_bp.route('/add-user', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Admin membuat akun user (non-admin) baru."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not name or not email or not password:
            flash('Semua field wajib diisi.', 'warning')
            return redirect(url_for('admin.add_user'))
        
        if User.query.filter_by(email=email).first():
            flash('Email ini sudah terdaftar.', 'danger')
            return redirect(url_for('admin.add_user'))
        
        try:
            hashed_password = generate_password_hash(password)
            
            new_user = User(
                name=name,
                email=email,
                password=hashed_password,
                is_admin=False             # <<< Kunci: Set is_admin ke False
            )
            
            db.session.add(new_user)
            db.session.commit()
            flash(f'Akun user "{name}" berhasil ditambahkan ✅', 'success')
            return redirect(url_for('admin.users_progress_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Gagal menambahkan user: {e}', 'danger')
            return redirect(url_for('admin.add_user'))
            
    return render_template('admin_add_user.html')


# ============================================================
# 🚨 FITUR BARU 2: UPDATE PASSWORD USER OLEH ADMIN
# ============================================================
@admin_bp.route('/update-password/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def update_user_password(user_id):
    """Admin mengubah password user tertentu."""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        new_password = request.form.get('new_password')
        
        if not new_password:
            flash('Password baru wajib diisi.', 'warning')
            return redirect(url_for('admin.update_user_password', user_id=user_id)) 
        
        try:
            # Enkripsi password baru
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash(f'Password untuk akun **{user.name}** berhasil diperbarui ✅', 'success')
            return redirect(url_for('admin.users_progress_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Gagal memperbarui password: {e}', 'danger')
            return redirect(url_for('admin.update_user_password', user_id=user_id))
            
    return render_template('admin_update_password.html', user=user) 


# ============================================================
# Tambah Akun Admin Baru 
# ============================================================
@admin_bp.route('/add-admin', methods=['GET', 'POST'])
@admin_required
def add_admin():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not name or not email or not password:
            flash('Semua field wajib diisi.', 'warning')
            return redirect(url_for('admin.add_admin'))
        
        if User.query.filter_by(email=email).first():
            flash('Email ini sudah terdaftar.', 'danger')
            return redirect(url_for('admin.add_admin'))
        
        try:
            hashed_password = generate_password_hash(password)
            
            new_admin = User(
                name=name,
                email=email,
                password=hashed_password, 
                is_admin=True             
            )
            
            db.session.add(new_admin)
            db.session.commit()
            flash(f'Akun admin "{name}" berhasil ditambahkan ✅', 'success')
            return redirect(url_for('admin.users_progress_list'))

        except Exception as e:
            db.session.rollback()
            flash(f'❌ Gagal menambahkan admin: {e}', 'danger')
            return redirect(url_for('admin.add_admin'))
            
    return render_template('admin_add_admin.html')


# ============================================================
# Daftar Pesan Masuk (Contact Messages) 
# ============================================================
@admin_bp.route('/contact-messages')
@admin_required
def contact_messages():
    """Menampilkan semua pesan yang diterima dari formulir kontak."""
    try:
        messages = ContactMessage.query.order_by(
            ContactMessage.is_read.asc(),
            ContactMessage.timestamp.desc()
        ).all()
        
        unread_count = ContactMessage.query.filter_by(is_read=False).count()
        
        return render_template('admin_contact.html', 
                               messages=messages, 
                               unread_count=unread_count)
        
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error memuat pesan kontak: {e}")
        flash('Gagal memuat daftar pesan kontak.', 'danger')
        return redirect(url_for('admin.dashboard'))

# ============================================================
# Toggle Status Dibaca/Belum Dibaca 
# ============================================================
@admin_bp.route('/contact-messages/toggle-read/<int:message_id>', methods=['POST'])
@admin_required
def toggle_read(message_id):
    """Mengubah status is_read pesan kontak."""
    message = ContactMessage.query.get_or_404(message_id)
    
    try:
        message.is_read = not message.is_read
        db.session.commit()
        
        status_text = "Dibaca" if message.is_read else "Belum Dibaca"
        flash(f'Status pesan dari "{message.name}" diubah menjadi {status_text}.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Gagal mengubah status pesan: {e}', 'danger')
        
    return redirect(url_for('admin.contact_messages'))

# ============================================================
# Hapus Pesan Kontak
# ============================================================
@admin_bp.route('/contact-messages/delete/<int:message_id>', methods=['POST'])
@admin_required
def delete_contact(message_id):
    """Menghapus pesan kontak secara permanen."""
    message = ContactMessage.query.get_or_404(message_id)
    
    try:
        db.session.delete(message)
        db.session.commit()
        flash(f'Pesan dari "{message.name}" berhasil dihapus permanen. ✅', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Gagal menghapus pesan: {e}', 'danger')
        
    return redirect(url_for('admin.contact_messages'))


# ============================================================
# Daftar Modul
# ============================================================
@admin_bp.route('/modules-list')
@admin_required
def modules_list():
    modules = Module.query.order_by(Module.id).all()
    return render_template('admin_modules_list.html', modules=modules)


# Upload Materi PDF ke Google Drive
@admin_bp.route('/add-lesson', methods=['GET', 'POST'])
@admin_required
def add_lesson():
    modules = Module.query.order_by(Module.id).all()
    if request.method == 'POST':
        module_id = request.form.get('module_id')
        title = request.form.get('lesson_title')
        pdf_file = request.files.get('lesson_pdf')

        if not title or not module_id:
            flash('Judul pelajaran dan modul harus diisi.', 'warning')
            return redirect(url_for('admin.dashboard'))

        if not pdf_file or pdf_file.filename == '':
            flash('Harap pilih file PDF sebelum mengunggah.', 'warning')
            return redirect(url_for('admin.dashboard'))

        if not pdf_file.filename.lower().endswith('.pdf'):
            flash('File harus berformat PDF.', 'danger')
            return redirect(url_for('admin.dashboard'))

        try:
            filename = secure_filename(pdf_file.filename)
            os.makedirs('tmp', exist_ok=True)
            temp_path = os.path.join('tmp', filename)
            pdf_file.save(temp_path)

            file_id = upload_to_drive(temp_path, filename)
            pdf_url = f"https://drive.google.com/file/d/{file_id}/preview"

            new_lesson = Lesson(module_id=module_id, title=title, pdf_url=pdf_url)
            db.session.add(new_lesson)
            db.session.commit()
            os.remove(temp_path)

            flash(f'Materi "{title}" berhasil diunggah ke Google Drive ✅', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'❌ Gagal upload PDF: {e}', 'danger')

        return redirect(url_for('admin.dashboard'))

    return render_template('admin_dashboard.html', modules=modules)


# Tambah Modul & Soal
@admin_bp.route('/add-content', methods=['POST'])
@admin_required
def add_content():
    content_type = request.form.get('content_type')

    try:
        if content_type == 'module':
            title = request.form.get('module_title')
            desc = request.form.get('module_description')
            if not title:
                flash('Judul modul wajib diisi.', 'warning')
                return redirect(url_for('admin.dashboard'))
            new_module = Module(title=title, description=desc)
            db.session.add(new_module)
            flash(f'Modul "{title}" berhasil ditambahkan ✅', 'success')

        elif content_type == 'question':
            lesson_id = request.form.get('lesson_id')
            question = request.form.get('question_text')
            answer = request.form.get('question_answer')
            points = int(request.form.get('question_points', 10))

            if not lesson_id or not question or not answer:
                flash('Semua field soal wajib diisi.', 'warning')
                return redirect(url_for('admin.dashboard'))

            new_question = Question(
                lesson_id=lesson_id,
                question=question,
                answer=answer,
                points=points
            )
            db.session.add(new_question)
            flash('Soal berhasil ditambahkan ✅', 'success')

        else:
            flash('Tipe konten tidak valid.', 'danger')

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Gagal menambahkan konten: {e}', 'danger')

    return redirect(url_for('admin.dashboard'))


# Daftar Pelajaran (Lessons)
@admin_bp.route('/lessons-list')
@admin_required
def lessons_list():
    lessons = Lesson.query.join(Module).add_columns(
        Lesson.id,
        Lesson.title,
        Lesson.pdf_url,
        Module.title.label('module_title')
    ).order_by(Module.id, Lesson.id).all()
    return render_template('admin_lessons_list.html', lessons=lessons)


# Daftar Soal
@admin_bp.route('/questions-list')
@admin_required
def questions_list():
    questions = (
        db.session.query(
            Question.id,
            Question.question,
            Question.answer,
            Question.points,
            Lesson.title.label('lesson_title'),
            Module.title.label('module_title')
        )
        .select_from(Question)
        .join(Lesson, Lesson.id == Question.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .order_by(Module.id, Lesson.id, Question.id)
        .all()
    )
    return render_template('admin_questions_list.html', questions=questions)


# Daftar Akun dan Progres Pengguna
@admin_bp.route('/users-progress-list')
@admin_required
def users_progress_list():
    total_lessons = db.session.query(Lesson).count()
    
    all_users = db.session.query(
        User.id,
        User.name, 
        User.email,
        User.is_admin
    ).order_by(User.id).all()
    
    progress_data = db.session.query(
        Progress.user_id,
        db.func.count(db.distinct(Progress.lesson_id)).label('completed_lessons_count')
    ).filter(Progress.completed == True) \
    .group_by(Progress.user_id) \
    .all()
    
    progress_map = {item.user_id: item.completed_lessons_count for item in progress_data}

    final_users_list = []
    for user in all_users:
        completed_lessons = progress_map.get(user.id, 0)
        
        if total_lessons > 0:
            total_progress_percent = round((completed_lessons / total_lessons) * 100, 1)
        else:
            total_progress_percent = 0.0

        final_users_list.append({
            'id': user.id,
            'name': user.name, 
            'email': user.email,
            'is_admin': user.is_admin,
            'completed_lessons': completed_lessons,
            'total_progress_percent': total_progress_percent
        })

    return render_template(
        'admin_users_list.html', 
        users=final_users_list, 
        total_lessons=total_lessons
    )


# Hapus Pengguna (User)
@admin_bp.route('/delete/user/<int:id>', methods=['POST'])
@admin_required
def delete_user(id):
    user_to_delete = User.query.get_or_404(id)
    
    if user_to_delete.id == session.get('user_id'):
        flash('❌ Anda tidak dapat menghapus akun admin yang sedang aktif Anda gunakan.', 'danger')
        return redirect(url_for('admin.users_progress_list'))

    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash(f'Akun "{user_to_delete.name}" berhasil dihapus, termasuk semua data progresnya. ✅', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Gagal menghapus pengguna: {e}', 'danger')
    return redirect(url_for('admin.users_progress_list'))


# Hapus Modul
@admin_bp.route('/delete/module/<int:id>', methods=['POST'])
@admin_required
def delete_module(id):
    module = Module.query.get_or_404(id)
    try:
        lessons = Lesson.query.filter_by(module_id=id).all()
        for lesson in lessons:
            Question.query.filter_by(lesson_id=lesson.id).delete()
            Progress.query.filter_by(lesson_id=lesson.id).delete()
            db.session.delete(lesson)

        db.session.delete(module)
        db.session.commit()
        flash(f'Modul "{module.title}" dan seluruh isinya berhasil dihapus ✅', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Gagal menghapus modul: {e}', 'danger')
    return redirect(url_for('admin.modules_list'))


# Hapus Pelajaran (Lesson)
@admin_bp.route('/delete/lesson/<int:id>', methods=['POST'])
@admin_required
def delete_lesson(id):
    lesson = Lesson.query.get_or_404(id)
    try:
        Question.query.filter_by(lesson_id=id).delete()
        Progress.query.filter_by(lesson_id=id).delete()
        db.session.delete(lesson)
        db.session.commit()
        flash(f'Pelajaran "{lesson.title}" berhasil dihapus ✅', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Gagal menghapus pelajaran: {e}', 'danger')
    return redirect(url_for('admin.lessons_list'))


# Hapus Soal
@admin_bp.route('/delete/question/<int:id>', methods=['POST'])
@admin_required
def delete_question(id):
    question = Question.query.get_or_404(id)
    try:
        UserAnswer.query.filter_by(question_id=id).delete()
        db.session.delete(question)
        db.session.commit()
        flash('Soal berhasil dihapus ✅', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'❌ Gagal menghapus soal: {e}', 'danger')
    return redirect(url_for('admin.questions_list'))