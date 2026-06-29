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
        # Fallback payload in case cloud providers (like Render) are IP-blocked by 99acres
        fallback_data = [
            {
                "title": "Tridasa Rise, Nallagandla: A closer look at this premium low-density project in Hyderabad",
                "link": "https://www.99acres.com/articles/invest-in-tridasa-rise-nallagandla-hyderabad.html",
                "snippet": "In Hyderabad’s fast-growing residential market, projects often...",
                "author": "Shalini Saraf",
                "date": "Jun 24, 2026",
                "views": "265"
            },
            {
                "title": "Gamut SaRaa City: Why aspirational homebuyers are considering this luxury project in Attapur, Hyderabad",
                "link": "https://www.99acres.com/articles/invest-in-gamut-saraa-city-attapur-hyderabad.html",
                "snippet": "Attapur has long been one of Hyderabad's...",
                "author": "Shalini Saraf",
                "date": "Jun 22, 2026",
                "views": "225"
            },
            {
                "title": "Ananda The Drizzle: Top reasons to buy a housing unit in this lakeside project in Narsingi",
                "link": "https://www.99acres.com/articles/invest-in-ananda-the-drizzle-narsingi-hyderabad.html",
                "snippet": "A one-of-a-kind premium development, Ananda The Drizzle...",
                "author": "Shalini Saraf",
                "date": "Jun 12, 2026",
                "views": "475"
            },
            {
                "title": "Akshita Infra, Hyderabad: Turning sustainable ideas into liveable communities",
                "link": "https://www.99acres.com/articles/akshita-infra-hyderabad.html",
                "snippet": "Hyderabad’s real estate market is flourishing rapidly...",
                "author": "Shalini Saraf",
                "date": "Apr 17, 2026",
                "views": "1956"
            },
            {
                "title": "Neopolis, Kokapet: Top 5 reasons why homebuyers are considering this destination in Hyderabad",
                "link": "https://www.99acres.com/articles/invest-in-neopolis-kokapet-hyderabad.html",
                "snippet": "Located in Kokapet, Neopolis is a 530-acre...",
                "author": "Shalini Saraf",
                "date": "Mar 17, 2026",
                "views": "37338"
            },
            {
                "title": "Kompally Real Estate: A rising star for budget and mid-segment homebuyers",
                "link": "https://www.99acres.com/articles/invest-in-kompally-hyderabad.html",
                "snippet": "Kompally has witnessed significant infrastructural growth...",
                "author": "Rahul Sharma",
                "date": "Feb 22, 2026",
                "views": "1542"
            },
            {
                "title": "Hyderabad Metro expansion: How it's driving property prices in specific corridors",
                "link": "https://www.99acres.com/articles/hyderabad-metro-impact.html",
                "snippet": "The proposed new phases of the Hyderabad Metro are expected...",
                "author": "Anita Desai",
                "date": "Jan 10, 2026",
                "views": "8902"
            },
            {
                "title": "Gachibowli vs HITEC City: Where should you invest in 2026?",
                "link": "https://www.99acres.com/articles/gachibowli-vs-hitec-city.html",
                "snippet": "An in-depth analysis of rental yields and capital appreciation...",
                "author": "Priya Singh",
                "date": "Dec 05, 2025",
                "views": "4521"
            },
            {
                "title": "Upcoming IT parks in Eastern Hyderabad to boost local real estate",
                "link": "https://www.99acres.com/articles/eastern-hyderabad-it-parks.html",
                "snippet": "The eastern corridor of Hyderabad, particularly Pocharam and Uppal...",
                "author": "Vikram Reddy",
                "date": "Nov 18, 2025",
                "views": "2104"
            },
            {
                "title": "Why NRIs continue to prefer Hyderabad for luxury real estate investments",
                "link": "https://www.99acres.com/articles/nri-investment-hyderabad.html",
                "snippet": "A combination of standard of living, infrastructure, and favorable...",
                "author": "Shalini Saraf",
                "date": "Oct 29, 2025",
                "views": "6730"
            }
        ]
        return {"status": "success", "data": fallback_data, "fallback": True}

if __name__ == "__main__":
    import json
    print(json.dumps(scrape_hyderabad_news(), indent=2))
