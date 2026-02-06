import requests
import os
import speech_recognition as sr
from pydub import AudioSegment
from pydub.utils import make_chunks
import time
import re
import shutil

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
                raise Exception(f"RapidAPI returned status {response.status_code}: {response.text[:200]}")
            
            data = response.json()
            
            # Extract video URL
            try:
                video_url = data['contents'][0]['videos'][0]['url']
            except (KeyError, IndexError, TypeError) as e:
                raise Exception(f"Failed to extract video URL from response: {e}\nResponse: {str(data)[:300]}")
            
            # Download video file
            video_temp = f"temp_reel_{shortcode}.mp4"
            
            print(f"[*] Downloading video file...")
            with requests.get(video_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(video_temp, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            print(f"[✓] Video downloaded: {video_temp}")
            return video_temp
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error: {e}")
        except Exception as e:
            raise Exception(f"RapidAPI download failed: {e}")
    
    def _transcribe_audio_google(self, video_path, language="hindi"):
        """
        Transcribe audio using Google Speech Recognition
        Chunks audio to ensure complete transcription
        """
        print(f"[*] Transcribing audio using Google Speech Recognition ({language})...")
        
        # Language codes for Google Speech API
        lang_codes = {
            "hindi": "hi-IN",
            "english": "en-US"
        }
        
        lang_code = lang_codes.get(language.lower(), "hi-IN")
        
        full_transcript = []
        chunk_files = []
        
        try:
            # Load audio
            print(f"[*] Processing audio file...")
            sound = AudioSegment.from_file(video_path)
            
            # Split into 10-second chunks (Google API works better with shorter segments)
            chunk_length_ms = 10000  # 10 seconds
            chunks = make_chunks(sound, chunk_length_ms)
            
            print(f"[*] Audio split into {len(chunks)} chunks")
            
            # Initialize recognizer
            r = sr.Recognizer()
            
            # Process each chunk
            for i, chunk in enumerate(chunks):
                chunk_name = f"chunk_{i}_{int(time.time())}.wav"
                chunk_files.append(chunk_name)
                
                # Export chunk as WAV
                chunk.export(chunk_name, format="wav")
                
                try:
                    with sr.AudioFile(chunk_name) as source:
                        # Adjust for ambient noise
                        r.adjust_for_ambient_noise(source, duration=0.5)
                        audio_data = r.record(source)
                    
                    # Recognize speech
                    print(f"[*] Transcribing chunk {i+1}/{len(chunks)}...")
                    text = r.recognize_google(audio_data, language=lang_code)
                    
                    if text.strip():
                        full_transcript.append(text)
                        print(f"    ✓ Chunk {i+1}: {len(text)} chars")
                    
                except sr.UnknownValueError:
                    # Silent chunk or unclear audio
                    print(f"    - Chunk {i+1}: Silent/unclear")
                    pass
                
                except sr.RequestError as e:
                    print(f"    ! Chunk {i+1}: Google API error: {e}")
                    pass
            
            # Combine all transcripts
            final_transcript = " ".join(full_transcript)
            
            print(f"\n[✓] Transcription complete")
            print(f"    Total chunks: {len(chunks)}")
            print(f"    Transcribed chunks: {len(full_transcript)}")
            print(f"    Total characters: {len(final_transcript)}")
            
            return final_transcript
            
        except Exception as e:
            raise Exception(f"Transcription failed: {e}")
        
        finally:
            # Cleanup chunk files
            for chunk_file in chunk_files:
                if os.path.exists(chunk_file):
                    try:
                        os.remove(chunk_file)
                    except:
                        pass
    
    def download_and_extract(self, url, video_lang="hindi"):
        """
        Main method: Download video and extract transcript
        """
        shortcode = self._extract_shortcode(url)
        video_path = None
        
        try:
            print(f"\n{'='*60}")
            print(f"Processing Reel: {shortcode}")
            print(f"{'='*60}")
            
            # Step 1: Download video using RapidAPI
            video_path = self._download_video_rapidapi(shortcode)
            
            # Step 2: Transcribe using Google Speech Recognition
            transcript = self._transcribe_audio_google(video_path, video_lang)
            
            if not transcript or len(transcript.strip()) == 0:
                raise Exception("No speech detected in video. Video may be:\n- Silent\n- Music only\n- Poor audio quality")
            
            # Display transcript in terminal
            print(f"\n{'='*60}")
            print(f"[EXTRACTED TRANSCRIPT]")
            print(f"{'='*60}")
            print(transcript)
            print(f"{'='*60}\n")
            
            # Cleanup
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
                print(f"[✓] Cleanup complete")
            
            return shortcode, transcript
            
        except Exception as e:
            # Cleanup on error
            if video_path and os.path.exists(video_path):
                try:
                    os.remove(video_path)
                except:
                    pass
            raise e