# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

Student-generated reviews for Computer Science and Data Science courses at UNL.
This knowledge is highly valuable because official university catalogs only list prerequisites and generic syllabus definitions. The unofficial reviews capture the true workload, grading curves, coding language requirements, and professor teaching styles that students need to survive and plan their schedules effectively.

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| #   | Source               | Description                     | URL or location                                                                                       |
| --- | -------------------- | ------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1   | Rate My Professor    | CS155E                          | https://www.ratemyprofessors.com/professor/1753186                                                    |
| 2   | Rate My Professor    | CSCE 322                        | https://www.ratemyprofessors.com/professor/3124994                                                    |
| 3   | Rate My Professor    | CSCE235                         | https://www.ratemyprofessors.com/professor/2548211                                                    |
| 4   | Rate My Professor    | CSCE378                         | https://www.ratemyprofessors.com/professor/2787050                                                    |
| 5   | Rate My Professor    | CSCE230                         | https://www.ratemyprofessors.com/professor/2398527                                                    |
| 6   | Reddit               | Transferring for CS to UNL post | https://www.reddit.com/r/Nebraska/comments/1bcxahr/university_of_nebraskalincoln_review_for_computer/ |
| 7   | Reddit               | Computer Science Questions      | https://www.reddit.com/r/UNLincoln/comments/qkig1k/computer_science_questions/                        |
| 8   | Official UNL website | UNL CS major overview           | https://catalog.unl.edu/undergraduate/engineering/computer-science/                                   |
| 9   | Official UNL website | Degree requirements             | http://catalog.unl.edu/undergraduate/engineering/computer-science/#text                               |
| 10  | Reddit               | Transferring to UNL CS Post     | https://www.reddit.com/r/UNLincoln/comments/giq20o/sccunl_comp_sci/                                   |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**
600 characters

**Overlap:**
75 characters

**Reasoning:**
Most of my documents are made up of RMP reviews and Reddit comment threads. These documents are very dense and expansive. Students may shift from discussing grading to exam difficulties within their comments. A smaller chunk size makes sure that the individual chunks remain semantically pure without diluting the semantic signal. The 75-character overlap guarantees that if a comment regarding a course prerequisite or a professor's grading policy spans two sentences, the context is preserved across chunk boundaries and won't be abruptly cut.

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**
all-MiniLM-L6-v2 (via sentence-transformers), stored in a local ChromaDB collection.

**Top-k:**
4

**Production tradeoff reflection:**
If deploying this product for real UNL students without cost constraints, I would move to an API-based commercial model like text-embedding-3-large or a stronger open model like bge-large-en-v1.5.

The main tradeoffs to weigh are context length, accuracy on domain-specific text, and latency vs. cost. all-MiniLM-L6-v2 caps out at 256 tokens, so longer reviews get truncated; a production model with a larger token limit would let me embed more of each review at once. A larger model would also better resolve the abbreviation/slang problem (mapping "weeder," "230," and a professor's nickname to the right course), at the cost of higher per-query latency and an API bill that scales with usage. Since this is a local, single-user demo, the small local model is the right call for now.

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| #   | Question                                                                                       | Expected answer                                                                                                                                                              |
| --- | ---------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | What do students say about the difficulty and exam structure of most CS classes?               | Difficulty varies by course (e.g. CSCE378 ~2/5, CSCE235 1–3/5, CSCE322 ~4/5); students note exams sometimes neglect key areas or contain errors, and homework is heavily weighted. |
| 2   | Can a transfer student easily transition into UNL's CS program from a community college?       | Yes — threads say community-college classes generally "transfer just fine," but you should confirm course equivalency early with an engineering advisor to avoid repeats.    |
| 3   | What are the technical elective requirements to graduate with a CS major at UNL?               | Core sequences (software-engineering foundations, data structures/algorithms, systems, discrete math, senior design) plus track electives; sequences taken in consecutive semesters. |
| 4   | How do students describe the workload and teaching style in upper-level courses?               | Upper-level courses shift from coding to theory/systems design; professors are described as caring and willing to adapt, expecting self-directed work and debugging.        |
| 5   | What is the easiest CS elective?                                                               | Students point to low-difficulty courses like CSCE378 (avg difficulty ~1.8/5) and Prof. Bevins' CSCE155T section ("easy to get a good grade with a little effort").         |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1. Students on Reddit and Rate My Professor often use abbreviations and slang, so the model might have trouble connecting queries to the right professor names and course numbers.

2. Student reviews have varied formats, so there is a risk that chunking splits a single student's multi-paragraph review across a chunk boundary, leaving retrieval with only half the context.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

```
┌────────────────────┐   ┌──────────────┐   ┌─────────────────────────┐
│ 1. INGESTION       │   │ 2. CHUNKING  │   │ 3. EMBEDDING + STORE    │
│ ingest.py          │   │ ingest.py    │   │ embed.py                │
│ • requests + BS4   │──▶│ chunk_text() │──▶│ • all-MiniLM-L6-v2      │
│ • RMP GraphQL      │   │ size 600     │   │   (sentence-transform.) │
│ • old.reddit HTML  │   │ overlap 75   │   │ • ChromaDB (.chroma/)   │
│ → documents/*.txt  │   │ → ~595 chunks│   │   collection: unl_cs    │
└────────────────────┘   └──────────────┘   └────────────┬────────────┘
                                                          │
        ┌─────────────────────────────────────────────────┘
        ▼
┌─────────────────────────┐   ┌──────────────────────────────────────┐
│ 4. RETRIEVAL            │   │ 5. GENERATION                        │
│ embed.query()           │   │ app.py                               │
│ • embed question        │──▶│ • Groq llama-3.3-70b-versatile       │
│ • cosine top-k = 4      │   │ • grounded system prompt + sources   │
│ • returns text+source   │   │ • Gradio web UI (localhost:7860)     │
└─────────────────────────┘   └──────────────────────────────────────┘
```

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**
Tool: Claude (Sonnet). Input: the Documents table and Chunking Strategy section above. Expectation: an `ingest.py` that fetches all 10 sources (Reddit via old.reddit HTML, UNL catalog via BeautifulSoup, RMP via its GraphQL endpoint), cleans the text, and saves one `.txt` per source, plus a `chunk_text()` using my 600/75 spec. Verify: run `python ingest.py`, confirm 10 files land in `documents/`, and spot-check that chunks are ~600 chars with the right overlap.

**Milestone 4 — Embedding and retrieval:**
Tool: Claude (Sonnet). Input: the Retrieval Approach section (all-MiniLM-L6-v2, top-k = 4) and the chunk files from Milestone 3. Expectation: an `embed.py` that embeds every chunk into a persistent ChromaDB collection and exposes a `query(question, k=4)` returning text + source + distance. Verify: run the built-in smoke test in `embed.py` against 3 sample questions and confirm the returned chunks are on-topic.

**Milestone 5 — Generation and interface:**
Tool: Claude (Sonnet) for code, Groq llama-3.3-70b-versatile for generation. Input: the retrieval output schema plus a grounding instruction. Expectation: an `app.py` with a system prompt that forces answers to use only retrieved excerpts, cites sources, and refuses when context is missing — wrapped in a Gradio UI. Verify: run my 5 evaluation questions through the UI and record results in README.md's Evaluation Report.
