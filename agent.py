import requests
import os
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import make_chunks
import time
import re

class ReelAgent:
    def __init__(self):
        self.rapidapi_key = None
        self._load_config()
    
    def _load_config(self):
        """Load RapidAPI key from Streamlit secrets"""
        try:
            import streamlit as st
            self.rapidapi_key = st.secrets.get("RAPIDAPI_KEY")
            
            if not self.rapidapi_key:
                raise ValueError("RAPIDAPI_KEY not found in secrets")
            
            print(f"[✓] RapidAPI key loaded")
            
        except Exception as e:
            raise ValueError(f"Failed to load RapidAPI key: {e}")
    
    def _extract_shortcode(self, url):
        """Extract shortcode from Instagram URL"""
        match = re.search(r'/(?:reels|reel|p)/([A-Za-z0-9_-]+)/', url)
        if not match:
            raise ValueError("Invalid Instagram URL format")
        return match.group(1)
    
    def _download_video_rapidapi(self, shortcode):
        """Download video using RapidAPI"""
        print(f"[*] Downloading via RapidAPI (shortcode: {shortcode})...")
        
        url = "https://social-media-video-downloader.p.rapidapi.com/instagram/v3/media/post/details"
        
        querystring = {"shortcode": shortcode}
        
        headers = {
            "x-rapidapi-key": self.rapidapi_key,
            "x-rapidapi-host": "social-media-video-downloader.p.rapidapi.com"
        }
        
        try:
            response = requests.get(url, headers=headers, params=querystring, timeout=30)
            
            if response.status_code != 200:
                raise Exception(f"RapidAPI returned status {response.status_code}")
            
            data = response.json()
            
            # Extract video URL
            try:
                video_url = data['contents'][0]['videos'][0]['url']
            except (KeyError, IndexError, TypeError) as e:
                raise Exception(f"Failed to extract video URL: {e}")
            
            # Download video file
            video_temp = f"temp_reel_{shortcode}_{int(time.time())}.mp4"
            
            print(f"[*] Downloading video file...")
            with requests.get(video_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(video_temp, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            print(f"[✓] Video downloaded: {video_temp}")
            return video_temp
            
        except Exception as e:
            raise Exception(f"RapidAPI download failed: {e}")
    
    def _transcribe_audio_google(self, video_path, language="hindi"):
        """
        Transcribe audio using Google Speech Recognition
        Returns Devanagari for Hindi
        """
        print(f"\n{'='*60}")
        print(f"[*] TRANSCRIPTION START")
        print(f"    Video: {video_path}")
        print(f"    Language: {language}")
        print(f"    Expected: {'Devanagari (देवनागरी)' if language == 'hindi' else 'English'}")
        print(f"{'='*60}")
        
        # Language codes
        lang_codes = {
            "hindi": "hi-IN",
            "english": "en-US"
        }
        
        lang_code = lang_codes.get(language.lower(), "hi-IN")
        print(f"[*] Using Google API language code: {lang_code}")
        
        full_transcript = []
        chunk_files = []
        
        try:
            # Load audio
            print(f"[*] Loading audio...")
            sound = AudioSegment.from_file(video_path)
            
            duration_seconds = len(sound) / 1000
            print(f"    Duration: {duration_seconds:.1f}s")
            
            # Split into chunks
            chunk_length_ms = 10000
            chunks = make_chunks(sound, chunk_length_ms)
            
            print(f"    Total chunks: {len(chunks)}")
            print(f"\n[*] Processing chunks...\n")
            
            # Initialize recognizer
            r = sr.Recognizer()
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                chunk_name = f"chunk_{i}_{int(time.time())}.wav"
                chunk_files.append(chunk_name)
                
                # Export chunk
                chunk.export(chunk_name, format="wav")
                
                try:
                    with sr.AudioFile(chunk_name) as source:
                        r.adjust_for_ambient_noise(source, duration=0.5)
                        audio_data = r.record(source)
                    
                    # Transcribe with specific language
                    text = r.recognize_google(audio_data, language=lang_code)
                    
                    if text.strip():
                        full_transcript.append(text)
                        
                        # Preview
                        preview = text[:60] + "..." if len(text) > 60 else text
                        print(f"    [{i+1}/{len(chunks)}] ✓ {len(text)} chars")
                        print(f"         {preview}")
                    
                except sr.UnknownValueError:
                    print(f"    [{i+1}/{len(chunks)}] - Silent")
                
                except sr.RequestError as e:
                    print(f"    [{i+1}/{len(chunks)}] ! API Error: {e}")
            
            # Combine
            final_transcript = " ".join(full_transcript)
            
            # Verification
            print(f"\n{'='*60}")
            print(f"[✓] TRANSCRIPTION COMPLETE")
            print(f"{'='*60}")
            print(f"Chunks processed: {len(chunks)}")
            print(f"Successful: {len(full_transcript)}")
            print(f"Total length: {len(final_transcript)} characters")
            
            # Script check for Hindi
            if language == "hindi" and final_transcript:
                devanagari_count = sum(1 for c in final_transcript if '\u0900' <= c <= '\u097F')
                arabic_count = sum(1 for c in final_transcript if '\u0600' <= c <= '\u06FF')
                
                print(f"\nScript Analysis:")
                print(f"  Devanagari chars: {devanagari_count}")
                print(f"  Arabic/Urdu chars: {arabic_count}")
                
                if arabic_count > devanagari_count:
                    print(f"  ⚠️  WARNING: Urdu script detected!")
                else:
                    print(f"  ✓  Correct script (Devanagari)")
            
            print(f"{'='*60}")
            
            # Display full transcript
            print(f"\n{'='*60}")
            print(f"[FINAL TRANSCRIPT - TO BE SAVED]")
            print(f"{'='*60}")
            print(final_transcript[:500] + ("..." if len(final_transcript) > 500 else ""))
            print(f"{'='*60}\n")
            
            return final_transcript
            
        except Exception as e:
            raise Exception(f"Transcription failed: {e}")
        
        finally:
            # Cleanup
            for chunk_file in chunk_files:
                if os.path.exists(chunk_file):
                    try:
                        os.remove(chunk_file)
                    except:
                        pass
    
    def download_and_extract(self, url, video_lang="hindi"):
        """
        Download and transcribe
        """
        shortcode = self._extract_shortcode(url)
        video_path = None
        
        try:
            print(f"\n{'='*60}")
            print(f"[NEW ANALYSIS REQUEST]")
            print(f"Shortcode: {shortcode}")
            print(f"Language: {video_lang}")
            print(f"{'='*60}\n")
            
            # Download
            video_path = self._download_video_rapidapi(shortcode)
            
            # Transcribe
            transcript = self._transcribe_audio_google(video_path, video_lang)
            
            if not transcript or len(transcript.strip()) == 0:
                raise Exception("No speech detected in video")
            
            # Verify before returning
            print(f"\n[*] Returning transcript to app...")
            print(f"    Shortcode: {shortcode}")
            print(f"    Length: {len(transcript)} chars")
            print(f"    First 100 chars: {transcript[:100]}...\n")
            
            # Cleanup
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                print(f"[✓] Cleanup complete\n")
            
            return shortcode, transcript
            
        except Exception as e:
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except:
                    pass
            raise e