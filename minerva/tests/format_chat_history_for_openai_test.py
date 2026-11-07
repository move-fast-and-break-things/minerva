from minerva.format_chat_history_for_openai import format_chat_history_for_openai
from minerva.message_history import Message, MessageHistory, PdfContent


def test_formats_tool_responses_by_content_type():
  history = MessageHistory(prompt_str="prompt", token_limit=100_000)
  history.add(Message("TOOL-read_text_file", "text"))
  history.add(
    Message("TOOL-read_pdf_file", PdfContent("data:application/pdf;base64,", "a.pdf", 1, "pages"))
  )

  messages = format_chat_history_for_openai("prompt", history)

  assert messages[1:] == [
    {"role": "system", "content": "text", "name": "TOOL-read_text_file"},
    {
      "role": "user",
      "content": [
        {
          "type": "file",
          "file": {"filename": "a.pdf", "file_data": "data:application/pdf;base64,"},
        },
        {"type": "text", "text": "pages"},
      ],
      "name": "TOOL-read_pdf_file",
    },
  ]
