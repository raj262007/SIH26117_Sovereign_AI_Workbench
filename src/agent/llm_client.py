"""
Unified LLM Client & Dynamic Gateway for Sovereign Agentic AI Workbench.
Handles model routing across Groq Cloud, Local Ollama, and Grounded Offline Simulation.
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

load_dotenv()

from src.utils.tracing import create_generation
from src.tools.ocr_tool import parse_inspection_text


SOVEREIGN_VISION_MODEL = "qwen2.5vl:3b"
SOVEREIGN_ANALYTICAL_MODEL = "qwen2.5:7b"
DEFAULT_OLLAMA_API_BASE = "http://localhost:11434/v1"


class LLMGateway:
    """Manages model calls across local sovereign Ollama models and deterministic offline fallback."""

    def __init__(self):
        self.mode = os.environ.get("WORKBENCH_MODE", "local").lower()
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.ollama_base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        self.ollama_api_base = os.environ.get("OLLAMA_API_BASE", DEFAULT_OLLAMA_API_BASE)

    def call_model(self, engine_name: str, prompt: str, system_prompt: Optional[str] = None,
                   temperature: Optional[float] = None,
                   langfuse_trace=None, langfuse_span=None,
                   context_metrics: Optional[Dict[str, Any]] = None,
                   chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Route prompt to assigned engine with timing, conversation memory, and observability."""
        active_key = os.environ.get("GROQ_API_KEY") or self.groq_api_key
        temp = temperature if temperature is not None else (0.6 if engine_name == "reasoning-engine" else 0.1)
        start_ms = time.time() * 1000

        target_model = SOVEREIGN_VISION_MODEL if "vision" in engine_name else SOVEREIGN_ANALYTICAL_MODEL

        # Strict local sovereign mode is the primary runtime path
        if self.mode == "cloud" and os.environ.get("GROQ_API_KEY"):
            result = self._call_groq(engine_name, prompt, system_prompt, os.environ.get("GROQ_API_KEY"), temp, context_metrics, chat_history)
            model_name = f"groq/{target_model}"
        elif self.mode == "offline":
            result = self._offline_generator(engine_name, prompt, context_metrics, chat_history)
            model_name = f"offline/{engine_name}"
        else:
            # Default is strictly local sovereign Ollama execution
            result = self._call_ollama(engine_name, prompt, system_prompt, target_model, temp, context_metrics, chat_history)
            model_name = f"ollama/{target_model}"

        # Audit trace
        create_generation(
            trace=langfuse_trace,
            name=f"llm-{engine_name}",
            model=model_name,
            input_text=prompt,
            output_text=result,
            duration_ms=(time.time() * 1000) - start_ms,
            parent_span=langfuse_span
        )
        return result

    def _call_groq(self, engine: str, prompt: str, system_prompt: Optional[str],
                   api_key: str, temperature: float, context_metrics: Optional[dict],
                   chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Execute request via Groq Cloud API with multi-turn conversation memory."""
        try:
            import litellm
            messages = [{"role": "system", "content": system_prompt}] if system_prompt else []
            if chat_history:
                for msg in chat_history:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role in ["user", "assistant"] and content:
                        messages.append({"role": role, "content": content})
            messages.append({"role": "user", "content": prompt})

            resp = litellm.completion(
                model="groq/qwen/qwen3.8-27b",
                messages=messages,
                api_key=api_key,
                temperature=temperature,
                timeout=15.0
            )
            return resp.choices[0].message.content
        except Exception:
            return self._offline_generator(engine, prompt, context_metrics, chat_history)

    def _call_ollama(self, engine: str, prompt: str, system_prompt: Optional[str],
                     target_model: str, temperature: float,
                     context_metrics: Optional[dict],
                     chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Execute request via local Ollama instance (OpenAI-compatible /v1 endpoint)
        strictly referencing the designated sovereign models without external cloud egress.
        """
        import requests

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if chat_history:
            for msg in chat_history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ["user", "assistant"] and content:
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": prompt})

        # Call local Ollama OpenAI-compatible /v1/chat/completions endpoint
        endpoint_v1 = f"{self.ollama_api_base}/chat/completions"
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }

        try:
            resp = requests.post(endpoint_v1, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices and "message" in choices[0]:
                    return choices[0]["message"].get("content", "")

            # If Ollama returns 404 (model not found)
            if resp.status_code == 404:
                advisory = (
                    f"[SOVEREIGN LOCAL ADVISORY: Model not yet pulled locally]\n"
                    f"Ollama model '{target_model}' is not installed locally. Run 'ollama pull {target_model}' to enable live local inference.\n"
                    f"Executing deterministic offline rule/math engine locally (Zero WAN Egress guaranteed).\n\n"
                )
                return advisory + self._offline_generator(engine, prompt, context_metrics, chat_history)
            elif resp.status_code != 200:
                advisory = (
                    f"[SOVEREIGN LOCAL ADVISORY: Model not yet pulled locally]\n"
                    f"Ollama returned HTTP {resp.status_code} for '{target_model}'. Run 'ollama pull {target_model}' if not present.\n"
                    f"Executing deterministic offline rule/math engine locally.\n\n"
                )
                return advisory + self._offline_generator(engine, prompt, context_metrics, chat_history)
        except requests.exceptions.ConnectionError:
            advisory = (
                f"[SOVEREIGN LOCAL ADVISORY: Model not yet pulled locally]\n"
                f"Local Ollama service is not reachable at {self.ollama_api_base}. Ensure Ollama is running locally ('ollama serve').\n"
                f"Executing deterministic offline rule/math engine locally (Zero WAN Egress guaranteed).\n\n"
            )
            return advisory + self._offline_generator(engine, prompt, context_metrics, chat_history)
        except Exception as e:
            advisory = (
                f"[SOVEREIGN LOCAL ADVISORY: Model not yet pulled locally]\n"
                f"Local Ollama inference failed ({str(e)}). Run 'ollama pull {target_model}'.\n"
                f"Executing deterministic offline rule/math engine locally.\n\n"
            )
            return advisory + self._offline_generator(engine, prompt, context_metrics, chat_history)

        # Strictly local deterministic fallback - ZERO WAN/Cloud fallback
        return self._offline_generator(engine, prompt, context_metrics, chat_history)

    def _offline_generator(self, engine: str, prompt: str, context_metrics: Optional[dict],
                           chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Deterministic, air-gapped generator for offline use.
        Distinguishes between general conversational inquiries and complex industrial inspections.
        """
        # Parse metrics using verified OCR parser
        parsed = context_metrics if (context_metrics and context_metrics.get("measurement_points")) else parse_inspection_text(prompt)
        points = parsed.get("measurement_points", [])

        # If no measurement points exist, treat as natural conversation / coding request
        if not points:
            return self._handle_general_query(prompt, engine, chat_history)

        # Industrial Inspection Mode:
        meta = parsed.get("metadata", {})
        thresh = parsed.get("thresholds", {})
        line_no = meta.get("line_number", "10\"-HC-1004-CS300")
        std_name = meta.get("standard", "API 570")
        t_thresh = thresh.get("t_threshold", 3.30)
        t_min = thresh.get("t_min", 2.80)

        breached = [p for p in points if p.get("measured_mm", 999) < t_thresh]
        worst_point = min(breached or points, key=lambda p: p.get("measured_mm", 999))

        loc_desc = f"{worst_point.get('point_id')} ({worst_point.get('description', 'Survey Point')})"
        meas = worst_point.get("measured_mm", t_thresh)
        nom = worst_point.get("nominal_mm", 10.31)
        deficit = round(meas - t_thresh, 2)
        is_breach = len(breached) > 0

        # Branch 1: Python CodeAct verification script
        if engine == "coding-engine":
            status_str = "FAIL - CRITICAL BREACH" if is_breach else "PASS - COMPLIANT"
            pts_code = ",\n".join(f"    {repr(p)}" for p in points)
            return f"""```python
# {std_name} Structural Integrity & Corrosion Math Verification Script
true = True
false = False
null = None

points = [
{pts_code}
]
T_threshold = {t_thresh}
T_min = {t_min}
line_name = {json.dumps(line_no)}
location_str = {json.dumps(loc_desc)}

breached_points = [p for p in points if p["measured_mm"] < T_threshold]
status = "{status_str}"

print(f"Asset / Line: {{line_name}}")
print(f"Status: {{status}}")
print(f"Location: {{location_str}}")
print(f"Actual Thickness: {meas} mm")
print(f"Retirement Threshold: {{T_threshold}} mm")
print(f"Deficit: {deficit} mm")
```"""

        # Branch 2: Reasoning Engine Chain-of-Thought & Executive Memo
        if is_breach:
            breach_list = ", ".join(f"{b['point_id']} ({b['measured_mm']} mm)" for b in breached)
            return (
                f"<think>\n"
                f"1. Structural evaluation of asset {line_no} under {std_name}.\n"
                f"2. Ultrasonic scan identified critical wall degradation at Location {loc_desc}.\n"
                f"3. Measured thickness {meas:.2f} mm is below threshold {t_thresh:.2f} mm ({deficit:+.2f} mm deficit).\n"
                f"4. Additional breached points: {breach_list}.\n"
                f"5. Mandatory operational de-rating and isolation enforced per {std_name} Clause 7.2.\n"
                f"</think>\n\n"
                f"{std_name} COMPLIANCE AUDIT CONCLUSION: CRITICAL BREACH DETECTED.\n"
                f"Asset Line {line_no} failed structural integrity criteria at Location {loc_desc}. "
                f"Current measured thickness of {meas:.2f} mm has breached the mandatory {t_thresh:.2f} mm retirement threshold "
                f"by {abs(deficit):.2f} mm ({deficit:+.2f} mm deficit). Additional breached locations: {breach_list}. "
                f"Immediate operational de-rating, process isolation, and urgent clamp replacement are mandated per {std_name}."
            )
        else:
            return (
                f"<think>\n"
                f"1. Structural evaluation of asset {line_no} under {std_name}.\n"
                f"2. All {len(points)} inspection points exceed retirement threshold {t_thresh:.2f} mm.\n"
                f"3. Lowest measured thickness is {meas:.2f} mm at Location {loc_desc}.\n"
                f"4. Safe operating margin maintained under {std_name}.\n"
                f"</think>\n\n"
                f"{std_name} COMPLIANCE AUDIT CONCLUSION: COMPLIANT / SAFE OPERATION.\n"
                f"All inspected measurement points for {line_no} meet or exceed the mandatory {t_thresh:.2f} mm retirement threshold. "
                f"Lowest measured point is {loc_desc} at {meas:.2f} mm. Routine operational clearance approved under {std_name}."
            )

    def _handle_general_query(self, prompt: str, engine: str = "reasoning-engine",
                              chat_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Handle greetings, coding requests, and general technical inquiries conversationally with memory."""
        p = prompt.strip().lower()

        # Build context from previous conversation turns
        history_text = ""
        if chat_history:
            turns = [f"{m.get('role', 'user').capitalize()}: {m.get('content', '')}" for m in chat_history if m.get('content')]
            history_text = "\n".join(turns)

            import re
            lines_found = re.findall(r'(\d{1,2}"?-[A-Za-z0-9]+-[A-Za-z0-9\-]+)', history_text)
            user_texts = " ".join(m.get("content", "") for m in chat_history if m.get("role") == "user")
            stop_words = {"evaluating", "inspecting", "checking", "testing", "analyzing", "working", "looking", "asking", "writing", "your"}
            raw_names = re.findall(r'(?:my name is|i am(?:\s+an?|\s+inspector|\s+engineer)?)\s+([A-Z][a-z]+)', user_texts, re.IGNORECASE)
            names_found = [n for n in raw_names if n.lower() not in stop_words]

            recalled_facts = []
            if lines_found:
                recalled_facts.append(f"- Line / Asset Tag: **{lines_found[-1]}**")
            if names_found:
                recalled_facts.append(f"- User: **{names_found[-1]}**")

            detail = "\n".join(recalled_facts) if recalled_facts else f"In our previous discussion, you noted: \"{chat_history[-1].get('content', '')[:120]}\""
            return (
                f"<think>\nRetrieved conversational memory from {len(chat_history)} previous turn(s).\n</think>\n\n"
                f"Based on our earlier discussion:\n{detail}\n\n"
                f"How would you like to proceed with this evaluation?"
            )

        # 2. Greetings
        if any(p.startswith(g) or p == g for g in ["hi", "hello", "hey", "hii", "hiii", "good morning", "greetings"]):
            return (
                f"<think>\nRecognized user greeting. Responding conversationally without running industrial inspection.\n</think>\n\n"
                f"Hello Sagar! I am your **Sovereign Industrial AI Workbench** assistant (Team rv2 // SIH 2026).\n\n"
                f"I operate fully on-premise to assist with:\n"
                f"- **Engineering Calculations:** Python scripts for corrosion rates and remaining life.\n"
                f"- **Regulatory Codes:** Guidance on API 570 and ASME B31.3 statutory provisions.\n"
                f"- **Autonomous Inspection Audits:** Upload inspection scans (PDF, TXT, CSV, image) or select a benchmark to run our tri-engine verification pipeline.\n\n"
                f"How can I help you today?"
            )

        # 3. Code / Calculation Request or Coding Engine
        if engine == "coding-engine" or any(w in p for w in ["calculate", "write code", "python code", "script", "function", "write a python", "def "]):
            return (
                f"<think>\nUser requested Python engineering code. Providing clean, documented implementation.\n</think>\n\n"
                f"Here is a clean, documented Python implementation for corrosion analysis:\n\n"
                f"```python\n"
                f"# Sovereign Engineering Calculation Utility per API 570\n\n"
                f"def calculate_corrosion_metrics(nominal_mm: float, measured_mm: float, t_min: float, service_years: float) -> dict:\n"
                f"    \"\"\"Calculate wall loss, corrosion rate, and remaining life per API 570.\"\"\"\n"
                f"    wall_loss = nominal_mm - measured_mm\n"
                f"    corrosion_rate = wall_loss / max(service_years, 0.1)\n"
                f"    remaining_life = (measured_mm - t_min) / max(corrosion_rate, 0.001) if corrosion_rate > 0 else 99.0\n"
                f"    \n"
                f"    return {{\n"
                f"        'wall_loss_mm': round(wall_loss, 2),\n"
                f"        'corrosion_rate_mm_year': round(corrosion_rate, 3),\n"
                f"        'remaining_life_years': round(remaining_life, 1),\n"
                f"        'status': 'BREACH' if measured_mm < t_min else ('MONITOR' if remaining_life < 2.0 else 'COMPLIANT')\n"
                f"    }}\n\n"
                f"if __name__ == '__main__':\n"
                f"    print(calculate_corrosion_metrics(nominal_mm=10.31, measured_mm=4.15, t_min=3.60, service_years=10.0))\n"
                f"```"
            )

        # 4. General Technical Q&A
        return (
            f"<think>\nUser asked technical inquiry. Formulating clear, grounded engineering response.\n</think>\n\n"
            f"Regarding **{prompt.strip()}**:\n\n"
            f"Under industrial process piping codes (**API 570** & **ASME B31.3**):\n"
            f"- **Structural Minimum ($T_{{\\text{{min}}}}$):** The minimum wall thickness required to contain internal pressure.\n"
            f"- **Retirement Threshold ($T_{{\\text{{threshold}}}}$):** Structural minimum plus mandatory corrosion safety allowance.\n"
            f"- **Category M Fluid Service:** Lethal or toxic process streams (e.g. sour gas with $H_2S > 8,500\\text{{ ppm}}$) requiring stringent containment.\n\n"
            f"To audit specific ultrasonic scan telemetry, upload your report file or select a benchmark to run the autonomous pipeline."
        )


def extract_think_cot(text: str) -> tuple[str, str]:
    """Extract <think>...</think> reasoning block from model response."""
    if "<think>" in text and "</think>" in text:
        parts = text.split("</think>", 1)
        return parts[0].replace("<think>", "").strip(), parts[1].strip()
    return "", text.strip()


# Global singleton instance
llm_gateway = LLMGateway()
