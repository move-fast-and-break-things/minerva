from inspect import signature
from typing import NamedTuple
import pyparsing as pp


def format_tool(name: str, tool: callable) -> str:
  return f"""Name: {name}
Signature: {signature(tool)}
Description: {tool.__doc__}
"""


class ToolCall(NamedTuple):
  tool_name: str
  args: list[any]


def parse_tool_call(message: str, tools: dict[str, callable]) -> ToolCall:
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

  tool_call = (
      pp.Word(pp.alphanums + "_").setResultsName("tool_name") + pp.Suppress("(")
      + pp.Optional(pp.delimitedList(pp.Word(pp.alphanums + "_\"':/.-"), delim=","))
      + pp.Suppress(")")
  )
  parsed = tool_call.parseString(message)
  tool_name = parsed["tool_name"]
  args = parsed[1:]

  try:
    tool = tools[tool_name]
  except KeyError:
    raise ValueError(f"Tool {tool_name} not found.")

  tool_signature = signature(tool)
  if len(args) != len(tool_signature.parameters):
    raise ValueError("The number of arguments does not match the tool's signature.")

  typed_args = []
  for arg, param in zip(args, tool_signature.parameters.values()):
    if param.annotation is str:
      # strip quotes around the string
      typed_args.append(arg[1:-1])
    else:
      typed_args.append(param.annotation(arg))

  return ToolCall(tool_name=tool_name, args=typed_args)


def format_tool_username(tool_name: str) -> str:
  return f"TOOL-{tool_name}"
