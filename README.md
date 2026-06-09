# The Unofficial Guide — Project 1

> **How to use this template:**
> Complete each section _after_ you've built and tested the corresponding part of your system.
> Do not write placeholder text — if a section isn't done yet, leave it blank and come back.
> Every section below is required for submission. One-liners will not receive full credit.

---

## Domain

This system answers questions about **Computer Science (and Data Science) courses, professors, and degree requirements at the University of Nebraska–Lincoln**, using student-generated reviews alongside the official catalog.

This knowledge is valuable because the official course catalog only lists prerequisites and generic descriptions — it says nothing about real workload, grading curves, which programming languages a course actually uses, exam fairness, or a professor's teaching style. That information is scattered across Rate My Professor reviews and Reddit threads, where it's hard to search and easy to lose. This guide pulls it into one place a student can query in plain English while planning a schedule.

---

## Document Sources

<!-- List every source you collected documents from.
     Be specific: include URLs, subreddit names, forum thread titles, or file names.
     Aim for variety — sources that together cover different subtopics or perspectives. -->

| #   | Source            | Type              | URL or file path                                                                                      |
| --- | ----------------- | ----------------- | ----------------------------------------------------------------------------------------------------- |
| 1   | Rate My Professor | Professor reviews | https://www.ratemyprofessors.com/professor/1753186 → `documents/rmp_cs155e.txt`                       |
| 2   | Rate My Professor | Professor reviews | https://www.ratemyprofessors.com/professor/3124994 → `documents/rmp_csce322.txt`                      |
| 3   | Rate My Professor | Professor reviews | https://www.ratemyprofessors.com/professor/2548211 → `documents/rmp_csce235.txt`                      |
| 4   | Rate My Professor | Professor reviews | https://www.ratemyprofessors.com/professor/2787050 → `documents/rmp_csce378.txt`                      |
| 5   | Rate My Professor | Professor reviews | https://www.ratemyprofessors.com/professor/2398527 → `documents/rmp_csce230.txt`                      |
| 6   | Reddit (r/Nebraska)  | Forum thread   | https://www.reddit.com/r/Nebraska/comments/1bcxahr/ → `documents/reddit_unl_cs_review.txt`            |
| 7   | Reddit (r/UNLincoln) | Forum thread   | https://www.reddit.com/r/UNLincoln/comments/qkig1k/ → `documents/reddit_cs_questions.txt`             |
| 8   | UNL Catalog       | Official catalog  | https://catalog.unl.edu/undergraduate/engineering/computer-science/ → `documents/unl_cs_overview.txt` |
| 9   | UNL Catalog       | Official catalog  | http://catalog.unl.edu/undergraduate/engineering/computer-science/#text → `documents/unl_cs_requirements.txt` |
| 10  | Reddit (r/UNLincoln) | Forum thread   | https://www.reddit.com/r/UNLincoln/comments/giq20o/ → `documents/reddit_transfer_cs.txt`              |

---

## Chunking Strategy

<!-- Describe your chunking approach with enough specificity that someone else could reproduce it.
     Include:
     - Chunk size (characters or tokens) and why that size fits your documents
     - Overlap size and why (or why not) you used overlap
     - Any preprocessing you did before chunking (e.g., stripping HTML, removing headers)
     - What your final chunk count was across all documents -->

**Chunk size:**
600 characters (implemented in `chunk_text()` in `ingest.py`).

**Overlap:**
75 characters.

**Why these choices fit your documents:**
The corpus is dominated by dense RMP reviews and Reddit comment threads where a single student can jump from grading to exam difficulty in a few sentences. A 600-character window keeps each chunk to roughly one review or comment so the embedding stays semantically focused, instead of blending several students' opinions into one diluted vector. The 75-character overlap preserves context across a boundary — if a remark about a prerequisite or grading policy straddles two chunks, neither chunk loses the thread. Preprocessing: `clean_text()` collapses repeated newlines and runs of whitespace; the catalog pages have `nav`/`footer`/`script`/`style`/`header`/`aside` stripped via BeautifulSoup; Reddit is scraped from `old.reddit.com` to get plain HTML. Chunks shorter than 50 characters (whitespace-only fragments) are dropped.

**Final chunk count:**
595 chunks across 10 documents. Per file: reddit_cs_questions 8, reddit_transfer_cs 12, reddit_unl_cs_review 18, rmp_cs155e 13, rmp_csce230 15, rmp_csce235 12, rmp_csce322 5, rmp_csce378 4, unl_cs_overview 254, unl_cs_requirements 254. (The two catalog pages are the heavy contributors at 254 each — see Failure Case Analysis.)

---

## Embedding Model

<!-- Name the embedding model you used and explain your choice.
     Then answer: if you were deploying this system for real users and cost wasn't a constraint,
     what tradeoffs would you weigh in choosing a different model?
     Consider: context length limits, multilingual support, accuracy on domain-specific text,
     latency, and local vs. API-hosted. -->

**Model used:**
`all-MiniLM-L6-v2` via `sentence-transformers`, with vectors stored in a local persistent ChromaDB collection (`.chroma/`, collection `unl_cs_guide`). Retrieval uses cosine distance, top-k = 4. It was chosen because it runs locally with no API cost or key, is fast on CPU, and is more than accurate enough for a single-user demo over a small corpus.

**Production tradeoff reflection:**
If I were deploying this for real UNL students and cost wasn't a constraint, I'd move to a stronger model such as OpenAI's `text-embedding-3-large` or the open `bge-large-en-v1.5`. The tradeoffs I'd weigh:
- **Context length:** all-MiniLM-L6-v2 truncates at 256 tokens, so longer reviews get cut off mid-thought. A larger context window would let me embed whole reviews without losing the tail.
- **Domain accuracy:** A larger model would better map student slang and abbreviations ("weeder," "230," a professor's nickname) onto the right courses, which is exactly where the small model struggles.
- **Latency vs. cost:** A bigger local model adds latency on CPU; an API-hosted model adds network round-trips and a per-query bill that scales with traffic. For a low-traffic local demo, the small model wins; for a real deployment serving many students, the accuracy gain would justify the cost.
- **Multilingual:** Not needed here (the corpus is English), so I wouldn't pay for multilingual capacity.

---

## Grounded Generation

<!-- Explain how your system enforces grounding — how does it prevent the LLM from answering
     beyond the retrieved documents?
     Describe both your system prompt (what instruction you gave the model) and any structural
     choices (e.g., how you formatted the context, whether you filtered low-relevance chunks).
     Do not just say "I told it to use the documents" — show the actual instruction or explain
     the mechanism. -->

**System prompt grounding instruction:**
The generator (Groq `llama-3.3-70b-versatile`, `temperature=0.2`) receives this system prompt (`app.py`):

> You are a helpful assistant for UNL Computer Science students. You answer questions using ONLY the document excerpts provided below. Do not use any outside knowledge or information not present in the excerpts.
> Rules:
> - If the excerpts do not contain enough information to answer the question, respond with: "I don't have enough information in my documents to answer that."
> - Always cite which document(s) your answer draws from at the end of your response, formatted as: Sources: [filename1, filename2, ...]
> - Be concise and specific. Quote or closely paraphrase the documents where relevant.

Beyond the prompt, grounding is enforced structurally: the only course content the model ever sees is the retrieved context. Each user turn is built as a labeled context block — `[Excerpt i — source: <filename>]` followed by the chunk text — and then the question, so the model can attribute claims to specific files. Low temperature (0.2) keeps it from drifting into invention, and if retrieval returns nothing the pipeline short-circuits before the LLM is even called ("No relevant documents found.").

**How source attribution is surfaced in the response:**
Two ways. (1) The model is instructed to end its answer with `Sources: [...]`. (2) Independently of the model, the app deduplicates the `source` filenames of the retrieved chunks and renders them in a dedicated **Sources** box in the Gradio UI, plus a collapsible "Retrieved chunks (debug)" panel that shows each raw chunk with its source and cosine distance — so a user can verify the answer against the underlying text.

---

## Evaluation Report

<!-- Run your 5 test questions from planning.md through your system and record the results.
     Be honest — a partially accurate or inaccurate result that you explain well is more
     valuable than a suspiciously perfect result. -->

| #   | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
| --- | -------- | --------------- | ---------------------------- | ----------------- | ----------------- |
| 1   | What do students say about the difficulty and exam structure of most CS classes? | Difficulty varies by course; exams sometimes miss key areas or contain errors; homework heavily weighted. | Pulled per-course difficulty (CSCE378 ~2/5, CSCE235 1–3/5, CSCE322 4/5) and noted CSCE230 exams "cover difficult parts and neglect key areas" and a CSCE322 exam had errors making problems unsolvable. | Relevant | Accurate |
| 2   | Can a transfer student easily transition into UNL's CS program from a community college? | Generally yes; classes "transfer just fine," but confirm equivalency with an advisor. | Said community-college classes would "transfer just fine," and recommended contacting a UNL advisor with your transcript for specifics. | Relevant | Accurate |
| 3   | What are the technical elective requirements to graduate with a CS major at UNL? | Core sequences + track electives, taken in consecutive semesters. | Returned the catalog's elective/prerequisite rules (CSCE 155, 156/156H, 310/310H, 361/361H) and the consecutive-semester sequencing rule. | Partially relevant | Partially accurate |
| 4   | How do students describe the workload and teaching style in upper-level courses? | Shift toward theory/systems; professors caring and adaptable, expect self-directed work. | Described professors as caring and adaptable (CSCE322 "cares more about understanding than rigorous testing"; CSCE235 Dr. Bolman "understanding about homework"). | Relevant | Accurate |
| 5   | What is the easiest CS elective? | Low-difficulty courses like CSCE378 and Prof. Bevins' CSCE155T. | Named Prof. Bevins' CSCE155T ("easy to get a good grade with a little effort," 2/5) and CSCE378 (avg difficulty ~1.8/5), while noting it can't be certain without data on every elective. | Partially relevant | Partially accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target
**Response accuracy:** Accurate / Partially accurate / Inaccurate

Overall: the system answers professor- and course-specific questions well because RMP reviews chunk cleanly. It is weaker on structural catalog questions (Q3, Q5) where the right answer is spread across the long, near-duplicate catalog pages and across many electives.

---

## Failure Case Analysis

<!-- Identify at least one question where retrieval or generation did not work as expected.
     Write a specific explanation of *why* it failed, tied to a part of the pipeline.

     "The answer was wrong" is not an explanation.

     "The relevant information was split across a chunk boundary, so retrieval returned
     only half the context — the model didn't have enough to answer correctly" is an explanation.

     "The embedding model treated the professor's nickname as out-of-vocabulary and returned
     results from an unrelated review" is an explanation. -->

**Question that failed:**
"What is the easiest CS elective?" (Q5) — and Q3 on technical-elective requirements shows the same root issue.

**What the system returned:**
For Q5 it named CSCE378 and one professor's CSCE155T section as "easy," but explicitly hedged that it couldn't confirm these were the *easiest* electives. It never compared across the full set of electives — it just surfaced the lowest-difficulty reviews that happened to be retrieved.

**Root cause (tied to a specific pipeline stage):**
This is a **retrieval + ingestion** failure, not a generation one. Two things compound:
1. **Duplicate ingestion skews the index.** The catalog "overview" and "requirements" URLs returned byte-identical pages (133,391 chars each → 254 chunks each), so 508 of 595 chunks — 85% of the index — are duplicated catalog boilerplate. Generic queries get crowded out by these near-identical chunks, and top-k = 4 can be filled by redundant catalog text instead of diverse reviews.
2. **"Easiest" requires comparison, but RAG retrieves locally.** Answering "easiest elective" means ranking *all* electives, but top-k = 4 only ever sees a handful of chunks. The model can only speak to whatever was retrieved, so it correctly refused to overclaim — the limitation is the retrieval design, not hallucination.

**What you would change to fix it:**
- De-duplicate at ingestion: hash each saved document and skip identical pages (drops ~254 redundant chunks immediately), or fetch the requirements page as a distinct catalog section.
- For comparison-style questions, raise top-k and/or add a metadata field for the numeric `avgDifficulty` per professor/course so the system can sort rather than rely on whatever embeds nearest.
- Add a light relevance-distance threshold so low-similarity catalog chunks don't fill the top-k for review-oriented questions.

---

## Spec Reflection

<!-- Reflect on how planning.md shaped your implementation.
     Answer both questions with at least 2–3 sentences each. -->

**One way the spec helped you during implementation:**
Writing the Chunking Strategy and Retrieval Approach sections first meant the chunk size (600), overlap (75), embedding model (all-MiniLM-L6-v2), and top-k (4) were already decided before any code existed. That let me hand those exact numbers to the AI tool as a concrete contract, so `chunk_text()` and `query()` came back matching the spec on the first pass instead of needing me to guess parameters and rewrite. Having the 10 sources tabulated up front also made `ingest.py` a straight translation of the table rather than an open-ended scraping task.

**One way your implementation diverged from the spec, and why:**
The planning doc anticipated using Claude/Groq purely for code, but I hadn't pinned down the *generation* model in the plan; in implementation I settled on Groq's `llama-3.3-70b-versatile` for the answer step because it's fast and free-tier friendly for a demo. I also discovered during ingestion that the two catalog URLs return the same page — something the plan didn't foresee — which inflated the chunk count and forced the de-duplication insight now captured in the Failure Case Analysis.

---

## AI Usage

<!-- Describe at least 2 specific instances where you used an AI tool during this project.
     For each: what did you give the AI as input, what did it produce, and what did you
     change, override, or direct differently?

     "I used Claude to help me code" is not sufficient.
     "I gave Claude my Chunking Strategy section from planning.md and asked it to implement
     chunk_text(). It returned a function using a fixed character split. I overrode the
     chunk size from 500 to 200 because my documents are short reviews, not long guides." -->

**Instance 1 — Ingestion of Rate My Professor reviews**

- _What I gave the AI:_ My Documents table from planning.md (the five RMP professor IDs and course labels) and a request to fetch their reviews into text files.
- _What it produced:_ An `ingest.py` that hits RMP's GraphQL endpoint, base64-encodes the legacy professor IDs into `Teacher-<id>` node IDs, and writes professor metadata plus up to 20 reviews per professor to `documents/`.
- _What I changed or overrode:_ I had it add a graceful fallback — when RMP blocks the request it prints a manual "copy/paste these URLs" step instead of crashing — and a `clean_text()` pass plus a 1.5s delay between requests so the scraper stays polite and the chunks aren't full of whitespace noise.

**Instance 2 — chunk_text() implementation**

- _What I gave the AI:_ My Chunking Strategy section (600-char chunks, 75-char overlap) and asked for a character-level splitter.
- _What it produced:_ A sliding-window `chunk_text()` stepping by `chunk_size - overlap`.
- _What I changed or overrode:_ I directed it to drop chunks shorter than 50 characters so whitespace-only fragments at document ends never get embedded — I'd rather lose a sliver of text than pollute the vector store with empty chunks. I kept the exact 600/75 numbers from the spec rather than letting it pick defaults.
