import requests
from bs4 import BeautifulSoup
from datetime import datetime

def scrape_hyderabad_news():
    url = "https://www.99acres.com/articles/hyderabad-property-news"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        news_items = []
        thumbs = soup.find_all("div", class_="thumb")
        
        for thumb in thumbs:
            banner_txt = thumb.find("div", class_="kc_bannertxt")
            if not banner_txt:
                continue
                
            title_tag = banner_txt.find("h3")
            title = title_tag.text.strip() if title_tag else ""
            
            title_a = title_tag.find_parent("a") if title_tag else None
            link = title_a["href"] if title_a and "href" in title_a.attrs else ""
            
            p_tag = banner_txt.find("p")
            snippet = p_tag.text.strip() if p_tag else ""
            
            author_span = banner_txt.find("span", class_="nam")
            author = author_span.text.strip() if author_span else ""
            
            date_em = banner_txt.find("em")
            date_str = date_em.text.strip() if date_em else ""
            
            view_span = banner_txt.find("span", class_="vew")
            views = view_span.text.strip() if view_span else ""
            
            if title and link:
                parsed_date = None
                if date_str:
                    try:
                        parsed_date = datetime.strptime(date_str, "%b %d, %Y")
                    except ValueError:
                        parsed_date = datetime.min
                        
                news_items.append({
                    "title": title,
                    "link": link,
                    "snippet": snippet,
                    "author": author,
                    "date": date_str,
                    "views": views,
                    "parsed_date": parsed_date or datetime.min
                })
                
        # Sort by latest date first
        news_items.sort(key=lambda x: x["parsed_date"], reverse=True)
        
        # Remove the datetime object before returning
        for item in news_items:
            del item["parsed_date"]
            
        return {"status": "success", "data": news_items}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import json
    print(json.dumps(scrape_hyderabad_news(), indent=2))
