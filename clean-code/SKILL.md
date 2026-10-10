---
name: clean-code
description: Use when implementing features, fixing bugs, refactoring, designing or reviewing code in any language. Applies Clean Code and GoF design patterns, adapted to modern practice, with a final self-review checklist.
---

# Clean Code and Design Patterns

Write code the next reader understands quickly and can change safely. The rules come from two books, adapted to modern languages:
- Robert C. Martin's *Clean Code* (2008). Codes like G5 or N7 point to its Chapter 17.
- The Gang of Four's *Design Patterns* (1994).

They are heuristics, not laws: if a rule would hurt readability in context, readability wins.

Two files in this skill's folder hold the details. Read them on demand:
- `references/clean-code-rules.md` has every rule below with its rationale, nuances and an example. Read it when applying a rule is unclear, or when reviewing.
- `references/design-patterns.md` covers all 23 GoF patterns. Read it before introducing a pattern or when choosing between similar ones.

**Review mode.** When asked to review rather than change code, report findings with their location and a fix, using the checklist. Don't edit unless asked.

## Precedence
1. Correct behavior, verified by tests.
2. The user's instructions and the scope of the task.
3. The project's conventions: formatter, linter, architecture, existing patterns, language idioms (G11, G24). Apply structural rules fully in new code. In existing code, go only as far as the codebase already goes.
4. The rules below. For design trade-offs, use Kent Beck's order: passes the tests, then no duplication, then expresses intent, then fewest elements.

## Workflow
1. **Before writing.**
   - Read the surrounding code and reuse its vocabulary and helpers.
   - Find the build, test and lint commands, ideally one command each (E1, E2).
   - Don't invent unclear requirements: ask, or do the clear part and flag the open question.
2. **Make it work.**
   - Take small steps, test first where practical.
   - New behavior ships with a test that would fail without it.
   - Keep the build green.
3. **Make it right (mandatory).** "It works" is not done.
   - Refactor in small, behavior-preserving steps until the code passes the checklist.
   - Use parallel change for structural moves. Never remove a public or persisted API without asking.
   - Know why the code is correct (G21).
4. **Stay in scope.**
   - Clean only what you touch: rename a local, extract a condition, delete dead code, fix a stale comment.
   - No unrelated refactors, mass reformatting or public renames. Report them instead.
   - If every new variant needs the same edit in many places, restructure first, within the task's footprint.
5. **Verify.**
   - Run the tests, linter, formatter and type checker. Report what you couldn't run.
   - Never weaken, skip or delete tests, or silence warnings, to get green (G4).

## Done checklist
- [ ] Names reveal intent, match the codebase's vocabulary, and show side effects and mutation.
- [ ] Each function does one thing at one level of abstraction.
- [ ] Functions have shallow nesting, few arguments, no flag or output arguments, and no hidden side effects.
- [ ] There is no duplicated knowledge and no repeated switch on the same type code. Magic values are named (G25).
- [ ] Code sits where a reader expects it: high cohesion, minimal public surface, vendor types at the edge, construction separate from use.
- [ ] Errors can't be silently ignored, carry context, and follow the language's idiom.
- [ ] There are no implicit nulls, and money is handled precisely.
- [ ] Comments say only why, warnings or contracts.
- [ ] There is no commented-out code, dead code, unused import, debug print or edit narration (G9, G12).
- [ ] Any pattern solves a present need, in the lightest form the language allows, and its role shows in names.
- [ ] New behavior, boundaries and fixed bugs are tested.
- [ ] Tests are fast, independent and deterministic, and the suite passes.
- [ ] The diff holds only the task plus small cleanups in touched code.

## Core rules

**Names (N1–N7).**
- Reveal intent, with units when the type lacks them (`timeoutMs`).
- No disinformation (an `accountList` that isn't a list), noise words (`Info`, `Data`) or encodings (`m_`, Hungarian notation). Language idioms win.
- Types are nouns, functions verbs, predicates `is`/`has`/`can`.
- One word per concept, no puns. Length grows with scope.
- Names state side effects (`getOrCreate…`) and whether a call mutates or returns a new value (`plusDays` vs `advanceByDays`) (G20).
- Avoid vague `Manager`/`Helper`/`Utils` unless the codebase already uses them.

**Functions (F1–F4, G15, G28–G34).**
- One thing, at one level of abstraction.
- Size is a smell, not a quota: be wary past about 20–30 lines or two levels of nesting, but don't shred coherent logic.
- Use guard clauses. Put the caller above the callee.
- Zero to two arguments is normal. Past three, use a parameter object. Don't move parameters into fields to cut arguments.
- No flag or selector arguments: split the function. No output arguments: return a value.
- Command–query separation. Least surprise (G2).
- Use explanatory variables (G19), named predicates (G28) and positive conditions (G29). Compute boundary math once (G33).
- Make temporal coupling explicit by passing each step's result to the next (G31).

**Comments (C1–C5).**
- Prefer expressing intent in code.
- Keep only: why, warnings, clarifications of external formats, references, legal headers, public-API contracts.
- Never write redundant or mandated comments, change logs, bylines, commented-out code, banners, edit narration (`// fixed bug`) or placeholders (`// ... rest unchanged`).
- TODOs state what and why.
- In lines you touch, update or delete comments the change made stale.

**Formatting.**
- Follow the project's formatter. Never mix unrelated reformatting into a change.
- Put high-level code first and keep related things close (G10).
- Keep files modest, and one language per file where practical (G1).

**Objects vs data.**
- Objects hide data and expose behavior (tell, don't ask).
- Data structures (records, DTOs) expose data, preferably immutable.
- Avoid hybrids, and don't add getters and setters by reflex.
- New types expected: use polymorphism. New operations over a closed set: use sealed types with an exhaustive match.
- Apply the Law of Demeter (G36) to objects, not to fluent APIs or plain data.
- A method that mostly uses another object's data belongs there (feature envy, G14).
- Keep business rules out of ORM models where the codebase separates layers.

**Errors.**
- Unignorable and off the happy path, in the language's idiom (exceptions, `Result`, error values). No error codes or sentinels.
- Give context and chain the cause. Keep secrets out of messages.
- Define error types by how callers handle them. Translate vendor errors at the boundary.
- No null for "nothing": return an empty collection or a Special Case, or make it explicit with `Option`/`T?`.
- Validate at trust boundaries. Never swallow errors.
- Be precise (G26): no floats for money, don't assume a query returns one result, handle concurrent updates.

**Boundaries.**
- Keep vendor and SDK types at the edge, behind a narrow domain interface. Do this in new code, or where the codebase already does.
- Learn unfamiliar APIs with small tests, and keep them as boundary tests.

**Tests (T1–T9).**
- Test code is production code: one concept per test, Arrange–Act–Assert, descriptive names.
- F.I.R.S.T.: fast, independent, repeatable (inject the clock, randomness and I/O), self-validating, timely.
- Test boundaries, the empty/one/many cases, and error paths. Reproduce each bug with a test first, then test around it.
- Coverage finds gaps; it isn't a target.
- Prefer fakes at real boundaries to mocking everything.

**Classes and modules.**
- One reason to change (SRP): describable in about 25 words without "and", "or", "if" or "but".
- High cohesion. Private by default (G8).
- Extend for new variants when change actually recurs (OCP), not speculatively.
- Inject abstractions at volatile seams (I/O, clock, vendors). No interface per class, no factory for everything.
- Keep each concept at the right level (G6). Base classes know nothing of their derivatives (G7).
- Statics and free functions only for stateless, non-polymorphic logic (G18). No hidden global state.
- Code goes where readers expect it (G17), without artificial coupling (G13). No arbitrary structure (G32). Prefer structure to convention (G27).
- ONE SWITCH rule (G23): never repeat the same non-exhaustive switch on a type code. Exhaustive matches over a sealed type are fine.

**Systems.**
- Wire dependencies in one place, the composition root.
- In new or layered code, keep domain logic free of infrastructure. Otherwise follow the framework's conventions.
- Grow the architecture incrementally. Think up front only about hard-to-reverse decisions: APIs, schemas, formats.
- Keep configuration at high levels (G35), and make logical dependencies explicit (G22).

**Duplication and simplicity.**
- Duplication means duplicated knowledge (G5).
- Rule of three: tolerate two copies and extract on the third, or immediately if they encode the same rule. A wrong abstraction costs more than duplication.
- YAGNI.

**Concurrency.**
- Keep concurrency separate from logic, and get the single-threaded logic right first.
- Minimize shared mutable state (immutability, confinement, messages). Use the platform's primitives.
- Check-then-act is a race, also across an `await`.
- Take locks in a global order, or with timeouts.
- Treat intermittent failures as real bugs.

## Design patterns (GoF)
- **Principles:**
  - Depend on abstractions where a seam is real (not an interface per class).
  - Favor composition over inheritance. Inherit for substitutability.
  - Encapsulate what varies.
  - Flexibility costs readability.
- **When to apply one:**
  - Start from a concrete problem, never from the wish to use a pattern.
  - Use it only when its flexibility is needed now, except at hard-to-reverse seams.
  - Check language features first.
  - Patterns make good refactoring targets.
  - Name participants by role (`PdfExportStrategy`).
- **Smells:**
  - an interface with one implementation and no second in sight
  - a factory for one product
  - a strategy that is never swapped
  - an observer chain nobody can trace
  - a Singleton used as global state
  - a Visitor over a hierarchy that keeps changing
  - a Builder for three fields

| Pattern | Use when | Lighter today |
|---|---|---|
| Abstract Factory | families of related objects are swapped together and never mixed | a DI module per family |
| Builder | one multi-step construction must produce several representations | named args, records with copy |
| Factory Method | a base workflow lets subclasses pick the product | pass a factory function |
| Prototype | kinds differ only in state, or classes are known only at run time | copy-with on immutable values |
| Singleton | exactly one instance is truly required | create once at the root and inject |
| Adapter | an existing class has the wrong interface | a mapping function |
| Bridge | abstraction and implementation vary independently | an injected backend interface |
| Composite | part–whole trees are handled uniformly | a sealed tree type plus recursion |
| Decorator | stackable behavior keeps the same interface | function wrappers, middleware |
| Facade | a complex subsystem needs a simple entry point | a module's public API |
| Flyweight | measured memory pressure from many similar objects | interning, caches |
| Proxy | access must be lazy, remote, checked or smart | lazy values, generated clients |
| Chain of Responsibility | the first capable handler in a changeable set takes the request | `(req, next)` middleware |
| Command | requests are queued, logged, undone or passed as data | closures, action objects |
| Interpreter | a small, simple grammar must be evaluated | a sealed AST plus match; a parser library |
| Iterator | a structure must be traversed without exposing it | language iterators, generators |
| Mediator | tangled many-to-many interactions need one owner | a controller, store or orchestrator |
| Memento | state must be snapshotted and restored without exposing internals | immutable state values |
| Observer | an unknown number of dependents react to changes | events, signals, streams (unsubscribable) |
| State | behavior depends on state and the same switch appears everywhere | a sealed state type plus `next(state, event)` |
| Strategy | interchangeable algorithms are chosen at run time | pass a function |
| Template Method | a fixed skeleton has a few varying steps | a higher-order function, `try/finally` |
| Visitor | many operations run over a stable set of node types | exhaustive pattern matching |

## Reporting back
When you finish, mention briefly:
- cleanups beyond the request
- trade-offs, such as rules you deliberately didn't apply
- patterns you introduced, and why
- checks you couldn't run
- smells outside the task's scope that you left alone
