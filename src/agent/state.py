"""
State schema for the Sovereign Agentic AI Workbench.
Keeps track of user input, extracted telemetry, sandboxed calculations, and generated deliverables.
"""

from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    # Raw input from user or file upload
    request: str  # User's directive or prompt
    user_query: str  # Backwards-compatible alias
    file_path: Optional[str]
    chat_history: Optional[List[Dict[str, str]]]  # Multi-turn conversation turns [{"role": "user"|"assistant", "content": "..."}]
    
    # Task routing & model dispatch
    task_type: str  # 'coding' | 'document_qa' | 'vision_document' | 'general_reasoning' | 'vision' | 'reasoning'
    selected_model: str  # Engine name (e.g. 'coding-engine', 'vision-engine')
    model_endpoint: Dict[str, Any]  # Config entry from MODEL_REGISTRY
    task_mode: str  # 'full_pipeline', 'deep_thinking', or 'coding_only'
    
    # Agent Planner State Machine fields
    plan: List[str]  # Ordered sequence of steps e.g. ["ingest", "retrieve", "calculate", "deliver"]
    completed_steps: List[Dict[str, Any]]  # Finished step outputs and telemetry
    current_step_index: int  # Pointer to active step in the plan
    retrieved_context: List[Dict[str, Any]]  # Chunks from RAG with doc and page citations
    retry_count: int  # Retries on current step (capped at 2)
    
    # Data extraction from OCR / parsing
    extracted_text: str
    extracted_metrics: Dict[str, Any]
    
    # Deep Thinking Chain-of-Thought (Reasoning Engine)
    deep_thinking_cot: str
    
    # Sandboxed execution (Coding Engine)
    generated_code: str
    sandbox_output: str
    calculation_status: str  # 'PASS', 'FAIL - CRITICAL BREACH', etc.
    
    # Final deliverables
    generated_report_path: Optional[str]  # Primary .docx memo path
    final_memo_text: str
    deliverables: Dict[str, str]  # Paths keyed by format: 'docx', 'xlsx', 'pptx'
    error_message: Optional[str]
    
    # Forensic audit trail
    execution_logs: List[str]
    
    # Observability & Orchestration (optional — set by Langfuse/Temporal integrations)
    langfuse_trace: Optional[Any]  # Langfuse trace object for nested span tracking
    workflow_id: Optional[str]  # Temporal workflow ID for durable execution
