"""Read-only live connection probe; never print credentials or provider payloads."""
import json

from backend.app.main import app  # noqa: F401 -- registers ORM models
from backend.app.database import SessionLocal
from yandex_wordstat.router import _service as wordstat_service
from yandex_webmaster.router import _service as webmaster_service


def main():
    from backend.app.config import get_settings
    print(json.dumps({"security_enforce_auth": get_settings().security_enforce_auth}))
    import httpx
    settings = get_settings()
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        login = client.post("/auth/login", json={"email": settings.admin_email, "password": settings.admin_password})
        print(json.dumps({"admin_login_status": login.status_code}))
        if login.is_success:
            client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
            for path in ["/auth/me", "/integrations/yandex-wordstat/status", "/integrations/yandex-webmaster/status", "/yandex-intelligence/dashboard", "/alice-learning/dashboard", "/alice-learning/automation/dashboard"]:
                response = client.get(path)
                result = {"path": path, "status": response.status_code}
                if path == "/auth/me" and response.is_success:
                    result["user_id"] = response.json().get("id")
                print(json.dumps(result))
            for path in ["/workspace/projects", "/research", "/geo/site-audits"]:
                response = client.get(path)
                if response.is_success and isinstance(response.json(), list):
                    print(json.dumps({"path": path, "items": [{key: item.get(key) for key in
                        ["id", "name", "title", "status", "project_id", "score", "final_url"] if key in item}
                        for item in response.json()[-8:]]}, ensure_ascii=False))
    with SessionLocal() as db:
        from yandex_wordstat.models import WordstatConnection
        from sqlalchemy import select

        for connection in db.scalars(select(WordstatConnection)):
            org = connection.organization_id
            result = {"organization_id": org}
            service = wordstat_service(db)
            try:
                record, credential = service._connection(org)
                data = service._request(credential, record.auth_type,
                    "/v2/wordstat/topRequests", {"phrase": "GEO продвижение",
                    "numPhrases": 1, "devices": ["DEVICE_ALL"], "folderId": record.folder_id})
                result["wordstat"] = {"ok": True, "rows": len(data.get("results", []))}
            except Exception as error:
                result["wordstat"] = {"ok": False, "error_type": type(error).__name__}
            try:
                hosts = webmaster_service(db).hosts(org)
                result["webmaster"] = {"ok": True, "hosts": [
                    {"url": host.ascii_host_url, "verified": host.verified} for host in hosts]}
            except Exception as error:
                result["webmaster"] = {"ok": False, "error_type": type(error).__name__}
            print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
