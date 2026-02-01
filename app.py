"""
┌─────────────────────────────────────────────────────────┐
│ YOUTUBE MP3 DOWNLOADER - FLASK APPLICATION              │
│ Author:  Aidan                                          │
│ Created: 2026-01-29                                     │
│ Updated: 2026-02-01                                     │
│ Version: 3.0                                            │
│ Features: YouTube to MP3 converter                      │
│                                                         │
│ I built this Flask app to download YouTube videos       │
│ and convert them to MP3 format.                         │
│                                                         │
│ I implemented:                                          │
│ - Multi-threaded downloads so I can handle multiple     │
│   videos at once                                        │
│ - Real-time progress tracking so users know what's      │
│   happening                                             │
│ - Automatic cleanup to delete old files after 24 hours  │
│ - Concurrent download limits to protect the server      │
└─────────────────────────────────────────────────────────┘
"""

# ===== IMPORTS =====
# I use Flask for the web server and routing
from flask import Flask, render_template, request, send_file, jsonify

# I use yt-dlp to download YouTube videos
import yt_dlp

# I use these for various utilities
import os
import uuid
import threading
import time
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from threading import Lock

# ===== LOGGING CONFIGURATION =====
# I set up logging so I can track what's happening in the app
# Logs include timestamps, severity levels, and detailed messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== FLASK APPLICATION INITIALIZATION =====
# Initialize Flask app and configure settings
app = Flask(__name__)

# Configure folder paths for file storage
app.config['DOWNLOAD_FOLDER'] = 'downloads'  # Store converted MP3 files
app.config['UPLOAD_FOLDER'] = 'uploads'      # Store user uploaded files for cleaning

# Set maximum file size to prevent memory issues (500MB)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

# Limit concurrent downloads to prevent server overload
app.config['MAX_DOWNLOADS'] = 10

# Automatically delete files after 24 hours for privacy and disk space
app.config['FILE_RETENTION_HOURS'] = 24

# Generate secure secret key for session management
# Uses environment variable if available, otherwise creates random key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))

# Only allow MP3 files for upload to prevent malicious file types
app.config['ALLOWED_EXTENSIONS'] = {'mp3'}

# ===== DIRECTORY SETUP =====
# Ensure required directories exist before starting application
# Creates directories if they don't exist, no error if already present
Path(app.config['DOWNLOAD_FOLDER']).mkdir(exist_ok=True)
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)

# ===== GLOBAL STATE MANAGEMENT =====
# Thread-safe storage for tracking download and processing status
# Keys are UUIDs, values are status dictionaries with progress info
download_status = {}      # Tracks YouTube download progress
status_lock = Lock()      # Ensures thread-safe access to status dictionaries


# ===== UTILITY FUNCTIONS =====

def allowed_file(filename):
    """
    Validate file extension for security
    
    Checks if uploaded file has an allowed extension (.mp3 only).
    Prevents users from uploading potentially malicious file types.
    
    Args:
        filename (str): Name of file to check
        
    Returns:
        bool: True if file extension is allowed, False otherwise
        
    Logic:
        1. Check if filename contains a dot (has extension)
        2. Split filename at last dot to get extension
        3. Convert extension to lowercase for case-insensitive comparison
        4. Check if extension is in ALLOWED_EXTENSIONS set
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def validate_youtube_url(url):
    """
    Validate and parse YouTube URLs
    
    Supports multiple YouTube URL formats and extracts the video ID.
    This ensures we only process valid YouTube links and prevents
    injection attacks or malformed URLs from causing issues.
    
    Args:
        url (str): YouTube URL to validate
        
    Returns:
        tuple: (is_valid: bool, video_id: str or None)
            - is_valid: True if URL matches YouTube pattern
            - video_id: 11-character YouTube video ID or None
            
    Supported URL formats:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        - All formats work with or without https:// and www.
        
    Logic:
        1. Check if URL exists (not empty)
        2. Try matching against 4 different YouTube URL patterns
        3. Extract 11-character video ID from matched pattern
        4. Return validation result and video ID
    """
    if not url:
        return False, None
    
    # Pattern 1: Standard watch URL - youtube.com/watch?v=VIDEO_ID
    pattern1 = r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})'
    # Pattern 2: Short URL - youtu.be/VIDEO_ID
    pattern2 = r'(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})'
    # Pattern 3: Embed URL - youtube.com/embed/VIDEO_ID
    pattern3 = r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})'
    # Pattern 4: Old style - youtube.com/v/VIDEO_ID
    pattern4 = r'(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})'
    
    # Try each pattern until we find a match
    for pattern in [pattern1, pattern2, pattern3, pattern4]:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)  # Extract the video ID from the regex group
            return True, video_id
    
    # No patterns matched - invalid URL
    return False, None


def get_active_downloads():
    """
    Count currently running downloads
    
    Checks the download_status dictionary to count how many downloads
    are currently in progress. Used to enforce concurrent download limits.
    
    Returns:
        int: Number of active downloads
        
    Logic:
        1. Acquire thread lock to safely read shared state
        2. Iterate through all download statuses
        3. Count entries with status='downloading'
        4. Release lock and return count
        
    Thread Safety:
        Uses status_lock to prevent race conditions when reading
        the shared download_status dictionary.
    """
    with status_lock:
        # Sum up all downloads that currently have 'downloading' status
        return sum(1 for status in download_status.values() 
                   if status.get('status') == 'downloading')


def download_mp3(video_url, download_id):
    """
    Download YouTube video and convert to MP3 audio
    
    This is the main download worker function that runs in a separate thread.
    It handles downloading the YouTube video and converting to MP3 format.
    Updates download_status dictionary with progress information.
    
    Args:
        video_url (str): Full YouTube URL to download
        download_id (str): Unique UUID for tracking this download
        
    Status Updates:
        - 'downloading' (0-100%): Downloading and converting video
        - 'completed' (100%): Ready for download
        - 'error': Something went wrong
        
    Logic Flow:
        1. Configure yt-dlp with optimal settings for audio extraction
        2. Extract video metadata (title, duration) before downloading
        3. Validate video duration (max 10 hours to prevent abuse)
        4. Download video and extract audio with progress tracking
        5. Convert to MP3 at 192kbps quality
        6. Update status to completed with file information
        7. Handle any errors and update status accordingly
        
    Thread Safety:
        All status updates use status_lock to prevent race conditions.
    """
    try:
        # ===== CONFIGURE YT-DLP OPTIONS =====
        # Set up yt-dlp with optimal settings for audio extraction
        ydl_opts = {
            # Request best quality audio stream available
            'format': 'bestaudio/best',
            
            # Post-processing: Extract and convert audio to MP3
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',    # Use FFmpeg for audio extraction
                'preferredcodec': 'mp3',         # Convert to MP3 format
                'preferredquality': '192',       # 192 kbps bitrate (good quality/size balance)
            }],
            
            # Output file template: saves as {download_id}.mp3 in downloads folder
            'outtmpl': f'{app.config["DOWNLOAD_FOLDER"]}/{download_id}.%(ext)s',
            
            # Suppress console output for cleaner logs
            'quiet': True,
            'no_warnings': True,
            
            # Audio extraction flags
            'extract_audio': True,
            
            # Prevent downloading entire playlists (only single video)
            'noplaylist': True,
            
            # No age restrictions
            'age_limit': None,
            
            # Timeout for socket connections (prevents hanging)
            'socket_timeout': 30,
            
            # Bypass YouTube restrictions using mobile client
            # This helps with videos that have playback limitations
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],  # Try Android client first
                    'player_skip': ['webpage', 'configs'], # Skip slow webpage parsing
                }
            },
        }
        
        # ===== INITIALIZE DOWNLOAD STATUS =====
        # Set initial status so frontend can start tracking progress
        with status_lock:
            download_status[download_id] = {'status': 'downloading', 'progress': 0}
        
        # ===== EXTRACT VIDEO METADATA =====
        # Get video information before downloading to validate and display to user
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Extracting info for download {download_id[:8]}")
            
            # Extract video metadata without downloading (download=False)
            info = ydl.extract_info(video_url, download=False)
            title = info.get('title', 'Unknown')  # Video title for display
            duration = info.get('duration', 0)    # Duration in seconds
            
            # ===== VALIDATE VIDEO DURATION =====
            # Reject videos longer than 10 hours to prevent abuse and excessive processing
            # 10 hours = 36000 seconds
            if duration > 36000:
                with status_lock:
                    download_status[download_id] = {
                        'status': 'error',
                        'error': 'Video is too long (max 10 hours)'
                    }
                logger.warning(f"Download {download_id[:8]} rejected: video too long ({duration}s)")
                return
            
            with status_lock:
                download_status[download_id]['title'] = title
                download_status[download_id]['duration'] = duration
            
            # Download with progress tracking
            def progress_hook(d):
                if d['status'] == 'downloading':
                    total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        progress = (downloaded / total) * 100
                        with status_lock:
                            if download_id in download_status:
                                download_status[download_id]['progress'] = round(progress, 2)
            
            ydl_opts['progress_hooks'] = [progress_hook]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_with_hooks:
                logger.info(f"Starting download {download_id[:8]}")
                ydl_with_hooks.download([video_url])
        
        with status_lock:
            download_status[download_id] = {
                'status': 'completed',
                'progress': 100,
                'filename': f'{download_id}.mp3',
                'title': title,
                'completed_at': datetime.now().isoformat()
            }
        
        logger.info(f"Download {download_id[:8]} completed successfully")
        
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if 'Video unavailable' in error_msg:
            error_msg = 'Video is unavailable or private'
        elif 'This video is not available' in error_msg:
            error_msg = 'Video not available in your region'
        else:
            error_msg = 'Failed to download video'
        
        with status_lock:
            download_status[download_id] = {
                'status': 'error',
                'error': error_msg
            }
        logger.error(f"Download {download_id[:8]} failed: {error_msg}")
        
    except Exception as e:
        with status_lock:
            download_status[download_id] = {
                'status': 'error',
                'error': 'An unexpected error occurred'
            }
        logger.error(f"Download {download_id[:8]} unexpected error: {str(e)}", exc_info=True)


# ===== ROUTE HANDLERS =====

@app.route('/')
def index():
    """
    Main page route
    
    Renders the index.html template which contains the full web interface.
    This is the entry point for users accessing the application.
    
    Returns:
        HTML: Rendered index page with converter interface
    """
    return render_template('index.html')


@app.route('/download', methods=['POST'])
def download():
    """
    Initialize YouTube to MP3 download
    
    Accepts YouTube URL from frontend. Validates URL, checks server capacity, 
    and starts download in background thread.
    
    Form Data:
        url (str): YouTube video URL to download
        
    Returns:
        JSON: {"download_id": "uuid"} on success
        JSON: {"error": "message"} on failure with appropriate HTTP status
        
    Status Codes:
        200: Download started successfully
        400: Invalid request (missing URL or invalid format)
        429: Too many concurrent downloads (server busy)
        500: Internal server error
        
    Logic:
        1. Extract and validate YouTube URL from form data
        2. Check if server has capacity for another download
        3. Generate unique UUID for tracking this download
        4. Start download in background thread
        5. Return download ID to frontend for status checking
    """
    try:
        video_url = request.form.get('url', '').strip()
        
        if not video_url:
            return jsonify({'error': 'URL is required'}), 400
        
        # Validate YouTube URL
        is_valid, video_id = validate_youtube_url(video_url)
        if not is_valid:
            return jsonify({'error': 'Please enter a valid YouTube URL'}), 400
        
        # Check concurrent download limit
        active_downloads = get_active_downloads()
        if active_downloads >= app.config['MAX_DOWNLOADS']:
            return jsonify({'error': 'Server is busy. Please try again later.'}), 429
        
        # Generate unique ID for this download
        download_id = str(uuid.uuid4())
        
        # Start download in background thread
        thread = threading.Thread(
            target=download_mp3,
            args=(video_url, download_id),
            daemon=True  # Thread will terminate when main program exits
        )
        thread.start()
        
        logger.info(f"Started download {download_id[:8]} for video {video_id}")
        return jsonify({'download_id': download_id})
    
    except Exception as e:
        logger.error(f"Download endpoint error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/status/<download_id>')
def check_status(download_id):
    """
    Check download progress and status
    
    Returns current status of a download including progress percentage,
    video title, and completion state. Frontend polls this endpoint
    every second to update the progress bar.
    
    Args:
        download_id (str): UUID of the download to check
        
    Returns:
        JSON: Status object with fields:
            - status: 'downloading', 'cleaning', 'completed', 'error', 'not_found'
            - progress: 0-100 percentage (if applicable)
            - title: Video title (if available)
            - error: Error message (if status is 'error')
            
    Status Codes:
        200: Status retrieved successfully
        400: Invalid UUID format
        500: Internal server error
        
    Thread Safety:
        Uses status_lock when reading download_status to prevent race conditions.
    """
    try:
        # Validate UUID format to prevent injection attacks
        uuid.UUID(download_id)
        
        with status_lock:
            status = download_status.get(download_id, {'status': 'not_found'})
        
        return jsonify(status)
    
    except ValueError:
        return jsonify({'status': 'invalid_id'}), 400
    except Exception as e:
        logger.error(f"Status check error: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'error': 'Status check failed'}), 500


@app.route('/get_file/<download_id>')
def get_file(download_id):
    """
    Serve completed MP3 file to user
    
    Validates download is complete, then sends the MP3 file to the user's browser.
    Uses the original video title for a friendly filename. Triggers cleanup
    of old files in background after serving.
    
    Args:
        download_id (str): UUID of the completed download
        
    Returns:
        File: MP3 audio file with appropriate headers for download
        JSON: {"error": "message"} on failure
        
    Status Codes:
        200: File sent successfully
        400: Invalid download ID format
        404: Download not found or not completed
        500: Internal server error
        
    Logic:
        1. Validate download ID is a valid UUID
        2. Check download status is 'completed'
        3. Verify file exists on disk
        4. Sanitize video title for safe filename
        5. Send file with proper MIME type and download headers
        6. Trigger background cleanup of old files
        
    Security:
        - Only serves files from designated download folder
        - Sanitizes filename to prevent directory traversal
        - Validates UUIDs to prevent path injection
    """
    try:
        # Validate UUID format
        uuid.UUID(download_id)
        
        with status_lock:
            status = download_status.get(download_id)
        
        if not status or status.get('status') != 'completed':
            return jsonify({'error': 'File not ready or not found'}), 404
        
        filename = f'{download_id}.mp3'
        filepath = os.path.join(app.config['DOWNLOAD_FOLDER'], filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'File not found'}), 404
        
        # Get original title for better filename
        title = status.get('title', 'download')
        # Sanitize title for filename
        safe_title = re.sub(r'[^\w\s-]', '', title)
        safe_title = re.sub(r'[-\s]+', '-', safe_title)[:50]
        download_name = f"{safe_title}.mp3" if safe_title else "download.mp3"
        
        logger.info(f"Serving file {download_id[:8]}")
        
        # Schedule cleanup for old files
        threading.Thread(target=cleanup_old_files, daemon=True).start()
        
        return send_file(
            filepath, 
            as_attachment=True, 
            download_name=download_name,
            mimetype='audio/mpeg'
        )
    
    except ValueError:
        return jsonify({'error': 'Invalid download ID'}), 400
    except Exception as e:
        logger.error(f"File serve error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Failed to serve file'}), 500


def cleanup_old_files(max_age_hours=None):
    """
    Remove old MP3 files to free disk space
    
    Scans download folder and deletes files older than the specified age.
    Also cleans up associated status entries. Runs automatically every hour
    and after each file download to maintain disk space.
    
    Args:
        max_age_hours (int, optional): Maximum file age in hours
            Defaults to FILE_RETENTION_HOURS (24) if not specified
            
    Returns:
        int: Number of files successfully deleted
        
    Logic:
        1. Calculate cutoff timestamp (now - max_age_hours)
        2. Scan all MP3 files in download folder
        3. Check each file's modification time
        4. Delete files older than cutoff
        5. Remove corresponding status entries
        6. Log cleanup results
        
    Privacy:
        Automatically deletes user files after 24 hours to protect privacy
        and comply with data retention policies.
        
    Disk Management:
        Prevents disk from filling up with forgotten downloads.
    """
    if max_age_hours is None:
        max_age_hours = app.config['FILE_RETENTION_HOURS']
    
    try:
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for file in Path(app.config['DOWNLOAD_FOLDER']).glob('*.mp3'):
            if file.is_file():
                file_time = datetime.fromtimestamp(file.stat().st_mtime)
                if file_time < cutoff_time:
                    try:
                        file_id = file.stem
                        file.unlink()
                        
                        # Clean up status entry if exists
                        with status_lock:
                            download_status.pop(file_id, None)
                        
                        cleaned_count += 1
                        logger.info(f"Cleaned up old file: {file_id[:8]}")
                    except Exception as e:
                        logger.error(f"Failed to cleanup file {file.name}: {str(e)}")
        
        if cleaned_count > 0:
            logger.info(f"Cleanup completed: removed {cleaned_count} file(s)")
        
        return cleaned_count
    
    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}", exc_info=True)
        return 0


@app.route('/cleanup', methods=['POST'])
def cleanup():
    """Manual cleanup endpoint"""
    try:
        cleaned = cleanup_old_files(1)  # Clean files older than 1 hour
        return jsonify({
            'message': 'Cleanup completed',
            'files_removed': cleaned
        })
    except Exception as e:
        logger.error(f"Manual cleanup error: {str(e)}", exc_info=True)
        return jsonify({'error': 'Cleanup failed'}), 500




@app.route('/health')
def health():
    """
    Health check endpoint for monitoring
    
    Returns server status and current capacity information.
    Useful for load balancers, monitoring systems, and debugging.
    
    Returns:
        JSON: {
            "status": "ok",
            "active_downloads": int,  # Current number of downloads
            "max_downloads": int      # Maximum allowed downloads
        }
        
    Status Code:
        200: Always returns 200 if server is running
        
    Use Cases:
        - Load balancer health checks
        - Monitoring dashboard display
        - Debugging server capacity issues
        - Rate limiting decisions
    """
    active_downloads = get_active_downloads()
    return jsonify({
        'status': 'ok',
        'active_downloads': active_downloads,
        'max_downloads': app.config['MAX_DOWNLOADS']
    })


# ===== ERROR HANDLERS =====

@app.errorhandler(413)
def request_entity_too_large(error):
    """
    Handle file upload size limit exceeded
    
    Triggered when uploaded file exceeds MAX_CONTENT_LENGTH (500MB).
    Returns user-friendly error message instead of default Flask error.
    
    Args:
        error: Flask error object (unused)
        
    Returns:
        JSON: {"error": "File too large"}
        
    Status Code:
        413: Payload Too Large
    """
    return jsonify({'error': 'File too large'}), 413


@app.errorhandler(500)
def internal_error(error):
    """
    Handle internal server errors
    
    Catches unhandled exceptions and returns user-friendly error.
    Logs full error details for debugging while hiding sensitive
    information from users.
    
    Args:
        error: Flask error object with exception details
        
    Returns:
        JSON: {"error": "Internal server error"}
        
    Status Code:
        500: Internal Server Error
        
    Security:
        Logs detailed error but returns generic message to users
        to prevent information disclosure.
    """
    logger.error(f"Internal server error: {str(error)}", exc_info=True)
    return jsonify({'error': 'Internal server error'}), 500



# ===== BACKGROUND TASKS =====

def periodic_cleanup():
    """
    Background thread for automatic file cleanup
    
    Runs continuously in a daemon thread, executing cleanup every hour.
    Ensures old files are removed even if users don't manually download,
    preventing disk from filling up and maintaining user privacy.
    
    Logic:
        1. Sleep for 1 hour (3600 seconds)
        2. Call cleanup_old_files() to remove expired files
        3. Handle any errors without crashing the thread
        4. Repeat indefinitely
        
    Thread Type:
        Daemon thread - terminates automatically when main app exits.
        Does not prevent graceful shutdown.
        
    Error Handling:
        Catches and logs exceptions to prevent thread death from
        transient errors (disk full, permission issues, etc.)
    """
    while True:
        time.sleep(3600)  # Wait 1 hour between cleanups
        try:
            cleanup_old_files()
        except Exception as e:
            logger.error(f"Periodic cleanup failed: {str(e)}", exc_info=True)


# ===== APPLICATION ENTRY POINT =====

if __name__ == '__main__':
    """
    Main application startup
    
    Initializes the application, starts background cleanup thread,
    and runs the Flask development server.
    
    Configuration:
        - Debug mode: Enabled for development (auto-reload on code changes)
        - Host: 127.0.0.1 (localhost only, not exposed to network)
        - Port: 5000 (standard Flask development port)
        - Threaded: True (handles multiple requests concurrently)
        
    Background Tasks:
        Starts periodic_cleanup thread to automatically remove old files
        every hour.
        
    Production Deployment:
        For production, use a WSGI server like Gunicorn or uWSGI instead
        of Flask's development server. Example:
            gunicorn -w 4 -b 0.0.0.0:5000 app:app
    """
    logger.info("Starting YouTube MP3 Downloader application")
    logger.info("=" * 60)
    logger.info(f"Download folder: {app.config['DOWNLOAD_FOLDER']}")
    logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
    logger.info(f"Max concurrent downloads: {app.config['MAX_DOWNLOADS']}")
    logger.info(f"File retention: {app.config['FILE_RETENTION_HOURS']} hours")
    logger.info("=" * 60)
    
    # Start background cleanup thread
    # Daemon thread will automatically terminate when main app exits
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    logger.info("Background cleanup thread started")
    
    # Start Flask development server
    # WARNING: Only for development. Use WSGI server for production.
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
