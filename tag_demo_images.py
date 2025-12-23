import os
os.environ['SKIP_MAINTENANCE'] = 'true'

from app import create_app, db
from app.models import Wallpaper, Tag
from app.utils import get_ai_tags

def tag_images():
    app = create_app()
    with app.app_context():
        # Get the first 50 wallpapers
        wallpapers = Wallpaper.query.limit(50).all()
        generic_tag_names = ["wallpaper", "hd", "background", "demo", "nature", "minimal", "art"]
        
        # 1. Clear generic tags from these wallpapers
        generic_tags = Tag.query.filter(Tag.name.in_(generic_tag_names)).all()
        for w in wallpapers:
            for gt in generic_tags:
                if gt in w.tags:
                    w.tags.remove(gt)
        db.session.commit()
        print("Cleared generic tags from wallpapers.")

        # 2. Perform real AI tagging
        upload_folder = app.config['UPLOAD_FOLDER']
        count = 0
        for w in wallpapers:
            print(f"[{count+1}/50] Tagging {w.filename}...")
            file_path = os.path.join(upload_folder, w.filename)
            ai_tags = get_ai_tags(file_path)
            
            if ai_tags:
                for tag_name in ai_tags:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    if tag not in w.tags:
                        w.tags.append(tag)
                print(f"  Added: {', '.join(ai_tags)}")
            else:
                print("  No AI tags generated.")
            
            count += 1
            if count % 10 == 0:
                db.session.commit() # Periodic commit
        
        db.session.commit()
        print(f"Successfully processed {count} images with AI tagging.")

if __name__ == '__main__':
    tag_images()
