from flask import Blueprint, request, jsonify, current_app, url_for, render_template, flash, redirect, abort
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import Wallpaper, User, Tag
from app.extensions import db
from app.utils import allowed_file, generate_thumbnail, generate_random_filename
from sqlalchemy import or_
import os
import uuid
from PIL import Image



bp = Blueprint('main', __name__)

# allowed_file moved to app.utils


@bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():

    # Manual size check for non-admins (300MB)
    if not current_user.is_admin:
        max_size = 300 * 1024 * 1024
        if request.content_length and request.content_length > max_size:
            flash('Total upload size exceeds 300MB limit')
            return redirect(request.url)

    if request.method == 'POST':
        if 'file' not in request.files:

            flash('No file part')
            return redirect(request.url)
        
        files = request.files.getlist('file')
        if not files or files[0].filename == '':
            flash('No selected file')
            return redirect(request.url)
            
        if len(files) > 10 and not current_user.is_admin:
             flash('Maximum 10 files allowed per upload')
             return redirect(request.url)


        # Check total size manually (though nginx/flask limits request body, this is a granular check)
        # Note: request.content_length is accurate for total body size
        

        uploaded_count = 0
        for file in files:
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
                # Save to quarantine folder initially
                quarantine_name = f"pending_{uuid.uuid4().hex}.{ext}"
                file.save(os.path.join(current_app.config['QUARANTINE_FOLDER'], quarantine_name))
                
                # Use original filename as default title, clean it up
                original_title = file.filename.rsplit('.', 1)[0].replace('_', ' ').replace('-', ' ').title()
                title = request.form.get('title') or original_title
                tags_str = request.form.get('tags', '')

                wallpaper = Wallpaper(
                    title=title, 
                    filename=quarantine_name, # Temporary filename in quarantine
                    original_filename=file.filename,
                    status='pending',
                    uploader=current_user
                )
                
                db.session.add(wallpaper)

                # Handle tags (stored even when pending)
                if tags_str:
                    tag_names = [t.strip().lower() for t in tags_str.split(',') if t.strip()]
                    for name in tag_names:
                        tag = Tag.query.filter_by(name=name).first()
                        if not tag:
                            tag = Tag(name=name)
                            db.session.add(tag)
                        wallpaper.tags.append(tag)

                uploaded_count += 1
        
        db.session.commit()
        
        if uploaded_count > 0:
            flash(f'{uploaded_count} wallpaper(s) uploaded and are being processed for security. They will appear soon.')
            return redirect(url_for('main.index'))
        else:
            flash('No valid files uploaded')
            return redirect(request.url)

    return render_template('upload.html')


@bp.route('/', methods=['GET'])
def index():
    page = request.args.get('page', 1, type=int)
    # Use 24 as it is divisible by 2, 3, 4, 6, 8, 12 for better grid filling
    pagination = Wallpaper.query.filter_by(status='active').order_by(Wallpaper.timestamp.desc()).paginate(page=page, per_page=24, error_out=False)
    wallpapers = pagination.items
    
    if request.args.get('load_more'):
        return render_template('partials/wallpaper_grid_items.html', wallpapers=wallpapers)

    next_url = url_for('main.index', page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.index', page=pagination.prev_num) if pagination.has_prev else None

    return render_template('index.html', title='Home', wallpapers=wallpapers, has_next=pagination.has_next, next_url=next_url, prev_url=prev_url)

@bp.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    if not query:
        return redirect(url_for('main.index'))
    
    page = request.args.get('page', 1, type=int)
    
    # Search in title or tags with pagination
    pagination = Wallpaper.query.filter(
        Wallpaper.status == 'active',
        or_(
            Wallpaper.title.ilike(f'%{query}%'),
            Wallpaper.tags.any(Tag.name.ilike(f'%{query}%'))
        )
    ).order_by(Wallpaper.timestamp.desc()).paginate(page=page, per_page=24, error_out=False)
    
    wallpapers = pagination.items

    if request.args.get('load_more'):
        return render_template('partials/wallpaper_grid_items.html', wallpapers=wallpapers)

    return render_template('index.html', title=f'Search: {query}', wallpapers=wallpapers, has_next=pagination.has_next)

@bp.route('/wallpaper/<string:slug>')
def wallpaper_detail(slug):
    # Search for wallpaper where filename starts with slug (UUID part)
    # We do a 'like' query to match slug + '.*'
    wallpaper = Wallpaper.query.filter(Wallpaper.filename.like(f"{slug}.%")).first_or_404()
    
    # Increment views
    # Check if viewer is not uploader (optional, simple logic here)
    if not current_user.is_authenticated or current_user.id != wallpaper.user_id:
        if hasattr(wallpaper.uploader, 'views'):
            wallpaper.uploader.views = (wallpaper.uploader.views or 0) + 1
            db.session.commit()

    # Find similar wallpapers
    # Logic: Wallpapers sharing at least one tag, excluding current one
    similar_wallpapers = []
    if wallpaper.tags:
        tag_ids = [t.id for t in wallpaper.tags]
        similar_wallpapers = Wallpaper.query.filter(
            Wallpaper.status == 'active',
            Wallpaper.id != wallpaper.id,
            Wallpaper.tags.any(Tag.id.in_(tag_ids))
        ).order_by(Wallpaper.timestamp.desc()).limit(4).all()
        
    # If not enough, maybe fill with random or recent? For now, just tags.
    
    return render_template('wallpaper.html', wallpaper=wallpaper, similar_wallpapers=similar_wallpapers)



@bp.route('/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    
    # Increment view count if the viewer is not the user
    if not current_user.is_authenticated or current_user.id != user.id:
        user.views = (user.views or 0) + 1
        db.session.commit()
    
    page = request.args.get('page', 1, type=int)
    is_own_profile = current_user.is_authenticated and current_user.id == user.id
    
    pagination = user.wallpapers.filter_by(status='active').order_by(Wallpaper.timestamp.desc()).paginate(page=page, per_page=24, error_out=False)
    wallpapers = pagination.items

    next_url = url_for('main.user_profile', username=username, page=pagination.next_num) if pagination.has_next else None
    prev_url = url_for('main.user_profile', username=username, page=pagination.prev_num) if pagination.has_prev else None
    
    return render_template('profile.html', user=user, wallpapers=wallpapers, next_url=next_url, prev_url=prev_url, is_own_profile=is_own_profile)
