import unittest

try:
    import sys
    from pathlib import Path
    from fastapi.testclient import TestClient

    # Pastikan src ada di sys.path agar api_fastapi bisa di-import
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    try:
        from api_fastapi import app  # type: ignore
    except Exception:
        from chatbot.api_fastapi import app  # type: ignore
    HAS_TESTCLIENT = True
except Exception:
    HAS_TESTCLIENT = False


@unittest.skipUnless(HAS_TESTCLIENT, "TestClient or FastAPI app not available")
class TestApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_chat_endpoint(self):
        resp = self.client.post("/chat", json={"message": "halo"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("intent", data)
        self.assertIn("reply", data)
        self.assertIn("status", data)
        self.assertIn(data["status"], ["AUTO_RESPONSE", "TO_CS", "TO_NOC"])

    def test_cs_escalate(self):
        resp = self.client.post("/cs/escalate", json={"message": "tolong"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ticket_id", data)

    def test_noc_escalate(self):
        resp = self.client.post("/noc/escalate", json={"message": "kabel putus"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("ticket_id", data)


if __name__ == "__main__":
    unittest.main()
