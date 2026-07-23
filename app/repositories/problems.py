from app.repositories.tables import Problem

a_plus_b_problem = Problem(
    id="P1001",
    title="A+B Problem", 
    description="输入两个整数 a 和 b，输出它们的和。",
    input_description="一行包含两个整数。", 
    output_description="输出它们的和。",
    samples=[{"input": "1 2\n", "output": "3\n"}], 
    constraints="|a|, |b| <= 10^9",
    time_limit=1.0, 
    memory_limit=128, 
    difficulty="easy", 
    tags=["基础", "输入输出"],
    test_cases=[
        {"case_id": "case_01", "input": "1 2\n", "output": "3\n", "score": 50, "is_hidden": False},
        {"case_id": "case_02", "input": "-1 2\n", "output": "1\n", "score": 50, "is_hidden": True},
    ],
    judge_mode="standard",
    spj=""
)


a_plus_b_problem_SPJ = Problem(
    id="P1002",
    title="A+B Problem (SPJ version)", 
    description="给定两个数的和，输出任意两个符合要求的整数",
    input_description="一个整数s", 
    output_description="空格分隔的两个整数，使它们的和为s",
    samples=[{"input": "3", "output": "1 2\n"}], 
    constraints="|s| <= 10^9",
    time_limit=1.0, 
    memory_limit=128, 
    difficulty="easy", 
    tags=["基础", "special judge"],
    test_cases=[
        {"case_id": "case_01", "input": "3\n", "output": "1 2\n", "score": 50, "is_hidden": False},
        {"case_id": "case_02", "input": "-3\n", "output": "-1 -2\n", "score": 50, "is_hidden": True},
    ],
    judge_mode="spj",
    spj=
'''
import sys
import json
def judge(input: str, expected_output: str, stdout: str, score: int) -> dict:
    WA = {
        "accepted": False,
        "score": 0,
        "message": "答案错误"
    }
    AC = {
        "accepted": True,
        "score": score,
        "message": "答案正确"
    }
    try:
        tup = tuple(map(int, stdout.split()))
        if len(tup) != 2:
            return WA
        elif tup[0] + tup[1] != int(input):
            return WA
        else:
            return AC
    except ValueError:
        return WA

if __name__ == "__main__":
    data = json.loads(sys.stdin.read())
    result = judge(data["input"], data["expected_output"], data["stdout"], data["score"])
    print(json.dumps(result, ensure_ascii=True))
'''
)

