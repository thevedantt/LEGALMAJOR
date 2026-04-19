'use client';
import { useState, useRef } from "react";
import { FileUpload } from "@/components/ui/file-upload";
import ActionButtons from "@/components/ActionButtons";
import AskInput from "@/components/AskInput";
import OutputCard from "@/components/OutputCard";

export default function Home() {
  const [docId, setDocId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [filename, setFilename] = useState<string | null>(null);
  const [active, setActive] = useState<'ask' | 'summarize' | 'analyze' | 'overallRisk' | 'fairness' | 'conflicts' | 'clauses' | 'suggestions'>('ask');
  const [question, setQuestion] = useState('');
  const [clauseQuery, setClauseQuery] = useState('');
  const [latency, setLatency] = useState<string | null>(null);
  const [output, setOutput] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setOutput(null);
    if (!fileInputRef.current || !fileInputRef.current.files?.length) {
      setError("Please select a PDF file to upload.");
      return;
    }
    setUploading(true);
    const file = fileInputRef.current.files[0];
    setFilename(file.name);
    const data = new FormData();
    data.append("file", file);
    try {
      const res = await fetch("/api/upload", {
        method: "POST",
        body: data,
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || "Upload failed");
      } else {
        const body = await res.json();
        setDocId(body.doc_id);
        setError(null);
      }
    } catch {
      setError("Network or server error during upload.");
    } finally {
      setUploading(false);
    }
  };

  // Unified handler for the three actions
  const handleAction = async (which: 'ask' | 'summarize' | 'analyze' | 'overallRisk' | 'fairness' | 'conflicts' | 'clauses' | 'suggestions', customQuestion?: string) => {
    setActive(which);
    setError(null);
    setOutput(null);
    setLatency(null);
    if (!docId) {
      setError("Please upload a PDF first.");
      return;
    }
    setLoading(true);
    const start = performance.now();
    let endpoint = "/api/ask";
    let payload: any = { doc_id: docId };
    if (which === "ask") {
      endpoint = "/api/ask";
      payload.question = customQuestion ?? question;
    } else if (which === "summarize") {
      endpoint = "/api/summarize";
      payload.query = "";
    } else if (which === "analyze") {
      endpoint = "/api/analyze-risk";
    } else if (which === "overallRisk") {
      endpoint = "/api/overall-risk";
    } else if (which === "fairness") {
      endpoint = "/api/fairness";
    } else if (which === "conflicts") {
      endpoint = "/api/check-conflicts";
    } else if (which === "clauses") {
      endpoint = "/api/extract-clauses";
    } else if (which === "suggestions") {
      endpoint = "/api/suggest-improvements";
    }
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || "Query failed");
      } else {
        const body = await res.json();
        setOutput(body);
      }
      const end = performance.now();
      setLatency(((end - start) / 1000).toFixed(2));
    } catch {
      setError("Network or server error during query.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen py-10 px-3 bg-[#b3e5fc] relative">
      <div className="absolute top-5 right-5 bg-[#c1121f] text-white px-3 py-1 rounded-md text-sm font-semibold">
        ⚡ {loading ? '...' : (latency ? `${latency}s` : '0.00s')}
      </div>
      {/* Header Section */}
      <div className="mb-8 text-center">
        <h1 className="text-3xl font-bold text-[#c1121f] mb-2">Legal Contract Analyzer</h1>
        <p className="text-lg text-[#c1121f]">Upload, analyze, and understand contracts instantly</p>
      </div>
      <div className="flex flex-1 w-full max-w-6xl mx-auto gap-8">
        {/* Left Panel: Upload + Actions */}
        <div className="w-[40%] flex flex-col">
          <div className="bg-[#c1121f] rounded-2xl p-6 flex flex-col min-h-[520px]">
            <div className="min-h-56 border border-dashed border-white bg-[#b3e5fc] rounded-lg flex flex-col items-center justify-center p-6 mb-5">
              <FileUpload
                onChange={async (files: File[]) => {
                  setError(null);
                  setOutput(null);
                  if (!files || files.length === 0) {
                    setError("Please select a PDF file to upload.");
                    return;
                  }
                  setUploading(true);
                  const file = files[0];
                  setFilename(file.name);
                  const data = new FormData();
                  data.append("file", file);
                  try {
                    const res = await fetch("/api/upload", {
                      method: "POST",
                      body: data,
                    });
                    if (!res.ok) {
                      const err = await res.json();
                      setError(err.detail || "Upload failed");
                    } else {
                      const body = await res.json();
                      setDocId(body.doc_id);
                      setError(null);
                    }
                  } catch {
                    setError("Network or server error during upload.");
                  } finally {
                    setUploading(false);
                  }
                }}
              />
              {filename && <div className="mt-2 text-xs text-[#c1121f]">File: <span className="font-medium">{filename}</span></div>}
              {docId && <span className="mt-2 inline-block bg-[#c1121f] text-white text-xs px-2 py-1 rounded">ID: {docId}</span>}
              {error && <div className="mt-2 text-[#c1121f] font-semibold text-center">{error}</div>}
            </div>
            {active === 'ask' && (
              <AskInput
                question={question}
                setQuestion={setQuestion}
                onAsk={(e: React.FormEvent) => {
                  e.preventDefault();
                  handleAction('ask');
                }}
                loading={loading}
                disabled={!docId || uploading}
              />
            )}
          </div>
          <div className="mt-6">
            <ActionButtons
              onAsk={() => handleAction('ask')}
              onSummarize={() => handleAction('summarize')}
              onAnalyze={() => handleAction('analyze')}
              onOverallRisk={() => handleAction('overallRisk')}
              onFairness={() => handleAction('fairness')}
              onConflicts={() => handleAction('conflicts')}
              onClauses={() => handleAction('clauses')}
              onSuggestImprovements={() => handleAction('suggestions')}
              onDownloadReport={async () => {
                if (!docId) {
                  setError('Please upload a PDF first.');
                  return;
                }
                setLoading(true);
                try {
                  const res = await fetch('/api/generate-report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ doc_id: docId }),
                  });
                  if (!res.ok) {
                    const err = await res.json();
                    setError(err.detail || 'Report generation failed');
                  } else {
                    const blob = await res.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `contract_report_${docId}.pdf`;
                    a.click();
                    window.URL.revokeObjectURL(url);
                  }
                } catch {
                  setError('Network or server error during report generation.');
                } finally {
                  setLoading(false);
                }
              }}
              disabled={!docId || uploading || loading}
              active={active}
            />
          </div>
        </div>
        {/* Right Panel: Clause Dashboard */}
        <div className="w-[60%] flex flex-col">
          <div className="w-full bg-[#c1121f] rounded-2xl p-6 min-h-[520px]">
            <input
              className="w-full px-4 py-2 rounded-md border border-[#c1121f] bg-[#b3e5fc] text-[#c1121f] placeholder:text-[#c1121f] focus:outline-none focus:border-[#c1121f]"
              placeholder="Search clauses..."
              value={clauseQuery}
              onChange={(e) => setClauseQuery(e.target.value)}
            />
            <div className="mt-6">
              {!docId && !loading && !error && (
                <div className="text-white text-center font-semibold">Upload a contract to begin analysis.</div>
              )}
              {docId && !loading && !error && !output && (
                <div className="text-white text-center font-semibold">
                  Start by summarizing or analyzing the contract.
                </div>
              )}
              <OutputCard
                mode={active}
                data={active === 'clauses' && clauseQuery && Array.isArray(output)
                  ? output.filter((c: any) =>
                      (c.text || '').toLowerCase().includes(clauseQuery.toLowerCase()) ||
                      (c.type || '').toLowerCase().includes(clauseQuery.toLowerCase()) ||
                      (c.section || '').toLowerCase().includes(clauseQuery.toLowerCase())
                    )
                  : output}
                loading={loading}
                error={error}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
