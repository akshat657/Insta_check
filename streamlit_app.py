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
        st.info("💡 Make sure to add API keys in Streamlit Secrets:\n- RAPIDAPI_KEY\n- GROQ_API_KEY_1/2/3")
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
    <p>RapidAPI + Google Speech Recognition + Groq AI</p>
</div>
''', unsafe_allow_html=True)

# Info
st.info("ℹ️ **How it works:** RapidAPI downloads video → Google Speech recognizes audio → Groq AI analyzes health claims")

# Input
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
        help="Language spoken in video"
    )

with col3:
    output_language = st.selectbox(
        "Output Language",
        ["Hindi", "English"],
        index=0,
        help="Analysis language"
    )

# Buttons
col1, col2 = st.columns([3, 1])

with col1:
    analyze_button = st.button("🔍 Analyze Reel", type="primary", use_container_width=True)

with col2:
    if st.session_state.analysis:
        if st.button("🔄 New Analysis", use_container_width=True):
            for key in ['fact_check_id', 'analysis', 'transcript', 'corrected_transcript', 'current_url']:
                st.session_state[key] = None if key != 'current_url' else ""
            st.rerun()

# Process
if analyze_button:
    if not reel_url:
        st.error("⚠️ Please enter Instagram Reel URL")
    else:
        st.session_state.current_url = reel_url
        
        try:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            status_box = st.empty()
            
            # Step 1: Download
            status_box.info("📥 Downloading via RapidAPI...")
            progress_bar.progress(15)
            
            shortcode, raw_transcript = agent.download_and_extract(
                reel_url,
                video_lang=video_language.lower()
            )
            
            progress_text.text("✅ Transcript extracted")
            progress_bar.progress(35)
            
            # Check existing
            existing = db.get_fact_check(shortcode)
            
            if existing:
                status_box.success("📂 Found in database")
                progress_bar.progress(100)
                
                st.session_state.transcript = existing['transcript']
                st.session_state.corrected_transcript = existing.get('corrected_transcript', raw_transcript)
                st.session_state.analysis = existing['analysis']
                st.session_state.fact_check_id = existing['id']
            else:
                # Step 2: Correct
                status_box.info("✍️ Correcting medical terms...")
                progress_bar.progress(50)
                
                corrected_transcript = checker.correct_transcript(
                    raw_transcript,
                    output_language.lower()
                )
                
                progress_text.text("✅ Transcript corrected")
                progress_bar.progress(65)
                
                # Step 3: Analyze
                status_box.info("🔬 Analyzing health claims...")
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
            
            status_box.success("✅ Analysis complete!")
            progress_bar.progress(100)
            
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            
            if "RAPIDAPI_KEY" in str(e):
                st.warning("🔑 Add RAPIDAPI_KEY in Streamlit Secrets")
            elif "rate_limit" in str(e).lower():
                st.warning("⚠️ API rate limit reached. Wait and try again.")
            elif "No speech detected" in str(e):
                st.warning("🔇 No speech found in video. Check if:\n- Video has audio\n- Audio is clear\n- Language is correct")

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
    st.markdown('<div class="section-header"><h3>🔬 Claims Analysis</h3></div>', unsafe_allow_html=True)
    
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
        st.markdown('<div class="section-header"><h3>⚠️ Key Issues</h3></div>', unsafe_allow_html=True)
        for issue in key_issues:
            st.warning(f"• {issue}")
    
    # Transcripts
    st.markdown('<div class="section-header"><h3>📝 Transcripts</h3></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("Original Transcript"):
            st.text_area("", st.session_state.transcript, height=150, disabled=True, key="orig", label_visibility="collapsed")
    
    with col2:
        with st.expander("Corrected Transcript"):
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
    
    if prompt := st.chat_input("Ask anything about this video..."):
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
    🚀 RapidAPI + Google Speech Recognition + Groq (3 Keys)
</p>
""", unsafe_allow_html=True)