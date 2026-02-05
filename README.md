# 🏥 Instagram Health Claim Fact Checker

Automatically fact-check health claims from Instagram Reels using AI.

## 🚀 Features

- ✅ Extract transcripts from Instagram Reels (Hindi & English)
- 🤖 AI-powered fact-checking using Groq (Llama 3.3 70B)
- 📊 Detailed claim analysis with scientific sources
- 💬 Interactive chat about analyzed videos
- 📁 Persistent storage of analyses

## 🛠️ Setup

### Prerequisites

1. **FFmpeg**: Required for audio extraction
```bash
   # Windows (using Chocolatey)
   choco install ffmpeg
   
   # Or download from: https://ffmpeg.org/download.html
```

2. **Groq API Key** (Free): Get from https://console.groq.com/keys

### Local Development

1. **Clone and install**:
```bash
   git clone <your-repo>
   cd health-claim-checker
   pip install -r requirements.txt
```

2. **Configure secrets**:
   - Create `.streamlit/secrets.toml`
   - Add: `GROQ_API_KEY = "your_key_here"`

3. **Run**:
```bash
   streamlit run streamlit_app.py
```

## ☁️ Deploy to Streamlit Cloud

1. **Push to GitHub**
2. **Go to**: https://share.streamlit.io
3. **Deploy** your repository
4. **Add secrets** in Settings:
   - `GROQ_API_KEY = your_groq_key`

### Important: FFmpeg on Streamlit Cloud

Add `packages.txt` file:
```
ffmpeg
```

## 📦 Project Structure
```
health-claim-checker/
├── streamlit_app.py      # Main Streamlit app
├── agent.py              # Reel downloader & transcriber
├── llm_checker.py        # Groq LLM integration
├── database.py           # JSON-based storage
├── requirements.txt      # Python dependencies
├── packages.txt          # System packages (ffmpeg)
├── .streamlit/
│   └── secrets.toml      # API keys (gitignored)
└── README.md
```

## 🔑 Free Resources Used

- **Groq**: 14,400 free requests/day (Llama 3.3 70B)
- **Whisper**: Open-source, runs locally
- **Streamlit Cloud**: Free hosting with 1GB resources

## 🎯 Usage

1. Paste Instagram Reel URL
2. Select language (Hindi/English)
3. Click "Analyze Reel"
4. View fact-check results
5. Chat with AI about the video

## ⚠️ Limitations

- File-based storage (resets on Streamlit Cloud restart)
- For production, use external database (Supabase/PlanetScale free tier)

## 📝 License

MIT
```

## 8. **packages.txt** (IMPORTANT for Streamlit Cloud)
```
ffmpeg