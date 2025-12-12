import os
from flask import Flask
from flask_cors import CORS
from sqlalchemy import text
# Pastikan Anda sudah mengimport 'db' dan 'init_db' dari models
from backend.models import db, init_db 

def create_app(reset_db=False):
    """
    Fungsi Pabrik Aplikasi (Application Factory)
    Membuat instance aplikasi Flask dan mengkonfigurasi semua komponen.
    """
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    FRONTEND_DIR = os.path.join(BASE_DIR, '..', 'frontend')

    app = Flask(
        __name__,
        template_folder=os.path.join(FRONTEND_DIR, 'templates'),
        static_folder=os.path.join(FRONTEND_DIR, 'static')
    )

    # Konfigurasi dasar
    # Mengambil kunci rahasia dari Environment Variables Render
    app.config['SECRET_KEY'] = os.environ.get('PYLEARN_SECRET', 'change-me')
    
    # -------------------------------------------------------------
    # PENYESUAIAN KRITIS UNTUK DEPLOYMENT (RENDER/HEROKU)
    # -------------------------------------------------------------
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    if DATABASE_URL:
        # Render dan Heroku memberikan URL dengan skema postgres://
        # Driver SQLAlchemy modern memerlukan skema postgresql://
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

    # Gunakan URL yang sudah dimodifikasi (dari Render) atau fallback lokal
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'postgresql+psycopg2://py_ai:python@localhost:5432/python_db'

    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # -------------------------------------------------------------

    # Inisialisasi database dan CORS
    db.init_app(app)
    CORS(app)

    # Folder upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, '..', 'uploads')
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

    # Register blueprints
    from backend.routes.main import main_bp
    from backend.routes.auth import auth_bp
    from backend.routes.admin import admin_bp
    from backend.routes.profile import profile_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(profile_bp, url_prefix='/profile')

    # Inisialisasi database + seed data
    with app.app_context():
        # Bagian ini HANYA berjalan jika reset_db=True dilewatkan
        if reset_db:
            print("⚠️ Menghapus schema public (development only)...")
            try:
                # Menghapus dan membuat ulang skema untuk reset data
                db.session.execute(text('DROP SCHEMA public CASCADE;'))
                db.session.execute(text('CREATE SCHEMA public;'))
                db.session.commit()
            except Exception as e:
                print(f"Gagal reset schema: {e}")
                db.session.rollback()

        # Buat tabel (jika belum ada) dan isi data awal (seed data)
        # init_db() akan membuat tabel JIKA BELUM ADA.
        init_db(app)

    return app


# === PENTING: Untuk Deployment Gunicorn ===
# Variabel 'app' harus didefinisikan di level global agar Gunicorn dapat mengimportnya.
# KITA PASTIKAN reset_db=False agar data tidak hilang saat deployment.
app = create_app(reset_db=False) 


if __name__ == '__main__':
    # === PENTING: Untuk Development Lokal ===
    # Bagian ini hanya berjalan ketika Anda menjalankan file secara langsung: python -m backend.app
    
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', 5000))

    # Kita menggunakan variabel 'app' yang sudah dibuat di atas (reset_db=False)
    print(f'✅ Server berjalan di http://{HOST}:{PORT}')
    app.run(host=HOST, port=PORT, debug=True)
