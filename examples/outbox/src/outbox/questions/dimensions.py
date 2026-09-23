"""Pass one, how the draft reads: six dimensions, each a Score on a 0-4 scale."""

from __future__ import annotations

# Each dimension is a spectrum, and the order of the list *is* the scale.
# For several of these the good answer is in the middle, not at the top: see
# AUDIENCES in audience.py, where each reader says which stretch it wants.
DIMENSIONS: dict[str, tuple[str, list[str]]] = {
    "clarity": (
        "After one read, how clear is it what `draft` is about?",
        [
            "The subject has to be guessed at",
            "The point is in there, buried under other material",
            "Clear after a second read",
            "Clear on one read",
            "Impossible to misunderstand",
        ],
    ),
    "actionability": (
        "After reading `draft`, how clearly does the reader know what to do next?",
        [
            "Nothing indicates what the reader should do",
            "Something is wanted, but not what, or not by whom",
            "The action is stated but the reader has to work out the details",
            "The action is stated plainly",
            "The action, the owner and the timing are all unmistakable",
        ],
    ),
    "directness": (
        "How directly does `draft` state its point?",
        [
            "The point is never actually stated",
            "Heavily softened; the reader must infer the point",
            "Stated, with cushioning around it",
            "Stated plainly and early",
            "Blunt to the point of abruptness",
        ],
    ),
    "warmth": (
        "How warm is the tone of `draft` towards the reader?",
        [
            "Cold or hostile",
            "Clipped and purely transactional",
            "Neutral and businesslike",
            "Friendly and considerate",
            "Effusive",
        ],
    ),
    "formality": (
        "How formal is the register of `draft`?",
        [
            "Slang, fragments, lower case throughout",
            "Casual, the way colleagues talk",
            "Everyday professional",
            "Formal business writing",
            "Legalistic or ceremonial",
        ],
    ),
    "brevity": (
        "How does the length of `draft` compare to what it has to say?",
        [
            "Far longer than the content justifies",
            "Padded; a third could go",
            "About right for the content",
            "Tight; nothing spare",
            "So short that context is missing",
        ],
    ),
}
