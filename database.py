import json
import os
from datetime import datetime

class Database:
    def __init__(self):
        self.data_file = "fact_checks.json"
        self.chat_file = "chat_history.json"
        self._init_files()
    
    def _init_files(self):
        if not os.path.exists(self.data_file):
            with open(self.data_file, 'w') as f:
                json.dump({}, f)
        
        if not os.path.exists(self.chat_file):
            with open(self.chat_file, 'w') as f:
                json.dump({}, f)
    
    def _load_fact_checks(self):
        with open(self.data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_fact_checks(self, data):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_chats(self):
        with open(self.chat_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_chats(self, data):
        with open(self.chat_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def save_fact_check(self, reel_url, shortcode, transcript, analysis, rating):
        """Save or UPDATE fact check"""
        data = self._load_fact_checks()
        
        # Check if exists
        if shortcode in data:
            print(f"\n[!] WARNING: Shortcode {shortcode} already exists in database!")
            print(f"    Old transcript preview: {data[shortcode]['transcript'][:100]}...")
            print(f"    New transcript preview: {transcript[:100]}...")
            print(f"[*] OVERWRITING with new data...\n")
        
        fact_check = {
            'id': shortcode,
            'reel_url': reel_url,
            'shortcode': shortcode,
            'transcript': transcript,  # This should be the NEW Devanagari transcript
            'analysis': analysis if isinstance(analysis, dict) else json.loads(analysis),
            'rating': rating,
            'created_at': datetime.now().isoformat()
        }
        
        data[shortcode] = fact_check
        self._save_fact_checks(data)
        
        print(f"[✓] Saved to database:")
        print(f"    Shortcode: {shortcode}")
        print(f"    Transcript length: {len(transcript)} chars")
        print(f"    First 100 chars: {transcript[:100]}...\n")
        
        return shortcode
    
    def get_fact_check(self, shortcode):
        """Get existing fact check"""
        data = self._load_fact_checks()
        result = data.get(shortcode)
        
        if result:
            print(f"\n[*] Found in database: {shortcode}")
            print(f"    Transcript preview: {result['transcript'][:100]}...\n")
        
        return result
    
    def save_chat(self, fact_check_id, user_msg, assistant_msg):
        chats = self._load_chats()
        
        if fact_check_id not in chats:
            chats[fact_check_id] = []
        
        chats[fact_check_id].append({
            'user_message': user_msg,
            'assistant_response': assistant_msg,
            'created_at': datetime.now().isoformat()
        })
        
        self._save_chats(chats)
    
    def get_chat_history(self, fact_check_id):
        chats = self._load_chats()
        return chats.get(fact_check_id, [])
    
    def clear_cache(self, shortcode):
        """Clear cached data for a shortcode"""
        data = self._load_fact_checks()
        
        if shortcode in data:
            del data[shortcode]
            self._save_fact_checks(data)
            print(f"[✓] Cleared cache for: {shortcode}")
            return True
        
        return False