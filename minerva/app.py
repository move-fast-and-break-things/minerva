from collections import namedtuple
import os
from typing import Dict, List
import discord
import openai
from dotenv import load_dotenv
from langchain.text_splitter import MarkdownTextSplitter

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
GUILD_ID = int(os.getenv("GUILD_ID"))
MAX_MESSAGE_LENGTH = 2000  # Discord message length limit

AI_NAME = "Minerva"

PROMPT = f"""You are {AI_NAME}. Your purpose is to guide and mentor aspiring software and machine learning engineers to enhance their skills and knowledge. You are good at breaking down intricate concepts and explaining them in a clear and understandable manner. You are highly effective as a teacher. You are friendly and respectful. When giving a response, you find the sources, base your response on them, and reference them. You will politely decline to answer any question or fulfill any request unrelated to learning.

If it makes sense, instead of providing a solution, nudge the user to think about the problem and come up with a solution themselves.

The conversation history will include multiple participants, and each message is structured as follows:
participant id: message content

Your user id is: {AI_NAME}

When you need to mention a participant, use the following format (include angle brackets): <@participant id>. Never mention yourself.

Use markdown to format quotes, code blocks, bold, italics, underline, and strikethrough text. Only these markdown rules are supported.

CONVERSATION HISTORY:
"""


Message = namedtuple("Message", ["author", "content"])


class MessageHistory:
    def __init__(self, message_limit=30, max_characters=3000):
        self.message_limit = message_limit
        self.max_characters = max_characters
        self.current_characters = 0
        self.history: List[Message] = []

    def add(self, message: Message):
        self.history.append(message)
        self.current_characters += len(message.content)
        while len(self.history) > self.message_limit or self.current_characters > self.max_characters:
            deleted_message = self.history.pop(0)
            self.current_characters -= len(deleted_message.content)

    def get(self):
        return self.history


def format_prompt(message_history: MessageHistory):
    prompt = PROMPT
    for message in message_history.get():
        prompt += f"\n{message.author}: {message.content}\n"
    prompt += "\nYour response:"
    return prompt


class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chat_histories: Dict[str, MessageHistory] = {}
        self.response_splitter = MarkdownTextSplitter(chunk_size=2000, chunk_overlap=0)

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_guild_join(self, guild):
        if guild.id != GUILD_ID:
            await guild.leave()

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            # Ignore messages from self
            return
        if message.channel.type.name not in ["text"]:
            # Ignore messages from non-text channels
            return
        # Add message to chat history
        if message.channel.id not in self.chat_histories:
            self.chat_histories[message.channel.id] = MessageHistory()
        chat_history = self.chat_histories[message.channel.id]
        chat_history.add(Message(message.author.id, message.content))
        # Don't respond if not mentioned explicitly
        if self.user not in message.mentions:
            return

        async with message.channel.typing():
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": format_prompt(chat_history)},
                ],
                temperature=0.6,
                max_tokens=2048,
            )

            answer = response.choices[0].message.content
            chat_history.add(Message(AI_NAME, answer))

            responses = self.response_splitter.create_documents([answer])
            for response in responses:
                await message.channel.send(response.page_content, reference=message)


def main():
    intents = discord.Intents.default()
    intents.message_content = True

    client = MyClient(intents=intents)
    client.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
