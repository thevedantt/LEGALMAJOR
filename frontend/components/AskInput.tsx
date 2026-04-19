import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface AskInputProps {
  question: string;
  setQuestion: (q: string) => void;
  onAsk: (e: React.FormEvent) => void;
  loading: boolean;
  disabled: boolean;
}

export default function AskInput({ question, setQuestion, onAsk, loading, disabled }: AskInputProps) {
  return (
    <form className="w-full max-w-md mx-auto mb-6 flex gap-2" onSubmit={onAsk}>
      <Input
        type="text"
        value={question}
        onChange={e => setQuestion(e.target.value)}
        placeholder="Type your question..."
        disabled={disabled || loading}
        className="flex-1"
      />
      <Button type="submit" disabled={disabled || loading} className="px-4">
        {loading ? "Asking..." : "Ask"}
      </Button>
    </form>
  );
}
