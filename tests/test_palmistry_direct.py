import asyncio
import base64
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.palmistry_service import PalmistryService
from app.schemas.palmistry import PalmReadingMode, ImageType, HandSide

async def main():
    service = PalmistryService()
    print("Creating session...")
    sess = await service.create_session("prof_dev", PalmReadingMode.DEEP, HandSide.RIGHT)

    print("Session created:", sess.id)

    # Fake 30KB image base64
    dummy_img = base64.b64encode(b"\xff\xd8\xff" + b"A" * 35000).decode('ascii')

    print("Uploading right hand image...")
    res1 = await service.upload_image(sess.id, ImageType.RIGHT_FULL, dummy_img)
    print("Right hand status:", res1.status)

    print("Uploading left hand image...")
    res2 = await service.upload_image(sess.id, ImageType.LEFT_FULL, dummy_img)
    print("Left hand status:", res2.status)

    if res2.right_hand and res2.left_hand:
        print("PALMISTRY DIRECT TEST PASSED SUCCESSFULLY!")
        print("Right hand shape:", res2.right_hand.hand_shape)
        print("Interpretation snippet:", res2.interpretation[:150] if res2.interpretation else "None")
    else:
        print("Status:", res2.status, "Requests:", res2.supplemental_requests)

if __name__ == "__main__":
    asyncio.run(main())
