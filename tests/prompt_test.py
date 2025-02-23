from minerva.prompt import ModelAction, ModelMessage, parse_model_message


def test_parse_model_message_parses_respond_action():
  model_message = f"""Action: {ModelAction.RESPOND}
I'm sorry, I'm having trouble understanding you right now.
"""

  parsed = parse_model_message(model_message)
  assert parsed == ModelMessage(
    ModelAction.RESPOND,
    "I'm sorry, I'm having trouble understanding you right now.",
  )


def test_parse_model_message_parses_use_tool_action():
  model_message = f"""Action: {ModelAction.USE_TOOL}
tool(arg1, arg2)
"""

  parsed = parse_model_message(model_message)
  assert parsed == ModelMessage(ModelAction.USE_TOOL, "tool(arg1, arg2)")


def test_parse_model_message_parses_respond_action_with_newlines():
  model_message = f"""Action: {ModelAction.RESPOND}
I'm sorry, I'm having trouble understanding you right now.
Could you please rephrase your question?
"""

  parsed = parse_model_message(model_message)
  assert parsed == ModelMessage(
    ModelAction.RESPOND,
    "I'm sorry, I'm having trouble understanding you right now.\nCould you please rephrase your question?",
  )


def test_parse_model_message_throws_value_error_when_action_is_invalid():
  model_message = """Action: invalid
I'm sorry, I'm having trouble understanding you right now.
"""

  try:
    parse_model_message(model_message)
    assert False
  except ValueError as err:
    assert str(err) == "'invalid' action is not supported, must be one of: tool, respond"


def test_parse_model_message_throws_value_error_when_action_is_missing():
  model_message = """I'm sorry, I'm having trouble understanding you right now.
"""

  try:
    parse_model_message(model_message)
    assert False
  except ValueError as err:
    assert str(err) == 'Action is missing, the message must start with "Action:"'


def test_parse_model_message_no_content():
  model_message = f"""Action: {ModelAction.RESPOND}"""

  parsed = parse_model_message(model_message)
  assert parsed == ModelMessage(ModelAction.RESPOND, "")
