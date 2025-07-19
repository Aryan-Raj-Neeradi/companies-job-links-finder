import requests
from bs4 import BeautifulSoup
import time
import csv
import re
from urllib.parse import urljoin, urlparse
import json

class CareerPageFinder:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.results = []
        
    def search_company_website(self, company_name):
        """Search for company website using Google/Bing"""
        try:
            # Clean company name for search
            search_query = f"{company_name} official website"
            
            # You can use Google Custom Search API or Bing Search API here
            # For now, we'll use a simple approach with DuckDuckGo instant answer
            search_url = f"https://duckduckgo.com/html/?q={search_query}"
            
            response = self.session.get(search_url, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract first result link
            result_links = soup.find_all('a', {'class': 'result__a'})
            if result_links:
                main_url = result_links[0].get('href')
                if main_url:
                    return main_url
            
        except Exception as e:
            print(f"Search error for {company_name}: {str(e)}")
        
        return None
    
    def find_career_page(self, company_name, main_website=None):
        """Find career page for a company"""
        career_urls = []
        
        try:
            # If no main website provided, search for it
            if not main_website:
                main_website = self.search_company_website(company_name)
                if not main_website:
                    return {"company": company_name, "main_website": "Not found", "career_urls": []}
            
            # Common career page patterns
            career_patterns = [
                '/careers',
                '/career',
                '/jobs',
                '/job-opportunities',
                '/work-with-us',
                '/join-us',
                '/employment',
                '/opportunities',
                '/hiring',
                '/openings'
            ]
            
            # Try to get main website content
            response = self.session.get(main_website, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for career links in navigation and footer
            career_links = []
            
            # Search in all links
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '').lower()
                text = link.get_text(strip=True).lower()
                
                # Check if link contains career-related keywords
                career_keywords = ['career', 'job', 'work with us', 'join us', 'employment', 'hiring', 'opportunities', 'openings']
                
                if any(keyword in href or keyword in text for keyword in career_keywords):
                    full_url = urljoin(main_website, link['href'])
                    if full_url not in career_links:
                        career_links.append(full_url)
            
            # If no career links found, try common patterns
            if not career_links:
                base_url = main_website.rstrip('/')
                for pattern in career_patterns:
                    test_url = base_url + pattern
                    try:
                        test_response = self.session.head(test_url, timeout=5)
                        if test_response.status_code == 200:
                            career_links.append(test_url)
                    except:
                        continue
            
            return {
                "company": company_name,
                "main_website": main_website,
                "career_urls": career_links[:3]  # Limit to top 3 results
            }
            
        except Exception as e:
            print(f"Error processing {company_name}: {str(e)}")
            return {
                "company": company_name,
                "main_website": main_website or "Error",
                "career_urls": []
            }
    
    def process_companies_from_file(self, input_file, output_file):
        """Process all companies from input file"""
        try:
            with open(input_file, 'r', encoding='utf-8') as file:
                companies = [line.strip() for line in file if line.strip()]
            
            print(f"Found {len(companies)} companies to process")
            print("Starting career page search...")
            print("=" * 60)
            
            results = []
            
            for i, company in enumerate(companies, 1):
                print(f"Processing {i}/{len(companies)}: {company}")
                
                result = self.find_career_page(company)
                results.append(result)
                
                # Show progress
                if result['career_urls']:
                    print(f"  ✅ Found {len(result['career_urls'])} career page(s)")
                    for url in result['career_urls']:
                        print(f"     🔗 {url}")
                else:
                    print(f"  ❌ No career page found")
                
                print(f"  🌐 Main website: {result['main_website']}")
                print("-" * 40)
                
                # Save progress every 50 companies
                if i % 50 == 0:
                    self.save_results(results, f"progress_{i}_{output_file}")
                    print(f"💾 Progress saved at {i} companies")
                
                # Rate limiting - be respectful to websites
                time.sleep(2)  # Wait 2 seconds between requests
            
            # Save final results
            self.save_results(results, output_file)
            self.generate_summary_report(results)
            
            return results
            
        except FileNotFoundError:
            print(f"❌ Error: File '{input_file}' not found!")
        except Exception as e:
            print(f"❌ Error: {str(e)}")
    
    def save_results(self, results, filename):
        """Save results to CSV and JSON files"""
        # Save as CSV
        csv_filename = filename.replace('.txt', '.csv') if '.txt' in filename else filename + '.csv'
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Company', 'Main_Website', 'Career_URL_1', 'Career_URL_2', 'Career_URL_3', 'Total_Career_URLs']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                row = {
                    'Company': result['company'],
                    'Main_Website': result['main_website'],
                    'Career_URL_1': result['career_urls'][0] if len(result['career_urls']) > 0 else '',
                    'Career_URL_2': result['career_urls'][1] if len(result['career_urls']) > 1 else '',
                    'Career_URL_3': result['career_urls'][2] if len(result['career_urls']) > 2 else '',
                    'Total_Career_URLs': len(result['career_urls'])
                }
                writer.writerow(row)
        
        # Save as JSON for detailed data
        json_filename = filename.replace('.txt', '.json') if '.txt' in filename else filename + '.json'
        with open(json_filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(results, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"✅ Results saved to:")
        print(f"   📊 CSV: {csv_filename}")
        print(f"   📋 JSON: {json_filename}")
    
    def generate_summary_report(self, results):
        """Generate a summary report"""
        total_companies = len(results)
        found_career_pages = sum(1 for r in results if r['career_urls'])
        found_websites = sum(1 for r in results if r['main_website'] not in ['Not found', 'Error'])
        
        print("\n" + "=" * 60)
        print("📈 SUMMARY REPORT")
        print("=" * 60)
        print(f"Total companies processed: {total_companies}")
        print(f"Main websites found: {found_websites} ({found_websites/total_companies*100:.1f}%)")
        print(f"Career pages found: {found_career_pages} ({found_career_pages/total_companies*100:.1f}%)")
        print(f"No career page found: {total_companies - found_career_pages}")
        
        # Companies with most career URLs
        top_companies = sorted([r for r in results if r['career_urls']], 
                              key=lambda x: len(x['career_urls']), reverse=True)[:10]
        
        if top_companies:
            print(f"\n🏆 Top companies with most career URLs:")
            for i, company in enumerate(top_companies, 1):
                print(f"   {i}. {company['company']}: {len(company['career_urls'])} URLs")

# Main execution
def main():
    finder = CareerPageFinder()
    
    input_file = "standardized_companies.txt"  # Your file with 748 companies
    output_file = "company_career_pages"
    
    print("🔍 Career Page Finder")
    print("=" * 60)
    print("This script will:")
    print("✓ Search for main website of each company")
    print("✓ Find career/jobs pages on their websites") 
    print("✓ Save results in CSV and JSON format")
    print("✓ Generate summary statistics")
    print("⚠️  This will take time (2-3 hours for 748 companies)")
    print("=" * 60)
    
    confirmation = input("Do you want to proceed? (yes/no): ").lower()
    if confirmation in ['yes', 'y']:
        results = finder.process_companies_from_file(input_file, output_file)
    else:
        print("Operation cancelled.")

if __name__ == "__main__":
    main()

# Quick test function for a few companies
def quick_test():
    """Test with a few companies first"""
    finder = CareerPageFinder()
    
    test_companies = [
        "Microsoft",
        "Google", 
        "Accenture",
        "IBM",
        "TCS"
    ]
    
    print("🧪 Quick test with sample companies...")
    
    results = []
    for company in test_companies:
        print(f"\nTesting: {company}")
        result = finder.find_career_page(company)
        results.append(result)
        
        if result['career_urls']:
            print(f"✅ Found career pages:")
            for url in result['career_urls']:
                print(f"   🔗 {url}")
        else:
            print("❌ No career pages found")
    
    finder.save_results(results, "test_career_pages")

# Uncomment to run quick test first
# quick_test()
