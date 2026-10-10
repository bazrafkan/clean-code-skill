---
name: clean-code
description: Use when implementing features, fixing bugs, refactoring, designing or reviewing code in any language. Applies Clean Code and GoF design patterns, adapted to modern practice, with a final self-review checklist.
---

# Clean Code and Design Patterns

The goal is code that the next reader understands quickly and can change safely. The skill draws on two books, both adapted to modern languages. Where a book gives Java- or C++-era specifics, the skill keeps the principle.

- **Robert C. Martin, *Clean Code* (2008).** Codes in parentheses (G5, N7, T4...) point to its Chapter 17 heuristics.
- **Gamma, Helm, Johnson and Vlissides, *Design Patterns* (1994), the "Gang of Four" (GoF).** It is summarized in "Design patterns" below. For the full entry on each of its 23 patterns, read `references/design-patterns.md` in this skill's folder, if present.

These are heuristics driven by values, not laws. If a rule would make a piece of code harder to read in its context, readability wins. Always know *why* you apply a rule.

**Review mode.** If you are asked to *review* code rather than change it, use the rules and the final checklist to report findings with location and a suggested fix. Don't apply edits unless asked.

## Precedence when rules conflict

1. **Correct behavior, verified by tests.**
2. **The user's explicit instructions and the scope of the task.**
3. **The project's own conventions.** This covers its formatter, linter, style guide, architecture, existing patterns and language idioms. Consistency with the codebase beats this skill (G11, G24). Apply the structural rules below fully in new modules, and in existing code only as far as the codebase already goes that way.
4. **The rules below.** For design trade-offs, use Kent Beck's simple design order (see "Simple design and duplication").

## Workflow

### 1. Before writing
- **Read the surrounding code.** Learn its naming lexicon, error-handling style, test layout, and how similar features are built. Reuse its vocabulary and helpers instead of inventing parallel ones.
- **Find the build, test and lint commands.** Each should be a single command (E1, E2).
- **Understand the requirement.** If a behavior is ambiguous, don't invent it. Ask, or implement the clear part and flag the open question. A pending or skipped test with a reason can document it (T4).

### 2. Make it work, in small verified steps
- **Test first where practical.** Write a failing test, make it pass with the simplest code, then refactor (red, green, refactor). At minimum, new behavior ships with a test that would fail without it.
- **Keep the system green between steps.** Never pile up many unverified changes.
- **A clumsy first draft is normal.** Nobody writes clean code in one pass. But a draft is not done.

### 3. Make it right (mandatory, not optional)
- **"It works" is not "done."** Before finishing, walk top to bottom through the code you wrote, using the checklist at the end.
- **Refactor in tiny, behavior-preserving steps** and run the tests after each one.
- **For structural moves, use parallel change.**
  - Add the new structure beside the old one.
  - Migrate callers one at a time.
  - Delete the old one once nothing uses it.
  - Never remove a public, exported or persisted API without asking.
- **Understand the algorithm (G21).** Passing the tests you thought of is not enough. Know why the code is correct, and refactor until that is obvious.

### 4. Scope discipline (a bounded Boy Scout Rule)
- **Leave the code you touch a little cleaner.** For example, in the function you are editing:
  - rename a misleading local
  - extract a tangled condition
  - delete dead code
  - fix a comment that has become wrong
- **Don't wander outside the task.**
  - Don't refactor unrelated files or mass-reformat.
  - Don't rename public, exported, serialized or string-referenced names as a side quest.
  - Wandering bloats the diff and hides the real change. Mention larger cleanup opportunities to the user instead.
- **Restructure before adding a variant when the same edit repeats.** If each new variant (type, case, option) needs the same edit in several places, restructure first so the next variant is one isolated addition. Do this only if the restructure stays within the task's footprint. Otherwise propose it.

### 5. Verify
- **Run the relevant checks.** That means the tests (including slower integration or acceptance tests when feasible here), linter, formatter and type checker. Report what you couldn't run.
- **Never override safeties to get green (G4).** Don't weaken, skip or delete tests, and don't silence warnings. If a test looks wrong, say so explicitly rather than editing it quietly.

## Rules

### Names (N1–N7)
- **Reveal intent.** A name says why the thing exists, what it does and how it is used. If it needs a comment, rename it.
  - Put units in the name when the type doesn't carry them: `timeoutMs`, `elapsedDays`, `priceCents`.
- **Avoid disinformation.**
  - Don't call something `accountList` unless it is a list. Use `accounts`.
  - Avoid names that differ only slightly, and avoid `l` and `O` as names.
- **Make meaningful distinctions.**
  - No number series (`data1`, `data2`). Use `source` and `target`.
  - No noise words that distinguish nothing (`Info`, `Data`, `Object`, `the`). Having `getAccount`, `getAccountInfo` and `getAccountData` side by side is a bug waiting to happen.
- **Use pronounceable, searchable names.** Name length grows with scope (N5): `i` in a three-line loop is fine, while module-level names must be descriptive and greppable.
- **Avoid encodings (N6).** No Hungarian notation, no `m_` or `f` prefixes, no project prefixes. Do follow language idioms, such as `IFoo` in C#, `_private` in Python, or `-er` interfaces in Go.
- **Parts of speech.**
  - Types are nouns: `Invoice`, `AddressParser`. Avoid vague names like `Manager`, `Processor`, `Helper` or `Utils` unless they are the codebase's established vocabulary.
  - Functions are verbs: `sendInvoice`, `parseHeader`.
  - Predicates start with `is`, `has`, `can` or `should`.
- **One word per concept, and no puns.**
  - Don't mix `fetch`, `get` and `retrieve` for the same idea.
  - Don't use one word for two meanings. If `add` means "sum", use `append` or `insert` for collections.
- **Draw names from the right domain.** Use solution-domain terms (`Queue`, `Visitor`, `Factory`, `Decorator`) for technical concepts (N3). Use the problem domain's ubiquitous language for business concepts.
- **Pitch names at the right level of abstraction (N2).** Prefer `connect(locator)` to `dial(phoneNumber)` when connections might not be phone calls.
- **Names describe side effects (N7).** Use `getOrCreateSession`, not a `getSession` that secretly creates one.
- **Function names say what they do (G20).** That includes whether they mutate or return a new value: `daysLater(5)` / `plusDays(5)` returns a new date, while `advanceByDays(5)` changes this one.
- **Add context through structure, not prefixes.** An `Address` type beats `addrStreet` and `addrCity`. Don't add gratuitous context such as an app-wide prefix on every class.
- **No cute or joke names.** Say what you mean.
- **Rename local and private names freely** when you find a better one, in the code you are changing. Use refactoring tools or search to catch every reference.

### Functions (F1–F4, G2, G15, G19, G28–G31, G33, G34)
- **Do one thing, at one level of abstraction (G30, G34).** Every statement sits one level below the function's name. A function does more than one thing when either is true:
  - you can extract a piece whose name isn't just a restatement of its code, or
  - it has sections (setup, compute, format) separated by blank lines or comments.
- **Treat size as a smell, not a quota.**
  - Be suspicious of functions past about 20–30 lines or with more than two levels of nesting.
  - Don't shatter a coherent linear algorithm into many one-line functions that make the reader jump around. Extract when the piece is a nameable concept.
  - Don't move parameters into instance fields just to cut argument count: that creates hidden mutable state.
- **Stepdown rule.** Put the caller above the callee where the language allows, so the file reads top-down like a story.
- **Keep nesting low.** Use guard clauses and early returns. The body of an `if`, `else` or loop is ideally short, often a single call to a well-named function.
- **Arguments: fewer is better (F1).**
  - Zero to two is normal, and three needs a reason.
  - Past three, introduce a parameter object or value type, or accept that the function does too much.
  - Named or keyword arguments ease the call site but not the coupling.
- **No flag or selector arguments (F3, G15).** Turn `render(true)` into `renderForSuite()` and `renderSingleTest()`. Enum or int selectors that switch behavior count too.
- **No output arguments (F2).** Return a value (a tuple, record or result type) or mutate the receiver, not a parameter.
- **No hidden side effects.** A function does what its name says and nothing more. Keep core logic pure where practical and push I/O and mutation to the edges.
- **Least surprise (G2).** Implement the behavior a caller would reasonably expect from the name. A day-name parser, for example, should accept "monday", "Monday" and common abbreviations.
- **Command–query separation.** A function either changes state or answers a question, not both. Idiomatic exceptions are fine: `pop()`, atomic `compareAndSet`, `putIfAbsent`.
- **Make temporal coupling explicit (G31).** When steps must run in order, have each step return what the next one needs (a "bucket brigade"), so the wrong order can't compile or run.
- **Use explanatory variables (G19).** Name intermediate values in calculations and regex groups: `key = match.group(1)`.
- **Encapsulate conditionals (G28).** Prefer `if shouldRetry(response)` to a raw compound boolean.
- **Prefer positive conditionals (G29).** Write `if isValid`, not `if not isInvalid`.
- **Encapsulate boundary conditions (G33).** Compute `nextLevel = level + 1` once instead of scattering `+1` and `-1` around.
- **Delete dead functions (F4).** Version control remembers them.
- **Multiple returns are fine** in small functions.

### Comments (C1–C5)
- **Express intent in code first.** Extract a function or variable whose name says what the comment would have said.
- **Good comments explain what code cannot:**
  - why: intent, rationale, trade-offs, non-obvious constraints
  - warnings of consequences: "not thread-safe", "O(n²), but n ≤ 50 by contract"
  - clarification of an external format, regex or API you can't change
  - amplification of something that looks trivial but matters
  - a reference that explains the why (a spec section, RFC or bug link)
  - legal or SPDX headers
  - docs for public APIs, covering the contract, units, errors and side effects
- **Never write these, and remove existing ones only in lines you are changing:**
  - redundant restatements (`i++  # increment i`) and docstrings that only repeat the signature
  - mandated boilerplate
  - change logs, bylines, and "added by" or "changed from X to Y" notes (C1). Version control holds history.
  - commented-out code (C5)
  - closing-brace comments, banners and position markers
  - nonlocal information and long history
  - HTML markup inside comments
  - misleading or obsolete comments (C2)
- **Agent-specific rules:**
  - Don't narrate your edit in comments (`// now uses the new helper`, `// fixed bug`). The diff and commit message carry that.
  - Don't leave placeholder comments such as `// ... rest unchanged`.
  - A TODO must state what and why, ideally with a ticket. Never use one to excuse leaving bad code.
- **Keep comments in sync.** When code changes, update or delete the comments that describe it.
- **Write comments well (C4).** Keep them brief and precise, with correct grammar, no rambling and nothing obvious.
- **"Comments are failures" is not a license** to delete valuable why, warning or reference comments.

### Formatting
- **Formatting follows the project's tooling.** Format your changes with the project's formatter and linter. Don't hand-format against them, and don't mix unrelated reformatting into your change.
- **Newspaper metaphor.** Put high-level concepts first and details below.
- **Keep related things vertically close (G10).**
  - Declare variables near their first use.
  - Put private helpers just below their first caller.
  - Keep functions that do similar things together.
- **Use blank lines to separate concepts.** Keep tightly related lines together.
- **Keep files modest.** The book's sample projects mostly kept files around 200 lines and rarely over 500. A big file usually means several responsibilities. For line length, follow the project's limit.
- **One language per file where possible (G1).** Move large embedded SQL, HTML or JSON into templates, resource files or builders.

### Objects and data structures
- **Decide which one you are building:**
  - An **object** hides its data and exposes behavior. Tell, don't ask: `order.ship()`, rather than reading its fields and deciding outside.
  - A **data structure** (DTO, record, dataclass, struct) exposes data and has no meaningful behavior. Prefer immutable ones.
  - Avoid **hybrids**: public data plus business behavior gives you the worst of both.
- **Don't add getters and setters for every field by reflex.** Expose abstractions such as `percentFuelRemaining()`, not the representation.
- **Choose by the expected axis of change:**
  - New types expected: use polymorphism.
  - New operations over a closed set of types expected: use data plus functions, for example a sealed type or tagged union with an exhaustive match in each operation.
- **Law of Demeter (G36).** Don't navigate `a.getB().getC().doThing()` through objects' internals. Ask the immediate collaborator to do it.
  - This doesn't apply to fluent, builder or stream APIs.
  - It doesn't apply to reading nested plain data either.
- **Feature envy (G14).** A method that uses another object's data more than its own probably belongs there. The exception is when moving it would couple that data to an unrelated concern, such as a report format.
- **Keep business rules out of persistence models.** ORM and Active Record models are data structures. Where the codebase separates layers, or the rules are more than trivial, put business rules in domain objects or services.

### Error handling
- **Errors must be impossible to ignore silently and must not swamp the happy path.** Use the language's idiom:
  - exceptions (Java, Python, C#, JavaScript/TypeScript)
  - `Result` with `?` (Rust)
  - error values (Go)
  - typed `throws` (Swift)
- **Keep error handling separate from logic.** A function that handles errors should do little else. Extract the body of a `try` into its own function.
- **No error codes or sentinel values** that callers must remember to check.
- **Give errors context.** Say which operation failed and with what input, chain the original cause, and keep secrets and PII out of messages.
- **Define error types by how callers will handle them,** not by where they came from. Translate third-party errors into your own types at the boundary.
- **Don't return null for "nothing":**
  - return an empty collection, or
  - return a Special Case or Null Object, or
  - make absence explicit in the type (`Optional`, `T?`, `Option`).
  - Don't pass null to functions that don't explicitly accept it.
- **Use the Special Case pattern for expected business variations** instead of using exceptions for control flow.
- **Validate at trust boundaries** (user input, I/O, public API) and trust the types inside.
- **Never swallow errors silently.** An intentionally empty catch block needs a comment saying why ignoring the error is correct.
- **Be precise (G26):**
  - No binary floats for money. Use integer minor units or a decimal or Money type.
  - Don't assume the first query match is the only one.
  - Handle possible concurrent updates.
  - Know how you handle each case your decision can produce.
- **Write the failure-path test first** for code that can fail.

### Boundaries (third-party code)
- **Keep vendor types at the edge.** Don't let HTTP clients, ORM entities, cloud SDK objects or generic `Map<string, any>` blobs spread through domain code.
  - In new code, or where the codebase already does this, wrap them behind a narrow interface in your domain language (adapter, ports and adapters).
  - Keep the number of places that touch a vendor API small.
  - Don't wrap stable standard-library types needlessly.
- **Explore an unfamiliar API with small learning tests** or a scratch script that use it the way you will. Keep the useful ones as boundary tests that catch behavior changes on upgrade.
- **When the real API doesn't exist yet,** code against the interface you wish you had, add the adapter later, and use a fake in tests.

### Tests (T1–T9)
- **Test code is production code.** It gets the same standards for names, clarity and duplication. Only runtime efficiency may be relaxed.
- **One concept per test.** Several asserts are fine when they verify one concept. Test names state the scenario and the expected outcome.
- **Structure each test as Arrange–Act–Assert** (or Given–When–Then). Hide incidental setup behind helpers, and let a small testing language emerge.
- **F.I.R.S.T.:**
  - **Fast** (T9).
  - **Independent:** tests run in any order.
  - **Repeatable:** no real network or clock. Inject time, randomness and I/O.
  - **Self-validating:** pass or fail, with no manual log reading.
  - **Timely:** written with or before the code.
- **Test everything that could break (T1).**
  - Cover boundaries (T5), the empty, one and many cases, and error paths.
  - Don't skip trivial tests (T3).
  - When you find a bug, first write a test that reproduces it, then test exhaustively around it (T6). Bugs cluster.
- **Use coverage to find gaps (T2), not as a target.** When debugging, read patterns of failing tests (T7) and of covered versus uncovered code (T8).
- **Prefer fakes at real boundaries over mocking every collaborator.** Test behavior, not implementation details. Over-mocked tests break on every refactor and defeat the purpose of having tests.

### Classes and modules
- **Small in responsibilities, not in lines (SRP).** A class or module has one reason to change. (Martin later clarified this as one actor or stakeholder.) Split it if:
  - you can't describe it in about 25 words without "if", "and", "or" or "but", or
  - it needs a vague name to cover everything.
- **High cohesion.** Methods should use most of the fields. When a subset of methods uses a subset of fields, another class is trying to get out.
- **Minimal public surface (G8).** Make things private by default and keep few methods, few fields and few exposed constants.
  - Test through the public API.
  - Needing to test a private method often means there is a class to extract.
- **Open/Closed, driven by real change.** When you keep reopening a class to add variants, restructure so new variants are added by extension: a new implementation, strategy, handler, or case in an exhaustive match. Don't do it speculatively.
- **Dependency inversion at volatile seams.** Depend on abstractions for I/O, network, clock, randomness and vendor services, and inject them through constructors or parameters.
  - Don't create an interface for every class that has a single implementation.
  - Don't add a factory for everything or many anemic wrapper classes. An abstraction earns its place at a real seam or a real variation.
- **Keep each concept at the right level (G6, G7).** Implementation-specific members don't belong in the general abstraction, and base classes know nothing about their derivatives.
- **Statics and free functions (G18).**
  - Stateless functions that will never need polymorphism are fine as static or module-level functions, where idiomatic.
  - If behavior will plausibly vary by type or implementation, make it a method on that type.
  - Avoid hidden mutable global or static state.
- **Put code where a reader would expect it (G17).** Don't couple artificially (G13): general-purpose enums and helpers don't live inside a specific class.
- **Don't be arbitrary (G32).** Have a reason for every structural choice, and make it visible in the structure, so others preserve it.
- **Prefer composition to inheritance for reuse.**
- **Structure over convention (G27).** Enforce rules with types (exhaustive enums or sealed types, abstract methods, interfaces) rather than naming conventions or comments.
- **Name magic values (G25, J3).** Replace magic numbers and strings with named constants or enums, and put behavior that depends on an enum value inside the enum. Self-evident literals (`0`, `1`, `* 2` in a formula, well-known constants) can stay.
- **ONE SWITCH rule (G23).** Never repeat the same non-exhaustive `switch` or `if` chain on a type code across the code.
  - Keep at most one such selection, ideally in a factory that creates polymorphic objects.
  - Compiler-checked exhaustive matches over a sealed type or enum, one per operation, are fine. Adding a variant makes the compiler flag every one of them.
  - For two or three stable cases, that is often clearer than a class hierarchy.

### Systems
- **Separate construction from use.** Wire dependencies in one place: the composition root, `main`, or a DI container. Business code receives its collaborators. It doesn't construct them or lazily initialize globals.
- **Keep the domain clean of infrastructure.** In new code, or where the codebase is already layered, keep domain logic in plain objects and functions. Put persistence, transactions, auth and caching at the edges, as middleware, decorators or adapters. In framework-centric codebases (Rails, Django, Spring...), follow the framework's conventions.
- **Grow the architecture incrementally.** Start with the simplest design that works and keep concerns well separated so it can evolve. Save up-front design effort for decisions that are hard to reverse: public APIs, schemas, data formats.
- **Keep configurable data at high levels (G35).** Defaults, limits and paths live near the entry point and are passed down, not buried in low-level functions.
- **Make logical dependencies physical (G22).** If module A relies on a fact about module B (such as B's page size), A should ask B for it explicitly rather than hard-coding the assumption.
- **Adopt a framework, standard or DSL only when it adds demonstrable value.**

### Simple design and duplication
Kent Beck's four rules, in priority order:
1. Passes all the tests.
2. Contains no duplication.
3. Expresses the programmer's intent.
4. Minimizes the number of classes and functions.

- **Duplication means duplicated knowledge (G5):** the same rule, fact or algorithm in more than one place. Watch for three forms:
  - Identical code: extract a function.
  - Similar algorithms: use a template method, a strategy, or a higher-order function.
  - The same selection repeated in several places: see the ONE SWITCH rule.
- **Rule of three.** Code that merely looks similar may change for different reasons. Tolerate two copies and extract on the third. Extract immediately when the copies encode the same rule. A wrong shared abstraction costs more than a little duplication.
- **YAGNI.** No speculative generality, unused parameters or ceremony "for the future."

### Concurrency (when the code is concurrent or async)
- **Separate and simplify.**
  - Keep concurrency code apart from business logic, with a thread-ignorant core and a thin thread-aware layer.
  - Make the single-threaded logic correct first.
- **Minimize shared mutable state.**
  - Prefer immutability, copies, confinement (one owner) and message passing.
  - Encapsulate what must be shared, and keep critical sections few and small.
  - Use the platform's concurrent collections, executors, atomics and async primitives, not hand-rolled locking.
- **Check-then-act is a race,** across threads and across an `await`.
  - Turn `if not cache.has(k): cache.set(k, v)` into one atomic operation: `computeIfAbsent`, a transaction, or a method on the shared object that locks internally.
  - `x++` is not atomic.
- **Avoid deadlock** by acquiring locks in a global order or using timeouts. Design bounded queues with backpressure, and plan shutdown and cancellation early.
- **Treat intermittent failures as real bugs.** Never dismiss one as a one-off.
  - Use race detectors and stress tests.
  - Use fake clocks and latches instead of `sleep` in tests.
- **Concurrency helps throughput only when work waits** (I/O-bound).

### Design patterns (GoF)
A design pattern is a named solution to a recurring design problem, with known consequences.
- The name gives you a shared vocabulary.
- The consequences are what you pay for that solution.

**Principles behind every pattern**
- **Program to an interface, not an implementation.**
  - Where an abstraction exists or a seam is real, depend on it rather than on the concrete class.
  - Otherwise, a class's public API is its interface. Don't add an interface for the sake of it.
- **Favor object composition over class inheritance.**
  - Inheritance is white-box reuse: fixed at compile time, coupled to the parent's internals.
  - Composition is black-box reuse: parts can be swapped through their interfaces.
  - Inherit for substitutability, preferably from abstract types, not merely to reuse code.
- **Encapsulate what varies.** Put the aspect that varies (or demonstrably will) behind its own interface, so it can change without redesign. Examples: an algorithm, a state, which class to create, a platform, a request.
- **Flexibility costs readability.**
  - Highly parameterized, dynamic designs are harder to understand than static code.
  - Use them only when they simplify more than they complicate, and in recognizable shapes.

**When and how to apply one**
- **Start from a concrete problem or smell, never from the wish to use a pattern.**
  - The book warns that patterns add indirection and should be applied only when their flexibility is actually needed.
  - This skill sharpens that to *needed now* (YAGNI), except at hard-to-reverse seams (see Systems).
  - Two or three stable cases rarely justify a pattern.
- **Read the pattern's applicability and consequences first.** Know what it lets vary and what it costs. The table below and `references/design-patterns.md` cover both. The reference also maps causes of redesign to patterns.
- **Check the language and the codebase's existing tools first.** Many patterns collapse to a lambda, a sealed type with `match`, a generator, an event, a wrapper or injection. See the chooser's last column.
- **Use patterns as refactoring targets.** When code degrades in a known way, refactor toward the pattern that removes that cause. Typical cases: a repeated switch, a class explosion, scattered `new ConcreteX()`.
- **Name participants in domain terms that keep the role visible** (N3): `PdfExportStrategy`, `RetryingClientDecorator`, `createParser()`. Use one naming convention per role.
- **Combine patterns freely when each solves a real need.** Good designs often contain several.

**Quick chooser.** Prefer the lighter form unless the full pattern's extra capability is needed.

| Pattern | Reach for it when | Often lighter today |
|---|---|---|
| Abstract Factory | whole families of related objects must be swapped together and never mixed | a DI module per family; a record of constructor functions |
| Builder | one multi-step construction must produce different representations, or it is order-dependent with validation at the end | named/default args, records with copy, an options object |
| Factory Method | a base class owns a workflow and subclasses choose the concrete product | pass a factory function; static named constructors |
| Prototype | new kinds differ only in state, or classes are known only at run time | copy-with on immutable values; constructor references |
| Singleton | exactly one instance must exist (a hardware or OS resource) | create once at the composition root and inject it |
| Adapter | an existing class has the wrong interface for its client | a mapping function; trait or extension conformance |
| Bridge | two dimensions vary independently (abstraction × implementation) | a constructor-injected backend interface |
| Composite | part–whole trees that clients handle uniformly | a sealed tree type plus recursive functions |
| Decorator | stackable, optional behavior around an object with the same interface | function wrappers, middleware |
| Facade | a simple entry point into a complex subsystem | a module's public API with the internals hidden |
| Flyweight | measured memory pressure from huge numbers of similar objects | interning, caches, dictionary encoding |
| Proxy | access control: lazy loading, remote, permissions, smart reference | lazy values, generated clients, smart pointers |
| Chain of Responsibility | the first capable handler in a changeable set should take a request | a `(req, next)` middleware pipeline |
| Command | requests must be queued, logged, undone or passed around as data | closures; action or message objects |
| Interpreter | evaluating a small, simple grammar | a sealed AST with pattern matching; a parser library |
| Iterator | traversing a structure without exposing it | the language's iterator protocol and generators |
| Mediator | many-to-many interactions in a group need one owner | a controller, view-model, store or orchestrator |
| Memento | snapshot and restore without exposing internals | immutable state values; serialization |
| Observer | an unknown number of dependents must react to a change | events, signals, streams (always unsubscribable) |
| State | behavior changes with state, and the same switch repeats across operations | a sealed state type plus a `next(state, event)` function |
| Strategy | interchangeable algorithms chosen by configuration or at run time | pass a function; a map of named functions |
| Template Method | a fixed skeleton with a few varying steps | a higher-order function; `try/finally` or context managers |
| Visitor | many operations over a stable set of node types | exhaustive pattern matching over a sealed type |

**Pattern smells**

Each of these means the pattern is solving no real problem; remove or simplify it:
- an interface with one implementation and no second in sight
- a factory that creates only one thing
- a strategy that is never swapped
- a decorator stack whose order nobody can explain
- an observer chain nobody can trace
- a Singleton used as convenient global state
- a Visitor over a hierarchy that keeps changing
- a Builder for a three-field value object

## Advice from the books that doesn't transfer literally

Follow the language and project instead of these Java- and C++-era specifics.

From *Clean Code* (CC):
- wildcard imports (J1)
- JavaBean `get`/`set` prefixes
- "always use unchecked exceptions"
- "no `I` prefix on interfaces"

From *Design Patterns* (GoF):
- class adapters built with multiple inheritance
- Singleton enforced by the class itself rather than by the composition root

From both books:
- class hierarchies as the default answer to switches

## Example (original, illustrative)

Before: a cryptic name, a flag argument, magic numbers, a float for money, and an output argument.

```python
def calc(o, f, out):
    t = 0.0
    for i in o.items:
        t += i.p * i.q
    if f:
        t = t * 0.9
    if t > 100:
        t -= 5
    out.append(t)
```

After: intention-revealing names, no flag, named constants, a decimal for money, a returned value, and one abstraction level per function.

```python
from decimal import Decimal

LOYALTY_DISCOUNT = Decimal("0.10")
REBATE_THRESHOLD = Decimal("100")
VOLUME_REBATE = Decimal("5")

def standard_total(order: Order) -> Decimal:
    return apply_volume_rebate(subtotal(order))

def loyalty_total(order: Order) -> Decimal:
    return apply_volume_rebate(subtotal(order) * (1 - LOYALTY_DISCOUNT))

def subtotal(order: Order) -> Decimal:
    return sum((item.unit_price * item.quantity for item in order.items), Decimal(0))

def apply_volume_rebate(amount: Decimal) -> Decimal:
    return amount - VOLUME_REBATE if amount > REBATE_THRESHOLD else amount
```

## Final self-review checklist

Run through this before saying the work is done. Fix what you find, or say why you left it.

**Names**
- [ ] Every name reveals intent at the right abstraction level, with no misleading names or encodings.
- [ ] Vocabulary is consistent with the codebase: one word per concept, no puns.
- [ ] Side effects and mutation show up in function names (N7, G20).

**Functions**
- [ ] Each function does one thing at one level of abstraction, does what its name promises, and has shallow nesting.
- [ ] There are few arguments, with no flag, selector or output arguments.
- [ ] There are no hidden side effects or hidden temporal couplings, and command–query separation is respected.
- [ ] Complex conditions and calculations use named predicates and explanatory variables, and boundary math is encapsulated.

**Structure**
- [ ] There is no duplicated knowledge and no repeated switch on the same type code.
- [ ] Code sits where a reader would look for it, with high cohesion and a minimal public surface.
- [ ] Vendor types stay at the edge. Construction is separated from use.
- [ ] Magic values are named. Configuration lives at a high level.
- [ ] Any design pattern solves a present need, uses the lightest form the language allows, and its role shows in the names.

**Errors**
- [ ] Errors can't be silently ignored, carry context, and use the language's idiom.
- [ ] No null is returned or passed without an explicit type. Nothing is swallowed. Money and numbers are handled precisely.

**Comments and hygiene**
- [ ] Comments explain only *why*, warnings or contracts. None are redundant, obsolete, change-log, placeholder or edit-narration comments.
- [ ] There is no commented-out code, dead code, unused variable or import, debug print or clutter in your changes (G9, G12).
- [ ] The style is consistent with similar code in the repo (G11). Formatter and linter are clean.

**Tests**
- [ ] New behavior and boundaries are tested, as is every bug fixed.
- [ ] Tests are readable, fast, independent and deterministic.
- [ ] The relevant suite passes, and no test was weakened or skipped to get there.

**Scope**
- [ ] The diff contains only the task plus small cleanups in touched code.
- [ ] Larger issues noticed elsewhere are reported to the user, not silently fixed.

## Reporting back

When you finish an implementation, briefly mention:
- any notable cleanups beyond the literal request
- the trade-offs you chose, such as where you deliberately didn't apply a rule
- any design pattern you introduced, and why
- any checks you couldn't run
- any smells you noticed outside the task's scope and left alone
