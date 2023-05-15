from pytube import YouTube
import whisper
import streamlit as st
import requests
from datetime import datetime, timedelta
from moviepy.editor import VideoFileClip
# from tempfile import NamedTemporaryFile
import os
import tempfile as tf
# from pydub import AudioSegment


# temp_dir = "/Users/asadal/Downloads/"

# Today String
datetime_utc = datetime.utcnow()
datetime_kst = datetime_utc + timedelta(hours=9)
today = datetime_kst.today().date().strftime('%Y.%m.%d')


# 임시 폴더 생성
def create_temp_dir():
    # Create a temporary directory
    set_temp_dir = tf.TemporaryDirectory()
    temp_dir = set_temp_dir.name + "/"
    # 디렉터리 접근 권한 설정
    os.chmod(temp_dir, 0o700)
    return temp_dir

# 유튜브 동영상 다운로드
def download_mp4(yt_url):
    yt = YouTube(yt_url)
    stream = yt.streams.get_highest_resolution()
    print("stream : ", stream)
    print("stream.url : ", stream.url)
    video_file_content = requests.get(stream.url).content
    print("video_file_content_type : ", type(video_file_content))
    video_file_name = f"{yt.title}.mp4"
    return video_file_content, video_file_name

# mp3 추출 함수
def download_mp3_from_mp4(yt_url):
    yt = YouTube(yt_url)
    stream = yt.streams.get_highest_resolution()
    temp_dir = create_temp_dir()
    stream.download(temp_dir, filename=f"{yt.title}.mp4")
    video_file_path = temp_dir + f"{yt.title}.mp4"
    video = VideoFileClip(video_file_path)
    audio_file_path = temp_dir + f"{yt.title}.mp3"
    # audio_file_name = f"{yt.title}.mp3"
    video.audio.write_audiofile(audio_file_path)
    st.success("유튜브 오디오 추출 완료!")
    with open(audio_file_path, 'rb') as f:
        audio_file = f.read()
    return audio_file, audio_file_path

# 스크립트 추출 함수
def extract_script(audio_file, whisper_model):
    try:
        model = whisper.load_model(whisper_model)
        result = model.transcribe(audio_file)
        script = result["text"]
        script_file_name = f"{audio_file.name}.txt"
        return script, script_file_name
    except Exception as e:
        print(f"스크립트 추출 과정에서 오류가 발생했습니다: {e}")

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
    st.markdown("유튜브 URL을 넣으면 :blue[동영상], :red[오디오], :green[스크립트]를 내려받을 수 있습니다.")

    # Input for YouTube URL
    yt_url = st.text_input(
        label="유튜브 주소를 넣어주세요.",
        placeholder="ex) https://www.youtube.com/watch?v=nVQY16LgEyU",
        key="yt_url"
    )
    # confirm = st.button("확인")
    
    st.divider()
    
    if yt_url is not None:
        con = st.container()
        with con:
            con.write("동영상(MP4) 내려받기")
            if st.button("동영상(MP4)"):
                with st.spinner("Downloading mp4..."):
                    video_file_content, video_file_name = download_mp4(yt_url)
                    st.success("유튜브 동영상 추출 완료!")
                    st.download_button(
                        label='Download Video', 
                        data=video_file_content, 
                        file_name=video_file_name, 
                        mime='video/mp4'
                        )
        with con:
            con.write("오디오(MP3) 내려받기")
            # 2. MP3 내려받기
            if st.button("오디오(MP3)"):
                with st.spinner("Downloading mp3..."):
                    audio_file, audio_file_path = download_mp3_from_mp4(yt_url)
                    st.audio(audio_file, format='audio/mp3')
                    st.write("오디오 파일을 저장하려면 메뉴(⋮)를 누르고 '다운로드'를 선택하세요.")
        with con:
            con.write("스크립트(TXT) 내려받기")
            # 3. 스크립트 내려받기
            if st.button("스크립트(TXT)"):
                whisper_model = 'medium'
                st.write("model : ", whisper_model)
                print("whisper model : ", whisper_model)
                # 스크립트 추출 실행
                with st.spinner("오디오를 추출합니다..."):
                    print("오디오 추출 시작")
                    audio_file, audio_file_path = download_mp3_from_mp4(yt_url)
                    st.audio(audio_file, format='audio/mp3')
                    st.write("오디오 파일을 저장하려면 메뉴(⋮)를 누르고 '다운로드'를 선택하세요.")
                with st.spinner("스크립트를 추출합니다..."):
                    print("스크립트 추출 시작")
                    model = whisper.load_model(whisper_model)
                    result = model.transcribe(audio_file_path)
                    script = result['text']
                    script_file_name = f"{YouTube(yt_url).title}.txt"
                    st.success("스크립트 추출 완료")
                    print("스크립트 추출 완료")
                st.write(script)
                file_bite = script.encode('utf-8')
                st.download_button(
                        label="Download Script",
                        data=file_bite,
                        file_name=script_file_name,
                        mime='text/plain'
                        )
    else:
        pass
# Main
if __name__ == "__main__":
    yt_app()
