import requests
import json

BASE_URL = "https://mahadev-jyotish-ai-backend-438666816654.asia-southeast1.run.app"

def search_rag(query, corpus):
    url = f"{BASE_URL}/api/v1/rag/search"
    payload = {
        "query": query,
        "corpus": corpus,
        "top_k": 3
    }
    r = requests.post(url, json=payload, timeout=30)
    if r.status_code == 200:
        return r.json()
    return None

def run_checks():
    checks = [
        ("PALMISTRY", "जीवन रेखा क्या बताती है?"),
        ("PALMISTRY", "विवाह रेखा का क्या अर्थ है?"),
        ("PALMISTRY", "What does the Mount of Jupiter represent?"),
        ("KP", "7th cusp sub lord marriage के बारे में क्या बताता है?"),
        ("KP", "What does the 10th cusp sub lord indicate?")
    ]

    for corpus, query in checks:
        print(f"\n[{corpus}] QUERY: {query}")
        res = search_rag(query, corpus)
        if res and res.get('retrieved_chunks'):
            for i, chunk in enumerate(res['retrieved_chunks']):
                print(f"  [{i+1}] {chunk['book_title']} (Score: {chunk['score']})")
                print(f"      {chunk['text'][:150]}...")
        else:
            print("  FAIL: No chunks retrieved")

if __name__ == "__main__":
    run_checks()
