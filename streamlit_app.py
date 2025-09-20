from youtube_transcript_api import YouTubeTranscriptApi
from yt_dlp import YoutubeDL
import streamlit as st
import requests
from datetime import datetime, timedelta
import os
import tempfile as tf
import ssl
import re
import unicodedata

ssl._create_default_https_context = ssl._create_unverified_context

# Today String
datetime_utc = datetime.utcnow()
datetime_kst = datetime_utc + timedelta(hours=9)
today = datetime_kst.today().date().strftime('%Y.%m.%d')

# Youtube API-Key
YOUTUBE_API_KEY = os.environ.get('GOOGLE_API_KEY')

def sanitize_filename(filename):
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)  # Remove special chars.
    # filename = filename.replace(" ", "_")  # Replace spaces with underscore.
    return filename

class MyLogger(object):
    def debug(self, msg):
        pass

    def warning(self, msg):
        st.warning(msg)

    def error(self, msg):
        st.error(msg)

def my_hook(d):
    if d['status'] == 'finished':
        st.write('다운로드가 완료되었습니다. 변환을 시작합니다...')
    elif d['status'] == 'error':
        st.error('다운로드 중 오류가 발생했습니다.')

# yt-dlp 업데이트 확인 및 권장사항
def check_ytdlp_version():
    try:
        import yt_dlp
        current_version = yt_dlp.version.__version__
        st.sidebar.info(f"yt-dlp 버전: {current_version}")
        st.sidebar.markdown("**💡 팁:** HTTP 403 오류가 지속되면 `pip install --upgrade yt-dlp`로 업데이트하세요.")
    except:
        st.sidebar.warning("yt-dlp 버전을 확인할 수 없습니다.")

# HTTP 403 오류 방지를 위한 공통 설정
def get_common_ydl_opts():
    import random
    
    # 다양한 User-Agent 중 랜덤 선택
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0'
    ]
    
    return {
        'quiet': True,
        'no_warnings': True,
        # 랜덤 User-Agent 설정
        'http_headers': {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
            'Connection': 'keep-alive',
        },
        # 쿠키 사용
        'cookiefile': None,
        # 지역 우회 (여러 국가 시도)
        'geo_bypass': True,
        'geo_bypass_country': random.choice(['US', 'CA', 'GB', 'DE', 'JP']),
        # 재시도 설정 강화
        'retries': 5,
        'fragment_retries': 5,
        'socket_timeout': 30,
        # 속도 제한으로 차단 방지
        'sleep_interval': 1,
        'max_sleep_interval': 3,
        'sleep_interval_requests': 1,
        # SSL 검증 비활성화
        'nocheckcertificate': True,
        # 추가 우회 옵션 강화
        'extractor_args': {
            'youtube': {
                'skip': ['hls'],  # HLS 스트림만 건너뛰기
                'player_client': ['android', 'web', 'ios'],  # 더 많은 클라이언트 시도
                'player_skip': ['configs'],
                'comment_sort': ['top'],
                'max_comments': [0],
            }
        },
        # 추가 안정성 옵션
        'source_address': '0.0.0.0',  # IPv4 강제 사용
        'force_ipv4': True,
    }

# 동영상 정보 및 사용 가능한 품질 가져오기
def get_video_info_and_formats(yt_url):
    try:
        ydl_opts = get_common_ydl_opts()
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(yt_url, download=False)
            
            title = info_dict.get('title', 'Unknown')
            duration = info_dict.get('duration', 0)
            uploader = info_dict.get('uploader', 'Unknown')
            view_count = info_dict.get('view_count', 0)
            
            # 사용 가능한 포맷 분석
            formats = info_dict.get('formats', [])
            
            # 비디오 품질 추출 (더 상세한 정보)
            video_qualities = set()
            audio_qualities = set()
            
            st.info(f"📊 총 {len(formats)}개의 포맷을 분석 중...")
            
            for fmt in formats:
                format_id = fmt.get('format_id', 'unknown')
                
                # 비디오 품질 (더 상세한 정보 포함)
                if fmt.get('vcodec') != 'none' and fmt.get('height'):
                    height = fmt.get('height')
                    width = fmt.get('width', 'unknown')
                    ext = fmt.get('ext', 'unknown')
                    fps = fmt.get('fps', 30)
                    vcodec = fmt.get('vcodec', 'unknown')
                    tbr = fmt.get('tbr', 0)  # 총 비트레이트
                    
                    # 해상도별 분류
                    if height >= 2160:
                        quality_label = f"4K ({height}p)"
                    elif height >= 1440:
                        quality_label = f"2K ({height}p)"
                    elif height >= 1080:
                        quality_label = f"1080p"
                    elif height >= 720:
                        quality_label = f"720p"
                    elif height >= 480:
                        quality_label = f"480p"
                    elif height >= 360:
                        quality_label = f"360p"
                    else:
                        quality_label = f"{height}p"
                    
                    # 상세 정보 포함
                    detail_info = f"{quality_label} ({ext}) - {fps}fps"
                    if tbr > 0:
                        detail_info += f" - {int(tbr)}kbps"
                    if vcodec != 'unknown':
                        detail_info += f" - {vcodec}"
                    
                    video_qualities.add(detail_info)
                
                # 오디오 품질 (더 상세한 정보 포함)
                if fmt.get('acodec') != 'none' and fmt.get('abr'):
                    abr = fmt.get('abr')
                    acodec = fmt.get('acodec', 'unknown')
                    ext = fmt.get('ext', 'unknown')
                    asr = fmt.get('asr', 'unknown')  # 샘플링 레이트
                    
                    # 품질별 분류
                    if abr >= 320:
                        quality_label = "최고음질"
                    elif abr >= 256:
                        quality_label = "고음질"
                    elif abr >= 192:
                        quality_label = "표준음질"
                    elif abr >= 128:
                        quality_label = "절약음질"
                    else:
                        quality_label = "저음질"
                    
                    # 상세 정보 포함
                    detail_info = f"{quality_label} ({int(abr)}kbps) - {acodec}"
                    if ext != 'unknown':
                        detail_info += f" ({ext})"
                    if asr != 'unknown':
                        detail_info += f" - {asr}Hz"
                    
                    audio_qualities.add(detail_info)
            
            return {
                'title': title,
                'duration': duration,
                'uploader': uploader,
                'view_count': view_count,
                'video_qualities': sorted(list(video_qualities), reverse=True),
                'audio_qualities': sorted(list(audio_qualities), reverse=True),
                'formats': formats
            }
            
    except Exception as e:
        st.error(f"동영상 정보를 가져오는 중 오류가 발생했습니다: {e}")
        return None

# 선택된 품질에 맞는 포맷 ID 찾기
def get_format_by_quality(formats, selected_quality, is_video=True):
    if is_video:
        # 비디오 품질에서 해상도 추출
        if "4K" in selected_quality or "2160p" in selected_quality:
            target_height = 2160
        elif "2K" in selected_quality or "1440p" in selected_quality:
            target_height = 1440
        elif "1080p" in selected_quality:
            target_height = 1080
        elif "720p" in selected_quality:
            target_height = 720
        elif "480p" in selected_quality:
            target_height = 480
        elif "360p" in selected_quality:
            target_height = 360
        else:
            target_height = 1080  # 기본값
        
        # 해당 해상도의 최고 품질 포맷 찾기
        best_format = None
        for fmt in formats:
            if (fmt.get('vcodec') != 'none' and 
                fmt.get('height') == target_height):
                if not best_format or (fmt.get('tbr', 0) > best_format.get('tbr', 0)):
                    best_format = fmt
        
        if best_format:
            return f"{best_format['format_id']}+bestaudio"
        else:
            return f"best[height<={target_height}]"
    
    else:  # 오디오
        # 오디오 품질에서 비트레이트 추출
        import re
        match = re.search(r'(\d+)kbps', selected_quality)
        if match:
            target_abr = int(match.group(1))
        else:
            target_abr = 320  # 기본값
        
        # 해당 비트레이트의 최고 품질 포맷 찾기
        best_format = None
        for fmt in formats:
            if (fmt.get('acodec') != 'none' and 
                fmt.get('abr') and abs(fmt.get('abr') - target_abr) <= 32):
                if not best_format or (fmt.get('abr', 0) > best_format.get('abr', 0)):
                    best_format = fmt
        
        if best_format:
            return best_format['format_id']
        else:
            return "bestaudio"

# 품질 설정에 따른 오디오 품질 반환
def get_audio_quality(quality_setting):
    qualities = {
        "최고 음질 (320kbps)": "320",
        "고음질 (256kbps)": "256", 
        "표준 (192kbps)": "192",
        "절약 (128kbps)": "128"
    }
    return qualities.get(quality_setting, "320")

# 사용 가능한 포맷 확인 함수
def check_available_formats(yt_url):
    try:
        ydl_opts = {'listformats': True}
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(yt_url, download=False)
            formats = info_dict.get('formats', [])
            st.write("사용 가능한 포맷:")
            for fmt in formats[:10]:  # 처음 10개만 표시
                st.write(f"- {fmt.get('format_id', 'N/A')}: {fmt.get('ext', 'N/A')} ({fmt.get('resolution', 'N/A')})")
    except Exception as e:
        st.error(f"포맷 확인 중 오류: {e}")

# 임시 폴더 생성
def create_temp_dir():
    temp_dir = tf.mkdtemp()
    os.chmod(temp_dir, 0o700)
    return temp_dir

# 유튜브 video_id 추출
def get_video_id(ytb):
    ytb_urls = ["https://www.youtube.com/watch?v=", "https://www.youtube.com/shorts/"]
    youtube_url = ytb.startswith(ytb_urls[0])
    shorts_url = ytb.startswith(ytb_urls[1])
    if youtube_url:
        video_id = ytb.split("=")[-1]
    else:
        video_id = ytb.split("/")[-1]
    return video_id

# 선택된 품질로 비디오 다운로드 (HTTP 403 오류 방지)
def download_video_with_quality(yt_url, temp_dir, video_file_name, selected_quality, formats):
    video_file_base = os.path.splitext(video_file_name)[0]
    
    # 여러 포맷 시도 (403 오류 방지)
    format_options = [
        get_format_by_quality(formats, selected_quality, is_video=True),
        'best[height<=1080]/best[height<=720]/best',  # 대안 포맷
        'worst[height>=480]/worst',  # 낮은 품질로 시도
        'best'  # 최후의 수단
    ]
    
    for format_selector in format_options:
        try:
            st.info(f"포맷 시도 중: {format_selector}")
            
            ydl_opts = get_common_ydl_opts()
            ydl_opts.update({
                'format': format_selector,
                'outtmpl': os.path.join(temp_dir, video_file_base + '.%(ext)s'),
                'merge_output_format': 'mp4',
                'logger': MyLogger(),
                'progress_hooks': [my_hook],
                'prefer_ffmpeg': True,
                # 추가 403 방지 설정
                'nocheckcertificate': True,
                'ignoreerrors': False,
            })
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([yt_url])
            
            # 생성된 파일 찾기
            possible_extensions = ['.mp4', '.webm', '.mkv', '.avi']
            video_file_path = None
            
            for ext in possible_extensions:
                potential_path = os.path.join(temp_dir, video_file_base + ext)
                if os.path.exists(potential_path):
                    video_file_path = potential_path
                    break
            
            if not video_file_path:
                # 디렉토리에서 파일 찾기
                for file in os.listdir(temp_dir):
                    if file.startswith(video_file_base):
                        video_file_path = os.path.join(temp_dir, file)
                        break
            
            if video_file_path and os.path.exists(video_file_path):
                with open(video_file_path, 'rb') as f:
                    st.success(f"✅ 비디오 다운로드 성공: {format_selector}")
                    return f.read()
                    
        except Exception as e:
            st.warning(f"포맷 {format_selector} 실패: {e}")
            continue
    
    st.error("모든 포맷으로 비디오 다운로드를 시도했지만 실패했습니다.")
    return None

# 선택된 품질로 오디오 다운로드 (HTTP 403 오류 방지)
def download_audio_with_quality(yt_url, temp_dir, audio_file_name, selected_quality, formats):
    audio_file_base = os.path.splitext(audio_file_name)[0]
    
    # 품질에서 비트레이트 추출
    import re
    match = re.search(r'(\d+)kbps', selected_quality)
    target_quality = match.group(1) if match else "320"
    
    # 여러 포맷 시도 (403 오류 방지)
    format_options = [
        get_format_by_quality(formats, selected_quality, is_video=False),
        'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
        'best[height<=720]/best',  # 동영상에서 오디오 추출
        'worst'  # 최후의 수단
    ]
    
    for format_selector in format_options:
        try:
            st.info(f"오디오 포맷 시도 중: {format_selector}")
            
            ydl_opts = get_common_ydl_opts()
            ydl_opts.update({
                'format': format_selector,
                'outtmpl': os.path.join(temp_dir, audio_file_base + '.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': target_quality,
                }],
                'logger': MyLogger(),
                'progress_hooks': [my_hook],
                'prefer_ffmpeg': True,
                'keepvideo': False,
                'nocheckcertificate': True,
            })
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([yt_url])
            
            # 생성된 파일 찾기
            audio_file_path = os.path.join(temp_dir, audio_file_base + '.mp3')
            
            if not os.path.exists(audio_file_path):
                # 디렉토리에서 mp3 파일 찾기
                for file in os.listdir(temp_dir):
                    if file.startswith(audio_file_base) and file.endswith('.mp3'):
                        audio_file_path = os.path.join(temp_dir, file)
                        break
            
            if os.path.exists(audio_file_path):
                with open(audio_file_path, 'rb') as f:
                    st.success(f"✅ 오디오 다운로드 성공: {format_selector}")
                    return f.read()
                    
        except Exception as e:
            st.warning(f"오디오 포맷 {format_selector} 실패: {e}")
            continue
    
    st.error("모든 포맷으로 오디오 다운로드를 시도했지만 실패했습니다.")
    return None

# 대안 오디오 포맷으로 다운로드 시도 - 품질 우선순위
def try_alternative_audio_formats(yt_url, temp_dir, audio_file_base):
    alternative_formats = [
        'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',  # 고품질 우선
        'bestaudio[abr>=128]/bestaudio',  # 최소 128kbps
        'best[height<=720]/best',  # 동영상에서 오디오 추출
        'worst'  # 최후의 수단
    ]
    
    for fmt in alternative_formats:
        try:
            st.info(f"대안 오디오 포맷으로 시도 중: {fmt}")
            ydl_opts = {
                'format': fmt,
                'outtmpl': os.path.join(temp_dir, audio_file_base + '.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '256',  # 대안에서도 높은 품질 유지
                }],
                'logger': MyLogger(),
                'progress_hooks': [my_hook],
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([yt_url])
            
            # 생성된 파일 찾기
            for file in os.listdir(temp_dir):
                if file.startswith(audio_file_base) and file.endswith('.mp3'):
                    audio_file_path = os.path.join(temp_dir, file)
                    with open(audio_file_path, 'rb') as f:
                        audio_file = f.read()
                    st.success(f"대안 포맷으로 오디오 다운로드 성공: {fmt}")
                    return audio_file
                    
        except Exception as e:
            st.warning(f"오디오 포맷 {fmt} 실패: {e}")
            continue
    
    st.error("모든 오디오 포맷으로 다운로드를 시도했지만 실패했습니다.")
    return None

# 오디오(MP3) 다운로드 함수 - 사용자 설정 음질
def download_mp3(yt_url, temp_dir, audio_file_name, quality_setting="최고 음질 (320kbps)"):
    # 파일명에서 확장자를 제거하여 base name 생성
    audio_file_base = os.path.splitext(audio_file_name)[0]
    audio_quality = get_audio_quality(quality_setting)
    
    ydl_opts = {
        # 최고 음질 오디오 포맷 우선순위
        'format': 'bestaudio[acodec^=opus]/bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best',
        'outtmpl': os.path.join(temp_dir, audio_file_base + '.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': audio_quality,
        }],
        'logger': MyLogger(),
        'progress_hooks': [my_hook],
        'ignoreerrors': False,
        # 최고 품질 우선
        'prefer_ffmpeg': True,
        'keepvideo': False,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
        st.success("유튜브 오디오 추출 완료!")
        
        # 최종 생성된 오디오 파일 경로
        audio_file_path = os.path.join(temp_dir, audio_file_base + '.mp3')
        
        # 파일이 없으면 다른 확장자로 찾기
        if not os.path.exists(audio_file_path):
            for file in os.listdir(temp_dir):
                if file.startswith(audio_file_base) and file.endswith('.mp3'):
                    audio_file_path = os.path.join(temp_dir, file)
                    break
        
        if not os.path.exists(audio_file_path):
            st.error(f"오디오 파일이 생성되지 않았습니다: {audio_file_path}")
            return try_alternative_audio_formats(yt_url, temp_dir, audio_file_base)
            
        with open(audio_file_path, 'rb') as f:
            audio_file = f.read()
        return audio_file
    except Exception as e:
        st.error(f"오디오 다운로드 중 오류가 발생했습니다: {e}")
        return try_alternative_audio_formats(yt_url, temp_dir, audio_file_base)

# 대안 포맷으로 다운로드 시도 - 화질 우선순위
def try_alternative_formats(yt_url, temp_dir, video_file_base):
    alternative_formats = [
        'best[height<=2160]/best[height<=1440]/best[height<=1080]',  # 4K, 2K, 1080p 우선
        'bestvideo[height<=1080]+bestaudio[ext=m4a]/best[height<=1080]',  # 1080p 조합
        'bestvideo[height<=720]+bestaudio/best[height<=720]',  # 720p 조합
        'best[ext=mp4]/best',  # mp4 우선
        'best'  # 최고 품질
    ]
    
    for fmt in alternative_formats:
        try:
            st.info(f"대안 포맷으로 시도 중: {fmt}")
            ydl_opts = {
                'format': fmt,
                'outtmpl': os.path.join(temp_dir, video_file_base + '.%(ext)s'),
                'logger': MyLogger(),
                'progress_hooks': [my_hook],
            }
            
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([yt_url])
            
            # 생성된 파일 찾기
            for file in os.listdir(temp_dir):
                if file.startswith(video_file_base):
                    video_file_path = os.path.join(temp_dir, file)
                    with open(video_file_path, 'rb') as f:
                        video_byte = f.read()
                    st.success(f"대안 포맷으로 다운로드 성공: {fmt}")
                    return video_byte
                    
        except Exception as e:
            st.warning(f"포맷 {fmt} 실패: {e}")
            continue
    
    st.error("모든 포맷으로 다운로드를 시도했지만 실패했습니다.")
    return None

# 비디오(MP4) 다운로드 함수 - 사용자 설정 품질
def download_mp4(yt_url, temp_dir, video_file_name, quality_setting="최고 품질 (4K/2K/1080p)"):
    # 파일명에서 확장자를 제거하여 base name 생성
    video_file_base = os.path.splitext(video_file_name)[0]
    video_format = get_video_format(quality_setting)
    
    ydl_opts = {
        'format': video_format,
        'outtmpl': os.path.join(temp_dir, video_file_base + '.%(ext)s'),
        'merge_output_format': 'mp4',
        'logger': MyLogger(),
        'progress_hooks': [my_hook],
        'ignoreerrors': False,
        'no_warnings': False,
        # 최고 품질 설정
        'prefer_ffmpeg': True,
        'writesubtitles': False,  # 자막은 제외
        'writeautomaticsub': False,
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
        st.success("유튜브 동영상 추출 완료!")
        
        # 실제 생성된 파일 찾기 (확장자가 다를 수 있음)
        possible_extensions = ['.mp4', '.webm', '.mkv', '.avi']
        video_file_path = None
        
        for ext in possible_extensions:
            potential_path = os.path.join(temp_dir, video_file_base + ext)
            if os.path.exists(potential_path):
                video_file_path = potential_path
                break
        
        if not video_file_path:
            st.error(f"동영상 파일이 생성되지 않았습니다.")
            return None
            
        with open(video_file_path, 'rb') as f:
            video_byte = f.read()
        return video_byte
    except Exception as e:
        st.error(f"동영상 다운로드 중 오류가 발생했습니다: {e}")
        # 대안 포맷으로 재시도
        return try_alternative_formats(yt_url, temp_dir, video_file_base)

# 스크립트 목록 추출. 없으면 안내 메시지 출력
def get_transcript_list(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=["ko", "en"])
        return transcript_list
    except Exception as e:
        st.error(f"스크립트를 가져오는 중 오류가 발생했습니다: {e}")
        st.markdown("MP3 파일을 저장한 다음, [Hani Script Extractor](https://haniscriptextractor.streamlit.app/)를 이용해 스크립트를 추출하세요")
        return None

# 시작 시간 표시
def set_time_form(script):
    seconds = script['start']
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    times = [str(hours), str(minutes), str(seconds)]
    for idx, time in enumerate(times):
        if int(time) < 10:
            times[idx] = "0" + time
    time_form = f"[{times[0]}:{times[1]}:{times[2]}]"
    return time_form

# 통 스크립트 표시
def extract_script_all(transcript_list, temp_dir, all_file_name):
    for script in transcript_list:
        text = script['text']
        try:
            with open(os.path.join(temp_dir, all_file_name), "a+", encoding="utf-8") as f:
                f.write(text + " ")
        except FileNotFoundError:
            os.mkdir(temp_dir)
            with open(os.path.join(temp_dir, all_file_name), "a+", encoding="utf-8") as f:
                f.write(text + " ")
    all_file = os.path.join(temp_dir, all_file_name)
    return all_file

# 타임라인 스크립트 표시
def extract_script_timeline(transcript_list, temp_dir, timeline_file_name):
    count = 10
    for i, script in enumerate(transcript_list):
        timeline = set_time_form(script)
        text = script['text']
        try:
            with open(os.path.join(temp_dir, timeline_file_name), "a+", encoding="utf-8") as f:
                if i == 0:
                    f.write(timeline + '\n\n')
                    f.write(text + " ")
                elif i < count:
                    f.write(text + " ")
                elif i == count:
                    f.write('\n\n' + timeline + '\n\n')
                    f.write(text + " ")
                    count += 10
        except FileNotFoundError:
            os.mkdir(temp_dir)
            with open(os.path.join(temp_dir, timeline_file_name), "a+", encoding="utf-8") as f:
                if i == 0:
                    f.write(timeline + '\n\n')
                    f.write(text + " ")
                elif i < count:
                    f.write(text + " ")
                elif i == count:
                    f.write('\n\n' + timeline + '\n\n')
                    f.write(text + " ")
                    count += 10
    timeline_file = os.path.join(temp_dir, timeline_file_name)
    return timeline_file

############################################################

def yt_app():
    # Set page title and icon
    st.set_page_config(
        page_title="유튜브 추출기",
        page_icon="https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png"
    )

    if 'video_byte' not in st.session_state:
        st.session_state.video_byte = None
    if 'audio_file' not in st.session_state:
        st.session_state.audio_file = None
    if 'script_timeline' not in st.session_state:
        st.session_state.script_timeline = None

    # Featured image with reload button
    col1, col2 = st.columns([1, 0.3])
    with col1:
        st.image(
            "https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png",
            width=150
        )
    with col2:
        if st.button("Reload ⟳"):
            st.rerun()

    # Main title and description
    st.title("유튜브 동영상 · 오디오 · 스크립트 추출기")
    st.markdown("유튜브 URL을 넣으면 🎬:blue[동영상], 🔊:red[오디오], 📝:green[스크립트]를 내려받을 수 있습니다.")
    
    # 버전 확인 및 팁 표시
    check_ytdlp_version()
    
    # HTTP 403 오류 해결 팁
    with st.expander("🔧 HTTP 403 오류 해결 방법"):
        st.markdown("""
        **HTTP 403 Forbidden 오류가 발생하는 경우:**
        
        1. **yt-dlp 업데이트**: `pip install --upgrade yt-dlp`
        2. **VPN 사용**: 다른 지역으로 IP 변경
        3. **시간 간격**: 잠시 후 다시 시도
        4. **다른 품질 선택**: 낮은 품질로 시도
        
        **이 앱의 개선사항:**
        - 자동 User-Agent 설정
        - 다중 포맷 시도
        - 지역 우회 설정
        - 재시도 메커니즘
        """)

    # Input for YouTube URL
    yt_url = st.text_input(
        label="유튜브 주소를 넣어주세요.(유튜브 쇼츠도 지원합니다.)",
        placeholder="ex) https://www.youtube.com/watch?v=nVQY16LgEyU",
        key="yt_url"
    )

    st.divider()

    if yt_url:
        if yt_url.startswith("https://www.youtube.com/") or yt_url.startswith("https://youtu.be/"):
            # 동영상 정보 가져오기
            with st.spinner("동영상 정보를 가져오는 중입니다..."):
                video_info = get_video_info_and_formats(yt_url)
            
            if video_info:
                # 동영상 정보 표시
                st.success("✅ 동영상 정보를 성공적으로 가져왔습니다!")
                
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.subheader(f"🎬 {video_info['title']}")
                    st.write(f"**업로더:** {video_info['uploader']}")
                    
                    duration_min = video_info['duration'] // 60
                    duration_sec = video_info['duration'] % 60
                    st.write(f"**길이:** {duration_min}분 {duration_sec}초")
                    
                    if video_info['view_count']:
                        st.write(f"**조회수:** {video_info['view_count']:,}회")
                
                with col2:
                    st.image("https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png", width=100)

                st.divider()

                # 사용 가능한 품질 표시 및 선택
                st.subheader("📊 사용 가능한 품질 선택")
                
                # 품질 분석 요약 표시
                quality_summary_col1, quality_summary_col2 = st.columns(2)
                with quality_summary_col1:
                    st.metric("🎬 비디오 품질", f"{len(video_info['video_qualities'])}개")
                with quality_summary_col2:
                    st.metric("🔊 오디오 품질", f"{len(video_info['audio_qualities'])}개")
                
                # 상세 품질 정보 확장 가능한 섹션
                with st.expander("🔍 전체 품질 목록 보기"):
                    detail_col1, detail_col2 = st.columns(2)
                    
                    with detail_col1:
                        st.markdown("**📹 사용 가능한 비디오 품질:**")
                        for i, quality in enumerate(video_info['video_qualities'], 1):
                            st.write(f"{i}. {quality}")
                    
                    with detail_col2:
                        st.markdown("**🎵 사용 가능한 오디오 품질:**")
                        for i, quality in enumerate(video_info['audio_qualities'], 1):
                            st.write(f"{i}. {quality}")
                
                # 임시 디렉토리 생성
                temp_dir = create_temp_dir()
                
                # 파일명 생성
                video_file_name = sanitize_filename(f"{video_info['title']}.mp4")
                audio_file_name = sanitize_filename(f"{video_info['title']}.mp3")
                timeline_file_name = sanitize_filename(f"{video_info['title']}_timeline.txt")
                all_file_name = sanitize_filename(f"{video_info['title']}_all.txt")

                # 3개 열로 나누어 비디오, 오디오, 스크립트
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("### 🎬 비디오 품질")
                    if video_info['video_qualities']:
                        st.info(f"📊 {len(video_info['video_qualities'])}개의 비디오 품질 사용 가능")
                        
                        selected_video_quality = st.selectbox(
                            "비디오 품질 선택:",
                            video_info['video_qualities'],
                            key="video_quality_select",
                            help="해상도, 포맷, FPS, 비트레이트, 코덱 정보가 포함됩니다"
                        )
                        
                        # 선택된 품질 상세 정보 표시
                        st.caption(f"선택된 품질: {selected_video_quality}")
                        
                        if st.button("📥 비디오 다운로드", key="video_download", use_container_width=True):
                            with st.spinner(f"비디오 다운로드 중... ({selected_video_quality})"):
                                video_byte = download_video_with_quality(
                                    yt_url, temp_dir, video_file_name, 
                                    selected_video_quality, video_info['formats']
                                )
                                if video_byte:
                                    st.success("✅ 비디오 다운로드 완료!")
                                    st.video(video_byte, format='video/mp4')
                                    st.download_button(
                                        label="💾 MP4 파일 저장",
                                        data=video_byte,
                                        file_name=video_file_name,
                                        mime='video/mp4',
                                        use_container_width=True
                                    )
                    else:
                        st.warning("사용 가능한 비디오 품질이 없습니다.")

                with col2:
                    st.markdown("### 🔊 오디오 품질")
                    if video_info['audio_qualities']:
                        st.info(f"📊 {len(video_info['audio_qualities'])}개의 오디오 품질 사용 가능")
                        
                        selected_audio_quality = st.selectbox(
                            "오디오 품질 선택:",
                            video_info['audio_qualities'],
                            key="audio_quality_select",
                            help="비트레이트, 코덱, 포맷, 샘플링 레이트 정보가 포함됩니다"
                        )
                        
                        # 선택된 품질 상세 정보 표시
                        st.caption(f"선택된 품질: {selected_audio_quality}")
                        
                        if st.button("📥 오디오 다운로드", key="audio_download", use_container_width=True):
                            with st.spinner(f"오디오 다운로드 중... ({selected_audio_quality})"):
                                audio_byte = download_audio_with_quality(
                                    yt_url, temp_dir, audio_file_name,
                                    selected_audio_quality, video_info['formats']
                                )
                                if audio_byte:
                                    st.success("✅ 오디오 다운로드 완료!")
                                    st.audio(audio_byte, format='audio/mp3')
                                    st.download_button(
                                        label="💾 MP3 파일 저장",
                                        data=audio_byte,
                                        file_name=audio_file_name,
                                        mime='audio/mp3',
                                        use_container_width=True
                                    )
                    else:
                        st.warning("사용 가능한 오디오 품질이 없습니다.")

                with col3:
                    st.markdown("### 📝 스크립트")
                    st.write("자막/스크립트를 추출합니다.")
                    
                    if st.button("📥 스크립트 다운로드", key="script_download", use_container_width=True):
                        with st.spinner("스크립트를 가져오는 중입니다..."):
                            video_id = get_video_id(yt_url)
                            transcript_list = get_transcript_list(video_id)
                            if transcript_list:
                                all_file = extract_script_all(transcript_list, temp_dir, all_file_name)
                                timeline_file = extract_script_timeline(transcript_list, temp_dir, timeline_file_name)
                                
                                with open(timeline_file, "r", encoding="utf-8") as f:
                                    timeline_data = f.read()
                                with open(all_file, "r", encoding="utf-8") as f:
                                    all_data = f.read()
                                
                                st.success("✅ 스크립트 추출 완료!")
                                st.text_area("스크립트 미리보기:", timeline_data[:500] + "...", height=150)
                                
                                script_col1, script_col2 = st.columns(2)
                                with script_col1:
                                    st.download_button(
                                        label="💾 타임라인 스크립트",
                                        data=timeline_data,
                                        file_name=timeline_file_name,
                                        mime='text/plain',
                                        use_container_width=True
                                    )
                                with script_col2:
                                    st.download_button(
                                        label="💾 전체 스크립트",
                                        data=all_data,
                                        file_name=all_file_name,
                                        mime='text/plain',
                                        use_container_width=True
                                    )
                            else:
                                st.error("스크립트를 가져올 수 없습니다.")
            else:
                st.error("동영상 정보를 가져올 수 없습니다.")
        else:
            st.error("올바른 유튜브 주소를 입력해주세요.")
    else:
        st.info("👆 위에 유튜브 URL을 입력하면 사용 가능한 품질을 확인할 수 있습니다.")

# Main
if __name__ == "__main__":
    yt_app()
