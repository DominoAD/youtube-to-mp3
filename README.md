# YouTube to MP3 Converter

A modern, user-friendly web application for converting YouTube videos to high-quality MP3 audio files.

## Features

- **Fast Conversion**: Quick YouTube video to MP3 conversion
- **High Quality**: 192kbps MP3 audio quality
- **Real-time Progress**: Live download and conversion progress tracking
- **Auto-cleanup**: Automatically removes files after 24 hours
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Security**: Input validation, rate limiting, and secure file handling

## Requirements

- Python 3.8+
- FFmpeg (required for audio conversion)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd youtube-mp3-downloader
   ```

2. **Install FFmpeg**:
   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt install ffmpeg` or `sudo yum install ffmpeg`

3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

4. **Activate the virtual environment**:
   - **Windows**: `venv\Scripts\activate`
   - **macOS/Linux**: `source venv/bin/activate`

5. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. **Start the application**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://127.0.0.1:5000
   ```

3. **Convert videos**:
   - Paste a YouTube URL into the input field
   - Click "Convert to MP3"
   - Wait for the conversion to complete
   - Download your MP3 file

## Configuration

You can modify settings in `app.py`:

```python
app.config['MAX_DOWNLOADS'] = 10  # Maximum concurrent downloads
app.config['FILE_RETENTION_HOURS'] = 24  # How long to keep files
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # Max file size
```

## API Endpoints

- `GET /` - Main application page
- `POST /download` - Start a new download
- `GET /status/<download_id>` - Check download status
- `GET /get_file/<download_id>` - Download the converted file
- `POST /cleanup` - Manual cleanup of old files
- `GET /health` - Health check endpoint

## Security Features

- URL validation to ensure only YouTube URLs are processed
- UUID-based download IDs to prevent unauthorized access
- Thread-safe download status management
- File retention limits
- Rate limiting for concurrent downloads
- Input sanitization and XSS protection

## Legal Disclaimer

**Important**: This tool is for educational purposes only. Users must:
- Only download content they own or have permission to download
- Respect copyright laws and YouTube's Terms of Service
- Comply with all applicable local, state, and federal laws

The developers are not responsible for any misuse of this application.

## Troubleshooting

### FFmpeg not found
Ensure FFmpeg is installed and added to your system PATH.

### Download fails
- Check your internet connection
- Verify the YouTube URL is valid and accessible
- Ensure the video is not private or region-locked

### Port already in use
Change the port in `app.py`:
```python
app.run(debug=True, host='127.0.0.1', port=5001)  # Change 5000 to another port
```

## Development

To run in development mode with debug enabled:
```bash
python app.py
```

For production deployment, use a production WSGI server like Gunicorn:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is provided as-is for educational purposes.
