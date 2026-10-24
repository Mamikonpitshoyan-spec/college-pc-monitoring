"""Smoke tests for the Stage 1 server structure."""

import unittest


class ServerImportTests(unittest.TestCase):
    def test_application_factory_imports(self) -> None:
        from app.main import create_app

        app = create_app()
        self.assertEqual(app.title, "Centralized Computer Monitoring Server")

    def test_database_infrastructure_imports(self) -> None:
        from app.database.session import SessionLocal, engine

        self.assertIsNotNone(engine)
        self.assertTrue(callable(SessionLocal))


if __name__ == "__main__":
    unittest.main()
