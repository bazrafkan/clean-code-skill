# Design patterns reference

The 23 patterns from Gamma, Helm, Johnson and Vlissides, *Design Patterns: Elements of Reusable Object-Oriented Software* (1994), adapted to modern languages.

Read a pattern's entry before introducing it, or when you meet it in existing code.

Entries use these fields, each where it applies:
- **Intent:** what the pattern is for.
- **Use when:** the situations where it applies.
- **Shape:** the parts and how they work together.
- **Gains / Costs:** the trade-offs the book lists.
- **Notes:** implementation advice.
- **Modern form:** the lighter way to get the same benefit today.
- **Don't use when:** overuse warnings.
- **Related:** patterns to compare with or combine.

Some fields are current practice rather than the book's text:
- "Modern form", "Pitfalls" and "Don't use when" are entirely current practice.
- "Notes" mix the book's implementation advice with current practice.
- Costs the book doesn't list are marked as such.

**When to use a pattern at all.** The book warns that a pattern buys flexibility by adding indirection, so apply it only when that flexibility is actually needed. This skill sharpens that to *needed now* (YAGNI). The exception is hard-to-reverse seams such as public APIs, data formats and vendor boundaries, which deserve some anticipation.

---

## Choosing between patterns

### Name the cause of the change

Adapted from GoF §1.6. Adapter and the lighter alternatives are additions.

| Cause of change or redesign | Consider |
|---|---|
| Code names a concrete class when it creates objects | Abstract Factory, Factory Method, Prototype, or a factory function or DI |
| Code hard-codes which operation satisfies a request | Command, Chain of Responsibility |
| Code depends on a platform or vendor | Abstract Factory, Bridge, plus an Adapter at the boundary |
| Clients know how an object is stored, located or represented | Bridge, Proxy, Memento, Abstract Factory |
| An algorithm is likely to change | Strategy, Template Method, Builder, Iterator, Visitor |
| Classes are tightly coupled | Facade, Mediator, Observer, Command, Chain of Responsibility, Bridge, Abstract Factory |
| Behavior is extended by subclassing | Decorator, Strategy, Composite, Bridge, Observer, Chain of Responsibility |
| A class can't be changed conveniently | Adapter, Decorator, Visitor |

### Break class explosions

A product of classes is the classic sign that one dimension should become an object passed in:

| Classes multiply as... | Use | Effect |
|---|---|---|
| features × features (BorderedScrollableX...) | Decorator | stack features at run time |
| requests × UI controls | Command | one request object, reused by every control |
| abstractions × platforms | Bridge | two hierarchies that grow separately |
| algorithms × data structure | Strategy | swap the algorithm without touching the structure |
| operations × node types, with node types stable | Visitor | one object per operation |

### Creational: subclass the creator, or pass a factory object
- **Factory Method subclasses the creator.** It adds just an operation, not new classes. The drawback is that you may need a subclass only to change the product, and the changes can cascade.
- **Abstract Factory, Builder and Prototype pass a factory object.** This is more flexible but more complex:
  - Abstract Factory makes several kinds of product.
  - Builder assembles one complex product through a protocol.
  - Prototype copies itself.
- **Designs typically start simple and evolve** toward the more flexible patterns where flexibility proves necessary. In modern code, "simple" usually means a constructor, a factory function, or injection.

### Structural: same shape, different intent
Most structural patterns are "a wrapper that holds a reference and forwards calls." Choose by intent, not by diagram:
- **Adapter vs Bridge.** An Adapter reconciles two existing interfaces after the fact. A Bridge is designed up front, so that an abstraction and its implementations can evolve independently.
- **Adapter vs Facade.** An Adapter reuses an old interface for one object. A Facade defines a new, simpler interface over many objects.
- **Composite vs Decorator.** A Composite represents a group as one thing. A Decorator adds responsibilities to one thing. They combine well behind a shared interface.
- **Decorator vs Proxy.** A Decorator adds behavior and composes recursively, so the total behavior is open-ended. A Proxy controls access to a subject that does the real work, and the relationship is fixed.

### Behavioral: how senders and receivers are decoupled
- **Command:** a request object binds sender to receiver. Use it when the request must be stored, queued, logged or undone.
- **Observer:** an open, run-time-variable set of listeners. Use it for data dependencies.
- **Mediator:** one object owns the interaction rules of a group. Use it when many-to-many rules need one readable home.
- **Chain of Responsibility:** the first capable handler in a sequence takes the request.
- **Mediator vs Observer.** Observer distributes communication. It is more reusable but harder to trace. Mediator centralizes it. It is easier to follow, but the mediator can grow into a monolith.
- **Strategy vs State vs Template Method.**
  - Strategy: the caller picks the whole algorithm.
  - State: the behavior changes on its own as internal state changes.
  - Template Method: inheritance varies some steps of a fixed skeleton.
- **Visitor vs methods on the classes.** Ask which changes more often. If operations are added often over stable types, use a Visitor or a pattern-matching function. If types are added often, use methods on the types.

### Patterns combine
Good designs usually contain several patterns, each solving a real problem:
- an Iterator walks a Composite while a Visitor acts at each node
- Commands are composed into macro commands (Composite), with Memento for undo
- a Builder assembles a Composite
- an Abstract Factory configures a Bridge

---

## Creational patterns

### Abstract Factory (also known as Kit)
- **Intent:** Create families of related objects through one interface, without naming their concrete classes.
- **Use when:**
  - The system must work with one of several product families.
  - A family's products must be used together and never mixed.
  - You want to expose only the interfaces of a product library.
- **Shape:**
  - A factory interface has one `createX()` method per product kind, with one concrete factory per family.
  - Clients see only the factory and the product interfaces.
  - Usually there is one factory instance, chosen in one place.
- **Gains:**
  - Concrete classes are isolated in one place.
  - Swapping a whole family is a single change.
  - Families can't be mixed by accident.
- **Costs:** Adding a new *kind* of product means changing the factory interface and every concrete factory.
- **Notes:**
  - Each create method is often a Factory Method.
  - Instead of one subclass per family, the factory can hold prototypes, or a registry from name to constructor, so a new family is only configuration.
  - A single `make(kind)` method is extensible but loses type safety. It is a selector argument, so keep it as the one allowed selection point (G23).
- **Modern form:**
  - A DI module or profile per family, or a record of constructor functions.
  - The composition root is the one place that picks the family.
- **Don't use when:**
  - There is only one family, or only one product type (use a function).
  - Product kinds change more often than families.
- **Related:**
  - Factory Method and Prototype are ways to implement it.
  - Singleton often holds the factory.
  - Builder differs: it assembles one complex product step by step, while Abstract Factory returns each product immediately.

### Builder
- **Intent:** Separate how a complex object is constructed from its representation, so the same construction process can produce different results.
- **Use when:**
  - The assembly algorithm should be independent of the parts and how they are represented.
  - The same steps must yield different representations. Example: one parser emitting HTML, an AST, or just statistics.
- **Shape:**
  - A director runs the steps and calls a builder interface (`addHeading`, `addParagraph`...).
  - Each concrete builder assembles its own product.
  - The client gets the result from the builder, not from the director.
- **Gains:**
  - A new representation is just a new builder.
  - Construction code is separated from representation code.
  - The product is built step by step and retrieved only when complete.
- **Costs (modern view; the book lists none):** It adds an extra protocol, and products from different builders often share no common interface.
- **Notes:**
  - Builder steps default to no-ops, so each concrete builder implements only what it needs.
  - Decide the assembly model: is appending enough, or do steps need parts built earlier?
  - A builder may produce no object at all, for example one that only counts.
- **Modern form:**
  - Event-driven or SAX-style parsers with pluggable sinks, query or request builders, test-data builders.
  - The "fluent builder" used to work around constructors with many parameters is a different, weaker use. Named or default arguments, records with copy-with, or an options object usually replace it.
  - When you do build: validate in `build()`, return an immutable product, and fail fast on missing parts.
- **Don't use when:**
  - It's a value object with a few fields.
  - The builder only mirrors setters and allows half-built objects.
  - There is one representation and one caller.
- **Related:**
  - Abstract Factory, which returns products one at a time.
  - Builders often build a Composite.

### Factory Method (also known as Virtual Constructor)
- **Intent:** Let subclasses decide which class a base class instantiates, through an overridable creation method.
- **Use when:**
  - A class can't anticipate which class of objects it must create.
  - A framework base class owns a workflow, and one step is "which concrete thing to make".
- **Shape:** The creator declares `createProduct()`, possibly with a default, and calls it from its own logic, often a Template Method. Subclasses override it.
- **Gains:**
  - Framework code depends only on the product interface.
  - Subclasses get a hook.
  - It connects parallel hierarchies: each figure creates its matching manipulator.
- **Costs:** Clients may have to subclass the creator just to change one product.
- **Notes:**
  - It comes in two variants: abstract, or with a default.
  - A parameterized `create(kind)` is possible. Keep it the single place that selects by kind (G23).
  - Never call an overridable factory method from the base constructor, because the subclass isn't ready yet. Create lazily instead.
  - A generic creator (`Creator<T>`) avoids subclassing.
  - Name factory methods consistently (`create...`).
- **Modern form:**
  - Pass a factory function or constructor reference (`() => T`, `Supplier<T>`), or inject the dependency.
  - Static named constructors (`fromPolar`, `ofSeconds`) are a different idiom: they name variants and don't defer the choice to subclasses.
- **Don't use when:**
  - The created class never varies.
  - The subclass exists only to `return new X()`.
- **Related:**
  - Abstract Factory is often built from factory methods.
  - Template Method usually calls them.
  - Prototype avoids subclassing the creator.

### Prototype
- **Intent:** Create new objects by copying a configured instance.
- **Use when:**
  - The classes to instantiate are known only at run time.
  - You want to avoid a factory hierarchy that mirrors the product hierarchy.
  - Instances differ only in a few combinations of state. Register preconfigured prototypes and clone them.
- **Shape:** Prototypes implement `clone()`. Clients hold prototypes, often in a registry keyed by name, and copy them.
- **Gains:**
  - Product kinds can be added and removed at run time.
  - "New kinds" can be defined by values, or by structure (clone a whole composite).
  - Fewer subclasses.
- **Costs:** Every class must implement `clone` correctly. That is hard for existing classes, for internals that can't be copied, and for cycles.
- **Notes:**
  - Shallow versus deep copy is the central decision. Decide what the clone and the original may share.
  - `clone` can't take varying parameters, so initialize the copy afterwards.
  - `clone` should return the concrete type, so callers never downcast.
- **Modern form:**
  - Copy-with on immutable records (`copy()`, `with`, `dataclasses.replace`, spread), `structuredClone`, Rust `Clone`.
  - Constructor references remove most of the original motivation.
  - Immutable prototypes make sharing trivial.
- **Pitfalls:**
  - Clones duplicating ids, timestamps, locks or connections.
  - Mutable prototypes edited after they were registered.
- **Don't use when:**
  - Building from configuration would be clearer.
  - Copies would silently share mutable nested state.
- **Related:**
  - Abstract Factory, as an alternative or combined with it.
  - Useful in designs heavy with Composite and Decorator.

### Singleton
- **Intent:** Guarantee a class has one instance, and a well-known way to reach it.
- **Use when:** There must be exactly one instance reachable from a known place. The book's examples are a print spooler and a window manager.
- **Shape:** A hidden constructor, plus a static accessor that creates the instance on first use.
- **Gains (as the book states them):**
  - Controlled access.
  - Fewer global names than global variables.
  - It can be subclassed and configured.
  - It is easy to allow N instances later.
  - It is more flexible than static methods.
- **Costs (modern consensus, not in the book):**
  - Hidden global state and hidden dependencies.
  - Tests that depend on their order.
  - Coupling.
  - Lazy initialization that is not thread-safe.
- **Modern form:**
  - Create one instance at the composition root and inject it. A DI container's "singleton scope" does the same.
  - A module-level instance, in languages where modules initialize once.
  - Language-level lazy statics (`OnceLock`, the holder idiom, `static let`), only for genuinely process-wide resources.
  - Keep "only one" a lifecycle decision, not a property of the class, so tests can make their own instance.
- **Legitimate uses:** hardware or OS handles, a read-only process-wide configuration or logger, the owner of a connection pool.
- **Don't use when:**
  - You only want convenient global access.
  - It holds mutable state touched from many places.
  - Tests need a `reset()`.
  - The real need is a constant, or one instance per request or tenant.
- **Related:** It often implements Abstract Factory, Facade and State objects.

---

## Structural patterns

### Adapter (also known as Wrapper)
- **Intent:** Make an existing class usable through the interface its clients expect, without changing it.
- **Use when:**
  - You are reusing a class whose interface doesn't match.
  - You are writing a reusable class that must cooperate with unforeseen classes.
  - You are adapting several subclasses through their common parent (object adapter).
- **Shape:**
  - The adapter implements the target interface, holds the adaptee and translates calls.
  - It may add what the adaptee lacks.
  - Prefer object adapters (composition). Class adapters (inheritance) are largely obsolete.
- **Gains:**
  - Reuse without modification.
  - One object adapter covers the adaptee and all its subclasses.
- **Costs:**
  - The adapter is not the adaptee, so it can't be passed where an adaptee is expected.
  - Overriding the adaptee's behavior is awkward.
- **Notes:** First find the narrowest interface you actually need. A tree view, for example, needs only "children of" and "render node", and those can simply be passed in as functions.
- **Modern form:**
  - Ports and adapters, or an anti-corruption layer around vendor SDKs.
  - Structural typing, traits and protocol extensions, extension functions.
  - A plain mapping function.
- **Don't use when:**
  - You own both sides. Change the interface instead.
  - It is a 1:1 pass-through "in case we switch libraries."
  - Adaptee types leak through its signatures.
  - It is accumulating business logic.
- **Related:**
  - Bridge (designed up front rather than added later).
  - Decorator (same interface, adds behavior).
  - Proxy (same interface, controls access).
  - Facade (a new, simpler interface over many objects).

### Bridge (also known as Handle/Body)
- **Intent:** Separate an abstraction from its implementation so the two can vary independently.
- **Use when:**
  - Both abstractions and implementations must be extensible.
  - The implementation is chosen or switched at run time.
  - N abstractions times M platforms would otherwise mean N×M subclasses.
  - Changes to the implementation shouldn't affect clients.
- **Shape:**
  - The abstraction holds a reference to an implementor interface and builds higher-level operations on its primitives.
  - The two hierarchies grow separately.
  - Their interfaces don't need to mirror each other.
- **Gains:**
  - The implementation is decoupled and swappable.
  - Clients have no compile-time dependency on implementations.
  - Each side extends independently.
  - Implementation details such as sharing or reference counting stay hidden.
- **Notes:**
  - Choose the implementor in one place: a constructor parameter, a default that can switch later, or an abstract factory.
  - Even with a single implementor, a Bridge still isolates clients from it.
- **Modern form:** A constructor-injected backend. Examples:
  - a database driver
  - a logging facade over a backend
  - storage or transport backends
  - renderers
  - notification channel × message type
- **Don't use when:**
  - Only one axis varies. A plain interface or a Strategy is enough.
  - The implementor interface merely mirrors the abstraction.
- **Related:**
  - Abstract Factory can create and configure it.
  - Adapter is the after-the-fact counterpart.

### Composite
- **Intent:** Compose objects into trees, and let clients treat single objects and groups the same way.
- **Use when:**
  - You are representing part–whole hierarchies.
  - Clients should ignore the difference between a single object and a composition.
- **Shape:**
  - A component interface.
  - Leaves.
  - Composites, which store children and implement operations by delegating to them, plus their own work.
- **Gains:**
  - Recursive structures.
  - Simple clients, with no type switching.
  - New component kinds don't change clients.
- **Costs:** It is overly general. It is hard to restrict what a composite may contain, and the type system won't help.
- **Notes:**
  - Keep parent references consistent by changing them only in add and remove.
  - Transparency versus safety:
    - Transparency means putting child operations on the component interface.
    - Safety means putting them only on composites.
    - If you choose transparency, a leaf's `add` should fail loudly, never silently.
  - Don't store the child list in the base type.
  - You can cache derived values such as bounds, but invalidate them up the tree.
- **Modern form:**
  - Sealed or union tree types (`Group(children) | Item`) with exhaustive matching. They restore the type safety the classic form lacks.
  - Typical uses: UI trees, ASTs, file trees, menus, rule trees.
  - For deep trees, traverse with generators or iteratively.
- **Don't use when:**
  - It's not really a tree (it has cycles).
  - Leaves and groups behave so differently that the shared interface is fiction, with many methods that throw.
  - There is only one level of grouping. A list is enough.
- **Related:**
  - Chain of Responsibility (the parent acts as successor).
  - Decorator.
  - Flyweight (shared leaves, which can't hold parent pointers).
  - Iterator and Visitor.

### Decorator (also known as Wrapper)
- **Intent:** Add responsibilities to an individual object dynamically, as an alternative to subclassing.
- **Use when:**
  - Responsibilities must be added or removed at run time without affecting other objects.
  - Combinations of features would explode the number of subclasses.
  - The class can't be subclassed.
- **Shape:** The decorator implements the component's interface, holds one component, forwards by default, and adds behavior before or after forwarding.
- **Gains:**
  - Pay-as-you-go features that can be mixed and matched at run time.
  - No feature-laden base classes.
- **Costs:**
  - A decorated object isn't identical to the original, so don't rely on identity.
  - Many small look-alike objects, which are hard to learn and debug.
- **Notes:**
  - Keep the component interface light: it defines an interface and holds no data.
  - Skip the abstract decorator class if you need only one decorator.
  - Decorator changes the "skin". Strategy changes the "guts". Prefer Strategy when the component is heavyweight.
- **Modern form:**
  - Function wrappers (in Python, keep metadata with `functools.wraps`).
  - HTTP middleware and interceptors.
  - I/O stream stacks.
  - Kotlin `by` and Go struct embedding remove the forwarding boilerplate.
- **Don't use when:**
  - There is one fixed combination.
  - The order of layers matters but isn't documented (is the retry outside the cache, or inside?).
  - Callers need decorator-specific methods.
  - Layers must share context. Use an explicit pipeline with a context object instead.
- **Related:**
  - Adapter (changes the interface).
  - Composite (a decorator is like a composite with one child).
  - Strategy and Proxy.

### Facade
- **Intent:** Provide one simpler, higher-level interface to a subsystem.
- **Use when:**
  - You want a simple default view of a complex subsystem.
  - You want to decouple clients from the subsystem's classes.
  - You are layering: each layer gets an entry point.
- **Shape:**
  - The facade delegates to subsystem classes, which don't know it exists.
  - Clients can still go beneath it when they need to.
- **Gains:**
  - Clients deal with fewer objects.
  - Coupling is weak.
  - Fewer compile or import dependencies, and easier porting.
- **Notes:**
  - Hide subsystem internals with module visibility.
  - A facade can be configured with different subsystem objects, but too many parameters defeat its purpose.
- **Modern form:**
  - SDK clients and application or service-layer entry points.
  - A package's public API (`internal/`, `pub(crate)`, barrel files).
  - An API gateway at service scale.
- **Don't use when:**
  - It is growing business logic of its own and becoming a god object.
  - It hides capabilities clients need, with no escape hatch.
  - It wraps something already simple.
  - It exposes subsystem types in its signatures.
- **Related:**
  - Abstract Factory.
  - Mediator differs: a mediator adds behavior and its colleagues know it, while a facade adds none and the subsystem is unaware of it.
  - Facades are often single instances; inject them.

### Flyweight
- **Intent:** Share fine-grained objects so huge numbers of them can be supported efficiently.
- **Use when all of these hold:**
  - There are very many objects.
  - The storage cost is high.
  - Most state can be made extrinsic, meaning supplied by the context.
  - Removing that state collapses many objects into few.
  - Identity doesn't matter.
- **Shape:**
  - Intrinsic state (shared, independent of context) lives in the flyweight.
  - Clients pass in the extrinsic state on each call.
  - A factory or pool hands out the shared instances.
- **Gains / Costs:** Memory is saved, at the run-time cost of computing or passing the extrinsic state.
- **Notes:**
  - Flyweights must be immutable.
  - Manage them through a lookup factory.
  - Reclaim them with weak references, or keep a small fixed set forever.
- **Modern form:**
  - Interning and value caches, shared enum or constant instances.
  - Sprite and glyph atlases.
  - Dictionary or columnar encoding of repeated values.
- **Don't use when:**
  - You haven't measured a memory problem. Flyweight then is premature optimization.
  - There are few objects.
  - The extrinsic state varies as much as the objects do.
- **Related:**
  - Composite (shared leaves).
  - State and Strategy objects often make good flyweights.

### Proxy (also known as Surrogate)
- **Intent:** A stand-in, with the same interface, that controls access to another object.
- **Kinds:**
  - **Remote:** a local representative of an object elsewhere.
  - **Virtual:** creates the expensive object on demand.
  - **Protection:** checks access rights.
  - **Smart reference:** extra work on access, such as reference counting, lazy loading, locking or copy-on-write.
- **Shape:** The proxy implements the subject's interface, holds a direct or indirect reference to it, and creates, guards or forwards as needed.
- **Gains:** It hides location, defers cost, and adds housekeeping transparently.
- **Pitfalls:**
  - Identity and equality differ from the real object.
  - A remote call looks local but has latency and failure modes. Don't hide that from callers.
  - Lazy ORM proxies cause N+1 queries and lazy-initialization errors.
  - Framework proxies are bypassed when an object calls its own methods.
  - Class-based proxies (subclass-generating frameworks) can't intercept final or private members.
- **Modern form:**
  - Lazy values (`lazy`, `cached_property`).
  - Generated RPC clients.
  - Smart pointers (`Rc`, `Arc`, `Cow`).
  - AOP dynamic proxies, JavaScript `Proxy`.
- **Don't use when:**
  - Plain lazy initialization inside the class is enough.
  - Security relies only on the wrapper being called. Enforce it in the subject too.
  - You are really adding behavior. That's a Decorator.
- **Related:**
  - Adapter (provides a different interface).
  - Decorator (adds responsibilities rather than controlling access).

---

## Behavioral patterns

### Chain of Responsibility
- **Intent:** Pass a request along a chain of potential handlers until one handles it, so the sender doesn't need to know the receiver.
- **Use when:**
  - Several objects could take a request, and which one does should be decided at run time rather than by the sender.
  - The set of handlers changes at run time.
- **Shape:** Each handler either handles the request or forwards it to its successor. The client sends to the first handler.
- **Gains:**
  - Reduced coupling.
  - Responsibilities can be reassigned by reconfiguring the chain.
- **Costs:** Nothing guarantees that anyone handles the request. It can pass through every handler unhandled.
- **Notes:**
  - Reuse existing links when they fit, such as parent pointers in a Composite.
  - Represent requests as typed objects, not codes.
- **Modern form:**
  - Middleware and interceptor pipelines (`(req, next) => ...`), event bubbling.
  - Decide and document the semantics: does the first handler consume the request, or may each stage act and then call `next`?
  - Add a terminal default handler or an explicit "unhandled" result, and log who handled each request.
- **Don't use when:**
  - The handler is known.
  - There are two or three fixed checks. Use early returns.
  - Routing is by key or type. Use a lookup table.
  - Handling must be guaranteed.
- **Related:** Composite, Command.

### Command (also known as Action, Transaction)
- **Intent:** Wrap a request in an object so it can be passed around, queued, logged and undone.
- **Use when you need to:**
  - parameterize objects by an action (the object-oriented callback)
  - execute requests later or elsewhere
  - support undo and redo
  - replay a log for recovery
  - build transactions from primitives
- **Shape:**
  - An invoker holds a command and calls `execute()`.
  - The command calls the receiver.
  - Undoable commands store what `undo()` needs.
  - A macro command is a Composite of commands.
- **Gains:**
  - The invoker is decoupled from the object that does the work.
  - Commands are first-class: they can be stored, composed and extended.
  - New commands don't change existing classes.
- **Notes:**
  - Store the undo state (receiver, arguments, old values) during `execute`.
  - A command that changed nothing shouldn't enter the history.
  - Copy a command before putting it in the history if its state varies.
  - Undo a macro's sub-commands in reverse order.
  - Repeated undo and redo can drift. Store enough state to prevent it, if needed with a Memento.
- **Modern form:**
  - A closure, for simple cases.
  - Command or action objects as data, for queues, event sourcing, Redux actions, job queues and up/down migrations.
  - For undo:
    - Keep two stacks, and clear the redo stack when a new command runs.
    - Cap the history and coalesce rapid edits.
    - Mark irreversible effects as not undoable.
- **Don't use when:**
  - A callback is enough.
  - Nothing needs queueing, undo or logging.
  - You'd create one class per method call that only forwards to it (command-bus ceremony).
- **Related:** Composite, Memento, Prototype, Chain of Responsibility.

### Interpreter
- **Intent:** Represent a simple language's grammar as a tree of objects, and evaluate sentences by walking that tree.
- **Use when:** The grammar is simple and efficiency isn't critical.
- **Shape:**
  - One class per grammar rule, split into terminal and nonterminal expressions.
  - `interpret(context)` recurses over the syntax tree.
- **Gains:**
  - The grammar is easy to change and extend.
  - New ways to interpret (printing, checking) are easy to add.
- **Costs:**
  - Complex grammars become unmaintainable, with one class per rule.
  - It is slow compared with translating to another form.
- **Notes:**
  - The pattern doesn't cover parsing.
  - Move many operations into a Visitor.
  - Share terminal nodes (Flyweight).
- **Modern form:**
  - A sealed AST with `eval` written as pattern matching.
  - Parser libraries and combinators, or an existing language or format (SQL, JSON logic, CEL, regex).
  - Predicate or specification combinators.
  - For speed, compile the tree to closures.
  - Sandbox any expression a user supplies.
- **Don't use when:**
  - A library or format already does the job.
  - It's really configuration or a rules table.
  - The grammar grows past about a dozen rules.
  - Nobody asked for a mini-language.
- **Related:** Composite, Flyweight, Iterator, Visitor.

### Iterator (also known as Cursor)
- **Intent:** Access the elements of an aggregate in sequence without exposing its representation.
- **Use when:**
  - Internals should stay hidden.
  - Several traversals must be in progress at the same time.
  - You want one traversal interface across different structures.
- **Shape:** The iterator keeps the position. The aggregate creates its iterator.
- **Gains:**
  - Traversal variants come from swapping iterators.
  - The aggregate's interface stays simpler.
  - Several traversals can be pending at once.
- **Notes:**
  - An external iterator is driven by the client. An internal iterator applies a function you pass in.
  - Decide how to stay robust when the aggregate changes during traversal.
  - Use a null iterator for leaves.
- **Modern form:**
  - Built into languages: iterator protocols, generators (`yield`), streams, LINQ, iterator adaptors.
  - Fail-fast or snapshot collections for robustness.
  - Pagination tokens and async iterators at service scale.
- **Don't use when:**
  - It would be a custom iterator class for a plain list.
  - A bulk or set operation fits better.
  - Watch for single-use iterators consumed twice, and for lazy I/O done per item.
- **Related:** Composite, Factory Method, Memento, Visitor.

### Mediator
- **Intent:** Put the interaction logic of a group of objects into one object, so they stop referring to each other directly.
- **Use when:**
  - A group of objects interacts in structured but tangled ways.
  - Reuse is blocked by many cross-references.
  - Behavior spread across classes should be customizable without subclassing.
- **Shape:** Colleagues know only the mediator and notify it. The mediator knows the colleagues and coordinates them.
- **Gains:**
  - Colleagues are decoupled.
  - Many-to-many becomes one-to-many.
  - Cooperation becomes an explicit concept.
  - Less subclassing.
- **Costs:** Centralization. The mediator can grow into a monolith.
- **Notes:**
  - Keep only coordination in the mediator, and domain logic in the colleagues.
  - Split mediators per workflow.
  - Dispatch on typed messages rather than `if sender == x` chains.
- **Modern form:**
  - A form controller, presenter or view-model.
  - A state store, or "lifting state up" to a parent.
  - A workflow orchestrator.
  - An event bus is a looser variant whose flow is harder to trace.
- **Don't use when:**
  - Two or three objects interact simply.
  - The mediator is turning into a god object.
  - A reactive or data-binding framework already expresses the dependencies.
- **Related:**
  - Facade (one-way, adds no behavior).
  - Observer (as the communication channel).

### Memento (also known as Token)
- **Intent:** Capture an object's internal state for later restoration without breaking its encapsulation.
- **Use when:** You need snapshots for undo or rollback, and exposing the state directly would leak implementation details.
- **Shape:**
  - The originator creates mementos and restores itself from them.
  - A caretaker stores them without looking inside.
  - The memento has a wide interface for the originator and a narrow one for everyone else.
- **Gains:**
  - Encapsulation is preserved.
  - The originator stays simpler.
- **Costs:**
  - It is expensive for large or frequent snapshots.
  - The caretaker can't see how big a memento is.
  - Separate narrow and wide interfaces are hard to express in some languages.
- **Notes:** Store only increments when snapshots are restored in a predictable order, as in a command history.
- **Modern form:**
  - Immutable values or persistent data structures, where the old value is the snapshot.
  - Serialization checkpoints, database savepoints, event sourcing with snapshots.
  - A `save()` that returns a restore closure.
- **Pitfalls:**
  - Shallow copies that alias mutable state.
  - Snapshotting external resources.
  - Unbounded history.
- **Don't use when:**
  - It's plain data with no encapsulation. Just copy it.
  - The state is already immutable.
  - A cheap exact inverse exists. Use Command undo.
- **Related:** Command, Iterator.

### Observer (also known as Dependents, Publish–Subscribe)
- **Intent:** When one object changes, notify an open set of dependents automatically, without coupling to them.
- **Use when:**
  - Two aspects of an abstraction must vary independently.
  - A change must reach an unknown number of objects.
  - The notifier mustn't know who listens.
- **Shape:** The subject keeps subscribers and notifies them. Observers update, often by reading state back from the subject.
- **Gains:**
  - Abstract, minimal coupling, which works even across layers.
  - Broadcast.
- **Costs:**
  - Unexpected cascades of updates, and spurious updates.
  - A bare "something changed" forces observers to work out what changed.
- **Notes:**
  - Make sure the subject is consistent before notifying: notify last.
  - Document which operations notify.
  - Choose push (send a payload) or pull (observers re-read).
  - Let observers subscribe to specific aspects.
  - Handle a subject that is deleted while observers still reference it.
- **Modern form:**
  - Events, signals, reactive streams.
  - Return an unsubscribe handle and tie it to a lifecycle.
  - Notify over a snapshot of the subscriber list.
  - Isolate one observer's errors from the others.
  - Decide sync or async delivery, and ordering.
  - Use typed event payloads.
- **Don't use when:**
  - There is exactly one known listener. Call it, or accept a callback.
  - Control flow would become invisible.
  - Order between observers matters. Use an explicit pipeline or a mediator.
  - You need a result back. Observer is fire-and-forget.
- **Related:** Mediator (a change manager is one), Singleton.

### State (also known as Objects for States)
- **Intent:** Let an object change its behavior when its internal state changes, by delegating to a state object.
- **Use when:**
  - Behavior depends on state and changes at run time.
  - Operations repeat large conditionals on the same state value.
- **Shape:** The context holds the current state object and delegates to it. Concrete states implement the behavior and usually choose the next state.
- **Gains:**
  - State-specific behavior lives in one place.
  - Transitions are explicit and atomic.
  - Stateless state objects can be shared.
- **Costs:**
  - More classes.
  - Transitions spread across files when each state picks its successor.
- **Notes:** Decide who owns the transitions: the context, the states, or a table. A transition table can be edited as data, but it makes actions less explicit.
- **Modern form:**
  - Sealed or union state types, each variant carrying only the data valid in that state, with exhaustive matching.
  - A `next(state, event) -> state` reducer, or statecharts.
  - Typestate, where invalid transitions don't compile.
  - Keep the transition graph visible in one place.
- **Don't use when:**
  - There are two or three states, or it's just a boolean.
  - States change only data, not behavior.
  - The state is chosen once and never changes. That's Strategy.
- **Related:** Flyweight, Singleton, Strategy.

### Strategy (also known as Policy)
- **Intent:** Make a family of algorithms interchangeable behind one interface, so the algorithm varies independently of the code that uses it.
- **Use when:**
  - Related classes differ only in behavior.
  - You need variants of an algorithm, such as time/space trade-offs.
  - An algorithm's data should stay hidden from clients.
  - A class picks its behavior through many conditionals.
- **Shape:** The context holds a strategy and delegates to it. Data is passed as parameters, or the strategy reads it from the context.
- **Gains:**
  - Families of algorithms.
  - An alternative to subclassing the context.
  - Fewer conditionals.
  - The choice can be made at run time.
- **Costs:**
  - Clients must understand the differences to choose a strategy.
  - One interface may pass data that some strategies ignore.
  - More objects. Make strategies stateless and shareable.
- **Notes:**
  - Design the interface so a new strategy doesn't change it.
  - Provide a default, so supplying a strategy is optional.
- **Modern form:**
  - Pass a function: `sort(items, key)`, `retry(op, backoff)`.
  - A registry of named functions selected by configuration.
  - Generics or traits for strategies chosen at compile time.
  - A small input struct instead of long parameter lists.
- **Don't use when:**
  - There is one implementation and none foreseen.
  - There are two or three closed, stable cases. A `match` is clearer.
  - The strategy needs the context's private data.
- **Related:**
  - Flyweight, State.
  - Template Method varies part of an algorithm through inheritance. Strategy varies the whole algorithm through delegation.

### Template Method
- **Intent:** Fix an algorithm's skeleton in a base operation, and let subclasses supply specific steps.
- **Use when:**
  - You want to implement the invariant parts once.
  - Subclasses duplicate behavior that can be factored out.
  - You want to control where extension is allowed (hooks).
- **Shape:**
  - The base class's template method calls two kinds of operations: primitive operations (abstract, must be overridden) and hooks (with a default, may be overridden).
  - This is the "don't call us, we'll call you" principle.
- **Gains:**
  - Reuse in frameworks.
  - It fixes "forgot to call super": the base does its own work and then calls the hook.
- **Notes:**
  - Make the template method itself non-overridable.
  - Keep the number of primitive operations small.
  - Document which operations are hooks and which are required.
- **Modern form:**
  - A higher-order function that takes the varying steps.
  - Setup/teardown invariants through `try/finally`, context managers, RAII, `using` or `withX(() => ...)`.
  - Trait or interface default methods.
  - Framework lifecycle hooks, where inheritance is the framework's choice.
- **Don't use when:**
  - Subclasses override most of the steps, or the order of steps varies.
  - The hierarchy is deep.
  - A callback parameter would do.
  - The algorithm must vary at run time.
- **Related:** Factory Method (often called from a template method), Strategy.

### Visitor
- **Intent:** Add new operations over a structure's element types without changing those types, by putting each operation in its own visitor object.
- **Use when:**
  - There are many element classes, and operations depend on the concrete class.
  - Many unrelated operations would pollute the element classes.
  - The element types rarely change but operations are added often.
- **Shape:**
  - The visitor has one `visitX` method per element type.
  - Each element's `accept(visitor)` calls its own `visitX(this)`. This is double dispatch.
  - Traversal is done by the structure, by an iterator, or by the visitor itself.
- **Gains:**
  - Adding an operation is easy.
  - Related operations are grouped together.
  - It works across unrelated classes.
  - State can be accumulated during traversal.
- **Costs:**
  - Adding an element type is hard, because every visitor changes.
  - Elements must expose enough state for visitors, which weakens encapsulation.
- **Notes:**
  - Keep traversal in the structure or a reusable walker. Put it in the visitor only when it depends on intermediate results.
  - Prefer visitors that return results (`Visitor<R>`) over mutable accumulators.
- **Modern form:**
  - Exhaustive pattern matching over a sealed type. Adding a variant makes the compiler flag every match, which makes the trade-off visible.
  - Keep classic accept/visit for open hierarchies, or for languages without sum types.
- **Don't use when:**
  - Element types change often.
  - There are only two or three element types, or only one operation. Put a method on the classes.
  - Every visitor repeats the same traversal.
- **Related:** Composite, Interpreter, Iterator.
