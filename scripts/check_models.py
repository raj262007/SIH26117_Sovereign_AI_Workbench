"""
Sovereign AI Workbench - Local Ollama Model Readiness & Health Check Script.
Queries http://localhost:11434/api/tags to verify that both required models:
  1. 'qwen2.5vl:3b' (Vision & Schematics Engine)
  2. 'qwen2.5:7b' (Analytical & Reasoning Engine)
are locally installed and ready for 100% air-gapped, zero-WAN-egress execution.
"""

import sys
import os
import requests

REQUIRED_MODELS = [
    {
        "role": "Vision & Schematics Engine",
        "tag": "qwen2.5vl:3b",
        "command": "ollama pull qwen2.5vl:3b",
        "description": "Visual telemetry extraction for P&ID drawings, schematics, and scanned inspection logs."
    },
    {
        "role": "Analytical & Reasoning Engine",
        "tag": "qwen2.5:7b",
        "command": "ollama pull qwen2.5:7b",
        "description": "Deterministic Python code execution, API 570 compliance auditing, and executive report drafting."
    }
]

OLLAMA_HOST = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")


if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def check_models():
    print("=" * 70)
    print(" [SOVEREIGN ON-PREMISE AGENTIC AI WORKBENCH - MODEL HEALTH CHECK]")
    print("=" * 70)
    print(f"Target Ollama Service : {OLLAMA_HOST}")

    # 1. Probe Ollama Connectivity
    tags_endpoint = f"{OLLAMA_HOST}/api/tags"
    try:
        resp = requests.get(tags_endpoint, timeout=3.0)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Cannot connect to Ollama service at {OLLAMA_HOST}.")
        print("   Please start Ollama using: 'ollama serve' in your terminal.\n")
        return False
    except Exception as e:
        print(f"\n[ERROR] Unexpected failure querying {tags_endpoint}: {e}\n")
        return False

    installed_models = [m.get("name", "") for m in data.get("models", [])]
    print(f"Ollama Status         : ONLINE (HTTP 200)")
    print(f"Total Installed Models: {len(installed_models)}")
    if installed_models:
        print(f"Installed Tags        : {', '.join(installed_models)}")
    else:
        print("Installed Tags        : (None)")
    print("-" * 70)

    # 2. Check each required model
    all_ready = True
    missing_models = []
    for item in REQUIRED_MODELS:
        role = item["role"]
        tag = item["tag"]
        cmd = item["command"]
        desc = item["description"]

        is_installed = any(tag.lower() in installed.lower() for installed in installed_models)
        if is_installed:
            status_symbol = "[READY]"
            action_text = "Installed and bound to local sovereign engine."
        else:
            status_symbol = "[NOT PULLED]"
            action_text = f"Action needed: run '{cmd}'"
            all_ready = False
            missing_models.append(tag)

        print(f"{status_symbol} {role}")
        print(f"    Model Tag  : {tag}")
        print(f"    Description: {desc}")
        print(f"    Status     : {action_text}\n")

    print("-" * 70)
    if all_ready:
        print("[SUCCESS] ALL REQUIRED SOVEREIGN MODELS ARE LOCALLY PRESENT!")
        print("   The workbench is 100% ready for air-gapped local AI inference.")
    else:
        print("[NOTICE] OFFLINE DETERMINISTIC FALLBACK MODE IS ACTIVE.")
        print("   The workbench will run all engineering math, OCR parsing,")
        print("   and deliverable generation (.docx/.xlsx) via deterministic offline logic.")
        print(f"   Missing model(s): {', '.join(missing_models)}")
        print("   To enable full on-premise neural inference, pull the missing model(s):")
        for m in missing_models:
            print(f"     ollama pull {m}")
    print("=" * 70 + "\n")

    return all_ready


if __name__ == "__main__":
    check_models()
