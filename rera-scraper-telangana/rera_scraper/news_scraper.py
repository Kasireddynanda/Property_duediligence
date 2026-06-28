import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_property_news():
    url = "https://www.99acres.com/articles/hyderabad-property-news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        news_items = []
        # Find the container with class kc_artlreathumb which has the news articles
        container = soup.find("div", class_="kc_artlreathumb")
        if not container:
            # Try the other section if first one is not found
            container = soup.find("div", class_="kc_artlcolmlft")
            
        if not container:
            logger.warning("Could not find news container on 99acres")
            return []
            
        articles = container.find_all("div", recursive=False)
        
        for article in articles:
            thumb = article.find("div", class_=lambda c: c and c.startswith("thumb"))
            if not thumb:
                continue
                
            img = thumb.find("img")
            img_url = img["src"] if img else ""
            
            bannertxt = thumb.find("div", class_="kc_bannertxt")
            if not bannertxt:
                continue
                
            # Extract links and text
            links = bannertxt.find_all("a")
            if len(links) < 2:
                continue
                
            category_tag = links[0].find("span", class_="ttl")
            category = category_tag.text.strip() if category_tag else ""
            
            title_tag = links[1].find("h3")
            title = title_tag.text.strip() if title_tag else ""
            link = links[1]["href"] if "href" in links[1].attrs else ""
            
            p_tag = bannertxt.find("p")
            description = p_tag.text.strip() if p_tag else ""
            
            author_tag = bannertxt.find("span", class_="nam")
            author = author_tag.text.strip() if author_tag else ""
            
            # The date is usually in a span next to the author link
            spans = bannertxt.find_all("span", recursive=False)
            date_str = ""
            for span in spans:
                em = span.find("em")
                if em:
                    date_str = em.text.strip()
                    break
                    
            views_tag = bannertxt.find("span", class_="vew")
            views = views_tag.text.strip() if views_tag else ""
            
            if title and link:
                news_items.append({
                    "title": title,
                    "link": link,
                    "image": img_url,
                    "category": category,
                    "description": description,
                    "author": author,
                    "date": date_str,
                    "views": views
                })
                
        return news_items
    except Exception as e:
        logger.error(f"Error scraping news: {e}")
        return []
