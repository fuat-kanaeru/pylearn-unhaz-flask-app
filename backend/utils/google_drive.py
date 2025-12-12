import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# --- KONSTANTA ---
# Scope izin untuk akses Drive (hanya untuk file yang dibuat atau diotorisasi)
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# File kredensial OAuth dari Google Console
CREDENTIALS_FILE = 'credentials/oauth_client.json'
# File tempat token (kunci) akan disimpan
TOKEN_FILE = 'credentials/token.pickle'

# ID folder tujuan di Google Drive Anda
DRIVE_FOLDER_ID = '10PcUcuwPovZu0TZMuobKkf4_oyOk0A-k'  # Ganti dengan Folder ID Anda yang benar


def get_drive_service():
    """Autentikasi dan bangun koneksi ke Google Drive API."""
    creds = None

    # 1. Muat token yang sudah ada dari file
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)

    # 2. Cek validitas: Jika token tidak valid, coba refresh
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Token Akses kedaluwarsa, coba perbarui menggunakan Refresh Token
            print("⏳ Token Akses Kadaluarsa. Mencoba untuk me-refresh otomatis...")
            try:
                creds.refresh(Request())
                print("✅ Token berhasil di-refresh.")
            except Exception as e:
                 # Jika Refresh Token gagal (dicabut/hilang), paksa otorisasi ulang
                 print(f"❌ Refresh token gagal ({e}). Otorisasi ulang diperlukan.")
                 creds = None 
                 
        if not creds or not creds.valid:
            # 3. Otorisasi ulang jika tidak ada kredensial valid
            print("🔑 Memulai Otorisasi Baru untuk mendapatkan Refresh Token persisten...")
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            
            # KUNCI SOLUSI: Menambahkan access_type='offline'
            creds = flow.run_local_server(port=0, access_type='offline') 
            
            # Simpan token baru, yang KINI berisi Refresh Token persisten
            os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
            print("✅ Otorisasi berhasil dan token baru (persisten) disimpan.")

    # 4. Bangun service Google Drive
    return build('drive', 'v3', credentials=creds)


def upload_to_drive(file_path, filename):
    """Upload file PDF ke folder Google Drive dan buat public URL."""
    # Akan memanggil get_drive_service() dan memastikan token valid
    service = get_drive_service() 

    # Metadata file
    file_metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
    media = MediaFileUpload(file_path, mimetype='application/pdf')

    # Upload file
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()

    file_id = uploaded_file.get('id')

    # Buat file bisa dilihat oleh siapa saja (public)
    service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'}
    ).execute()

    print(f"✅ File berhasil diupload: {filename}")
    print(f"🔗 https://drive.google.com/file/d/{file_id}/preview")

    return file_id