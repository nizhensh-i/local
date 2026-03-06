import os
import sys
import json
import socket
import ntpath
from pathlib import Path
from flask import Flask, jsonify, request, Response, send_file, send_from_directory
from flask_cors import CORS
import mimetypes
import config
from config import VIDEO_FOLDER, DEFAULT_PAGE_SIZE, PROJECT_ROOT, IS_FROZEN, reload_video_folder
from datetime import datetime
from utils import scan_video_files, filter_and_sort_videos, paginate_videos, format_file_size, generate_video_id

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
            # 放行常见内网地址: 192.168.x.x / 10.x.x.x / 172.16-31.x.x
            r"^http://192\.168\.\d{1,3}\.\d{1,3}:\d+$",
            r"^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$",
            r"^http://172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}:\d+$"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Range", "Accept"],
        "expose_headers": ["Content-Range", "Accept-Ranges", "Content-Length"],
        "supports_credentials": True
    }
})

# 缓存视频列表，避免重复扫描
cached_videos = None


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


def _safe_video_file_path(filename):
    """构建并校验视频文件路径，防止绝对路径和目录穿越"""
    if not filename or '\x00' in filename:
        raise ValueError('Invalid filename')

    if filename.startswith(('/', '\\\\', '//')):
        raise ValueError('Invalid filename')

    drive, _ = ntpath.splitdrive(filename)
    if drive:
        raise ValueError('Invalid filename')

    full_path = os.path.abspath(os.path.join(VIDEO_FOLDER, filename))
    base_path = os.path.abspath(VIDEO_FOLDER)

    try:
        if os.path.commonpath([full_path, base_path]) != base_path:
            raise ValueError('Invalid filename')
    except ValueError:
        raise ValueError('Invalid filename')

    return full_path


def _get_lan_ipv4_addresses():
    """获取本机局域网 IPv4 地址"""
    addresses = set()
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # 连接到一个外部地址（不需要实际连通）
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        addresses.add(ip)
    except Exception:
        pass
    finally:
        s.close()

    return sorted(addresses)


def get_videos_cache():
    """获取视频列表缓存"""
    global cached_videos
    if cached_videos is None:
        cached_videos = scan_video_files(VIDEO_FOLDER)
    return cached_videos


@app.route('/api/videos', methods=['GET'])
def get_videos():
    """获取视频列表接口"""
    try:
        folder_exists = os.path.isdir(VIDEO_FOLDER)

        if not folder_exists:
            return jsonify({
                'success': True,
                'data': {
                    'videos': [],
                    'folder_exists': False,
                    'video_folder': VIDEO_FOLDER,
                    'pagination': {
                        'total': 0,
                        'page': 1,
                        'page_size': DEFAULT_PAGE_SIZE,
                        'total_pages': 1
                    }
                }
            })

        # 获取查询参数
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))
        keyword = request.args.get('keyword', '').strip()
        sort_by = request.args.get('sort', 'name')
        
        # 获取视频列表
        videos = get_videos_cache()
        
        # 过滤和排序
        filtered_videos = filter_and_sort_videos(videos, keyword, sort_by)
        
        # 分页
        result = paginate_videos(filtered_videos, page, page_size)
        
        return jsonify({
            'success': True,
            'data': {
                'videos': result['videos'],
                'folder_exists': True,
                'video_folder': VIDEO_FOLDER,
                'pagination': {
                    'total': result['total'],
                    'page': result['page'],
                    'page_size': result['page_size'],
                    'total_pages': result['total_pages']
                }
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def send_file_partial(path, filename):
    """支持 Range 请求的文件发送 - 优化大文件支持"""
    try:
        file_size = os.path.getsize(path)
        range_header = request.headers.get('Range', None)
        
        # 获取 MIME 类型
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type:
            # 根据文件扩展名确定 MIME 类型
            ext = os.path.splitext(path)[1].lower()
            mime_types = {
                '.mp4': 'video/mp4',
                '.mov': 'video/quicktime',
                '.mkv': 'video/x-matroska',
                '.webm': 'video/webm',
                '.avi': 'video/x-msvideo',
                '.flv': 'video/x-flv'
            }
            mime_type = mime_types.get(ext, 'video/mp4')
        
        # 对文件名进行URL编码，避免中文等非ASCII字符导致的编码问题
        import urllib.parse
        safe_filename = urllib.parse.quote(filename, safe='')
        
        if range_header:
            # 解析 Range 请求，处理各种格式
            try:
                byte_ranges = range_header.strip().split('=')[-1]
                range_parts = byte_ranges.split('-')
                
                start_str, end_str = range_parts[0], range_parts[1] if len(range_parts) > 1 else ''
                
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                
                # 确保范围有效
                start = max(0, start)
                end = min(file_size - 1, end)
                
                # 确保 start <= end
                if start > end:
                    start = end
                
                content_length = end - start + 1
                
                # 读取指定范围的数据
                def generate():
                    with open(path, 'rb') as f:
                        f.seek(start)
                        bytes_read = 0
                        chunk_size = 8192  # 8KB chunks
                        while bytes_read < content_length:
                            bytes_to_read = min(chunk_size, content_length - bytes_read)
                            data = f.read(bytes_to_read)
                            if not data:
                                break
                            bytes_read += len(data)
                            yield data
                
                # 构建响应
                headers = {
                    'Content-Type': mime_type,
                    'Content-Length': str(content_length),
                    'Content-Range': f'bytes {start}-{end}/{file_size}',
                    'Accept-Ranges': 'bytes',
                    'Content-Disposition': f'inline; filename*=UTF-8\'\'{safe_filename}',
                    'Cache-Control': 'no-cache, no-store, must-revalidate',
                    'Pragma': 'no-cache',
                    'Expires': '0'
                }
                
                return Response(
                    generate(),
                    status=206,
                    headers=headers,
                    direct_passthrough=True
                )
            
            except Exception as e:
                # Range 解析失败，返回 416 Requested Range Not Satisfiable
                headers = {
                    'Content-Type': mime_type,
                    'Content-Range': f'bytes */{file_size}',
                    'Accept-Ranges': 'bytes'
                }
                return Response(status=416, headers=headers)
        
        else:
            # 普通请求，返回整个文件（使用流式传输）
            def generate():
                with open(path, 'rb') as f:
                    chunk = f.read(8192)
                    while chunk:
                        yield chunk
                        chunk = f.read(8192)
            
            headers = {
                'Content-Type': mime_type,
                'Content-Length': str(file_size),
                'Accept-Ranges': 'bytes',
                'Content-Disposition': f'inline; filename*=UTF-8\'\'{safe_filename}',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            return Response(
                generate(),
                status=200,
                headers=headers,
                direct_passthrough=True
            )
    
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


@app.route('/api/videos/<filename>', methods=['GET'])
def stream_video(filename):
    """视频流式传输接口"""
    try:
        # 构建并校验文件路径
        file_path = _safe_video_file_path(filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Video not found'
            }), 404
        
        if not os.path.isfile(file_path):
            return jsonify({
                'success': False,
                'error': 'Invalid video file'
            }), 400
        
        return send_file_partial(file_path, filename)
    
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid filename'
        }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos/<filename>/meta', methods=['GET'])
def get_video_meta(filename):
    """获取单个视频元信息（用于详情页精确查询）"""
    try:
        file_path = _safe_video_file_path(filename)
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': 'Video not found'
            }), 404

        if not os.path.isfile(file_path):
            return jsonify({
                'success': False,
                'error': 'Invalid video file'
            }), 400

        relative_path = os.path.relpath(file_path, VIDEO_FOLDER)
        stat = os.stat(file_path)
        data = {
            'id': generate_video_id(relative_path),
            'name': filename,
            'size': stat.st_size,
            'size_formatted': format_file_size(stat.st_size),
            'mtime': stat.st_mtime,
            'mtime_formatted': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'path': file_path,
            'url': f"/api/videos/{filename}",
            'relative_path': relative_path
        }

        return jsonify({
            'success': True,
            'data': data
        })
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid filename'
        }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/videos/<filename>/poster', methods=['GET'])
def get_video_poster(filename):
    """不生成视频封面，统一回退到前端占位图"""
    try:
        _safe_video_file_path(filename)
    except ValueError:
        return jsonify({
            'success': False,
            'error': 'Invalid filename'
        }), 400

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


@app.route('/api/refresh', methods=['POST'])
def refresh_videos():
    """刷新视频列表缓存"""
    global cached_videos, VIDEO_FOLDER

    try:
        print("=" * 60)
        print("Refreshing video cache...")
        old_folder = VIDEO_FOLDER

        # Try to read config file directly
        config_path = config.get_config_path()
        print(f"Config path: {config_path}")

        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    new_folder = data.get('video_folder')
                    print(f"Config video_folder: {new_folder}")

                    if new_folder and os.path.isdir(new_folder) and new_folder != old_folder:
                        VIDEO_FOLDER = new_folder
                        print(f"[OK] Updated VIDEO_FOLDER: {old_folder} -> {VIDEO_FOLDER}")
                    elif new_folder == old_folder:
                        print(f"[OK] VIDEO_FOLDER unchanged: {VIDEO_FOLDER}")
                    elif new_folder and not os.path.isdir(new_folder):
                        print(f"[WARN] Invalid folder path (not exists or not a directory): {new_folder}")
                        print(f"[OK] Keep current VIDEO_FOLDER: {VIDEO_FOLDER}")
                    else:
                        print(f"[WARN] Invalid config, keeping: {VIDEO_FOLDER}")
            except Exception as e:
                print(f"[ERR] Error reading config: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[WARN] Config file not found: {config_path}")

        # Keep old folder if current folder becomes invalid for any reason
        if not os.path.isdir(VIDEO_FOLDER):
            print(f"[WARN] Current VIDEO_FOLDER is invalid: {VIDEO_FOLDER}")
            if os.path.isdir(old_folder):
                VIDEO_FOLDER = old_folder
                print(f"[OK] Reverted VIDEO_FOLDER to previous valid folder: {VIDEO_FOLDER}")
            else:
                # Fallback to config default loader without changing API behavior
                VIDEO_FOLDER = reload_video_folder()
                print(f"[OK] Reloaded VIDEO_FOLDER from config/default: {VIDEO_FOLDER}")

        # Clear cache and rescan
        print(f"Scanning videos from: {VIDEO_FOLDER}")
        cached_videos = None
        video_count = len(get_videos_cache())
        print(f"[OK] Found {video_count} videos")
        print("=" * 60)

        return jsonify({
            'success': True,
            'message': f'Video cache refreshed, found {video_count} videos',
            'video_folder': VIDEO_FOLDER,
            'old_folder': old_folder,
            'video_count': video_count
        })
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
    cached_video_count = len(cached_videos) if cached_videos else None
    return jsonify({
        'success': True,
        'message': 'Server is running',
        'video_folder': VIDEO_FOLDER,
        'folder_exists': os.path.exists(VIDEO_FOLDER) and os.path.isdir(VIDEO_FOLDER),
        'config_path': config_path,
        'config_exists': config_path and os.path.exists(config_path),
        'runtime_root': str(PROJECT_ROOT),
        'is_frozen': IS_FROZEN,
        'video_count': cached_video_count
    })


@app.route('/api/videos/<filename>/check', methods=['GET'])
def check_video(filename):
    """检查视频文件信息"""
    try:
        file_path = _safe_video_file_path(filename)
        
        if not os.path.exists(file_path):
            return jsonify({
                'success': False,
                'error': '视频文件不存在'
            }), 404
        
        file_size = os.path.getsize(file_path)
        ext = os.path.splitext(filename)[1].lower()
        
        # 基本检查
        result = {
            'exists': True,
            'size': file_size,
            'size_formatted': format_file_size(file_size),
            'extension': ext,
            'can_read': False,
            'is_large_file': file_size > 2 * 1024 * 1024 * 1024,  # > 2GB
            'issues': []
        }
        
        # 尝试读取文件
        try:
            with open(file_path, 'rb') as f:
                header = f.read(32)
                result['can_read'] = len(header) > 0
                if not result['can_read']:
                    result['issues'].append('文件为空或无法读取')
        except Exception as e:
            result['issues'].append(f'文件读取错误: {str(e)}')
        
        # 检查文件扩展名
        supported_extensions = {'.mp4', '.mov', '.mkv', '.webm', '.avi', '.flv'}
        if ext not in supported_extensions:
            result['issues'].append(f'文件扩展名 {ext} 可能不被支持')
        
        # 大文件警告
        if result['is_large_file']:
            result['issues'].append(f'文件较大 ({result["size_formatted"]})，可能需要更长的加载时间')
        
        # 编码建议
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
    print(f"Video folder: {VIDEO_FOLDER}")
    print(f"IS_FROZEN: {IS_FROZEN}")
    print(f"PROJECT_ROOT: {PROJECT_ROOT}")
    
    # 确保视频目录存在
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER, exist_ok=True)
        print(f"Created video folder: {VIDEO_FOLDER}")
    
    # 扫描视频文件
    try:
        video_count = len(get_videos_cache())
        print(f"Videos found: {video_count}")
    except Exception as e:
        print(f"Error scanning videos: {e}")
        video_count = 0
    
    debug_mode = os.getenv('FLASK_DEBUG', '0') == '1'

    # Desktop packaged app should only listen on localhost to avoid Windows firewall prompts
    # and unintended LAN exposure. In dev, keep 0.0.0.0 for LAN access.
    default_host ='0.0.0.0'
    host = os.getenv('LOCAL_V_HOST', default_host)
    
    print(f"Listening on: {host}:56173")
    print(f"Debug mode: {debug_mode}")
    print(f"=" * 60)
    
    app.run(host=host, port=56173, debug=debug_mode)
