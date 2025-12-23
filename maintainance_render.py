import os
import time
import datetime
from PIL import Image
from app import create_app, db
from app.models import Wallpaper, Tag
from app.utils import (
    generate_thumbnail, 
    generate_random_filename
)

# Simplified maintenance for OnRender/Github
# ONLY handles moving files from quarantine to active and generating thumbnails.
# NO AI TAGGING.

LOG_FILE = 'maintainance_render.log'
SLEEP_IDLE = 30

def log_message(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with open(LOG_FILE, 'a') as f:
        f.write(formatted + '\n')

def process_single_quarantine(app):
    with app.app_context():
        wallpaper = Wallpaper.query.filter_by(status='pending').first()
        if not wallpaper:
            return False
            
        quarantine_folder = app.config['QUARANTINE_FOLDER']
        upload_folder = app.config['UPLOAD_FOLDER']
        
        quarantine_path = os.path.join(quarantine_folder, wallpaper.filename)
        
        if not os.path.exists(quarantine_path):
            db.session.delete(wallpaper)
            db.session.commit()
            return True

        try:
            with Image.open(quarantine_path) as img:
                img.verify()
            
            with Image.open(quarantine_path) as img:
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")
                    
                new_filename = generate_random_filename(wallpaper.original_filename)
                final_path = os.path.join(upload_folder, new_filename)
                
                ext = wallpaper.original_filename.rsplit('.', 1)[1].lower() if '.' in wallpaper.original_filename else 'jpg'
                format_map = {'jpg': 'JPEG', 'jpeg': 'JPEG', 'png': 'PNG', 'gif': 'GIF'}
                img.save(final_path, format_map.get(ext, 'JPEG'))
                
            wallpaper.filename = new_filename
            wallpaper.status = 'active'
            
            thumb = generate_thumbnail(new_filename)
            if thumb:
                wallpaper.thumbnail_filename = thumb

            os.remove(quarantine_path)
            log_message(f"Render Success: {wallpaper.original_filename} processed.")
            db.session.commit()
            return True
            
        except Exception as e:
            log_message(f"Render Error: {e}")
            db.session.delete(wallpaper)
            if os.path.exists(quarantine_path):
                os.remove(quarantine_path)
            db.session.commit()
            return True

def main():
    app = create_app()
    log_message("=== Render Maintenance Daemon Started ===")
    
    while True:
        try:
            if not process_single_quarantine(app):
                time.sleep(SLEEP_IDLE)
            else:
                time.sleep(1)
        except Exception as e:
            log_message(f"Render Loop Error: {e}")
            time.sleep(SLEEP_IDLE)

if __name__ == '__main__':
    main()
