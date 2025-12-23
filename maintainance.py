import os
import time
import datetime
import uuid
from PIL import Image
from app import create_app, db
from app.models import Wallpaper, User, Tag
from app.utils import (
    get_system_load, 
    get_image_hash, 
    generate_thumbnail, 
    generate_random_filename,
    get_image_dimensions,
    get_ai_tags
)

LOG_FILE = 'maintainance.log'
LOAD_THRESHOLD = 5.0  # Adjust based on CPU cores. Lower means more sensitive.
SLEEP_IDLE = 30       # Seconds to sleep when no work is found
SLEEP_HIGH_LOAD = 10  # Seconds to sleep when load is too high
DRY_RUN = False

def log_message(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {message}"
    print(formatted)
    with open(LOG_FILE, 'a') as f:
        f.write(formatted + '\n')

def process_single_quarantine(app):
    """Processes exactly ONE pending wallpaper from quarantine."""
    with app.app_context():
        wallpaper = Wallpaper.query.filter_by(status='pending').first()
        if not wallpaper:
            return False
            
        quarantine_folder = app.config['QUARANTINE_FOLDER']
        upload_folder = app.config['UPLOAD_FOLDER']
        
        log_message(f"Atomic Task: Security scanning {wallpaper.original_filename}")
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

            # AI AUTO-TAGGING
            ai_tags = get_ai_tags(final_path)
            if ai_tags:
                for tag_name in ai_tags:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    if tag not in wallpaper.tags:
                        wallpaper.tags.append(tag)

            os.remove(quarantine_path)
            log_message(f"Success: {wallpaper.original_filename} processed and moved.")
            db.session.commit()
            return True
            
        except Exception as e:
            log_message(f"Error processing {wallpaper.original_filename}: {e}")
            db.session.delete(wallpaper)
            if os.path.exists(quarantine_path):
                os.remove(quarantine_path)
            db.session.commit()
            return True

def process_single_tagging(app):
    """Processes exactly ONE untagged wallpaper."""
    with app.app_context():
        w = Wallpaper.query.filter(Wallpaper.status == 'active', ~Wallpaper.tags.any()).first()
        if not w:
            return False
            
        upload_folder = app.config['UPLOAD_FOLDER']
        file_path = os.path.join(upload_folder, w.filename)
        
        if not os.path.exists(file_path):
            log_message(f"Missing file for tagging: {w.filename}. Skipping.")
            return False

        log_message(f"Atomic Task: AI tagging existing image {w.filename}")
        ai_tags = get_ai_tags(file_path)
        if ai_tags:
            for tag_name in ai_tags:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                if tag not in w.tags:
                    w.tags.append(tag)
            db.session.commit()
        return True

def run_cleanup(app):
    """Occasional cleanup of orphans and duplicates."""
    with app.app_context():
        log_message("Opportunistic Cleanup: Orphans and Duplicates")
        upload_folder = app.config['UPLOAD_FOLDER']
        
        # Orphans
        db_filenames = set()
        for w in Wallpaper.query.all():
            db_filenames.add(w.filename)
            if w.thumbnail_filename:
                db_filenames.add(w.thumbnail_filename)
        
        for filename in os.listdir(upload_folder):
            if filename not in db_filenames and not filename.startswith('.'):
                try:
                    os.remove(os.path.join(upload_folder, filename))
                except: pass
        
        # Very light version of Duplicates check (could be expanded)
        # For a daemon, we just do a quick pass
        return True

def main():
    app = create_app()
    log_message("=== Maintenance Daemon Started ===")
    
    last_cleanup = 0
    
    while True:
        # 1. Check Load
        load = get_system_load()
        if load > LOAD_THRESHOLD:
            # log_message(f"High Load ({load:.2f}). Pausing...") # Optional: keep logs lean
            time.sleep(SLEEP_HIGH_LOAD)
            continue
            
        # 2. Try Atomic Work
        work_done = False
        
        # Priority 1: Quarantine
        if process_single_quarantine(app):
            work_done = True
            
        # Priority 2: Tagging (if no quarantine work was done to prevent starvation)
        elif process_single_tagging(app):
            work_done = True
            
        # Priority 3: Periodic Cleanup (every 1 hour-ish of active time)
        elif time.time() - last_cleanup > 3600:
            run_cleanup(app)
            last_cleanup = time.time()
            work_done = True
            
        if not work_done:
            # log_message("No work found. Sleeping...")
            time.sleep(SLEEP_IDLE)
        else:
            # Small yield to prevent 100% single-core thrashing if load average lags
            time.sleep(0.5)

def run_maintenance_loop(app):
    """
    Function to be run in a background thread within the Flask app.
    """
    log_message("Starting background maintenance thread...")
    last_cleanup = 0
    
    while True:
        try:
            # On Render/Production, load might not be as reliable to check via getloadavg
            # but we keep it for consistency.
            work_done = False
            
            if process_single_quarantine(app):
                work_done = True
            elif process_single_tagging(app):
                work_done = True
            elif time.time() - last_cleanup > 3600:
                run_cleanup(app)
                last_cleanup = time.time()
                work_done = True
                
            if not work_done:
                time.sleep(SLEEP_IDLE)
            else:
                time.sleep(1) # Small rest between items
        except Exception as e:
            log_message(f"Maintenance thread error: {e}")
            time.sleep(SLEEP_IDLE)

if __name__ == '__main__':
    main()
