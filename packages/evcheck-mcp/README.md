# evcheck-mcp

The MCP server of [evcheck](https://github.com/llia0031-dotcom/evidence-check): an assistant can check every number and quotation in a draft against the user's own files (Markdown, text, Word, PDF, web pages, CSV and Excel), offline and without a model.

```bash
claude mcp add evcheck -- uvx evcheck-mcp
```

Tools: `check_draft` (a whole draft), `check_claim` (one sentence and the quotes chosen for it) and `find_quote` (where a passage appears word for word, or the closest lines). Sources can be given as paths or, when they are in the assistant's own sandbox, as text.

Documentation, evaluation and source: https://github.com/llia0031-dotcom/evidence-check

<!-- mcp-name: io.github.llia0031-dotcom/evcheck -->
