import streamlit as st
import json
import os
import sys
import pandas as pd
from datetime import datetime
from Phase1.scraper import fetch_reviews, save_reviews
from Phase2.analyzer import GroqAnalyzer
from Phase4.email_generator import generate_html_email
from Phase4.mailer import send_pulse_email
from dotenv import load_dotenv

# Page configuration
st.set_page_config(
    page_title="GROWW Weekly Pulse",
    page_icon="🍀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for GROWW-themed look
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main {
        background-color: #FFFFFF;
        padding-top: 2rem;
    }
    
    /* Global Card styling */
    .stMetric, .theme-card, .quote-card, .action-card {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 16px;
        border: 1px solid #EBEEF2;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 20px;
    }

    /* Groww Specific Accents */
    .stButton>button {
        background-color: #00d09c;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        border: none;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #00b386;
        border: none;
        color: white;
        transform: translateY(-1px);
    }
    
    .theme-card {
        border-left: 6px solid #00d09c;
    }
    
    .quote-card {
        font-style: italic;
        color: #44475B;
        border-left: 4px solid #5367F5;
        background-color: #F8F9FA;
    }
    
    .action-card {
        background-color: #F0FAF8;
        border-color: #00d09c;
    }
    
    h1, h2, h3 {
        color: #44475B;
        font-weight: 700;
    }
    
    .stMetric label {
        color: #7C7E8C !important;
        font-weight: 500 !important;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #F8F9FA;
        border-right: 1px solid #EBEEF2;
    }
    
    .sync-badge {
        background-color: #E6FBF7;
        color: #00d09c;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

def load_local_data():
    """Loads existing reviews and analyzer report if they exist."""
    reviews_data = []
    report = None
    
    # Paths relative to root
    reviews_path = "reviews.json"
    report_path = os.path.join("Phase2", "pulse_report.json")
    
    if os.path.exists(reviews_path):
        with open(reviews_path, "r", encoding="utf-8") as f:
            reviews_data = json.load(f)
            
    if os.path.exists(report_path):
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
            
    return reviews_data, report

def get_secret(key, default=None):
    """Helper to get secret from st.secrets or environment variable."""
    if key in st.secrets:
        return st.secrets[key]
    return os.getenv(key, default)

def main():
    # Load environment variables if .env exists (local run)
    if os.path.exists(".env"):
        load_dotenv()
        
    # Load existing data on startup
    existing_reviews, existing_report = load_local_data()
    if 'report' not in st.session_state and existing_report:
        st.session_state['report'] = existing_report
        st.session_state['reviews_count'] = len(existing_reviews)
        st.session_state['avg_rating'] = pd.DataFrame(existing_reviews)['rating'].mean() if existing_reviews else 0

    st.sidebar.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 20px;">
            <div style="background-color: #00d09c; width: 40px; height: 40px; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin-right: 12px;">
                <span style="color: white; font-weight: 800; font-size: 20px;">G</span>
            </div>
            <h2 style="margin: 0; font-size: 24px; color: #44475B;">Groww Pulse</h2>
        </div>
    """, unsafe_allow_html=True)
    
    app_id = st.sidebar.text_input("App ID", value="com.nextbillion.groww")
    weeks = st.sidebar.slider("Weeks to analyze", 1, 12, 12)
    
    st.markdown(f'<div class="sync-badge">Last Synced: {datetime.now().strftime("%I:%M %p")}</div>', unsafe_allow_html=True)
    st.title("📈 Weekly Pulse Report")
    st.markdown("<p style='color: #7C7E8C; margin-top: -10px;'>High-impact insights from user feedback.</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Check for API Key (Secrets compatible)
    api_key = get_secret("GROQ_API_KEY")
    
    if not api_key:
        st.sidebar.warning("⚠️ No Groq API Key found. Set GROQ_API_KEY in Streamlit Secrets or .env")
    
    if st.sidebar.button("🔄 Sync & Analyze"):
        with st.spinner("Fetching latest reviews..."):
            reviews_data = fetch_reviews(app_id=app_id, weeks=weeks)
            # Save to standard root path
            save_reviews(reviews_data, filename="reviews.json") 
        
        if api_key:
            with st.spinner("Analyzing with Groq AI..."):
                analyzer = GroqAnalyzer(api_key=api_key)
                report = analyzer.analyze_reviews(reviews_data)
                
                # Save report
                report_path = os.path.join("Phase2", "pulse_report.json")
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                with open(report_path, "w", encoding="utf-8") as f:
                    json.dump(report, f, indent=4)
                    
                st.session_state['report'] = report
        else:
            st.error("Cannot run AI analysis without Groq API Key.")
            
        st.session_state['reviews_count'] = len(reviews_data)
        st.session_state['avg_rating'] = pd.DataFrame(reviews_data)['rating'].mean() if reviews_data else 0

    # Display Report
    if 'report' in st.session_state:
        report = st.session_state['report']
        
        # Executive Summary
        if "pulse_summary" in report:
            st.markdown(f"""
            <div style="background-color: #e6f3ff; padding: 20px; border-radius: 10px; border-left: 5px solid #2196F3; margin-bottom: 25px;">
                <h4 style="margin-top: 0; color: #0D47A1;">📝 Executive Summary</h4>
                <p style="font-size: 1.1em; color: #1565C0;">{report['pulse_summary']}</p>
            </div>
            """, unsafe_allow_html=True)

        # Top Stats
        # Top Stats - Custom Styled Cards to prevent truncation
        col1, col2, col3 = st.columns(3)
        reviews_count = st.session_state.get('reviews_count', 0)
        avg_rating = st.session_state.get('avg_rating', 0)
        pulse_date = datetime.now().strftime("%d %b, %Y")
        
        with col1:
            st.markdown(f"""
                <div class="stMetric">
                    <div style="color: #7C7E8C; font-size: 0.9em; font-weight: 500; margin-bottom: 8px;">Total Reviews Analyzed</div>
                    <div style="color: #44475B; font-size: 2.2em; font-weight: 700;">{reviews_count}</div>
                </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
                <div class="stMetric">
                    <div style="color: #7C7E8C; font-size: 0.9em; font-weight: 500; margin-bottom: 8px;">Average Rating</div>
                    <div style="color: #44475B; font-size: 2.2em; font-weight: 700;">{avg_rating:.2f} <span style="font-size: 0.8em;">⭐</span></div>
                </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
                <div class="stMetric">
                    <div style="color: #7C7E8C; font-size: 0.9em; font-weight: 500; margin-bottom: 8px;">Pulse Date</div>
                    <div style="color: #44475B; font-size: 1.8em; font-weight: 700; white-space: nowrap;">{pulse_date}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("### 🎯 Top Feedback Themes")
        themes = report.get('themes', [])
        if themes:
            theme_cols = st.columns(len(themes))
            for i, theme in enumerate(themes):
                sentiment = theme.get('sentiment', 'Neutral')
                sentiment_colors = {
                    "Positive": "#E8F5E9",
                    "Negative": "#FFEBEE",
                    "Neutral": "#FFF3E0"
                }
                border_colors = {
                    "Positive": "#4CAF50",
                    "Negative": "#F44336",
                    "Neutral": "#FF9800"
                }
                bg = sentiment_colors.get(sentiment, "#F5F5F5")
                border = border_colors.get(sentiment, "#9E9E9E")
                
                with theme_cols[i]:
                    st.markdown(f"""
                    <div style="background-color: #FFFFFF; padding: 24px; border-radius: 16px; border: 1px solid #EBEEF2; border-top: 6px solid {border}; height: 100%; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                        <h4 style="margin-top: 0; color: #44475B; margin-bottom: 8px;">{theme['name']}</h4>
                        <p style="color: #7C7E8C; font-size: 0.9em; line-height: 1.5;">{theme['description']}</p>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 15px; border-top: 1px solid #F1F3F6; padding-top: 12px;">
                            <span style="font-weight: 600; color: {border}; font-size: 0.85em;">{sentiment.upper()}</span>
                            <span style="color: #7C7E8C; font-size: 0.8em; font-weight: 500;">Impact: {theme.get('impact_score', 'N/A')}/10</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.markdown("### 💬 User Voices")
            for quote in report.get('top_quotes', []):
                st.markdown(f"""
                <div class="quote-card">
                    "{quote}"
                </div>
                """, unsafe_allow_html=True)

        with col_right:
            st.markdown("### 🚀 Growth Roadmap")
            for idea in report.get('action_ideas', []):
                st.markdown(f"""
                <div class="action-card">
                    <span style="color: #00d09c; font-weight: 700; margin-right: 8px;">•</span> {idea}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("📧 Generate Premium HTML Email"):
            with st.spinner("Generating premium draft..."):
                st.success("Premium HTML email draft generated!")
                html_email = generate_html_email(report)
                st.session_state['last_html_email'] = html_email
                
                # Save for Phase 4 records
                email_draft_path = os.path.join("Phase4", "email_draft.html")
                os.makedirs(os.path.dirname(email_draft_path), exist_ok=True)
                with open(email_draft_path, "w", encoding="utf-8") as f:
                    f.write(html_email)

        if 'last_html_email' in st.session_state:
            html_email = st.session_state['last_html_email']
            st.markdown("---")
            st.write("### 📝 Email Preview")
            st.components.v1.html(html_email, height=600, scrolling=True)
            
            with st.expander("📄 View Source HTML"):
                st.code(html_email, language="html")
                
            st.markdown("---")
            if st.button("🚀 Send Pulse to My Email"):
                with st.spinner("Sending email..."):
                    # Standard paths in root
                    reviews_json_path = "reviews.json"
                    attachment_path = "reviews_report.csv"
                    
                    if os.path.exists(reviews_json_path):
                        with open(reviews_json_path, "r", encoding="utf-8") as f:
                            reviews_data = json.load(f)
                        pd.DataFrame(reviews_data).to_csv(attachment_path, index=False, encoding='utf-8-sig')
                    
                    # Fail-safe: Handle both old (bool) and new (tuple) return values
                    # pass secrets as needed
                    result = send_pulse_email(
                        st.session_state['last_html_email'], 
                        attachment_path=attachment_path
                    )
                    
                    if isinstance(result, tuple):
                        success, message = result
                    else:
                        success = result
                        message = "Check SMTP settings" if not success else "Success"
                        
                    if success:
                        recipient = get_secret('RECIPIENT_EMAIL')
                        st.success(f"Pulse sent to {recipient}!")
                    else:
                        st.error(f"Failed to send email: {message}")
                        st.info("Ensure you have set up your SMTP secrets in Streamlit Cloud.")

if __name__ == "__main__":
    main()
