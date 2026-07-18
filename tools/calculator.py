"""
Chhoti Don - Calculator
Advanced calculator with basic ops, scientific functions,
expression evaluation, unit conversion, and history.
Phase 2.2 - Full Upgrade
"""

import math
import re
from typing import Dict, List, Optional, Union


# ==================================================
# 🎯 OPERATOR & FUNCTION MAPS
# ==================================================

OPERATORS = {"+", "-", "*", "/", "//", "%", "**", "^"}

SAFE_FUNCTIONS = {
    "sqrt": math.sqrt, "cbrt": lambda x: x ** (1/3),
    "abs": abs, "ceil": math.ceil, "floor": math.floor,
    "round": round, "sin": math.sin, "cos": math.cos,
    "tan": math.tan, "asin": math.asin, "acos": math.acos,
    "atan": math.atan, "atan2": math.atan2,
    "log": math.log, "log2": math.log2, "log10": math.log10,
    "exp": math.exp, "pow": math.pow,
    "degrees": math.degrees, "radians": math.radians,
    "factorial": math.factorial, "gcd": math.gcd,
    "pi": math.pi, "e": math.e, "inf": math.inf,
    "min": min, "max": max, "sum": sum,
}

# Unit conversion factors (to base unit)
UNIT_CONVERSIONS = {
    # Length (base: meter)
    "km": 1000, "m": 1, "cm": 0.01, "mm": 0.001,
    "mile": 1609.344, "yard": 0.9144, "foot": 0.3048,
    "inch": 0.0254, "ft": 0.3048, "in": 0.0254,

    # Weight (base: kg)
    "kg": 1, "g": 0.001, "mg": 0.000001,
    "lb": 0.453592, "oz": 0.0283495, "ton": 1000,

    # Temperature handled separately

    # Speed (base: m/s)
    "mps": 1, "kph": 0.277778, "mph": 0.44704,
    "kmh": 0.277778,

    # Data (base: bytes)
    "b": 1, "kb": 1024, "mb": 1048576, "gb": 1073741824,
    "tb": 1099511627776,
}

# Calculation history
_history: List[Dict] = []


# ==================================================
# 🎯 MAIN FUNCTION (PRESERVED + UPGRADED)
# ==================================================

def run_calculator(data: Dict) -> Dict:
    """
    Original function — preserved + massively upgraded.
    Handles basic ops, expressions, scientific, and unit conversion.
    """
    if not isinstance(data, dict):
        return _error("Invalid input format. Expected dictionary.")

    # Route to appropriate calculator
    if "expression" in data:
        return evaluate_expression(data)
    elif "convert" in data:
        return convert_units(data)
    elif "function" in data:
        return calculate_function(data)
    else:
        return basic_calculate(data)


def basic_calculate(data: Dict) -> Dict:
    """
    Basic arithmetic — preserved.
    """
    a = data.get("a")
    b = data.get("b")
    operator = data.get("operator")

    if a is None or b is None or operator is None:
        return _error("Missing 'a', 'b', or 'operator' parameter.")

    try:
        a = float(a)
        b = float(b)
    except (ValueError, TypeError):
        return _error("Operands must be numbers.")

    try:
        if operator in ("+", "add"):
            result = a + b
        elif operator in ("-", "subtract"):
            result = a - b
        elif operator in ("*", "multiply", "x"):
            result = a * b
        elif operator in ("/", "divide"):
            if b == 0:
                return _error("Division by zero is not allowed.")
            result = a / b
        elif operator in ("//", "floor_divide"):
            if b == 0:
                return _error("Division by zero is not allowed.")
            result = a // b
        elif operator in ("%", "modulo", "mod"):
            if b == 0:
                return _error("Modulo by zero is not allowed.")
            result = a % b
        elif operator in ("**", "^", "power", "pow"):
            result = a ** b
        elif operator in ("sqrt",):
            result = math.sqrt(a)
        else:
            return _error(f"Invalid operator '{operator}'. "
                         f"Supported: +, -, *, /, //, %, **, sqrt")

        result = _round_result(result)
        _add_history(f"{a} {operator} {b}", result)

        return {
            "status": "success",
            "result": result,
            "expression": f"{a} {operator} {b}",
            "confidence": 1.0,
        }

    except Exception as e:
        return _error(str(e))


def evaluate_expression(data: Dict) -> Dict:
    """
    Safe mathematical expression evaluator.
    Example: {"expression": "sqrt(16) + 2**3"}
    """
    expr = data.get("expression", "").strip()

    if not expr:
        return _error("Empty expression.")

    # Safety check — only allow safe characters
    if not re.match(r"^[0-9\s\+\-\*\/\(\)\.\,\%\^a-zA-Z_]+$", expr):
        return _error("Expression contains unsafe characters.")

    # Block dangerous builtins
    dangerous = ["import", "exec", "eval", "open", "__", "os", "sys",
                 "subprocess", "compile", "globals", "locals"]
    for d in dangerous:
        if d in expr.lower():
            return _error(f"Expression contains forbidden keyword: {d}")

    try:
        # Replace ^ with ** for power
        expr_clean = expr.replace("^", "**")

        # Evaluate safely
        result = eval(expr_clean, {"__builtins__": {}}, SAFE_FUNCTIONS)
        result = _round_result(result)

        _add_history(expr, result)

        return {
            "status": "success",
            "result": result,
            "expression": expr,
            "confidence": 1.0,
        }

    except ZeroDivisionError:
        return _error("Division by zero in expression.")
    except Exception as e:
        return _error(f"Expression error: {str(e)}")


def calculate_function(data: Dict) -> Dict:
    """
    Scientific function calculation.
    Example: {"function": "sqrt", "value": 16}
    Example: {"function": "sin", "value": 90, "unit": "degrees"}
    """
    func_name = data.get("function", "").lower()
    value = data.get("value")
    unit = data.get("unit", "").lower()

    if func_name not in SAFE_FUNCTIONS:
        return _error(f"Unknown function '{func_name}'. "
                     f"Available: {list(SAFE_FUNCTIONS.keys())[:10]}")

    if value is None:
        return _error("Missing 'value' parameter.")

    try:
        value = float(value)
    except (ValueError, TypeError):
        return _error("Value must be a number.")

    try:
        # Degree → radian conversion for trig
        if func_name in ("sin", "cos", "tan") and unit == "degrees":
            value = math.radians(value)

        func = SAFE_FUNCTIONS[func_name]
        result = func(value)
        result = _round_result(result)

        _add_history(f"{func_name}({value})", result)

        return {
            "status": "success",
            "result": result,
            "function": func_name,
            "input": value,
            "confidence": 1.0,
        }

    except ValueError as e:
        return _error(f"Math error: {str(e)}")
    except Exception as e:
        return _error(str(e))


def convert_units(data: Dict) -> Dict:
    """
    Unit conversion.
    Example: {"convert": 100, "from": "km", "to": "miles"}
    """
    value = data.get("convert")
    from_unit = data.get("from", "").lower()
    to_unit = data.get("to", "").lower()

    if value is None:
        return _error("Missing 'convert' value.")

    try:
        value = float(value)
    except (ValueError, TypeError):
        return _error("Value must be a number.")

    # Temperature conversion (special case)
    if from_unit in ("c", "celsius", "f", "fahrenheit", "k", "kelvin"):
        result = _convert_temperature(value, from_unit, to_unit)
        if result is None:
            return _error(f"Cannot convert temperature from '{from_unit}' to '{to_unit}'")
        return {
            "status": "success",
            "result": _round_result(result),
            "from": f"{value} {from_unit}",
            "to": f"{_round_result(result)} {to_unit}",
            "confidence": 1.0,
        }

    # Standard conversion
    if from_unit not in UNIT_CONVERSIONS:
        return _error(f"Unknown unit '{from_unit}'.")
    if to_unit not in UNIT_CONVERSIONS:
        return _error(f"Unknown unit '{to_unit}'.")

    # Convert to base, then to target
    base_value = value * UNIT_CONVERSIONS[from_unit]
    result = base_value / UNIT_CONVERSIONS[to_unit]
    result = _round_result(result)

    _add_history(f"{value} {from_unit} → {to_unit}", result)

    return {
        "status": "success",
        "result": result,
        "from": f"{value} {from_unit}",
        "to": f"{result} {to_unit}",
        "confidence": 1.0,
    }


def _convert_temperature(value: float, from_unit: str, to_unit: str) -> Optional[float]:
    """Temperature conversion."""
    # Normalize unit names
    unit_map = {"c": "c", "celsius": "c", "f": "f", "fahrenheit": "f", "k": "k", "kelvin": "k"}
    f = unit_map.get(from_unit)
    t = unit_map.get(to_unit)

    if not f or not t or f == t:
        return value if f == t else None

    # Convert to Celsius first
    if f == "f":
        celsius = (value - 32) * 5/9
    elif f == "k":
        celsius = value - 273.15
    else:
        celsius = value

    # Then to target
    if t == "f":
        return celsius * 9/5 + 32
    elif t == "k":
        return celsius + 273.15
    return celsius


def get_history(last_n: int = 10) -> List[Dict]:
    """Calculation history lo."""
    return _history[-last_n:]


def clear_history() -> None:
    """History clear karo."""
    _history.clear()


# ==================================================
# 🔧 HELPERS
# ==================================================

def _error(message: str) -> Dict:
    """Standard error response."""
    return {"status": "error", "result": message, "confidence": 0.0}


def _round_result(result) -> Union[float, int]:
    """Result sensibly round karo."""
    if isinstance(result, float):
        if result.is_integer() and abs(result) < 1e15:
            return int(result)
        return round(result, 10)
    return result


def _add_history(expression: str, result) -> None:
    """History mein add karo."""
    _history.append({
        "expression": expression,
        "result": result,
        "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
    })
    if len(_history) > 100:
        _history.pop(0)
