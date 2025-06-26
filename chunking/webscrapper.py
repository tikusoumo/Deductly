import os
import re
import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import BSHTMLLoader
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from datetime import datetime


def scrape_blog_to_pdf(url, output_dir="data", filename=None):
    """
    Scrapes content from a blog website and saves it as a well-formatted PDF file.

    Args:
        url (str): The URL of the blog to scrape.
        output_dir (str): Directory to save the PDF (default: "data").
        filename (str, optional): Name for the output PDF file. If None, a name will be generated.

    Returns:
        str: Path to the saved PDF file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    
    try:
        headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}
        response = requests.get(url)
        response.raise_for_status()

        # Parse HTML using BeautifulSoup
        soup = BeautifulSoup(response.content, 'html5lib')

       # Remove unwanted elements
        for selector in ['header', 'footer', 'nav', 'aside', 'script', 'style']:
            for tag in soup.select(selector):
                tag.decompose()

        # Extract blog title
        title = soup.title.string.strip() if soup.title else "Blog Article"

        # Try to detect main content region
        main_content = (
            soup.find('article') or
            soup.find('main') or
            soup.find('div', class_=re.compile(r'(content|post|blog|entry)', re.I)) or
            soup.body
        )

        # Extract structured content
        elements = []
        if main_content:
            tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote', 'pre', 'code']
            for tag in main_content.find_all(tags, recursive=True):
                text = tag.get_text(strip=True)
                if text:
                    elements.append((tag.name, re.sub(r'\s+', ' ', text)))

        # Generate filename if not provided
        if not filename:
            clean_title = re.sub(r'[^\w\s-]', '', title).strip().lower()
            clean_title = re.sub(r'[-\s]+', '-', clean_title)
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"{clean_title}-{date_str}.pdf"

        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        pdf_path = os.path.join(output_dir, filename)

        # Define PDF styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, textColor=colors.darkblue, spaceAfter=0.3 * inch)
        body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontSize=11, leading=14, spaceBefore=0.1 * inch, spaceAfter=0.1 * inch)
        bullet_style = ParagraphStyle('BulletStyle', parent=styles['Normal'], fontSize=11, leading=14, leftIndent=12, bulletIndent=0)

        # Build PDF content
        pdf_content = [Paragraph(title, title_style), Spacer(1, 0.2 * inch)]
        pdf_content.append(Paragraph(f"Source: {url}", styles['Italic']))
        pdf_content.append(Spacer(1, 0.1 * inch))
        pdf_content.append(Paragraph(f"Scraped on: {datetime.now().strftime('%B %d, %Y')}", styles['Italic']))
        pdf_content.append(Spacer(1, 0.3 * inch))

        for tag, para in elements:
            if tag.startswith('h') and tag[1:].isdigit():
                level = int(tag[1:])
                heading_style = ParagraphStyle(
                    f'Heading{level}',
                    parent=styles.get(f'Heading{min(level, 3)}', styles['Heading3']),
                    fontSize=14 - (level - 1),
                    spaceBefore=0.2 * inch,
                    spaceAfter=0.1 * inch
                )
                pdf_content.append(Paragraph(para, heading_style))
            elif tag == 'li':
                pdf_content.append(Paragraph(f"• {para}", bullet_style))
            elif tag in ['pre', 'code']:
                code_style = ParagraphStyle('CodeStyle', parent=styles['Code'], fontSize=9, leading=12, leftIndent=12)
                pdf_content.append(Paragraph(para.replace(' ', '&nbsp;').replace('\n', '<br />'), code_style))
            else:
                pdf_content.append(Paragraph(para, body_style))

            pdf_content.append(Spacer(1, 0.1 * inch))

        # Write PDF
        doc = SimpleDocTemplate(pdf_path, pagesize=letter)
        doc.build(pdf_content)

        print(f"✅ Successfully scraped and saved PDF at: {pdf_path}")
        return pdf_path

    except Exception as e:
        print(f"❌ Error scraping blog: {str(e)}")
        return None

# Example usage
if __name__ == "__main__":
    blog_url = "https://example-blog-url.com/some-article"
    output_pdf = scrape_blog_to_pdf(blog_url)
    if output_pdf:
        print(f"PDF saved at: {output_pdf}")
    else:
        print("Failed to generate PDF.")
    
    
    
    
    
   