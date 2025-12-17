from duckduckgo_search import DDGS
import json

def test_search(query):
    print(f"Testing query: '{query}'")
    try:
        results = list(DDGS().text(query, max_results=5))
        for r in results:
            print(f"- {r.get('title')}: {r.get('href')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search("Baksters official website")
    print("-" * 20)
    test_search("Baksters")
