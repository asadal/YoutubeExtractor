from youtube_transcript_api import YouTubeTranscriptApi
from pytube import YouTube
import streamlit as st
import requests
from datetime import datetime, timedelta
from moviepy.editor import VideoFileClip
import os
import tempfile as tf


# temp_dir = "/Users/asadal/Downloads/"

# Today String
datetime_utc = datetime.utcnow()
datetime_kst = datetime_utc + timedelta(hours=9)
today = datetime_kst.today().date().strftime('%Y.%m.%d')

# Youtube API-Key
YOUTUBE_API_KEY = os.environ.get('GOOGLE_API_KEY')

# 임시 폴더 생성
def create_temp_dir():
    # Create a temporary directory
    set_temp_dir = tf.TemporaryDirectory()
    temp_dir = set_temp_dir.name + "/"
    # 디렉터리 접근 권한 설정
    os.chmod(temp_dir, 0o700)
    return temp_dir

# 유튜브 video_id 추출
def get_video_id(ytb):
    video_id = ytb.split("=")[-1]
    return video_id

# 유튜브 동영상 다운로드
def download_mp4(ytb):
    stream = ytb.streams.get_highest_resolution()
    print("stream : ", stream)
    print("stream.url : ", stream.url)
    video_byte = requests.get(stream.url).content
    return video_byte

# mp3 추출 함수
def download_mp3_from_mp4(ytb, temp_dir, video_file_name, video_file_path, audio_file_path):
    stream = ytb.streams.get_highest_resolution()
    stream.download(temp_dir, filename=video_file_name)
    video = VideoFileClip(video_file_path)
    video.audio.write_audiofile(audio_file_path)
    st.success("유튜브 오디오 추출 완료!")
    with open(audio_file_path, 'rb') as f:
        audio_file = f.read()
    return audio_file

def get_transcript_list(video_id):
    transcript_list = YouTubeTranscriptApi.get_transcript(video_id,languages=["ko", "en"])
    return transcript_list

def read_file_data(filename, opt):
    with open(filename, opt, encoding="utf-8") as f:
        data = f.read()
        return data

def extract_script_all(transcript_list, temp_dir, script_file_name):
    for script in transcript_list:
        set_time = str(round(script['start']/60,2)).split(".")
        text = script['text']
        try:
            with open(temp_dir + script_file_name + "_all", "a+", encoding="utf-8") as f:
                f.write(text + " ")
        except TranscriptsDisabled:
            st.error("스크립트가 없는 영상입니다. 😢")
            st.markdown("[Youtube-Whisper](https://huggingface.co/spaces/kazuk/youtube-whisper-10)를 이용해 스크립트를 추출하세요")
            st.stop()
    all_file = temp_dir + script_file_name + "_all"
    return all_file

def extract_script_timeline(transcript_list, temp_dir, script_file_name):
    count = 10
    for i, script in enumerate(transcript_list):
        set_time = str(round(script['start']/60,2)).split(".")
        timeline = "[" + set_time[0] + ":" + set_time[1] + "]"
        text = script['text']
        with open(temp_dir + script_file_name  + "_timeline", "a+", encoding="utf-8") as f:
            if i == 0:
                f.write(timeline + '\n\n')
                f.write(text + " ")
            elif i < count:
                f.write(text + " ")
            elif i == count:
                f.write('\n\n' + timeline + '\n\n')
                f.write(text + " ")
                count += 10
    timeline_file = temp_dir + script_file_name + "_timeline"
    return timeline_file

############################################################

def yt_app():
    # Set page title and icon
    st.set_page_config(
        page_title="유튜브 추출기",
        page_icon="https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png"
    )

    # Featured image
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/e/ef/Youtube_logo.png",
        width=150
    )

    # Main title and description
    st.title("유튜브 동영상 · 오디오 · 스크립트 추출기")
    st.markdown("유튜브 URL을 넣으면 🎬:blue[동영상], 🔊:red[오디오], 📝:green[스크립트]를 내려받을 수 있습니다.")

    # Input for YouTube URL
    yt_url = st.text_input(
        label="유튜브 주소를 넣어주세요.",
        placeholder="ex) https://www.youtube.com/watch?v=nVQY16LgEyU",
        key="yt_url"
    )
    # confirm = st.button("확인")
    
    st.divider()
    
    # if yt_url is not None:
    if yt_url:
        
        if yt_url.startswith("https://www.youtube.com/watch?v="):
            # 기본 변수 설정
            temp_dir = create_temp_dir()
            yt = YouTube(yt_url)
            title = yt.title
            video_file_name = f"{title}.mp4"
            audio_file_name = f"{title}.mp3"
            video_file_path = temp_dir + video_file_name
            audio_file_path = temp_dir + audio_file_name
            script_file_name = f"{title}.txt"

            # 컨테이너 생성
            con = st.container()
            with con:
                con.write("동영상(MP4) 내려받기")
                # 1. MP4 내려받기
                if st.button("🎬 동영상(MP4)"):
                    with st.spinner("Downloading mp4..."):
                        video_byte = download_mp4(yt)
                        st.success("유튜브 동영상 추출 완료!")
                        st.download_button(
                            label='📥 Download MP4 File 🎬', 
                            data=video_byte, 
                            file_name=video_file_name, 
                            mime='video/mp4'
                        )

            with con:
                con.write("오디오(MP3) 내려받기")
                # 2. MP3 내려받기
                if st.button("🔊 오디오(MP3)"):
                    with st.spinner("Downloading mp3..."):
                        audio_file = download_mp3_from_mp4(yt, temp_dir, video_file_name, video_file_path, audio_file_path)
                        st.audio(audio_file, format='audio/mp3')
                        st.write("오디오 파일을 저장하려면 메뉴(⋮)를 누르고 '다운로드'를 선택하세요. 🔊")
                        st.download_button(
                            label='📥 Download MP3 File 🔊',
                            data=audio_file,
                            file_name=audio_file_name,
                            mime='audio/mp3'
                        )

            with con:
                con.write("스크립트(TXT) 내려받기")
                # 3. 스크립트 내려받기
                if st.button("📝 스크립트(TXT)"):
                    temp_dir = create_temp_dir()
                    video_id = yt.video_id
                    transcript_list = get_transcript_list(video_id)
                    entire_file = extract_script_all(transcript_list, temp_dir, script_file_name)
                    timeline_file = extract_script_timeline(transcript_list, temp_dir, script_file_name)
                    timeline_data = read_file_data(timeline_file, "r")
                    st.write(timeline_data)
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                                label="📥 Download Timeline Script ⏱",
                                data=timeline_data,
                                file_name= script_file_name + "_timeline",
                                mime='text/plain'
                                )
                    with col2:
                        st.download_button(
                                label="📥 Download Entire Script 📝",
                                data=read_file_data(entire_file, "r"),
                                file_name=script_file_name + "_all",
                                mime='text/plain'
                                )
                                
        else:
            st.error("올바른 유튜브 주소를 입력해주세요.")
    else:
        pass
    # st.stop()
# Main
if __name__ == "__main__":
    yt_app()
 
