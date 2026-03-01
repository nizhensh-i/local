import os
from flask import Flask, jsonify, request, send_file, Response
from flask_cors import CORS
import mimetypes
from config import VIDEO_FOLDER, DEFAULT_PAGE_SIZE
from utils import scan_video_files, filter_and_sort_videos, paginate_videos

app = Flask(__name__)
CORS(app)

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
    """支持 Range 请求的文件发送"""
    try:
        file_size = os.path.getsize(path)
        range_header = request.headers.get('Range', None)
        
        if range_header:
            # 解析 Range 请求
            byte_ranges = range_header.strip().split('=')[-1]
            start_str, end_str = byte_ranges.split('-')
            
            start = int(start_str) if start_str else 0
            end = int(end_str) if end_str else file_size - 1
            
            # 确保范围有效
            start = max(0, start)
            end = min(file_size - 1, end)
            
            # 读取指定范围的数据
            with open(path, 'rb') as f:
                f.seek(start)
                data = f.read(end - start + 1)
            
            # 获取 MIME 类型
            mime_type, _ = mimetypes.guess_type(path)
            if not mime_type:
                mime_type = 'video/mp4'
            
            # 构建响应
            headers = {
                'Content-Type': mime_type,
                'Content-Length': str(end - start + 1),
                'Content-Range': f'bytes {start}-{end}/{file_size}',
                'Accept-Ranges': 'bytes',
                'Content-Disposition': f'inline; filename="{filename}"',
                'Cache-Control': 'public, max-age=3600'
            }
            
            return Response(
                data,
                status=206,
                headers=headers
            )
        
        else:
            # 普通请求，返回整个文件
            mime_type, _ = mimetypes.guess_type(path)
            if not mime_type:
                mime_type = 'video/mp4'
            
            headers = {
                'Content-Type': mime_type,
                'Content-Length': str(file_size),
                'Accept-Ranges': 'bytes',
                'Content-Disposition': f'inline; filename="{filename}"',
                'Cache-Control': 'public, max-age=3600'
            }
            
            return send_file(
                path,
                mimetype=mime_type,
                as_attachment=False,
                conditional=True,
                add_etags=True,
                cache_timeout=3600
            )
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to stream video: {str(e)}'
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


if __name__ == '__main__':
    print(f"Starting Flask server...")
    print(f"Video folder: {VIDEO_FOLDER}")
    print(f"Videos found: {len(get_videos_cache())}")
    
    # 确保视频目录存在
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER, exist_ok=True)
        print(f"Created video folder: {VIDEO_FOLDER}")
    
    app.run(host='0.0.0.0', port=8990, debug=True)
