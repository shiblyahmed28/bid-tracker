import { api } from "./client";

export type ExportParams = Record<string, string | number | undefined>;

interface SyncPdfResult {
  kind: "pdf";
  blob: Blob;
  filename: string;
}

interface AsyncPdfResult {
  kind: "async";
  taskId: string;
  rowCount: number;
}

export type PdfExportResult = SyncPdfResult | AsyncPdfResult;

function extractFilename(contentDisposition: string | undefined, fallback: string): string {
  const match = contentDisposition ? /filename="?([^"]+)"?/.exec(contentDisposition) : null;
  return match ? match[1] : fallback;
}

/** GET /bids/export/pdf/ — synchronous under the row threshold (a real PDF
 * blob comes back), otherwise a 202 with a task_id to poll (§13 bullet 5). */
export async function requestBidPdfExport(params: ExportParams): Promise<PdfExportResult> {
  const response = await api.get("/bids/export/pdf/", {
    params,
    responseType: "blob",
    validateStatus: (s) => s === 200 || s === 202,
  });

  if (response.status === 202) {
    const text = await (response.data as Blob).text();
    const payload = JSON.parse(text) as { task_id: string; row_count: number };
    return { kind: "async", taskId: payload.task_id, rowCount: payload.row_count };
  }

  return {
    kind: "pdf",
    blob: response.data as Blob,
    filename: extractFilename(response.headers["content-disposition"], "bid-register.pdf"),
  };
}

export async function pollExportStatus(taskId: string): Promise<string> {
  const response = await api.get<{ task_id: string; state: string }>("/bids/export/pdf/status/", {
    params: { task_id: taskId },
  });
  return response.data.state;
}

export async function downloadExportResult(taskId: string): Promise<{ blob: Blob; filename: string }> {
  const response = await api.get("/bids/export/pdf/download/", {
    params: { task_id: taskId },
    responseType: "blob",
  });
  return {
    blob: response.data as Blob,
    filename: extractFilename(response.headers["content-disposition"], "bid-register.pdf"),
  };
}

export async function downloadBidsCsv(params: ExportParams): Promise<void> {
  const response = await api.get("/bids/export/csv/", { params, responseType: "blob" });
  const filename = extractFilename(response.headers["content-disposition"], "bid-register.csv");
  triggerBlobDownload(response.data as Blob, filename);
}

/** GET /bids/{id}/export/pdf/ — the per-bid PDF (§Phase 22 item 3): key
 * details plus the full cost breakdown, unlike the register export above. */
export async function downloadBidDetailPdf(bidId: string, reference: string): Promise<void> {
  const response = await api.get(`/bids/${bidId}/export/pdf/`, { responseType: "blob" });
  const filename = extractFilename(response.headers["content-disposition"], `${reference}.pdf`);
  triggerBlobDownload(response.data as Blob, filename);
}

export function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
