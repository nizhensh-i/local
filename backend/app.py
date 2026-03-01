import os
from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS
import mimetypes
from config import VIDEO_FOLDER, DEFAULT_PAGE_SIZE
from utils import scan_video_files, filter_and_sort_videos, paginate_videos

app = Flask(__name__)

# 配置 CORS - 支持本地和局域网访问
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            # 允许任何 192.168.x.x 和 10.x.x.x 的局域网地址
            r"^http://192\.168\.\d{1,3}\.\d{1,3}:\d+$",
            r"^http://10\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$"
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Range", "Accept"],
        "expose_headers": ["Content-Range", "Accept-Ranges", "Content-Length"],
        "supports_credentials": True
    }
})

# 缓存视频列表，避免重复扫描
cached_videos = None


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
                    'Content-Disposition': f'inline; filename="{filename}"',
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
                'Content-Disposition': f'inline; filename="{filename}"',
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
        # 安全检查，防止路径遍历攻击
        if '..' in filename or filename.startswith('/'):
            return jsonify({
                'success': False,
                'error': 'Invalid filename'
            }), 400
        
        # 构建文件路径
        file_path = os.path.join(VIDEO_FOLDER, filename)
        
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
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/refresh', methods=['POST'])
def refresh_videos():
    """刷新视频列表缓存"""
    global cached_videos
    cached_videos = None
    return jsonify({
        'success': True,
        'message': 'Video cache refreshed'
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'success': True,
        'message': 'Server is running',
        'video_folder': VIDEO_FOLDER,
        'video_count': len(get_videos_cache())
    })


@app.route('/api/videos/<filename>/check', methods=['GET'])
def check_video(filename):
    """检查视频文件信息"""
    try:
        # 安全检查
        if '..' in filename or filename.startswith('/'):
            return jsonify({
                'success': False,
                'error': 'Invalid filename'
            }), 400
        
        file_path = os.path.join(VIDEO_FOLDER, filename)
        
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
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'检查视频时出错: {str(e)}'
        }), 500


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


if __name__ == '__main__':
    print(f"Starting Flask server...")
    print(f"Video folder: {VIDEO_FOLDER}")
    print(f"Videos found: {len(get_videos_cache())}")
    
    # 确保视频目录存在
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER, exist_ok=True)
        print(f"Created video folder: {VIDEO_FOLDER}")
    
    app.run(host='0.0.0.0', port=8990, debug=True)
