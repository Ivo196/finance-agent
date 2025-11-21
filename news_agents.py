import feedparser
import yfinance as yf
import urllib.parse
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import concurrent.futures
from abc import ABC, abstractmethod

class NewsAgent(ABC):
    @abstractmethod
    def get_news(self, ticker: str) -> list[dict]:
        """
        Returns a list of news items.
        Each item should be a dict:
        {
            "source": str,
            "title": str,
            "link": str,
            "published": str (YYYY-MM-DD HH:MM or similar readable format),
            "timestamp": float (unix timestamp for sorting)
        }
        """
        pass

class GoogleNewsAgent(NewsAgent):
    def get_news(self, ticker: str) -> list[dict]:
        """
        Obtiene noticias de la última semana con búsquedas diversificadas:
        1. Búsqueda fundamental (earnings, financial, reports)
        2. Búsqueda de sentimiento (stock, market, price)
        """
        news_items = []
        
        # Definir múltiples queries para diversificar
        queries = [
            f"{ticker} stock earnings financial report",  # Noticias fundamentales
            f"{ticker} stock market price analysis",       # Noticias de sentimiento
            f"{ticker} stock news"                         # General
        ]
        
        try:
            for query_text in queries:
                encoded_query = urllib.parse.quote(f"{query_text} when:7d")  # 7d = última semana
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
                feed = feedparser.parse(rss_url)
                
                # Tomar menos noticias por query para no saturar (5 por query = 15 total)
                for entry in feed.entries[:5]:
                    dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now()
                    
                    news_items.append({
                        "source": entry.source.title if hasattr(entry, 'source') else "Google News",
                        "title": entry.title,
                        "link": entry.link,
                        "published": dt.strftime('%Y-%m-%d %H:%M'),
                        "timestamp": dt.timestamp()
                    })
        except Exception as e:
            print(f"Error in GoogleNewsAgent: {e}")
        
        return news_items

class YahooNewsAgent(NewsAgent):
    def get_news(self, ticker: str) -> list[dict]:
        news_items = []
        try:
            stock = yf.Ticker(ticker)
            news_data = stock.news
            
            if news_data:
                for n in news_data:
                    ts = n.get('providerPublishTime', 0)
                    dt = datetime.fromtimestamp(ts)
                    
                    news_items.append({
                        "source": n.get('publisher', 'Yahoo Finance'),
                        "title": n.get('title', 'No Title'),
                        "link": n.get('link', '#'),
                        "published": dt.strftime('%Y-%m-%d %H:%M'),
                        "timestamp": float(ts)
                    })
        except Exception as e:
            print(f"Error in YahooNewsAgent: {e}")
        return news_items

class FinVizNewsAgent(NewsAgent):
    def get_news(self, ticker: str) -> list[dict]:
        news_items = []
        try:
            # Using direct scraping as it's often more reliable/faster than wrappers for simple news
            url = f"https://finviz.com/quote.ashx?t={ticker}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            news_table = soup.find(id='news-table')
            if news_table:
                rows = news_table.findAll('tr')
                for row in rows[:10]:
                    a_tag = row.find('a')
                    if not a_tag: continue
                    
                    link = a_tag['href']
                    title = a_tag.text
                    
                    # Date parsing in FinViz is tricky (sometimes just time if same day)
                    td_text = row.td.text.strip()
                    # Simple placeholder for now, improving date parsing would be good but complex
                    # Format is usually "Nov-20-25 09:00PM" or just "09:00PM"
                    
                    news_items.append({
                        "source": "FinViz",
                        "title": title,
                        "link": link,
                        "published": td_text, # Keep raw text for now
                        "timestamp": datetime.now().timestamp() # Fallback
                    })
        except Exception as e:
            print(f"Error in FinVizNewsAgent: {e}")
        return news_items

class InvestingComAgent(NewsAgent):
    def get_news(self, ticker: str) -> list[dict]:
        news_items = []
        try:
            # Investing.com search RSS is tricky, using a general market news fallback or specific if possible
            # For now, let's use a general search RSS or similar. 
            # Actually, scraping the search page might be better but harder.
            # Let's try a search RSS approach if available, otherwise fallback to general US stock news
            # Note: Investing.com often blocks scrapers. We will try a known RSS feed for general context if specific fails.
            
            # Using a general feed for "Stock Market News" as a reliable fallback
            rss_url = "https://www.investing.com/rss/news_25.rss" 
            feed = feedparser.parse(rss_url)
            
            for entry in feed.entries[:5]:
                 dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now()
                 news_items.append({
                    "source": "Investing.com",
                    "title": entry.title,
                    "link": entry.link,
                    "published": dt.strftime('%Y-%m-%d %H:%M'),
                    "timestamp": dt.timestamp()
                })
        except Exception as e:
            print(f"Error in InvestingComAgent: {e}")
        return news_items

class NewsAggregator:
    def __init__(self):
        self.agents = [
            GoogleNewsAgent(),
            YahooNewsAgent(),
            FinVizNewsAgent(),
            InvestingComAgent()
        ]
    
    def get_consolidated_news(self, ticker: str) -> list[dict]:
        all_news = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_agent = {executor.submit(agent.get_news, ticker): agent for agent in self.agents}
            for future in concurrent.futures.as_completed(future_to_agent):
                try:
                    data = future.result()
                    if data:
                        all_news.extend(data)
                except Exception as exc:
                    print(f"Agent generated an exception: {exc}")
        
        # Deduplicate by Title (fuzzy match or exact)
        seen_titles = set()
        unique_news = []
        for item in all_news:
            # Simple normalization
            title_slug = ''.join(e for e in item['title'] if e.isalnum()).lower()
            if title_slug not in seen_titles:
                seen_titles.add(title_slug)
                unique_news.append(item)
        
        # Sort by timestamp descending (más reciente primero)
        unique_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        # Limitar a las mejores 20 noticias para no saturar el prompt
        # Esto da un balance entre contexto histórico y relevancia
        return unique_news[:20]
