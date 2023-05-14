from pytube import YouTube
import whisper
import streamlit as st
import requests
from datetime import datetime, timedelta
from moviepy.editor import VideoFileClip

BASE_FOLDER = "/Users/asadal/Downloads/"

# Today String
datetime_utc = datetime.utcnow()
datetime_kst = datetime_utc + timedelta(hours=9)
today = datetime_kst.today().date().strftime('%Y.%m.%d')

# 유튜브 동영상 다운로드
def download_mp4(yt_url):
    yt = YouTube(yt_url)
    stream = yt.streams.get_highest_resolution()
    print("stream : ", stream)
    print("stream.url : ", stream.url)
    video_file_content = requests.get(stream.url).content
    print("video_file_content_type : ", type(video_file_content))
    video_file_name = f"{yt.title}.mp4"
    # stream.download(BASE_FOLDER +  video_file_name)
    # print("Downloaded File: ", BASE_FOLDER +  video_file_name)
    return video_file_content, video_file_name

# mp3 추출 함수
def download_mp3_from_mp4(yt_url):
    yt = YouTube(yt_url)
    stream = yt.streams.get_highest_resolution()
    stream.download(BASE_FOLDER, filename=f"{yt.title}.mp4")
    video_file_path = BASE_FOLDER + f"{yt.title}.mp4"
    video = VideoFileClip(video_file_path)
    audio_file_path = BASE_FOLDER + f"{yt.title}.mp3"
    audio_file_name = f"{yt.title}.mp3"
    video.audio.write_audiofile(audio_file_path)
    st.success("유튜브 오디오 저장 완료!")
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
        # with open(script_file_name, "w", encoding="utf-8") as f:
        #     f.write(script)
        # with open(script_file_name, "rb") as f:
        #     script_file_content = f.read()
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
    confirm = st.button("확인")
    
    st.divider()
    
    # st.write(st.session_state['yt_url'])
    # if st.session_state("yt_url") and confirm:
    
    # if confirm:
    con = st.container()
    with con:
        con.write("동영상(MP4) 내려받기")
        if st.button("동영상(MP4)"):
            with st.spinner("Downloading mp4..."):
                video_file_content, video_file_name = download_mp4(yt_url)
                st.success("유튜브 동영상 추출 완료!")
                # video_file = open(video_file_content, 'rb')
                # video_bytes = video_file.read()
                # st.video(video_byte
                # mp4 다운로드
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
    with con:
        con.write("스크립트(TXT) 내려받기")
        # 3. 스크립트 내려받기
        if st.button("스크립트(TXT)"):
            whisper_model = 'base'
            st.write("model : ", whisper_model)
            print("whisper model : ", whisper_model)
            # 스크립트 추출 실행
            with st.spinner("오디오를 추출합니다..."):
                print("오디오 추출 시작")
                audio_file, audio_file_path = download_mp3_from_mp4(yt_url)
            with st.spinner("스크립트를 추출합니다..."):
                print("스크립트 추출 시작")
                audio_file_path = BASE_FOLDER + YouTube(yt_url).title + ".mp3"
                model = whisper.load_model(whisper_model)
                result = model.transcribe(audio_file_path)
                script = result['text']
                script_file_name = f"{YouTube(yt_url).title}.txt"
                # script, script_file_name = extract_script(audio_file_path, whisper_model)
                # time.sleep(30)
                # st.write("스크립트 추출에 시간이 걸리고 있습니다. 오류가 뜨지 않는다면 인내심을 갖고 기다려주세요.🙏")
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
# Main
if __name__ == "__main__":
    yt_app()
