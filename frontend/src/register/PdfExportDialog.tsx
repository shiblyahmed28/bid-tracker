import { useEffect, useState } from "react";

import {
  downloadExportResult,
  pollExportStatus,
  requestBidPdfExport,
  triggerBlobDownload,
  type ExportParams,
} from "../api/exports";
import { Modal } from "../components/Modal";
import { formatDMY } from "../lib/dateUtils";
import { COLUMN_GROUPS, COLUMNS } from "./columns";

const COLUMN_WARNING_THRESHOLD = 10;
const POLL_INTERVAL_MS = 1500;

interface PdfExportDialogProps {
  open: boolean;
  onClose: () => void;
  matchedCount: number | null;
  exportParams: ExportParams;
  filterChipLabels: string[];
  from: string;
  to: string;
  initialColumnKeys: string[];
}

type Status = "idle" | "working" | "error";

export function PdfExportDialog({
  open,
  onClose,
  matchedCount,
  exportParams,
  filterChipLabels,
  from,
  to,
  initialColumnKeys,
}: PdfExportDialogProps) {
  const [selectedKeys, setSelectedKeys] = useState<string[]>(initialColumnKeys);
  const [status, setStatus] = useState<Status>("idle");
  const [progressMessage, setProgressMessage] = useState("");

  useEffect(() => {
    if (open) {
      setSelectedKeys(initialColumnKeys);
      setStatus("idle");
      setProgressMessage("");
    }
    // Only reset when the dialog opens, not on every parent re-render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function toggle(key: string) {
    setSelectedKeys((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  }

  async function handleGenerate() {
    setStatus("working");
    setProgressMessage("Generating…");
    try {
      const params = { ...exportParams, columns: selectedKeys.join(",") };
      const result = await requestBidPdfExport(params);

      if (result.kind === "pdf") {
        triggerBlobDownload(result.blob, result.filename);
        onClose();
        return;
      }

      setProgressMessage(`Generating ${result.rowCount} rows…`);
      let state = "PENDING";
      while (state === "PENDING" || state === "STARTED") {
        await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
        state = await pollExportStatus(result.taskId);
      }
      if (state !== "SUCCESS") throw new Error("Export failed");

      const { blob, filename } = await downloadExportResult(result.taskId);
      triggerBlobDownload(blob, filename);
      onClose();
    } catch {
      setStatus("error");
    }
  }

  const columnCount = selectedKeys.length;
  const working = status === "working";

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Download PDF"
      footer={
        <>
          <button className="btn btn-s" onClick={onClose} disabled={working}>
            Cancel
          </button>
          <button className="btn btn-p" onClick={handleGenerate} disabled={working || columnCount === 0}>
            {working ? progressMessage : "Generate PDF"}
          </button>
        </>
      }
    >
      <div className="banner b-info">
        Exports <b className="num">{matchedCount ?? "—"}</b> bid{matchedCount === 1 ? "" : "s"} using the filters
        below.
      </div>

      <h3 style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)", marginBottom: 8 }}>
        Filters applied
      </h3>
      <div className="chiplist" style={{ marginBottom: 16 }}>
        <span className="mini">
          Dates: {formatDMY(from)} → {formatDMY(to)}
        </span>
        {filterChipLabels.map((label) => (
          <span className="mini" key={label}>
            {label}
          </span>
        ))}
      </div>

      <h3 style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--muted)", marginBottom: 8 }}>
        Columns to print
      </h3>
      {COLUMN_GROUPS.map((group) => {
        const columns = COLUMNS.filter((c) => c.group === group);
        if (!columns.length) return null;
        return (
          <div key={group}>
            <p className="hint" style={{ margin: "9px 0 5px", fontWeight: 700, color: "var(--ink)" }}>
              {group}
            </p>
            <div className="colgrid">
              {columns.map((c) => (
                <label className={`colchk${c.isNew ? " new" : ""}`} key={c.key}>
                  <input type="checkbox" checked={selectedKeys.includes(c.key)} onChange={() => toggle(c.key)} />
                  {c.label}
                  {c.isNew && <small>new</small>}
                </label>
              ))}
            </div>
          </div>
        );
      })}

      {columnCount > COLUMN_WARNING_THRESHOLD && (
        <p className="hint" style={{ color: "var(--warn)", marginTop: 12, fontWeight: 600 }}>
          {columnCount} columns selected — more than about 10 will be cramped on the printed page.
        </p>
      )}

      {status === "error" && <p className="err">Something went wrong generating the PDF. Try again.</p>}
    </Modal>
  );
}
