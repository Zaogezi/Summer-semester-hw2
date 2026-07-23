from app.repositories.database import SessionLocal
from app.repositories.problems import a_plus_b_problem, a_plus_b_problem_SPJ
from app.repositories.tables import Problem

problems = [a_plus_b_problem, a_plus_b_problem_SPJ]


def append_problems() -> None:
    with SessionLocal() as db:
        for problem in problems:
            if db.get(Problem, problem.id) is not None:
                print(f"[skip] 题目 {problem.id} 已存在")
                continue
            db.add(problem)
            print(f"[add]  题目 {problem.id} {problem.title}")
        db.commit()
    print("完成")


if __name__ == "__main__":
    append_problems()
