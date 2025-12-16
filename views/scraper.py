import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin, urlparse
import pandas as pd

def is_valid_url(url):
    """Check if URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def normalize_url(url):
    """Normalize URL to include https."""
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url.rstrip('/')

def is_shopify_store(url):
    """Check if a URL is a Shopify store."""
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Check for Shopify indicators
        indicators = [
            'cdn.shopify.com',
            'Shopify.theme',
            'shopify-features',
            '/cdn/shop/',
            'myshopify.com'
        ]
        
        return any(indicator in response.text for indicator in indicators)
    except:
        return False

def extract_emails_from_text(text):
    """Extract email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    
    # Filter out common false positives
    filtered_emails = [
        email for email in emails 
        if not any(x in email.lower() for x in ['example.com', 'yoursite.com', 'yourdomain.com', 'sentry.io'])
    ]
    
    return list(set(filtered_emails))

def find_contact_pages(base_url):
    """Find potential contact pages."""
    contact_paths = [
        '/pages/contact',
        '/pages/contact-us',
        '/contact',
        '/contact-us',
        '/pages/about',
        '/pages/about-us',
        '/about',
        '/about-us',
        '/pages/support',
        '/support'
    ]
    
    pages_to_check = [urljoin(base_url, path) for path in contact_paths]
    pages_to_check.insert(0, base_url)  # Check homepage first
    
    return pages_to_check

def scrape_store_info(url, progress_callback=None):
    """Scrape publicly available contact information from a Shopify store."""
    
    if progress_callback:
        progress_callback(0.1, "Validating URL...")
    
    url = normalize_url(url)
    
    if not is_valid_url(url):
        return {"error": "Invalid URL"}
    
    if progress_callback:
        progress_callback(0.2, "Checking if it's a Shopify store...")
    
    if not is_shopify_store(url):
        return {"error": "This doesn't appear to be a Shopify store"}
    
    info = {
        "store_url": url,
        "emails": [],
        "phone_numbers": [],
        "social_media": {},
        "store_name": None
    }
    
    if progress_callback:
        progress_callback(0.3, "Finding contact pages...")
    
    pages_to_check = find_contact_pages(url)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for idx, page_url in enumerate(pages_to_check):
        try:
            if progress_callback:
                progress = 0.3 + (0.5 * (idx / len(pages_to_check)))
                progress_callback(progress, f"Checking page {idx + 1}/{len(pages_to_check)}...")
            
            response = requests.get(page_url, timeout=10, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract store name
            if not info["store_name"]:
                title = soup.find('title')
                if title:
                    info["store_name"] = title.text.strip()
            
            # Extract emails
            page_text = soup.get_text()
            emails = extract_emails_from_text(page_text)
            info["emails"].extend(emails)
            
            # Also check mailto links
            mailto_links = soup.find_all('a', href=re.compile(r'^mailto:'))
            for link in mailto_links:
                email = link['href'].replace('mailto:', '').split('?')[0]
                if email and '@' in email:
                    info["emails"].append(email)
            
            # Extract phone numbers
            phone_pattern = r'\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b'
            phones = re.findall(phone_pattern, page_text)
            for phone in phones:
                formatted = f"({phone[0]}) {phone[1]}-{phone[2]}"
                if formatted not in info["phone_numbers"]:
                    info["phone_numbers"].append(formatted)
            
            # Extract social media links
            social_patterns = {
                'facebook': r'facebook\.com/[\w.-]+',
                'instagram': r'instagram\.com/[\w.-]+',
                'twitter': r'twitter\.com/[\w.-]+',
                'linkedin': r'linkedin\.com/[\w.-/]+',
                'youtube': r'youtube\.com/[\w.-/]+'
            }
            
            for platform, pattern in social_patterns.items():
                if platform not in info["social_media"]:
                    matches = re.findall(pattern, page_text)
                    if matches:
                        info["social_media"][platform] = f"https://{matches[0]}"
            
            time.sleep(0.5)  # Be respectful with requests
            
        except Exception as e:
            continue
    
    # Remove duplicates
    info["emails"] = list(set(info["emails"]))
    info["phone_numbers"] = list(set(info["phone_numbers"]))
    
    if progress_callback:
        progress_callback(1.0, "Complete!")
    
    return info

def bulk_scrape_stores(urls, progress_callback=None):
    """Scrape multiple stores."""
    results = []
    total = len(urls)
    
    for idx, url in enumerate(urls):
        if progress_callback:
            progress_callback((idx + 1) / total, f"Processing store {idx + 1}/{total}...")
        
        info = scrape_store_info(url)
        results.append(info)
        time.sleep(1)  # Be respectful between requests
    
    return results

def main():
    st.title("🛍️ Shopify Store Contact Finder")
    st.markdown("Find publicly available contact information from Shopify stores")
    
    # Important disclaimer
    st.warning("""
    ⚠️ **Important Legal & Ethical Notice:**
    
    This tool only collects **publicly available** contact information from store websites. 
    
    - ✅ Use for legitimate business outreach
    - ✅ Respect privacy and anti-spam laws (GDPR, CAN-SPAM)
    - ✅ Always provide opt-out options in communications
    - ❌ Do not use for spam or unsolicited bulk emails
    - ❌ Do not scrape excessively (respect rate limits)
    
    **By using this tool, you agree to use the data ethically and legally.**
    """, icon="⚠️")
    
    st.divider()
    
    # Initialize session state
    if 'results' not in st.session_state:
        st.session_state['results'] = None
    if 'search_type' not in st.session_state:
        st.session_state['search_type'] = 'single'
    
    # Tabs for single vs bulk
    tab1, tab2 = st.tabs(["🔍 Single Store", "📊 Bulk Search"])
    
    with tab1:
        st.subheader("Find Contact Info for a Single Store")
        
        single_url = st.text_input(
            "Shopify Store URL:",
            placeholder="e.g., https://example.myshopify.com or https://www.storename.com",
            help="Enter the full URL of the Shopify store"
        )
        
        if st.button("🔎 Find Contact Info", use_container_width=True, type="primary"):
            if not single_url.strip():
                st.error("❌ Please enter a URL")
            else:
                st.session_state['search_type'] = 'single'
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(value, message):
                    progress_bar.progress(value)
                    status_text.info(message)
                
                result = scrape_store_info(single_url.strip(), update_progress)
                
                progress_bar.empty()
                status_text.empty()
                
                if "error" in result:
                    st.error(f"❌ {result['error']}")
                else:
                    st.session_state['results'] = [result]
                    st.success("✅ Contact information found!")
    
    with tab2:
        st.subheader("Find Contact Info for Multiple Stores")
        
        bulk_input = st.text_area(
            "Enter Shopify Store URLs (one per line):",
            placeholder="https://store1.com\nhttps://store2.myshopify.com\nhttps://store3.com",
            height=150,
            help="Enter multiple URLs, one per line"
        )
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if st.button("🔎 Find All Contact Info", use_container_width=True, type="primary"):
                urls = [url.strip() for url in bulk_input.split('\n') if url.strip()]
                
                if not urls:
                    st.error("❌ Please enter at least one URL")
                else:
                    st.session_state['search_type'] = 'bulk'
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_progress(value, message):
                        progress_bar.progress(value)
                        status_text.info(message)
                    
                    results = bulk_scrape_stores(urls, update_progress)
                    
                    progress_bar.empty()
                    status_text.empty()
                    
                    st.session_state['results'] = results
                    success_count = len([r for r in results if "error" not in r])
                    st.success(f"✅ Processed {success_count}/{len(results)} stores successfully!")
        
        with col2:
            st.caption(f"💡 Be respectful\nMax 10 stores recommended")
    
    # Display results
    if st.session_state.get('results'):
        st.divider()
        st.subheader("📋 Results")
        
        results = st.session_state['results']
        
        # Statistics
        total_emails = sum(len(r.get('emails', [])) for r in results if 'error' not in r)
        total_phones = sum(len(r.get('phone_numbers', [])) for r in results if 'error' not in r)
        success_count = len([r for r in results if 'error' not in r])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Stores Processed", success_count)
        with col2:
            st.metric("Emails Found", total_emails)
        with col3:
            st.metric("Phone Numbers", total_phones)
        
        st.divider()
        
        # Display each result
        for idx, result in enumerate(results, 1):
            if "error" in result:
                with st.expander(f"❌ Store {idx} - Error", expanded=False):
                    st.error(result["error"])
                continue
            
            store_name = result.get('store_name', 'Unknown Store')
            email_count = len(result.get('emails', []))
            
            with st.expander(f"🛍️ Store {idx}: {store_name} ({email_count} email(s))", expanded=(len(results) == 1)):
                st.write(f"**🌐 URL:** {result['store_url']}")
                
                # Emails
                if result.get('emails'):
                    st.write("**📧 Email Addresses:**")
                    for email in result['emails']:
                        st.code(email, language=None)
                else:
                    st.info("No email addresses found")
                
                # Phone numbers
                if result.get('phone_numbers'):
                    st.write("**📞 Phone Numbers:**")
                    for phone in result['phone_numbers']:
                        st.code(phone, language=None)
                
                # Social media
                if result.get('social_media'):
                    st.write("**🔗 Social Media:**")
                    for platform, link in result['social_media'].items():
                        st.markdown(f"- **{platform.title()}:** {link}")
        
        # Export options
        st.divider()
        st.subheader("💾 Export Results")
        
        # Prepare CSV data
        csv_rows = []
        for result in results:
            if "error" in result:
                continue
            
            row = {
                "Store Name": result.get('store_name', 'N/A'),
                "Store URL": result.get('store_url', 'N/A'),
                "Emails": '; '.join(result.get('emails', [])) or 'None found',
                "Phone Numbers": '; '.join(result.get('phone_numbers', [])) or 'None found',
                "Facebook": result.get('social_media', {}).get('facebook', 'N/A'),
                "Instagram": result.get('social_media', {}).get('instagram', 'N/A'),
                "Twitter": result.get('social_media', {}).get('twitter', 'N/A'),
            }
            csv_rows.append(row)
        
        if csv_rows:
            df = pd.DataFrame(csv_rows)
            csv = df.to_csv(index=False)
            
            col_csv, col_clear = st.columns([3, 1])
            
            with col_csv:
                st.download_button(
                    "📊 Download CSV",
                    data=csv,
                    file_name=f"shopify_contacts_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    type="primary"
                )
            
            with col_clear:
                if st.button("🗑️ Clear Results", use_container_width=True):
                    st.session_state['results'] = None
                    st.rerun()
    
    # Help section
    with st.sidebar:
        st.header("ℹ️ How to Use")
        
        st.markdown("""
        **Steps:**
        1. Enter Shopify store URL(s)
        2. Click "Find Contact Info"
        3. Review the results
        4. Export to CSV if needed
        
        **What it finds:**
        - 📧 Email addresses
        - 📞 Phone numbers
        - 🔗 Social media links
        - 🏪 Store information
        
        **Tips:**
        - Check contact/about pages
        - Some stores hide contact info
        - Respect rate limits
        - Use data ethically
        """)
        
        st.divider()
        
        st.header("⚖️ Legal Compliance")
        st.markdown("""
        **Before contacting:**
        - ✅ Verify email legitimacy
        - ✅ Provide opt-out option
        - ✅ Follow CAN-SPAM Act
        - ✅ Respect GDPR rules
        - ✅ Send value, not spam
        
        **Resources:**
        - [CAN-SPAM Act](https://www.ftc.gov/business-guidance/resources/can-spam-act-compliance-guide-business)
        - [GDPR Guidelines](https://gdpr.eu/)
        """)

if __name__ == "__main__":
    main()