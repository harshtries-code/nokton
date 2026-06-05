import inspect
import typing


def func_to_json_schema(func) -> dict:
    sig = inspect.signature(func)
    doc = inspect.getdoc(func) or ""
    params = _parse_docstring_params(doc)

    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name == "self" or name == "cls":
            continue
        schema = _type_hint_to_json_schema(param.annotation) if param.annotation is not inspect.Parameter.empty else {"type": "string"}
        doc_desc = params.get(name, "")
        if doc_desc:
            schema["description"] = doc_desc
        properties[name] = schema
        if param.default is inspect.Parameter.empty:
            required.append(name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _type_hint_to_json_schema(annotation) -> dict:
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)

    if origin is list or origin is typing.List:
        item_schema = _type_hint_to_json_schema(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": item_schema}

    if origin is dict or origin is typing.Dict:
        return {"type": "object"}

    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return _type_hint_to_json_schema(non_none[0])
        return {"type": "string"}

    origin_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
    }
    json_type = origin_map.get(annotation, "string")
    return {"type": json_type}


def _parse_docstring_params(doc: str) -> dict[str, str]:
    params = {}
    lines = doc.split("\n")
    in_args = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Args:"):
            in_args = True
            continue
        if in_args:
            if stripped.startswith("Returns:") or stripped.startswith("Raises:"):
                break
            if ":" in stripped:
                parts = stripped.split(":", 1)
                param_name = parts[0].strip().split()[0] if parts[0].strip() else ""
                param_desc = parts[1].strip()
                if param_name:
                    params[param_name] = param_desc
    return params
