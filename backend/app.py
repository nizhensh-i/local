import os
import sys
import socket
import ntpath
import urllib.parse
from pathlib import Path
from datetime import datetime

from flask import Flask, jsonify, request, Response, send_file, send_from_directory
from flask_cors import CORS
import mimetypes
from werkzeug.exceptions import RequestedRangeNotSatisfiable

import config
from config import DEFAULT_PAGE_SIZE, PROJECT_ROOT, IS_FROZEN, reload_video_config
from utils import scan_video_files, filter_and_sort_videos, paginate_videos, format_file_size, ScanLimitExceededError

app = Flask(__name__)

# 配置 CORS - 支持本地和局域网访问
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "tauri://localhost",
            "http://localhost:3650",
            "http://127.0.0.1:3650",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            r"^http://tauri\.localhost(:\d+)?$",
            r"^http://localhost(:\d+)?$",
            r"^http://127\.0\.0\.1(:\d+)?$",
            r"^http://192\.168\.\d{1,3}\.\d{1,3}:\d+$",
            r"^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$",
            r"^http://172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}:\d+$"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Range", "Accept"],
        "expose_headers": ["Content-Range", "Accept-Ranges", "Content-Length", "ETag", "Last-Modified"],
        "supports_credentials": True
    }
})

cached_index = None


def _resolve_frontend_dist_dir():
    """Resolve frontend static dist directory for packaged runtime."""
    env_dir = os.getenv('LOCAL_V_FRONTEND_DIST_PATH', '').strip()
    if env_dir:
        candidate = Path(env_dir)
        if (candidate / 'index.html').exists():
            return candidate

    candidates = []
    if IS_FROZEN:
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir / 'web')
        meipass = getattr(sys, '_MEIPASS', None)
        if meipass:
            candidates.append(Path(meipass) / 'web')
            candidates.append(Path(meipass) / 'dist')

    candidates.append(PROJECT_ROOT / 'dist')

    for candidate in candidates:
        if (candidate / 'index.html').exists():
            return candidate
    return None


def _normalize_relative_path(relative_path):
    normalized = str(relative_path or '').replace('\\', '/').strip()
    return normalized.strip('/')


def _public_categories():
    return [
        {
            'id': item['id'],
            'name': item['name'],
            'folder': item['folder'],
            'enabled': item.get('enabled', True) is not False
        }
        for item in config.VIDEO_CATEGORIES
        if item.get('enabled', True) is not False
    ]


def _safe_join(base_folder, relative_path):
    normalized = _normalize_relative_path(relative_path)
    if not normalized or '\x00' in normalized:
        raise ValueError('Invalid relative path')

    drive, _ = ntpath.splitdrive(normalized)
    if drive or normalized.startswith('/'):
        raise ValueError('Invalid relative path')

    full_path = os.path.abspath(os.path.join(base_folder, normalized))
    base_path = os.path.abspath(base_folder)
    try:
        if os.path.commonpath([full_path, base_path]) != base_path:
            raise ValueError('Invalid relative path')
    except ValueError:
        raise ValueError('Invalid relative path')

    return full_path


def _build_video_record(category, file_path, relative_path, video_key=''):
    normalized_relative_path = _normalize_relative_path(relative_path)
    subfolder = str(Path(normalized_relative_path).parent).replace('\\', '/')
    if subfolder == '.':
        subfolder = ''

    stat = os.stat(file_path)
    return {
        'id': f"{category['id']}:{normalized_relative_path}",
        'name': os.path.basename(file_path),
        'size': stat.st_size,
        'size_formatted': format_file_size(stat.st_size),
        'mtime': stat.st_mtime,
        'mtime_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
        'path': file_path,
        'url': f"/api/videos/{os.path.basename(file_path)}",
        'relative_path': normalized_relative_path,
        'subfolder': subfolder,
        'category_id': category['id'],
        'category_name': category['name'],
        'video_key': video_key
    }


def _get_lan_ipv4_addresses():
    """获取本机局域网 IPv4 地址"""
    addresses = set()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        addresses.add(ip)
    except Exception:
        pass
    finally:
        s.close()

    return sorted(addresses)


def get_videos_cache():
    """获取视频缓存索引。"""
    global cached_index
    if cached_index is not None:
        return cached_index

    categories = _public_categories()
    all_videos = []
    by_key = {}
    videos_by_category = {}
    folder_exists_map = {}

    for category in categories:
        folder_exists = os.path.isdir(category['folder'])
        folder_exists_map[category['id']] = folder_exists
        videos = scan_video_files(category['folder'], recursive=True, category=category) if folder_exists else []
        videos_by_category[category['id']] = videos
        all_videos.extend(videos)
        for video in videos:
            by_key[video['video_key']] = video

    cached_index = {
        'videos': all_videos,
        'videos_by_category': videos_by_category,
        'by_key': by_key,
        'folder_exists_map': folder_exists_map
    }
    return cached_index


def _guess_video_mimetype(path):
    """Guess a stable mimetype for direct browser playback."""
    mime_type, _ = mimetypes.guess_type(path)
    if mime_type:
        return mime_type

    ext = os.path.splitext(path)[1].lower()
    mime_types = {
        '.mp4': 'video/mp4',
        '.mov': 'video/quicktime',
        '.mkv': 'video/x-matroska',
        '.webm': 'video/webm',
        '.avi': 'video/x-msvideo',
        '.flv': 'video/x-flv'
    }
    return mime_types.get(ext, 'application/octet-stream')


def _resolve_video_record(filename=None):
    video_key = request.args.get('video_key', '').strip()
    category_id = request.args.get('category_id', '').strip()
    relative_path = request.args.get('relative_path', '').strip()

    cache = get_videos_cache()
    if video_key:
        video = cache['by_key'].get(video_key)
        if video:
            return video
        raise FileNotFoundError('Video not found')

    if category_id and relative_path:
        normalized_relative_path = _normalize_relative_path(relative_path)
        for video in cache['videos_by_category'].get(category_id, []):
            if video['relative_path'] == normalized_relative_path:
                return video

        category = next((item for item in _public_categories() if item['id'] == category_id), None)
        if not category:
            raise FileNotFoundError('Video not found')

        file_path = _safe_join(category['folder'], normalized_relative_path)
        if not os.path.isfile(file_path):
            raise FileNotFoundError('Video not found')

        return _build_video_record(category, file_path, normalized_relative_path, video_key=video_key)

    if filename:
        matches = [video for video in cache['videos'] if video['name'] == filename]
        if len(matches) == 1:
            return matches[0]

    raise FileNotFoundError('Video not found')


def _list_payload(videos, active_category_id, subfolders, pagination):
    cache = get_videos_cache()
    return {
        'videos': videos,
        'folder_exists': cache['folder_exists_map'].get(active_category_id, True),
        'folder_exists_map': cache['folder_exists_map'],
        'categories': _public_categories(),
        'active_category_id': active_category_id,
        'subfolders': subfolders,
        'pagination': pagination
    }


@app.route('/api/videos', methods=['GET'])
def get_videos():
    """获取视频列表接口"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))
        keyword = request.args.get('keyword', '').strip()
        sort_by = request.args.get('sort', 'name')
        category_id = request.args.get('category_id', '').strip()
        subfolder = request.args.get('subfolder', '').strip()

        categories = _public_categories()
        active_category_id = category_id or config.ACTIVE_CATEGORY_ID or (categories[0]['id'] if categories else '')

        cache = get_videos_cache()
        videos = cache['videos_by_category'].get(active_category_id, [])

        normalized_subfolder = _normalize_relative_path(subfolder)
        if normalized_subfolder:
            if normalized_subfolder == 'root':
                videos = [video for video in videos if not video.get('subfolder')]
            else:
                videos = [video for video in videos if video.get('subfolder') == normalized_subfolder]

        filtered_videos = filter_and_sort_videos(videos, keyword, sort_by)
        result = paginate_videos(filtered_videos, page, page_size)

        subfolders = sorted({
            video['subfolder']
            for video in cache['videos_by_category'].get(active_category_id, [])
            if video.get('subfolder')
        })

        return jsonify({
            'success': True,
            'data': _list_payload(
                result['videos'],
                active_category_id,
                subfolders,
                {
                    'total': result['total'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'total_pages': result['total_pages']
                }
            )
        })

    except ScanLimitExceededError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 422
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def send_file_partial(path, filename):
    """使用 Flask/Werkzeug 内建条件响应处理本地视频 Range 请求。"""
    try:
        file_size = os.path.getsize(path)
        mime_type = _guess_video_mimetype(path)
        safe_filename = urllib.parse.quote(filename, safe='')
        response = send_file(
            path,
            mimetype=mime_type,
            as_attachment=False,
            conditional=True,
            etag=True,
            last_modified=os.path.getmtime(path),
            max_age=0
        )
        response.headers['Accept-Ranges'] = 'bytes'
        response.headers['Content-Disposition'] = f'inline; filename*=UTF-8\'\'{safe_filename}'
        response.headers['Cache-Control'] = 'no-cache'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    except RequestedRangeNotSatisfiable:
        headers = {
            'Content-Type': mime_type,
            'Content-Range': f'bytes */{file_size}',
            'Accept-Ranges': 'bytes'
        }
        return Response(status=416, headers=headers)
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': '视频文件不存在'
        }), 404
    except PermissionError:
        return jsonify({
            'success': False,
            'error': '没有权限访问视频文件'
        }), 403
    except Exception as e:
        print(f'视频流错误: {str(e)}')
        return jsonify({
            'success': False,
            'error': f'视频流错误: {str(e)}'
        }), 500


@app.route('/api/videos/<filename>', methods=['GET', 'HEAD'])
def stream_video(filename):
    """视频流式传输接口"""
    try:
        video = _resolve_video_record(filename)
        return send_file_partial(video['path'], video['name'])
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid filename'
        }), 400
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Video not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos/<filename>/meta', methods=['GET'])
def get_video_meta(filename):
    """获取单个视频元信息（用于详情页精确查询）"""
    try:
        video = _resolve_video_record(filename)
        return jsonify({
            'success': True,
            'data': video
        })
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid filename'
        }), 400
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Video not found'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos/<filename>/poster', methods=['GET'])
def get_video_poster(filename):
    """不生成视频封面，统一回退到前端占位图"""
    try:
        _resolve_video_record(filename)
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid filename'
        }), 400
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': 'Video not found'
        }), 404

    return jsonify({
        'success': False,
        'poster': None,
        'error': 'Poster not available'
    }), 404


@app.route('/api/network-info', methods=['GET'])
def get_network_info():
    """返回前端局域网访问地址建议"""
    frontend_port = request.args.get('frontend_port', '').strip()
    if IS_FROZEN:
        frontend_port = '56173'
    elif not frontend_port.isdigit():
        frontend_port = '3650'

    addresses = _get_lan_ipv4_addresses()
    frontend_urls = [f'http://{ip}:{frontend_port}' for ip in addresses]

    return jsonify({
        'success': True,
        'data': {
            'ips': addresses,
            'frontend_port': frontend_port,
            'frontend_urls': frontend_urls
        }
    })


@app.route('/api/categories', methods=['GET'])
def get_categories():
    cache = get_videos_cache()
    return jsonify({
        'success': True,
        'data': {
            'categories': _public_categories(),
            'active_category_id': config.ACTIVE_CATEGORY_ID,
            'folder_exists_map': cache['folder_exists_map']
        }
    })


@app.route('/api/refresh', methods=['POST'])
def refresh_videos():
    """刷新视频列表缓存"""
    global cached_index

    try:
        print("=" * 60)
        print("Refreshing video cache...")
        old_active_category = config.ACTIVE_CATEGORY_ID
        print(f"Config path: {config.get_config_path()}")

        new_config = reload_video_config()
        print(f"[OK] Reloaded {len(new_config['categories'])} categories")

        cached_index = None
        index = get_videos_cache()
        video_count = len(index['videos'])
        print(f"[OK] Found {video_count} videos across all categories")
        print("=" * 60)

        return jsonify({
            'success': True,
            'message': f'Video cache refreshed, found {video_count} videos',
            'active_category_id': config.ACTIVE_CATEGORY_ID,
            'old_active_category_id': old_active_category,
            'video_count': video_count,
            'categories': _public_categories()
        })
    except ScanLimitExceededError as e:
        print(f"[ERR] Failed to refresh video cache: {e}")
        cached_index = None
        return jsonify({
            'success': False,
            'error': str(e)
        }), 422
    except Exception as e:
        print(f"[ERR] Failed to refresh video cache: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    config_path = config.get_config_path()
    cached_video_count = len(cached_index['videos']) if cached_index else None
    return jsonify({
        'success': True,
        'message': 'Server is running',
        'video_folder': config.VIDEO_FOLDER,
        'folder_exists': os.path.exists(config.VIDEO_FOLDER) and os.path.isdir(config.VIDEO_FOLDER),
        'config_path': config_path,
        'config_exists': config_path and os.path.exists(config_path),
        'runtime_root': str(PROJECT_ROOT),
        'is_frozen': IS_FROZEN,
        'video_count': cached_video_count,
        'categories': _public_categories(),
        'active_category_id': config.ACTIVE_CATEGORY_ID
    })


@app.route('/api/videos/<filename>/check', methods=['GET'])
def check_video(filename):
    """检查视频文件信息"""
    try:
        video = _resolve_video_record(filename)
        file_path = video['path']

        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '视频文件不存在'
            }), 404

        file_size = os.path.getsize(file_path)
        ext = os.path.splitext(filename)[1].lower()

        result = {
            'exists': True,
            'size': file_size,
            'size_formatted': format_file_size(file_size),
            'extension': ext,
            'can_read': False,
            'is_large_file': file_size > 2 * 1024 * 1024 * 1024,
            'issues': []
        }

        try:
            with open(file_path, 'rb') as f:
                header = f.read(32)
                result['can_read'] = len(header) > 0
                if not result['can_read']:
                    result['issues'].append('文件为空或无法读取')
        except Exception as e:
            result['issues'].append(f'文件读取错误: {str(e)}')

        supported_extensions = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv'}
        if ext not in supported_extensions:
            result['issues'].append(f'文件扩展名 {ext} 可能不被支持')

        if result['is_large_file']:
            result['issues'].append(f'文件较大 ({result["size_formatted"]})，可能需要更长的加载时间')

        result['encoding_tips'] = [
            '确保视频使用 H.264 (AVC) 视频编码',
            '音频编码建议使用 AAC',
            '如果无法播放，可以尝试使用 ffmpeg 转换:',
            f'ffmpeg -i "{filename}" -c:v libx264 -preset medium -crf 23 -c:a aac output.mp4'
        ]

        return jsonify({
            'success': True,
            'data': result
        })
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid filename'
        }), 400
    except FileNotFoundError:
        return jsonify({
            'success': False,
            'error': '视频文件不存在'
        }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'检查视频时出错: {str(e)}'
        }), 500


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Packaged mode: serve built frontend files for LAN devices."""
    if path.startswith('api/'):
        return jsonify({
            'success': False,
            'error': 'Not found'
        }), 404

    dist_dir = _resolve_frontend_dist_dir()
    if not dist_dir:
        return jsonify({
            'success': False,
            'error': 'Frontend dist not found'
        }), 404

    requested_file = dist_dir / path if path else None
    if requested_file and requested_file.exists() and requested_file.is_file():
        return send_from_directory(str(dist_dir), path)

    return send_file(dist_dir / 'index.html')


if __name__ == '__main__':
    print(f"=" * 60)
    print(f"Starting Flask server...")
    print(f"Video folder: {config.VIDEO_FOLDER}")
    print(f"IS_FROZEN: {IS_FROZEN}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")

    video_folder = Path(config.VIDEO_FOLDER)
    if not video_folder.exists():
        video_folder.mkdir(parents=True, exist_ok=True)
        print(f"Created video folder: {config.VIDEO_FOLDER}")

    try:
        video_count = len(get_videos_cache()['videos'])
        print(f"Videos found: {video_count}")
    except Exception as e:
        print(f"Error scanning videos: {e}")
        video_count = 0

    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'
    default_host = '0.0.0.0'
    host = os.getenv('LOCAL_V_HOST', default_host)

    print(f"Listening on: {host}:56173")
    print(f"Debug mode: {debug_mode}")
    print(f"=" * 60)

    app.run(host=host, port=56173, debug=debug_mode, threaded=True)
