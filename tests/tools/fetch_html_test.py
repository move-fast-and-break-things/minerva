from minerva.tools.fetch_html import clean_html


def test_clean_html():
  html = """<html>
  <head>
    <title>Test</title>
    <script>alert('Hello, World!')</script>
    <style>body { background-color: red; }</style>
  </head>
  <body>
    <h1 class="test-class">Hello, World!</h1>
    <p>This is a test.</p>
  </body>
</html>"""
  expected_clean_html = """<title>Test</title><h1>Hello, World!</h1><p>This is a test.</p>"""
  assert clean_html(html) == expected_clean_html


def test_clean_html_doesnt_destroy_plaintext_files():
  text = """This is a plaintext file."""
  expected_clean_text = """This is a plaintext file."""
  assert clean_html(text) == expected_clean_text
