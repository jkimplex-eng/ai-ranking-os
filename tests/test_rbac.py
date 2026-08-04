import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base, get_db
from backend.app.main import app
from rbac.repository import SqlAlchemyRbacRepository
from rbac.schemas import PermissionCreate, RoleCreate, RoleUpdate
from rbac.service import RbacError, RbacService


@pytest.fixture
def context():
    engine = create_engine(
        "sqlite+pysqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


def test_inherited_permission_and_cycle(context):
    with context() as db:
        service = RbacService(SqlAlchemyRbacRepository(db))
        viewer = service.create_role(RoleCreate(code="Viewer", name="Viewer"))
        analyst = service.create_role(
            RoleCreate(code="Analyst", name="Analyst", parent_role_ids=[viewer.id])
        )
        permission = service.create_permission(
            PermissionCreate(resource="analytics", action="read")
        )
        service.grant(viewer.id, permission.id)
        service.assign(7, analyst.id)
        assert service.is_allowed(7, "analytics", "read")
        with pytest.raises(RbacError, match="cycle"):
            service.update_role(viewer.id, RoleUpdate(parent_role_ids=[analyst.id]))


def test_rbac_api_and_openapi(context):
    def override():
        with context() as db:
            yield db

    app.dependency_overrides[get_db] = override
    client = TestClient(app)
    role = client.post("/rbac/roles", json={"code": "API", "name": "API"})
    permission = client.post("/rbac/permissions", json={"resource": "research", "action": "read"})
    assert role.status_code == permission.status_code == 201
    assert (
        client.post(
            f"/rbac/roles/{role.json()['id']}/permissions",
            json={"permission_id": permission.json()["id"]},
        ).status_code
        == 200
    )
    client.post("/rbac/users/9/roles", json={"role_id": role.json()["id"]})
    assert client.post(
        "/rbac/check", json={"user_id": 9, "resource": "research", "action": "read"}
    ).json()["allowed"]
    assert "/rbac/check" in app.openapi()["paths"]
    app.dependency_overrides.clear()
