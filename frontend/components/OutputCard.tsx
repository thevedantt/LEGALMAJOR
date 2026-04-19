import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

function RiskLevelBadge({ risk }: { risk: string }) {
  let display = String(risk || '').toUpperCase();
  let base = 'inline-block px-6 py-2 rounded-lg font-bold uppercase mb-2';
  if (display === 'HIGH')
    return <span className={`${base} text-white text-2xl bg-[#c1121f] border border-white shadow-xl`} style={{letterSpacing:2}}>High</span>;
  if (display === 'MEDIUM')
    return <span className={`${base} text-white text-2xl`} style={{ background:'#c1121f80', border:'2px solid #fff'}}>Medium</span>;
  if (display === 'LOW')
    return <span className={`${base} text-[#c1121f] text-2xl bg-[#b3e5fc] border border-[#b3e5fc]`}>Low</span>;
  return <span className={`${base} text-white text-2xl bg-[#c1121f] border border-[#fff9]`}>{display}</span>;
}

interface OutputCardProps {
  mode: 'ask' | 'summarize' | 'analyze' | 'overallRisk' | 'fairness' | 'conflicts' | 'clauses' | 'suggestions';
  data: any;
  loading: boolean;
  error: string | null;
}

export default function OutputCard({ mode, data, loading, error }: OutputCardProps) {
  // Shared style for all result cards
  const cardClass = "w-full max-w-xl mx-auto mt-6 p-8 rounded-2xl bg-[#c1121f] text-white shadow-xl";
  if (loading) return (
    <Card className={cardClass + " flex flex-col min-h-32"}>
      <div className="mb-4 text-white font-semibold">Analyzing document...</div>
      <Skeleton className="h-6 w-full mb-2 bg-[#b3e5fc]" />
      <Skeleton className="h-6 w-4/5 mb-2 bg-[#b3e5fc]" />
      <Skeleton className="h-6 w-3/5 bg-[#b3e5fc]" />
    </Card>
  );
  if (error) return (
    <Card className={cardClass + " font-semibold text-center min-h-32"}>
      ❌ Something went wrong. Please try again.
    </Card>
  );
  if (!data) return null;

  if (mode === 'ask') {
    // Handle answer as either { answer: string } or just a string
    let answer = typeof data === 'object' && data !== null && 'answer' in data ? data.answer : data;
    if (typeof answer !== 'string') answer = '';
    return (
      <Card className={cardClass}>
        <h2 className="text-2xl font-bold mb-4 tracking-wide">Answer:</h2>
        <p className="text-lg whitespace-pre-line leading-relaxed text-white mb-2" style={{wordBreak:'break-word'}}>{answer}</p>
      </Card>
    );
  }
  if (mode === 'summarize') {
    let summaryRaw = (typeof data === 'object' && data !== null && 'summary' in data) ? data.summary : data;
    let points: string[] = [];
    if (typeof summaryRaw === 'string') {
      points = summaryRaw.split(/\n|•|\d+[\).]/).map(s => s.trim()).filter(Boolean);
    } else if (Array.isArray(summaryRaw)) {
      points = summaryRaw;
    }
    return (
      <Card className={cardClass}>
        <h2 className="text-2xl font-bold mb-4 tracking-wide">Summary:</h2>
        {points.length >= 2 ? (
          <ul className="list-disc pl-7 space-y-2">
            {points.map((point, i) => <li key={i} className="text-lg leading-snug text-white">{point}</li>)}
          </ul>
        ) : (
          <p className="text-lg leading-relaxed text-white whitespace-pre-line mb-2">{points[0] || 'No summary available.'}</p>
        )}
      </Card>
    );
  }
  if (mode === 'analyze') {
    let risk = (typeof data === 'object' && data !== null && 'overall_risk' in data)
      ? data.overall_risk
      : ((typeof data === 'object' && 'risk' in data) ? data.risk : 'Unknown');
    let pts: string[] = (typeof data === 'object' && data !== null && 'points' in data)
      ? data.points
      : [];
    if ((!pts.length) && typeof data === 'string') {
      pts = data.split(/\n|•|\d+[\).]/).filter(Boolean).slice(1);
    }
    return (
      <Card className={cardClass}>
        <h2 className="text-2xl font-bold mb-4 tracking-wide">Risk Analysis:</h2>
        <div className="flex flex-col items-start gap-2 mb-6">
          <RiskLevelBadge risk={risk} />
        </div>
        <ul className="list-disc pl-7 space-y-2">
          {pts.length ? pts.map((pt, i) => <li key={i} className="text-lg leading-snug text-white">{pt.trim()}</li>) : <li className="text-lg leading-snug text-white">No details found.</li>}
        </ul>
      </Card>
    );
  }
  // --- OVERALL RISK OUTPUT CARD ---
  if (mode === 'overallRisk') {
    // expects: { overall_risk, score, breakdown: { HIGH, MEDIUM, LOW } }
    const risk = data.overall_risk || 'Unknown';
    const score = typeof data.score === 'number' ? data.score : null;
    const breakdown = data.breakdown || {};
    const normalizedBreakdown = {
      HIGH: breakdown.HIGH ?? breakdown.High ?? 0,
      MEDIUM: breakdown.MEDIUM ?? breakdown.Medium ?? 0,
      LOW: breakdown.LOW ?? breakdown.Low ?? 0,
    };
    // For Pie: Compute totals and angles
    const ALL = ['HIGH', 'MEDIUM', 'LOW'];
    const total = ALL.map((k)=>normalizedBreakdown[k]||0).reduce((a,b)=>a+b,0)||1;
    const angles = ALL.map((k)=>{
      const val=(normalizedBreakdown[k]||0);
      return ((val/total)*360)
    });
    // Pie colors
    const PIE_COLORS = ['#c1121f','#c1121faa','#b3e5fc'];
    // SVG Pie generator (one ring, each slice)
    let accumAngle=0;
    const pieSlices = angles.map((angle, idx) => {
      const start = accumAngle;
      const end = accumAngle+angle;
      const large = angle > 180 ? 1 : 0;
      const r = 36, cx = 40, cy = 40;
      const x1 = cx + r * Math.cos(Math.PI * start/180);
      const y1 = cy + r * Math.sin(Math.PI * start/180);
      const x2 = cx + r * Math.cos(Math.PI * end/180);
      const y2 = cy + r * Math.sin(Math.PI * end/180);
      const path = `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z`;
      accumAngle += angle;
      return <path d={path} fill={PIE_COLORS[idx]} stroke="#fff" strokeWidth={2} key={idx}/>;
    });
    return (
      <Card className={cardClass}>
        <h2 className="text-2xl font-bold mb-4 tracking-wide">Overall Risk</h2>
        <div className="flex items-center justify-between gap-8 mb-6">
          <div className="w-20 h-20">
            <svg width={80} height={80} viewBox="0 0 80 80">{pieSlices}</svg>
            <div className="text-xs text-white font-semibold flex justify-between mt-1">
              <span className="inline-block w-2 h-2 rounded-full" style={{background:PIE_COLORS[0]}}></span> High
              <span className="inline-block w-2 h-2 rounded-full ml-3" style={{background:PIE_COLORS[1]}}></span> Med
              <span className="inline-block w-2 h-2 rounded-full ml-3" style={{background:PIE_COLORS[2]}}></span> Low
            </div>
          </div>
          <div className="flex flex-col items-center justify-center">
            <RiskLevelBadge risk={risk}/>
            {score !== null && (
              <div className="mt-2 px-4 py-1 rounded-full bg-[#b3e5fc] text-[#c1121f] font-bold text-lg">
                Score: {(score*100).toFixed(0)}
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-8 justify-between mt-2">
          {/* Breakdown by numbers */}
          {ALL.map((k)=>(<div key={k} className="flex flex-col items-center mx-3">
            <span className="text-sm font-semibold text-white">{k[0] + k.slice(1).toLowerCase()}</span>
            <span className="font-bold text-xl text-white">{normalizedBreakdown[k] ?? 0}</span>
          </div>))}
        </div>
      </Card>
    );
  }
  if (mode === 'fairness') {
    const rawFavors = data?.favors;
    let favors = 'Balanced';
    if (typeof rawFavors === 'string') {
      favors = rawFavors;
    } else if (rawFavors && typeof rawFavors === 'object') {
      if (rawFavors.Company) favors = 'Company';
      else if (rawFavors.Customer) favors = 'Customer';
      else if (rawFavors.Balanced) favors = 'Balanced';
    }
    const score = typeof data?.fairness_score === 'number' ? data.fairness_score : null;
    const reason = data?.reason || 'No reason provided.';
    return (
      <Card className={cardClass}>
        <h2 className="text-2xl font-bold mb-4 tracking-wide">Fairness</h2>
        <div className="flex items-center gap-4 mb-4">
          <Badge className="bg-white text-[#c1121f] text-lg font-bold px-4 py-1">Favors: {favors}</Badge>
          {score !== null && (
            <span className="text-white font-semibold">Score: {(score * 100).toFixed(0)}</span>
          )}
        </div>
        <p className="text-lg leading-relaxed text-white">{reason}</p>
      </Card>
    );
  }
  if (mode === 'conflicts') {
    const conflicts = data?.conflicts || [];
    return (
      <Card className={cardClass}>
        <h2 className="text-2xl font-bold mb-4 tracking-wide">Conflicts</h2>
        {conflicts.length ? (
          <ul className="list-disc pl-7 space-y-2">
            {conflicts.map((c: any, i: number) => (
              <li key={i} className="text-lg leading-snug text-white">
                <strong>{(c.clauses || []).join(' vs ')}</strong>: {c.reason}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-lg leading-relaxed text-white">No conflicts detected.</p>
        )}
      </Card>
    );
  }
  if (mode === 'clauses') {
    const clauses = Array.isArray(data) ? data : (data?.clauses || []);
    return (
      <Card className={cardClass + " p-6 rounded-2xl w-full"}>
        <h2 className="text-2xl font-bold mb-4 tracking-wide">Clause Breakdown</h2>
        <div className="max-h-[520px] overflow-y-auto space-y-4 pr-4 scroll-smooth">
          {clauses.length ? clauses.map((c: any, i: number) => {
            const risk = String(c.risk || '').toLowerCase();
            const color = risk === 'high' ? 'bg-[#c1121f]' : (risk === 'medium' ? 'bg-[#c1121faa]' : 'bg-[#b3e5fc]');
            const textColor = risk === 'low' ? 'text-[#c1121f]' : 'text-white';
            return (
              <div key={i} className={`p-4 rounded-lg ${color} ${textColor} mb-4`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-bold">{c.type || 'Clause'}</span>
                  <span className="text-xs">{c.section || ''}</span>
                </div>
                <div className="text-sm leading-relaxed">{c.text}</div>
                <div className="border-t border-white/40 mt-3" />
              </div>
            );
          }) : (
            <p className="text-lg leading-relaxed text-white">No clauses extracted.</p>
          )}
        </div>
      </Card>
    );
  }
  if (mode === 'suggestions') {
    const suggestions = data?.suggestions || [];
    return (
      <Card className={cardClass}>
        <h2 className="text-2xl font-bold mb-4 tracking-wide">Negotiation Suggestions</h2>
        {suggestions.length ? (
          <ul className="list-disc pl-7 space-y-2">
            {suggestions.map((s: string, i: number) => (
              <li key={i} className="text-lg leading-snug text-white">{s}</li>
            ))}
          </ul>
        ) : (
          <p className="text-lg leading-relaxed text-white">No suggestions available.</p>
        )}
      </Card>
    );
  }
  return null;
}
