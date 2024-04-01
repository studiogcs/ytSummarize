# ytSummarize
Python script to extract text summaries from YouTube videos. 

The script performs the following steps: Starting with a URL, it will 1) download the audio as mp3 from YouTube; 2) transcribe the entire audio file; 3) split the file into 10min chunks and generate summaries for each; 4) join the summaries into a single file. 

## Setup

The following must be created in the root directory:

Output file directories - as the script runs, it will place the output of each phase in the following folders.

- `audio`: stores output .mp3 files
- `chunks`: stores individual chunks of the processed .mp3 file
- `summary`: stores a file containing the concatenated summaries for all the chunks, as well as a single file that combines all chunks into a single coherent .txt
- `transcript`: stores the transcript of the entire audio file

You should also set up the following files:

- `.env`: you will need to add the following environment variables.
    - `OPENAI_API_KEY=<your key>`
    - `DEBUG`: if True, the script will look at urls in `urls.local.txt`;
    - `OVERWRITE_AUDIO`: if False, the script will skip to transcription unless the file has not been created yet;
    - `OVERWRITE_TRANSCRIPTION`: if False, the script will skip to summary, unless the file has not been created yet;
    - `OVERWRITE_SUMMARY`: if False, the script will not perform summary, unless the file has not been created yet.
- `urls.local.txt`: this file is the same as `urls.txt` but for when `DEBUG`is set to True. The format *must* be "https://www.youtube.com/...". You can include multiple urls, line by line. 

## How to run
Go to the root directory and create a virtual environment via .venv directory. In terminal, activate the virtual environment and run:

    $ source .venv/bin/activate
    $ python ytSummarize.py --url <video url>

Note: You can run without the optional input argument. If so, the script will look for video URLs in the urls.txt (or urls.local.txt) file. 

Note: If you already ran the process, and therefore already have output files with a given FILENAME, you can edit the .env file to include the DEBUG_FILENAME. The script will check which files already exist in the output folders; if they exist already, it skips to the next step.

## Customization

You can adjust the `SUMMARY_PROMPT` global at the top of the script to your needs.  