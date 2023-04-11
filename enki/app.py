import os
import discord
import openai
from dotenv import load_dotenv

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")
GUILD_ID = int(os.getenv("GUILD_ID"))

PROMPT = """You are Enki. As Enki, your purpose is to guide and mentor aspiring software and machine learning engineers to enhance their skills and knowledge. Your strength lies in your ability to break down intricate concepts and explain them in a clear and understandable manner. You are highly effective as a teacher, and your support is invaluable to those seeking to learn and develop in these fields.

You will politely decline to answer any question or fulfill any request unrelated to learning.

If it makes sense, instead of providing a solution, you will nudge the user to think about the problem and come up with a solution themselves. Apply the Socratic method of teaching."""


class MyClient(discord.Client):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

    async def on_guild_join(self, guild):
        if guild.id != GUILD_ID:
            await guild.leave()

    async def on_message(self, message):
        if message.author == self.user:
            return
        if message.channel.type.name not in ["text"]:
            return
        if self.user not in message.mentions:
            return

        response = await openai.ChatCompletion.acreate(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": PROMPT},
                {"role": "user", "content": message.content}
            ],
            temperature=0.6,
        )

        answer = response.choices[0].message.content
        for i in range(0, len(answer), 2000):
            await message.channel.send(answer[i:i+2000])


def main():
    intents = discord.Intents.default()
    intents.message_content = True

    client = MyClient(intents=intents)
    client.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
