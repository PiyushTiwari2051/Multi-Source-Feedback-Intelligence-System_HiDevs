import io
import logging
from typing import List, Dict, Any
import pandas as pd
import matplotlib
# Use non-interactive backend for Matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

logger = logging.getLogger(__name__)

def generate_pdf_report(reviews: List[Dict[str, Any]], date_range_str: str) -> io.BytesIO:
    """
    Generates a professional PDF weekly report using reportlab and embeds a matplotlib chart.
    """
    logger.info("Starting PDF report generation.")
    
    # Create an in-memory buffer for the PDF
    pdf_buffer = io.BytesIO()
    
    # Setup Document
    # Page size: Letter (8.5 x 11 inches)
    # Margins: 0.5 inches
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#0F172A'), # Navy Slate
        spaceAfter=6
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#64748B'), # Slate Gray
        spaceAfter=20
    )
    
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=15,
        spaceAfter=8,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#334155')
    )
    
    cell_style = ParagraphStyle(
        'Cell',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor('#334155')
    )
    
    header_cell_style = ParagraphStyle(
        'HeaderCell',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.white
    )
    
    card_title_style = ParagraphStyle(
        'CardTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor('#475569')
    )
    
    card_value_style = ParagraphStyle(
        'CardValue',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#0F172A')
    )

    # Document Header
    story.append(Paragraph("Feedback Intelligence System", title_style))
    story.append(Paragraph(f"Weekly Insights & Analytics Report  |  Covering: {date_range_str}", subtitle_style))
    story.append(Spacer(1, 10))

    if not reviews:
        story.append(Paragraph("No feedback data available for the specified range.", body_style))
        doc.build(story)
        pdf_buffer.seek(0)
        return pdf_buffer
        
    df = pd.DataFrame(reviews)
    
    # Calculate Summary Statistics
    total_reviews = len(df)
    
    ratings = df['rating'].dropna()
    avg_rating = round(ratings.mean(), 2) if not ratings.empty else "N/A"
    
    sentiments = df['sentiment_label'].value_counts()
    neg_pct = round((sentiments.get('negative', 0) / total_reviews) * 100, 1) if total_reviews > 0 else 0
    pos_pct = round((sentiments.get('positive', 0) / total_reviews) * 100, 1) if total_reviews > 0 else 0
    neu_pct = round((sentiments.get('neutral', 0) / total_reviews) * 100, 1) if total_reviews > 0 else 0
    
    # KPI Grid Table
    kpi_data = [
        [
            Paragraph("Total Reviews", card_title_style),
            Paragraph("Average Rating", card_title_style),
            Paragraph("Negative Ratio", card_title_style),
            Paragraph("Positive Ratio", card_title_style)
        ],
        [
            Paragraph(str(total_reviews), card_value_style),
            Paragraph(f"{avg_rating} / 5" if isinstance(avg_rating, float) else avg_rating, card_value_style),
            Paragraph(f"{neg_pct}%", card_value_style),
            Paragraph(f"{pos_pct}%", card_value_style)
        ]
    ]
    
    # Grid width = 7.5 inches (540 points)
    kpi_table = Table(kpi_data, colWidths=[135, 135, 135, 135])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (0,1), (-1,1), colors.HexColor('#F1F5F9')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    
    story.append(Paragraph("Performance Summary", section_heading))
    story.append(kpi_table)
    story.append(Spacer(1, 15))
    
    # Generate Matplotlib chart: Volume by Category
    # We will build a neat side-by-side or stacked horizontal bar plot
    fig, ax = plt.subplots(figsize=(7, 2.5))
    category_counts = df['category'].value_counts()
    
    # Ensure all default categories are shown
    for c in ['Bug', 'Crash', 'Feature Request', 'Support', 'Pricing', 'Other']:
        if c not in category_counts:
            category_counts[c] = 0
            
    # Sort
    category_counts = category_counts.sort_values(ascending=True)
    
    # Plotting
    colors_list = ['#94A3B8', '#F43F5E', '#A855F7', '#3B82F6', '#06B6D4', '#10B981']
    # Map colors to sorted index
    category_counts.plot(kind='barh', color='#3B82F6', ax=ax)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_color('#E2E8F0')
    ax.spines['bottom'].set_color('#E2E8F0')
    ax.tick_params(colors='#475569', labelsize=8)
    ax.set_title("Feedback Volume by Category", fontsize=10, fontweight='bold', color='#0F172A', pad=10)
    plt.tight_layout()
    
    chart_buffer = io.BytesIO()
    plt.savefig(chart_buffer, format='png', dpi=300, bbox_inches='tight')
    chart_buffer.seek(0)
    plt.close(fig)
    
    story.append(Paragraph("Issue Breakdown", section_heading))
    story.append(Image(chart_buffer, width=5.2*inch, height=2.2*inch))
    story.append(Spacer(1, 15))
    
    # Top 5 Negative / Urgent Reviews Table
    story.append(Paragraph("Top Critical Issues & Customer Voices", section_heading))
    
    # Filter for negative reviews first, order by priority score descending or rating ascending
    critical_df = df.copy()
    
    # Sort by rating ascending, priority_score descending
    critical_df = critical_df.sort_values(by=['rating', 'priority_score'], ascending=[True, False])
    top_5 = critical_df.head(5)
    
    if top_5.empty:
        story.append(Paragraph("No negative or critical items found in this period.", body_style))
    else:
        table_data = [
            [
                Paragraph("Date", header_cell_style),
                Paragraph("Source", header_cell_style),
                Paragraph("Category", header_cell_style),
                Paragraph("Rating", header_cell_style),
                Paragraph("Feedback Content", header_cell_style)
            ]
        ]
        
        for _, r in top_5.iterrows():
            date_val = str(r['date'])[:10] if r['date'] else "N/A"
            source_val = str(r['source']).replace('_', ' ').title()
            category_val = str(r['category'])
            rating_val = f"{int(r['rating'])}★" if pd.notna(r['rating']) else "N/A"
            
            # Truncate content to fit well in cells
            content_str = str(r['text'])
            if len(content_str) > 130:
                content_str = content_str[:127] + "..."
                
            table_data.append([
                Paragraph(date_val, cell_style),
                Paragraph(source_val, cell_style),
                Paragraph(category_val, cell_style),
                Paragraph(rating_val, cell_style),
                Paragraph(content_str, cell_style)
            ])
            
        # Total printable width is 540
        # Col widths: Date=65, Source=65, Category=85, Rating=40, Content=285
        issues_table = Table(table_data, colWidths=[65, 65, 85, 40, 285])
        issues_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')), # Dark Slate header
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(issues_table)
        
    doc.build(story)
    pdf_buffer.seek(0)
    logger.info("PDF report generated successfully.")
    return pdf_buffer
