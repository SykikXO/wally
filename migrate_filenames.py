
import os
import shutil
import uuid
from app import create_app, db
from app.models import Wallpaper
from app.utils import generate_thumbnail

def is_uuid_like(filename):
    """Check if filename stem looks like a UUID hex string"""
    stem = filename.rsplit('.', 1)[0]
    # UUID hex is 32 chars
    if len(stem) != 32:
        return False
    try:
        int(stem, 16)
        return True
    except ValueError:
        return False

def migrate_filenames():
    app = create_app()
    with app.app_context():
        upload_folder = app.config['UPLOAD_FOLDER']
        wallpapers = Wallpaper.query.all()
        
        migrated_count = 0
        
        print(f"Checking {len(wallpapers)} wallpapers for migration...")
        
        for wallpaper in wallpapers:
            if not is_uuid_like(wallpaper.filename):
                print(f"Migrating: {wallpaper.filename}")
                
                old_path = os.path.join(upload_folder, wallpaper.filename)
                
                if not os.path.exists(old_path):
                    print(f"Warning: File not found {old_path}, skipping.")
                    continue
                
                # Generate new filename
                try:
                    ext = wallpaper.filename.rsplit('.', 1)[1].lower()
                except IndexError:
                    ext = ""
                    
                new_stem = uuid.uuid4().hex
                new_filename = f"{new_stem}.{ext}" if ext else new_stem
                new_path = os.path.join(upload_folder, new_filename)
                
                # Rename file
                try:
                    os.rename(old_path, new_path)
                except OSError as e:
                    print(f"Error renaming {old_path}: {e}")
                    continue
                
                # Update DB
                wallpaper.filename = new_filename
                
                # Handle thumbnail
                # Old thumbnail might be thumb_oldname.webp or similar if using old util
                # But easiest is just to regenerate it
                if wallpaper.thumbnail_filename:
                    old_thumb_path = os.path.join(upload_folder, wallpaper.thumbnail_filename)
                    if os.path.exists(old_thumb_path):
                        os.remove(old_thumb_path)
                
                # Generate new thumbnail
                new_thumb = generate_thumbnail(new_filename)
                if new_thumb:
                    wallpaper.thumbnail_filename = new_thumb
                
                migrated_count += 1
        
        if migrated_count > 0:
            db.session.commit()
            print(f"Successfully migrated {migrated_count} wallpapers.")
        else:
            print("No wallpapers needed migration.")

if __name__ == '__main__':
    migrate_filenames()
