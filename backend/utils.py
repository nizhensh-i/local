import os
import hashlib
import time
from pathlib import Path
from datetime import datetime
from config import VIDEO_EXTENSIONS


class ScanTimeoutError(RuntimeError):
    """Raised when directory scanning exceeds the safety timeout."""


def generate_video_id(relative_path):
    """基于相对路径生成稳定ID，避免每次扫描变化"""
    digest = hashlib.md5(relative_path.encode('utf-8')).hexdigest()
    return digest


def format_file_size(size_bytes):
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = size_bytes
    
    while size >= 1024 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def generate_video_key(category_id, relative_path):
    normalized_path = str(Path(relative_path)).replace('\\', '/')
    digest = hashlib.md5(f"{category_id}:{normalized_path}".encode('utf-8')).hexdigest()
    return digest


def scan_video_files(video_folder, recursive=True, category=None, max_duration_sec=30):
    """扫描视频文件夹，返回视频文件列表
    
    Args:
        video_folder: 视频文件夹路径
        recursive: 是否递归扫描子文件夹
    
    Returns:
        视频文件列表
    """
    if not os.path.exists(video_folder):
        print(f"Video folder does not exist: {video_folder}")
        return []
    
    if not os.path.isdir(video_folder):
        print(f"Path is not a directory: {video_folder}")
        return []
    
    videos = []
    video_path = Path(video_folder)
    started_at = time.monotonic()
    
    # 使用递归或非递归扫描
    if recursive:
        # 递归扫描所有子文件夹
        file_pattern = "**/*"
    else:
        # 只扫描当前文件夹
        file_pattern = "*"
    
    for file_path in video_path.glob(file_pattern):
        if time.monotonic() - started_at > max_duration_sec:
            raise ScanTimeoutError(f"扫描超时（超过 {max_duration_sec} 秒），请缩小目录范围后重试")
        if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
            stat = file_path.stat()
            relative_path = str(file_path.relative_to(video_path)).replace('\\', '/')
            subfolder = str(Path(relative_path).parent).replace('\\', '/')
            if subfolder == '.':
                subfolder = ''
            category_id = category.get('id') if isinstance(category, dict) else ''
            category_name = category.get('name') if isinstance(category, dict) else ''
            video_key = generate_video_key(category_id or 'default', relative_path)
            videos.append({
                'id': generate_video_id(f"{category_id}:{relative_path}"),
                'name': file_path.name,
                'size': stat.st_size,
                'size_formatted': format_file_size(stat.st_size),
                'mtime': stat.st_mtime,
                'mtime_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'path': str(file_path),
                'url': f"/api/videos/{file_path.name}",
                'relative_path': relative_path,
                'subfolder': subfolder,
                'category_id': category_id,
                'category_name': category_name,
                'video_key': video_key
            })
    
    print(f"Scanned {len(videos)} videos from {video_folder}")
    return videos


def filter_and_sort_videos(videos, keyword=None, sort_by='name'):
    """过滤和排序视频列表"""
    result = videos.copy()
    
    # 搜索过滤
    if keyword:
        keyword = keyword.lower()
        result = [v for v in result if keyword in v['name'].lower()]
    
    # 排序
    if sort_by == 'name':
        result.sort(key=lambda x: x['name'].lower())
    elif sort_by == 'size':
        result.sort(key=lambda x: x['size'], reverse=True)
    elif sort_by == 'mtime':
        result.sort(key=lambda x: x['mtime'], reverse=True)
    
    return result


def paginate_videos(videos, page=1, page_size=12):
    """分页处理"""
    total = len(videos)
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        'videos': videos[start:end],
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': (total + page_size - 1) // page_size
    }
