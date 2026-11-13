import asyncio
import httpx

BASE_URL = "https://mahadev-jyotish-ai-backend-438666816654.asia-southeast1.run.app/api/v1/calculations"

async def test_gochar():
    # Target date
    target = "2026-08-15T06:30:00Z"

    profiles = [
        {"name": "Vineet", "latitude": 26.9124, "longitude": 75.7873, "date_of_birth": "1998-02-05", "time_of_birth": "11:30:00", "timezone_id": "Asia/Kolkata"},
        {"name": "Night_Ref", "latitude": 26.9124, "longitude": 75.7873, "date_of_birth": "1998-02-05", "time_of_birth": "23:30:00", "timezone_id": "Asia/Kolkata"}
    ]

    async with httpx.AsyncClient(timeout=30.0) as client:
        results = []
        for p in profiles:
            r = await client.post(f"{BASE_URL}/gochar", json={**p, "target_datetime_utc": target})
            results.append(r.json())

        m1 = next(t for t in results[0]['transits'] if t['body'] == 'Moon')
        m2 = next(t for t in results[1]['transits'] if t['body'] == 'Moon')

        print(f"Profile 1 (Vineet) Transit Moon Lon: {m1['sidereal_longitude']:.4f} | House from Lagna: {m1['house_from_d1_lagna']}")
        print(f"Profile 2 (London) Transit Moon Lon: {m2['sidereal_longitude']:.4f} | House from Lagna: {m2['house_from_d1_lagna']}")

        assert abs(m1['sidereal_longitude'] - m2['sidereal_longitude']) < 1e-5
        assert m1['house_from_d1_lagna'] != m2['house_from_d1_lagna']
        print("Gochar Closure Test: PASS")

if __name__ == "__main__":
    asyncio.run(test_gochar())
