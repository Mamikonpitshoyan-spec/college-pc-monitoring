"""Level 12: agent installer package download."""

import io
import os
import unittest
import zipfile

from fastapi.testclient import TestClient

import app.models  # noqa: F401
from app.database.base import Base
from app.database.session import engine
from app.main import create_app


@unittest.skipUnless(
    os.path.isdir(os.path.join(os.path.dirname(os.path.dirname(os.getcwd())))),
    "agent dist folder not found",
)
class DownloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client_context = TestClient(create_app())
        cls.client = cls.client_context.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client_context.__exit__(None, None, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def test_download_page_renders(self) -> None:
        response = self.client.get("/download")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Установка агента", response.text)

    def test_agent_package_is_the_single_exe(self) -> None:
        response = self.client.get("/download/agent-package")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('filename="MonitoringAgentApp.exe"', response.headers["content-disposition"])
        self.assertEqual(response.content[:2], b"MZ")

    def test_pairing_code_carries_server_address(self) -> None:
        from app.services.pairing import encode_address, full_code

        self.assertEqual(full_code("A7K-29P", "example.local", 8000), "A7K-29P")
        self.assertIsNone(encode_address("192.168.1.9", 9000))
        packed = full_code("A7K-29P", "192.168.1.9", 8003)
        self.assertRegex(packed, r"^A7K-29P-[A-Z0-9]{4}-[A-Z0-9]{4}$")

if __name__ == "__main__":
    unittest.main()
