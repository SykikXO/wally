import os
import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import Wallpaper, User, Tag
from app.utils import allowed_file, generate_thumbnail
from werkzeug.utils import secure_filename
import shutil

@click.command('load-wallpapers')
@click.argument('folder_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--username', default='admin', help='Username of the uploader')
@with_appcontext
def load_wallpapers_command(folder_path, username):
    """Recursively load wallpapers from a folder into the database."""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f"User '{username}' not found. Please create it first.")
        return

    upload_folder = current_app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    count = 0
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if allowed_file(file):
                file_path = os.path.join(root, file)
                filename = secure_filename(file)
                
                # Handle filename collisions
                if Wallpaper.query.filter_by(filename=filename).first():
                    import uuid
                    filename = f"{uuid.uuid4().hex}_{filename}"
                
                dest_path = os.path.join(upload_folder, filename)
                shutil.copy2(file_path, dest_path)
                
                # Generate thumbnail
                thumb_filename = generate_thumbnail(filename)
                
                # Use subfolder name as tag
                tag_name = os.path.basename(root).lower()
                tag = None
                if tag_name and tag_name != os.path.basename(folder_path).lower():
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                
                title = file.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                wallpaper = Wallpaper(
                    title=title,
                    filename=filename,
                    thumbnail_filename=thumb_filename,
                    uploader=user
                )
                if tag:
                    wallpaper.tags.append(tag)
                
                db.session.add(wallpaper)
                count += 1
                click.echo(f"Added: {title}")

    db.session.commit()
    click.echo(f"Successfully loaded {count} wallpapers.")

@click.command('make-admin')
@click.argument('username')
@with_appcontext
def make_admin_command(username):
    """Promote a user to admin."""
    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f"User '{username}' not found.")
        return
    
    user.is_admin = True
    db.session.commit()
    click.echo(f"User '{username}' is now an admin.")


from flask import current_app
