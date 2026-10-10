`report/report.py` has become hard to change. Add a Markdown output format (`"md"`), and leave the code easier to extend with further formats.

Constraints:
- `generate(path, fmt)` keeps its signature. `fmt` is `"text"`, `"html"` or `"md"`. An unknown format still raises an exception.
- `"text"` and `"html"` output must stay byte-for-byte identical to today's output, for every input.
- The Markdown output uses the same values and ordering as the other formats (rows sorted by name), in exactly this layout. Each line ends with `\n`, and there is one blank line between blocks:

```
# Sales report

## Totals by region

| Region | Revenue |
|---|---|
| East | 57.48 |
| North | 44.99 |
| South | 74.47 |

## Totals by product

| Product | Units | Revenue |
|---|---|---|
| Doohickey | 2 | 14.50 |
| Gadget | 6 | 119.94 |
| Widget | 17 | 42.50 |

**Top product:** Gadget

**Average order value:** 29.49
```

(This is the expected output for `samples/sales.csv`.)
