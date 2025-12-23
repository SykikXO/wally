# WALLY - Minimalist Wallpaper Library
#### Video Demo:  <URL HERE>
#### Description:

**Wally** is a full-stack web application designed for the modern wallpaper enthusiast. Built with a focus on high aesthetics, extreme minimalism, and powerful AI automation, Wally provides a platform where users can discover, upload, and organize high-resolution wallpapers. The project was born from a desire to combine the simplicity of a classic terminal-inspired aesthetic with the power of modern vision-language models to automate the tedious parts of content management—specifically, tagging and categorization.

### Project Philosophy
The core philosophy of Wally is "Simple Power." On the surface, the user is greeted with a clean, distraction-free environment utilizing a dark color palette, monospace typography (JetBrains Mono/Iosevka), and subtle micro-animations. However, beneath this minimalist shell lies a sophisticated pipeline that handles everything from secure file processing to AI-driven metadata generation. We believe that technology should feel invisible until it’s needed, and Wally achieves this by automating the heavy lifting behind a simple "Upload" button.

### File Breakdown

#### Root Directory
- **`run.py`**: The main entry point for the application. It initializes the Flask app factory and sets up shell context processors for easier debugging in the CLI.
- **`config.py`**: Contains the central configuration logic for the application, including database URIs, secret keys, and folder paths for uploads and quarantine.
- **`app.db`**: The SQLite database containing all user data, wallpaper records, and tag associations.
- **`maintainance.py`**: A standalone daemon script meant to run alongside the web server. It monitors system load and processes files in the quarantine folder, performing AI auto-tagging.
- **`maintainance_render.py`**: A specialized, lightweight version of the maintenance script designed for cloud environments like Render. It skips AI processing to avoid heavy resource dependencies while still handling file movement and thumbnails.
- **`tag_git_wallpapers.py`**: A utility script created to ensure repository consistency. It parses `.gitignore` to identify only the wallpapers tracked by Git and generates AI tags for them, ensuring the live demo matches the local environment.

#### Application Core (`app/`)
- **`__init__.py`**: Houses the `create_app` factory function. It manages extension initialization, blueprint registration, and spawns the background maintenance thread.
- **`models.py`**: Defines the SQLAlchemy database schema. This includes the `User` model, the `Wallpaper` model (with status tracking and slug logic), and the `Tag` model with its associated join table for a many-to-many relationship.
- **`utils.py`**: The "brains" of the image processing. This file contains logic for generating random secure filenames, creating WebP thumbnails, and the integration with **Ollama** (Moondream and Gemma models) for vision-based auto-tagging.
- **`extensions.py`**: A clean way to manage Flask extension instances (SQLAlchemy, Migrate, LoginManager) to avoid circular imports.

#### Routes & Logic (`app/routes/`)
- **`auth.py`**: Manages the user session lifecycle, including registration, login, and logout.
- **`main.py`**: The heart of the app’s functionality. It handles the index feed, search queries, user profile displays, and the complex multipart upload logic that puts files into quarantine.

#### Templates (`app/templates/`)
- **`base.html`**: The foundational layout containing the CSS design system and the "Grid Balance" JavaScript logic.
- **`index.html`** & **`wallpaper.html`**: The primary views for browsing the library and viewing individual wallpapers with full metadata and similar image recommendations.
- **`upload.html`**: A clean, drag-and-drop-ready interface for batch uploading wallpapers.

### Design Choices

#### 1. SQLite Database
I chose SQLite for this project due to its portability, ease of setup, and the fact that I was already familiar with it because of CS50. Since Wally is designed to be a demo-ready masterpiece, having a single-file database ensures that the entire project state can be easily curated, tagged, and pushed to a repository for instant deployment.

#### 2. The Quarantine System
A major design decision was the implementation of a "Quarantine" folder. When a user uploads a file, it is NOT immediately made active. Instead, it is saved with a temporary name in a separate directory. A background thread (or the maintenance daemon) then picks it up to perform security scans (image verification) and heavy AI tagging. This choice serves two purposes: it protects the server from malicious files and ensures that the user's frontend experience is never slowed down by the significant compute requirements of the AI vision models.

#### 3. AI-Driven Tagging (Ollama)
Manual tagging is where most wallpaper sites fail. I chose to integrate **Ollama** running **Moondream** (for vision) and **Gemma** (for natural language processing). Moondream looks at the image and describes it in detail, then Gemma extracts the most relevant 5-10 tags from that description. This creates a highly searchable and organized library with zero effort from the user.

#### 4. User-Centric Views & Performance
I implemented views tracking and similar-image recommendations based on shared tags. To keep performance high, the app uses **WebP conversion** for all thumbnails, significantly reducing page load times while maintaining high visual fidelity. The UI also employs **Intersection Observer** for infinite scrolling, ensuring that the browsing experience feels fluid and modern.

### Conclusion
Wally is more than just a gallery; it’s a demonstration of how AI can be gracefully integrated into a classic web stack to solve real-world content management problems while adhering to a strict, beautiful design aesthetic. 

- **Built by**: Mayank Kushwaha
- **Research and Coding Assists**: Perplexity.ai. Antigravity's Gemini 3 Flash
- **Vision & Edge-AI**: Moondream, Gemma 3 on Ollama
