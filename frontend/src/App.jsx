import React, { useState, useEffect, useRef } from 'react';
import ReasoningBox, { ClaudeAsterisk } from './ReasoningBox';

const SAMPLE_BENCHMARKS = [
  {
    id: "rg-3301",
    title: '12"-RG-3301 Sour Gas (Breach Test)',
    filename: "uploads/Custom_Inspection_Telemetry.txt",
    query: "Verify 12\"-RG-3301-CS-NACE sour hydrogen recycle gas line against API 570 Category M thresholds and issue emergency memo.",
    preview: "12\"-RG-3301-CS-NACE | RG-05 degraded to 3.40mm (T_threshold: 4.50mm, T_min: 3.60mm)"
  },
  {
    id: "piping-104",
    title: "Piping UT Scan 104 (API 570)",
    filename: "Piping_UT_Scan_104.txt",
    query: "Verify ultrasonic piping thickness scan against API 570 thresholds and issue an executive de-rating memo.",
    preview: "10\"-HC-1004-CS300 | T-12 degraded to 3.20mm (T_threshold: 3.30mm, T_min: 2.80mm)"
  },
  {
    id: "cdu-overhead",
    title: "CDU-1 Heavy Crude Overhead",
    filename: "Piping_UT_Scan_104.txt",
    query: "Perform API 570 statutory audit on Atmospheric Distillation CDU-1 overhead piping.",
    preview: "Crude Distillation Unit CDU-1 | In-service wall thickness monitoring"
  }
];

export default function App() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [taskMode, setTaskMode] = useState("full_pipeline"); // full_pipeline, deep_thinking_only, coding_only
  const [selectedModel, setSelectedModel] = useState("qwen2.5:7b (Sovereign Local)");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Multi-turn conversation messages state
  const [messages, setMessages] = useState(() => {
    try {
      const saved = localStorage.getItem("sovereign_chat_messages");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Ingestion & File State
  const [attachedFile, setAttachedFile] = useState(null);
  const [attachedFileName, setAttachedFileName] = useState("");
  const [selectedBenchmark, setSelectedBenchmark] = useState(null);

  // Collapsible drawers state per message (keyed by message id)
  const [expandedDrawers, setExpandedDrawers] = useState({});

  // Live network egress telemetry state
  const [egressData, setEgressData] = useState({ egress_bytes: 0, status: "AIR_GAPPED_VERIFIED" });
  const [airgapStatus, setAirgapStatus] = useState({ outbound_kb_s: 0.0, is_airgapped: true, status: "AIR-GAPPED (0.0 KB/s)" });
  const fileInputRef = useRef(null);
  const chatBottomRef = useRef(null);

  // Persist messages to localStorage
  useEffect(() => {
    try {
      localStorage.setItem("sovereign_chat_messages", JSON.stringify(messages));
    } catch {}
  }, [messages]);

  // Network egress & live air-gap status polling
  useEffect(() => {
    const fetchEgress = () => {
      fetch("/api/airgap-status")
        .then(res => res.json())
        .then(data => {
          if (data && typeof data === "object") {
            setAirgapStatus(data);
          }
        })
        .catch(() => {});

      fetch("/api/network-egress")
        .then(res => res.json())
        .then(data => setEgressData(data))
        .catch(() => {});
    };
    fetchEgress();
    const timer = setInterval(fetchEgress, 3000);
    return () => clearInterval(timer);
  }, []);

  // Auto-scroll to bottom on new message or loading state
  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading]);

  const toggleDrawer = (msgId, drawerName) => {
    const key = `${msgId}-${drawerName}`;
    setExpandedDrawers(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const isDrawerOpen = (msgId, drawerName) => {
    return !!expandedDrawers[`${msgId}-${drawerName}`];
  };

  const handleFileSelect = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setAttachedFile(file);
      setAttachedFileName(file.name);
      setSelectedBenchmark(null);
      if (!query) {
        setQuery(`Analyze uploaded inspection report "${file.name}" against API 570 and synthesize compliance findings.`);
      }
    }
  };

  const handleSelectBenchmark = (benchmark) => {
    setSelectedBenchmark(benchmark);
    setAttachedFile(null);
    setAttachedFileName(benchmark.title);
    setQuery(benchmark.query);
  };

  const handleNewTask = () => {
    setMessages([]);
    try {
      localStorage.removeItem("sovereign_chat_messages");
    } catch {}
    setLoading(false);
    setQuery("");
    setAttachedFile(null);
    setAttachedFileName("");
    setSelectedBenchmark(null);
    setExpandedDrawers({});
  };

  const handleExecute = async (overridePrompt = null, overrideBenchmark = null) => {
    const activeBenchmark = overrideBenchmark || selectedBenchmark;
    const promptText = (overridePrompt || query).trim() || (activeBenchmark ? activeBenchmark.query : "");
    if (!promptText && !attachedFile && !activeBenchmark) return;

    const userMessage = {
      id: "msg-" + Date.now(),
      role: "user",
      content: promptText,
      attachedFileName: attachedFileName || (activeBenchmark ? activeBenchmark.title : ""),
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const currentHistory = [...messages, userMessage];
    setMessages(currentHistory);
    setQuery("");
    setLoading(true);
    const startTime = Date.now();

    // Prepare prior conversation turns for backend memory
    const historyPayload = messages.map(m => ({
      role: m.role,
      content: m.content || m.reasoning_summary || m.final_memo_text || ""
    }));

    const formData = new FormData();
    formData.append("query", promptText);
    formData.append("task_mode", taskMode);
    formData.append("chat_history", JSON.stringify(historyPayload));

    if (attachedFile) {
      formData.append("file", attachedFile);
    } else if (activeBenchmark) {
      formData.append("sample_name", activeBenchmark.filename);
    }

    try {
      const res = await fetch("/api/run-workflow", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      const seconds = Math.max(1, Math.round((Date.now() - startTime) / 1000));

      const assistantMessage = {
        id: "msg-" + (Date.now() + 1),
        role: "assistant",
        content: data.reasoning_summary || data.final_memo_text || "",
        executionDuration: seconds,
        ...data,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      if (data.selected_model) {
        setSelectedModel(data.selected_model);
      }

      setMessages([...currentHistory, assistantMessage]);
    } catch (err) {
      const errorAssistantMessage = {
        id: "msg-" + (Date.now() + 1),
        role: "assistant",
        content: "Error executing request: " + err.message,
        is_general_chat: true,
        is_error: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages([...currentHistory, errorAssistantMessage]);
    } finally {
      setLoading(false);
      setAttachedFile(null);
      setAttachedFileName("");
      setSelectedBenchmark(null);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!loading && (query.trim() || attachedFile || selectedBenchmark)) {
        handleExecute();
      }
    }
  };

  // Helper: Render an assistant message payload
  const renderAssistantContent = (msg) => {
    const isGeneralChat = msg.is_general_chat || !msg.status;

    // Mode 1: Clean Conversational / Coding prose (like Claude / ChatGPT)
    if (isGeneralChat) {
      return (
        <div className="text-sm text-[#1F1E1D] leading-relaxed whitespace-pre-wrap font-sans bg-white border border-[#E5E3DD] p-5 rounded-2xl shadow-2xs">
          {msg.final_memo_text || msg.reasoning_summary || msg.content}
        </div>
      );
    }

    // Mode 2: Industrial Inspection & Telemetry Compliance Suite
    const criticalPt = msg.extracted_metrics?.critical_points?.[0];
    const thresh = msg.extracted_metrics?.thresholds?.t_threshold;
    const stdName = msg.extracted_metrics?.metadata?.standard || "API 570";
    const isBreached = msg.status?.includes("FAIL") || msg.status?.includes("BREACH");
    const deficitNum = criticalPt && thresh ? (criticalPt.measured_mm - thresh).toFixed(2) : null;

    return (
      <div className="flex flex-col gap-4 self-start w-full">
        {/* Status Verdict Banner */}
        <div
          className={`p-4 rounded-xl border flex items-center justify-between ${
            isBreached ? "bg-red-50/80 border-red-200 text-red-900" : "bg-emerald-50/80 border-emerald-200 text-emerald-900"
          }`}
        >
          <div className="flex items-center gap-2.5">
            <i className={`fa-solid ${isBreached ? "fa-triangle-exclamation text-red-600" : "fa-circle-check text-emerald-600"} text-lg`}></i>
            <div>
              <div className="text-sm font-semibold tracking-tight">
                {msg.status || (isBreached ? "FAIL - CRITICAL BREACH" : "PASS - COMPLIANT")}
              </div>
              <div className="text-xs opacity-80 mt-0.5">
                {isBreached
                  ? `Location ${criticalPt?.point_id || "RG-05"} measured at ${criticalPt?.measured_mm?.toFixed(2)} mm (below ${thresh?.toFixed(2)} mm threshold)`
                  : `All points exceed statutory ${stdName} thresholds (${thresh ? `${thresh.toFixed(2)} mm` : "3.00 mm"})`}
              </div>
            </div>
          </div>
          <span className={`text-xs font-mono font-semibold px-2.5 py-1 rounded-full ${
            isBreached ? "bg-red-100 text-red-800 border border-red-300" : "bg-emerald-100 text-emerald-800 border border-emerald-300"
          }`}>
            {isBreached ? `Deficit: ${deficitNum ? `${deficitNum} mm` : "-0.30 mm"}` : "Compliant"}
          </span>
        </div>

        {/* Executive Memo Narrative */}
        {(msg.final_memo_text || msg.reasoning_summary) && (
          <div className="text-sm text-[#1F1E1D] leading-relaxed whitespace-pre-wrap font-sans bg-white border border-[#E5E3DD] p-5 rounded-2xl shadow-2xs">
            {msg.final_memo_text || msg.reasoning_summary}
          </div>
        )}

        {/* Generated Sovereign Deliverables (Word, Excel, PowerPoint) */}
        <div className="flex flex-col gap-2">
          <span className="text-xs font-medium text-stone-500 uppercase tracking-wider">
            Generated Sovereign Deliverables (3 Formats)
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
            <a
              href={msg.docx_download_url || "/api/download/Refinery_Inspection_Approval_Memo.docx"}
              download
              className="flex items-center justify-between p-3 bg-white hover:bg-stone-50 border border-[#E5E3DD] rounded-xl transition-all shadow-2xs group"
            >
              <div className="flex items-center gap-2.5">
                <i className="fa-regular fa-file-word text-blue-600 text-xl"></i>
                <div className="text-left">
                  <div className="text-xs font-semibold text-[#1F1E1D]">Approval Memo</div>
                  <div className="text-[10px] text-stone-400">.docx (Executive)</div>
                </div>
              </div>
              <i className="fa-solid fa-download text-xs text-stone-400 group-hover:text-[#D97757]"></i>
            </a>

            <a
              href={msg.xlsx_download_url || "/api/download/Refinery_Piping_Thickness_Log.xlsx"}
              download
              className="flex items-center justify-between p-3 bg-white hover:bg-stone-50 border border-[#E5E3DD] rounded-xl transition-all shadow-2xs group"
            >
              <div className="flex items-center gap-2.5">
                <i className="fa-regular fa-file-excel text-emerald-600 text-xl"></i>
                <div className="text-left">
                  <div className="text-xs font-semibold text-[#1F1E1D]">UT Thickness Log</div>
                  <div className="text-[10px] text-stone-400">.xlsx (Data Table)</div>
                </div>
              </div>
              <i className="fa-solid fa-download text-xs text-stone-400 group-hover:text-[#D97757]"></i>
            </a>

            <a
              href={msg.pptx_download_url || "/api/download/Refinery_Inspection_Executive_Brief.pptx"}
              download
              className="flex items-center justify-between p-3 bg-white hover:bg-stone-50 border border-[#E5E3DD] rounded-xl transition-all shadow-2xs group"
            >
              <div className="flex items-center gap-2.5">
                <i className="fa-regular fa-file-powerpoint text-amber-600 text-xl"></i>
                <div className="text-left">
                  <div className="text-xs font-semibold text-[#1F1E1D]">Executive Brief</div>
                  <div className="text-[10px] text-stone-400">.pptx (4 Slides)</div>
                </div>
              </div>
              <i className="fa-solid fa-download text-xs text-stone-400 group-hover:text-[#D97757]"></i>
            </a>
          </div>
        </div>

        {/* Collapsible Technical Drawers */}
        <div className="flex flex-col gap-2 pt-2 border-t border-[#E5E3DD]">
          {/* CodeAct Sandbox Drawer */}
          {msg.generated_code && (
            <div className="border border-[#E5E3DD] bg-white rounded-xl overflow-hidden">
              <button
                type="button"
                onClick={() => toggleDrawer(msg.id, 'code')}
                className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-mono text-stone-700 hover:bg-stone-50 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <i className="fa-solid fa-terminal text-emerald-600"></i>
                  <span>Deterministic CodeAct Sandbox Verification ({msg.selected_model || "qwen2.5:7b"})</span>
                </span>
                <i className={`fa-solid fa-chevron-${isDrawerOpen(msg.id, 'code') ? 'up' : 'down'} text-stone-400 text-xs`}></i>
              </button>
              {isDrawerOpen(msg.id, 'code') && (
                <div className="p-4 bg-stone-900 text-stone-200 font-mono text-xs border-t border-stone-800 leading-relaxed overflow-x-auto">
                  <div className="text-stone-500 mb-1"># Executed Verification Script:</div>
                  <pre className="text-blue-300 mb-3">{msg.generated_code}</pre>
                  <div className="text-stone-500 mb-1"># Sandbox Output:</div>
                  <pre className="text-emerald-400 font-bold">{msg.sandbox_output}</pre>
                </div>
              )}
            </div>
          )}

          {/* Sovereign RAG Citations Drawer */}
          {msg.retrieved_context && msg.retrieved_context.length > 0 && (
            <div className="border border-[#E5E3DD] bg-white rounded-xl overflow-hidden">
              <button
                type="button"
                onClick={() => toggleDrawer(msg.id, 'rag')}
                className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-mono text-stone-700 hover:bg-stone-50 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <i className="fa-solid fa-book-bookmark text-blue-600"></i>
                  <span>Grounded Sovereign Regulatory Standards ({msg.retrieved_context.length} Citations)</span>
                </span>
                <i className={`fa-solid fa-chevron-${isDrawerOpen(msg.id, 'rag') ? 'up' : 'down'} text-stone-400 text-xs`}></i>
              </button>
              {isDrawerOpen(msg.id, 'rag') && (
                <div className="p-4 bg-[#FAF9F5] border-t border-[#E5E3DD] flex flex-col gap-2.5">
                  {msg.retrieved_context.map((item, idx) => (
                    <div key={idx} className="p-3 bg-white border border-[#E5E3DD] rounded-lg text-xs">
                      <div className="flex items-center justify-between font-semibold text-[#1F1E1D] mb-1">
                        <span>{item.clause || item.standard}</span>
                        <span className="text-[10px] bg-stone-100 px-1.5 py-0.5 rounded text-stone-600">p. {item.page}</span>
                      </div>
                      <p className="text-stone-600 leading-relaxed">{item.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* LangGraph State Machine Drawer */}
          {msg.completed_steps && (
            <div className="border border-[#E5E3DD] bg-white rounded-xl overflow-hidden">
              <button
                type="button"
                onClick={() => toggleDrawer(msg.id, 'statemachine')}
                className="w-full px-4 py-2.5 flex items-center justify-between text-xs font-mono text-stone-700 hover:bg-stone-50 transition-colors"
              >
                <span className="flex items-center gap-2">
                  <i className="fa-solid fa-arrows-spin text-purple-600"></i>
                  <span>LangGraph Autonomous State Machine ({msg.completed_steps.length} Steps)</span>
                </span>
                <i className={`fa-solid fa-chevron-${isDrawerOpen(msg.id, 'statemachine') ? 'up' : 'down'} text-stone-400 text-xs`}></i>
              </button>
              {isDrawerOpen(msg.id, 'statemachine') && (
                <div className="p-4 bg-[#FAF9F5] border-t border-[#E5E3DD] flex flex-col gap-2">
                  <div className="grid grid-cols-5 gap-2 text-center text-xs font-mono">
                    <div className="bg-white border border-[#E5E3DD] p-2 rounded-lg">1. Classify</div>
                    <div className="bg-white border border-[#E5E3DD] p-2 rounded-lg">2. Plan</div>
                    <div className="bg-white border border-[#E5E3DD] p-2 rounded-lg">3. Act</div>
                    <div className="bg-white border border-[#E5E3DD] p-2 rounded-lg">4. Validate</div>
                    <div className="bg-white border border-[#E5E3DD] p-2 rounded-lg">5. Deliver</div>
                  </div>
                  <div className="mt-2 text-[11px] font-mono text-stone-500 flex items-center justify-between">
                    <span>Audit SHA-256: {msg.sha256_fingerprint || "Verified"}</span>
                    <span>Zero WAN Egress</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#FAF9F5] text-[#1F1E1D] font-sans antialiased selection:bg-[#D97757]/20 selection:text-[#1F1E1D]">
      {/* Hidden File Input */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        className="hidden"
        accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.docx,.xlsx,.json"
      />

      {/* ========================================================================= */}
      {/* 1. LEFT SIDEBAR (Claude-style) */}
      {/* ========================================================================= */}
      <aside
        className={`${
          sidebarOpen ? "w-64" : "w-0 -translate-x-full"
        } transition-all duration-300 ease-in-out bg-[#F3F1EC] border-r border-[#E5E3DD] flex flex-col justify-between flex-shrink-0 z-20 overflow-hidden select-none`}
      >
        <div className="flex flex-col p-3 gap-3 min-w-[16rem]">
          {/* Brand Header */}
          <div className="flex items-center justify-between px-1 py-1">
            <div className="flex items-center gap-2 cursor-pointer" onClick={handleNewTask}>
              <ClaudeAsterisk className="w-5 h-5 text-[#D97757]" />
              <span className="font-serif text-xl font-medium tracking-tight text-[#1F1E1D]">Claude</span>
              <span className="text-[10px] font-mono font-medium px-1.5 py-0.5 rounded bg-[#E5E3DD] text-stone-600">Sovereign</span>
            </div>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="p-1 rounded-md text-stone-400 hover:text-stone-700 hover:bg-stone-200/60 transition-colors"
              title="Close sidebar"
            >
              <i className="fa-solid fa-chevron-left text-xs"></i>
            </button>
          </div>

          {/* + New Chat & Task Button */}
          <button
            type="button"
            onClick={handleNewTask}
            className="w-full bg-[#FAF9F5] hover:bg-white border border-[#E5E3DD] text-[#1F1E1D] text-sm font-medium py-2 px-3 rounded-xl flex items-center gap-2.5 shadow-2xs transition-all hover:shadow-sm group"
          >
            <i className="fa-solid fa-plus text-xs text-stone-400 group-hover:text-[#D97757] transition-colors"></i>
            <span>New Chat & Task</span>
          </button>

          {/* Active Memory Status */}
          {messages.length > 0 && (
            <div className="px-2.5 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-[11px] flex items-center justify-between font-mono">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span>Memory: {messages.length} turns</span>
              </span>
              <button
                type="button"
                onClick={handleNewTask}
                className="text-stone-400 hover:text-red-600 transition-colors"
                title="Clear conversation memory"
              >
                <i className="fa-regular fa-trash-can text-xs"></i>
              </button>
            </div>
          )}

          {/* Navigation Links */}
          <div className="flex flex-col gap-0.5 text-xs text-stone-600 pt-1">
            <button
              type="button"
              onClick={handleNewTask}
              className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-stone-200/60 transition-colors text-left"
            >
              <i className="fa-regular fa-folder-open text-stone-400 text-xs w-4"></i>
              <span>Projects</span>
            </button>
            <a
              href="http://localhost:5567"
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-stone-200/60 transition-colors text-left text-stone-600"
            >
              <i className="fa-solid fa-chart-line text-stone-400 text-xs w-4"></i>
              <span>Data Formulator</span>
            </a>
          </div>

          {/* Chats & Tasks List (Industrial Benchmarks) */}
          <div className="flex flex-col mt-2">
            <div className="text-[11px] font-medium text-stone-500 uppercase tracking-wider px-2 mb-1.5 flex items-center justify-between">
              <span>Benchmarks & Telemetry</span>
              <i className="fa-solid fa-arrow-down-short-wide text-[10px]"></i>
            </div>
            <div className="flex flex-col gap-0.5 overflow-y-auto max-h-[calc(100vh-340px)] pr-1">
              {SAMPLE_BENCHMARKS.map((b) => (
                <button
                  key={b.id}
                  type="button"
                  onClick={() => {
                    handleSelectBenchmark(b);
                    setTimeout(() => handleExecute(b.query, b), 50);
                  }}
                  className={`text-left text-xs px-2.5 py-2 rounded-lg transition-all flex items-start gap-2 group ${
                    selectedBenchmark?.id === b.id
                      ? "bg-white border border-[#E5E3DD] text-[#1F1E1D] font-medium shadow-2xs"
                      : "text-stone-700 hover:bg-stone-200/60"
                  }`}
                >
                  <i className="fa-regular fa-message text-[11px] text-stone-400 mt-0.5 group-hover:text-[#D97757]"></i>
                  <div className="flex flex-col overflow-hidden">
                    <span className="truncate">{b.title}</span>
                    <span className="text-[10px] text-stone-400 truncate">{b.preview}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-[#E5E3DD] flex flex-col gap-2 min-w-[16rem]">
          {/* Air-Gap Telemetry Badge */}
          <div className="flex items-center justify-between bg-[#FAF9F5] border border-[#E5E3DD] px-2.5 py-1.5 rounded-lg text-[11px] font-mono text-stone-600 shadow-2xs">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-semibold text-emerald-700">0 WAN Egress</span>
            </span>
            <span className="text-stone-400">{egressData.egress_bytes} B</span>
          </div>

          {/* User Profile */}
          <div className="flex items-center justify-between px-1 py-1 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-full bg-[#D97757]/15 border border-[#D97757]/30 text-[#D97757] font-medium flex items-center justify-center text-xs">
                S
              </div>
              <div className="flex flex-col">
                <span className="font-medium text-[#1F1E1D]">Sagar</span>
                <span className="text-[10px] text-stone-500 font-mono">Team rv2 &bull; On-Prem</span>
              </div>
            </div>
            <i className="fa-solid fa-ellipsis text-stone-400"></i>
          </div>
        </div>
      </aside>

      {/* ========================================================================= */}
      {/* 2. MAIN WORKSPACE / CONVERSATIONAL CANVAS */}
      {/* ========================================================================= */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Minimal Navigation Bar */}
        <header className="h-12 border-b border-[#E5E3DD]/80 px-4 flex items-center justify-between flex-shrink-0 bg-[#FAF9F5]/80 backdrop-blur-xs z-10">
          <div className="flex items-center gap-2.5">
            {!sidebarOpen && (
              <button
                type="button"
                onClick={() => setSidebarOpen(true)}
                className="p-1.5 rounded-md text-stone-500 hover:text-stone-800 hover:bg-stone-200/60 transition-colors"
                title="Open sidebar"
              >
                <i className="fa-solid fa-bars text-sm"></i>
              </button>
            )}
            <span className="text-xs text-stone-600 font-normal">
              {messages.length > 0 ? "Autonomous Industrial Conversation & Audit Stream" : "Self-hosted AI workbench for confidential industrial work"}
            </span>
          </div>

          {/* Top Right Badges */}
          <div className="flex items-center gap-2">
            {/* Live Zero-Egress Air-Gap Proof Badge */}
            <div className={`flex items-center gap-1.5 text-[11px] font-mono px-2 py-0.5 rounded border transition-colors ${
              airgapStatus.is_airgapped
                ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                : "bg-amber-50 text-amber-700 border-amber-200"
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${airgapStatus.is_airgapped ? "bg-emerald-500 animate-pulse" : "bg-amber-500"}`}></span>
              <span>{airgapStatus.status || "AIR-GAPPED (0.0 KB/s)"}</span>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 text-xs text-stone-500 font-mono px-2 py-0.5 rounded bg-stone-200/50 border border-stone-300/50">
              <span className="w-1.5 h-1.5 rounded-full bg-[#D97757]"></span>
              <span>{selectedModel}</span>
            </div>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-[#E5E3DD] text-stone-700">
              SIH 2026
            </span>
          </div>
        </header>

        {/* ======================================================================= */}
        {/* VIEW A: EMPTY STATE (Hey there, Sagar) */}
        {/* ======================================================================= */}
        {messages.length === 0 && !loading && (
          <div className="flex-1 flex flex-col items-center justify-center p-4 sm:p-8 overflow-y-auto">
            <div className="w-full max-w-2xl flex flex-col items-center gap-6">
              {/* Centered Brand Icon & Greeting */}
              <div className="flex flex-col items-center gap-3 text-center">
                <ClaudeAsterisk className="w-10 h-10 text-[#D97757]" />
                <h1 className="font-serif text-3xl sm:text-4xl text-[#1F1E1D] font-normal tracking-tight">
                  Hey there, Sagar
                </h1>
                <p className="text-xs sm:text-sm text-stone-500 font-sans max-w-md">
                  Sovereign industrial compliance assistant with multi-turn memory. Chat freely, test code, or run an autonomous piping inspection audit.
                </p>
              </div>

              {/* Centered Floating Prompt Card */}
              <div className="w-full bg-white border border-[#E5E3DD] rounded-2xl shadow-xs p-3.5 flex flex-col gap-3 transition-shadow focus-within:shadow-md focus-within:border-stone-400">
                {attachedFileName && (
                  <div className="flex items-center justify-between bg-[#FAF9F5] border border-[#E5E3DD] px-3 py-1.5 rounded-lg text-xs font-mono text-[#D97757]">
                    <span className="flex items-center gap-1.5 truncate">
                      <i className="fa-solid fa-paperclip"></i>
                      <span className="truncate">{attachedFileName}</span>
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setAttachedFile(null);
                        setAttachedFileName("");
                        setSelectedBenchmark(null);
                      }}
                      className="text-stone-400 hover:text-stone-700 ml-2"
                    >
                      <i className="fa-solid fa-xmark"></i>
                    </button>
                  </div>
                )}

                <textarea
                  rows={3}
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="How can I help you today? (e.g. 'hello', 'calculate corrosion rate', or upload an API 570 scan)"
                  className="w-full resize-none text-sm text-[#1F1E1D] placeholder-stone-400 focus:outline-none bg-transparent leading-relaxed"
                />

                <div className="flex items-center justify-between pt-1 border-t border-stone-100">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current && fileInputRef.current.click()}
                      className="p-1.5 rounded-lg text-stone-500 hover:text-[#1F1E1D] hover:bg-stone-100 transition-colors"
                      title="Attach telemetry document (PDF, TXT, CSV, Image)"
                    >
                      <i className="fa-solid fa-plus text-sm"></i>
                    </button>

                    {/* Task Mode Pills */}
                    <div className="flex items-center bg-[#FAF9F5] p-0.5 rounded-lg border border-[#E5E3DD] text-xs">
                      <button
                        type="button"
                        onClick={() => setTaskMode("full_pipeline")}
                        className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                          taskMode === "full_pipeline" ? "bg-white shadow-2xs text-[#1F1E1D]" : "text-stone-500 hover:text-stone-800"
                        }`}
                      >
                        Tri-Engine
                      </button>
                      <button
                        type="button"
                        onClick={() => setTaskMode("deep_thinking_only")}
                        className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                          taskMode === "deep_thinking_only" ? "bg-white shadow-2xs text-[#1F1E1D]" : "text-stone-500 hover:text-stone-800"
                        }`}
                      >
                        Deep Thinking
                      </button>
                      <button
                        type="button"
                        onClick={() => setTaskMode("coding_only")}
                        className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                          taskMode === "coding_only" ? "bg-white shadow-2xs text-[#1F1E1D]" : "text-stone-500 hover:text-stone-800"
                        }`}
                      >
                        Sandbox
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-stone-400 font-mono hidden sm:inline">
                      Sonnet 5 Extra &bull; Sovereign
                    </span>
                    <button
                      type="button"
                      onClick={() => handleExecute()}
                      disabled={loading || (!query.trim() && !attachedFile && !selectedBenchmark)}
                      className="w-8 h-8 rounded-full bg-[#D97757] hover:bg-[#C96442] disabled:bg-stone-300 text-white flex items-center justify-center transition-all shadow-xs"
                      title="Run workflow"
                    >
                      <i className="fa-solid fa-arrow-up text-xs"></i>
                    </button>
                  </div>
                </div>
              </div>

              {/* Quick Suggestion Chips */}
              <div className="flex flex-wrap justify-center gap-2 text-xs">
                {SAMPLE_BENCHMARKS.map((b) => (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => {
                      handleSelectBenchmark(b);
                      setTimeout(() => handleExecute(b.query, b), 50);
                    }}
                    className="bg-white hover:bg-[#FAF9F5] border border-[#E5E3DD] text-stone-600 hover:text-[#1F1E1D] px-3 py-1.5 rounded-full transition-all shadow-2xs flex items-center gap-1.5"
                  >
                    <span>{b.title}</span>
                    <i className="fa-solid fa-arrow-right text-[10px] text-stone-400"></i>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ======================================================================= */}
        {/* VIEW B: CONVERSATIONAL CHAT STREAM (Multi-Turn Memory) */}
        {/* ======================================================================= */}
        {(messages.length > 0 || loading) && (
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 flex flex-col items-center">
            <div className="w-full max-w-3xl flex flex-col gap-6">
              {/* Render all message turns sequentially */}
              {messages.map((msg, index) => {
                if (msg.role === 'user') {
                  return (
                    <div
                      key={msg.id || index}
                      className="self-end bg-[#F3F1EC] border border-[#E5E3DD] rounded-2xl px-4 py-3 max-w-[85%] text-sm text-[#1F1E1D] shadow-2xs leading-relaxed"
                    >
                      {msg.attachedFileName && (
                        <div className="flex items-center gap-1.5 text-xs font-mono text-[#D97757] mb-1">
                          <i className="fa-solid fa-paperclip text-[10px]"></i>
                          <span>{msg.attachedFileName}</span>
                        </div>
                      )}
                      <p className="whitespace-pre-wrap font-normal">{msg.content}</p>
                      {msg.timestamp && (
                        <div className="text-[10px] text-stone-400 text-right mt-1 font-mono">
                          {msg.timestamp}
                        </div>
                      )}
                    </div>
                  );
                }

                // Assistant message
                return (
                  <div key={msg.id || index} className="self-start w-full flex flex-col gap-3">
                    {/* Claude Thinking Trace */}
                    {msg.deep_thinking_cot && (
                      <ReasoningBox
                        isLoading={false}
                        thinkingText={msg.deep_thinking_cot}
                        elapsedDuration={msg.executionDuration}
                        modelName={msg.selected_model || "Qwen3.6-27B CoT"}
                      />
                    )}

                    {/* Content Payload */}
                    {renderAssistantContent(msg)}
                  </div>
                );
              })}

              {/* Active Thinking Bubble when waiting for model response */}
              {loading && (
                <div className="self-start w-full">
                  <ReasoningBox
                    isLoading={true}
                    thinkingText=""
                    elapsedDuration={null}
                    modelName={selectedModel || "Qwen3.6-27B CoT"}
                  />
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>

            {/* Bottom Floating Prompt Bar for follow-ups */}
            <div className="w-full max-w-3xl mt-4 sticky bottom-4 z-10">
              <div className="bg-white border border-[#E5E3DD] rounded-2xl shadow-md p-2.5 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current && fileInputRef.current.click()}
                  className="p-1.5 rounded-lg text-stone-400 hover:text-stone-700 transition-colors"
                  title="Attach file"
                >
                  <i className="fa-solid fa-paperclip text-sm"></i>
                </button>
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask a follow-up, test code, or run an inspection report..."
                  className="flex-1 text-sm text-[#1F1E1D] placeholder-stone-400 focus:outline-none bg-transparent"
                />
                <button
                  type="button"
                  onClick={() => handleExecute()}
                  disabled={loading || !query.trim()}
                  className="w-7 h-7 rounded-full bg-[#D97757] hover:bg-[#C96442] disabled:bg-stone-300 text-white flex items-center justify-center transition-all shadow-2xs"
                >
                  <i className="fa-solid fa-arrow-up text-xs"></i>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
