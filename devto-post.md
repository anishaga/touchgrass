---
title: The AI That Prints You a Walk, Then Tells You to Close the Laptop
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

## What I Built

Most "AI for the outdoors" apps want you to keep looking at your phone while you're outdoors. I wanted the opposite: an AI whose output is a piece of paper.

**Touch Grass Field Cards** is a small command-line tool. You tell it where you're walking, for how long, who's coming and what mood you're in. A model running on your own machine writes a one-page A5 card: a mission, six things to look for, a listening exercise, a no-phone challenge and a "home by" time. You print it, put the phone in your pocket, and tick boxes with a pen.

It's for anyone who sets out for a walk and ends up scrolling, and especially for families who need a reason to go past the end of the street.

## Demo

A sample card is in the repo at [`examples/sample-card.html`](https://github.com/anishaga/touchgrass/blob/main/examples/sample-card.html). Run the tool with `--demo` to generate one without a model.

## Code

{% embed https://github.com/anishaga/touchgrass %}

## How I Built It

The design rule is **facts from math, words from the model.**

- **Facts are computed, not generated.** Sunrise, sunset, moon phase and season come from the NOAA solar equations, about 15 lines of standard-library Python that run offline. The "be home by" time is calculated in code too. A hallucinated sunset on a trail is a safety bug, so the model never gets to decide it.
- **The model supplies the voice.** I run Gemma 3 1B through Ollama and pass the facts in as ground truth. A 1B model can't be trusted to follow a format on its own, so Ollama's structured outputs enforce a JSON schema, and the result is still validated, clipped to sane lengths and retried up to three times if it's unusable.
- **It prompts, it never identifies.** I deliberately don't ask a small local model "what is this plant?" or "is this safe?", because small models are confidently wrong. The prompt only lets it say notice, count, compare, listen and sketch. A word check in code also throws away any card that mentions eating, tasting or touching and asks again, so safety doesn't depend on a 1B model obeying a prompt. The printed card tells you not to touch or eat anything you can't identify yourself.
- **Paper is the interface.** Output is one self-contained HTML file with print CSS for A5, styled after trail blazes and park signage, so there's nothing to load at the trailhead.

There are no dependencies beyond Python and Ollama. I built it with Claude as my coding assistant.

## Why Does Open Innovation Matter?

- **A tiny model is enough.** Gemma 3 1B is small enough to run on an ordinary laptop with no GPU, which is the difference between a tool you can use anywhere and one that needs a data centre.
- **Where you walk is a pattern of life.** Your coordinates plus the time you leave the house say a lot about you. With local inference, that never leaves your machine.
- **The card works with no signal.** Generate it at home, even in airplane mode. The product is paper, so the backcountry doesn't break it.
- **Swap the model, change the voice.** `--model` takes anything Ollama serves, and the whole personality is one string in the repo. A birder edition or a kid edition is a fork away, which a closed API wouldn't let me fine-tune or inspect.
- **It costs nothing per walk.** A family can print a card for every outing without thinking about metered tokens.

The honest trade-off: a frontier model would probably write wittier prompts, and a 1B model will be plainer than a bigger one (`--model gemma3:4b` is one flag away). I'll take a plainer card that works in a forest.

## Field Test

I generated the card for a walk around the neighborhood. I set the location coordinates for my local park and used `--minutes 45`. The card printed smoothly on half-letter paper.
During the walk, it was incredibly refreshing to keep the phone in my pocket. I actually managed to check off four out of the six prompts: "Something that changed since last week" (the leaves were noticeably more orange) and "A pattern that repeats" (brickwork on a path). I also did the listening exercise for a minute straight.

The card took about 8-10 seconds to generate locally using Gemma 3 1B on my Windows machine. It was fast, coherent, and perfectly fulfilled the mission without ever feeling like an "AI feature".

## Prize Categories

**Best Use of Gemma**: the cards are written by Gemma 3 1B running locally through Ollama.
