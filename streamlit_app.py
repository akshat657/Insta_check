import streamlit as st
from agent import ReelAgent
from llm_checker import HealthClaimChecker
from database import Database
import time

st.set_page_config(
    page_title="Instagram Health Fact Checker",
    page_icon="🏥",
    layout="wide"
)

# CSS
st.markdown("""
<style>
    .setup-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
    .step-box {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    .main-header {
        text-align: center;
        padding: 1.5rem;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
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
    }
</style>
""", unsafe_allow_html=True)

# Check session
try:
    session_configured = bool(st.secrets.get("INSTAGRAM_SESSION"))
except:
    session_configured = False

# Setup guide if no session
if not session_configured:
    st.markdown('<div class="setup-box">', unsafe_allow_html=True)
    st.markdown("""
    # 🔧 पहली बार सेटअप / First Time Setup Required
    
    **Instagram session upload करें to avoid 401/403 errors**
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    with st.expander("📋 **Step-by-Step Setup Guide** (Click करें)", expanded=True):
        st.markdown("""
        <div class="step-box">
        <h3>Step 1: अपने Computer पर Session Generate करें</h3>
        
        1. **Download** `local_session_generator.py` file
        2. **अपने computer पर चलाएं** (NOT on cloud):
```bash
        pip install instaloader
        python local_session_generator.py
```
        
        3. Instagram **username** और **password** enter करें
        4. Base64 string **copy** करें (auto-saved in `streamlit_secrets.txt`)
        </div>
        
        <div class="step-box">
        <h3>Step 2: Streamlit Cloud में Upload करें</h3>
        
        1. Go to: **Streamlit Cloud → Your App → Settings → Secrets**
        2. निम्न paste करें:
```toml
        INSTAGRAM_SESSION = "your_base64_string_here"
        INSTAGRAM_USERNAME = "your_username"
        
        GROQ_API_KEY_1 = "gsk_your_key_1"
        GROQ_API_KEY_2 = "gsk_your_key_2"
        GROQ_API_KEY_3 = "gsk_your_key_3"
        
        # Optional: Residential Proxy
        # RESIDENTIAL_PROXY = "http://user:pass@proxy.com:port"
```
        
        3. **Save** → App restart होगा
        </div>
        
        <div class="step-box">
        <h3>Step 3: Verify करें</h3>
        
        - Page reload करें
        - "✅ Session Loaded" दिखना चाहिए
        - अब errors नहीं आएंगे!
        </div>
        """, unsafe_allow_html=True)
        
        st.warning("⚠️ **Important Notes:**\n- Instagram में 2FA disable रखें\n- Session ~30 days valid\n- Private accounts work नहीं करेंगे")
    
    st.stop()

# Initialize
@st.cache_resource
def init_components():
    try:
        print("\n" + "="*60)
        print("INITIALIZING")
        print("="*60)
        agent = ReelAgent()
        checker = HealthClaimChecker()
        db = Database()
        print("="*60 + "\n")
        return agent, checker, db
    except Exception as e:
        st.error(f"❌ Init error: {e}")
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

# Header
st.markdown('''
<div class="main-header">
    <h1>🏥 Instagram Health Claim Fact Checker</h1>
    <p>Session-Based Download + AI Analysis</p>
</div>
''', unsafe_allow_html=True)

# Status
if session_configured:
    st.success("✅ Instagram Session Active")
else:
    st.error("❌ Session Not Found - Setup required above")

# Input
st.markdown('<div class="section-header"><h3>📎 Enter Details</h3></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    reel_url = st.text_input(
        "URL",
        placeholder="https://www.instagram.com/reel/...",
        value=st.session_state.current_url,
        label_visibility="collapsed"
    )

with col2:
    video_language = st.selectbox("Video Lang", ["Hindi", "English"], index=0)

with col3:
    output_language = st.selectbox("Output Lang", ["Hindi", "English"], index=0)

# Buttons
col1, col2 = st.columns([3, 1])

with col1:
    analyze_button = st.button("🔍 Analyze", type="primary", use_container_width=True)

with col2:
    if st.session_state.analysis:
        if st.button("🔄 New", use_container_width=True):
            for key in ['fact_check_id', 'analysis', 'transcript', 'corrected_transcript', 'current_url']:
                st.session_state[key] = None if key != 'current_url' else ""
            st.rerun()

# Process
if analyze_button:
    if not reel_url:
        st.error("⚠️ URL required")
    else:
        st.session_state.current_url = reel_url
        
        try:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            status_box = st.empty()
            
            status_box.info("📥 Downloading...")
            progress_bar.progress(15)
            
            shortcode, raw_transcript = agent.download_and_extract(reel_url, video_lang=video_language.lower())
            
            progress_text.text("✅ Transcript extracted")
            progress_bar.progress(35)
            
            existing = db.get_fact_check(shortcode)
            
            if existing:
                status_box.success("📂 Found in DB")
                progress_bar.progress(100)
                
                st.session_state.transcript = existing['transcript']
                st.session_state.corrected_transcript = existing.get('corrected_transcript', raw_transcript)
                st.session_state.analysis = existing['analysis']
                st.session_state.fact_check_id = existing['id']
            else:
                status_box.info("✍️ Correcting...")
                progress_bar.progress(50)
                
                corrected_transcript = checker.correct_transcript(raw_transcript, output_language.lower())
                
                progress_text.text("✅ Corrected")
                progress_bar.progress(65)
                
                status_box.info("🔬 Analyzing...")
                progress_bar.progress(75)
                
                analysis = checker.analyze_claims(corrected_transcript, output_language.lower())
                
                progress_text.text("✅ Analysis done")
                progress_bar.progress(90)
                
                fact_check_id = db.save_fact_check(reel_url, shortcode, raw_transcript, analysis, analysis.get('rating', 0))
                
                st.session_state.transcript = raw_transcript
                st.session_state.corrected_transcript = corrected_transcript
                st.session_state.analysis = analysis
                st.session_state.fact_check_id = fact_check_id
            
            status_box.success("✅ Complete!")
            progress_bar.progress(100)
            
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            
            if "401" in str(e) or "403" in str(e):
                st.warning("""
                **🔴 Authentication Error**
                
                Solutions:
                1. Session upload करें (main solution)
                2. 15-20 min wait करें
                3. Proxy add करें (optional)
                """)

# Results
if st.session_state.analysis:
    st.markdown("---")
    
    st.markdown('<div class="section-header"><h3>📊 Results</h3></div>', unsafe_allow_html=True)
    
    rating = st.session_state.analysis.get('rating', 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Accuracy", f"{rating:.1f}%")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        status = "✅ Trustworthy" if rating >= 70 else "⚠️ Questionable" if rating >= 40 else "❌ Misleading"
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Status", status)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        claim_count = len(st.session_state.analysis.get('claims', []))
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Claims", claim_count)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        issue_count = len(st.session_state.analysis.get('key_issues', []))
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Issues", issue_count)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Summary
    st.markdown('<div class="section-header"><h3>📋 Summary</h3></div>', unsafe_allow_html=True)
    st.info(st.session_state.analysis.get('summary', 'N/A'))
    
    # Claims
    st.markdown('<div class="section-header"><h3>🔬 Claims</h3></div>', unsafe_allow_html=True)
    
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
            
            with st.expander(f"{icon} **Claim {i}:** {claim.get('claim', 'Unknown')}", expanded=(i==1)):
                st.markdown(f"**Verdict:** :{color}[{verdict}]")
                st.markdown(f"**Explanation:** {claim.get('explanation', 'N/A')}")
                
                sources = claim.get('sources', [])
                if sources:
                    st.markdown("**📚 Sources:**")
                    for source in sources:
                        st.markdown(f"- {source}")
    
    # Issues
    key_issues = st.session_state.analysis.get('key_issues', [])
    if key_issues:
        st.markdown('<div class="section-header"><h3>⚠️ Issues</h3></div>', unsafe_allow_html=True)
        for issue in key_issues:
            st.warning(f"• {issue}")
    
    # Transcripts
    st.markdown('<div class="section-header"><h3>📝 Transcripts</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("Original"):
            st.text_area("", st.session_state.transcript, height=150, disabled=True, key="orig", label_visibility="collapsed")
    
    with col2:
        with st.expander("Corrected"):
            st.text_area("", st.session_state.corrected_transcript or st.session_state.transcript, height=150, disabled=True, key="corr", label_visibility="collapsed")
    
    # Chat
    st.markdown("---")
    st.markdown('<div class="section-header"><h3>💬 Ask Questions</h3></div>', unsafe_allow_html=True)
    
    chat_history = db.get_chat_history(st.session_state.fact_check_id)
    
    for chat in chat_history:
        with st.chat_message("user"):
            st.write(chat['user_message'])
        with st.chat_message("assistant"):
            st.write(chat['assistant_response'])
    
    if prompt := st.chat_input("Ask anything..."):
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
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
<p style='text-align: center; color: gray;'>
    🔒 Session-Based + 3 Groq Keys + Whisper + FFmpeg
</p>
""", unsafe_allow_html=True)