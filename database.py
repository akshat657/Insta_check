import json
import os
from datetime import datetime

# Simple file-based storage for Streamlit Cloud
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
        data = self._load_fact_checks()
        
        fact_check = {
            'id': shortcode,
            'reel_url': reel_url,
            'shortcode': shortcode,
            'transcript': transcript,
            'analysis': analysis if isinstance(analysis, dict) else json.loads(analysis),
            'rating': rating,
            'created_at': datetime.now().isoformat()
        }
        
        data[shortcode] = fact_check
        self._save_fact_checks(data)
        return shortcode
    
    def get_fact_check(self, shortcode):
        data = self._load_fact_checks()
        return data.get(shortcode)
    
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