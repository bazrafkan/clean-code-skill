# Clean Code skill

An [Agent Skill](https://code.claude.com/docs/en/skills) that makes Claude write, refactor and review code following *Clean Code* and the Gang of Four *Design Patterns*, adapted to modern languages. It applies whenever Claude implements features, fixes bugs, refactors, designs or reviews code, in any language.

Where the books give Java- or C++-era specifics, the skill keeps the underlying principle:

- the project's conventions and the language's idioms come first
- error handling follows the language (exceptions, `Result`, error values)
- function size is a smell, not a quota
- no interface for every class
- the rule of three before extracting duplication
- the lightest form of a pattern the language allows, used only when the flexibility is needed now

## What's inside

```
clean-code/
├── SKILL.md                     # loaded when the skill triggers
└── references/
    └── design-patterns.md       # full catalog, read on demand
```

### `clean-code/SKILL.md`

- **Precedence rules.** When rules conflict, the order is tests and correctness, then the user's instructions and task scope, then project conventions, then the skill's rules.
- **Workflow:**
  1. Read the surrounding code.
  2. Make it work in small tested steps.
  3. Do a mandatory "make it right" pass.
  4. Apply a bounded Boy Scout Rule.
  5. Verify, without ever weakening tests.
- **Clean Code rules** for:
  - names, functions, comments and formatting
  - objects versus data structures
  - error handling, third-party boundaries, tests
  - classes and modules, systems, simple design and duplication
  - concurrency
- **Design patterns:**
  - the GoF principles: program to an interface, favor composition over inheritance, encapsulate what varies
  - when (and when not) to apply a pattern
  - a "causes of redesign" table and a quick chooser for all 23 patterns, each with its lighter modern form
  - pattern smells
- **A final self-review checklist** and a review mode for code reviews.
- **Cross-references** to *Clean Code*'s Chapter 17 heuristic codes (G5, N7, T4…).

### `clean-code/references/design-patterns.md`

One entry per GoF pattern, with:
- intent and when to use it
- its shape
- gains and costs
- implementation notes
- the modern form
- when not to use it
- related patterns

The file also covers how to choose between similar patterns (Adapter vs Bridge, Decorator vs Proxy, Strategy vs State, Mediator vs Observer…) and how to break up class explosions.

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

1. Zip the skill folder, including `references/`: `zip -r clean-code.zip clean-code`
2. In Claude, go to **Customize → Skills**, click **+**, then **Create skill → Upload a skill**, and upload the ZIP.

Code execution must be enabled. See [Use skills in Claude](https://support.claude.com/en/articles/12512180-use-skills-in-claude).

## Usage

Claude loads the skill on its own when a task involves writing, designing or changing code. In Claude Code you can also invoke it explicitly with `/clean-code`.

## Credits

The rules are paraphrased, with modern adaptations, from:

- Robert C. Martin, *Clean Code: A Handbook of Agile Software Craftsmanship* (Prentice Hall, 2008)
- Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software* (Addison-Wesley, 1994)

This project is not affiliated with or endorsed by the authors or publishers. No text from the books is included. Read the books for the full reasoning and examples.
