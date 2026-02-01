// =====================================================
// GLOBAL STATE MANAGEMENT
// =====================================================

// YouTube download tracking
let currentDownloadId = null;   // UUID of active download
let statusInterval = null;      // Interval timer for polling status
let retryCount = 0;             // Failed status check counter
const MAX_RETRIES = 3;          // Maximum retry attempts before giving up

// =====================================================
// EVENT LISTENERS - YOUTUBE DOWNLOADER
// =====================================================

// Attach event listeners for YouTube download functionality
document.getElementById('downloadBtn').addEventListener('click', startDownload);
document.getElementById('cancelBtn').addEventListener('click', cancelDownload);
document.getElementById('downloadFileBtn').addEventListener('click', downloadFile);

console.log('Event listeners attached successfully');

// =====================================================
// KEYBOARD SHORTCUTS
// =====================================================

// Allow Enter key to submit YouTube URL
document.getElementById('youtubeUrl').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        startDownload();
    }
});

// =====================================================
// YOUTUBE DOWNLOAD FUNCTIONS
// =====================================================

/**
 * Initialize YouTube to MP3 download
 * 
 * Main entry point for YouTube conversion. Validates URL,
 * sends request to backend, and starts progress monitoring.
 * 
 * Workflow:
 * 1. Validate YouTube URL format
 * 2. Send POST request to /download endpoint
 * 3. Receive download ID
 * 4. Start polling /status endpoint for progress
 * 
 * Validation:
 * - URL must not be empty
 * - URL must contain 'youtube.com' or 'youtu.be'
 * 
 * Error Handling:
 * - Network errors: Show retry message
 * - Server busy: Show capacity error
 * - Invalid URL: Show validation error
 */
async function startDownload() {
    console.log('startDownload called');
    const url = document.getElementById('youtubeUrl').value.trim();
    
    console.log('URL:', url);
    
    if (!url) {
        showError('Please enter a YouTube URL');
        return;
    }
    
    // Basic URL validation
    if (!url.includes('youtube.com') && !url.includes('youtu.be')) {
        showError('Please enter a valid YouTube URL (youtube.com or youtu.be)');
        return;
    }

    // Reset UI
    hideError();
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = '0%';
    document.getElementById('statusText').textContent = 'Starting...';
    document.getElementById('downloadFileBtn').style.display = 'none';
    document.getElementById('videoInfo').innerHTML = '';
    retryCount = 0;

    // Disable download button
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';

    try {
        const response = await fetch('/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `url=${encodeURIComponent(url)}`
        });

        const data = await response.json();
        
        if (response.ok) {
            currentDownloadId = data.download_id;
            startStatusCheck();
        } else {
            showError(data.error || 'Failed to start download');
            resetDownloadButton();
        }
    } catch (error) {
        console.error('Download error:', error);
        showError('Network error. Please check your connection and try again.');
        resetDownloadButton();
    }
}

function startStatusCheck() {
    if (statusInterval) clearInterval(statusInterval);
    
    statusInterval = setInterval(async () => {
        try {
            const response = await fetch(`/status/${currentDownloadId}`);
            
            if (!response.ok) {
                throw new Error('Status check failed');
            }
            
            const status = await response.json();
            retryCount = 0; // Reset retry count on successful fetch
            
            if (status.status === 'downloading') {
                const progress = status.progress || 0;
                document.getElementById('progressFill').style.width = `${progress}%`;
                document.getElementById('progressText').textContent = `${progress}%`;
                document.getElementById('statusText').textContent = 'Downloading and converting...';
                
                if (status.title) {
                    document.getElementById('videoInfo').innerHTML = 
                        `<p><strong>Converting:</strong> ${escapeHtml(status.title)}</p>`;
                }
            } else if (status.status === 'completed') {
                clearInterval(statusInterval);
                document.getElementById('progressFill').style.width = '100%';
                document.getElementById('progressText').textContent = '100%';
                document.getElementById('statusText').textContent = '✓ Completed!';
                document.getElementById('downloadFileBtn').style.display = 'inline-block';
                resetDownloadButton();
                
                // Auto-download after 2 seconds
                setTimeout(() => {
                    if (currentDownloadId) {
                        downloadFile();
                    }
                }, 2000);
            } else if (status.status === 'error') {
                clearInterval(statusInterval);
                showError(status.error || 'Conversion failed. Please try again.');
                resetDownloadButton();
            } else if (status.status === 'not_found') {
                clearInterval(statusInterval);
                showError('Download session expired. Please try again.');
                resetDownloadButton();
            }
        } catch (error) {
            console.error('Status check error:', error);
            retryCount++;
            
            if (retryCount >= MAX_RETRIES) {
                clearInterval(statusInterval);
                showError('Lost connection to server. Please try again.');
                resetDownloadButton();
            }
        }
    }, 1000);
}

function cancelDownload() {
    if (statusInterval) clearInterval(statusInterval);
    document.getElementById('progressSection').style.display = 'none';
    resetDownloadButton();
    currentDownloadId = null;
    hideError();
}


function downloadFile() {
    if (currentDownloadId) {
        window.location.href = `/get_file/${currentDownloadId}`;
        // Clear input after download
        setTimeout(() => {
            document.getElementById('youtubeUrl').value = '';
            document.getElementById('progressSection').style.display = 'none';
        }, 3000);
    }
}

function resetDownloadButton() {
    const downloadBtn = document.getElementById('downloadBtn');
    downloadBtn.disabled = false;
    downloadBtn.innerHTML = '<i class="fas fa-download"></i> Convert to MP3';
}

function showError(message) {
    document.getElementById('errorText').textContent = message;
    document.getElementById('errorSection').style.display = 'block';
    document.getElementById('progressSection').style.display = 'none';
}

function hideError() {
    document.getElementById('errorSection').style.display = 'none';
}

// =====================================================
// UTILITY FUNCTIONS
// =====================================================

/**
 * Escape HTML to prevent XSS attacks
 * 
 * Converts special characters to HTML entities to safely
 * display user-generated content (like video titles) without
 * allowing script injection.
 * 
 * @param {string} text - Text to escape
 * @returns {string} HTML-safe text
 * 
 * Security:
 * Prevents cross-site scripting (XSS) attacks by escaping
 * special characters like <, >, &, ", and '.
 * 
 * Example:
 *   escapeHtml('<script>alert("XSS")</script>')
 *   // Returns: '&lt;script&gt;alert(&quot;XSS&quot;)&lt;/script&gt;'
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;  // textContent auto-escapes
    return div.innerHTML;    // Get escaped HTML
}

// =====================================================
// PAGE LIFECYCLE EVENTS
// =====================================================

/**
 * Auto-cleanup on page load
 * 
 * Triggers server cleanup of old files when user loads page.
 * This helps maintain disk space even if users don't download.
 * Runs silently in background - failures are ignored.
 * 
 * Called automatically when page finishes loading.
 */
window.addEventListener('load', () => {
    fetch('/cleanup', { method: 'POST' }).catch(() => {});
});

/**
 * Cleanup before leaving page
 * 
 * Stops all polling intervals to prevent memory leaks and
 * unnecessary API calls after user navigates away.
 * 
 * Called automatically when user closes tab or navigates away.
 */
window.addEventListener('beforeunload', () => {
    if (statusInterval) clearInterval(statusInterval);
});
