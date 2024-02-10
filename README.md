# Minerva

[[Blog]](https://mikhalevi.ch/minerva-a-gpt-powered-discord-bot-built-to-help-students-learn-software-development/) [[Demo on YouTube]](https://www.youtube.com/watch?v=H9WEqr7ZgYk)

<div align="center">
  <img alt="Minerva is a GPT-powered Discord bot built to help students learn software development." src="minerva-banner-1280x640.png" width="900px" />
</div>

**Minerva** is a GPT-powered Discord bot built to help students learn software development.

## How can I add Minerva to my Discord guild (server)?

<a href="https://www.youtube.com/watch?v=H9WEqr7ZgYk">
  <img alt="Minerva demo" src="minerva-demo.gif" width="900px" />
</a>

By default, the bot uses the `gpt-3.5-turbo-1106` model from OpenAI, which costs
[$0.002 per 1K tokens](https://openai.com/pricing) (or roughly 750 common English words).
You can use [this online tokenizer from OpenAI](https://platform.openai.com/tokenizer) to
estimate how many tokens it will take to encode your text.

You can switch to a different OpenAI model by defining the `OPENAI_MODEL` environment variable.
For example, `OPENAI_MODEL=gpt-4-1106-preview` will make Minerva use the latest GPT-4 model.

To run Minerva, you'll need to:
- [install poetry](https://python-poetry.org/docs/#installation)
- [create a Discord bot account](https://discordpy.readthedocs.io/en/stable/discord.html) and obtain the Discord bot token
- [create an OpenAI account](https://platform.openai.com/) and get the OpenAI token
- [obtain the id of the Discord guild (server)](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) that you want to add the bot to

After you have done this:
1. Copy `.env.example` to `.env`.
2. Enter your Discord bot token, OpenAI API key, and Discord guild (server) id into `.env`. The bot will only function within this server.
3. In the terminal, navigate to the project dir and run:
```sh
poetry install
poetry run minerva
```

### Using Docker

You can also run Minerva using docker. To run Minerva in docker, follow the instructions above, but skip `poetry` installation and, instead of the commands suggested in step 3, run:
```sh
docker compose up
```

## Contributing

This repository follows the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard.

## License

MIT
