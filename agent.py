import subprocess
import os
import re
import whisper
import shutil
import time
import instaloader
import base64
import tempfile
import random

class ReelAgent:
    def __init__(self):
        self.session_loaded = False
        self.L = None
        self.proxy = None
        self._load_config()
        self._init_instaloader()
    
    def _load_config(self):
        """Load configuration from Streamlit secrets"""
        try:
            import streamlit as st
            self.proxy = st.secrets.get("RESIDENTIAL_PROXY")
            if self.proxy:
                print(f"[✓] Proxy configured: {self.proxy.split('@')[1] if '@' in self.proxy else 'Yes'}")
        except:
            pass
    
    def _init_instaloader(self):
        """Initialize Instaloader with session if available"""
        # First, always initialize basic loader
        self._init_basic_loader()
        
        # Then try to load session
        try:
            import streamlit as st
            
            session_b64 = st.secrets.get("INSTAGRAM_SESSION")
            username = st.secrets.get("INSTAGRAM_USERNAME")
            
            if session_b64 and username:
                print("[*] Loading Instagram session from Streamlit Secrets...")
                
                # Decode Base64 session
                session_data = base64.b64decode(session_b64)
                
                # Create temp file for session
                temp_session = tempfile.NamedTemporaryFile(delete=False, suffix='_session')
                temp_session.write(session_data)
                temp_session.close()
                
                # Re-initialize with session
                self.L = instaloader.Instaloader(
                    download_pictures=False,
                    save_metadata=False,
                    download_comments=False,
                    max_connection_attempts=3,
                    request_timeout=30,
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                
                # Load session
                self.L.load_session_from_file(username, temp_session.name)
                
                print(f"[✓] Session loaded for: @{username}")
                self.session_loaded = True
                
                # Cleanup temp file
                os.unlink(temp_session.name)
            else:
                print("[!] No session found - using anonymous mode")
                
        except Exception as e:
            print(f"[!] Session load failed: {e}")
            print("[!] Falling back to anonymous mode")
    
    def _init_basic_loader(self):
        """Initialize basic Instaloader without session"""
        self.L = instaloader.Instaloader(
            download_pictures=False,
            save_metadata=False,
            download_comments=False,
            max_connection_attempts=3,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
    
    def _extract_shortcode(self, url):
        """Extract shortcode from Instagram URL"""
        match = re.search(r'/(?:reels|reel|p)/([A-Za-z0-9_-]+)/', url)
        if not match:
            raise ValueError("Invalid Instagram URL format")
        return match.group(1)
    
    def _exponential_backoff(self, attempt, base_delay=2, max_delay=60):
        """Exponential backoff with jitter"""
        delay = min(base_delay * (2 ** attempt), max_delay)
        jitter = random.uniform(0, delay * 0.1)  # 0-10% jitter
        return delay + jitter
    
    def _download_with_ytdlp(self, url, folder):
        """Method 1: Download using yt-dlp"""
        print(f"[*] Trying yt-dlp method...")
        
        video_path = os.path.join(folder, "video.mp4")
        
        cmd = [
            "yt-dlp",
            url,
            "-o", video_path,
            "--no-playlist",
            "--quiet",
            "--no-warnings",
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "--sleep-interval", "3",
            "--max-sleep-interval", "7"
        ]
        
        # Add proxy if configured
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
            
            if result.returncode == 0 and os.path.exists(video_path):
                print(f"[✓] yt-dlp download successful")
                return video_path
            else:
                print(f"[!] yt-dlp failed: {result.stderr[:200]}")
                return None
        
        except subprocess.TimeoutExpired:
            print(f"[!] yt-dlp timeout after 90 seconds")
            return None
        except Exception as e:
            print(f"[!] yt-dlp error: {e}")
            return None
    
    def _download_with_instaloader(self, url, shortcode, folder):
        """Method 2: Download using Instaloader with session"""
        # Check if L is properly initialized
        if self.L is None:
            print(f"[!] Instaloader not initialized properly")
            return None
        
        if not self.session_loaded:
            print(f"[!] No session - skipping Instaloader method")
            return None
        
        print(f"[*] Trying Instaloader with session...")
        
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                # Add delay with exponential backoff
                if attempt > 0:
                    delay = self._exponential_backoff(attempt)
                    print(f"[*] Retry {attempt + 1}/{max_retries} after {delay:.1f}s wait...")
                    time.sleep(delay)
                
                # Random delay before request (look human)
                time.sleep(random.uniform(2, 5))
                
                # Download post
                post = instaloader.Post.from_shortcode(self.L.context, shortcode)
                self.L.download_post(post, target=folder)
                
                # Find video file
                for f in os.listdir(folder):
                    if f.endswith(".mp4"):
                        video_path = os.path.join(folder, f)
                        print(f"[✓] Instaloader download successful")
                        return video_path
                
                raise FileNotFoundError("Video file not found in downloaded files")
            
            except instaloader.exceptions.ConnectionException as e:
                error_str = str(e)
                
                if "429" in error_str or "Too Many Requests" in error_str:
                    print(f"[!] Rate limit (429) - waiting with exponential backoff...")
                    continue
                elif "401" in error_str or "403" in error_str:
                    print(f"[!] Authentication error ({error_str[:100]})")
                    print("    → Session may be expired. Re-run local_session_generator.py")
                    return None
                else:
                    print(f"[!] Connection error: {error_str[:100]}")
                    continue
            
            except Exception as e:
                print(f"[!] Instaloader error: {str(e)[:100]}")
                return None
        
        print(f"[!] All {max_retries} retries exhausted")
        return None
    
    def download_and_extract(self, url, video_lang="hindi"):
        """
        Main download and transcription method
        Tries multiple methods with fallback
        """
        whisper_lang_map = {"hindi": "hi", "english": "en"}
        whisper_code = whisper_lang_map.get(video_lang.lower(), "hi")
        
        shortcode = self._extract_shortcode(url)
        folder = f"temp_{shortcode}_{int(time.time())}"
        
        os.makedirs(folder, exist_ok=True)
        
        try:
            print(f"\n{'='*60}")
            print(f"Processing Reel: {shortcode}")
            print(f"{'='*60}")
            
            # Try methods in order
            download_methods = [
                ("yt-dlp", lambda: self._download_with_ytdlp(url, folder)),
                ("Instaloader + Session", lambda: self._download_with_instaloader(url, shortcode, folder))
            ]
            
            video_path = None
            
            for method_name, method_func in download_methods:
                print(f"\n[Method: {method_name}]")
                video_path = method_func()
                
                if video_path:
                    print(f"[✓] Success with {method_name}")
                    break
                else:
                    print(f"[!] {method_name} failed - trying next method...")
            
            # If all methods failed
            if not video_path:
                raise Exception(
                    "❌ सभी download methods विफल!\n\n"
                    "संभावित समाधान:\n"
                    "1. ✅ Instagram session upload करें (सबसे जरूरी!)\n"
                    "   → local_session_generator.py चलाएं\n"
                    "   → Base64 string को Streamlit Secrets में paste करें\n\n"
                    "2. ⏰ 15-20 मिनट प्रतीक्षा करें (Instagram rate limit)\n\n"
                    "3. 🌐 Residential proxy add करें (optional)\n\n"
                    "4. 🔒 Ensure reel is public (not private account)\n"
                )
            
            print(f"\n[✓] Video downloaded successfully")
            
            # Extract audio using FFmpeg
            print(f"[*] Extracting audio with FFmpeg...")
            audio_path = os.path.join(folder, "audio.mp3")
            
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr[:300]}")
            
            print(f"[✓] Audio extracted")
            
            # Transcribe with Whisper
            print(f"[*] Transcribing audio ({video_lang})...")
            
            model = whisper.load_model("base")
            
            if video_lang.lower() == "hindi":
                transcribe_result = model.transcribe(
                    audio_path,
                    language="hi",
                    task="transcribe",
                    fp16=False
                )
            else:
                transcribe_result = model.transcribe(
                    audio_path,
                    language=whisper_code,
                    fp16=False
                )
            
            transcript = transcribe_result["text"].strip()
            
            # Display transcript in terminal
            print(f"\n{'='*60}")
            print(f"[EXTRACTED TRANSCRIPT]")
            print(f"{'='*60}")
            print(transcript)
            print(f"{'='*60}\n")
            
            # Cleanup temporary files
            print(f"[*] Cleaning up temporary files...")
            shutil.rmtree(folder, ignore_errors=True)
            print(f"[✓] Cleanup complete")
            
            return shortcode, transcript
        
        except Exception as e:
            # Cleanup on error
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
            raise e