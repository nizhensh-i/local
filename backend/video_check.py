#!/usr/bin/env python3
"""
视频文件检查工具
用于诊断视频播放问题
"""

import os
import sys
import subprocess
from pathlib import Path

def check_video_file(video_path):
    """检查视频文件信息"""
    if not os.path.exists(video_path):
        return {'error': '文件不存在'}
    
    file_size = os.path.getsize(video_path)
    ext = os.path.splitext(video_path)[1].lower()
    
    result = {
        'path': video_path,
        'size': file_size,
        'size_formatted': format_file_size(file_size),
        'extension': ext,
        'can_read': False,
        'has_video_stream': False,
        'has_audio_stream': False,
        'video_codec': None,
        'audio_codec': None,
        'duration': None,
        'is_supported': False,
        'issues': []
    }
    
    # 尝试读取文件前几个字节
    try:
        with open(video_path, 'rb') as f:
            header = f.read(32)
            if len(header) > 0:
                result['can_read'] = True
            else:
                result['issues'].append('文件为空或无法读取')
    except Exception as e:
        result['issues'].append(f'文件读取错误: {str(e)}')
        return result
    
    # 使用 ffprobe 检查视频信息（如果安装了 ffmpeg）
    try:
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
            '-show_format', '-show_streams', video_path
        ]
        probe_result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if probe_result.returncode == 0:
            import json
            probe_data = json.loads(probe_result.stdout)
            
            # 获取格式信息
            if 'format' in probe_data:
                format_info = probe_data['format']
                result['duration'] = float(format_info.get('duration', 0))
                result['format_name'] = format_info.get('format_name', '')
            
            # 检查流信息
            if 'streams' in probe_data:
                for stream in probe_data['streams']:
                    if stream['codec_type'] == 'video':
                        result['has_video_stream'] = True
                        result['video_codec'] = stream['codec_name']
                        
                        # 检查视频编码是否被浏览器支持
                        supported_video_codecs = ['h264', 'avc', 'vp8', 'vp9', 'av1']
                        if result['video_codec'].lower() in supported_video_codecs:
                            result['is_supported'] = True
                        else:
                            result['issues'].append(
                                f"视频编码 '{result['video_codec']}' 可能不被浏览器支持。"
                                f"支持的编码: H.264, VP8, VP9, AV1"
                            )
                    
                    elif stream['codec_type'] == 'audio':
                        result['has_audio_stream'] = True
                        result['audio_codec'] = stream['codec_name']
            
            # 如果没有检测到支持的编码，添加警告
            if not result['is_supported'] and result['has_video_stream']:
                result['issues'].append(
                    "未检测到浏览器支持的视频编码。建议使用 H.264 (AVC) 编码。"
                )
        
        else:
            result['issues'].append('无法使用 ffprobe 检查视频信息（未安装 ffmpeg）')
            # 基于文件扩展名做基本判断
            if ext in ['.mp4', '.mov', '.webm', '.mkv']:
                result['is_supported'] = True  # 假设支持
    
    except FileNotFoundError:
        result['issues'].append('未安装 ffprobe（ffmpeg），无法检查视频详细信息')
        result['issues'].append('建议安装 ffmpeg: brew install ffmpeg')
        # 基于文件扩展名做基本判断
        if ext in ['.mp4', '.mov', '.webm']:
            result['is_supported'] = True
    
    except Exception as e:
        result['issues'].append(f'检查视频时出错: {str(e)}')
    
    return result


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


def print_check_result(result):
    """打印检查结果"""
    print("=" * 70)
    print("视频文件检查报告")
    print("=" * 70)
    print(f"文件路径: {result['path']}")
    print(f"文件大小: {result['size_formatted']}")
    print(f"文件扩展名: {result['extension']}")
    
    if result['can_read']:
        print("✓ 文件可读")
    else:
        print("✗ 文件无法读取")
    
    if 'format_name' in result:
        print(f"容器格式: {result['format_name']}")
    
    if result['has_video_stream']:
        print(f"✓ 视频流: {result['video_codec'] or '未知'}")
    else:
        print("✗ 未找到视频流")
    
    if result['has_audio_stream']:
        print(f"✓ 音频流: {result['audio_codec'] or '未知'}")
    else:
        print("! 未找到音频流（可能是纯视频文件）")
    
    if result['duration']:
        print(f"视频时长: {result['duration']:.2f} 秒")
    
    print("\n浏览器兼容性:")
    if result['is_supported']:
        print("✓ 视频编码应该被现代浏览器支持")
    else:
        print("✗ 视频编码可能不被浏览器支持")
    
    if result['issues']:
        print("\n发现的问题:")
        for i, issue in enumerate(result['issues'], 1):
            print(f"{i}. {issue}")
    
    print("\n建议:")
    if not result['is_supported']:
        print("- 将视频转换为 H.264 (AVC) 编码的 MP4 格式")
        print("- 可以使用 ffmpeg 进行转换:")
        print(f"  ffmpeg -i \"{result['path']}\" -c:v libx264 -preset medium -crf 23 -c:a aac -b:a 128k output.mp4")
    
    if result['size'] > 2 * 1024 * 1024 * 1024:  # 2GB
        print(f"- 文件较大 ({result['size_formatted']})，建议使用支持 Range 请求的播放器")
    
    print("=" * 70)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python3 video_check.py <视频文件路径>")
        sys.exit(1)
    
    video_path = sys.argv[1]
    
    if not os.path.exists(video_path):
        print(f"错误: 文件不存在: {video_path}")
        sys.exit(1)
    
    print(f"正在检查视频文件: {video_path}")
    print("这可能需要一些时间，请稍候...\n")
    
    result = check_video_file(video_path)
    print_check_result(result)
    
    # 退出码
    sys.exit(0 if result['is_supported'] and not result['issues'] else 1)


if __name__ == '__main__':
    main()
