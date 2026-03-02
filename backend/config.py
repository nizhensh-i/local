import os
import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent
IS_FROZEN = bool(getattr(sys, 'frozen', False))
PROJECT_ROOT = Path(sys.executable).resolve().parent if IS_FROZEN else SOURCE_ROOT

# 视频文件夹路径（固定在代码中）
VIDEO_FOLDER = '/Users/nizhenshi/Documents/proj/local_v/public'

# PyInstaller 场景兜底：如果固定目录不存在，尝试 exe 同目录下 public
if IS_FROZEN and not os.path.exists(VIDEO_FOLDER):
    runtime_public = Path(sys.executable).resolve().parent / 'public'
    VIDEO_FOLDER = str(runtime_public)

# 支持的视频格式
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.webm'}

# 默认分页大小
DEFAULT_PAGE_SIZE = 12
