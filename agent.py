import instaloader
import subprocess
import os
import re
import whisper
import shutil

class ReelAgent:
    def __init__(self):
        self.L = instaloader.Instaloader(
            download_pictures=False, 
            save_metadata=False, 
            download_comments=False
        )
    
    def download_and_extract(self, url, lang_choice="hindi"):
        lang_map = {
            "hindi": "hi",
            "english": "en"
        }
        
        selected_lang_code = lang_map.get(lang_choice.lower(), "hi")
        
        match = re.search(r'/(?:reels|reel|p)/([A-Za-z0-9_-]+)/', url)
        if not match:
            raise ValueError("Invalid Instagram URL")
        
        shortcode = match.group(1)
        folder = f"temp_{shortcode}"
        
        try:
            # Download reel
            post = instaloader.Post.from_shortcode(self.L.context, shortcode)
            self.L.download_post(post, target=folder)
            
            # Find video file
            video_path = None
            for f in os.listdir(folder):
                if f.endswith(".mp4"):
                    video_path = os.path.join(folder, f)
                    break
            
            if not video_path:
                raise FileNotFoundError("No video found in download")
            
            # Extract audio
            audio_path = os.path.join(folder, "audio.mp3")
            subprocess.run(
                ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"],
                check=True, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.STDOUT
            )
            
            # Transcribe
            model = whisper.load_model("base")
            result = model.transcribe(audio_path, language=selected_lang_code)
            transcript = result["text"]
            
            # Cleanup
            shutil.rmtree(folder, ignore_errors=True)
            
            return shortcode, transcript
            
        except Exception as e:
            # Cleanup on error
            if os.path.exists(folder):
                shutil.rmtree(folder, ignore_errors=True)
            raise e