# Product vision

## The role of semantic memory

Kivi already has two forms of personalization that solve local problems: styles shape how speech becomes text, and phonetic memory helps it recognize words that belong to the person. Semantic memory is different. It gives Hey Kivi continuity across interactions: not just “what did they say?” but “what durable context from their work should change what I do now?”

I would make Kivi’s semantic memory a **grounded working memory of durable context**. It is deliberately smaller than the user's history. The system should remember things that are useful across future requests: stable preferences, project facts, important decisions, recurring working conventions, and notable episodes. It should ignore conversational filler, guesses, temporary moods, and details whose value is unclear.

## Where the value is created

The value is not the memory itself. It is the reduction in repeated explanation.

A person should be able to say “prepare this for the design review” and have Kivi understand that “design review” refers to a particular project, that the user prefers short headings plus action items, and that a previous decision should be preserved. The assistant becomes more useful because the user does not need to reconstruct context every time.

This argues for a narrow product: memory should influence Hey Kivi when it helps complete a request. It should have little or no effect on ordinary dictation, where predictability is more important than personalization.

## What deserves to be remembered

I use three practical categories:

**Facts** — durable statements about the user's work or operating context, such as “Atlas launches in October.”

**Preferences** — explicit or repeatedly evidenced preferences, such as “meeting notes should end with action items.”

**Episodes** — significant prior events that may matter later, such as “the Atlas review moved to Thursday after the client requested more pricing detail.”

Each memory has evidence links to source interactions. Memories can be superseded, rejected, or forgotten; the original evidence remains inspectable.

## What Kivi must never assume

Kivi should not infer high-stakes or identity-level attributes from weak signals. It should not promote a one-off statement into a permanent preference without enough evidence. It should not treat an old statement as current when a later interaction contradicts it. Most importantly, the assistant must not fill gaps with plausible guesses. “I don't have enough evidence in your history” is a better product outcome than a confident falsehood.

## Trust and control

Other memory products show the right direction but also expose a tension. ChatGPT provides controls to review, edit, delete, and disable memory, and shows sources behind personalization.Other assistants increasingly treat memory as something users should be able to inspect and control. Kivi should take the same principle further by making the source and reasoning behind remembered context visible.

Kivi should make the same principle more operational: whenever memory changes Hey Kivi's behaviour, the user can see the remembered claim and its supporting interactions. Forgetting should be a user action, not an administrator workflow. A memory should be useful enough to earn its place, and reversible enough that the user never has to surrender control to keep using the assistant.

The resulting product is not an assistant with a giant biography of the user. It is an assistant with a small, evidence-backed map of context that helps it do work.
