from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.repositories.database import Base, get_db
from app.repositories.tables import User
from app.repositories.problems import a_plus_b_problem
from app.services.auth import password_hash

from app.utils.common import model_dict


@pytest.fixture()
def db_session_factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    with factory() as db:
        db.add_all(
            [
                User(
                    username="admin",
                    password_hash=password_hash("admin12345"),
                    role="admin",
                ),
                User(
                    username="teacher",
                    password_hash=password_hash("teacher123"),
                    role="teacher",
                ),
            ]
        )
        db.commit()

    yield factory
    engine.dispose()


@pytest.fixture()
def client(db_session_factory, monkeypatch) -> Iterator[TestClient]:
    def override_get_db():
        with db_session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr("app.routers.submission.start_judge", lambda _id: None)
    test_client = TestClient(app)
    yield test_client
    test_client.close()
    app.dependency_overrides.clear()


@pytest.fixture()
def student(client: TestClient) -> TestClient:
    response = client.post(
        "/api/auth/register",
        json={"username": "student", "password": "student123"},
    )
    assert response.status_code == 201
    response = client.post(
        "/api/auth/login",
        json={"username": "student", "password": "student123"},
    )
    assert response.status_code == 200
    return client


@pytest.fixture()
def problem_data() -> dict:
    return model_dict(a_plus_b_problem)


def login(client: TestClient, username: str, password: str) -> None:
    response = client.post("/api/auth/login", 
                           json={"username": username, "password": password})
    assert response.status_code == 200


def create_problem(client: TestClient, problem_data: dict) -> None:
    login(client, "teacher", "teacher123")
    response = client.post("/api/problems", json=problem_data)
    assert response.status_code == 201
    client.post("/api/auth/logout")


def test_unauthenticated_user_cannot_access_profile(client: TestClient):
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_register_login_profile_and_logout(client: TestClient):
    credentials = {"username": "student1", "password": "student123"}
    registered = client.post("/api/auth/register", json=credentials)
    assert registered.status_code == 201
    assert registered.json()["data"]["username"] == "student1"
    assert "password_hash" not in registered.json()["data"]

    logged_in = client.post("/api/auth/login", json=credentials)
    assert logged_in.status_code == 200
    assert logged_in.json()["data"]["username"] == "student1"

    profile = client.get("/api/auth/me")
    assert profile.status_code == 200
    assert profile.json()["data"]["username"] == "student1"

    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_duplicate_registration_and_bad_login(client: TestClient):
    credentials = {"username": "student2", "password": "student123"}
    assert client.post("/api/auth/register", json=credentials).status_code == 201

    duplicate = client.post("/api/auth/register", json=credentials)
    bad_login = client.post(
        "/api/auth/login",
        json={"username": "student2", "password": "student12345"},
    )
    assert duplicate.status_code == 409
    assert bad_login.status_code == 401


def test_student_cannot_create_problem(student: TestClient, problem_data: dict):
    response = student.post("/api/problems", json=problem_data)
    assert response.status_code == 403


def test_teacher_can_create_update_and_delete_problem(
    client: TestClient, problem_data: dict
):
    login(client, "teacher", "teacher123")

    created = client.post("/api/problems", json=problem_data)
    assert created.status_code == 201

    updated_data = {**problem_data, "title": "A+B Problem updated"}
    updated = client.put("/api/problems/P1001", json=updated_data)
    assert updated.status_code == 200
    assert client.get("/api/problems/P1001").json()["data"]["title"] == "A+B Problem updated"

    assert client.delete("/api/problems/P1001").status_code == 200
    assert client.get("/api/problems/P1001").status_code == 404


def test_student_problem_view_hides_test_cases(
    client: TestClient, student: TestClient, problem_data: dict
):
    create_problem(client, problem_data)
    login(client, "admin", "admin12345")
    teacher_view = client.get("/api/problems/P1001")
    assert "test_cases" in teacher_view.json()["data"]
    client.post("/api/auth/logout")
    
    login(client, "student", "student123")
    student_view = client.get("/api/problems/P1001")

    assert student_view.status_code == 200
    assert "test_cases" not in student_view.json()["data"]


def test_submission_creation_and_owner_queries(
    client: TestClient, problem_data: dict
):
    create_problem(client, problem_data)
    login(client, "admin", "admin12345")
    created = client.post(
        "/api/submissions",
        json={
            "problem_id": "P1001",
            "language": "python",
            "source_code": "a, b = map(int, input().split())\nprint(a + b)\n",
        },
    )
    assert created.status_code == 202
    submission_id = created.json()["data"]["submission_id"]

    detail = client.get(f"/api/submissions/{submission_id}")
    listing = client.get("/api/submissions")
    assert detail.status_code == 200
    assert detail.json()["data"]["problem_id"] == "P1001"
    assert listing.status_code == 200
    assert listing.json()["data"]["total"] == 1
    assert listing.json()["data"]["items"][0]["id"] == submission_id


def test_submission_validation(student: TestClient):
    missing_problem = student.post(
        "/api/submissions",
        json={"problem_id": "missing", "source_code": "print(1)"},
    )
    blank_code = student.post(
        "/api/submissions",
        json={"problem_id": "missing", "source_code": "   "},
    )

    assert missing_problem.status_code == 404
    assert blank_code.status_code == 422


def test_only_admin_can_list_users(client: TestClient, student: TestClient):
    forbidden = student.get("/api/users")
    assert forbidden.status_code == 403

    student.post("/api/auth/logout")
    login(client, "admin", "admin12345")
    response = client.get("/api/users?page=1&page_size=10")

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 3
