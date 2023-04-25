from collections import namedtuple
import os
from typing import Dict, List
import discord
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
GUILD_ID = int(os.getenv("GUILD_ID"))

AI_NAME = "Minerva"

PROMPT = f"""You are {AI_NAME}. As {AI_NAME}, your purpose is to guide and mentor aspiring software and machine learning engineers to enhance their skills and knowledge. Your strength lies in your ability to break down intricate concepts and explain them in a clear and understandable manner. You are highly effective as a teacher, and your support is invaluable to those seeking to learn and develop in these fields.

You will politely decline to answer any question or fulfill any request unrelated to learning.

You will always be respectful and kind to other members.

If it makes sense, instead of providing a solution, you will nudge the user to think about the problem and come up with a solution themselves.

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

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_guild_join(self, guild):
        if guild.id != GUILD_ID:
            await guild.leave()

    async def on_message(self, message: discord.Message):
        if message.author == self.user:
            return
        if message.channel.type.name not in ["text"]:
            return
        if self.user not in message.mentions:
            return

        if message.channel.id not in self.chat_histories:
            self.chat_histories[message.channel.id] = MessageHistory()
        chat_history = self.chat_histories[message.channel.id]
        chat_history.add(Message(message.author.id, message.content))

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

            for i in range(0, len(answer), 2000):
                await message.channel.send(answer[i:i+2000], reference=message)


def main():
    intents = discord.Intents.default()
    intents.message_content = True

    client = MyClient(intents=intents)
    client.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
