# Example script demonstrating how to use the blog web scraper

from webscrapper import scrape_blog_to_pdf

def main():
    # Example blog URLs to scrape
    blog_urls = [
        # "https://www.360propertymanagement.in/capital-gain-tax-exemption-on-residential-property-landmark-judgments-part-a/",
        # "https://kdpaccountants.com/blogs/possession-date-for-capital-gains-exemption",
        # "https://taxguru.in/income-tax/capital-gain-tax-exemption-section-54f-landmark-judgements.html",
        # "https://www.taxscan.in/allotment-date-not-registration-itats-landmark-ruling-changes-how-house-property-sale-gains-are-computed/508267",
        # "https://kdpaccountants.com/blogs/possession-date-for-capital-gains-exemption",
        # "https://www.taxscan.in/an-analysis-of-key-itat-income-tax-appellate-tribunal-rulings/512039"

    ]
    
    # Scrape each blog URL
    for i, url in enumerate(blog_urls):
        print(f"\nScraping blog {i+1}/{len(blog_urls)}: {url}")
        
        # Custom output filename for this example
        # filename = f"Capital_Gain_Tax_Exemption{i+1}.pdf"
        # filename = f"Recent_Tribunal_Rullings{i+1}.pdf"
        filename = f"Britanica_Artificial_Intelligence.pdf"
        
        # Scrape the blog and save as PDF
        pdf_path = scrape_blog_to_pdf(
            url=url,
            output_dir="data",  # Will save to the data directory
            filename=filename
        )
        
        if pdf_path:
            print(f"✓ Successfully saved PDF: {pdf_path}")
        else:
            print(f"✗ Failed to scrape blog: {url}")

if __name__ == "__main__":
    main()