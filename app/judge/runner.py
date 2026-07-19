import subprocess
import sys
import tempfile
import time
from pathlib import Path

from app.utils.common import truncate


def normalized(value: str) -> str:
    value = value.replace("\r\n","\n").replace("\r","\n")
    lines = []
    for line in value.strip("\n"):
        lines.append(line.rstrip(" \t"))
    value = "\n".join(lines)
    value = value.rstrip("\n")
    return value


def judge(source_code: str, test_cases: list[dict], time_limit: float, temp_root: Path) -> dict:
    results = []
    with tempfile.TemporaryDirectory(dir=temp_root) as directory:
        source = Path(directory) / "main.py"
        source.write_text(source_code, encoding="utf-8")
        for case in test_cases:
            started = time.perf_counter()
            try:
                process = subprocess.run(
                    [sys.executable, str(source)],
                    input=case["input"].encode(),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=time_limit,
                    cwd=directory,
                )
                used = time.perf_counter() - started
                try:
                    stdout = process.stdout.decode("utf-8")
                    stderr = process.stderr.decode("utf-8")
                except UnicodeDecodeError:
                    result, stdout, stderr, message = "RE", "", "", "程序输出不是 UTF-8"
                else:
                    if process.returncode:
                        result, message = "RE", "程序运行错误"
                    elif normalized(stdout) != normalized(case["output"]):
                        result, message = "WA", "输出与标准答案不一致"
                    else:
                        result, message = "AC", "通过"
                exit_code = process.returncode
            except subprocess.TimeoutExpired as error:
                used = time.perf_counter() - started
                result, stdout, stderr = "TLE", "", ""
                message, exit_code = "运行超时", None
            results.append({
                "case_id": case["case_id"], 
                "result": result,
                "score": case["score"] if result == "AC" else 0,
                "time_used": round(used, 4), 
                "exit_code": exit_code,
                "input_data": truncate(case["input"]), 
                "stdout": truncate(stdout),
                "stderr": truncate(stderr), 
                "expected_output": truncate(case["output"]),
                "message": message, 
                "is_hidden": case["is_hidden"],
            })
            if result in {"RE", "TLE"}:
                break
    result_type = "AC"
    for name in ["TLE", "RE", "WA"]:
        if result_type != "AC": 
            break
        for item in results:
            if item["result"] == name: 
                result_type = name
                break
    return {"result": result_type, "score": sum(item["score"] for item in results), "total_time": round(sum(item["time_used"] for item in results), 4), "cases": results}
