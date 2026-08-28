import { useEffect, useRef, useState } from "react";

import { fetchQuarantineRows, fetchSyncRuns, triggerSyncRun, type QuarantineRowItem, type SyncRunItem } from "../../api/sync";
import { Skeleton } from "../../dashboard/Skeleton";
import { formatFullDateTime } from "../../lib/dateUtils";

const STATUS_TAG: Record<string, string> = { success: "t-won", failed: "t-lost", running: "t-pend" };
const TRIGGER_LABEL: Record<string, string> = { scheduled: "Scheduled", manual: "Manual" };

function quarantineSummary(row: QuarantineRowItem): string {
  const cells = row.raw_data?.row;
  if (!Array.isArray(cells)) return "—";
  return (
    cells
      .filter((v) => v !== null && v !== undefined && String(v).trim() !== "")
      .slice(0, 5)
      .join(" · ") || "—"
  );
}

export function SyncHistoryPage() {
  const [runs, setRuns] = useState<SyncRunItem[] | null>(null);
  const [quarantine, setQuarantine] = useState<QuarantineRowItem[] | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  function load() {
    fetchSyncRuns(1, 10).then((page) => setRuns(page.results));
    fetchQuarantineRows(1, 20).then((page) => setQuarantine(page.results));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleRunNow() {
    setSyncing(true);
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    try {
      await triggerSyncRun();
      load();
    } finally {
      if (timerRef.current) clearInterval(timerRef.current);
      setSyncing(false);
    }
  }

  const latest = runs?.[0];

  return (
    <>
      <div className="banner b-ok">
        Runs automatically every 8 hours — 00:00, 08:00 and 16:00 Asia/Dhaka.
      </div>

      <div className="grid kpis" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        <div className="card kpi">
          <span className="klab">Last run</span>
          <b className="num kval">{latest ? formatFullDateTime(latest.started_at) : "—"}</b>
          <span className="ksub">
            {latest ? `${TRIGGER_LABEL[latest.trigger]} · ${latest.duration_seconds?.toFixed(1) ?? "—"}s` : "No runs yet"}
          </span>
        </div>
        <div className="card kpi">
          <span className="klab">Rows read</span>
          <b className="num kval">{latest?.rows_read ?? "—"}</b>
          <span className="ksub">{latest ? `${latest.rows_quarantined} quarantined` : "—"}</span>
        </div>
        <div className="card kpi">
          <span className="klab">Changes applied</span>
          <b className="num kval">{latest ? latest.rows_created + latest.rows_updated : "—"}</b>
          <span className="ksub">
            {latest ? `${latest.rows_created} created · ${latest.rows_updated} updated` : "—"}
          </span>
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Fetch history</h2>
          <div className="hgap" />
          <button className="btn btn-s btn-sm" onClick={handleRunNow} disabled={syncing}>
            {syncing ? `Running… ${elapsed}s` : "Run now"}
          </button>
        </div>
        <div className="tscroll">
          {runs === null ? (
            <div className="cbody">
              <Skeleton height={160} />
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Started</th>
                  <th>Trigger</th>
                  <th style={{ textAlign: "right" }}>Duration</th>
                  <th style={{ textAlign: "right" }}>Read</th>
                  <th style={{ textAlign: "right" }}>Created</th>
                  <th style={{ textAlign: "right" }}>Updated</th>
                  <th style={{ textAlign: "right" }}>Quarantined</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.id}>
                    <td className="num">#{r.id}</td>
                    <td className="num" style={{ whiteSpace: "nowrap" }}>
                      {formatFullDateTime(r.started_at)}
                    </td>
                    <td>{TRIGGER_LABEL[r.trigger]}{r.actor_email ? ` · ${r.actor_email}` : ""}</td>
                    <td className="num" style={{ textAlign: "right" }}>
                      {r.duration_seconds !== null ? `${r.duration_seconds.toFixed(1)}s` : "—"}
                    </td>
                    <td className="num" style={{ textAlign: "right" }}>{r.rows_read}</td>
                    <td className="num" style={{ textAlign: "right" }}>{r.rows_created}</td>
                    <td className="num" style={{ textAlign: "right" }}>{r.rows_updated}</td>
                    <td className="num" style={{ textAlign: "right" }}>{r.rows_quarantined}</td>
                    <td>
                      <span className={`tag ${STATUS_TAG[r.status]}`}>{r.status}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Quarantined rows</h2>
          <span className="scope">Needs a human</span>
        </div>
        <div className="tscroll">
          {quarantine === null ? (
            <div className="cbody">
              <Skeleton height={100} />
            </div>
          ) : quarantine.length === 0 ? (
            <div className="cbody">
              <p className="hint">Nothing quarantined.</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Sheet row</th>
                  <th>Reason</th>
                  <th>Raw value</th>
                </tr>
              </thead>
              <tbody>
                {quarantine.map((q) => (
                  <tr key={q.id}>
                    <td className="num">{q.sheet_row ?? "—"}</td>
                    <td>{q.reason}</td>
                    <td className="num trunc" style={{ maxWidth: 320 }} title={quarantineSummary(q)}>
                      {quarantineSummary(q)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </>
  );
}
