import os
import sys
import logging
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Dynamic python path resolution: add feedback_intelligence root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import local system components
from src.storage.db import (
    init_db,
    insert_reviews,
    get_filtered_reviews,
    update_priority_scores
)
from src.ingestion.google_play import fetch_google_play_reviews
from src.ingestion.app_store import fetch_app_store_reviews
from src.ingestion.csv_loader import load_csv_feedback
from src.processing.cleaner import clean_text
from src.processing.sentiment import analyze_sentiment
from src.processing.categorizer import categorize_feedback
from src.intelligence.trend import calculate_trends
from src.intelligence.priority import calculate_priority_scores
from src.reporting.pdf_report import generate_pdf_report

# Configure logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize DB on load
init_db()

# --- Page Setup ---
st.set_page_config(
    page_title="Feedback Intelligence System",
    page_icon="📊",
    layout="wide"
)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .header-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 2rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    .header-banner h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.025em;
        background: linear-gradient(to right, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .header-banner p {
        margin: 0.5rem 0 0 0;
        color: #94a3b8;
        font-size: 1rem;
    }
    
    .card {
        background-color: #ffffff;
        padding: 1.25rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
        margin-bottom: 1.25rem;
    }
    
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #0f172a;
        margin: 0.25rem 0;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #64748b;
        font-weight: 600;
    }
    
    .priority-badge-high {
        background-color: #fee2e2;
        color: #ef4444;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.75rem;
    }
    .priority-badge-medium {
        background-color: #ffedd5;
        color: #f97316;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.75rem;
    }
    .priority-badge-low {
        background-color: #dcfce7;
        color: #22c55e;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-weight: bold;
        font-size: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to ingest and process reviews
def process_and_save_reviews(raw_reviews):
    if not raw_reviews:
        st.warning("No reviews found or parsed.")
        return 0
        
    processed = []
    for r in raw_reviews:
        cleaned = clean_text(r['text'])
        if not cleaned:
            continue
        sent = analyze_sentiment(cleaned)
        cat = categorize_feedback(cleaned)
        
        processed.append({
            'id': r['id'],
            'source': r['source'],
            'text': cleaned,
            'rating': r['rating'],
            'date': r['date'],
            'sentiment_label': sent['label'],
            'sentiment_score': sent['score'],
            'category': cat,
            'priority_score': 0.0  # calculated in next step
        })
        
    if not processed:
        return 0
        
    # Save the processed reviews to the DB
    inserted_count = insert_reviews(processed)
    
    # Recalculate priority scores based on all reviews currently in the DB
    all_db_reviews = get_filtered_reviews()
    priorities = calculate_priority_scores(all_db_reviews)
    update_priority_scores({cat: details['score'] for cat, details in priorities.items()})
    
    return inserted_count

# Header Banner
st.markdown("""
<div class="header-banner">
    <h1>Multi-Source Feedback Intelligence System</h1>
    <p>Real-time review aggregation, sentiment analysis, dynamic issue prioritization, and automated reporting.</p>
</div>
""", unsafe_allow_html=True)

# Fetch all available data first to populate filter bounds
all_reviews_for_bounds = get_filtered_reviews()
default_days = int(os.getenv("DEFAULT_DATE_RANGE_DAYS", "30"))
default_start = datetime.now().date() - timedelta(days=default_days)
default_end = datetime.now().date()

# --- FILTER SECTION ---
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    date_range = st.date_input("Date Range", [default_start, default_end])
with col_f2:
    source_filter = st.selectbox("Source", ["All", "google_play", "app_store", "csv"])
with col_f3:
    sentiment_filter = st.selectbox("Sentiment", ["All", "positive", "neutral", "negative"])

# Parse date filter bounds
start_dt = None
end_dt = None
min_date = default_start
max_date = default_end
if isinstance(date_range, list) or isinstance(date_range, tuple):
    if len(date_range) >= 1:
        min_date = date_range[0]
        start_dt = datetime.combine(min_date, datetime.min.time()).isoformat()
    if len(date_range) == 2:
        max_date = date_range[1]
        end_dt = datetime.combine(max_date, datetime.max.time()).isoformat()

# Fetch filtered reviews
filtered_reviews = get_filtered_reviews(
    source=source_filter,
    sentiment=sentiment_filter,
    start_date=start_dt,
    end_date=end_dt
)

# Recalculate priority scores specifically for current context (if database is not empty)
all_db_reviews = get_filtered_reviews()
if all_db_reviews:
    priorities = calculate_priority_scores(all_db_reviews)
else:
    priorities = {cat: {'score': 0.0, 'level': 'Low', 'frequency': 0} for cat in ['Bug', 'Crash', 'Feature Request', 'Support', 'Pricing', 'Other']}

# --- METRIC CARDS ---
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
total_count = len(filtered_reviews)

if total_count > 0:
    df_filtered = pd.DataFrame(filtered_reviews)
    ratings = df_filtered['rating'].dropna()
    csat = round((ratings.mean() / 5.0) * 100, 1) if not ratings.empty else "N/A"
    
    neg_count = len(df_filtered[df_filtered['sentiment_label'] == 'negative'])
    neg_ratio = round((neg_count / total_count) * 100, 1)
    
    # High Priority Issues: categories marked as 'High' priority
    high_priority_categories = [cat for cat, details in priorities.items() if details['level'] == 'High']
    high_priority_count = len(df_filtered[df_filtered['category'].isin(high_priority_categories)])
else:
    csat = "N/A"
    neg_ratio = 0.0
    high_priority_count = 0

with col_m1:
    st.markdown(f"""
    <div class="card">
        <div class="metric-label">TOTAL FEEDBACK</div>
        <div class="metric-value">{total_count}</div>
    </div>
    """, unsafe_allow_html=True)
with col_m2:
    st.markdown(f"""
    <div class="card">
        <div class="metric-label">CSAT % (AVG RATING)</div>
        <div class="metric-value">{csat}{'%' if csat != 'N/A' else ''}</div>
    </div>
    """, unsafe_allow_html=True)
with col_m3:
    st.markdown(f"""
    <div class="card">
        <div class="metric-label">NEGATIVE RATIO</div>
        <div class="metric-value" style="color: #ef4444;">{neg_ratio}%</div>
    </div>
    """, unsafe_allow_html=True)
with col_m4:
    st.markdown(f"""
    <div class="card">
        <div class="metric-label">CRITICAL ITEMS (HIGH PRIO)</div>
        <div class="metric-value" style="color: #ef4444;">{high_priority_count}</div>
    </div>
    """, unsafe_allow_html=True)

# --- VISUALIZATION & PRIORITY SECTION ---
col_left, col_mid, col_right = st.columns([4, 4, 3])

with col_left:
    st.markdown("### Real-Time Sentiment Trends")
    trend_df = calculate_trends(filtered_reviews, interval='daily')
    if not trend_df.empty:
        fig, ax = plt.subplots(figsize=(5, 3.5))
        ax.plot(trend_df['date'], trend_df['positive'], color='#10B981', label='Positive', linewidth=2)
        ax.plot(trend_df['date'], trend_df['neutral'], color='#64748B', label='Neutral', linewidth=2)
        ax.plot(trend_df['date'], trend_df['negative'], color='#EF4444', label='Negative', linewidth=2)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cbd5e1')
        ax.spines['bottom'].set_color('#cbd5e1')
        ax.tick_params(labelsize=8)
        # Limit ticks for readability
        if len(trend_df) > 8:
            plt.xticks(trend_df['date'][::len(trend_df)//6], rotation=30, ha='right')
        else:
            plt.xticks(rotation=30, ha='right')
        ax.legend(frameon=False, fontsize=8)
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("No trend data available for the selected filters.")

with col_mid:
    st.markdown("### Recurring Issues")
    if total_count > 0:
        df_filtered = pd.DataFrame(filtered_reviews)
        category_counts = df_filtered['category'].value_counts()
        for cat in ['Bug', 'Crash', 'Feature Request', 'Support', 'Pricing', 'Other']:
            if cat not in category_counts:
                category_counts[cat] = 0
        
        # Sort counts
        category_counts = category_counts.loc[['Bug', 'Crash', 'Feature Request', 'Support', 'Pricing', 'Other']]
        
        fig, ax = plt.subplots(figsize=(5, 3.5))
        # Color mapping
        cat_colors = {
            'Crash': '#EF4444',
            'Bug': '#F97316',
            'Feature Request': '#A855F7',
            'Support': '#3B82F6',
            'Pricing': '#06B6D4',
            'Other': '#94A3B8'
        }
        colors_list = [cat_colors[cat] for cat in category_counts.index]
        
        ax.bar(category_counts.index, category_counts.values, color=colors_list)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#cbd5e1')
        ax.spines['bottom'].set_color('#cbd5e1')
        ax.tick_params(labelsize=8)
        plt.xticks(rotation=30, ha='right')
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info("No issue counts available.")

with col_right:
    st.markdown("### Weekly Insight Reports")
    st.markdown("""
    <div style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; text-align: center;">
        <span style="font-size: 3rem;">📄</span>
        <h4 style="margin: 10px 0; color: #0f172a;">PDF Report Generator</h4>
        <p style="color: #64748b; font-size: 0.85rem; margin-bottom: 20px;">Download an on-demand stakeholder-ready summary with stats, distribution charts, and critical issues.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Generate report range string
    range_str = f"{min_date.strftime('%b %d, %Y')} - {max_date.strftime('%b %d, %Y')}"
    
    if st.button("Generate PDF Report", use_container_width=True):
        with st.spinner("Generating PDF..."):
            pdf_buf = generate_pdf_report(filtered_reviews, range_str)
            st.download_button(
                label="Download PDF Report",
                data=pdf_buf,
                file_name=f"feedback_intelligence_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

st.markdown("---")

# --- PRIORITY RANKING & DATA INGESTION ---
col_prio, col_ingest = st.columns([5, 6])

with col_prio:
    st.markdown("### Priority Ranking")
    sorted_priorities = sorted(priorities.items(), key=lambda x: x[1]['score'], reverse=True)
    
    for cat, details in sorted_priorities:
        score = details['score']
        level = details['level']
        freq = details['frequency']
        
        # Style badge
        if level == 'High':
            badge_html = f'<span class="priority-badge-high">🔥 HIGH</span>'
            border_color = "#ef4444"
        elif level == 'Medium':
            badge_html = f'<span class="priority-badge-medium">⚡ MEDIUM</span>'
            border_color = "#f97316"
        else:
            badge_html = f'<span class="priority-badge-low">🛡️ LOW</span>'
            border_color = "#22c55e"
            
        st.markdown(f"""
        <div style="background-color: #ffffff; border-left: 5px solid {border_color}; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; border-radius: 4px; padding: 12px; margin-bottom: 10px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; color: #0f172a; font-size: 1rem;">{cat}</span>
                {badge_html}
            </div>
            <div style="margin-top: 8px; display: flex; gap: 20px; font-size: 0.85rem; color: #64748b;">
                <span>Priority Score: <strong style="color: #334155;">{score}</strong></span>
                <span>Reviews: <strong style="color: #334155;">{freq}</strong></span>
            </div>
        </div>
        """, unsafe_allow_html=True)

with col_ingest:
    st.markdown("### Data Ingestion Control")
    if st.button("🗑️ Clear Existing Data", use_container_width=True):
        from src.storage.db import clear_db
        clear_db()
        st.success("Database cleared successfully! Scraping will now start fresh.")
        st.rerun()
    tab_play, tab_apple, tab_csv = st.tabs(["🤖 Google Play Scraper", "🍏 App Store Scraper", "📁 CSV Importer"])
    
    with tab_play:
        gp_app_id = st.text_input("Google Play App ID", "com.whatsapp", key="gp_id_input")
        gp_count = st.slider("Count", min_value=10, max_value=200, value=50, step=10, key="gp_count_slider")
        if st.button("Ingest Google Play Reviews", use_container_width=True):
            with st.spinner("Scraping Google Play Store..."):
                raw_reviews = fetch_google_play_reviews(gp_app_id, count=gp_count)
                inserted = process_and_save_reviews(raw_reviews)
                if inserted > 0:
                    st.success(f"Ingested and analyzed {inserted} new reviews.")
                    st.rerun()
                else:
                    st.warning("No new reviews imported.")
                    
    with tab_apple:
        as_app_id = st.text_input("App Store App ID (Number)", "389801252", key="as_id_input")
        as_pages = st.slider("Pages", min_value=1, max_value=5, value=1, step=1, key="as_pages_slider")
        if st.button("Ingest App Store Reviews", use_container_width=True):
            with st.spinner("Scraping App Store..."):
                raw_reviews = fetch_app_store_reviews(as_app_id, pages=as_pages)
                inserted = process_and_save_reviews(raw_reviews)
                if inserted > 0:
                    st.success(f"Ingested and analyzed {inserted} new reviews.")
                    st.rerun()
                else:
                    st.warning("No new reviews imported.")
                    
    with tab_csv:
        uploaded_file = st.file_uploader("Upload CSV Feedback File", type=['csv'])
        
        # Option mapping
        st.markdown("#### Optional Column Mapping")
        col_text = st.text_input("Feedback Text Column", "", placeholder="Auto-detect")
        col_rating = st.text_input("Rating/Score Column", "", placeholder="Auto-detect")
        col_date = st.text_input("Date Column", "", placeholder="Auto-detect")
        
        if uploaded_file is not None:
            mapping = {}
            if col_text: mapping['text'] = col_text
            if col_rating: mapping['rating'] = col_rating
            if col_date: mapping['date'] = col_date
            
            if st.button("Ingest CSV File", use_container_width=True):
                with st.spinner("Parsing and importing CSV..."):
                    raw_reviews = load_csv_feedback(uploaded_file, col_mapping=mapping)
                    inserted = process_and_save_reviews(raw_reviews)
                    if inserted > 0:
                        st.success(f"Ingested and analyzed {inserted} new reviews.")
                        st.rerun()
                    else:
                        st.warning("No new reviews imported. Check if column headers exist.")

st.markdown("---")

# --- RECENT REVIEWS VIEW ---
st.markdown("### Recent Customer Feedback")
if total_count > 0:
    # Build a clean dataframe for display
    df_display = pd.DataFrame(filtered_reviews)[[
        'date', 'source', 'category', 'rating', 'sentiment_label', 'text'
    ]].copy()
    
    # Rename columns for presentation
    df_display.columns = ['Date', 'Source', 'Category', 'Rating', 'Sentiment', 'Text']
    df_display['Date'] = df_display['Date'].apply(lambda x: str(x)[:16])
    df_display['Source'] = df_display['Source'].apply(lambda x: str(x).replace('_', ' ').title())
    df_display['Rating'] = df_display['Rating'].apply(lambda x: f"{int(x)}★" if pd.notna(x) else "N/A")
    df_display['Sentiment'] = df_display['Sentiment'].apply(lambda x: str(x).title())
    
    # Render reviews as styled cards in a scrollable container
    cards_html = ""
    for idx, row in df_display.iterrows():
        sentiment_color = "#10B981" if row['Sentiment'] == "Positive" else "#EF4444" if row['Sentiment'] == "Negative" else "#64748B"
        cards_html += f"""
        <div style="background-color: #ffffff; border-left: 5px solid {sentiment_color}; border-radius: 4px; padding: 12px; margin-bottom: 10px; border-top: 1px solid #e2e8f0; border-bottom: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); text-align: left;">
            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #64748b; margin-bottom: 6px;">
                <span>📅 {row['Date']} | 🔌 {row['Source']} | 🏷️ {row['Category']}</span>
                <span>⭐ {row['Rating']} | <strong style="color: {sentiment_color};">{row['Sentiment']}</strong></span>
            </div>
            <p style="margin: 0; font-size: 0.9rem; color: #0f172a; line-height: 1.4; word-wrap: break-word; text-align: left;">{row['Text']}</p>
        </div>
        """
        
    st.markdown(f"""
    <div style="max-height: 450px; overflow-y: auto; padding-right: 8px;">
        {cards_html}
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("No reviews match the selected filters or database is empty.")
