import React, { useState, useEffect, useRef } from 'react';

/**
 * Authentic Claude-style Asterisk / Sunburst Icon
 * Matches Claude's signature terracotta #D97757 radiating 14-spoke emblem.
 */
export function ClaudeAsterisk({ className = "w-4 h-4", spinning = false }) {
  return (
    <svg
      className={`${className} ${spinning ? "animate-spin-slow" : ""}`}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      <circle cx="12" cy="12" r="1.6" fill="#D97757" />
      {[
        0, 25.7, 51.4, 77.1, 102.8, 128.5, 154.2,
        180, 205.7, 231.4, 257.1, 282.8, 308.5, 334.2
      ].map((deg, i) => {
        const isLong = i % 2 === 0;
        return (
          <line
            key={i}
            x1="12"
            y1={isLong ? "2.2" : "3.8"}
            x2="12"
            y2="7.8"
            stroke="#D97757"
            strokeWidth="2.2"
            strokeLinecap="round"
            transform={`rotate(${deg} 12 12)`}
          />
        );
      })}
    </svg>
  );
}

// Realistic rotating thinking phrases matching Claude's CoT & our sovereign agent pipeline
const THINKING_PHASES = [
  "Crystallizing",
  "Pondering",
  "Reading telemetry data",
  "Analyzing ultrasonic scan points",
  "Cross-referencing API 570 & ASME B31.3",
  "Evaluating localized corrosion rates",
  "Computing retirement thickness thresholds",
  "Executing deterministic CodeAct sandbox",
  "Validating wall loss calculations",
  "Synthesizing executive memo",
];

/**
 * Claude-style Thinking Component
 * Supports both active thinking (while workflow runs) and completed state (showing "Thought for Xs").
 * Clicking expands/collapses the thinking thoughts trace inline.
 */
export default function ReasoningBox({
  thinkingText = "",
  isLoading = false,
  elapsedDuration = null,
  modelName = "Qwen3.6-27B CoT",
  defaultExpanded = false
}) {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [phaseIndex, setPhaseIndex] = useState(0);
  const [copied, setCopied] = useState(false);
  const contentRef = useRef(null);
  const startTimeRef = useRef(Date.now());

  // Timer & Phase Rotation while active
  useEffect(() => {
    if (isLoading) {
      startTimeRef.current = Date.now();
      setElapsedTime(0);
      setPhaseIndex(0);

      const timerInterval = setInterval(() => {
        setElapsedTime(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }, 1000);

      const phaseInterval = setInterval(() => {
        setPhaseIndex((prev) => (prev + 1) % THINKING_PHASES.length);
      }, 2400);

      return () => {
        clearInterval(timerInterval);
        clearInterval(phaseInterval);
      };
    } else if (elapsedDuration !== null && elapsedDuration !== undefined) {
      setElapsedTime(elapsedDuration);
    }
  }, [isLoading, elapsedDuration]);

  // Auto-scroll when expanded and receiving new text
  useEffect(() => {
    if (isExpanded && contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [thinkingText, isExpanded]);

  const handleCopy = (e) => {
    e.stopPropagation();
    if (thinkingText) {
      navigator.clipboard.writeText(thinkingText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const finalSeconds = elapsedDuration ?? Math.max(elapsedTime, 3);

  return (
    <div className="w-full my-2 font-sans select-none">
      {/* Inline Claude-style Header Button */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="group inline-flex items-center gap-2 text-[14px] text-stone-700 hover:text-stone-900 transition-all py-1 px-1 rounded hover:bg-stone-200/50 cursor-pointer focus:outline-none"
        title={isExpanded ? "Click to collapse thoughts" : "Click to view thoughts"}
      >
        {/* Claude Terracotta Asterisk Icon */}
        <ClaudeAsterisk className="w-4 h-4" spinning={isLoading} />

        {/* Phase Text or Completed "Thought for Xs" */}
        <span className="font-normal text-stone-700">
          {isLoading ? (
            <span>{THINKING_PHASES[phaseIndex]}</span>
          ) : (
            <span>Thought for {finalSeconds} seconds</span>
          )}
        </span>

        {/* Muted Timer (while active) */}
        {isLoading && (
          <span className="text-stone-400 font-mono text-xs">
            {elapsedTime}s
          </span>
        )}

        {/* Small Subtle Right / Down Chevron */}
        <span
          className={`text-stone-400 group-hover:text-stone-600 text-xs transition-transform duration-200 ${
            isExpanded ? "rotate-90" : ""
          }`}
        >
          ›
        </span>
      </button>

      {/* Expandable Thoughts Drawer */}
      {isExpanded && (
        <div className="mt-2.5 ml-2 pl-3.5 border-l-2 border-stone-300 transition-all duration-300">
          <div className="bg-[#FAF9F5] border border-stone-200 rounded-xl overflow-hidden shadow-sm">
            {/* Drawer Header */}
            <div className="flex items-center justify-between px-3.5 py-2 bg-stone-100/70 border-b border-stone-200 text-[11px] font-mono text-stone-500">
              <span className="flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#D97757]"></span>
                <span className="font-medium text-stone-700">{modelName} Reasoning Trace</span>
                {thinkingText && (
                  <span className="text-stone-400">
                    ({thinkingText.length.toLocaleString()} chars)
                  </span>
                )}
              </span>

              {thinkingText && (
                <button
                  type="button"
                  onClick={handleCopy}
                  className="hover:text-stone-800 transition-colors flex items-center gap-1 text-[11px]"
                >
                  <i className={`fa-solid ${copied ? "fa-check text-emerald-600" : "fa-copy"}`}></i>
                  <span>{copied ? "Copied" : "Copy"}</span>
                </button>
              )}
            </div>

            {/* Thoughts Body */}
            <div
              ref={contentRef}
              className="p-4 font-mono text-xs text-stone-700 bg-white max-h-80 overflow-y-auto leading-relaxed whitespace-pre-wrap select-text scroll-smooth"
            >
              {thinkingText ? (
                thinkingText
              ) : isLoading ? (
                <div className="flex flex-col gap-1.5 text-stone-500 text-[11px]">
                  <div className="flex items-center gap-2 text-[#D97757]">
                    <i className="fa-solid fa-spinner fa-spin text-xs"></i>
                    <span>Actively evaluating engineering constraints...</span>
                  </div>
                  <div className="text-stone-500 pl-4 border-l border-stone-200 mt-1">
                    <div>&bull; Grounding regulatory clauses via local ChromaDB RAG</div>
                    <div>&bull; Formulating deterministic CodeAct Python script</div>
                    <div>&bull; Checking T_actual against T_threshold</div>
                  </div>
                </div>
              ) : (
                <span className="text-stone-400 italic">No reasoning trace generated for this step.</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
