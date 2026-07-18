from repositories.tables import Problem

a_plus_b_problem = Problem(
    id="P1001", title="A+B Problem", description="输入两个整数 a 和 b，输出它们的和。",
    input_description="一行包含两个整数。", output_description="输出它们的和。",
    samples=[{"input": "1 2\n", "output": "3\n"}], constraints="|a|, |b| <= 10^9",
    time_limit=1.0, memory_limit=128, difficulty="easy", tags=["基础", "输入输出"],
    test_cases=[
        {"case_id": "case_01", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
        {"case_id": "case_02", "input": "-1 2\n", "output": "1\n", "score": 50, "is_hidden": True},
    ],
)