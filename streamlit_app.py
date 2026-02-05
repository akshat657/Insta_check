import streamlit as st
from agent import ReelAgent
from llm_checker import HealthClaimChecker
from database import Database
import json
import os

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
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize components
@st.cache_resource
def init_components():
    try:
        agent = ReelAgent()
        checker = HealthClaimChecker()
        db = Database()
        return agent, checker, db
    except Exception as e:
        st.error(f"Initialization error: {e}")
        st.stop()

agent, checker, db = init_components()

# Session state initialization
if 'fact_check_id' not in st.session_state:
    st.session_state.fact_check_id = None
if 'analysis' not in st.session_state:
    st.session_state.analysis = None
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'current_url' not in st.session_state:
    st.session_state.current_url = ""

# Header
st.markdown('<div class="main-header"><h1>🏥 Instagram Health Claim Fact Checker</h1><p>Debunk health misinformation from Instagram Reels</p></div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    language = st.selectbox("Select Language", ["Hindi", "English"], index=0)
    
    st.markdown("---")
    st.markdown("### 📋 How it works")
    st.markdown("""
    1. 📎 Paste Instagram Reel URL
    2. 🎥 AI extracts transcript
    3. 🔬 Medical LLM analyzes claims
    4. ✅ Get fact-check report
    5. 💬 Chat about the video
    """)
    
    st.markdown("---")
    st.markdown("### 🔑 Powered by")
    st.markdown("- **Groq** (Llama 3.3 70B)")
    st.markdown("- **OpenAI Whisper**")
    st.markdown("- **Streamlit Cloud**")

# Main content
reel_url = st.text_input("📎 Paste Instagram Reel URL", 
                         placeholder="https://www.instagram.com/reel/...",
                         value=st.session_state.current_url)

col1, col2 = st.columns([3, 1])
with col1:
    analyze_button = st.button("🔍 Analyze Reel", type="primary", use_container_width=True)
with col2:
    if st.session_state.analysis:
        if st.button("🔄 Clear", use_container_width=True):
            st.session_state.fact_check_id = None
            st.session_state.analysis = None
            st.session_state.transcript = None
            st.session_state.current_url = ""
            st.rerun()

if analyze_button:
    if not reel_url:
        st.error("⚠️ Please enter a valid Instagram Reel URL")
    else:
        st.session_state.current_url = reel_url
        
        with st.spinner("🔄 Processing..."):
            try:
                # Step 1: Download & Extract
                progress_text = st.empty()
                progress_bar = st.progress(0)
                
                progress_text.text("📥 Downloading reel...")
                progress_bar.progress(25)
                
                shortcode, transcript = agent.download_and_extract(reel_url, language.lower())
                
                progress_text.text("✅ Transcript extracted")
                progress_bar.progress(50)
                
                # Check if already analyzed
                existing = db.get_fact_check(shortcode)
                
                if existing:
                    progress_text.text("📂 Loading from database...")
                    st.session_state.transcript = existing['transcript']
                    st.session_state.analysis = existing['analysis']
                    st.session_state.fact_check_id = existing['id']
                else:
                    progress_text.text("🤖 Analyzing health claims...")
                    progress_bar.progress(75)
                    
                    analysis = checker.analyze_claims(transcript, language.lower())
                    
                    # Save to DB
                    fact_check_id = db.save_fact_check(
                        reel_url, shortcode, transcript, 
                        analysis,
                        analysis.get('rating', 0)
                    )
                    
                    st.session_state.transcript = transcript
                    st.session_state.analysis = analysis
                    st.session_state.fact_check_id = fact_check_id
                
                progress_text.text("✅ Analysis complete!")
                progress_bar.progress(100)
                
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Tip: Make sure the URL is a public Instagram Reel")

# Display results
if st.session_state.analysis:
    st.markdown("---")
    
    # Overall Rating
    rating = st.session_state.analysis.get('rating', 0)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Overall Accuracy", f"{rating:.1f}%")
    with col2:
        status = "✅ Trustworthy" if rating >= 70 else "⚠️ Questionable" if rating >= 40 else "❌ Misleading"
        st.metric("Status", status)
    with col3:
        claim_count = len(st.session_state.analysis.get('claims', []))
        st.metric("Claims Analyzed", claim_count)
    
    # Summary
    st.markdown("### 📋 Executive Summary")
    st.info(st.session_state.analysis.get('summary', 'No summary available'))
    
    # Claims Analysis
    st.markdown("### 🔬 Detailed Claim Analysis")
    
    claims = st.session_state.analysis.get('claims', [])
    if claims:
        for i, claim in enumerate(claims, 1):
            verdict = claim.get('verdict', 'UNKNOWN')
            
            # Verdict styling
            if verdict == "TRUE":
                icon = "🟢"
                color = "green"
            elif verdict == "FALSE":
                icon = "🔴"
                color = "red"
            elif verdict == "PARTIALLY TRUE":
                icon = "🟡"
                color = "orange"
            else:
                icon = "⚪"
                color = "gray"
            
            with st.expander(f"{icon} **Claim {i}:** {claim.get('claim', 'Unknown claim')}", expanded=(i==1)):
                st.markdown(f"**Verdict:** :{color}[{verdict}]")
                st.markdown(f"**Explanation:** {claim.get('explanation', 'No explanation')}")
                
                sources = claim.get('sources', [])
                if sources:
                    st.markdown("**📚 Sources:**")
                    for source in sources:
                        st.markdown(f"- {source}")
    else:
        st.warning("No specific claims identified")
    
    # Key Issues
    key_issues = st.session_state.analysis.get('key_issues', [])
    if key_issues:
        st.markdown("### ⚠️ Key Issues Identified")
        for issue in key_issues:
            st.warning(f"• {issue}")
    
    # Transcript
    with st.expander("📝 View Full Transcript"):
        st.text_area("Transcript", st.session_state.transcript, height=200, disabled=True)
    
    # Chat Interface
    st.markdown("---")
    st.markdown("### 💬 Ask Questions About This Video")
    
    # Load chat history
    chat_history = db.get_chat_history(st.session_state.fact_check_id)
    
    # Display chat history
    for chat in chat_history:
        with st.chat_message("user"):
            st.write(chat['user_message'])
        with st.chat_message("assistant"):
            st.write(chat['assistant_response'])
    
    # Chat input
    if prompt := st.chat_input("Ask anything about this video..."):
        # Display user message
        with st.chat_message("user"):
            st.write(prompt)
        
        # Generate and display response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                response = checker.chat_about_video(
                    st.session_state.transcript,
                    st.session_state.analysis,
                    prompt,
                    chat_history,
                    language.lower()
                )
                st.write(response)
                
                # Save to DB
                db.save_chat(st.session_state.fact_check_id, prompt, response)

# Footer
st.markdown("---")
st.markdown("<p style='text-align: center; color: gray;'>Built with ❤️ using Streamlit | Powered by Groq & Whisper</p>", unsafe_allow_html=True)