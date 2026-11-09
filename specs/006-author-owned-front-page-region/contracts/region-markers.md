# Contract: Region markers

The file-format contract for guide-owned regions. Consumers: `region.py` (parser), `publish.py` (writer), `check.py` (validation), `embed.py` (front page status, move plan), `attrs.py` (generated regions), every skill that edits a front page or published README.

## Grammar

```text
file        := author_text? begin_marker guide_content end_marker author_text?
begin_marker:= "<!-- guide:region -->"     (on its own line)
end_marker  := "<!-- /guide:region -->"    (on its own line)
```

- Exactly one marker pair per file (FR-001). Zero pairs means the whole file is guide-owned, but only for files the guide already owns (the embedded front page, FR-002); a declared publish target with no markers is an error.
- Markers inside fenced code blocks (``` or ~~~) are literal text, not delimiters (FR-005).
- `guide_content` is ordinary guide page Markdown: sources block, generated `guide:attr` regions, headings, navigation. It must satisfy the front page contract on its own (FR-009).
- `author_text` is never written, verified, or reported by any guide command, except the whole-file link check (FR-008).

## Writes

The only legal mutation of a file with markers is `splice`: replace `guide_content` between the markers, leave every byte of `author_text` untouched. Writers that add markers (embedded create's `apply`, research R9) do so once, below retained author text, as part of an approved move plan.

## Errors

| Condition | Error |
|-----------|-------|
| begin without end, or end without begin | `region-unbalanced` (names file and marker line) |
| more than one pair | `region-duplicate` (names file and count) |
| publish target without markers | publish error, nothing written (spec story 1, scenario 5) |
| publish source page missing | check error naming the page |

Nothing is written when any of these hold (FR-004).
