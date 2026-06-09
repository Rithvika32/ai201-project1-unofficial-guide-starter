"""
app.py — Grounded RAG query interface for the UNL CS Unofficial Guide.

Retrieves relevant chunks from ChromaDB, then uses Groq (llama-3.3-70b-versatile)
to generate an answer grounded strictly in the retrieved context.

Run:
    python app.py
Then open http://localhost:7860
"""

import os

import gradio as gr
from dotenv import load_dotenv
from groq import Groq

from embed import query

load_dotenv()

GROQ_MODEL = "llama-3.3-70b-versatile"

client = Groq(api_key=os.environ["GROQ_API_KEY"])

SYSTEM_PROMPT = """You are a helpful assistant for UNL (University of Nebraska-Lincoln) \
Computer Science students. You answer questions using ONLY the document excerpts provided \
below. Do not use any outside knowledge or information not present in the excerpts.

Rules:
- If the excerpts do not contain enough information to answer the question, respond with: \
"I don't have enough information in my documents to answer that."
- Always cite which document(s) your answer draws from at the end of your response, \
formatted as: Sources: [filename1, filename2, ...]
- Be concise and specific. Quote or closely paraphrase the documents where relevant."""


def ask(question: str) -> dict:
    """
    Full RAG pipeline: retrieve chunks, generate grounded answer.
    Returns dict with keys: answer (str), sources (list[str]), chunks (list[dict]).
    """
    chunks = query(question)

    if not chunks:
        return {
            "answer": "No relevant documents found.",
            "sources": [],
            "chunks": [],
        }

    # Build context block from retrieved chunks
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[Excerpt {i} — source: {chunk['source']}]\n{chunk['text'].strip()}"
        )
    context = "\n\n".join(context_parts)

    user_message = f"Document excerpts:\n\n{context}\n\nQuestion: {question}"

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=512,
    )

    answer = response.choices[0].message.content.strip()
    sources = list(dict.fromkeys(c["source"] for c in chunks))  # deduplicated, ordered

    return {"answer": answer, "sources": sources, "chunks": chunks}


# ── Gradio UI ─────────────────────────────────────────────────────────────────

def handle_query(question: str):
    if not question.strip():
        return "", "", ""

    try:
        result = ask(question)
    except Exception as e:
        return f"Error: {e}", "", ""

    sources_text = "\n".join(f"• {s}" for s in result["sources"])

    chunks_text = ""
    for i, c in enumerate(result["chunks"], 1):
        chunks_text += f"[{i}] ({c['source']}  dist={c['distance']})\n{c['text'].strip()}\n\n"

    return result["answer"], sources_text, chunks_text.strip()


with gr.Blocks(title="UNL CS Unofficial Guide") as demo:
    gr.Markdown("# UNL CS Unofficial Guide\nAsk anything about CS courses, professors, or degree requirements at UNL.")

    with gr.Row():
        with gr.Column(scale=2):
            question_input = gr.Textbox(
                label="Your question",
                placeholder='e.g. "What do students say about CSCE 235?" or "What are the CS degree requirements?"',
                lines=2,
            )
            ask_btn = gr.Button("Ask", variant="primary")

        with gr.Column(scale=3):
            answer_output = gr.Textbox(label="Answer", lines=8, interactive=False)
            sources_output = gr.Textbox(label="Sources", lines=3, interactive=False)

    with gr.Accordion("Retrieved chunks (debug)", open=False):
        chunks_output = gr.Textbox(label="Raw retrieved chunks", lines=12, interactive=False)

    ask_btn.click(
        fn=handle_query,
        inputs=question_input,
        outputs=[answer_output, sources_output, chunks_output],
    )
    question_input.submit(
        fn=handle_query,
        inputs=question_input,
        outputs=[answer_output, sources_output, chunks_output],
    )

if __name__ == "__main__":
    demo.launch()
