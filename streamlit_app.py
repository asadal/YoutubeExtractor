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

# 오디오(MP3) 다운로드 함수
def download_mp3(yt_url, temp_dir, audio_file_name):
    # 파일명에서 확장자를 제거하여 base name 생성
    audio_file_base = os.path.splitext(audio_file_name)[0]
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(temp_dir, audio_file_base + '.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320',  # 최고 음질로 설정
        }],
        'logger': MyLogger(),
        'progress_hooks': [my_hook],
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
        st.success("유튜브 오디오 추출 완료!")
        # 최종 생성된 오디오 파일 경로
        audio_file_path = os.path.join(temp_dir, audio_file_base + '.mp3')
        st.write(f"생성된 오디오 파일 위치: {audio_file_path}")
        if not os.path.exists(audio_file_path):
            st.error(f"오디오 파일이 생성되지 않았습니다: {audio_file_path}")
            return None
        with open(audio_file_path, 'rb') as f:
            audio_file = f.read()
        return audio_file
    except Exception as e:
        st.error(f"오디오 다운로드 중 오류가 발생했습니다: {e}")
        return None

# 비디오(MP4) 다운로드 함수
def download_mp4(yt_url, temp_dir, video_file_name):
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # 최고 화질로 설정
        'outtmpl': os.path.join(temp_dir, video_file_name),
        'merge_output_format': 'mp4',
    }
    try:
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])
        st.success("유튜브 동영상 추출 완료!")
        with open(os.path.join(temp_dir, video_file_name), 'rb') as f:
            video_byte = f.read()
        return video_byte
    except Exception as e:
        st.error(f"동영상 다운로드 중 오류가 발생했습니다: {e}")
        return None

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
    times = [hours, minutes, seconds]
    for idx, time in enumerate(times):
        if time < 10:
            times[idx] = "0" + str(time)
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
            st.experimental_rerun()

    # Main title and description
    st.title("유튜브 동영상 · 오디오 · 스크립트 추출기")
    st.markdown("유튜브 URL을 넣으면 🎬:blue[동영상], 🔊:red[오디오], 📝:green[스크립트]를 내려받을 수 있습니다.")

    # Input for YouTube URL
    yt_url = st.text_input(
        label="유튜브 주소를 넣어주세요.(유튜브 쇼츠도 지원합니다.)",
        placeholder="ex) https://www.youtube.com/watch?v=nVQY16LgEyU",
        key="yt_url"
    )

    st.divider()

    if yt_url:
        if yt_url.startswith("https://www.youtube.com/") or yt_url.startswith("https://youtu.be/"):
            # 기본 변수 설정
            temp_dir = create_temp_dir()
            try:
                ydl_opts = {}
                with YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(yt_url, download=False)
                    title = info_dict.get('title', None)
                    if title is None:
                        st.error("동영상 제목을 가져올 수 없습니다.")
                        st.stop()
            except Exception as e:
                st.error(f"동영상 정보를 가져오는 중 오류가 발생했습니다: {e}")
                st.stop()

            video_file_name = sanitize_filename(f"{title}.mp4")
            audio_file_name = sanitize_filename(f"{title}.mp3")
            timeline_file_name = sanitize_filename(f"{title}_timeline.txt")
            all_file_name = sanitize_filename(f"{title}_all.txt")

            # 컨테이너 생성
            con = st.container()
            with con:
                con.write("동영상(MP4) 내려받기")
                if st.button("🎬 동영상(MP4)"):
                    with st.spinner("동영상을 다운로드 중입니다..."):
                        video_byte = download_mp4(yt_url, temp_dir, video_file_name)
                        if video_byte:
                            st.session_state.video_byte = video_byte
                            st.video(st.session_state.video_byte, format='video/mp4')
                            st.download_button(
                                label='📥 Download MP4 File 🎬',
                                data=st.session_state.video_byte,
                                file_name=video_file_name,
                                mime='video/mp4'
                            )

            if st.button("🔊 오디오(MP3)"):
                with st.spinner("오디오를 다운로드 중입니다..."):
                    audio_file = download_mp3(yt_url, temp_dir, audio_file_name)
                    if audio_file:
                        st.session_state.audio_file = audio_file
                        st.audio(st.session_state.audio_file, format='audio/mp3')
                        st.download_button(
                            label='📥 Download MP3 File 🔊',
                            data=st.session_state.audio_file,
                            file_name=audio_file_name,
                            mime='audio/mp3'
                        )

            if st.button("📝 스크립트(TXT)"):
                with st.spinner("스크립트를 가져오는 중입니다..."):
                    video_id = get_video_id(yt_url)
                    transcript_list = get_transcript_list(video_id)
                    if transcript_list:
                        all_file = extract_script_all(transcript_list, temp_dir, all_file_name)
                        timeline_file = extract_script_timeline(transcript_list, temp_dir, timeline_file_name)
                        with open(timeline_file, "r", encoding="utf-8") as f:
                            timeline_data = f.read()
                            st.session_state.script_timeline = timeline_data
                        st.write(st.session_state.script_timeline)
                        with open(all_file, "r", encoding="utf-8") as f:
                            all_data = f.read()
                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button(
                                label="📥 Download Timeline Script ⏱",
                                data=timeline_data,
                                file_name=timeline_file_name,
                                mime='text/plain'
                            )
                        with col2:
                            st.download_button(
                                label="📥 Download Entire Script 📝",
                                data=all_data,
                                file_name=all_file_name,
                                mime='text/plain'
                            )
                    else:
                        st.error("스크립트를 가져올 수 없습니다.")

        else:
            st.error("올바른 유튜브 주소를 입력해주세요.")
    else:
        pass

# Main
if __name__ == "__main__":
    yt_app()
