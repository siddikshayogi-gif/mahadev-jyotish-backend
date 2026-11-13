import requests
import json
import time

BASE_URL = "https://mahadev-jyotish-ai-backend-438666816654.asia-southeast1.run.app"
AUTH_HEADER = {"Authorization": "Bearer test_token_final_live_v2"}
DUMMY_IMAGE = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

def test_step(name, logic_fn):
    print(f"\n[STEP] {name}")
    try:
        success, result = logic_fn()
        if success:
            print(f"  Result: PASS")
            return result
        else:
            print(f"  Result: FAIL - {result}")
            return None
    except Exception as e:
        print(f"  Result: ERROR - {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def create_and_setup_session(profile_id="test_user"):
    r = requests.post(f"{BASE_URL}/api/v1/palm/session", json={"profile_id": profile_id, "mode": "DEEP"}, headers=AUTH_HEADER)
    if r.status_code != 200: return False, f"Create session failed: {r.text}"
    session_id = r.json()["id"]

    requests.post(f"{BASE_URL}/api/v1/palm/upload", json={"session_id": session_id, "image_type": "RIGHT_FULL", "image_base64": DUMMY_IMAGE}, headers=AUTH_HEADER)
    requests.post(f"{BASE_URL}/api/v1/palm/upload", json={"session_id": session_id, "image_type": "LEFT_FULL", "image_base64": DUMMY_IMAGE}, headers=AUTH_HEADER)

    for i in range(20):
        r = requests.get(f"{BASE_URL}/api/v1/palm/session/{session_id}", headers=AUTH_HEADER)
        status = r.json()["status"]
        print(f"    Polling status ({i+1}): {status}")
        if status == "COMPLETED":
            return True, r.json()
        if status == "FAILED":
            return False, "Session failed"
        time.sleep(5)
    return False, "Timeout"

def run_verification():
    # 1. Setup Session 1 (Normal)
    sess1 = test_step("Session 1 Setup (Normal)", lambda: create_and_setup_session("NormalUser"))
    if not sess1: return
    s1_id = sess1["id"]

    # 2. Setup Session 2 (Weak)
    sess2 = test_step("Session 2 Setup (Weak)", lambda: create_and_setup_session("WeakProfile"))
    if not sess2: return
    s2_id = sess2["id"]

    # 3. Personalization Test
    print("\n[TEST] Personalization Check")
    q = "मेरी भाग्य रेखा career के बारे में क्या बताती है?"
    r1 = requests.post(f"{BASE_URL}/api/v1/palm/session/{s1_id}/ask", json={"question": q, "mode": "DEEP", "language": "hi"}, headers=AUTH_HEADER).json()
    r2 = requests.post(f"{BASE_URL}/api/v1/palm/session/{s2_id}/ask", json={"question": q, "mode": "DEEP", "language": "hi"}, headers=AUTH_HEADER).json()

    print(f"  S1 (Normal) Answer: {r1.get('answer', 'N/A')[:100]}...")
    print(f"  S2 (Weak) Answer: {r2.get('answer', 'N/A')[:100]}...")

    if r1.get('answer') != r2.get('answer'):
        print("  Personalization: PASS")
    else:
        print("  Personalization: FAIL (Identical answers)")

    # 4. Follow-up Memory Test
    print("\n[TEST] Follow-up Memory")
    q_follow = "इसका स्वभाव पर क्या प्रभाव पड़ेगा?"
    rf = requests.post(f"{BASE_URL}/api/v1/palm/session/{s1_id}/ask", json={"question": q_follow}, headers=AUTH_HEADER).json()
    print(f"  Follow-up Answer: {rf.get('answer', 'N/A')[:150]}...")
    if "भाग्य" in rf.get('answer', '') or "fate" in rf.get('answer', '').lower() or len(rf.get('history', [])) > 2:
        print("  Memory: PASS")
    else:
        print("  Memory: FAIL")

    # 5. Supplemental Photo Test
    print("\n[TEST] Supplemental Photo Request")
    q_supp = "मेरे कितने बच्चे होंगे?"
    rs = requests.post(f"{BASE_URL}/api/v1/palm/session/{s1_id}/ask", json={"question": q_supp}, headers=AUTH_HEADER).json()
    if rs["type"] == "NEED_MORE_EVIDENCE":
        print(f"  Correct status: {rs['type']}")
        print(f"  Reason: {rs['supplemental_request']['reason']}")

        # Uploading supplemental
        itype = rs['supplemental_request']['image_type']
        print(f"  Uploading: {itype}")
        ru = requests.post(f"{BASE_URL}/api/v1/palm/upload", json={"session_id": s1_id, "image_type": itype, "image_base64": DUMMY_IMAGE}, headers=AUTH_HEADER).json()

        if ru["status"] == "COMPLETED":
            print("  Resumed automatically. Checking last assistant message...")
            # Search for the answer in history
            ans = next((m["content"] for m in reversed(ru.get("history", [])) if m["role"] == "assistant"), None)
            if ans and "बच्चे" in ans:
                print(f"  Answer found: {ans[:100]}...")
                print("  Auto-Resume: PASS")
            else:
                print(f"  Answer missing or irrelevant in history. Last msg: {ans}")
                print("  Auto-Resume: FAIL")
        else:
            print(f"  Status not completed: {ru['status']}")
    else:
        print(f"  Fail: Expected NEED_MORE_EVIDENCE but got {rs['type']}")

    # 6. Source Transparency
    print("\n[TEST] Source Transparency")
    if sess1.get("sources"):
        print(f"  Sources found: {len(sess1['sources'])}")
        for s in sess1['sources']:
             print(f"    - {s['title']}")
        print("  Transparency: PASS")
    else:
        print("  Transparency: FAIL")

if __name__ == "__main__":
    run_verification()
