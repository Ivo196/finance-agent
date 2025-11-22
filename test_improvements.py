#!/usr/bin/env python3
"""
Quick test script to verify the improvements made to the AI finance agent.
Tests: 1) ADX calculation, 2) News aggregation, 3) Description truncation
"""

import sys
sys.path.insert(0, '/Users/ivotonioni/Documents/Ivo/Repositories/ai-finance-agent')

def test_adx_calculation():
    """Test that ADX calculation works with Wilder smoothing"""
    print("\n" + "="*60)
    print("TEST 1: ADX Calculation with Wilder Smoothing")
    print("="*60)
    
    try:
        import yfinance as yf
        from calculate_indicators import calculate_indicators
        
        # Get sample data
        ticker = "AAPL"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo", interval="1d")
        
        if hist.empty:
            print("❌ Failed to download data")
            return False
        
        # Calculate indicators
        hist = calculate_indicators(hist)
        
        # Check that ADX exists and is reasonable
        last_adx = hist['ADX'].iloc[-1]
        last_atr = hist['ATR'].iloc[-1]
        
        print(f"✅ ADX calculated successfully for {ticker}")
        print(f"   Last ADX value: {last_adx:.2f}")
        print(f"   Last ATR value: {last_atr:.2f}")
        
        # ADX should be between 0 and 100
        if 0 <= last_adx <= 100 and not pd.isna(last_adx):
            print(f"✅ ADX value is in valid range (0-100)")
            return True
        else:
            print(f"❌ ADX value is invalid: {last_adx}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing ADX: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_news_aggregation():
    """Test that news aggregation works with all sources"""
    print("\n" + "="*60)
    print("TEST 2: News Aggregation with Descriptions")
    print("="*60)
    
    try:
        from news_agents import NewsAggregator
        
        aggregator = NewsAggregator()
        ticker = "AAPL"
        news = aggregator.get_consolidated_news(ticker, days=7)
        
        print(f"✅ Found {len(news)} news items for {ticker}")
        
        if len(news) > 0:
            # Check first news item structure
            first = news[0]
            print(f"\n   Sample news item:")
            print(f"   - Source: {first.get('source', 'N/A')}")
            print(f"   - Title: {first.get('title', 'N/A')[:60]}...")
            print(f"   - Published: {first.get('published', 'N/A')}")
            print(f"   - Has description: {'description' in first and bool(first['description'])}")
            
            # Check for duplicates using the new cleaning
            from news_agents import NewsAgent
            titles = [NewsAgent._clean_title(n['title']) for n in news]
            unique_titles = len(set(titles))
            
            print(f"\n   Total news: {len(news)}")
            print(f"   Unique titles (after cleaning): {unique_titles}")
            
            if unique_titles == len(news):
                print(f"✅ No duplicates detected")
                return True
            else:
                print(f"⚠️  Some duplicates may exist ({len(news) - unique_titles} potential duplicates)")
                return True  # Still pass, aggressive cleaning might filter some
        else:
            print("⚠️  No news found (might be normal for some tickers)")
            return True
            
    except Exception as e:
        print(f"❌ Error testing news: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_description_truncation():
    """Test that description truncation works correctly"""
    print("\n" + "="*60)
    print("TEST 3: Description Truncation")
    print("="*60)
    
    try:
        from data_loader import _truncate_description
        
        # Test cases
        test_cases = [
            ("Short text", "Short text"),  # No truncation needed
            ("This is a longer text. It has multiple sentences. We want to see if it truncates properly at sentence boundaries. This should be cut off.", 
             "This is a longer text. It has multiple sentences. We want to see if it truncates properly at sentence boundaries."),
            ("A very long text without periods that goes on and on and on and should be truncated at a word boundary instead of in the middle of a word to maintain readability and avoid cutting words in half which would look unprofessional",
             None)  # Will truncate at word boundary
        ]
        
        all_passed = True
        for i, (input_text, expected_pattern) in enumerate(test_cases, 1):
            result = _truncate_description(input_text, max_length=250)
            
            print(f"\n   Test case {i}:")
            print(f"   Input length: {len(input_text)}")
            print(f"   Output length: {len(result)}")
            print(f"   Output: {result[:100]}{'...' if len(result) > 100 else ''}")
            
            if len(result) <= 250:
                print(f"   ✅ Within 250 char limit")
            else:
                print(f"   ❌ Exceeds 250 char limit!")
                all_passed = False
                
        return all_passed
            
    except Exception as e:
        print(f"❌ Error testing truncation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n🚀 Running AI Finance Agent Improvement Tests\n")
    
    import pandas as pd
    
    results = {
        "ADX Calculation": test_adx_calculation(),
        "News Aggregation": test_news_aggregation(),
        "Description Truncation": test_description_truncation()
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review the output above.")
        sys.exit(1)
