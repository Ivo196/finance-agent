import feedparser
import yfinance as yf
import urllib.parse
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import concurrent.futures
from abc import ABC, abstractmethod

class NewsAgent(ABC):
    @abstractmethod
    def get_news(self, ticker: str, days: int = 7) -> list[dict]:
        """
        Returns a list of news items from the last 'days'.
        Each item should be a dict:
        {
            "source": str,
            "title": str,
            "link": str,
            "published": str (YYYY-MM-DD HH:MM),
            "timestamp": float (unix timestamp for sorting)
        }
        """
        pass

class GoogleNewsAgent(NewsAgent):
    def get_news(self, ticker: str, days: int = 7) -> list[dict]:
        """
        Obtiene noticias de los últimos 'days' días.
        """
        news_items = []
        
        # Definir múltiples queries para diversificar
        queries = [
            f"{ticker} stock earnings financial",
            f"{ticker} stock price market",
            f"{ticker} stock news"
        ]
        
        try:
            for query_text in queries:
                # when:Xd syntax for Google News
                encoded_query = urllib.parse.quote(f"{query_text} when:{days}d")
                rss_url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"
                feed = feedparser.parse(rss_url)
                
                # Aumentamos límite a 10 por query
                for entry in feed.entries[:10]:
                    dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now()
                    
                    # Double check date just in case
                    if (datetime.now() - dt).days > days + 1:
                        continue

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
    def get_news(self, ticker: str, days: int = 7) -> list[dict]:
        news_items = []
        cutoff_date = datetime.now() - timedelta(days=days)
        
        try:
            stock = yf.Ticker(ticker)
            news_data = stock.news
            
            if news_data:
                for n in news_data:
                    ts = n.get('providerPublishTime', 0)
                    dt = datetime.fromtimestamp(ts)
                    
                    if dt < cutoff_date:
                        continue
                    
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
    def get_news(self, ticker: str, days: int = 7) -> list[dict]:
        news_items = []
        # FinViz doesn't support easy date filtering in URL, so we parse and filter if possible
        # For simplicity in scraping, we just take the top items and assume they are recent.
        try:
            url = f"https://finviz.com/quote.ashx?t={ticker}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(url, headers=headers, timeout=5)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            news_table = soup.find(id='news-table')
            if news_table:
                rows = news_table.findAll('tr')
                for row in rows[:15]: # Check top 15
                    a_tag = row.find('a')
                    if not a_tag: continue
                    
                    link = a_tag['href']
                    title = a_tag.text
                    td_text = row.td.text.strip()
                    
                    # Very basic date parsing could go here, but for now we trust FinViz sorts by date
                    # We'll just take them as "Recent"
                    
                    news_items.append({
                        "source": "FinViz",
                        "title": title,
                        "link": link,
                        "published": td_text, 
                        "timestamp": datetime.now().timestamp() 
                    })
        except Exception as e:
            print(f"Error in FinVizNewsAgent: {e}")
        return news_items

class InvestingComAgent(NewsAgent):
    def get_news(self, ticker: str, days: int = 7) -> list[dict]:
        news_items = []
        try:
            rss_url = "https://www.investing.com/rss/news_25.rss" 
            feed = feedparser.parse(rss_url)
            
            cutoff_date = datetime.now() - timedelta(days=days)

            for entry in feed.entries[:10]:
                 dt = datetime(*entry.published_parsed[:6]) if hasattr(entry, 'published_parsed') and entry.published_parsed else datetime.now()
                 
                 if dt < cutoff_date:
                     continue

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
    
    def get_consolidated_news(self, ticker: str, days: int = 7) -> list[dict]:
        all_news = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_agent = {executor.submit(agent.get_news, ticker, days): agent for agent in self.agents}
            for future in concurrent.futures.as_completed(future_to_agent):
                try:
                    data = future.result()
                    if data:
                        all_news.extend(data)
                except Exception as exc:
                    print(f"Agent generated an exception: {exc}")
        
        # Deduplicate by Title
        seen_titles = set()
        unique_news = []
        for item in all_news:
            title_slug = ''.join(e for e in item['title'] if e.isalnum()).lower()
            if title_slug not in seen_titles:
                seen_titles.add(title_slug)
                unique_news.append(item)
        
        # Sort by timestamp descending
        unique_news.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
        
        return unique_news[:30] # Increased limit

