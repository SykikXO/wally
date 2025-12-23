from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db, login_manager

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

# Association table for wallpapers and tags
wallpaper_tags = db.Table('wallpaper_tags',
    db.Column('wallpaper_id', db.Integer, db.ForeignKey('wallpaper.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    wallpapers = db.relationship('Wallpaper', backref='uploader', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Wallpaper(db.Model):
    __tablename__ = 'wallpaper'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(140), nullable=False)
    filename = db.Column(db.String(140), unique=True, nullable=False)
    thumbnail_filename = db.Column(db.String(140), unique=True, nullable=True)
    status = db.Column(db.String(20), default='pending') # pending, active, malicious
    original_filename = db.Column(db.String(140), nullable=True)
    tags = db.relationship('Tag', secondary=wallpaper_tags, backref=db.backref('wallpapers', lazy='dynamic'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f'<Wallpaper {self.title}>'

    @property
    def slug(self):
        """Returns the UUID part of the filename (without extension)."""
        if '.' in self.filename:
            return self.filename.rsplit('.', 1)[0]
        return self.filename

class Tag(db.Model):
    __tablename__ = 'tag'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, index=True)

    def __repr__(self):
        return f'<Tag {self.name}>'

