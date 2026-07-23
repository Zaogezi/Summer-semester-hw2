import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.repositories.database import Base, get_db
from app.judge.runner import normal_judge, special_judge
from app.repositories.tables import AuditLog, JudgeLog, Problem, Submission, User
from app.repositories.problems import a_plus_b_problem, a_plus_b_problem_SPJ
from app.services.auth import password_hash

from app.utils.common import model_dict


@pytest.fixture()
def tmp_path() -> Iterator[Path]:
    path = Path("temp") / f"pytest-{uuid4().hex}"
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture()
def db_session_factory(tmp_path: Path, monkeypatch) -> Iterator[sessionmaker[Session]]:
    db_path = tmp_path / "test.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
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

    monkeypatch.setattr("app.services.submission.SessionLocal", factory)
    monkeypatch.setattr("app.routers.backup.DB_PATH", db_path)
    monkeypatch.setattr("app.routers.backup.BACKUP_DIR", backup_dir)
    monkeypatch.setattr("app.routers.backup.engine", engine)

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

@pytest.fixture()
def problem_data_spj() -> dict:
    return model_dict(a_plus_b_problem_SPJ)

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


@pytest.mark.parametrize(
    "credentials",
    [
        {"username": "ab", "password": "student123"},
        {"username": "valid_name", "password": "short"},
    ],
)
def test_registration_validates_username_and_password(client: TestClient, credentials: dict):
    response = client.post("/api/auth/register", json=credentials)

    assert response.status_code == 422
    assert response.json()["code"] == 422
    assert response.json()["data"] is None


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


def test_problem_duplicate_and_not_found_responses(client: TestClient, problem_data: dict):
    login(client, "teacher", "teacher123")
    assert client.post("/api/problems", json=problem_data).status_code == 201

    assert client.post("/api/problems", json=problem_data).status_code == 409
    assert client.get("/api/problems/UNKNOWN").status_code == 404
    assert client.delete("/api/problems/UNKNOWN").status_code == 404

    renamed = {**problem_data, "id": "P1002"}
    assert client.put("/api/problems/P1001", json=renamed).status_code == 400


@pytest.mark.parametrize(
    "change",
    [
        {"id": "bad id"},
        {"title": ""},
        {"difficulty": "expert"},
        {"time_limit": 0},
        {"test_cases": []},
        {
            "test_cases": [
                {"case_id": "only", "input": "1 2\n", "output": "3\n", "score": 99, "is_hidden": False}
            ]
        },
        {
            "test_cases": [
                {"case_id": "same", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
                {"case_id": "same", "input": "2 3\n", "output": "5\n", "score": 50, "is_hidden": True},
            ]
        },
    ],
)
def test_problem_field_validation(client: TestClient, problem_data: dict, change: dict):
    login(client, "teacher", "teacher123")
    response = client.post("/api/problems", json={**problem_data, **change})

    assert response.status_code == 422
    assert response.json()["code"] == 422


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
    assert "spj" not in student_view.json()["data"]

    listing = client.get("/api/problems")
    assert listing.status_code == 200
    assert "test_cases" not in listing.json()["data"]["items"][0]
    assert "spj" not in listing.json()["data"]["items"][0]


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

    unsupported_language = student.post(
        "/api/submissions",
        json={"problem_id": "missing", "language": "cpp", "source_code": "int main(){}"},
    )
    oversized = student.post(
        "/api/submissions",
        json={"problem_id": "missing", "source_code": "x" * 65537},
    )
    assert unsupported_language.status_code == 422
    assert oversized.status_code == 422


def test_only_admin_can_list_users(client: TestClient, student: TestClient):
    forbidden = student.get("/api/users")
    assert forbidden.status_code == 403

    student.post("/api/auth/logout")
    login(client, "admin", "admin12345")
    response = client.get("/api/users?page=1&page_size=10")

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 3

    for item in response.json()["data"]["items"]:
        assert "password_hash" not in item


def test_admin_updates_user_and_disabled_user_loses_access(
    client: TestClient, student: TestClient, db_session_factory
):
    with db_session_factory() as db:
        student_id = db.scalar(select(User.id).where(User.username == "student"))

    student.post("/api/auth/logout")
    login(client, "teacher", "teacher123")
    assert client.put(
        f"/api/users/{student_id}", json={"role": "teacher", "is_active": True}
    ).status_code == 403

    client.post("/api/auth/logout")
    login(client, "admin", "admin12345")
    updated = client.put(
        f"/api/users/{student_id}", json={"role": "student", "is_active": False}
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["is_active"] is False
    assert "password_hash" not in updated.json()["data"]

    client.post("/api/auth/logout")
    disabled_login = client.post(
        "/api/auth/login", json={"username": "student", "password": "student123"}
    )
    assert disabled_login.status_code == 403

    with db_session_factory() as db:
        actions = set(db.scalars(select(AuditLog.action)).all())
    assert "DISABLE_USER" in actions


def test_admin_cannot_disable_self(client: TestClient, db_session_factory):
    login(client, "admin", "admin12345")
    with db_session_factory() as db:
        admin_id = db.scalar(select(User.id).where(User.username == "admin"))

    response = client.put(
        f"/api/users/{admin_id}", json={"role": "admin", "is_active": False}
    )
    assert response.status_code == 400


def test_student_cannot_view_another_students_submission(
    client: TestClient, problem_data: dict
):
    create_problem(client, problem_data)
    first = {"username": "student_a", "password": "student123"}
    second = {"username": "student_b", "password": "student123"}
    assert client.post("/api/auth/register", json=first).status_code == 201
    assert client.post("/api/auth/register", json=second).status_code == 201
    assert client.post("/api/auth/login", json=first).status_code == 200
    created = client.post(
        "/api/submissions",
        json={"problem_id": "P1001", "source_code": "print(3)"},
    )
    submission_id = created.json()["data"]["submission_id"]

    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json=second).status_code == 200
    assert client.get(f"/api/submissions/{submission_id}").status_code == 403
    assert client.get(f"/api/submissions/{submission_id}/logs").status_code == 403
    listing = client.get("/api/submissions", params={"user_id": "not-this-user"})
    assert listing.status_code == 200
    assert listing.json()["data"]["total"] == 0


def test_rejudge_checks_role_and_state_and_writes_audit(
    client: TestClient, problem_data: dict, db_session_factory
):
    create_problem(client, problem_data)
    credentials = {"username": "student_c", "password": "student123"}
    client.post("/api/auth/register", json=credentials)
    client.post("/api/auth/login", json=credentials)
    created = client.post(
        "/api/submissions",
        json={"problem_id": "P1001", "source_code": "print(3)"},
    )
    submission_id = created.json()["data"]["submission_id"]
    assert client.post(f"/api/submissions/{submission_id}/rejudge").status_code == 403

    client.post("/api/auth/logout")
    login(client, "teacher", "teacher123")
    assert client.post(f"/api/submissions/{submission_id}/rejudge").status_code == 409

    with db_session_factory() as db:
        submission = db.get(Submission, submission_id)
        submission.status = "finished"
        submission.result = "WA"
        submission.score = 50
        db.commit()

    rejudged = client.post(f"/api/submissions/{submission_id}/rejudge")
    assert rejudged.status_code == 202
    assert rejudged.json()["data"]["status"] == "pending"
    with db_session_factory() as db:
        submission = db.get(Submission, submission_id)
        assert submission.result is None
        assert submission.score == 0
        assert db.scalar(
            select(AuditLog).where(
                AuditLog.action == "REJUDGE_SUBMISSION",
                AuditLog.target_id == submission_id,
            )
        ) is not None

def test_spj_create_and_judge(
    client: TestClient, problem_data_spj: dict, tmp_path: Path
):
    login(client, "teacher", "teacher123")

    created = client.post("/api/problems", json=problem_data_spj)
    assert created.status_code == 201

    judge_temp = tmp_path / "judge"
    judge_temp.mkdir()
    judged = special_judge(
        "s=int(input())\nprint(1, s-1)\n",
        problem_data_spj["test_cases"],
        problem_data_spj["time_limit"],
        judge_temp,
        problem_data_spj["spj"],
    )

    assert judged["result"] == "AC"
    assert judged["score"] == 100
    assert [case["result"] for case in judged["cases"]] == ["AC", "AC"]
    assert list(judge_temp.iterdir()) == []


def test_normal_judge_accepts_multiple_cases_and_normalizes_output(tmp_path: Path):
    cases = [
        {"case_id": "visible", "input": "1 2\n", "output": "3\n", "score": 40, "is_hidden": False},
        {"case_id": "hidden", "input": "-1 2\n", "output": "1\r\n", "score": 60, "is_hidden": True},
    ]
    source = (
        "import sys\n"
        "a, b = map(int, input().split())\n"
        "sys.stdout.write(f'{a + b}   \\r\\n\\r\\n')\n"
    )

    judged = normal_judge(source, cases, 1.0, tmp_path, "standard")

    assert judged["result"] == "AC"
    assert judged["score"] == 100
    assert len(judged["cases"]) == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    ("source_code", "expected_result"),
    [
        ("print(0)\n", "WA"),
        ("print(1 / 0)\n", "RE"),
        ("import sys; sys.stdout.buffer.write(b'\\xff')\n", "RE"),
    ],
)
def test_normal_judge_classifies_wrong_and_runtime_outputs(
    tmp_path: Path, source_code: str, expected_result: str
):
    cases = [
        {"case_id": "case_01", "input": "1 2\n", "output": "3\n", "score": 100, "is_hidden": False}
    ]

    judged = normal_judge(source_code, cases, 1.0, tmp_path, "standard")

    assert judged["result"] == expected_result
    assert judged["score"] == 0
    assert judged["cases"][0]["result"] == expected_result


def test_normal_judge_times_out_and_cleans_temp_directory(tmp_path: Path):
    cases = [
        {"case_id": "case_01", "input": "", "output": "", "score": 100, "is_hidden": True}
    ]

    judged = normal_judge("while True:\n    pass\n", cases, 0.05, tmp_path, "standard")

    assert judged["result"] == "TLE"
    assert judged["cases"][0]["exit_code"] is None
    assert list(tmp_path.iterdir()) == []


def test_submission_logs_are_role_aware_and_teacher_view_is_audited(
    client: TestClient, problem_data: dict, db_session_factory
):
    create_problem(client, problem_data)
    credentials = {"username": "log_student", "password": "student123"}
    client.post("/api/auth/register", json=credentials)
    client.post("/api/auth/login", json=credentials)
    created = client.post(
        "/api/submissions",
        json={"problem_id": "P1001", "source_code": "print(0)"},
    )
    submission_id = created.json()["data"]["submission_id"]

    with db_session_factory() as db:
        db.add_all(
            [
                JudgeLog(
                    submission_id=submission_id,
                    case_id="visible",
                    result="WA",
                    score=0,
                    time_used=0.01,
                    exit_code=0,
                    input_data="1 2\n",
                    stdout="0\n",
                    stderr="Traceback (most recent call last):\n  File C:\\server\\temp\\main.py, line 1",
                    expected_output="3\n",
                    message="wrong answer",
                    is_hidden=False,
                ),
                JudgeLog(
                    submission_id=submission_id,
                    case_id="hidden",
                    result="WA",
                    score=0,
                    time_used=0.01,
                    exit_code=0,
                    input_data="secret input",
                    stdout="secret actual",
                    stderr="x" * 5000,
                    expected_output="secret answer",
                    message="hidden mismatch",
                    is_hidden=True,
                ),
            ]
        )
        db.commit()

    student_logs = client.get(f"/api/submissions/{submission_id}/logs")
    assert student_logs.status_code == 200
    visible, hidden = student_logs.json()["data"]["cases"]
    assert visible["stdout"] == "0\n"
    assert visible["expected_output"] == "3\n"
    assert "C:\\server" not in visible["stderr"]
    assert "File " not in visible["stderr"]
    for field in ("input_data", "stdout", "expected_output"):
        assert field not in hidden
    assert hidden["stderr"].endswith("...[truncated]")

    client.post("/api/auth/logout")
    login(client, "teacher", "teacher123")
    teacher_logs = client.get(f"/api/submissions/{submission_id}/logs")
    assert teacher_logs.status_code == 200
    assert teacher_logs.json()["data"]["cases"][1]["input_data"] == "secret input"
    assert teacher_logs.json()["data"]["cases"][1]["expected_output"] == "secret answer"

    with db_session_factory() as db:
        audit = db.scalar(
            select(AuditLog).where(
                AuditLog.action == "VIEW_FULL_JUDGE_LOG",
                AuditLog.target_id == submission_id,
            )
        )
    assert audit is not None


def test_teacher_can_filter_logs_but_student_cannot(
    client: TestClient, student: TestClient
):
    assert student.get("/api/logs").status_code == 403
    student.post("/api/auth/logout")
    login(client, "teacher", "teacher123")
    response = client.get("/api/logs", params={"page": 1, "page_size": 10, "result": "WA"})
    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "total": 0, "page": 1, "page_size": 10}


def test_sqlite_data_can_be_read_after_engine_reopen(
    client: TestClient, problem_data: dict, db_session_factory
):
    create_problem(client, problem_data)
    original_engine = db_session_factory.kw["bind"]
    database_url = str(original_engine.url)
    original_engine.dispose()
    reopened_engine = create_engine(database_url, connect_args={"check_same_thread": False})

    with Session(reopened_engine) as db:
        persisted = db.get(Problem, "P1001")
        assert persisted is not None
        assert persisted.title == problem_data["title"]
        assert len(persisted.test_cases) == 2
    reopened_engine.dispose()


def test_admin_creates_lists_and_restores_backup(
    client: TestClient, problem_data: dict, db_session_factory, tmp_path: Path
):
    create_problem(client, problem_data)
    assert client.post("/api/admin/backups").status_code == 401
    login(client, "admin", "admin12345")

    created = client.post("/api/admin/backups")
    assert created.status_code == 201
    backup_id = created.json()["data"]["backup_id"]
    backup_folder = tmp_path / "backups" / backup_id
    manifest = json.loads((backup_folder / "manifest.json").read_text(encoding="utf-8"))
    assert (backup_folder / "oj.db").is_file()
    assert manifest["storage"] == "sqlite"
    assert manifest["files"] == ["oj.db"]

    listed = client.get("/api/admin/backups")
    assert listed.status_code == 200
    assert listed.json()["data"][0]["id"] == backup_id

    assert client.delete("/api/problems/P1001").status_code == 200
    with db_session_factory() as db:
        assert db.get(Problem, "P1001") is None

    restored = client.post(f"/api/admin/backups/{backup_id}/restore")
    assert restored.status_code == 200
    with db_session_factory() as db:
        assert db.get(Problem, "P1001") is not None
    assert not (tmp_path / "test.rollback").exists()
    assert not (tmp_path / "test.restore").exists()


def test_restore_rolls_back_current_database_on_error(
    client: TestClient,
    problem_data: dict,
    db_session_factory,
    tmp_path: Path,
    monkeypatch,
):
    create_problem(client, problem_data)
    login(client, "admin", "admin12345")
    backup_id = client.post("/api/admin/backups").json()["data"]["backup_id"]
    assert client.delete("/api/problems/P1001").status_code == 200

    replacement = tmp_path / "test.restore"
    original_replace = Path.replace

    def replace_then_fail(self: Path, target: Path):
        result = original_replace(self, target)
        if self == replacement:
            raise OSError("simulated restore failure")
        return result

    monkeypatch.setattr(Path, "replace", replace_then_fail)

    with pytest.raises(OSError, match="simulated restore failure"):
        client.post(f"/api/admin/backups/{backup_id}/restore")

    with db_session_factory() as db:
        assert db.get(Problem, "P1001") is None
    assert not (tmp_path / "test.rollback").exists()
    assert not replacement.exists()


def test_incomplete_backup_fails_without_changing_current_data(
    client: TestClient, problem_data: dict, db_session_factory, tmp_path: Path
):
    create_problem(client, problem_data)
    broken = tmp_path / "backups" / "broken"
    broken.mkdir()
    (broken / "manifest.json").write_text("not json", encoding="utf-8")
    login(client, "admin", "admin12345")

    response = client.post("/api/admin/backups/broken/restore")

    assert response.status_code == 404
    with db_session_factory() as db:
        assert db.get(Problem, "P1001") is not None
