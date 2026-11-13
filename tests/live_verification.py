import requests
import json
import time

BASE_URL = "https://mahadev-jyotish-ai-backend-438666816654.asia-southeast1.run.app"

def test_endpoint(name, path, method="GET", payload=None):
    print(f"Testing {name}...")
    url = f"{BASE_URL}{path}"
    try:
        if method == "GET":
            r = requests.get(url, timeout=30)
        else:
            r = requests.post(url, json=payload, timeout=30)

        if r.status_code == 200:
            print(f"  {name}: PASS")
            return True, r.json()
        elif r.status_code == 401:
            print(f"  {name}: PASS (Auth Required)")
            return True, "401"
        else:
            print(f"  {name}: FAIL (Status {r.status_code})")
            print(f"  Response: {r.text[:200]}")
            return False, r.text
    except Exception as e:
        print(f"  {name}: ERROR - {str(e)}")
        return False, str(e)

def run_all_tests():
    results = {}

    # 1. Health
    results['health'], _ = test_endpoint("Health", "/health")

    # 2. RAG Vedic
    results['rag_vedic'], _ = test_endpoint("RAG Vedic", "/api/v1/rag/search", "POST", {
        "query": "What are shlokas in BPHS?",
        "corpus": "VEDIC",
        "top_k": 1
    })

    # 3. RAG KP
    results['rag_kp'], _ = test_endpoint("RAG KP", "/api/v1/rag/search", "POST", {
        "query": "7th cusp sub lord marriage",
        "corpus": "KP",
        "top_k": 1
    })

    # 4. RAG Palmistry
    results['rag_palmistry'], _ = test_endpoint("RAG Palmistry", "/api/v1/rag/search", "POST", {
        "query": "जीवन रेखा क्या बताती है?",
        "corpus": "PALMISTRY",
        "top_k": 1
    })

    natal_payload = {
        "name": "Test",
        "date_of_birth": "1990-05-15",
        "time_of_birth": "10:30:00",
        "latitude": 28.61,
        "longitude": 77.21,
        "timezone_id": "Asia/Kolkata"
    }

    # 5. Vedic Calculation
    results['vedic_calc'], _ = test_endpoint("Vedic Calc", "/api/v1/calculations/vedic", "POST", natal_payload)

    # 6. KP Calculation
    results['kp_calc'], _ = test_endpoint("KP Calc", "/api/v1/calculations/kp", "POST", natal_payload)

    # 7. Dasha
    results['dasha'], _ = test_endpoint("Dasha", "/api/v1/calculations/dasha", "POST", natal_payload)

    # 8. Gochar
    gochar_payload = natal_payload.copy()
    gochar_payload["target_datetime_utc"] = "2024-08-21T12:00:00Z"
    results['gochar'], _ = test_endpoint("Gochar", "/api/v1/calculations/gochar", "POST", gochar_payload)

    # 12. PDF (Protected)
    results['pdf'], _ = test_endpoint("PDF Endpoint", "/api/v1/reports/generate", "POST", {"profile_id": "test", "type": "VEDIC", "language": "en"})

    # 13. Wallet (Protected)
    results['wallet'], _ = test_endpoint("Wallet Endpoint", "/api/v1/wallet")

    print("\nVerification Summary:")
    for k, v in results.items():
        print(f"{k}: {'PASS' if v else 'FAIL'}")

if __name__ == "__main__":
    run_all_tests()
