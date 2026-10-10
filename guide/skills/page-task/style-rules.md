# Built-in style rules

These rules apply when cc-prose is not installed (FR-003a). With cc-prose, the section's voice profile and the prose AI-pattern check replace the "Voices" part; the "Always" part still applies. The guide's own `styleguide.md` adds project terms and wins on conflicts.

## Always

- No em dash or en dash characters. Use commas, parentheses, or separate sentences.
- One idea per sentence. Most sentences stay under 25 words; split longer ones.
- Active voice with a clear actor: "The installer creates the namespace", not "The namespace is created".
- Address the reader as "you" in task pages; describe the system in the third person in concept pages.
- Name things exactly as the source does (file names, keys, targets, flags), in code formatting.
- Define a term at its first use on a page, or link to the page that defines it. A definition says what the thing does for the reader; it never explains a name with the same name or with the repository, recipe, or directory that contains it (`overview-contract.md` has the four tests).
- State facts plainly. Hedge only where the source is genuinely uncertain, and then say what is uncertain.
- No promotional or inflated wording. Banned: "seamless", "robust", "powerful", "cutting-edge", "game-changer", "leverage" (as a verb), "unlock", "empower", "delve", "landscape", "tapestry", "testament", "pivotal", "crucial role", "plays a key role", "in today's", "it's worth noting", "it is important to note", "simply", "just" (as in "just run"), "easily".
- No filler openers or closers: "In this section, we will", "Let's dive in", "In conclusion", "To sum up", "Happy hacking".
- No rule-of-three padding: list three items only when there are three.
- No rhetorical questions as headings or transitions.
- Numbers, ports, and versions come from the sources and the baseline values, never from memory.

## Voices

The section's `voice` in `guide.yaml` names one of these styles.

### concepts

Explains what something is and why it is built that way, for a reader deciding whether and how to use it.
- Lead with the purpose in one or two sentences, then the parts and how they interact. On the start page and section overview pages, follow the shape in `overview-contract.md`.
- Prefer a diagram reference over a long description of topology.
- Compare with what the reader already knows only when the comparison is exact.
- Short paragraphs (two to four sentences); no numbered steps.

### technical

Gets a reader through a task with a working result.
- A short paragraph on why the reader does the task, then numbered steps.
- One action per step, imperative mood: "Run", "Open", "Set".
- Every command is copy-paste ready, in a listing, with placeholders written as `<name>` and explained once.
- A step with an observable result ends with a `Check:` line and its expectation.
- Warnings come before the step they concern, never after.

### reference

Lets a reader look something up quickly.
- Tables and definition lists over prose; one row per item.
- Each entry: name, what it does, default, where it is defined (source location).
- No narrative, no examples longer than a few lines, no repeated explanations from concept pages (link to them).
