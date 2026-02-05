import subprocess
import os
import re
import whisper
import shutil
import time
import instaloader
import json

class ReelAgent:
    def __init__(self):
        self.L = instaloader.Instaloader(
            download_pictures=False,
            save_metadata=False,
            download_comments=False,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            max_connection_attempts=3
        )
        self.session_file = "instagram_session.json"
    
    def _extract_shortcode(self, url):
        """Extract shortcode from Instagram URL"""
        match = re.search(r'/(?:reels|reel|p)/([A-Za-z0-9_-]+)/', url)
        if not match:
            raise ValueError("Invalid Instagram URL format")
        return match.group(1)
    
    def _download_with_ytdlp(self, url, folder):
        """Method 1: Download using yt-dlp (more reliable)"""
        print(f"[*] Trying yt-dlp method...")
        
        video_path = os.path.join(folder, "video.mp4")
        
        # yt-dlp command
        cmd = [
            "yt-dlp",
            url,
            "-o", video_path,
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--sleep-interval", "3",
            "--max-sleep-interval", "6"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(video_path):
                print(f"[✓] yt-dlp download successful")
                return video_path
            else:
                raise Exception(f"yt-dlp failed: {result.stderr}")
        
        except Exception as e:
            print(f"[!] yt-dlp failed: {e}")
            return None
    
    def _download_with_instaloader(self, url, shortcode, folder):
        """Method 2: Download using Instaloader (fallback)"""
        print(f"[*] Trying Instaloader method...")
        
        try:
            # Add delay to avoid rate limiting
            time.sleep(5)
            
            # Try to load session if exists
            if os.path.exists(self.session_file):
                try:
                    with open(self.session_file, 'r') as f:
                        session_data = json.load(f)
                    username = session_data.get('username')
                    if username:
                        self.L.load_session_from_file(username, self.session_file)
                        print(f"[✓] Loaded session for {username}")
                except:
                    pass
            
            # Download post
            post = instaloader.Post.from_shortcode(self.L.context, shortcode)
            self.L.download_post(post, target=folder)
            
            # Find video file
            for f in os.listdir(folder):
                if f.endswith(".mp4"):
                    video_path = os.path.join(folder, f)
                    print(f"[✓] Instaloader download successful")
                    return video_path
            
            raise FileNotFoundError("No video file found")
        
        except Exception as e:
            print(f"[!] Instaloader failed: {e}")
            return None
    
    def download_and_extract(self, url, video_lang="hindi"):
        """
        Download Instagram Reel and extract transcript
        Tries yt-dlp first, then Instaloader as fallback
        """
        whisper_lang_map = {
            "hindi": "hi",
            "english": "en"
        }
        
        whisper_code = whisper_lang_map.get(video_lang.lower(), "hi")
        
        # Extract shortcode
        shortcode = self._extract_shortcode(url)
        folder = f"temp_{shortcode}_{int(time.time())}"
        
        os.makedirs(folder, exist_ok=True)
        
        try:
            print(f"\n[*] Processing Reel (Shortcode: {shortcode})...")
            
            # Try yt-dlp first
            video_path = self._download_with_ytdlp(url, folder)
            
            # If yt-dlp fails, try Instaloader
            if not video_path:
                print(f"[*] yt-dlp failed, trying Instaloader as fallback...")
                video_path = self._download_with_instaloader(url, shortcode, folder)
            
            # If both failed
            if not video_path:
                raise Exception(
                    "Both download methods failed. Possible reasons:\n"
                    "1. Instagram rate limiting (wait 10-15 minutes)\n"
                    "2. Private account\n"
                    "3. Reel deleted or unavailable\n"
                    "4. Network issues"
                )
            
            print(f"[✓] Download complete")
            
            # Extract audio
            print(f"[*] Extracting audio using system FFmpeg...")
            audio_path = os.path.join(folder, "audio.mp3")
            
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            print(f"[✓] Audio extracted")
            
            # Transcribe
            print(f"[*] Transcribing in {video_lang.capitalize()}...")
            
            model = whisper.load_model("base")
            
            if video_lang.lower() == "hindi":
                result = model.transcribe(
                    audio_path,
                    language="hi",
                    task="transcribe",
                    fp16=False
                )
            else:
                result = model.transcribe(
                    audio_path,
                    language=whisper_code,
                    fp16=False
                )
            
            transcript = result["text"].strip()
            
            # Terminal output
            print(f"\n{'='*60}")
            print(f"[EXTRACTED TRANSCRIPT]")
            print(f"{'='*60}")
            print(transcript)
            print(f"{'='*60}\n")
            
            # Cleanup
            print(f"[*] Cleaning up temporary files...")
            shutil.rmtree(folder, ignore_errors=True)
            print(f"[✓] Cleanup complete\n")
            
            return shortcode, transcript
        
        except Exception as e:
            # Cleanup on error
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
            raise e
    
    def login_and_save_session(self, username, password):
        """
        Optional: Login to Instagram and save session
        This can help avoid rate limiting
        """
        try:
            self.L.login(username, password)
            self.L.save_session_to_file(self.session_file)
            
            # Save username for later
            with open(self.session_file + ".meta", 'w') as f:
                json.dump({"username": username}, f)
            
            print(f"[✓] Session saved for {username}")
            return True
        except Exception as e:
            print(f"[!] Login failed: {e}")
            return False