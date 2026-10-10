# Clean Code skill

An [Agent Skill](https://code.claude.com/docs/en/skills) that makes Claude apply Clean Code principles whenever it implements features, fixes bugs, refactors or reviews code, in any language.

The rules come from Robert C. Martin's *Clean Code* (2008), distilled into actionable instructions and adapted to modern practice. Where the book gives Java-era specifics, the skill keeps the underlying principle instead:

- the project's conventions and the language's idioms come first
- error handling follows the language (exceptions, `Result`, error values)
- function size is a smell, not a quota
- no interface for every class
- the rule of three before extracting duplication

## What's inside

[`clean-code/SKILL.md`](clean-code/SKILL.md) contains:

- **Precedence rules.** When rules conflict, the order is tests and correctness, then the user's instructions and task scope, then project conventions, then the skill's rules.
- **Workflow:**
  1. Read the surrounding code.
  2. Make it work in small tested steps.
  3. Do a mandatory "make it right" pass.
  4. Apply a bounded Boy Scout Rule.
  5. Verify, without ever weakening tests.
- **Rules** for:
  - names, functions, comments and formatting
  - objects versus data structures
  - error handling, third-party boundaries, tests
  - classes and modules, systems, simple design and duplication
  - concurrency
- **"Doesn't transfer literally".** A list of book advice that shouldn't be applied as written.
- **A final self-review checklist** and a review mode for code reviews.
- **Cross-references** to the book's Chapter 17 heuristic codes (G5, N7, T4…), so each rule can be traced back to the book.

## Install

### Claude Code

Personal (all your projects):

```bash
git clone https://github.com/bazrafkan/clean-code-skill.git
mkdir -p ~/.claude/skills
cp -r clean-code-skill/clean-code ~/.claude/skills/
```

Per project: copy the `clean-code` folder into `.claude/skills/` in your repository and commit it.

### Claude apps (claude.ai, desktop, mobile)

1. Zip the skill folder: `zip -r clean-code.zip clean-code`
2. In Claude, go to **Customize → Skills**, click **+**, then **Create skill → Upload a skill**, and upload the ZIP.

Code execution must be enabled. See [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

## Usage

Claude loads the skill on its own when a task involves writing or changing code. In Claude Code you can also invoke it explicitly with `/clean-code`.

## Credits

The rules are paraphrased from Robert C. Martin, *Clean Code: A Handbook of Agile Software Craftsmanship* (Prentice Hall, 2008), with modern adaptations. This project is not affiliated with or endorsed by the author or publisher. No text from the book is included. Read the book for the full reasoning and examples.
