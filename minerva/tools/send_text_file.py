async def send_text_file(filename: str, content: str) -> str:
	"""Send a text file with the given filename and content to the user.

	This tool triggers Minerva to send a document back to the user in the current
	chat/topic. The actual sending is handled by the chat session; this function
	returns a short confirmation for the model's internal tool response history.
	"""

	# The actual sending is performed by the chat session, which has access to the
	# Telegram Bot instance and thread context.
	return f"sent:{filename}:{len(content.encode('utf-8'))}"


