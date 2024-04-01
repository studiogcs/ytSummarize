import argparse
from pytube import YouTube
import os
from dotenv import load_dotenv
from openai import OpenAI
import soundfile as sf
import librosa
import time
from functools import wraps
from distutils.util import strtobool

# ------------------------------------------------------------------------------------------------
# PROMPT ENGINEERING
# ------------------------------------------------------------------------------------------------

# Generic prompt: 
# SUMMARY_PROMPT = """You are a helpful assistant that summarizes youtube videos. 
#                 You are provided chunks of raw audio that were transcribed from the video's audio. 
#                 Summarize the current chunk to succint and clear bullet points of its contents.
#                 """

# Custom prompt:
SUMMARY_PROMPT = """You are a helpful assistant that summarizes youtube videos. 
                You are provided chunks of raw audio that were transcribed from the video's audio. 
                Summarize the current chunk, and make bulleted lists for each of the following, with brief descriptions:
                1. names of organizations, startups, or companies; 2. the names of innovative technology solutions and projects; 
                3. added value and benefits provided by these technologies to specific stakeholders.
                """

# ------------------------------------------------------------------------------------------------
# SETUP
# ------------------------------------------------------------------------------------------------
load_dotenv()

DEBUG = bool(strtobool(os.getenv('DEBUG')))
OVERWRITE_AUDIO = bool(strtobool(os.getenv('OVERWRITE_AUDIO')))
OVERWRITE_TRANSCRIPTION = bool(strtobool(os.getenv('OVERWRITE_TRANSCRIPTION')))
OVERWRITE_SUMMARY = bool(strtobool(os.getenv('OVERWRITE_SUMMARY')))

if DEBUG:
    URLS_PATH = "urls.local.txt"
else:
    URLS_PATH = "urls.txt"

AUDIO_PATH = "./audio"
CHUNKS_PATH = "./chunks"
TRANSCRIPT_PATH = "./transcript"
SUMMARY_PATH = "./summary"
CHUNK_LEN = 10 * 60 # 10 minute segments

client = OpenAI()

# ------------------------------------------------------------------------------------------------
# FUNCTIONS
# ------------------------------------------------------------------------------------------------
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
    yt = YouTube(url)

    output_file = yt.title+'.mp3'

    if OVERWRITE_AUDIO or output_file not in os.listdir(os.path.join(AUDIO_PATH)):
        print("Fetching audio...")
        video = yt.streams.filter(only_audio=True).first()
        out_file = video.download(output_path=AUDIO_PATH)
        base, ext = os.path.splitext(out_file)
        new_file = base+'.mp3'
        os.rename(out_file, new_file)
        print(yt.title + " has been successfully downloaded.")
    
    return yt.title

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
        sf.write(os.path.join(output_dir, f"{filename}_segment_{i}.mp3"), segment, sr)

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
def summarize(path, filename, system_prompt: str, output_file, model="gpt-3.5-turbo"):
    print(f"Summarizing with {model=}...")

    if filename in os.listdir(path):
        with open(os.path.join(path, filename)) as chunks:
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

            print("Generating summaries for each prompt...")
            full_text = ''
            with open(output_file + "_summaries", "w") as file:
                for summary in summaries:
                    file.write(summary + "\n")
                    full_text = full_text + summary + "\n"
            
            print("Combining into a single summary...")
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": f"This text contains multiple chatGPT speech-to-text summaries, each one corresponding to a chunk of the same audio file. Please combine these summaries into one coeherent text, without losing the original format: keep using bulleted lists and keep the same division of topics. Do not lose information by summarizing further."},
                    {"role": "user", "content": full_text},
                ],
                temperature=0
            )
            summary = response.choices[0].message.content
            with open(output_file, "w") as file:
                file.write(summary + "\n")

def run(url=None):
    try:
        print('Checking URL:', url)
        if isURL(url):
            filename = getAudio(url)
                
            audio_output_file_path = os.path.join(AUDIO_PATH, filename + '.mp3')
            transcript_output_file_path = os.path.join(TRANSCRIPT_PATH, filename+'.txt')
            summary_output_file_path = os.path.join(SUMMARY_PATH, filename+'.txt')

            if OVERWRITE_TRANSCRIPTION or not transcript_output_file_path.split('/')[-1] in os.listdir(TRANSCRIPT_PATH):
                chunked_audio_files = chunk_audio(audio_output_file_path, segment_length=CHUNK_LEN, output_dir=CHUNKS_PATH)
                transcribe_audio(
                    audio_files=chunked_audio_files, 
                    output_file=transcript_output_file_path,
                )
            
            if OVERWRITE_SUMMARY or not summary_output_file_path.split('/')[-1] in os.listdir(SUMMARY_PATH):
                summarize(
                    path=TRANSCRIPT_PATH,
                    filename=filename+'.txt', 
                    output_file=summary_output_file_path,
                    system_prompt=SUMMARY_PROMPT,
                )
    except Exception as e:
        print(e)

# ------------------------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Summarize as text the audio from a YouTube video. Input: video url.')
    parser.add_argument('--url', type=str, help='YouTube video URL')
    args = parser.parse_args()
    url = args.url

    if url:
        run(url=url)
    else:
        with open(URLS_PATH) as f: 
            for line in f:
                run(url=line)