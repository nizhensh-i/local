import os
import uuid
from pathlib import Path
from datetime import datetime
from config import VIDEO_EXTENSIONS


def generate_video_id():
    """生成视频唯一ID"""
    return str(uuid.uuid4())


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


def scan_video_files(video_folder):
    """扫描视频文件夹，返回视频文件列表"""
    if not os.path.exists(video_folder):
        return []
    
    videos = []
    video_path = Path(video_folder)
    
    for file_path in video_path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in VIDEO_EXTENSIONS:
            stat = file_path.stat()
            videos.append({
                'id': generate_video_id(),
                'name': file_path.name,
                'size': stat.st_size,
                'size_formatted': format_file_size(stat.st_size),
                'mtime': stat.st_mtime,
                'mtime_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'path': str(file_path),
                'url': f"/api/videos/{file_path.name}"
            })
    
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
