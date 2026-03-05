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
        print(f"LOCAL_V_CONFIG_PATH environment variable not set")
        return None
    
    if not os.path.exists(config_path):
        print(f"Config file not found at: {config_path}")
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        folder = data.get('video_folder')
        if folder:
            print(f"Found video_folder in config: '{folder}'")
            # Check if folder exists and is a directory
            folder_path = Path(folder)
            if folder_path.exists() and folder_path.is_dir():
                print(f"Loaded video folder from config: '{folder}'")
                return folder
            else:
                print(f"Configured folder does not exist or is not a directory: '{folder}'")
                print(f"  - Path exists: {folder_path.exists()}")
                print(f"  - Is directory: {folder_path.is_dir()}")
        else:
            print(f"No video_folder key in config: {config_path}")
    except json.JSONDecodeError as e:
        print(f"JSON decode error in {config_path}: {e}")
        print(f"  File content might be corrupted")
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

    return None


def get_config_path():
    """Get the full path to the config file
    
    Priority:
    1. Use LOCAL_V_CONFIG_PATH env variable if set
    2. Fallback to OS-specific AppData path
    """
    config_path = os.getenv('LOCAL_V_CONFIG_PATH')
    
    # If env variable is set, return it (whether file exists or not)
    if config_path:
        print(f"Using config path from env: {config_path}")
        return config_path
    
    # Fallback: construct the path based on OS
    import platform
    system = platform.system()
    
    if system == 'Windows':
        app_data = os.getenv('APPDATA')
    elif system == 'Darwin':  # macOS
        app_data = os.path.expanduser('~/Library/Application Support')
    else:  # Linux
        app_data = os.getenv('XDG_CONFIG_HOME') or os.path.expanduser('~/.config')
    
    if app_data:
        fallback_path = os.path.join(app_data, 'com.tauri.local', 'video_folder.json')
        print(f"Using fallback config path: {fallback_path}")
        return fallback_path
    
    print("Could not determine config path")
    return None


# 视频文件夹路径（默认路径）
# VIDEO_FOLDER_DEFAULT = get_default_video_folder()
VIDEO_FOLDER_DEFAULT = '/Users/v/Downloads'

def reload_video_folder():
    """Reload video folder configuration"""
    global VIDEO_FOLDER
    configured = _load_video_folder_from_config()
    
    if configured:
        VIDEO_FOLDER = configured
        print(f"Using configured video folder: {VIDEO_FOLDER}")
    else:
        VIDEO_FOLDER = VIDEO_FOLDER_DEFAULT
        print(f"Using default video folder: {VIDEO_FOLDER}")

    # Ensure the video folder exists
    folder_path = Path(VIDEO_FOLDER)
    if not folder_path.exists():
        print(f"Warning: Video folder does not exist: {VIDEO_FOLDER}")
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            print(f"Created video folder: {VIDEO_FOLDER}")
        except Exception as e:
            print(f"Failed to create video folder: {e}")
    elif not folder_path.is_dir():
        print(f"Warning: Video folder path is not a directory: {VIDEO_FOLDER}")

    return VIDEO_FOLDER


VIDEO_FOLDER = reload_video_folder()

# 支持的视频格式
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv'}

# 默认分页大小
DEFAULT_PAGE_SIZE = 12
