import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import time
from urllib.parse import urljoin, urlparse, quote_plus
import pandas as pd
import random

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
        if not any(x in email.lower() for x in ['example.com', 'yoursite.com', 'yourdomain.com', 'sentry.io', 'schema.org'])
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

def search_shopify_stores_google(query, num_results=10, progress_callback=None):
    """Search for Shopify stores using Google search."""
    stores = []
    
    # Google search query to find Shopify stores
    search_queries = [
        f'{query} site:myshopify.com',
        f'{query} "powered by shopify"',
        f'{query} shopify store'
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    for idx, search_query in enumerate(search_queries):
        if progress_callback:
            progress_callback((idx + 1) / len(search_queries), f"Searching with query {idx + 1}/{len(search_queries)}...")
        
        try:
            # Use Google Custom Search (free tier) or DuckDuckGo as alternative
            # For demo purposes, we'll use a simple approach
            encoded_query = quote_plus(search_query)
            search_url = f"https://www.google.com/search?q={encoded_query}&num={num_results}"
            
            response = requests.get(search_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract URLs from search results
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if '/url?q=' in href:
                    # Extract actual URL from Google redirect
                    url = href.split('/url?q=')[1].split('&')[0]
                    
                    # Clean and validate
                    if url.startswith('http') and not any(x in url for x in ['google.com', 'youtube.com']):
                        # Check if it's a myshopify.com subdomain
                        if 'myshopify.com' in url:
                            stores.append(url)
                        # Or try to get the main domain if it mentions shopify
                        elif 'shopify' in href.lower():
                            domain = urlparse(url).netloc
                            clean_url = f"https://{domain}"
                            if clean_url not in stores:
                                stores.append(clean_url)
            
            time.sleep(2)  # Be respectful with search requests
            
        except Exception as e:
            continue
    
    # Remove duplicates and limit results
    unique_stores = list(set(stores))[:num_results]
    
    # Verify they're actually Shopify stores
    if progress_callback:
        progress_callback(0.9, "Verifying Shopify stores...")
    
    verified_stores = []
    for store in unique_stores[:num_results]:
        try:
            if is_shopify_store(store):
                verified_stores.append(store)
            time.sleep(0.5)
        except:
            continue
    
    return verified_stores

def search_shopify_stores_duckduckgo(query, num_results=10, progress_callback=None):
    """Alternative search using DuckDuckGo."""
    stores = []
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        if progress_callback:
            progress_callback(0.2, "Searching DuckDuckGo...")
        
        # DuckDuckGo HTML search
        encoded_query = quote_plus(f'{query} myshopify.com OR "powered by shopify"')
        search_url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
        
        response = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract URLs
        for link in soup.find_all('a', class_='result__url'):
            href = link.get('href', '')
            if href.startswith('http'):
                stores.append(href)
        
        # Also check direct links
        for result in soup.find_all('a', class_='result__a'):
            href = result.get('href', '')
            if '//' in href:
                try:
                    # Extract actual URL
                    url = href.split('uddg=')[1] if 'uddg=' in href else href
                    if url.startswith('http'):
                        stores.append(url)
                except:
                    continue
        
    except Exception as e:
        if progress_callback:
            progress_callback(0.5, f"Search error: {str(e)[:50]}")
    
    # Remove duplicates
    unique_stores = list(set(stores))[:num_results * 2]
    
    # Verify they're Shopify stores
    if progress_callback:
        progress_callback(0.6, "Verifying stores...")
    
    verified_stores = []
    for idx, store in enumerate(unique_stores):
        if len(verified_stores) >= num_results:
            break
        
        try:
            if progress_callback:
                progress_callback(0.6 + (0.3 * idx / len(unique_stores)), f"Checking store {idx + 1}...")
            
            if is_shopify_store(store):
                verified_stores.append(store)
            time.sleep(0.5)
        except:
            continue
    
    return verified_stores

def discover_shopify_stores(niche=None, num_results=10, progress_callback=None):
    """Discover Shopify stores by niche or randomly."""
    
    if niche:
        # Search for stores in specific niche
        queries = [
            f"{niche} store",
            f"{niche} shop",
            f"buy {niche} online"
        ]
        query = random.choice(queries)
    else:
        # Random popular niches
        niches = [
            "fashion", "jewelry", "home decor", "fitness", "beauty",
            "tech accessories", "pet supplies", "art", "kids toys",
            "outdoor gear", "sustainable products", "handmade"
        ]
        niche = random.choice(niches)
        query = f"{niche} store"
    
    if progress_callback:
        progress_callback(0.1, f"Searching for {niche} stores...")
    
    # Try DuckDuckGo first (more reliable for automated searches)
    stores = search_shopify_stores_duckduckgo(query, num_results, progress_callback)
    
    # If not enough results, try another niche
    if len(stores) < num_results // 2 and not niche:
        if progress_callback:
            progress_callback(0.5, "Trying additional search...")
        backup_niche = random.choice([n for n in niches if n != niche])
        backup_stores = search_shopify_stores_duckduckgo(f"{backup_niche} store", num_results // 2, progress_callback)
        stores.extend(backup_stores)
    
    return list(set(stores))[:num_results]

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
    if 'discovered_stores' not in st.session_state:
        st.session_state['discovered_stores'] = None
    
    # Tabs for different modes
    tab1, tab2, tab3 = st.tabs(["🔍 Single Store", "📊 Bulk Search", "🎯 Auto-Discover Stores"])
    
    with tab1:
        st.subheader("Find Contact Info for a Single Store")
        
        single_url = st.text_input(
            "Shopify Store URL:",
            placeholder="e.g., https://example.myshopify.com or https://www.storename.com",
            help="Enter the full URL of the Shopify store"
        )
        
        if st.button("🔎 Find Contact Info", use_container_width=True, type="primary", key="single_search"):
            if not single_url.strip():
                st.error("❌ Please enter a URL")
            else:
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
            if st.button("🔎 Find All Contact Info", use_container_width=True, type="primary", key="bulk_search"):
                urls = [url.strip() for url in bulk_input.split('\n') if url.strip()]
                
                if not urls:
                    st.error("❌ Please enter at least one URL")
                else:
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
    
    with tab3:
        st.subheader("🎯 Automatically Discover Shopify Stores")
        st.markdown("Let the tool find Shopify stores for you based on niche or randomly")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            niche_input = st.text_input(
                "Niche/Category (optional):",
                placeholder="e.g., fashion, jewelry, home decor, fitness, beauty",
                help="Leave empty for random discovery across popular niches"
            )
        
        with col2:
            num_stores = st.number_input(
                "Number of stores:",
                min_value=1,
                max_value=20,
                value=5,
                step=1,
                help="How many stores to discover (max 20)"
            )
        
        st.info("💡 **Tip:** Leave niche empty to discover stores randomly, or specify a niche for targeted results")
        
        col_discover, col_use = st.columns([2, 1])
        
        with col_discover:
            if st.button("🚀 Discover Stores", use_container_width=True, type="primary", key="discover"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(value, message):
                    progress_bar.progress(value)
                    status_text.info(message)
                
                niche = niche_input.strip() if niche_input.strip() else None
                stores = discover_shopify_stores(niche, num_stores, update_progress)
                
                progress_bar.empty()
                status_text.empty()
                
                if stores:
                    st.session_state['discovered_stores'] = stores
                    st.success(f"✅ Discovered {len(stores)} Shopify stores!")
                else:
                    st.warning("⚠️ No stores found. Try a different niche or try again.")
        
        # Display discovered stores
        if st.session_state.get('discovered_stores'):
            st.divider()
            st.subheader("📋 Discovered Stores")
            
            discovered = st.session_state['discovered_stores']
            
            # Show list with checkboxes for selection
            st.markdown(f"**Found {len(discovered)} store(s):**")
            
            selected_stores = []
            for idx, store in enumerate(discovered, 1):
                if st.checkbox(f"{idx}. {store}", value=True, key=f"store_select_{idx}"):
                    selected_stores.append(store)
            
            st.divider()
            
            col_scrape, col_copy = st.columns([2, 1])
            
            with col_scrape:
                if st.button("📧 Get Contact Info for Selected", use_container_width=True, type="primary", key="scrape_discovered"):
                    if not selected_stores:
                        st.error("❌ Please select at least one store")
                    else:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        def update_progress(value, message):
                            progress_bar.progress(value)
                            status_text.info(message)
                        
                        results = bulk_scrape_stores(selected_stores, update_progress)
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        st.session_state['results'] = results
                        success_count = len([r for r in results if "error" not in r])
                        st.success(f"✅ Processed {success_count}/{len(results)} stores successfully!")
            
            with col_copy:
                # Copy URLs to clipboard
                urls_text = '\n'.join(selected_stores)
                st.download_button(
                    "📋 Copy URLs",
                    data=urls_text,
                    file_name="discovered_stores.txt",
                    mime="text/plain",
                    use_container_width=True
                )
    
    # Display results
    if st.session_state.get('results'):
        st.divider()
        st.subheader("📋 Contact Information Results")
        
        results = st.session_state['results']
        
        # Statistics
        total_emails = sum(len(r.get('emails', [])) for r in results if 'error' not in r)
        total_phones = sum(len(r.get('phone_numbers', [])) for r in results if 'error' not in r)
        success_count = len([r for r in results if 'error' not in r])
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Stores Processed", success_count)
        with col2:
            st.metric("Emails Found", total_emails)
        with col3:
            st.metric("Phone Numbers", total_phones)
        with col4:
            avg_emails = total_emails / success_count if success_count > 0 else 0
            st.metric("Avg. Emails/Store", f"{avg_emails:.1f}")
        
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
                        col_email, col_copy = st.columns([4, 1])
                        with col_email:
                            st.code(email, language=None)
                        with col_copy:
                            st.button("📋", key=f"copy_email_{idx}_{email}", help="Click to highlight")
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
                    st.session_state['discovered_stores'] = None
                    st.rerun()
    
    # Help section
    with st.sidebar:
        st.header("ℹ️ How to Use")
        
        st.markdown("""
        **3 Ways to Find Stores:**
        
        1️⃣ **Single Store**
        - Enter a known store URL
        - Get contact info instantly
        
        2️⃣ **Bulk Search**
        - Paste multiple store URLs
        - Process all at once
        
        3️⃣ **Auto-Discover** ⭐
        - Specify a niche or go random
        - Tool finds stores for you
        - Select which to scrape
        
        **What it finds:**
        - 📧 Email addresses
        - 📞 Phone numbers
        - 🔗 Social media links
        - 🏪 Store information
        """)
        
        st.divider()
        
        st.header("💡 Tips")
        st.markdown("""
        **For Best Results:**
        - Try specific niches (e.g., "eco fashion")
        - Check multiple pages
        - Verify email validity
        - Be patient with discovery
        
        **Popular Niches:**
        - Fashion & Apparel
        - Jewelry & Accessories
        - Home & Living
        - Beauty & Cosmetics
        - Tech Accessories
        - Pet Supplies
        - Art & Crafts
        - Fitness & Wellness
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