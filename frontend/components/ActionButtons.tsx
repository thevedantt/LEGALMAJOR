import { Button } from "@/components/ui/button";

interface ActionButtonsProps {
  onAsk: () => void;
  onSummarize: () => void;
  onAnalyze: () => void;
  onOverallRisk: () => void;
  onFairness: () => void;
  onConflicts: () => void;
  onClauses: () => void;
  onDownloadReport: () => void;
  onSuggestImprovements: () => void;
  disabled: boolean;
  active: 'ask' | 'summarize' | 'analyze' | 'overallRisk' | 'fairness' | 'conflicts' | 'clauses';
}

export default function ActionButtons({ onAsk, onSummarize, onAnalyze, onOverallRisk, onFairness, onConflicts, onClauses, onDownloadReport, onSuggestImprovements, disabled, active }: ActionButtonsProps) {
  return (
    <div className="flex flex-wrap gap-2 w-full max-w-md my-6 mx-auto">
      <Button
        onClick={onAsk}
        disabled={disabled}
        variant={active === 'ask' ? 'default' : 'outline'}
        className="flex-1"
      >Ask</Button>
      <Button
        onClick={onSummarize}
        disabled={disabled}
        variant={active === 'summarize' ? 'default' : 'outline'}
        className="flex-1"
      >Summarize</Button>
      <Button
        onClick={onAnalyze}
        disabled={disabled}
        variant={active === 'analyze' ? 'default' : 'outline'}
        className="flex-1"
      >Analyze Risk</Button>
      <Button
        onClick={onOverallRisk}
        disabled={disabled}
        variant={active === 'overallRisk' ? 'default' : 'outline'}
        className="flex-1 bg-[#c1121f] text-white border border-white"
      >Overall Risk</Button>
      <Button
        onClick={onFairness}
        disabled={disabled}
        variant={active === 'fairness' ? 'default' : 'outline'}
        className="flex-1"
      >Check Fairness</Button>
      <Button
        onClick={onConflicts}
        disabled={disabled}
        variant={active === 'conflicts' ? 'default' : 'outline'}
        className="flex-1"
      >Find Conflicts</Button>
      <Button
        onClick={onClauses}
        disabled={disabled}
        variant={active === 'clauses' ? 'default' : 'outline'}
        className="flex-1"
      >Show Clauses</Button>
      <Button
        onClick={onSuggestImprovements}
        disabled={disabled}
        variant={active === 'suggestions' ? 'default' : 'outline'}
        className="flex-1"
      >Negotiation Suggestions</Button>
      <Button
        onClick={onDownloadReport}
        disabled={disabled}
        variant="outline"
        className="flex-1"
      >Download Report</Button>
    </div>
  );
}
