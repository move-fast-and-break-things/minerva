# Minerva

**Minerva** is a ChatGPT-powered Discord bot built to help students learn software development.

## How can I add Minerva to my Discord guild (server)?

The bot uses the `gpt-3.5-turbo` model, which costs [$0.002 per 1K tokens](https://openai.com/pricing) (or roughly 750 common English words). You can use [this online tokenizer from OpenAI](https://platform.openai.com/tokenizer) to estimate how many tokens it will take to encode your text.

To run Minerva, you'll need to:
- [install poetry](https://python-poetry.org/docs/#installation)
- [create a Discord bot account](https://python-poetry.org/docs/#installation) and obtain the Discord bot token
- [create an OpenAI account](https://platform.openai.com/) and get the OpenAI token
- [obtain the Discord guild (server) id](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID-) that you want to add the bot to

After you have done this:
1. Copy `.env.example` to `.env`.
2. Enter your Discord bot token, OpenAI API key, and Discord guild (server) id into `.env`. The bot will only function within this server.
3. In the terminal, navigate to the project dir and run:
```sh
poetry install
poetry run minerva
```

## Contributing

This repository follows the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) standard.

## License

MIT
