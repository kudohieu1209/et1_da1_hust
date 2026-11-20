"""Production SPA routing and same-origin session writes, without live services."""
import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import SESSION_COOKIE_NAME
from app.main import app, health_check, register_frontend, root


class FrontendServingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.dist = Path(directory.name) / "dist"

    def client(self):
        application = FastAPI()
        application.add_api_route("/api/health", health_check)
        application.add_api_route("/api/system", root)
        register_frontend(application, self.dist)
        return TestClient(application)

    def test_development_root_without_built_frontend(self):
        for has_directory in (False, True):
            if has_directory:
                self.dist.mkdir()
            with self.subTest(has_directory=has_directory):
                client = self.client()
                self.assertEqual(client.get("/").json(), client.get("/api/system").json())
                self.assertIn("/", client.get("/openapi.json").json()["paths"])
                self.assertEqual(client.get("/some/spa/route").status_code, 404)

    def test_production_files_spa_and_reserved_routes(self):
        (self.dist / "assets").mkdir(parents=True)
        index = '<html><div id="root"></div></html>'
        (self.dist / "index.html").write_text(index)
        (self.dist / "assets" / "app.js").write_text("console.log('app');")
        (self.dist / "favicon.svg").write_text("<svg/>")
        outside = self.dist.parent / "outside.txt"
        outside.write_text("must remain private")
        (self.dist / "escape.txt").symlink_to(outside)
        client = self.client()
        for path in ("/", "/some/spa/route"):
            response = client.get(path)
            self.assertEqual(response.text, index)
            self.assertIn("text/html", response.headers["content-type"])
        script = client.get("/assets/app.js")
        self.assertEqual(script.text, "console.log('app');")
        self.assertIn("javascript", script.headers["content-type"])
        self.assertEqual(client.get("/favicon.svg").text, "<svg/>")
        self.assertEqual(client.get("/api/health").json(), {"status": "healthy"})
        self.assertEqual(client.get("/api/system").json()["status"], "online")
        self.assertIn("swagger-ui", client.get("/docs").text)
        self.assertIn("redoc", client.get("/redoc").text)
        self.assertIn("openapi", client.get("/openapi.json").json())
        for path in ("/api/missing", "/docs/missing", "/redoc/missing",
                     "/openapi.json/missing", "/assets/missing.js", "/escape.txt",
                     "/%2e%2e/outside.txt"):
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 404)


class SameOriginWriteTests(unittest.TestCase):
    def test_cookie_writes_match_scheme_host_and_port(self):
        client = TestClient(app, base_url="https://demo-advisor.hf.space")
        client.cookies.set(SESSION_COOKIE_NAME, "synthetic-session")
        for origin, status in (
            ("https://demo-advisor.hf.space", 204),
            ("https://demo-advisor.hf.space:443", 204),
            ("http://localhost:5173", 204),
            ("https://untrusted.example", 403),
            ("https://demo-advisor.hf.space.evil.example", 403),
            ("http://demo-advisor.hf.space", 403),
            ("https://demo-advisor.hf.space:444", 403),
            ("null", 403),
        ):
            with self.subTest(origin=origin):
                response = client.post("/api/auth/logout", headers={"Origin": origin})
                self.assertEqual(response.status_code, status)
                client.cookies.set(SESSION_COOKIE_NAME, "synthetic-session")

    def test_https_origin_behind_trusted_proxy(self):
        proxied = ProxyHeadersMiddleware(app, trusted_hosts="*")
        client = TestClient(proxied, base_url="http://demo-advisor.hf.space")
        client.cookies.set(SESSION_COOKIE_NAME, "synthetic-session")
        response = client.post("/api/auth/logout", headers={
            "Origin": "https://demo-advisor.hf.space", "X-Forwarded-Proto": "https",
        })
        self.assertEqual(response.status_code, 204)


class StartupSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_modes(self):
        from unittest import mock
        import app.main as main
        for mode, expected_force in (("auto", False), ("always", True), ("never", None)):
            with self.subTest(mode=mode), mock.patch.object(main, "RAG_SYNC_ON_STARTUP", mode), mock.patch.object(
                main.rag_engine, "sync_knowledge_base", return_value={"status": "success", "total_chunks": 1}
            ) as sync:
                async with main.lifespan(main.app):
                    pass
                if expected_force is None:
                    sync.assert_not_called()
                else:
                    sync.assert_called_once_with(force=expected_force)


class RenderOriginTests(unittest.TestCase):
    def test_render_env_origin_allows_cors_and_csrf_with_internal_host(self):
        # A fresh process exercises config -> CORS middleware -> CSRF together.
        import os
        import subprocess
        import sys
        script = '''
import sys
import tests
from fastapi.testclient import TestClient
from app.core.config import CORS_ORIGINS, SESSION_COOKIE_NAME
from app.main import app
assert "google.genai" not in sys.modules, "Unconfigured Gemini must not load its SDK"
origin = "https://hust-course-advisor.onrender.com"
assert origin in CORS_ORIGINS
assert "https://custom.example" in CORS_ORIGINS
client = TestClient(app, base_url="http://internal-render:10000")
client.cookies.set(SESSION_COOKIE_NAME, "synthetic-session")
preflight = client.options("/api/auth/logout", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
assert preflight.status_code == 200, preflight.text
assert preflight.headers["access-control-allow-origin"] == origin
assert preflight.headers["access-control-allow-credentials"] == "true"
assert client.post("/api/auth/logout", headers={"Origin": origin}).status_code == 204
client.cookies.set(SESSION_COOKIE_NAME, "synthetic-session")
assert client.post("/api/auth/logout", headers={"Origin": origin + ".evil.example"}).status_code == 403
'''
        environment = {**os.environ, "PYTHON_DOTENV_DISABLED": "1", "MONGODB_URI": "",
                       "GEMINI_API_KEY": "", "GOOGLE_API_KEY": "", "VECTOR_DB_DIR": tempfile.mkdtemp(),
                       "CORS_ORIGINS": "https://custom.example",
                       "RENDER_EXTERNAL_URL": "https://hust-course-advisor.onrender.com/"}
        try:
            result = subprocess.run([sys.executable, "-c", script], env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        finally:
            import shutil
            shutil.rmtree(environment["VECTOR_DB_DIR"])


if __name__ == "__main__":
    unittest.main()
