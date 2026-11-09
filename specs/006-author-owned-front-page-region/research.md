# Research: Author-owned region on the generated front page

Phase 0 output. Each entry records the decision, the rationale, and the alternatives considered. Findings reference the spec's FR numbers and the code as it is on this branch.

## R1: Where does marker parsing live?

**Decision**: a new `guide/toolkit/region.py` module with no CLI: `parse(text) -> Region` (fence-aware), `splice(text, new_region) -> text`, and errors for unbalanced, duplicated, or fence-shadowed markers. `publish.py`, `check.py`, `embed.py`, and `attrs.py` import it.

**Rationale**: three consumers need identical semantics. `attrs.py` already shows the cost of copied regexes: `REGION_RE` is defined three times with slight drift (`attrs.py:79`, `check.py:86`, `fetch.py:218`). The toolkit rule (self-contained, imports only from its own directory) permits the import.

**Alternatives considered**: parsing inline in `publish.py` with others importing from it (couples the embedded front page to the publish CLI); a marker-free sentinel like a dedicated front-matter key (rejected: the spec fixes HTML comment markers, FR-001).

## R2: Marker spelling and the fence rule

**Decision**: `<!-- guide:region -->` opens, `<!-- /guide:region -->` closes (Clarifications). The parser masks fenced code blocks before scanning for markers, reusing the fence detection approach of `embed.py:_fence_mask` (lines 272-286), which already exists for section extraction.

**Rationale**: mirrors `<!-- guide:attr NAME -->` / `<!-- /guide:attr -->` exactly (`attrs.py:21`), so one convention family covers all generated content. Fence masking is required by FR-005 and has a tested precedent.

**Alternatives considered**: `guide:begin`/`guide:end` (brainstorm draft; less consistent with the attr pair); attribute-style `guide:region name=readme` (rejected: one unnamed region, FR-001).

## R3: The publish writer and link rebasing

**Decision**: new `guide/toolkit/publish.py` with `--write` and `--check` modes. It renders the source page by copying its text and rebasing relative links with `embed.rewrite_links` (line 335) exactly as `relink` (line 363) does for move-plan relocations: source-page-relative paths become target-README-relative paths. Absolute URLs and pure fragments pass through. The rendered page keeps its `// Sources:` block and generated `guide:attr` regions (they are guide-owned content, FR-009).

**Rationale**: aprofile's `sync-readme.py` proved this transform (inline and reference links, angle brackets, fenced code protection); `embed.rewrite_links` already implements it and is tested (`test_embed.py`).

**Alternatives considered**: invoking pandoc to render (unnecessary: gfm pages render on GitHub as they are, only paths change); publishing a site build artifact (couples the README to `make site`).

## R4: The publish declaration in guide.yaml

**Decision**: a `publish` block parsed by `guidecfg.py` into a `Publish` dataclass: `page` (relative to the guide root, must resolve inside the content root and exist) and `target` (relative to the guide root, must resolve outside the content root). Validation errors use the existing `ConfigError` with file/line context. Present only for the gfm adapter: the adapter descriptor lists `publish` support so other adapters reject it in `validate` (research R8).

**Rationale**: follows the `embedded` block pattern (`guidecfg.py:323-350`): tolerant raw read, resolved path helpers, never fails before guide.yaml is valid. One target in v1 (Clarifications) keeps the dataclass flat.

**Alternatives considered**: a list of targets (YAGNI, no second consumer); declaring the target in the page's front matter (gfm pages have no front matter contract).

## R5: Hand-edit detection narrows to the region

**Decision**: `fetch.normalized_front_page` (line 304) gains region awareness: when markers are present, the text compared and blob-recorded is the region content only (generated attr regions still emptied inside it); without markers, the whole file as today (FR-002). `embed.front_page_status` (line 910) and `fetch.store_front_page_blob` (line 309) use it unchanged. A recorded whole-file blob from an older guide stays valid only while the file has no markers; adding markers to an existing front page makes the first `evolve` report one edit (the author sees the region transition), which is acceptable and will be noted in the skill.

**Rationale**: the blob id is the comparison key; normalizing to the region makes author edits invisible to the comparison without touching the storage scheme (loose object plus baseline `front_page_blob`, lines 929-951).

**Alternatives considered**: recording two blobs (region and file; rejected: no consumer for the file blob); switching to a hash file inside the guide (changes the FR-014 fingerprint flow of spec 005 for no gain).

## R6: Checks and structure rules

**Decision**:
- `check.py` gains a `region` rule: for every file it already scans plus the publish target and the embedded front page, markers must be balanced, exactly one pair, and outside fences; violations name file and problem (FR-004, FR-005).
- `check_structure` (line 343) reads the front page's guide content through the region lens: with markers, section titles and persona links are read from the region only.
- The whole-file link check adds the publish target to its file set (the embedded front page is already in it, line 768-769), so author links into the guide must resolve (FR-008).
- The front-page ownership comment rule moves inside the region (FR-011): `front-page-contract.md` rule 1 changes to "the first line of the region is the ownership comment", and the comment text states that text between the markers is guide-owned and the rest belongs to the author.

**Rationale**: `check.py` already funnels every rule through `Violation(path, line, rule, message)` and already special-cases the embedded front page in three places (lines 101, 346-358, 768-769), so the region lens slots into existing plumbing.

**Alternatives considered**: a separate `region.py check` CLI (splits one check run into two commands the Makefile must wire); ignoring structure rules inside regions (would let the guide region lose the front page contract, FR-009).

## R7: attrs regions and author text

**Decision**: `attrs.regions` (line 99) applies `REGION_RE` substitution to guide-owned content only: when the front page has markers, the substitution runs on the region; author text is untouched even if it contains a `guide:attr` marker (which then also never raises the unknown-attribute error). `fetch.normalized_front_page` keeps emptying attr regions inside the region only.

**Rationale**: FR-003 forbids any command modifying author text; today's whole-file substitution would rewrite (or reject) an author's coincidental `guide:attr` comment.

**Alternatives considered**: erroring on author-text attr markers (a new failure mode for author text, violating FR-013).

## R8: Adapter scope and Makefile wiring

**Decision**: the gfm `adapter.yaml` documents the `publish` block and the marker convention; the gfm scaffold `Makefile` gains `publish` (`publish.py --write`) and `check-publish` (`publish.py --check`) targets, and `check` runs `check-publish` when guide.yaml declares a publish block (the target is a no-op with a notice otherwise). `doctor.py` needs no change (no new tools). Antora and MkDocs adapters are untouched (FR-016).

**Rationale**: the scaffold Makefile is the integration point for every toolkit command (`regions`, `site`, `check` at lines 65-83); conditional wiring mirrors how `site-internal` and embedded paths already vary.

**Alternatives considered**: running the publish check unconditionally from `check.py` (couples the core checker to the gfm-only publish feature; the Makefile already owns format-specific wiring).

## R9: Embedded create move plan

**Decision**: `DESTINATIONS` in `embed.py` (line 62) gains `author-region`. The plan validator allows it only for sections of the root Markdown README (the file the front page replaces), and `apply` (line 704) writes the markers below the retained landing text instead of removing or relocating those sections. The create skill's classification step lists it as the default for landing-oriented sections (pitch, context, usage examples); `input` remains the default for instructional material. The old README's retained text stays byte-identical; the generated front page region (ownership comment, title, badges note if any, sources block, why card, navigation, closing links) is written below the end marker by the front page task, which now edits the region between markers instead of the whole file.

**Rationale**: the move plan already carries per-section destinations with validation (lines 557-574) and per-path constraints for the root README (lines 652-656: its only destinations today are input/developer); adding one destination follows the existing shape. The front page task then works on a file that already has markers and author text, which is exactly the story 2 flow.

**Alternatives considered**: a plan-level boolean `keep_landing` instead of per-section destinations (less granular than the existing per-section model the author already edits); relocating landing text into the guide and re-emitting it (defeats the purpose: the text would be guide-owned).

## R10: Reviewer briefs and evolve flow

**Decision**: `front-page-contract.md` is rewritten for the region model: the ownership comment inside the region, badges and logo as ordinary author text (rule 3's special case dissolves), the region-only editing rule for the page task, and a review addition directing the reviewer to read the author region and flag contradictions with the guide region or sources as non-blocking findings (FR-014). `page-procedure.md` and `page-review-guide.md` carry the same instruction for published-region source pages. `evolve/SKILL.md` section 8 (hand edits) states that author text outside the region is never reported and that region hand edits are reported before rewriting (FR-010).

**Rationale**: these three files are the single source of the page task and review behavior; the plugin's skills are thin wrappers around them.

**Alternatives considered**: encoding the advisory in `check.py` as a lint (rejected by the brainstorm: nothing in the author region may fail a check, FR-013; contradiction detection is judgment, not syntax).

## R11: aprofile migration

**Decision**: out of scope for this feature (spec Assumptions). The publish mechanism is its replacement path: declare the publish block, add markers, delete `sync-readme.py` and the two Makefile targets. Recorded here so the adoption note lands in the feature's walkthrough.

**Alternatives considered**: shipping a migration subcommand in `adopt.py` (no second consumer yet; aprofile is one repository).
