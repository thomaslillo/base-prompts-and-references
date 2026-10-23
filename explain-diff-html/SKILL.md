---
name: "explain-diff-html"
description: "Use when the user asks for a rich or interactive explanation of a code change, diff, branch, or PR, or invokes /explain-diff-html. Produces an HTML slide deck, fact-checked against the code and written in plain newspaper prose."
---

# Explain a code change

Build an HTML slide deck that explains a code change to reviewers and product readers. Every claim matches the code. The prose reads like a New York Times article.

Work in this order: read the change, write a document, verify it, slice it into slides, build the HTML and review it. The document decides what to say. The slides decide how to show it.

Two files sit beside this skill:

- `gallery.html` holds the shell (styles, navigation, quiz engine) and one example of each component, with notes on when to use it. Draw from it. It is a resource, and its slide order means nothing.
- `check_deck.py` checks the markup, the slide budget and the code sidebars. Run it from the repository root, so it can confirm every file path: `python3 <this-skill-dir>/check_deck.py <deck.html>`.

## 1. Read the change

- Run `git diff --stat origin/main...HEAD`, `git diff --name-status origin/main...HEAD` and `git log --oneline origin/main..HEAD`. Read new files in full and changed files as diffs.
- Read the old behavior from the base branch with `git show origin/main:<path>`. Never describe old behavior from memory or from a plan document.
- Run `git status`. Describe uncommitted changes only when the working tree contains them.
- Treat plan documents as context. When a plan and the code disagree, the code wins.
- Read the latest commits. They often change a behavior the plan describes, such as a retry path that now fails jobs instead of skipping them.

## 2. Write the document

Write the whole explanation as one Markdown document before you write any HTML. Save it in a temporary directory outside the repository. Delete it after the final review. The deck is the only deliverable.

Use these sections, in this order. Skip any that do not apply.

1. **Title.** The headline and a lede of two or three sentences.
2. **Background, broad.** What the system does, end to end.
3. **Background, narrow.** The old behavior and the problem it caused.
4. **Overview.** Every stage of the new flow.
5. **Example.** Toy data that shows the core idea.
6. **One section per stage or mechanism**, in execution order.
7. **Failure handling.**
8. **Modes or tracks**, if the change behaves differently per client or configuration.
9. **Outputs.** The files or records the change produces.
10. **Rollout**, if the change needs a migration, a flag or a deploy order.
11. **Code**, in the order a reviewer should read it.
12. **Results and risks.** Gains, costs, what nobody has tested, what to check in the first runs and any known gap.
13. **Quiz.** Five questions.

Each section has a headline, prose in the style of section 4, and one line naming the visual it needs, such as `Visual: table of 5 prompts by outcome`. Name the visual here. Build it in step 6.

A code section also names the file by its full repository path, the lines to show, and one sentence on when the code runs and who calls it.

The deck has no target length. It has as many slides as the story needs. Concise writing keeps a small change short and gives a large one room. Do not pad a small change or squeeze a large one.

## 3. Verify every claim

Check each factual claim in the document against the code before you slice it. Prose is easier to check than claims spread across tables, cards and diagrams.

For a long document, split the claims into three or four groups. If your agent can run subagents in parallel, give each one a group. Give each checker:

- The exact claims to check, one by one: names, numbers, defaults, enum values, file paths, error types and behavior.
- The instruction to report a verdict for each claim (correct, wrong, partly wrong or can't verify), with `file:line` evidence and corrected wording.
- The instruction to check old behavior against `origin/main` and to edit nothing.

Confirm the high-impact corrections yourself before you apply them. Checkers misread intent too. "Exhausted ops are dropped" can mean ops that ran out of revision rounds, or ops that hit the call budget.

These claims most often turn out wrong:

- Retry and redrive behavior. Does the code skip a job, fail it or reject the request?
- What a function removes or accepts. "Removes unbacked JSON-LD" turned out to mean "removes JSON-LD that fails to parse."
- Which mode or client type a feature applies to.
- Exact function signatures, enum members, section headings and file paths.
- Which errors raise and which the code handles.
- Counts. Check "nine switches," "four ops" and "five replace seven" against the code.
- Quiz answers. Each correct answer must be a behavior the code has. Do not invent details such as "logs a warning."

## 4. Write like a New York Times article

Four rules govern the prose: be concise, use active voice, add no flair and be clear.

**Concise**

- A headline is one full sentence of about 12 words that says what is now true: "The gate now checks every atom against the page, 10 at a time."
- Every sentence carries a fact the reader needs in this section. Cut sentences that restate the headline or an earlier section.
- State each fact once. A later section refers back to it.
- Keep one idea per sentence. Vary the length. Split any sentence the reader would have to parse twice.
- After the draft, make a cutting pass. Remove every word that does not change the meaning.

**Active voice**

- Name the actor: "the pipeline," "the editor," "Gemini," "the API" or a named function. Do not say "code" when you mean a specific part of the system.
- Write without first person. The deck has no narrator.

**No flair**

- Use plain verbs. Leave out superlatives, teasers, reveals and adjectives that grade the change, such as "clean," "powerful" or "elegant."
- Write headlines as news. Leave out slogans and summaries of a relationship, such as "Code owns structure; models own words."
- State the positive fact. Leave out "X, not Y" constructions such as "slots, not byte offsets."
- Write short, literal transitions: "Then the editor runs." Leave out colon setups like "Next, the main event: the edit loop."
- Give callouts plain labels: "Decision," "Edge case," "Order matters," "In short" or "Known gap."

**Clear**

- Say the concrete thing. Instead of "Models write the documents, inside a structure that code controls," write "A model writes the sentences, and the pipeline picks the sections."
- Use plain words for internal jargon in prose: "edit" for "op," "phrases that give away the source" for "provenance leaks."
- Put an identifier in `<code>` where it first matters and where a reviewer needs to find it. Do not repeat it in every sentence.
- Define a term on first use. Use the same term after that.
- Name the uncertainty. Say plainly what nobody has tested and what could go wrong in the first runs.

**Punctuation.** Use no em dashes or en dashes. Avoid parentheses in prose. Use colons only before a list or an example. Use straight quotes. Leave out the serial comma, as the Times does: "summary, FAQ and captions."

When the draft is done, run the `unslop` skill over it if it is available. `check_deck.py` later flags flair, likely passive voice and first person in the deck.

## 5. Slice the document into slides

Each section becomes one or more slides. Every slide fits this budget:

- An eyebrow and one headline.
- One visual.
- At most one callout.
- About 80 words of prose.
- An italic transition line that leads into the next slide.

The word counts are guidance. A failures table can run long. A second visual always gets its own slide. Slicing moves sentences from the document onto slides and adds none. Detail that fits no slide stays out of the deck.

**Code slides** follow extra rules, so a developer can place the code in the codebase:

- A slide shows one code block, or two that the reader needs together, such as a caller and the function it calls.
- A `.code-context` sentence above the code says when it runs and who calls it. A `.code-note` sentence below it says what to notice.
- The `.file` label gives the full path from the repository root in a `.path` span, such as `ace-edge/core/db.py`.
- A collapsible `details.tree` sidebar shows the slide's files and the folders above them, from the repository root. Each file shown is an `li.hit` whose `data-path` matches its label. With two blocks, `.mark` numbers match each block to its file. Mark added and modified files from `git diff --name-status`. Add a sibling folder only when its role helps place the file.
- Use `pre.sample` for log lines, payloads and other output that lives in no source file. It needs no sidebar.

## 6. Build the HTML

Write one self-contained HTML file.

- Copy the shell from `gallery.html` unchanged: the first `<style>` block, the shared SVG `defs` at the top of `<body>`, the navigation bar and the last `<script>` block. Leave out the gallery-only `<style>` block and every `.gallery-note`.
- Open the gallery now, after the document exists. For each slide, pick the component that fits the visual the document names. Do not follow the gallery's order, and do not use a component because the gallery has it.
- Write the quiz in the `#quiz-data` JSON block: five questions, four options each, the correct index in `a` and an explanation in `e`, written in the section 4 style.
- Unless the user gives a location, save the file under the repository's `docs/` directory with a date prefix, such as `docs/2026-01-12-explanation-<slug>.html`. Create the directory if needed.

| Component | Use it for | Avoid it for |
|---|---|---|
| Flow row: `.flow`, `.step.model`, `.step.code`, `.step.out` | Pipelines and request paths of four to six steps | Branches and loops |
| Card grid: `.grid.g2` or `.g3`, `.card.good`, `.warn`, `.bad`, `.info` | Two or three parallel ideas, such as gains, costs and risks | Four or more cards, or cards longer than two sentences |
| Before and after: `.g2` with `.card.bad` and `.card.good` | One behavior, old and new | A list of unrelated old problems |
| Table: `.tablewrap`, with `.chip.g`, `.y`, `.r`, `.b` | Rows with the same columns: failures, outputs, settings | One or two rows |
| Toy data: `.page`, `.el`, `.slot` | The example section | Real pages |
| Diagram: `.svgwrap` with `.sv-*` classes | Loops, branches and fan-out | Anything a flow row shows |
| Code: `.codeview` | Every code block taken from a file | Output samples |
| Output sample: `pre.sample` | Log lines and payloads | Code from a file |
| Callout: `.callout.key`, `.decision`, `.edge`, `.risk` | The main point, a decision, an edge case, a risk | A second callout on the slide |

Colors carry meaning. In flows and diagrams, blue is a model call, green is deterministic code and red is a stored output. On cards and chips, green is safe or passing, yellow is a tradeoff, red is a failure or risk and blue is an external system or human step. Use the tokens and classes. Never write hex values in markup.

Keep the shell's type. Text a reader reads uses `--ink`. `--muted` is for chrome only: arrows, the slide counter, code comments and tree labels. Monospace is for code, file paths and the directory tree. Size any new element in `rem`, so the root size still scales the whole deck.

These details prevent rendering problems:

- Put every SVG marker in the shared `defs` at the top of `<body>`. A marker inside a hidden slide does not render from other slides.
- Do not put a newline directly after `<pre>`. It renders as a blank line.
- Escape `<` as `&lt;` in code. An unescaped generic or tag can swallow the rest of the block.
- SVG text does not wrap. Use one `<text>` element per line and keep labels short enough to fit their boxes.
- Give every diagram `role="img"` and an `aria-label`.

## 7. Final review

1. Run `check_deck.py`. Fix every FAIL. Fix every WARN unless the content justifies it.
2. Read the deck from start to finish as the target reader. Check the story, slide order, visuals, technical accuracy, navigation and quiz answers. Open a code slide at phone width and confirm the sidebar collapses above the code.
3. Fix what you find, then run the checker again.
4. Delete the Markdown document.
5. End with a short summary: the checks you ran, each factual correction with the old and new claim side by side, and anything you could not verify.
