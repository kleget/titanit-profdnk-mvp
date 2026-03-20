from __future__ import annotations

import ast
from typing import Any


class FormulaError(ValueError):
    pass


_ALLOWED_BIN_OPS = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
}

_ALLOWED_UNARY_OPS = {
    ast.UAdd: lambda a: +a,
    ast.USub: lambda a: -a,
}

_ALLOWED_FUNCS = {
    "min": min,
    "max": max,
    "abs": abs,
    "round": round,
}


def _to_number(value: Any) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise FormulaError(f"Non-numeric value: {value}") from exc


def _eval_node(node: ast.AST, context: dict[str, float]) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body, context)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise FormulaError("Only numeric constants are allowed")
    if isinstance(node, ast.Name):
        if node.id not in context:
            raise FormulaError(f"Unknown variable: {node.id}")
        return _to_number(context[node.id])
    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_BIN_OPS:
            raise FormulaError(f"Operator not allowed: {op_type.__name__}")
        left = _eval_node(node.left, context)
        right = _eval_node(node.right, context)
        try:
            return _ALLOWED_BIN_OPS[op_type](left, right)
        except ZeroDivisionError as exc:
            raise FormulaError("Division by zero") from exc
    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _ALLOWED_UNARY_OPS:
            raise FormulaError(f"Operator not allowed: {op_type.__name__}")
        return _ALLOWED_UNARY_OPS[op_type](_eval_node(node.operand, context))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise FormulaError("Only direct function calls are allowed")
        fn_name = node.func.id
        if fn_name not in _ALLOWED_FUNCS:
            raise FormulaError(f"Function not allowed: {fn_name}")
        if node.keywords:
            raise FormulaError("Keyword arguments are not allowed")
        args = [_eval_node(arg, context) for arg in node.args]
        if fn_name == "round":
            if len(args) == 1:
                return _to_number(round(args[0]))
            if len(args) == 2:
                return _to_number(round(args[0], int(args[1])))
            raise FormulaError("round() accepts 1 or 2 arguments")
        return _to_number(_ALLOWED_FUNCS[fn_name](*args))
    raise FormulaError(f"Unsupported expression element: {type(node).__name__}")


def evaluate_formula(expression: str, context: dict[str, float]) -> float:
    trimmed = expression.strip()
    if not trimmed:
        raise FormulaError("Empty expression")
    if len(trimmed) > 300:
        raise FormulaError("Expression is too long")
    try:
        tree = ast.parse(trimmed, mode="eval")
    except SyntaxError as exc:
        raise FormulaError("Invalid expression syntax") from exc
    return _eval_node(tree, context)
