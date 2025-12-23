import os
import uuid
import base64
import requests
import re
from PIL import Image
from flask import current_app

def generate_random_filename(filename):
    """
    Generates a secure random filename while preserving the extension.
    """
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if not ext:
        # Fallback or error if no extension, but simple fallback here
        return f"{uuid.uuid4().hex}"
    return f"{uuid.uuid4().hex}.{ext}"

def generate_thumbnail(filename, size=(300, 300)):
    """
    Generates a thumbnail for the given filename.
    Returns the thumbnail filename if successful, None otherwise.
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    
    if not os.path.exists(file_path):
        return None
    
    try:
        with Image.open(file_path) as img:
            # Convert to RGB if necessary (e.g., for RGBA or CMYK)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Maintain aspect ratio and crop to square
            width, height = img.size
            if width > height:
                left = (width - height) / 2
                top = 0
                right = (width + height) / 2
                bottom = height
            else:
                left = 0
                top = (height - width) / 2
                right = width
                bottom = (height + width) / 2
            
            img = img.crop((left, top, right, bottom))
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Use .webp extension for better efficiency
            base_filename = filename.rsplit('.', 1)[0]
            thumb_filename = f"thumb_{base_filename}.webp"
            thumb_path = os.path.join(upload_folder, thumb_filename)
            img.save(thumb_path, "WEBP", quality=60)
            
            return thumb_filename

    except Exception as e:
        print(f"Error generating thumbnail for {filename}: {e}")
        return None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def get_system_load():
    """
    Returns the 1-minute load average.
    """
    try:
        return os.getloadavg()[0]
    except AttributeError:
        # Fallback for systems without getloadavg
        return 0.0

def get_image_hash(filename):
    """
    Generates a simple average hash for the image to detect near-duplicates.
    Returns the hex string of the hash.
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    
    if not os.path.exists(file_path):
        return None
        
    try:
        with Image.open(file_path) as img:
            # Resize to small 8x8 and convert to grayscale
            img = img.resize((8, 8), Image.Resampling.LANCZOS).convert('L')
            pixels = list(img.getdata())
            avg = sum(pixels) / 64
            # Bitstring: 1 if pixel > avg, else 0
            bits = "".join(['1' if p > avg else '0' for p in pixels])
            # Convert bits to hex
            return hex(int(bits, 2))[2:]
    except Exception as e:
        print(f"Error hashing image {filename}: {e}")
        return None

def get_image_dimensions(filename):
    """
    Returns (width, height) if successful, None otherwise.
    """
    upload_folder = current_app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)
    
    if not os.path.exists(file_path):
        return None
        
    try:
        with Image.open(file_path) as img:
            return img.size
    except Exception:
        return None

def get_ai_tags(file_path):
    """
    Uses Ollama + Moondream to generate tags for an image.
    Expects an absolute path to the image file.
    """
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Step 1: Get description from Moondream
        response = requests.post('http://localhost:11434/api/generate', json={
            "model": "moondream",
            "prompt": "Describe this image in detail.",
            "images": [encoded_string],
            "stream": False
        }, timeout=300)
        
        if response.status_code != 200:
            return []
            
        description = response.json().get('response', '')
        if not description:
            return []
            
        # Step 2: Extract tags using Gemma
        response = requests.post('http://localhost:11434/api/generate', json={
            "model": "gemma3:1b",
            "prompt": f"Extract 5-10 descriptive, one-word tags from this description: \"{description}\". Reply ONLY with a comma-separated list of tags. No other text.",
            "stream": False
        }, timeout=60)
        
        if response.status_code == 200:
            text = response.json().get('response', '')
            # Clean up and split
            tags = [t.strip().lower() for t in text.split(',') if t.strip()]
            
            # Final sanitize: alphanumeric, reasonable length, no stop words
            stop_words = {'a', 'an', 'the', 'and', 'with', 'stands', 'out', 'against', 'its', 'their', 'this', 'that', 'from', 'into', 'for', 'are', 'was', 'were'}
            final_tags = []
            for t in tags:
                # Remove punctuation from tag
                t = re.sub(r'[^\w\s]', '', t)
                if len(t) > 2 and len(t) < 30 and not any(c.isdigit() for c in t) and t not in stop_words:
                    final_tags.append(t)
            
            return list(dict.fromkeys(final_tags))[:10]
    except Exception as e:
        print(f"Error in two-step AI tagging for {file_path}: {e}")
    
    return []
