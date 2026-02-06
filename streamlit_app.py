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
    .debug-box {
        background: #fff3cd;
        border: 1px solid #ffc107;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .setup-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #2196f3;
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
        st.error(f"❌ Initialization Error: {e}")
        
        # Show setup guide if API keys missing
        if "RAPIDAPI_KEY" in str(e):
            st.markdown('<div class="setup-box">', unsafe_allow_html=True)
            st.markdown("""
            ## 🔧 First Time Setup Required
            
            ### ⚠️ RapidAPI Key Missing
            
            **Steps to add API keys:**
            
            1. **Get RapidAPI Key** (Free):
               - Go to: https://rapidapi.com/
               - Sign up
               - Subscribe to: **Social Media Video Downloader**
               - Copy your API key
            
            2. **Get Groq API Keys** (Free):
               - Go to: https://console.groq.com/keys
               - Create 3 API keys
            
            3. **Add to Streamlit Secrets**:
               - Go to: **Streamlit Cloud → Your App → Settings → Secrets**
               - Paste:
```toml
               RAPIDAPI_KEY = "your_rapidapi_key_here"
               
               GROQ_API_KEY_1 = "gsk_your_key_1"
               GROQ_API_KEY_2 = "gsk_your_key_2"
               GROQ_API_KEY_3 = "gsk_your_key_3"
```
            
            4. **Save** → App will restart
            
            ✅ **No Instagram login needed!** RapidAPI handles everything.
            """)
            st.markdown('</div>', unsafe_allow_html=True)
        
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
    <p style="font-size: 1.1rem; margin-top: 0.5rem;">
        Debunk Health Misinformation from Instagram Reels
    </p>
    <p style="font-size: 0.9rem; opacity: 0.9; margin-top: 0.5rem;">
        Powered by: RapidAPI + Google Speech Recognition + Groq AI
    </p>
</div>
''', unsafe_allow_html=True)

# How it works
with st.expander("ℹ️ How it works", expanded=False):
    st.markdown("""
    ### 🔄 Process Flow:
    
    1. **📥 Download**: RapidAPI downloads Instagram Reel (no login needed!)
    2. **🎤 Transcribe**: Google Speech Recognition extracts audio → text
    3. **✍️ Correct**: Groq AI fixes medical terminology
    4. **🔬 Analyze**: Groq AI fact-checks health claims with sources
    5. **💬 Chat**: Ask follow-up questions about the video
    
    ### 🔑 Technology Stack:
    - **RapidAPI** - Instagram video downloader
    - **Google Speech API** - Hindi/English transcription (Devanagari)
    - **Groq** - Llama 3.3 70B (3 API keys for reliability)
    - **Streamlit** - Web interface
    
    ### ⚠️ Limitations:
    - Only public Instagram reels
    - Clear audio required
    - Hindi (Devanagari) and English only
    """)

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
        help="भाषा जो वीडियो में बोली गई है"
    )

with col3:
    output_language = st.selectbox(
        "Output Language",
        ["Hindi", "English"],
        index=0,
        help="रिपोर्ट की भाषा"
    )

# Action Buttons
col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    analyze_button = st.button(
        "🔍 विश्लेषण करें / Analyze Reel", 
        type="primary", 
        use_container_width=True
    )

with col2:
    force_refresh = st.button(
        "🔄 Force Refresh", 
        use_container_width=True, 
        help="Clear cache और नया analysis"
    )

with col3:
    if st.session_state.analysis:
        if st.button("🆕 New Analysis", use_container_width=True):
            for key in ['fact_check_id', 'analysis', 'transcript', 'corrected_transcript', 'current_url']:
                st.session_state[key] = None if key != 'current_url' else ""
            st.rerun()

# Force refresh logic
if force_refresh and reel_url:
    try:
        shortcode = agent._extract_shortcode(reel_url)
        db.clear_cache(shortcode)
        
        for key in ['fact_check_id', 'analysis', 'transcript', 'corrected_transcript']:
            st.session_state[key] = None
        
        st.success(f"✅ Cache cleared for {shortcode}. Click 'Analyze' to re-process.")
        
    except Exception as e:
        st.error(f"Error: {e}")

# Analysis Process
if analyze_button:
    if not reel_url:
        st.error("⚠️ कृपया Instagram Reel URL दर्ज करें / Please enter URL")
    else:
        st.session_state.current_url = reel_url
        
        try:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            status_box = st.empty()
            
            # Step 1: Download & Transcribe
            status_box.info("📥 Downloading reel via RapidAPI...")
            progress_bar.progress(15)
            
            shortcode, raw_transcript = agent.download_and_extract(
                reel_url,
                video_lang=video_language.lower()
            )
            
            # Debug info
            if raw_transcript:
                st.markdown('<div class="debug-box">', unsafe_allow_html=True)
                
                # Script detection
                devanagari_count = sum(1 for c in raw_transcript if '\u0900' <= c <= '\u097F')
                arabic_count = sum(1 for c in raw_transcript if '\u0600' <= c <= '\u06FF')
                english_count = sum(1 for c in raw_transcript if c.isalpha() and c.isascii())
                
                st.markdown(f"""
                **🔍 Debug Information:**
                - Shortcode: `{shortcode}`
                - Transcript length: `{len(raw_transcript)}` characters
                - Devanagari chars: {devanagari_count}
                - Arabic/Urdu chars: {arabic_count}
                - English chars: {english_count}
                - Script: {'✅ Devanagari' if devanagari_count > arabic_count else '⚠️ Not Devanagari'}
                """)
                st.markdown('</div>', unsafe_allow_html=True)
            
            progress_text.text("✅ Transcript extracted")
            progress_bar.progress(35)
            
            # Check cache
            existing = db.get_fact_check(shortcode)
            
            if existing:
                st.warning(f"📂 Found cached analysis. Click 'Force Refresh' for new analysis.")
                progress_bar.progress(100)
                
                st.session_state.transcript = existing['transcript']
                st.session_state.corrected_transcript = existing.get('corrected_transcript', raw_transcript)
                st.session_state.analysis = existing['analysis']
                st.session_state.fact_check_id = existing['id']
            else:
                # Fresh analysis
                status_box.info("✍️ Correcting medical terminology...")
                progress_bar.progress(50)
                
                corrected_transcript = checker.correct_transcript(
                    raw_transcript,
                    output_language.lower()
                )
                
                progress_text.text("✅ Transcript corrected")
                progress_bar.progress(65)
                
                status_box.info("🔬 Analyzing health claims with AI...")
                progress_bar.progress(75)
                
                analysis = checker.analyze_claims(
                    corrected_transcript,
                    output_language.lower()
                )
                
                progress_text.text("✅ Analysis complete")
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
            
            status_box.success("✅ विश्लेषण पूर्ण! / Analysis complete!")
            progress_bar.progress(100)
            
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            
            # Specific error handling
            if "RAPIDAPI_KEY" in str(e):
                st.warning("🔑 RapidAPI key missing. Add in Streamlit Secrets.")
            elif "rate_limit" in str(e).lower():
                st.warning("⚠️ API rate limit reached. Wait a few minutes.")
            elif "No speech detected" in str(e):
                st.warning("🔇 No clear audio found. Check:\n- Video has speech\n- Audio is clear\n- Correct language selected")
            else:
                st.info("💡 Tip: Check URL is correct and reel is public")

# Results Display
if st.session_state.analysis:
    st.markdown("---")
    
    # Metrics
    st.markdown('<div class="section-header"><h3>📊 Analysis Results / विश्लेषण परिणाम</h3></div>', unsafe_allow_html=True)
    
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
    st.markdown('<div class="section-header"><h3>📋 सारांश / Summary</h3></div>', unsafe_allow_html=True)
    st.info(st.session_state.analysis.get('summary', 'N/A'))
    
    # Claims Analysis
    st.markdown('<div class="section-header"><h3>🔬 विस्तृत विश्लेषण / Detailed Analysis</h3></div>', unsafe_allow_html=True)
    
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
                st.markdown(f"**निर्णय / Verdict:** :{color}[{verdict}]")
                st.markdown(f"**स्पष्टीकरण / Explanation:** {claim.get('explanation', 'N/A')}")
                
                sources = claim.get('sources', [])
                if sources:
                    st.markdown("**📚 स्रोत / Sources:**")
                    for source in sources:
                        st.markdown(f"- {source}")
    else:
        st.warning("कोई विशिष्ट दावे नहीं मिले / No specific claims identified")
    
    # Key Issues
    key_issues = st.session_state.analysis.get('key_issues', [])
    if key_issues:
        st.markdown('<div class="section-header"><h3>⚠️ मुख्य मुद्दे / Key Issues</h3></div>', unsafe_allow_html=True)
        for issue in key_issues:
            st.warning(f"• {issue}")
    
    # Transcripts
    st.markdown('<div class="section-header"><h3>📝 ट्रांसक्रिप्ट / Transcripts</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("मूल ट्रांसक्रिप्ट / Original (Google Speech)", expanded=False):
            st.text_area("", st.session_state.transcript, height=200, disabled=True, key="orig", label_visibility="collapsed")
    
    with col2:
        with st.expander("सुधारा हुआ / Corrected (Groq AI)", expanded=False):
            st.text_area("", st.session_state.corrected_transcript or st.session_state.transcript, height=200, disabled=True, key="corr", label_visibility="collapsed")
    
    # Chat Interface
    st.markdown("---")
    st.markdown('<div class="section-header"><h3>💬 प्रश्न पूछें / Ask Questions</h3></div>', unsafe_allow_html=True)
    
    chat_history = db.get_chat_history(st.session_state.fact_check_id)
    
    # Display chat history
    for chat in chat_history:
        with st.chat_message("user"):
            st.write(chat['user_message'])
        with st.chat_message("assistant"):
            st.write(chat['assistant_response'])
    
    # Chat input
    if prompt := st.chat_input("कुछ भी पूछें... / Ask anything..."):
        with st.chat_message("user"):
            st.write(prompt)
        
        with st.chat_message("assistant"):
            with st.spinner("सोच रहा हूँ... / Thinking..."):
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
<p style='text-align: center; color: #666; font-size: 0.9rem;'>
    🚀 Powered by: RapidAPI + Google Speech (Devanagari) + Groq Llama 3.3 70B<br>
    ❤️ Built with Streamlit | No Instagram login required!
</p>
""", unsafe_allow_html=True)