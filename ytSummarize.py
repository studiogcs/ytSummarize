import argparse
from pytube import YouTube
import os
from dotenv import load_dotenv
from openai import OpenAI
import soundfile as sf
import librosa
import time
from functools import wraps

# To run with input, execute $ python ytSummarize --url <youtube url>
# Otherwise, include the url in the urls.txt file (format must be "https://www.youtube.com/...")

AUDIO_PATH = "./output-mp3"
CHUNKS_PATH = "./chunks"
TRANSCRIPT_PATH = "./transcripts"
SUMMARY_PATH = "./output-text"
CHUNK_LEN = 10 * 60 # 10 minute segments

load_dotenv()

client = OpenAI()

def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        print(f"Function '{func.__name__}' took {end_time - start_time:.6f} seconds to execute.")
        return result
    return wrapper

def isURL(input):
    if not input.startswith("https:"):
        print("Must be HTTPS.")
        return False
    if "www.youtube.com" not in input:
        print("Not a YouTube URL")
        return False
    return True

def getAudio(url):
    print("Fetching audio...")
    yt = YouTube(url)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path=AUDIO_PATH)
    base, ext = os.path.splitext(out_file)
    new_file = base+'.mp3'
    os.rename(out_file, new_file)
    print(yt.title + " has been successfully downloaded.")
    return new_file, yt.title

def find_audio_files(path, extension=".mp3"):
    """Recursively find all files with extension in path."""
    audio_files = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(extension):
                audio_files.append(os.path.join(root, f))
    return audio_files

def chunk_audio(filename, segment_length: int, output_dir): # segment length in seconds
    print(f"Chunking audio to {segment_length} second segments...")

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    audio_data, sr = librosa.load(filename)
    duration = len(audio_data) / sr
    num_segments = int(duration / segment_length) + 1

    print(f"Chunking {num_segments} chunks...")

    for i in range(num_segments):
        start = i * segment_length * sr
        end = (i + 1) * segment_length * sr
        segment = audio_data[start:end]
        sf.write(os.path.join(output_dir, f"segment_{i}.mp3"), segment, sr)

    chunked_audio_files = find_audio_files(output_dir)
    return sorted(chunked_audio_files)

@timer
def transcribe_audio(audio_files: list, output_file=None, model="whisper-1") -> list:
    print("Converting audio to text...")
    transcripts = []

    for audio_file_path in audio_files:
        with open(audio_file_path, 'rb') as audio_file:
            response = client.audio.transcriptions.create(model=model, file=audio_file, response_format="text")
            transcripts.append(response)

    if output_file is not None:
        with open(output_file, "w") as file:
            for transcript in transcripts:
                file.write(transcript + "\n")

    return transcripts

@timer
def summarize(chunks: list[str], system_prompt: str, model="gpt-3.5-turbo", output_file=None):
    print(f"Summarizing with {model=}")
    summaries = []
    for chunk in chunks:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chunk},
            ],
            temperature=0
        )
        summary = response.choices[0].message.content
        summaries.append(summary)

    if output_file is not None:
        with open(output_file, "w") as file:
            for summary in summaries:
                file.write(summary + "\n")
    
    return summaries

def run(url):
    print('Checking URL:', url)
    try:
        if isURL(url):
            # file_path, filename = getAudio(url)

            filename = "Top Food Tech Trends Transforming the Industry in 2023"
            file_path = os.path.join(AUDIO_PATH, filename + '.mp3')

            # chunked_audio_files = chunk_audio(file_path, segment_length=CHUNK_LEN, output_dir=CHUNKS_PATH)
            
            # transcriptions = transcribe_audio(chunked_audio_files, os.path.join(TRANSCRIPT_PATH, filename+'.txt'))
            
            summarize(
                transcriptions, 
                system_prompt= """You are a helpful assistant that summarizes youtube videos. 
                You are provided chunks of raw audio that were transcribed from the video's audio. 
                Summarize the current chunk to succint and clear bullet points of its contents.
                """, 
                output_file=os.path.join(SUMMARY_PATH, filename+'.txt')
            )
        else:
            print("ERROR: Invalid URL")
    except Exception as e:
        print(e)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize as text the audio from a YouTube video. Input: video url.')
    parser.add_argument('--url', type=str, help='YouTube video URL')
    args = parser.parse_args()
    url = args.url

    if url:
        run(url)
    else:
        with open("urls.txt") as f: 
            for line in f:
                run(line)