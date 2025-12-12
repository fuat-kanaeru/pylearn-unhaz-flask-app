from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from datetime import datetime

# ==========================================================
# 0️⃣ INISIALISASI SQLAlchemy
# ==========================================================
db = SQLAlchemy()

# ==========================================================
# 1️⃣ MODEL USERS
# ==========================================================
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    progress = db.relationship('Progress', backref='user', cascade='all, delete-orphan')
    answers = db.relationship('UserAnswer', backref='user', cascade='all, delete-orphan')
    # 🚨 BARU: Relasi untuk Jawaban Pilihan Ganda
    mcq_answers = db.relationship('MultipleChoiceAnswer', backref='user', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<User {self.name}>"

# ==========================================================
# 2️⃣ MODEL MODULES
# ==========================================================
class Module(db.Model):
    __tablename__ = 'modules'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    lessons = db.relationship('Lesson', backref='module', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Module {self.title}>"

# ==========================================================
# 3️⃣ MODEL LESSONS
# ==========================================================
class Lesson(db.Model):
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('modules.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)
    pdf_url = db.Column(db.String(500))

    questions = db.relationship('Question', backref='lesson', cascade='all, delete-orphan')
    # 🚨 BARU: Relasi ke Soal Pilihan Ganda
    mcqs = db.relationship('MultipleChoiceQuestion', backref='lesson', cascade='all, delete-orphan')
    
    progress = db.relationship('Progress', backref='lesson', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Lesson {self.title}>"

# ==========================================================
# 4️⃣ MODEL QUESTIONS (Isian Singkat)
# ==========================================================
class Question(db.Model):
    __tablename__ = 'questions'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.String(255), nullable=False) # Jawaban isian singkat
    points = db.Column(db.Integer, default=10)

    answers = db.relationship('UserAnswer', backref='question', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<Question {self.id}>"

# ==========================================================
# 🚨 MODEL BARU: Pilihan Ganda (MultipleChoiceQuestion)
# ==========================================================
class MultipleChoiceQuestion(db.Model):
    __tablename__ = 'multiple_choice_questions'

    id = db.Column(db.Integer, primary_key=True)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(500), nullable=False)
    option_b = db.Column(db.String(500), nullable=False)
    option_c = db.Column(db.String(500), nullable=False)
    option_d = db.Column(db.String(500), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False) # 'A', 'B', 'C', atau 'D'
    points = db.Column(db.Integer, default=10)

    # Relasi dengan Jawaban User
    answers = db.relationship('MultipleChoiceAnswer', backref='mcq', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<MCQ {self.id}>"

# ==========================================================
# 🚨 MODEL BARU: Jawaban Pilihan Ganda (MultipleChoiceAnswer)
# ==========================================================
class MultipleChoiceAnswer(db.Model):
    __tablename__ = 'multiple_choice_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('multiple_choice_questions.id', ondelete='CASCADE'), nullable=False)
    user_choice = db.Column(db.String(1), nullable=False) # Jawaban user: 'A', 'B', 'C', atau 'D'
    is_correct = db.Column(db.Boolean, default=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'question_id', name='unique_user_mcq'),)


# ==========================================================
# 5️⃣ MODEL PROGRESS
# ==========================================================
class Progress(db.Model):
    __tablename__ = 'progress'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lessons.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Integer, default=0)
    completed = db.Column(db.Boolean, default=False)
    last_update = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='unique_user_lesson'),)

# ==========================================================
# 6️⃣ MODEL USER_ANSWERS (Jawaban Isian Singkat)
# ==========================================================
class UserAnswer(db.Model):
    __tablename__ = 'user_answers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False)
    answered_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'question_id', name='unique_user_question'),)

# ==========================================================
# 7️⃣ MODEL KONTAK
# ==========================================================
class ContactMessage(db.Model):
    """Model untuk menyimpan pesan yang dikirim melalui formulir Kontak."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False) # Status pesan, default belum dibaca

    def __repr__(self):
        return f'<ContactMessage {self.email} - Subject: {self.subject}>'


# ==========================================================
# 8️⃣ FUNGSI INISIALISASI DATABASE (seed_data - DIMODIFIKASI)
# ==========================================================
def seed_data():
    """Mengisi data awal (admin + modul dasar) jika belum ada."""
    if not User.query.filter_by(email='admin@pylearn.com').first():
        admin = User(
            name='Admin Utama',
            email='admin@pylearn.com',
            password=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        db.session.flush()

    if Module.query.count() == 0:
        dasar = Module(title='Dasar Python', description='Belajar variabel dan kontrol alur.')
        analisis = Module(title='Analisis Data', description='Pengenalan Pandas dan Numpy.')
        db.session.add_all([dasar, analisis])
        db.session.flush()

        lesson1 = Lesson(module_id=dasar.id, title='Variabel & Tipe Data',
                         content='Pelajari integer, string, dan boolean.')
        lesson2 = Lesson(module_id=dasar.id, title='Struktur Kondisi (If/Else)',
                         content='Pelajari penggunaan if, elif, else.')
        db.session.add_all([lesson1, lesson2])
        db.session.flush()

        # Soal Isian Singkat (Existing)
        q1 = Question(lesson_id=lesson1.id, question='Apa keyword untuk mencetak output?', answer='print', points=10)
        q2 = Question(lesson_id=lesson2.id, question='Keyword awal untuk kondisi?', answer='if', points=15)
        db.session.add_all([q1, q2])
        
        # 🚨 BARU: Soal Pilihan Ganda
        mcq1 = MultipleChoiceQuestion(
            lesson_id=lesson1.id, 
            question='Manakah tipe data yang digunakan untuk bilangan bulat?', 
            option_a='string', 
            option_b='float', 
            option_c='integer', 
            option_d='boolean', 
            correct_option='C', 
            points=10
        )
        mcq2 = MultipleChoiceQuestion(
            lesson_id=lesson2.id, 
            question='Apa yang akan dieksekusi jika kondisi `if` bernilai False?', 
            option_a='`pass`', 
            option_b='`then`', 
            option_c='`else`', 
            option_d='`skip`', 
            correct_option='C', 
            points=10
        )
        db.session.add_all([mcq1, mcq2])

    db.session.commit()
    print("✅ Data awal berhasil dimasukkan.")

def init_db(app):
    """Membuat tabel dan mengisi data awal"""
    with app.app_context():
        # db.drop_all() # Hapus ini jika Anda tidak ingin menghapus database lama
        db.create_all()
        seed_data()