---
name: clean-and-simple-code
description: >-
  Enforces writing clean, simple, and easily understandable code without unnecessary complexity,
  and maintaining a clear, organized, and relevant project structure. Use whenever writing,
  refactoring, or organizing code and files in the project.
---

# Clean, Simple Code & Logical Project Structure

This skill guides the agent to prioritize simplicity, legibility, and maintainability above all else. Avoid premature optimization, excessive abstraction, and bloated project hierarchies.

---

## 1. Core Principles: Keep It Simple (KISS)

1. **Clarity Over Cleverness**:
   * Write code that a beginner or peer can understand in 10 seconds.
   * Avoid convoluted one-liners, obscure language features, or deeply nested logic.
   * Prefer explicit `for` loops and simple conditional blocks over dense, nested list comprehensions or lambda chaining.

2. **No Over-Engineering (YAGNI - You Aren't Gonna Need It)**:
   * Do not create 5 layers of abstract base classes, factories, and interfaces when a single, clean function or small class solves the problem directly.
   * Do not introduce heavy third-party libraries when a standard library module (e.g., `os`, `json`, `urllib`, `dataclasses`) is sufficient.

3. **Readable Function & Variable Names**:
   * Use descriptive, intention-revealing names:
     * Good: `calculate_corrosion_deficit(actual_thickness, minimum_threshold)`
     * Bad: `calc_def(t, m)`, `process_data_v2_final()`
   * Keep functions short (typically 15–30 lines) and focused on a single responsibility.

4. **Helpful, Non-Obvious Comments**:
   * Explain *why* something is done, not just *what* the syntax is.
   * Add docstrings to all major functions specifying expected input types and return values.

---

## 2. Standard & Relevant Project Structure

Always organize project files into logical, self-contained directories. Never dump scripts, configs, and outputs randomly into the root folder.

### Recommended Layout:

```text
my_project/
├── AGENTS.md                  # Project rules & coding standards
├── README.md                  # Project overview, setup, and usage guide
├── requirements.txt           # Clean, unpinned or loosely pinned core dependencies
├── .env.example               # Template for environment variables (no real secrets)
│
├── config/                    # Configuration files only
│   ├── litellm_config.yaml    # Model routing & provider configuration
│   └── settings.py            # Typed application settings (ports, paths)
│
├── src/                       # All core source code
│   ├── __init__.py
│   ├── agent/                 # Agent reasoning and orchestration logic
│   │   ├── state.py           # Clean state schema (e.g., TypedDict)
│   │   └── graph.py           # LangGraph workflow definition
│   │
│   ├── tools/                 # Independent, modular tools (easy to unit-test)
│   │   ├── ocr_tool.py        # Document parsing & text extraction
│   │   ├── sandbox_tool.py    # Local Python code execution
│   │   └── export_tool.py     # Word/Excel deliverable generation
│   │
│   └── utils/                 # General-purpose helper functions
│       └── file_helpers.py    # Safe file I/O, hashing, directory creation
│
├── ui/                        # Frontend presentation code
│   └── app.py                 # Streamlit / Web dashboard
│
├── tests/                     # Clean, fast unit and integration tests
│   ├── test_tools.py
│   └── test_workflow.py
│
├── data/                      # Local data (git-ignored if large/confidential)
│   ├── sample_inputs/         # Example test files (e.g., sample PDF/image)
│   └── outputs/               # Generated reports (.docx, .xlsx)
│
└── .agents/                   # Agent customizations, skills, and runbooks
    └── skills/
        └── clean-and-simple-code/
            └── SKILL.md
```

---

## 3. Code Standards Checklist Before Saving Code

Before presenting or saving any code, verify:

- [ ] **Can a new developer understand this immediately?**
- [ ] **Is the project hierarchy flat and intuitive?** (No unnecessary nesting like `src/app/core/services/impl/handlers/...`)
- [ ] **Are error messages helpful?** (Print exact reasons for failure, e.g., `"File 'data/input.pdf' not found. Please place the file in the data/ directory."`)
- [ ] **Are dependencies minimal?** Only import packages genuinely needed for the task.
- [ ] **Are sensitive credentials protected?** Always load via environment variables (`os.environ.get(...)`) and provide `.env.example`.
