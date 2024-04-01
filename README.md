# ytSummarize
Python script to extract text summaries from YouTube videos. 

## How to run
Go to root directory. In terminal, activate the virtual environment and run:

    $ source .venv/bin/activate
    $ python ytSummarize.py --url <video url>

Note: You can run without the optional input argument. If so, the script will look for video URLs in the urls.txt file. 

The forma *must* be: "https://www.youtube.com/..."

## Output

Audio files will be saved as .mp3 in the `output-mp3` folder. 

Text summaries will be saved in the `output-txt` folder. 