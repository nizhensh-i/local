import os
from pathlib import Path

# 视频文件夹路径 - 请根据需要修改
VIDEO_FOLDER = os.getenv('VIDEO_FOLDER', '/Users/nizhenshi/Documents/proj/local_v/public')

# 支持的视频格式
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.mkv', '.webm'}

# 默认分页大小
DEFAULT_PAGE_SIZE = 12

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
