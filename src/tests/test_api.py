import unittest

try:
    from fastapi.testclient import TestClient
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
