from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify
from sqlalchemy import text
from backend.models import db, ContactMessage, Question, UserAnswer, MultipleChoiceQuestion, MultipleChoiceAnswer, Progress
from datetime import datetime 

main_bp = Blueprint('main', __name__)

# ---------------------------------------------
# 1. HOME PAGE
# ---------------------------------------------
@main_bp.route('/')
def home():
    user_name = session.get('user_name')
    return render_template('home.html', user_name=user_name)


# ---------------------------------------------
# 2. TAMPILAN MODULES (KATEGORI UTAMA)
# ---------------------------------------------
@main_bp.route('/modules')
def modules():
    """Daftar Modul Utama (Kategori) + Progres Total."""
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu untuk mengakses modul.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    try:
        with db.engine.connect() as conn:
            query = text("""
                SELECT
                    m.id,
                    m.title,
                    m.description,
                    COALESCE((
                        SELECT SUM(p.score)
                        FROM lessons l 
                        JOIN progress p ON l.id = p.lesson_id
                        WHERE l.module_id = m.id AND p.user_id = :uid
                    ), 0) AS total_score,
                    
                    -- 🚨 MODIFIKASI: Hitung total maksimal score dari Question DAN MultipleChoiceQuestion
                    COALESCE((
                        SELECT SUM(q.points)
                        FROM lessons l 
                        JOIN questions q ON l.id = q.lesson_id
                        WHERE l.module_id = m.id
                    ), 0) +
                    COALESCE((
                        SELECT SUM(mcq.points)
                        FROM lessons l 
                        JOIN multiple_choice_questions mcq ON l.id = mcq.lesson_id
                        WHERE l.module_id = m.id
                    ), 0) AS max_score

                FROM modules m
                ORDER BY m.id
            """)
            mods = conn.execute(query, {"uid": user_id}).mappings().all()

        return render_template('modules.html', modules=mods)

    except Exception as e:
        print("❌ Error di /modules:", e)
        flash("Terjadi kesalahan saat memuat modul.", "danger")
        return redirect(url_for('main.home'))


# ---------------------------------------------
# 3. DETAIL MODULE (DAFTAR LESSONS/SUB-MODUL)
# ---------------------------------------------
@main_bp.route('/modules/<int:id>')
def module_detail(id):
    """Menampilkan daftar pelajaran (lessons) untuk Modul Utama tertentu."""
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    try:
        with db.engine.connect() as conn:
            mod = conn.execute(text("SELECT * FROM modules WHERE id = :id"), {"id": id}).mappings().first()

            if not mod:
                flash('Modul tidak ditemukan.', 'danger')
                return redirect(url_for('main.modules'))

            lessons = conn.execute(text("""
                SELECT
                    l.id,
                    l.title,
                    COALESCE(p.score, 0) AS score,
                    COALESCE(CAST(p.completed AS INTEGER), 0) AS completed,
                    
                    -- 🚨 MODIFIKASI: Hitung total maksimal score dari Question DAN MultipleChoiceQuestion
                    COALESCE((
                        SELECT SUM(points) FROM questions WHERE lesson_id = l.id
                    ), 0) +
                    COALESCE((
                        SELECT SUM(points) FROM multiple_choice_questions WHERE lesson_id = l.id
                    ), 0) AS max_score

                FROM lessons l
                LEFT JOIN progress p ON l.id = p.lesson_id AND p.user_id = :uid
                WHERE l.module_id = :mid
                ORDER BY l.id
            """), {"uid": user_id, "mid": id}).mappings().all()

        return render_template('module_lessons.html', module=mod, lessons=lessons)

    except Exception as e:
        print("❌ Error di /modules/<id>:", e)
        flash("Terjadi kesalahan saat memuat pelajaran modul.", "danger")
        return redirect(url_for('main.modules'))


# ---------------------------------------------
# 4. DETAIL LESSON (KONTEN + SOAL) - DIMODIFIKASI
# ---------------------------------------------
@main_bp.route('/lessons/<int:id>')
def lesson_detail(id):
    """Menampilkan konten pelajaran dan soal latihan."""
    if 'user_id' not in session:
        flash('Silakan login terlebih dahulu.', 'warning')
        return redirect(url_for('auth.login'))

    user_id = session['user_id']

    try:
        with db.engine.connect() as conn:
            lesson = conn.execute(text("SELECT * FROM lessons WHERE id = :id"), {"id": id}).mappings().first()
            if not lesson:
                flash('Pelajaran tidak ditemukan.', 'danger')
                return redirect(url_for('main.modules'))

            # 🚨 BARU: Ambil Soal Pilihan Ganda (MCQs)
            mcqs = conn.execute(
                text("SELECT * FROM multiple_choice_questions WHERE lesson_id = :id ORDER BY id"), {"id": id}
            ).mappings().all()

            # Ambil Soal Isian Singkat (Existing)
            questions = conn.execute(
                text("SELECT * FROM questions WHERE lesson_id = :id ORDER BY id"), {"id": id}
            ).mappings().all()

            # Ambil Jawaban Isian Singkat yang sudah dijawab
            answered_short = conn.execute(text("""
                SELECT question_id FROM user_answers
                WHERE user_id = :uid AND question_id IN (
                    SELECT id FROM questions WHERE lesson_id = :lid
                )
            """), {"uid": user_id, "lid": id}).mappings().all()
            
            # 🚨 BARU: Ambil Jawaban Pilihan Ganda yang sudah dijawab
            answered_mcq = conn.execute(text("""
                SELECT question_id, user_choice, is_correct FROM multiple_choice_answers
                WHERE user_id = :uid AND question_id IN (
                    SELECT id FROM multiple_choice_questions WHERE lesson_id = :lid
                )
            """), {"uid": user_id, "lid": id}).mappings().all()


        # Proses ID soal yang sudah dijawab (untuk Isian Singkat)
        answered_ids_short = {row['question_id'] for row in answered_short}
        
        # Proses ID soal yang sudah dijawab (untuk Pilihan Ganda)
        answered_mcqs_map = {
            row['question_id']: {'choice': row['user_choice'], 'correct': row['is_correct']} 
            for row in answered_mcq
        }


        return render_template(
            'lesson_detail.html',
            lesson=lesson,
            questions=questions,          # Soal Isian Singkat
            mcqs=mcqs,                    # Soal Pilihan Ganda
            answered_ids_short=answered_ids_short, # Status Isian Singkat
            answered_mcqs_map=answered_mcqs_map    # Status Pilihan Ganda
        )

    except Exception as e:
        print("❌ Error di /lessons/<id>:", e)
        flash("Terjadi kesalahan saat memuat pelajaran.", "danger")
        return redirect(url_for('main.modules'))


# ---------------------------------------------
# FUNGSI BANTUAN: UPDATE PROGRESS UTAMA
# ---------------------------------------------
def update_lesson_progress(conn, user_id, lesson_id):
    """
    Menghitung ulang total skor dan status completed untuk Lesson, 
    berdasarkan kedua tipe soal (Question dan MCQ).
    """
    
    # 1. Hitung total skor yang didapat (dari kedua tipe soal)
    total_score_short = conn.execute(text("""
        SELECT COALESCE(SUM(q.points), 0)
        FROM user_answers ua
        JOIN questions q ON ua.question_id = q.id
        WHERE ua.user_id = :uid AND q.lesson_id = :lid
    """), {"uid": user_id, "lid": lesson_id}).scalar() or 0

    total_score_mcq = conn.execute(text("""
        SELECT COALESCE(SUM(mcq.points), 0)
        FROM multiple_choice_answers mca
        JOIN multiple_choice_questions mcq ON mca.question_id = mcq.id
        WHERE mca.user_id = :uid AND mcq.lesson_id = :lid AND mca.is_correct = TRUE
    """), {"uid": user_id, "lid": lesson_id}).scalar() or 0
    
    total_score = total_score_short + total_score_mcq

    # 2. Hitung total soal (dari kedua tipe soal)
    total_questions = conn.execute(text("""
        SELECT COUNT(id) FROM questions WHERE lesson_id = :lid
    """), {"lid": lesson_id}).scalar() or 0
    
    total_mcqs = conn.execute(text("""
        SELECT COUNT(id) FROM multiple_choice_questions WHERE lesson_id = :lid
    """), {"lid": lesson_id}).scalar() or 0
    
    total_all_q = total_questions + total_mcqs


    # 3. Hitung total soal yang sudah dijawab dengan benar
    correct_short = conn.execute(text("""
        SELECT COUNT(DISTINCT question_id)
        FROM user_answers
        WHERE user_id = :uid AND question_id IN (
            SELECT id FROM questions WHERE lesson_id = :lid
        )
    """), {"uid": user_id, "lid": lesson_id}).scalar() or 0

    correct_mcq = conn.execute(text("""
        SELECT COUNT(DISTINCT question_id)
        FROM multiple_choice_answers
        WHERE user_id = :uid AND question_id IN (
            SELECT id FROM multiple_choice_questions WHERE lesson_id = :lid
        ) AND is_correct = TRUE
    """), {"uid": user_id, "lid": lesson_id}).scalar() or 0
    
    correct_all_q = correct_short + correct_mcq

    # 4. Tentukan status completed
    completed = True if total_all_q > 0 and correct_all_q >= total_all_q else False

    # 5. Upsert progress
    conn.execute(text("""
        INSERT INTO progress (user_id, lesson_id, score, completed, last_update)
        VALUES (:uid, :lid, :score, :comp, NOW())
        ON CONFLICT (user_id, lesson_id)
        DO UPDATE SET score = EXCLUDED.score, completed = EXCLUDED.completed, last_update = NOW()
    """), {"uid": user_id, "lid": lesson_id, "score": total_score, "comp": completed})
    
    return completed # Mengembalikan status penyelesaian


# ---------------------------------------------
# 5. API CHECK ANSWER (Isian Singkat) - DIMODIFIKASI
# ---------------------------------------------
@main_bp.route('/check_answer', methods=['POST'])
def check_answer():
    """Menerima jawaban user (Isian Singkat) dan update progres di tabel progress."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Anda harus login.'}), 401

    data = request.get_json()
    question_id = data.get('question_id')
    user_answer = (data.get('answer') or '').strip().lower()

    if not question_id:
        return jsonify({'status': 'error', 'message': 'ID soal tidak valid.'})

    try:
        with db.engine.begin() as conn:
            q_data = conn.execute(text("""
                SELECT lesson_id, answer FROM questions WHERE id = :qid
            """), {"qid": question_id}).mappings().first()

            if not q_data:
                return jsonify({'status': 'error', 'message': 'Soal isian singkat tidak ditemukan.'})

            lesson_id = q_data['lesson_id']
            correct_answer = q_data['answer'].strip().lower()
            
            is_correct = (user_answer == correct_answer)

            if is_correct:
                # Simpan jawaban benar (jika belum)
                conn.execute(text("""
                    INSERT INTO user_answers (user_id, question_id)
                    VALUES (:uid, :qid)
                    ON CONFLICT (user_id, question_id) DO NOTHING
                """), {"uid": user_id, "qid": question_id})

                # Update Progres Lesson
                update_lesson_progress(conn, user_id, lesson_id)

                return jsonify({'status': 'correct', 'message': '✅ Jawaban Benar! Progres diperbarui.'})

            else:
                return jsonify({'status': 'wrong', 'message': '❌ Jawaban Salah. Coba lagi!'})

    except Exception as e:
        print("❌ Database Error di check_answer (Isian Singkat):", e)
        return jsonify({'status': 'error', 'message': 'Terjadi kesalahan database.'}), 500


# ---------------------------------------------
# 🚨 BARU: API SUBMIT MCQ ANSWER (Pilihan Ganda)
# ---------------------------------------------
@main_bp.route('/submit_mcq_answer', methods=['POST'])
def submit_mcq_answer():
    """Menerima jawaban user (Pilihan Ganda) dan update progres."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'Anda harus login.'}), 401

    data = request.get_json()
    question_id = data.get('question_id')
    user_choice = (data.get('user_choice') or '').strip().upper() # A, B, C, atau D

    if user_choice not in ['A', 'B', 'C', 'D']:
        return jsonify({'status': 'error', 'message': 'Pilihan jawaban tidak valid.'})

    try:
        with db.engine.begin() as conn:
            # 1. Ambil data soal
            mcq_data = conn.execute(text("""
                SELECT lesson_id, correct_option, points FROM multiple_choice_questions WHERE id = :qid
            """), {"qid": question_id}).mappings().first()

            if not mcq_data:
                return jsonify({'status': 'error', 'message': 'Soal pilihan ganda tidak ditemukan.'})

            lesson_id = mcq_data['lesson_id']
            correct_option = mcq_data['correct_option'].strip().upper()
            
            is_correct = (user_choice == correct_option)

            # 2. Simpan atau perbarui jawaban Pilihan Ganda
            conn.execute(text("""
                INSERT INTO multiple_choice_answers (user_id, question_id, user_choice, is_correct, answered_at)
                VALUES (:uid, :qid, :choice, :correct, NOW())
                ON CONFLICT (user_id, question_id)
                DO UPDATE SET user_choice = EXCLUDED.user_choice, is_correct = EXCLUDED.is_correct, answered_at = NOW()
            """), {
                "uid": user_id, 
                "qid": question_id, 
                "choice": user_choice, 
                "correct": is_correct
            })
            
            # 3. Update Progres Lesson (menggunakan fungsi bantuan yang baru)
            update_lesson_progress(conn, user_id, lesson_id)
            
            
            if is_correct:
                return jsonify({
                    'status': 'correct', 
                    'message': '✅ Jawaban Benar! Progres diperbarui.', 
                    'user_choice': user_choice
                })
            else:
                return jsonify({
                    'status': 'wrong', 
                    'message': f'❌ Jawaban Salah. Jawaban yang benar adalah {correct_option}.', 
                    'user_choice': user_choice,
                    'correct_option': correct_option
                })

    except Exception as e:
        print("❌ Database Error di submit_mcq_answer:", e)
        return jsonify({'status': 'error', 'message': 'Terjadi kesalahan database.'}), 500


# ---------------------------------------------
# 6. SUBMIT FORMULIR KONTAK (BARU)
# ---------------------------------------------
@main_bp.route('/contact', methods=['POST'])
def contact_submit():
    """Menerima dan menyimpan pesan dari formulir kontak ke database."""
    # Ambil data dari formulir
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject') 
    message = request.form.get('message')
    
    # Validasi input dasar
    if not name or not email or not message:
        flash('Semua kolom wajib diisi (Nama, Email, Pesan).', 'danger')
        # Redirect ke halaman utama dan kembali ke bagian kontak
        return redirect(url_for('main.home', _external=True) + '#contact-section')

    try:
        # Buat objek ContactMessage baru
        new_message = ContactMessage(
            name=name,
            email=email,
            subject=subject or 'Tanpa Subjek',
            message=message,
            timestamp=datetime.utcnow()
        )
        db.session.add(new_message)
        db.session.commit()
        
        flash('Pesan Anda berhasil terkirim! Tim kami akan segera meninjaunya.', 'success')
        # Redirect ke halaman utama dan kembali ke bagian kontak
        return redirect(url_for('main.home', _external=True) + '#contact-section')
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ Error menyimpan pesan kontak: {e}")
        flash('Terjadi kesalahan server saat mengirim pesan. Mohon coba lagi nanti.', 'danger')
        # Redirect ke halaman utama dan kembali ke bagian kontak
        return redirect(url_for('main.home', _external=True) + '#contact-section')

# === KODE ADMIN SEMENTARA (MASUKKAN EMAIL & PASSWORD ANDA) ===

from backend.models import db, User 
from werkzeug.security import generate_password_hash

@main_bp.route('/buat-admin-rahasia') # <-- Route rahasia yang akan diakses
def create_admin_secretly():

    # GANTI DENGAN KREDENSIAL YANG ANDA INGINKAN!
    admin_email = 'admin@pylearn.com' 
    admin_password = 'taufik' 

    # Logika untuk membuat pengguna dengan is_admin=True
    existing_user = User.query.filter_by(email=admin_email).first()

    if not existing_user:
        hashed_password = generate_password_hash(admin_password, method='scrypt')
        new_admin = User(
            email=admin_email,
            password=hashed_password,
            is_admin=True 
        )

        db.session.add(new_admin)
        db.session.commit()
        return "Akun admin berhasil dibuat. SEGERA HAPUS KODE INI!"
    else:
        return "Admin sudah ada."

# === AKHIR KODE ADMIN SEMENTARA ===

