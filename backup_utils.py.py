import os
import io
import csv
from datetime import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/drive.file']
BACKUP_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')  # create a folder and get its ID

def get_drive_service():
    creds = None
    token_file = 'token.json'
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return build('drive', 'v3', credentials=creds)

def backup_database_to_drive():
    try:
        engine = create_engine(os.getenv('DATABASE_URL'))
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        output = io.StringIO()
        
        for table in tables:
            output.write(f"\n--- {table} ---\n")
            conn = engine.connect()
            result = conn.execute(f"SELECT * FROM {table}")
            if result.returns_rows:
                writer = csv.writer(output)
                writer.writerow(result.keys())
                writer.writerows(result.fetchall())
            conn.close()
        
        # Upload to Google Drive
        service = get_drive_service()
        file_metadata = {
            'name': f'backup_{timestamp}.csv',
            'parents': [BACKUP_FOLDER_ID]
        }
        media = MediaIoBaseUpload(io.BytesIO(output.getvalue().encode('utf-8')),
                                  mimetype='text/csv',
                                  resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"Backup uploaded, file ID: {file.get('id')}")
        return True
    except Exception as e:
        print(f"Backup failed: {e}")
        return False