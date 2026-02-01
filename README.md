# YouTube to MP3 Converter

A simple web app that grabs audio from YouTube videos and converts them to MP3s.

## What it does

- Converts YouTube videos to MP3 format (192kbps quality)
- Shows you what's happening while it downloads and converts
- Cleans up old files automatically so your storage doesn't get cluttered
- Works on whatever device you're using
- Has some basic security stuff built in

## What you'll need

- Python 3.8 or newer
- FFmpeg (this is what actually handles the audio conversion)

## Getting it running

Grab the code:

```bash
git clone <repository-url>
cd youtube-mp3-downloader
```

Install FFmpeg (if you don't have it already):

- Windows: Download from ffmpeg.org and add it to your PATH
- Mac: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg` (or `yum` if that's your thing)

Set up Python stuff:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## How to use it

Fire it up:

```bash
python app.py
```

Then just open your browser and go to http://127.0.0.1:5000

Paste in a YouTube link, hit the convert button and download your MP3.

## Tweaking settings

If you want to mess with the config, it's in app.py:

```python
app.config['MAX_DOWNLOADS'] = 10  # how many can run at once
app.config['FILE_RETENTION_HOURS'] = 24  # when to delete old files
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # max file size
```

## The endpoints

These are the endpoints:

- `GET /` - the main page
- `POST /download` - starts a download
- `GET /status/<download_id>` - checks on your download
- `GET /get_file/<download_id>` - grabs your file
- `POST /cleanup` - manually cleans up old files
- `GET /health` - checks if everything's running

## Heads up

This is is just a learning project. Only download stuff you actually have the rights to download. Respect copyright laws and YouTube's rules.

I am not responsible if you use this for something sketchy.

## When stuff goes wrong

- FFmpeg not working? Make sure it's installed and in your PATH.
- Downloads failing? Could be your internet, a bad URL, or the video might be private/region-locked.
- Port's taken? Change it in app.py:

```python
app.run(debug=True, host='127.0.0.1', port=5001)
```

## Running it for real

Development mode (what you've been doing):

```bash
python app.py
```

Production (if you're actually deploying this):

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Contributing

If you want to improve it, go for it.

## License

It's here, use it however you want for learning. (idk what to say here)