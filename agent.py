import instaloader
import subprocess
import os
import re
import whisper
import shutil
import time

class ReelAgent:
    def __init__(self):
        self.L = instaloader.Instaloader(
            download_pictures=False, 
            save_metadata=False, 
            download_comments=False,
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
    
    def download_and_extract(self, url, video_lang="hindi"):
        """
        Download Instagram Reel and extract transcript
        Returns: (shortcode, raw_transcript)
        """
        whisper_lang_map = {
            "hindi": "hi",
            "english": "en"
        }
        
        whisper_code = whisper_lang_map.get(video_lang.lower(), "hi")
        
        # Extract shortcode from URL
        match = re.search(r'/(?:reels|reel|p)/([A-Za-z0-9_-]+)/', url)
        if not match:
            raise ValueError("Invalid Instagram URL")
        
        shortcode = match.group(1)
        folder = f"temp_{shortcode}_{int(time.time())}"
        
        try:
            print(f"\n[*] Downloading Reel (Shortcode: {shortcode})...")
            
            # Add delay to avoid rate limiting
            time.sleep(2)
            
            # Download reel
            post = instaloader.Post.from_shortcode(self.L.context, shortcode)
            self.L.download_post(post, target=folder)
            
            print(f"[✓] Download complete")
            
            # Find video file
            video_path = None
            for f in os.listdir(folder):
                if f.endswith(".mp4"):
                    video_path = os.path.join(folder, f)
                    break
            
            if not video_path:
                raise FileNotFoundError("No video file found in download")
            
            print(f"[*] Extracting audio using system FFmpeg...")
            
            # Extract audio using system FFmpeg
            audio_path = os.path.join(folder, "audio.mp3")
            
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"FFmpeg failed: {result.stderr}")
            
            print(f"[✓] Audio extracted")
            print(f"[*] Transcribing in {video_lang.capitalize()}...")
            
            # Load Whisper model
            model = whisper.load_model("base")
            
            # Transcribe with language specification
            if video_lang.lower() == "hindi":
                result = model.transcribe(
                    audio_path, 
                    language="hi",
                    task="transcribe",
                    fp16=False  # CPU compatibility
                )
            else:
                result = model.transcribe(
                    audio_path, 
                    language=whisper_code,
                    fp16=False
                )
            
            transcript = result["text"].strip()
            
            # TERMINAL OUTPUT
            print(f"\n{'='*60}")
            print(f"[EXTRACTED TRANSCRIPT]")
            print(f"{'='*60}")
            print(transcript)
            print(f"{'='*60}\n")
            
            # Cleanup temp files (important for Streamlit Cloud)
            print(f"[*] Cleaning up temporary files...")
            shutil.rmtree(folder, ignore_errors=True)
            print(f"[✓] Cleanup complete\n")
            
            return shortcode, transcript
            
        except Exception as e:
            # Cleanup on error
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
            raise e