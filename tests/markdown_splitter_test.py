from minerva.markdown_splitter import split_markdown


def test_markdown_splitter_doesnt_split_if_too_short():
  max_chunk_size = 10

  markdown = "test"
  expected = ["test"]
  assert list(split_markdown(markdown, max_chunk_size)) == expected

  markdown = "0123456789"
  expected = ["0123456789"]
  assert list(split_markdown(markdown, max_chunk_size)) == expected


def test_markdown_splitter_splits_at_chunk_size_if_no_space_or_newline():
  max_chunk_size = 10

  markdown = "0123456789a"
  expected = ["0123456789", "a"]
  assert list(split_markdown(markdown, max_chunk_size)) == expected

  markdown = "0123456789ab"
  expected = ["0123456789", "ab"]
  assert list(split_markdown(markdown, max_chunk_size)) == expected


def test_markdown_splitter_splits_at_space_if_chunk_size_exceeded():
  max_chunk_size = 5

  markdown = "test test"
  expected = ["test", "test"]
  assert list(split_markdown(markdown, max_chunk_size)) == expected


def test_markdown_splitter_splits_at_newline_if_chunk_size_exceeded():
  max_chunk_size = 5

  markdown = "test\ntest"
  expected = ["test", "test"]
  assert list(split_markdown(markdown, max_chunk_size)) == expected


def test_markdown_splitter_preserves_multiline_code_formatting():
  max_chunk_size = 100
  markdown = """Here is an example code snippet to define the Transformer architecture in PyTorch:

```
import torch.nn as nn

class Transformer(nn.Module):
    def init(self, input_size, output_size, num_layers, hidden_size, num_heads, dropout):
        super(Transformer, self).init()

        self.embedding = nn.Embedding(input_size, hidden_size)
        self.pos_encoding = PositionalEncoding(hidden_size, dropout)

        self.encoder_layers = nn.ModuleList([
            EncoderLayer(hidden_size, numheads, dropout) for  in range(num_layers)])
        self.decoder_layers = nn.ModuleList([
            DecoderLayer(hidden_size, numheads, dropout) for  in range(num_layers)])

        self.linear = nn.Linear(hidden_size, output_size)
```
  """
  expected = [
    # FIXME: avoid closing empty sequences
    # "Here is an example code snippet to define the Transformer architecture in PyTorch:\n\n```",
    "Here is an example code snippet to define the Transformer architecture in PyTorch:\n\n``````",  # noqa: E501
    "```import torch.nn as nn\n\nclass Transformer(nn.Module):```",
    "```    def init(self, input_size, output_size, num_layers, hidden_size, num_heads, dropout):\n        super(Transformer, self).init()\n```",  # noqa: E501
    "```        self.embedding = nn.Embedding(input_size, hidden_size)```",
    "```        self.pos_encoding = PositionalEncoding(hidden_size, dropout)\n\n        self.encoder_layers = nn.ModuleList([```",  # noqa: E501
    "```            EncoderLayer(hidden_size, numheads, dropout) for  in range(num_layers)])```",
    "```        self.decoder_layers = nn.ModuleList([```",
    "```            DecoderLayer(hidden_size, numheads, dropout) for  in range(num_layers)])\n\n        self.linear = nn.Linear(hidden_size, output_size)\n```\n  ",  # noqa: E501
  ]
  result = list(split_markdown(markdown, max_chunk_size))
  assert result == expected


def test_markdown_splitter_parses_text_with_multiple_code_blocks():
  max_chunk_size = 100
  markdown = """Here is how to print "Hello, world!" in Python:
```
print("Hello, world!")
```

Here is how to print "Hello, world!" in JavaScript:
```
console.log("Hello, world!");
```
"""

  expected = [
    'Here is how to print "Hello, world!" in Python:\n```\nprint("Hello, world!")\n```\n',
    'Here is how to print "Hello, world!" in JavaScript:\n```\nconsole.log("Hello, world!");\n```\n',  # noqa: E501
  ]
  result = list(split_markdown(markdown, max_chunk_size))
  assert result == expected
