import { useRef, useState } from "react";
import { FileSpreadsheet, UploadCloud, CheckCircle2, XCircle, Loader2, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type UploadStatus = "idle" | "uploading" | "success" | "warning" | "error";
type UploadResult = { message?: string; status?: "success" | "warning" | "error"; details?: string[] };

interface FileUploadProps {
  /** Upload handler function passed by parent page (supports onUpload or onFileSelect) */
  onUpload?: (file: File) => Promise<UploadResult | any>;
  onFileSelect?: (file: File) => Promise<UploadResult | any> | void;
  accept?: string;
  hint?: string;
  label?: string;
  uploading?: boolean;
}

export function FileUpload({
  onUpload,
  onFileSelect,
  accept = ".xlsx,.xls,.csv",
  hint,
  label = "Drag & drop your Excel/CSV file here",
  uploading = false,
}: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [status, setStatus] = useState<UploadStatus>("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [details, setDetails] = useState<string[]>([]);

  const displayHint = hint || `Supported formats: ${accept}`;

  const selectFile = (selected: File | null) => {
    if (!selected) return;
    setFile(selected);
    setStatus("idle");
    setMessage(null);
    setDetails([]);

    const validExts = accept
      .split(",")
      .map((e) => e.trim().toLowerCase());
    const fileExt = "." + (selected.name.split(".").pop()?.toLowerCase() || "");
    if (validExts.length > 0 && !validExts.includes(fileExt) && !accept.includes("*")) {
      setStatus("error");
      setMessage(`Unsupported file type '${fileExt}'. Allowed format(s): ${accept}`);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    const uploadFn = onUpload || onFileSelect;
    if (!uploadFn) {
      setStatus("error");
      setMessage("No upload function configured for this uploader.");
      return;
    }

    setStatus("uploading");
    setMessage(null);
    try {
      const result = await uploadFn(file);
      setStatus(result?.status || "success");
      setMessage(
        (result && typeof result === "object" && result.message) ||
          "File uploaded and processed successfully!"
      );
      setDetails(Array.isArray(result?.details) ? result.details : []);
    } catch (error: any) {
      setStatus("error");
      setDetails([]);
      setMessage(
        error instanceof Error
          ? `Upload failed. ${error.message}`
          : error?.message
          ? `Upload failed. ${error.message}`
          : "Upload failed. Please check your file."
      );
    }
  };

  const isUploading = status === "uploading" || uploading;

  return (
    <div className="space-y-4">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          selectFile(e.dataTransfer.files?.[0] ?? null);
        }}
        className={cn(
          "flex w-full min-w-0 cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-border bg-muted/30 p-8 text-center transition-colors",
          dragging && "border-primary bg-accent"
        )}
      >
        <UploadCloud className="size-8 text-muted-foreground" />
        <p className="max-w-full break-words text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground">or</p>
        <span className="text-sm font-medium text-primary underline underline-offset-4">
          Browse files
        </span>
        <p className="max-w-full break-words text-xs text-muted-foreground">{displayHint}</p>
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="sr-only"
          onChange={(e) => selectFile(e.target.files?.[0] ?? null)}
        />
      </div>

      {file ? (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-border bg-card p-3">
          <div className="flex min-w-0 items-center gap-2">
            <FileSpreadsheet className="size-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">Selected file:</p>
              <p className="truncate text-sm font-medium">{file.name}</p>
            </div>
          </div>
          <Button onClick={handleUpload} disabled={isUploading} size="sm">
            {isUploading ? (
              <>
                <Loader2 className="size-4 animate-spin mr-1" /> Uploading...
              </>
            ) : (
              "Upload"
            )}
          </Button>
        </div>
      ) : null}

      {status === "success" && message ? (
        <p className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 font-medium">
          <CheckCircle2 className="size-4 shrink-0" /> {message}
        </p>
      ) : null}
      {status === "warning" && message ? (
        <p className="flex items-center gap-2 text-sm text-amber-700 dark:text-amber-400 font-medium">
          <TriangleAlert className="size-4 shrink-0" /> {message}
        </p>
      ) : null}
      {status === "error" && message ? (
        <p className="flex items-center gap-2 text-sm text-destructive font-medium">
          <XCircle className="size-4 shrink-0" /> {message}
        </p>
      ) : null}
      {details.length > 0 ? (
        <ul className="list-disc space-y-1 pl-6 text-xs text-muted-foreground">
          {details.map((detail, index) => <li key={`${index}-${detail}`}>{detail}</li>)}
        </ul>
      ) : null}
    </div>
  );
}
