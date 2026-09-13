# Project Rules: Code Simplicity & Architecture

This file defines mandatory rules for this repository. Every piece of code written or modified must adhere to these principles.

## 1. Code Simplicity (KISS & Anti-Overengineering)
- **Always write clean, straightforward, and readable code.** Never write complex, convoluted, or over-engineered logic when a simple, direct approach works.
- **Avoid unnecessary abstraction layers.** Do not create extra wrapper classes, design pattern cascades, or factory factories unless explicitly required.
- **Prioritize clarity over cleverness.** Use self-explanatory variable and function names. Write simple loops and conditionals instead of confusing one-liners.
- **Add concise, helpful comments.** Briefly explain the purpose of functions and any non-obvious engineering logic (e.g. calculation formulas or data transformations).

## 2. Organized & Relevant Project Structure
- Keep the directory structure clean, logical, and modular:
  - `src/`: Core application logic (agent graph, state, business logic).
  - `src/tools/`: Discrete, single-purpose tools (OCR, sandbox runner, report generators).
  - `config/`: Configuration files (LiteLLM YAML, environment configurations).
  - `ui/`: User interface code (Streamlit / frontend).
  - `data/`: Sample inputs and generated deliverables (`.docx`, `.xlsx`).
  - `tests/`: Simple, readable tests verifying core functionality.
- Never scatter scratch files, test scripts, or unorganized modules across the root directory.
- Keep dependencies lean, minimal, and documented in `requirements.txt`.
