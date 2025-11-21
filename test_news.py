from news_agents import NewsAggregator
import time

def test_news_fetching():
    ticker = "AAPL"
    print(f"Testing news fetching for {ticker}...")
    
    aggregator = NewsAggregator()
    start_time = time.time()
    news = aggregator.get_consolidated_news(ticker)
    end_time = time.time()
    
    print(f"Fetched {len(news)} news items in {end_time - start_time:.2f} seconds.")
    
    if not news:
        print("FAILED: No news fetched.")
        return
    
    sources = set(n['source'] for n in news)
    print(f"Sources found: {sources}")
    
    print("\nTop 5 News Items:")
    for n in news[:5]:
        print(f"- [{n['source']}] {n['title']} ({n['published']})")

if __name__ == "__main__":
    test_news_fetching()
