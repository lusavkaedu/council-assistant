# utils/http_utils.py
import requests
import random
import time
import http.cookiejar

def get_random_headers():
    """Generate random-looking but realistic browser headers"""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    
    # Common accept headers
    accept = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    accept_language = "en-GB,en;q=0.9"
    
    headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": accept,
        "Accept-Language": accept_language,
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
        "DNT": "1",
    }
    
    # Occasionally add a referer to make it seem like we clicked a link
    if random.random() > 0.7:
        headers["Referer"] = "https://democracy.kent.gov.uk/ieDocHome.aspx"
        
    return headers

def create_session():
    """Create a persistent session object with cookies enabled"""
    session = requests.Session()
    # Set a cookie policy that accepts all cookies
    session.cookies.set_policy(http.cookiejar.DefaultCookiePolicy(
        allowed_domains=None,  # Allow all domains
    ))
    return session

def request_with_retry(session, url, max_retries=3, backoff_factor=1.5):
    """Make a request with exponential backoff retry logic"""
    headers = get_random_headers()
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Vary the timeout slightly
            timeout = random.uniform(8, 12)
            response = session.get(url, headers=headers, timeout=timeout)
            
            # If successful, return the response
            if response.status_code == 200:
                return response
                
            # If we get a 403 or 429, back off and retry
            if response.status_code in (403, 429):
                retry_count += 1
                wait_time = backoff_factor ** retry_count
                # Add some randomness to the wait time
                wait_time = wait_time * random.uniform(0.8, 1.2)
                print(f"⚠️ Got status {response.status_code}, waiting {wait_time:.2f}s before retry {retry_count}/{max_retries}")
                time.sleep(wait_time)
                continue
                
            # For other status codes, just return the response
            return response
            
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            retry_count += 1
            wait_time = backoff_factor ** retry_count
            print(f"⚠️ Connection error: {str(e)}, waiting {wait_time:.2f}s before retry {retry_count}/{max_retries}")
            time.sleep(wait_time)
    
    # If we've exhausted all retries, raise an exception
    raise Exception(f"Failed to retrieve {url} after {max_retries} retries")


