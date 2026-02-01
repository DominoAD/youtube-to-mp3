# YouTube MP3 Downloader & Voice Cleaner

A Flask web application that converts YouTube videos to MP3 files and includes a powerful voice isolation tool that strips background noise, rain, and white noise from audio files.

## Features

### YouTube to MP3 Converter
- Convert YouTube videos to high-quality MP3 files (192kbps)
- Fast conversion and download
- Progress tracking
- Automatic file cleanup after 24 hours
- Support for various YouTube URL formats

### Voice Isolation Tool
- **Remove Background Noise**: Strips constant background noise like rain, wind, air conditioning, and hiss
- **Frequency Filtering**: Isolates human voice frequencies (80-3000 Hz)
- **Harmonic Enhancement**: Uses harmonic-percussive separation to emphasize voice
- **Smart Processing**: AI-based noise reduction algorithms
- **High Quality Output**: Maintains voice quality while removing unwanted audio

## How It Works

### Voice Cleaning Technology

The voice cleaner uses a multi-stage processing pipeline:

1. **Noise Reduction**: Uses spectral gating and statistical noise profiling to remove constant background noise
2. **Bandpass Filtering**: Isolates the frequency range where human voice resides (80-3000 Hz)
3. **Harmonic-Percussive Separation**: Separates harmonic components (voice) from percussive sounds (noise)
4. **Normalization**: Adjusts audio levels for consistent output

## Installation

1. **Install Python** (3.8 or higher)

2. **Install FFmpeg** (required for audio processing):
   - Download from: https://ffmpeg.org/download.html
   - Add to system PATH

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Start the Application

```bash
python app.py
```

The app will be available at: http://127.0.0.1:5000

### YouTube to MP3 Conversion

1. Copy a YouTube video URL
2. Paste it in the input field
3. Click "Convert to MP3"
4. Wait for the conversion to complete
5. Download your MP3 file

### Voice Cleaning

1. Click "Select MP3 File" in the Voice Isolation Tool section
2. Choose an MP3 file from your computer (max 100MB)
3. Click "Clean Voice"
4. Wait for processing (usually 10-30 seconds depending on file size)
5. Download the cleaned MP3 file

## Command Line Usage

You can also use the voice cleaner directly from the command line:

```bash
python mp3_cleaner.py input_file.mp3 output_file.mp3
```

Or let it auto-generate the output filename:

```bash
python mp3_cleaner.py input_file.mp3
# Creates: input_file_cleaned.mp3
```

## Technical Details

### Libraries Used

- **Flask**: Web framework
- **yt-dlp**: YouTube video downloading
- **librosa**: Audio analysis and processing
- **noisereduce**: Advanced noise reduction
- **soundfile**: Audio file I/O
- **pydub**: Audio format conversion
- **NumPy**: Numerical processing

### Audio Processing Pipeline

```
Input MP3
    ↓
Load & Decode (librosa)
    ↓
Noise Reduction (noisereduce)
    ↓
Bandpass Filter (80-3000 Hz)
    ↓
Harmonic-Percussive Separation
    ↓
Normalize Audio Levels
    ↓
Export to MP3 (pydub)
    ↓
Output Cleaned MP3
```

## Best Results

The voice cleaner works best with:
- Recordings with consistent background noise (rain, white noise, fan noise)
- Clear voice recordings with single speakers
- Audio where voice is louder than background noise

Less effective with:
- Multiple overlapping voices
- Music with vocals (will remove instruments)
- Highly variable/unpredictable background noise

## Limitations

- Maximum file size: 100MB for uploads
- Processing time depends on file duration (typically 0.5x to 1x realtime)
- Files are automatically deleted after 24 hours

## Security & Privacy

- All uploaded files are processed locally on the server
- Files are automatically deleted after 24 hours
- No audio data is stored permanently
- No data is shared with third parties

## Troubleshooting

### Voice cleaner not working?

1. **Check FFmpeg installation**: Run `ffmpeg -version` in terminal
2. **File too large**: Ensure MP3 is under 100MB
3. **Format issues**: Ensure file is MP3 format

### Downloads failing?

1. Check your internet connection
2. Verify the YouTube URL is valid and video is accessible
3. Some videos may be region-restricted

## License

Educational purposes only. Always respect copyright laws and YouTube's Terms of Service.

## Disclaimer

This tool is for educational purposes. Only download content you own or have permission to download. The voice cleaner should be used ethically and in compliance with applicable laws.
