from minerva.tool_utils import GenericToolFn, ToolCall, format_tool, parse_tool_call


async def sum(a: int, b: int) -> str:
  """Sum two numbers."""
  return str(a + b)


async def do_x() -> str:
  """Does X."""
  return "done"


async def fetch(url: str) -> str:
  return "this is a mock function"


def test_format_tool():
  expected_sum = """Name: sum
Signature: (a: int, b: int) -> int
Description: Sum two numbers.
"""
  assert format_tool("sum", sum) == expected_sum

  expected_do_x = """Name: do_x
Signature: ()
Description: Does X.
"""
  assert format_tool("do_x", do_x) == expected_do_x

  expected_fetch = """Name: fetch
Signature: (url: str) -> str
Description: None
"""
  assert format_tool("fetch", fetch) == expected_fetch


def test_parse_tool_call():
  tools: dict[str, GenericToolFn] = {
    "sum": sum,
    "do_x": do_x,
  }

  toolCall = parse_tool_call("sum(1, 2)", tools)
  assert toolCall == ToolCall(tool_name="sum", args=[1, 2])

  toolCall = parse_tool_call("do_x()", tools)
  assert toolCall == ToolCall(tool_name="do_x", args=[])


def test_parse_tool_call_erros_if_tool_doesnt_exist():
  tools: dict[str, GenericToolFn] = {
    "sum": sum,
  }

  try:
    parse_tool_call("do_x()", tools)
    assert False
  except ValueError as e:
    assert str(e) == "Tool do_x not found."


def test_parse_tool_call_errors_if_number_of_args_doesnt_match_signature():
  tools: dict[str, GenericToolFn] = {
    "sum": sum,
  }

  try:
    parse_tool_call("sum(1)", tools)
    assert False
  except ValueError as e:
    assert str(e) == "The number of arguments does not match the tool's signature."


def test_parse_tool_call_supports_string_arguments_with_single_quote():
  tools: dict[str, GenericToolFn] = {
    "fetch": fetch,
  }

  toolCall = parse_tool_call("fetch('https://example.com')", tools)
  assert toolCall == ToolCall(tool_name="fetch", args=["https://example.com"])


def test_parse_tool_call_supports_string_arguments_with_double_quote():
  tools: dict[str, GenericToolFn] = {
    "fetch": fetch,
  }

  toolCall = parse_tool_call('fetch("https://example.com")', tools)
  assert toolCall == ToolCall(tool_name="fetch", args=["https://example.com"])


def test_parse_tool_call_supports_arguments_with_dashes():
  tools: dict[str, GenericToolFn] = {
    "fetch": fetch,
  }

  toolCall = parse_tool_call('fetch("https://github.com/move-fast-and-break-things")', tools)
  assert toolCall == ToolCall(
    tool_name="fetch", args=["https://github.com/move-fast-and-break-things"]
  )
