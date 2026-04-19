import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface UploadCardProps {
  onUpload: (e: React.FormEvent<HTMLFormElement>) => void;
  uploading: boolean;
  fileName: string | null;
  docId: string | null;
  error: string | null;
  fileInputRef: React.RefObject<HTMLInputElement>;
}

export default function UploadCard({ onUpload, uploading, fileName, docId, error, fileInputRef }: UploadCardProps) {
  return (
    <Card className="w-full max-w-md mx-auto p-6 flex flex-col items-center bg-background">
      <form className="flex flex-col items-center w-full" onSubmit={onUpload}>
        <input
          type="file"
          accept="application/pdf"
          ref={fileInputRef}
          className="mb-2 w-full"
          disabled={uploading}
        />
        <button type="submit" className="w-full bg-primary text-primary-foreground rounded px-4 py-2 mt-2 disabled:opacity-60" disabled={uploading}>
          {uploading ? "Uploading..." : "Upload PDF"}
        </button>
      </form>
      {fileName && <div className="mt-2 text-xs">File: <span className="font-medium">{fileName}</span></div>}
      {docId && <Badge className="mt-2 bg-primary text-primary-foreground">ID: {docId}</Badge>}
      {error && <div className="mt-2 text-primary font-semibold text-center">{error}</div>}
    </Card>
  );
}
