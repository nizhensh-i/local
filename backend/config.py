import json
import os
import sys
import platform
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent
IS_FROZEN = bool(getattr(sys, 'frozen', False))
PROJECT_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else SOURCE_ROOT

def get_default_video_folder():
    """Get default video folder based on platform"""
    system = platform.system()
    if system == 'Windows':
        # Windows: Use Downloads or Videos folder
        downloads = Path.home() / 'Downloads'
        videos = Path.home() / 'Videos'
        if downloads.exists():
            return str(downloads)
        elif videos.exists():
            return str(videos)
        else:
            return str(downloads)
    elif system == 'Darwin':  # macOS
        videos = Path.home() / 'Movies'
        downloads = Path.home() / 'Downloads'
        if videos.exists():
            return str(videos)
        elif downloads.exists():
            return str(downloads)
        else:
            return str(videos)
    else:  # Linux
        videos = Path.home() / 'Videos'
        downloads = Path.home() / 'Downloads'
        if videos.exists():
            return str(videos)
        elif downloads.exists():
            return str(downloads)
        else:
            return str(videos)

def _load_video_folder_from_config():
    """Load video folder configuration from JSON file"""
    config_path = os.getenv('LOCAL_V_CONFIG_PATH')
    if not config_path:
        return None
    
    if not os.path.exists(config_path):
        print(f"Config file not found at: {config_path}")
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        folder = data.get('video_folder')
        if folder:
            if os.path.isdir(folder):
                print(f"Loaded video folder from config: {folder}")
                return folder
            else:
                print(f"Configured folder does not exist: {folder}")
        else:
            print(f"No video_folder key in config: {config_path}")
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return None

    return None


# 视频文件夹路径（默认路径）
VIDEO_FOLDER_DEFAULT = get_default_video_folder()

def reload_video_folder():
    """Reload video folder configuration"""
    global VIDEO_FOLDER
    configured = _load_video_folder_from_config()
    
    if configured:
        VIDEO_FOLDER = configured
    else:
        VIDEO_FOLDER = VIDEO_FOLDER_DEFAULT
        print(f"Using default video folder: {VIDEO_FOLDER}")

    # PyInstaller 场景兜底：如果目录不存在，尝试 exe 同目录下 public
    if IS_FROZEN and not os.path.exists(VIDEO_FOLDER):
        runtime_public = Path(sys.executable).resolve().parent / 'public'
        if runtime_public.exists():
            VIDEO_FOLDER = str(runtime_public)
            print(f"Using fallback video folder: {VIDEO_FOLDER}")
        else:
            print(f"Warning: Video folder does not exist: {VIDEO_FOLDER}")
            # Create it if it doesn't exist
            try:
                os.makedirs(VIDEO_FOLDER, exist_ok=True)
                print(f"Created video folder: {VIDEO_FOLDER}")
            except Exception as e:
                print(f"Failed to create video folder: {e}")

    return VIDEO_FOLDER


VIDEO_FOLDER = reload_video_folder()

# 支持的视频格式
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv'}

# 默认分页大小
DEFAULT_PAGE_SIZE = 12
