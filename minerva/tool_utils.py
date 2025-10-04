from inspect import signature, Parameter, Signature
from typing import Any, Coroutine, NamedTuple, Callable, cast
import pyparsing as pp


TOOL_PREFIX = "TOOL-"

GenericToolFn = Callable[..., Coroutine[Any, Any, str]]


def get_tool_signature(tool: GenericToolFn) -> Signature:
  sig = signature(tool)
  filtered_params = [
    param for param in sig.parameters.values() if param.kind != Parameter.VAR_KEYWORD
  ]
  filtered_sig = sig.replace(parameters=filtered_params)
  return filtered_sig


def format_tool(name: str, tool: GenericToolFn) -> str:
  return f"""Name: {name}
Signature: {get_tool_signature(tool)}
Description: {tool.__doc__}
"""


class ToolCall(NamedTuple):
  tool_name: str
  args: list[Any]


def parse_tool_call(message: str, tools: dict[str, GenericToolFn]) -> ToolCall:
  """Parse a tool call message and return a ToolCall object.

  The tool call message format:
  tool_name(arg1, arg2, arg3, ...)

  Examples:
  sum(1, 2)
  do_x()
  fetch_html('https://example.com')

  Use pyparsing.
  Split arguments into a list.
  Check that the length of arguments matches th length of the arguments on the tool's signature.
  Convert arguments to the correct types according to the tool's signature.
  """

  # Support robust argument parsing including quoted strings (single/double),
  # escaped quotes with backslash, and multiline content inside quotes.
  quoted_single = cast(Any, pp.QuotedString("'", escChar="\\", multiline=True))
  quoted_double = cast(Any, pp.QuotedString('"', escChar="\\", multiline=True))
  simple_token = cast(Any, pp.Word(pp.alphanums + "._-:/"))

  arg_expr = quoted_single | quoted_double | simple_token

  tool_call = cast(
    Any,
    pp.Word(pp.alphanums + "_").setResultsName("tool_name")
    + pp.Suppress("(")
    + pp.Optional(pp.delimitedList(arg_expr, delim=","))
    + pp.Suppress(")"),
  )
  parsed = tool_call.parseString(message)
  tool_name = cast(str, parsed["tool_name"])
  args = cast(list[Any], parsed[1:])

  try:
    tool = tools[tool_name]
  except KeyError:
    raise ValueError(f"Tool {tool_name} not found.")

  tool_signature = get_tool_signature(tool)
  if len(args) != len(tool_signature.parameters):
    raise ValueError("The number of arguments does not match the tool's signature.")

  typed_args: list[Any] = []
  for arg, param in zip(args, tool_signature.parameters.values()):
    if param.annotation is str:
      if isinstance(arg, str):
        typed_args.append(arg)
      else:
        typed_args.append(str(arg))
    else:
      typed_args.append(param.annotation(arg))

  return ToolCall(tool_name=tool_name, args=typed_args)


def format_tool_username(tool_name: str) -> str:
  return f"{TOOL_PREFIX}{tool_name}"
