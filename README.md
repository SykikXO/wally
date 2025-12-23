# Wally

A simple wallpaper library project.

Created by **Mayank Kushwaha**.

Built with some help from:
- **Antigravity** (Agentic AI)
- **Ollama** (Local AI runner)
- **Moondream** (Image descriptions)
- **Gemma** (Tag cleaning)

## Features
- User accounts and uploads.
- Auto-tagging using local AI.
- Minimalist dark UI.
- Background processing for new uploads.

## Setup
1. **Ollama**: (Optional) Run `ollama pull moondream` and `ollama pull gemma:1b`.
2. **Install**: `pip install -r requirements.txt`.
3. **Database**: `flask db upgrade`.
4. **Run**: `python run.py`.

## Maintenance
- `maintainance.py`: Processes uploads and tags them (local).
- `maintainance_render.py`: Simpler version for cloud hosting.
- `tag_git_wallpapers.py`: Tags the wallpapers currently in the repo.
