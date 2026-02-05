import streamlit as st
from agent import ReelAgent
from llm_checker import HealthClaimChecker
from database import Database
import json
import time

st.set_page_config(
    page_title="Instagram Health Claim Fact Checker",
    page_icon="🏥",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .section-header {
        background: #f8f9fa;
        padding: 0.8rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 1.5rem 0 1rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .error-box {
        background: #fee;
        border-left: 4px solid #f44;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .tip-box {
        background: #eff;
        border-left: 4px solid #4af;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize
@st.cache_resource
def init_components():
    try:
        print("\n" + "="*60)
        print("INITIALIZING COMPONENTS")
        print("="*60)
        agent = ReelAgent()
        checker = HealthClaimChecker()
        db = Database()
        print("="*60 + "\n")
        return agent, checker, db
    except Exception as e:
        st.error(f"❌ Initialization error: {e}")
        st.stop()

agent, checker, db = init_components()

# Session state
if 'fact_check_id' not in st.session_state:
    st.session_state.fact_check_id = None
if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'corrected_transcript' not in st.session_state:
    st.session_state.corrected_transcript = None
if 'current_url' not in st.session_state:
    st.session_state.current_url = ""
if 'show_login' not in st.session_state:
    st.session_state.show_login = False

# Header
st.markdown('''
<div class="main-header">
    <h1>🏥 Instagram Health Claim Fact Checker</h1>
    <p style="font-size: 1.1rem; margin-top: 0.5rem;">Instagram Reels से स्वास्थ्य गलत सूचनाओं का पर्दाफाश करें</p>
</div>
''', unsafe_allow_html=True)

# Important Notice
st.info("ℹ️ **महत्वपूर्ण:** यह टूल yt-dlp और Instaloader का उपयोग करता है। यदि त्रुटि आती है तो 10-15 मिनट प्रतीक्षा करें। | **Important:** This tool uses yt-dlp and Instaloader. If you get an error, wait 10-15 minutes.")

# Optional Login Section
with st.expander("🔐 वैकल्पिक: Instagram Login (Rate Limit से बचने के लिए)", expanded=False):
    st.warning("⚠️ **गोपनीयता सूचना**: आपका पासवर्ड सहेजा नहीं जाता। केवल session token सहेजा जाता है।")
    
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        login_username = st.text_input("Instagram Username", key="login_user")
    
    with col2:
        login_password = st.text_input("Password", type="password", key="login_pass")
    
    with col3:
        st.write("")
        st.write("")
        if st.button("Login"):
            if login_username and login_password:
                with st.spinner("Logging in..."):
                    success = agent.login_and_save_session(login_username, login_password)
                    if success:
                        st.success("✅ Session saved!")
                    else:
                        st.error("❌ Login failed")
            else:
                st.error("Enter username and password")

# Input Section
st.markdown('<div class="section-header"><h3>📎 Enter Reel Details</h3></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    reel_url = st.text_input(
        "Instagram Reel URL",
        placeholder="https://www.instagram.com/reel/...",
        value=st.session_state.current_url,
        label_visibility="collapsed"
    )

with col2:
    video_language = st.selectbox(
        "Video Language",
        ["Hindi", "English"],
        index=0,
        help="वीडियो में कौनसी भाषा बोली गई है"
    )

with col3:
    output_language = st.selectbox(
        "Output Language",
        ["Hindi", "English"],
        index=0,
        help="परिणाम किस भाषा में चाहिए"
    )

# Action Buttons
col1, col2 = st.columns([3, 1])

with col1:
    analyze_button = st.button("🔍 विश्लेषण शुरू करें / Analyze Reel", type="primary", use_container_width=True)

with col2:
    if st.session_state.analysis:
        if st.button("🔄 नया / New", use_container_width=True):
            st.session_state.fact_check_id = None
            st.session_state.analysis = None
            st.session_state.transcript = None
            st.session_state.corrected_transcript = None
            st.session_state.current_url = ""
            st.rerun()

# How it works
with st.expander("📋 कैसे काम करता है / How It Works"):
    st.markdown("""
    **🔧 तकनीकी विवरण:**
    1. **Download Method 1:** yt-dlp (primary) - बेहतर Instagram support
    2. **Download Method 2:** Instaloader (fallback) - यदि yt-dlp विफल
    3. **Audio Extraction:** System FFmpeg
    4. **Transcription:** OpenAI Whisper (base model)
    5. **Analysis:** Groq Llama 3.3 70B (3 API keys)
    
    **⏱️ समय / Time:**
    - Download: 10-20 सेकंड
    - Transcription: 10-20 सेकंड
    - Analysis: 15-30 सेकंड
    - **कुल:** ~40-70 सेकंड
    
    **⚠️ सामान्य त्रुटियाँ:**
    - **401/403 Error:** Instagram rate limit → 10-15 मिनट प्रतीक्षा करें
    - **Private Account:** Public reels ही download हो सकते हैं
    - **Video Not Found:** URL check करें
    """)

# Analysis Process
if analyze_button:
    if not reel_url:
        st.error("⚠️ कृपया Instagram Reel URL दर्ज करें")
    else:
        st.session_state.current_url = reel_url
        
        progress_container = st.container()
        
        with progress_container:
            try:
                progress_text = st.empty()
                progress_bar = st.progress(0)
                status_box = st.empty()
                
                # Step 1: Download
                status_box.info("📥 रील डाउनलोड हो रही है (yt-dlp → Instaloader)...")
                progress_bar.progress(15)
                
                shortcode, raw_transcript = agent.download_and_extract(
                    reel_url,
                    video_lang=video_language.lower()
                )
                
                progress_text.text("✅ ट्रांसक्रिप्ट निकाली गई")
                progress_bar.progress(35)
                
                # Check existing
                existing = db.get_fact_check(shortcode)
                
                if existing:
                    status_box.success("📂 डेटाबेस में मिला!")
                    progress_bar.progress(100)
                    
                    st.session_state.transcript = existing['transcript']
                    st.session_state.corrected_transcript = existing.get('corrected_transcript', raw_transcript)
                    st.session_state.analysis = existing['analysis']
                    st.session_state.fact_check_id = existing['id']
                else:
                    # Step 2: Correct
                    status_box.info("✍️ चिकित्सा शब्दों को सुधार रहा है...")
                    progress_bar.progress(50)
                    
                    corrected_transcript = checker.correct_transcript(
                        raw_transcript,
                        output_language.lower()
                    )
                    
                    progress_text.text("✅ ट्रांसक्रिप्ट सुधारी गई")
                    progress_bar.progress(65)
                    
                    # Step 3: Analyze
                    status_box.info("🔬 स्वास्थ्य दावों का विश्लेषण...")
                    progress_bar.progress(75)
                    
                    analysis = checker.analyze_claims(
                        corrected_transcript,
                        output_language.lower()
                    )
                    
                    progress_text.text("✅ विश्लेषण पूर्ण")
                    progress_bar.progress(90)
                    
                    # Save
                    fact_check_id = db.save_fact_check(
                        reel_url, shortcode, raw_transcript,
                        analysis,
                        analysis.get('rating', 0)
                    )
                    
                    st.session_state.transcript = raw_transcript
                    st.session_state.corrected_transcript = corrected_transcript
                    st.session_state.analysis = analysis
                    st.session_state.fact_check_id = fact_check_id
                
                status_box.success("✅ विश्लेषण पूर्ण!")
                progress_bar.progress(100)
                
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                error_msg = str(e)
                
                # Custom error handling
                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                st.error(f"❌ त्रुटि / Error:")
                st.code(error_msg)
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Specific error messages
                if "401" in error_msg or "403" in error_msg or "Unauthorized" in error_msg:
                    st.markdown('<div class="tip-box">', unsafe_allow_html=True)
                    st.markdown("""
                    ### 🔴 Instagram Rate Limit Error
                    
                    **समस्या:** Instagram ने अस्थायी रूप से ब्लॉक किया है।
                    
                    **समाधान:**
                    1. ⏰ **10-15 मिनट प्रतीक्षा करें**
                    2. 🔐 Instagram login करें (ऊपर देखें)
                    3. 🌐 दूसरे network से try करें
                    4. 🕐 थोड़ी देर बाद पुनः प्रयास करें
                    
                    यह Instagram की सुरक्षा है, app की समस्या नहीं।
                    """)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                elif "private" in error_msg.lower():
                    st.warning("⚠️ यह private account का reel है। केवल public reels download हो सकते हैं।")
                
                elif "ffmpeg" in error_msg.lower():
                    st.error("FFmpeg नहीं मिला! Streamlit Cloud settings में packages.txt जोड़ें।")
                
                elif "not found" in error_msg.lower() or "404" in error_msg:
                    st.warning("⚠️ Reel नहीं मिला। URL check करें या reel delete हो गया है।")
                
                else:
                    st.info("💡 Tip: URL check करें, internet connection verify करें, या थोड़ी देर बाद try करें।")

# Results Display
if st.session_state.analysis:
    st.markdown("---")
    
    # Metrics
    st.markdown('<div class="section-header"><h3>📊 Analysis Results</h3></div>', unsafe_allow_html=True)
    
    rating = st.session_state.analysis.get('rating', 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("सटीकता / Accuracy", f"{rating:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        if output_language == "Hindi":
            status = "✅ भरोसेमंद" if rating >= 70 else "⚠️ संदिग्ध" if rating >= 40 else "❌ भ्रामक"
        else:
            status = "✅ Trustworthy" if rating >= 70 else "⚠️ Questionable" if rating >= 40 else "❌ Misleading"
        
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("स्थिति / Status", status)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        claim_count = len(st.session_state.analysis.get('claims', []))
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("दावे / Claims", claim_count)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        issue_count = len(st.session_state.analysis.get('key_issues', []))
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("मुद्दे / Issues", issue_count)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Summary
    st.markdown('<div class="section-header"><h3>📋 कार्यकारी सारांश / Summary</h3></div>', unsafe_allow_html=True)
    st.info(st.session_state.analysis.get('summary', 'No summary'))
    
    # Claims
    st.markdown('<div class="section-header"><h3>🔬 विस्तृत दावा विश्लेषण / Claims</h3></div>', unsafe_allow_html=True)
    
    claims = st.session_state.analysis.get('claims', [])
    if claims:
        for i, claim in enumerate(claims, 1):
            verdict = claim.get('verdict', 'UNKNOWN')
            
            if verdict == "TRUE":
                icon, color = "🟢", "green"
            elif verdict == "FALSE":
                icon, color = "🔴", "red"
            elif verdict == "PARTIALLY TRUE":
                icon, color = "🟡", "orange"
            else:
                icon, color = "⚪", "gray"
            
            with st.expander(f"{icon} **दावा {i}:** {claim.get('claim', 'Unknown')}", expanded=(i==1)):
                st.markdown(f"**निर्णय:** :{color}[{verdict}]")
                st.markdown(f"**स्पष्टीकरण:** {claim.get('explanation', 'N/A')}")
                
                sources = claim.get('sources', [])
                if sources:
                    st.markdown("**📚 स्रोत:**")
                    for source in sources:
                        st.markdown(f"- {source}")
    
    # Key Issues
    key_issues = st.session_state.analysis.get('key_issues', [])
    if key_issues:
        st.markdown('<div class="section-header"><h3>⚠️ मुख्य मुद्दे / Issues</h3></div>', unsafe_allow_html=True)
        for issue in key_issues:
            st.warning(f"• {issue}")
    
    # Transcripts
    st.markdown('<div class="section-header"><h3>📝 Transcripts</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("मूल / Original", expanded=False):
            st.text_area("", st.session_state.transcript, height=200, disabled=True, key="orig", label_visibility="collapsed")
    
    with col2:
        with st.expander("सुधारा / Corrected", expanded=False):
            st.text_area("", st.session_state.corrected_transcript or st.session_state.transcript, height=200, disabled=True, key="corr", label_visibility="collapsed")
    
    # Chat
    st.markdown("---")
    st.markdown('<div class="section-header"><h3>💬 प्रश्न पूछें / Ask Questions</h3></div>', unsafe_allow_html=True)
    
    chat_history = db.get_chat_history(st.session_state.fact_check_id)
    
    # Display chat
    for chat in chat_history:
        with st.chat_message("user"):
            st.write(chat['user_message'])
        with st.chat_message("assistant"):
            st.write(chat['assistant_response'])
    
    # Chat input
    if prompt := st.chat_input("कुछ भी पूछें..."):
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("सोच रहा हूँ..."):
                response = checker.chat_about_video(
                    st.session_state.transcript,
                    st.session_state.corrected_transcript or st.session_state.transcript,
                    st.session_state.analysis,
                    prompt,
                    chat_history,
                    output_language.lower()
                )
                st.write(response)
                
                db.save_chat(st.session_state.fact_check_id, prompt, response)

# Footer
st.markdown("---")
st.markdown("""
<p style='text-align: center; color: gray; font-size: 0.9rem;'>
    🚀 Method: yt-dlp (primary) + Instaloader (fallback)<br>
    🔑 Groq (3 API Keys) + Whisper + FFmpeg
</p>
""", unsafe_allow_html=True)