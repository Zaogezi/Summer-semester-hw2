import ast


spj_keys = {"accepted", "score", "message"}

def _param_count(func: ast.FunctionDef) -> int:
    args = func.args
    positional = args.posonlyargs + args.args
    if args.vararg is not None:
        return 4
    return len(positional)


def _returns_dict(func: ast.FunctionDef) -> bool:
    for node in ast.walk(func):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict):
            keys = {
                k.value
                for k in node.value.keys
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            }
            if keys and not spj_keys.issubset(keys):
                return False
    return True


def valid_spj(code: str) -> bool:
    if not code or not code.strip():
        return False
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return False

    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "judge"):
            continue
        if _param_count(node) < 4:
            return False
        if not _returns_dict(node):
            return False
        return True

    return False
