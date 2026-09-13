"""
Dynamic Task Classifier & Model Router for Sovereign Agentic AI Workbench.
Autonomously dispatches heterogeneous tasks to specialized open-weight models.
Supports 2-stage classification: Stage 1 (Fast Rule Heuristics) -> Stage 2 (LLM Fallback).
"""

import json
from typing import Dict, Any, Tuple, Optional

# Official Model Registry strictly bound to local on-premise Ollama models
SOVEREIGN_VISION_MODEL = "qwen2.5vl:3b"
SOVEREIGN_ANALYTICAL_MODEL = "qwen2.5:7b"
OLLAMA_API_BASE = "http://localhost:11434/v1"

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "coding": {
        "model": SOVEREIGN_ANALYTICAL_MODEL,
        "endpoint": OLLAMA_API_BASE,
        "engine_alias": "coding-engine",
        "rationale": f"High-precision deterministic Python code generation and mathematical verification ({SOVEREIGN_ANALYTICAL_MODEL})."
    },
    "document_qa": {
        "model": SOVEREIGN_ANALYTICAL_MODEL,
        "endpoint": OLLAMA_API_BASE,
        "engine_alias": "reasoning-engine",
        "rationale": f"Grounded document analysis, compliance checks, and regulatory QA ({SOVEREIGN_ANALYTICAL_MODEL})."
    },
    "vision_document": {
        "model": SOVEREIGN_VISION_MODEL,
        "endpoint": OLLAMA_API_BASE,
        "engine_alias": "vision-engine",
        "rationale": f"Multimodal visual parsing for engineering drawings, P&IDs, and scanned forms ({SOVEREIGN_VISION_MODEL})."
    },
    "general_reasoning": {
        "model": SOVEREIGN_ANALYTICAL_MODEL,
        "endpoint": OLLAMA_API_BASE,
        "engine_alias": "reasoning-engine",
        "rationale": f"General reasoning, multi-step synthesis, and executive briefing drafting ({SOVEREIGN_ANALYTICAL_MODEL})."
    }
}

def classify_stage1_rules(user_query: str, file_path: str = "") -> Optional[Tuple[str, str]]:
    """
    Stage 1: Fast deterministic rule-based heuristic classification.
    Returns (task_type, rationale) or None if inconclusive.
    """
    query_lower = (user_query or "").lower()
    file_lower = (file_path or "").lower()

    # Rule 1: Visual / Multimodal files or keywords
    visual_extensions = [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".pdf"]
    visual_keywords = ["scan", "drawing", "p&id", "image", "schematic", "visual", "ocr", "layout", "diagram"]
    if any(file_lower.endswith(ext) for ext in visual_extensions) or any(k in query_lower for k in visual_keywords):
        return ("vision_document", "Stage 1 Rule: Visual extension or diagram/scan keywords detected.")

    # Rule 2: Code files or computational keywords
    code_extensions = [".py", ".csv", ".json", ".sql", ".sh", ".ts", ".js"]
    code_keywords = ["code", "calculate", "math", "verify", "formula", "python", "deficit", "thickness", "simulation", "equation"]
    if any(file_lower.endswith(ext) for ext in code_extensions) or any(k in query_lower for k in code_keywords):
        return ("coding", "Stage 1 Rule: Code/data extension or computational keywords detected.")

    # Rule 3: Document QA / Regulatory keywords
    doc_keywords = ["memo", "policy", "standard", "compliance", "executive", "board", "sop", "draft", "clause", "summarize", "approval note", "qa"]
    if any(k in query_lower for k in doc_keywords):
        return ("document_qa", "Stage 1 Rule: Regulatory, policy, or memo drafting keywords detected.")

    return None

def classify_two_stage(user_query: str, file_path: str = "") -> Tuple[str, Dict[str, Any], str]:
    """
    Two-Stage Task Classifier:
    1. Stage 1: Deterministic rules (file extensions + keyword heuristics).
    2. Stage 2: Small LLM fallback with strict JSON schema if Stage 1 is inconclusive.
    Returns: (task_type, model_config, rationale)
    """
    # Stage 1: Rule-based
    rule_match = classify_stage1_rules(user_query, file_path)
    if rule_match:
        task_type, rationale = rule_match
        config = MODEL_REGISTRY.get(task_type, MODEL_REGISTRY["general_reasoning"])
        return task_type, config, rationale

    # Stage 2: Local Ollama Fallback (strictly on-premise, zero WAN/cloud)
    try:
        import requests
        prompt = (
            f"Classify the following request into exactly ONE task type: 'coding', 'document_qa', 'vision_document', or 'general_reasoning'.\n"
            f"Request: \"{user_query}\"\n"
            f"Respond ONLY with valid JSON: {{\"task_type\": \"<type>\", \"rationale\": \"<short reason>\"}}"
        )
        payload = {
            "model": SOVEREIGN_ANALYTICAL_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.0}
        }
        res = requests.post("http://localhost:11434/api/generate", json=payload, timeout=2.0)
        if res.status_code == 200:
            res_text = res.json().get("response", "")
            if "{" in res_text and "}" in res_text:
                json_str = res_text[res_text.find("{"):res_text.rfind("}") + 1]
                data = json.loads(json_str)
                tt = data.get("task_type", "general_reasoning")
                if tt in MODEL_REGISTRY:
                    return tt, MODEL_REGISTRY[tt], f"Stage 2 Local Ollama Fallback: {data.get('rationale', 'Classified via local Ollama')}"
    except Exception:
        pass

    # Default sovereign fallback
    default_type = "general_reasoning"
    return default_type, MODEL_REGISTRY[default_type], "Defaulted to general reasoning engine for multi-step agentic execution."


def auto_select_model(prompt: str, file_payload: Optional[str] = None) -> Dict[str, str]:
    """
    Intelligent, deterministic, and LLM-assisted router for the Sovereign Workbench.
    Strictly dispatches between two local Ollama models:
      1. 'qwen2.5vl:3b' for visual schematics, P&ID drawings, inspection sheets (MULTIMODAL_VISION).
      2. 'qwen2.5:7b' for math, Python code execution, API 570 SOP auditing, and memos (ANALYTICAL_REASONING).

    No UI dropdown required; routing is completely autonomous.
    Returns:
        {"selected_model": str, "task_type": str, "routing_reason": str}
    """
    prompt_str = (prompt or "").strip()
    prompt_lower = prompt_str.lower()
    file_str = (file_payload or "").strip()
    file_lower = file_str.lower()

    # 1. Deterministic Heuristics: Visual file extensions & base64 image data
    visual_extensions = (".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp")
    is_visual_file = any(file_lower.endswith(ext) for ext in visual_extensions) or file_str.startswith("data:image/")

    if is_visual_file:
        return {
            "selected_model": SOVEREIGN_VISION_MODEL,
            "task_type": "MULTIMODAL_VISION",
            "routing_reason": f"Image file payload detected ({file_str[:50]}). Auto-selected {SOVEREIGN_VISION_MODEL} for visual telemetry extraction."
        }

    # 2. Deterministic Heuristics: Visual engineering concepts in prompt
    visual_keywords = [
        "p&id", "pid", "schematic", "blueprint", "corrosion photo",
        "drawing", "diagram", "scan", "visual", "ocr", "layout",
        "flowsheet", "piping and instrumentation", "inspection sheet",
        "radiograph", "isometrics", "photo"
    ]
    if any(vk in prompt_lower for vk in visual_keywords):
        return {
            "selected_model": SOVEREIGN_VISION_MODEL,
            "task_type": "MULTIMODAL_VISION",
            "routing_reason": f"Visual engineering analysis keywords detected in prompt. Auto-selected {SOVEREIGN_VISION_MODEL}."
        }

    # 3. Deterministic Heuristics: Formula calculation, Python execution, API 570 SOP auditing, or memo drafting
    analytical_keywords = [
        "calculate", "formula", "python", "code", "execute", "execution",
        "script", "deficit", "thickness", "retirement thickness", "remaining life",
        "corrosion rate", "api 570", "api-570", "asme", "sop", "compliance",
        "audit", "memo", "approval memo", "executive memo", "draft", "standard",
        "clause", "equation", "math", "simulation"
    ]
    code_extensions = (".py", ".csv", ".json", ".sql", ".sh")
    is_code_file = any(file_lower.endswith(ext) for ext in code_extensions)

    if is_code_file or any(ak in prompt_lower for ak in analytical_keywords):
        return {
            "selected_model": SOVEREIGN_ANALYTICAL_MODEL,
            "task_type": "ANALYTICAL_REASONING",
            "routing_reason": f"Computational, compliance auditing, or drafting task detected. Auto-selected {SOVEREIGN_ANALYTICAL_MODEL}."
        }

    # 4. Stage 2: LLM-Assisted Fallback (local Ollama zero-shot classification)
    try:
        import requests
        system_instruction = (
            "You are an industrial task routing classifier. "
            "Classify the user prompt into exactly ONE task: 'MULTIMODAL_VISION' or 'ANALYTICAL_REASONING'.\n"
            "Output strictly valid JSON: {\"task_type\": \"MULTIMODAL_VISION\" | \"ANALYTICAL_REASONING\", \"reason\": \"<short reason>\"}"
        )
        payload = {
            "model": SOVEREIGN_ANALYTICAL_MODEL,
            "prompt": f"{system_instruction}\n\nUser Request: {prompt_str}\nClassification JSON:",
            "stream": False,
            "options": {"temperature": 0.0}
        }
        res = requests.post("http://localhost:11434/api/generate", json=payload, timeout=1.5)
        if res.status_code == 200:
            res_text = res.json().get("response", "")
            if "{" in res_text and "}" in res_text:
                json_str = res_text[res_text.find("{"):res_text.rfind("}") + 1]
                data = json.loads(json_str)
                tt = data.get("task_type", "ANALYTICAL_REASONING").upper()
                if "VISION" in tt:
                    return {
                        "selected_model": SOVEREIGN_VISION_MODEL,
                        "task_type": "MULTIMODAL_VISION",
                        "routing_reason": f"LLM Router: {data.get('reason', 'Classified as multimodal vision task.')}"
                    }
                else:
                    return {
                        "selected_model": SOVEREIGN_ANALYTICAL_MODEL,
                        "task_type": "ANALYTICAL_REASONING",
                        "routing_reason": f"LLM Router: {data.get('reason', 'Classified as analytical reasoning task.')}"
                    }
    except Exception:
        pass

    # 5. Default Sovereign Fallback
    return {
        "selected_model": SOVEREIGN_ANALYTICAL_MODEL,
        "task_type": "ANALYTICAL_REASONING",
        "routing_reason": f"Defaulted to sovereign analytical & coding engine ({SOVEREIGN_ANALYTICAL_MODEL}) for general engineering operations."
    }


def route_task(user_query: str, file_path: str = "") -> Tuple[str, str, str]:
    """
    Backwards-compatible router function for existing tests and endpoints.
    Returns: (task_type, engine_name, rationale)
    """
    task_type, config, rationale = classify_two_stage(user_query, file_path)
    
    # Map back to legacy names if needed
    legacy_type_map = {
        "vision_document": "vision",
        "coding": "coding",
        "document_qa": "reasoning",
        "general_reasoning": "general"
    }
    legacy_task_type = legacy_type_map.get(task_type, "general")
    engine_name = config.get("engine_alias", "coding-engine")
    
    return legacy_task_type, engine_name, rationale

