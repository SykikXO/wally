import os
import re
os.environ['SKIP_MAINTENANCE'] = 'true'

from app import create_app, db
from app.models import Wallpaper, Tag
from app.utils import get_ai_tags

def get_allowed_files():
    allowed_files = []
    gitignore_path = '.gitignore'
    if os.path.exists(gitignore_path):
        with open(gitignore_path, 'r') as f:
            for line in f:
                # Match lines like !app/static/uploads/filename.ext
                match = re.search(r'!app/static/uploads/([a-z0-9]+\.(jpg|png|jpeg))', line)
                if match:
                    allowed_files.append(match.group(1))
    return allowed_files

def tag_specific_files():
    app = create_app()
    with app.app_context():
        allowed_filenames = get_allowed_files()
        print(f"Found {len(allowed_filenames)} files in .gitignore.")
        
        upload_folder = app.config['UPLOAD_FOLDER']
        
        for filename in allowed_filenames:
            w = Wallpaper.query.filter_by(filename=filename).first()
            if not w:
                print(f"File {filename} not in DB. Skipping.")
                continue
                
            print(f"Checking {filename}...")
            file_path = os.path.join(upload_folder, filename)
            
            # If it has generic tags or no tags, we process it
            generic_tag_names = {"wallpaper", "hd", "background", "demo", "nature"}
            has_real_tags = any(t.name not in generic_tag_names for t in w.tags)
            
            if has_real_tags:
                print(f"  {filename} already has descriptive tags. Skipping AI processing.")
                continue

            # Clear generic tags if any
            for tag in list(w.tags):
                if tag.name in generic_tag_names:
                    w.tags.remove(tag)

            print(f"  Tagging {filename} with AI...")
            ai_tags = get_ai_tags(file_path)
            if ai_tags:
                for tag_name in ai_tags:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    if tag not in w.tags:
                        w.tags.append(tag)
                print(f"    Added: {', '.join(ai_tags)}")
            
            db.session.commit()

if __name__ == '__main__':
    tag_specific_files()
