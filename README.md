# Minerva

[[Blog]](https://mikhalevi.ch/minerva-a-gpt-powered-discord-bot-built-to-help-students-learn-software-development/) [[Demo on YouTube (of the old Discord version)]](https://www.youtube.com/watch?v=H9WEqr7ZgYk)

<div align="center">
  <img alt="Minerva is a GPT-powered Telegram bot built to help Move Fast and Break Things community members learn software development." src="minerva-telegram-banner-1280x640.png" width="900px" />
</div>

**Minerva** is a GPT-powered Telegram bot built to help community members learn software development.

## How can I add Minerva to my Telegram group (chat)?

By default, the bot uses the `gpt-5-2025-08-07` model from OpenAI, which costs
[$10.00 / 1M output tokens](https://platform.openai.com/docs/models/gpt-5). You can use
[this online tokenizer from OpenAI](https://platform.openai.com/tokenizer) to
estimate how many tokens it will take to encode your text.

You can switch to a different OpenAI model by defining the `OPENAI_MODEL` environment variable.
For example, `OPENAI_MODEL=gpt-5` will make Minerva use the latest GPT-5 model.

To run Minerva, you'll need to:
- [install poetry](https://python-poetry.org/docs/#installation)
- [create a Telegram bot](https://core.telegram.org/bots/tutorial#obtain-your-bot-token) and obtain the Telegram bot token
- [create an OpenAI account](https://platform.openai.com/) and get the OpenAI token
- [obtain the id of the Telegram group (chat)](https://stackoverflow.com/a/32572159/2027961) that you want to add the bot to

After you have done this:
1. Copy `.env.example` to `.env`.
2. Enter your Telegram bot token, OpenAI API key, and Telegram group (chat) id into `.env`. The bot will only function within this group.
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
