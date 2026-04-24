import json
import os
import sys
import platform
import hashlib
from datetime import datetime
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
        downloads = Path.home() / 'Downloads'
        videos = Path.home() / 'Movies'
        if downloads.exists():
            return str(downloads)
        elif videos.exists():
            return str(videos)
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

def _stable_category_id(name, folder):
    base = f"{name or ''}:{folder or ''}"
    return f"cat_{hashlib.md5(base.encode('utf-8')).hexdigest()[:10]}"


def _normalize_categories(data):
    categories = []
    seen_ids = set()
    raw_categories = data.get('categories') if isinstance(data, dict) else None

    if isinstance(raw_categories, list):
        for item in raw_categories:
            if not isinstance(item, dict):
                continue
            folder = str(item.get('folder') or item.get('path') or '').strip()
            if not folder:
                continue

            name = str(item.get('name') or '').strip() or Path(folder).name or '未命名分类'
            category_id = str(item.get('id') or '').strip() or _stable_category_id(name, folder)
            enabled = item.get('enabled', True) is not False

            if category_id in seen_ids:
                category_id = _stable_category_id(f"{name}-{len(categories)}", folder)

            seen_ids.add(category_id)
            categories.append({
                'id': category_id,
                'name': name,
                'folder': folder,
                'enabled': enabled
            })

    if not categories and isinstance(data, dict):
        folder = str(data.get('video_folder') or '').strip()
        if folder:
            categories.append({
                'id': _stable_category_id('默认分类', folder),
                'name': '默认分类',
                'folder': folder,
                'enabled': True
            })

    active_category_id = str(data.get('active_category_id') or '').strip() if isinstance(data, dict) else ''
    enabled_categories = [item for item in categories if item['enabled']]
    valid_active = next((item['id'] for item in enabled_categories if item['id'] == active_category_id), '')
    if not valid_active and enabled_categories:
        valid_active = enabled_categories[0]['id']

    return {
        'categories': categories,
        'active_category_id': valid_active
    }


def _load_video_folder_from_config():
    """Load category configuration from JSON file."""
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
        normalized = _normalize_categories(data)
        print(f"Loaded {len(normalized['categories'])} categories from config")
        return normalized
    except json.JSONDecodeError as e:
        print(f"JSON decode error in {config_path}: {e}")
        print(f"  File content might be corrupted")
        _backup_broken_config_file(config_path)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        import traceback
        traceback.print_exc()
        return None

    return None


def _backup_broken_config_file(config_path):
    """Backup a broken JSON config so startup can recover cleanly next time."""
    try:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        broken_path = f"{config_path}.broken.{timestamp}"
        os.replace(config_path, broken_path)
        print(f"Backed up broken config to: {broken_path}")
    except Exception as error:
        print(f"Failed to backup broken config {config_path}: {error}")


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


VIDEO_FOLDER_DEFAULT = get_default_video_folder()


def _build_default_config():
    default_folder = VIDEO_FOLDER_DEFAULT
    category = {
        'id': _stable_category_id('默认分类', default_folder),
        'name': '默认分类',
        'folder': default_folder,
        'enabled': True
    }
    return {
        'categories': [category],
        'active_category_id': category['id']
    }


def reload_video_config():
    """Reload category configuration and validate folders."""
    global VIDEO_CONFIG, VIDEO_FOLDER, VIDEO_CATEGORIES, ACTIVE_CATEGORY_ID

    configured = _load_video_folder_from_config()
    VIDEO_CONFIG = configured if configured is not None else _build_default_config()

    valid_categories = []
    for item in VIDEO_CONFIG['categories']:
        folder = item['folder']
        folder_path = Path(folder)
        if not folder_path.exists():
            print(f"Warning: category folder does not exist: {folder}")
            try:
                folder_path.mkdir(parents=True, exist_ok=True)
                print(f"Created category folder: {folder}")
            except Exception as e:
                print(f"Failed to create category folder {folder}: {e}")
        elif not folder_path.is_dir():
            print(f"Warning: category folder path is not a directory: {folder}")

        valid_categories.append({
            'id': item['id'],
            'name': item['name'],
            'folder': folder,
            'enabled': item.get('enabled', True) is not False
        })

    VIDEO_CATEGORIES = valid_categories
    ACTIVE_CATEGORY_ID = VIDEO_CONFIG.get('active_category_id') or (
        VIDEO_CATEGORIES[0]['id'] if VIDEO_CATEGORIES else ''
    )
    VIDEO_FOLDER = next(
        (item['folder'] for item in VIDEO_CATEGORIES if item['id'] == ACTIVE_CATEGORY_ID),
        VIDEO_FOLDER_DEFAULT
    )

    print(f"Loaded {len(VIDEO_CATEGORIES)} categories, active={ACTIVE_CATEGORY_ID or 'none'}")
    return {
        'categories': VIDEO_CATEGORIES,
        'active_category_id': ACTIVE_CATEGORY_ID
    }


def reload_video_folder():
    """Backward-compatible wrapper for legacy callers."""
    reload_video_config()
    return VIDEO_FOLDER


VIDEO_CONFIG = {}
VIDEO_CATEGORIES = []
ACTIVE_CATEGORY_ID = ''
VIDEO_FOLDER = VIDEO_FOLDER_DEFAULT
reload_video_config()

# 支持的视频格式
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv'}

# 默认分页大小
DEFAULT_PAGE_SIZE = 12
