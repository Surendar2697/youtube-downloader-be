from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import uuid
from urllib.parse import quote

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
DOWNLOAD_DIR = "downloads"
BASE_URL = "https://youtube-downloader-be-2.onrender.com/downloads/"  # Updated for Render
FFMPEG_PATH = "./fm/bin/ffmpeg"  # Use forward slashes and Linux-compatible path

def get_ffmpeg_path():
    """Return the path to the FFmpeg executable."""
    if not os.path.exists(FFMPEG_PATH):
        return None
    return FFMPEG_PATH

def download_youtube_video(url, choice, ffmpeg_path, output_path):
    """Download YouTube video/audio with specified quality using provided FFmpeg."""
    try:
        os.makedirs(output_path, exist_ok=True)

        unique_id = str(uuid.uuid4())
        output_template = os.path.join(output_path, f'%(title)s_{unique_id}.%(ext)s')

        ydl_opts = {
            'outtmpl': output_template,
            'ffmpeg_location': ffmpeg_path,
            'noplaylist': True,
        }

        # Select format
        if choice == '1':  # Low quality video
            ydl_opts['format'] = 'worstvideo[ext=mp4]+bestaudio[ext=m4a]/worst[ext=mp4]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif choice == '2':  # Medium quality video
            ydl_opts['format'] = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif choice == '3':  # High quality video
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]'
            ydl_opts['merge_output_format'] = 'mp4'
        elif choice == '4':  # MP3 audio
            ydl_opts['format'] = 'bestaudio[ext=m4a]'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

            if choice == '4':
                filename = filename.rsplit('.', 1)[0] + '.mp3'

            safe_filename = quote(os.path.basename(filename))
            download_url = f"{BASE_URL}{safe_filename}"
            return download_url
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")

@app.route('/download', methods=['POST'])
def download_video():
    """API endpoint to download YouTube video/audio and return download URL."""
    try:
        ffmpeg_path = get_ffmpeg_path()
        if not ffmpeg_path:
            return jsonify({"error": "FFmpeg not found."}), 500

        data = request.get_json()
        if not data or 'url' not in data or 'choice' not in data:
            return jsonify({"error": "Missing 'url' or 'choice' in request body."}), 400

        video_url = data['url']
        choice = data['choice']

        if choice not in ['1', '2', '3', '4']:
            return jsonify({"error": "Invalid choice. Must be 1, 2, 3, or 4."}), 400

        download_url = download_youtube_video(video_url, choice, ffmpeg_path, DOWNLOAD_DIR)
        return jsonify({"download_url": download_url}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/downloads/<filename>')
def serve_file(filename):
    """Serve the downloaded file."""
    try:
        return send_from_directory(DOWNLOAD_DIR, filename, as_attachment=True)
    except FileNotFoundError:
        return jsonify({"error": "File not found."}), 404

if __name__ == "__main__":
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    port = int(os.environ.get("PORT", 5000))  # Render will set this
    app.run(host="0.0.0.0", port=port, debug=True)
