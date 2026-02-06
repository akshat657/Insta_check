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
            
            try:
                video_url = data['contents'][0]['videos'][0]['url']
            except (KeyError, IndexError, TypeError) as e:
                raise Exception(f"Failed to extract video URL: {e}")
            
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
        Transcribe audio using Google Speech Recognition API
        No microphone needed - works with audio files!
        """
        print(f"\n{'='*60}")
        print(f"[*] TRANSCRIPTION START")
        print(f"    Video: {video_path}")
        print(f"    Language: {language}")
        print(f"{'='*60}")
        
        # Language codes for Google Speech API
        lang_codes = {
            "hindi": "hi-IN",
            "english": "en-US"
        }
        
        lang_code = lang_codes.get(language.lower(), "hi-IN")
        
        full_transcript = []
        chunk_files = []
        
        try:
            # Load audio with pydub
            print(f"[*] Loading audio...")
            sound = AudioSegment.from_file(video_path)
            
            duration_seconds = len(sound) / 1000
            print(f"    Duration: {duration_seconds:.1f}s")
            
            # Split into 10-second chunks
            chunk_length_ms = 10000
            chunks = make_chunks(sound, chunk_length_ms)
            
            print(f"    Total chunks: {len(chunks)}")
            print(f"\n[*] Transcribing...\n")
            
            # Initialize recognizer
            recognizer = sr.Recognizer()
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                chunk_name = f"chunk_{i}_{int(time.time())}.wav"
                chunk_files.append(chunk_name)
                
                # Export chunk as WAV
                chunk.export(chunk_name, format="wav")
                
                try:
                    # Load audio file
                    with sr.AudioFile(chunk_name) as source:
                        # Adjust for ambient noise (duration must be int)
                        recognizer.adjust_for_ambient_noise(source, duration=1)
                        # Record the audio
                        audio_data = recognizer.record(source)
                    
                    # Recognize speech using Google Speech Recognition API
                    text = recognizer.recognize_google(audio_data, language=lang_code)
                    
                    if text and text.strip():
                        full_transcript.append(text)
                        
                        preview = text[:60] + "..." if len(text) > 60 else text
                        print(f"    [{i+1}/{len(chunks)}] ✓ {len(text)} chars")
                        print(f"         {preview}")
                    
                except sr.UnknownValueError:
                    # Google Speech Recognition could not understand audio
                    print(f"    [{i+1}/{len(chunks)}] - Silent/unclear")
                
                except sr.RequestError as e:
                    # Could not request results from Google Speech Recognition
                    print(f"    [{i+1}/{len(chunks)}] ! API Error: {e}")
                
                except Exception as e:
                    print(f"    [{i+1}/{len(chunks)}] ! Error: {e}")
            
            # Combine all transcripts
            final_transcript = " ".join(full_transcript)
            
            # Results
            print(f"\n{'='*60}")
            print(f"[✓] TRANSCRIPTION COMPLETE")
            print(f"{'='*60}")
            print(f"Chunks processed: {len(chunks)}")
            print(f"Successful: {len(full_transcript)}")
            print(f"Total length: {len(final_transcript)} characters")
            
            # Script verification for Hindi
            if language == "hindi" and final_transcript:
                devanagari_count = sum(1 for c in final_transcript if '\u0900' <= c <= '\u097F')
                arabic_count = sum(1 for c in final_transcript if '\u0600' <= c <= '\u06FF')
                
                print(f"\nScript Analysis:")
                print(f"  Devanagari: {devanagari_count}")
                print(f"  Arabic/Urdu: {arabic_count}")
                
                if arabic_count > devanagari_count:
                    print(f"  ⚠️  WARNING: Urdu script!")
                else:
                    print(f"  ✓  Correct (Devanagari)")
            
            print(f"{'='*60}")
            
            # Preview
            print(f"\n{'='*60}")
            print(f"[TRANSCRIPT PREVIEW]")
            print(f"{'='*60}")
            preview_length = min(500, len(final_transcript))
            print(final_transcript[:preview_length])
            if len(final_transcript) > 500:
                print("...")
            print(f"{'='*60}\n")
            
            return final_transcript
            
        except Exception as e:
            raise Exception(f"Transcription failed: {e}")
        
        finally:
            # Cleanup chunk files
            print(f"[*] Cleaning up {len(chunk_files)} chunk files...")
            for chunk_file in chunk_files:
                if os.path.exists(chunk_file):
                    try:
                        os.remove(chunk_file)
                    except Exception as cleanup_error:
                        print(f"    ! Could not remove {chunk_file}: {cleanup_error}")
    
    def download_and_extract(self, url, video_lang="hindi"):
        """
        Main method: Download Instagram Reel and extract transcript
        
        Args:
            url: Instagram Reel URL
            video_lang: Language spoken in video ("hindi" or "english")
        
        Returns:
            tuple: (shortcode, transcript)
        """
        shortcode = self._extract_shortcode(url)
        video_path = None
        
        try:
            print(f"\n{'='*60}")
            print(f"[NEW ANALYSIS REQUEST]")
            print(f"Shortcode: {shortcode}")
            print(f"Language: {video_lang}")
            print(f"Method: RapidAPI + Google Speech Recognition")
            print(f"{'='*60}\n")
            
            # Step 1: Download video via RapidAPI
            video_path = self._download_video_rapidapi(shortcode)
            
            # Step 2: Transcribe using Google Speech Recognition
            transcript = self._transcribe_audio_google(video_path, video_lang)
            
            # Validation
            if not transcript or len(transcript.strip()) == 0:
                raise Exception(
                    "No speech detected in video.\n\n"
                    "Possible causes:\n"
                    "• Video has no speech (music-only/silent)\n"
                    "• Audio quality is very poor\n"
                    "• Wrong language selected\n"
                    "• Background noise is too loud"
                )
            
            # Success message
            print(f"\n[✓] SUCCESS")
            print(f"    Shortcode: {shortcode}")
            print(f"    Transcript length: {len(transcript)} characters")
            print(f"    First 100 chars: {transcript[:100]}...\n")
            
            # Cleanup video file
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                print(f"[✓] Cleanup complete\n")
            
            return shortcode, transcript
            
        except Exception as e:
            # Cleanup on error
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                    print(f"[*] Cleaned up video file")
                except:
                    pass
            
            # Re-raise the error
            raise e