import { useEffect, useState } from "react";

import { fetchSentEmails, type SentEmailFilters, type SentEmailItem, type SentEmailKind } from "../../api/notifications";
import { Pager } from "../../register/Pager";
import { Skeleton } from "../../dashboard/Skeleton";
import { formatFullDateTime } from "../../lib/dateUtils";

const KIND_LABELS: Record<SentEmailKind, string> = {
  new_bid: "New bid",
  deadline: "Deadline reminder",
  policy_event: "Policy event",
  digest: "Digest",
  welcome_engagement: "Welcome email",
  password_reset: "Password reset",
};

/** §Phase 21 item 4 — "did that person get notified?" Admin-only; deliberately
 * has no message-body column at all (the backend never stores one, so
 * financial detail in a bid email can never leak through this screen). */
export function EmailLogPage() {
  const [kind, setKind] = useState<SentEmailKind | "">("");
  const [success, setSuccess] = useState<"" | "true" | "false">("");
  const [recipient, setRecipient] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const [entries, setEntries] = useState<SentEmailItem[] | null>(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const filters: SentEmailFilters = { page, page_size: pageSize };
    if (kind) filters.kind = kind;
    if (success) filters.success = success;
    if (recipient) filters.recipient = recipient;

    setEntries(null);
    fetchSentEmails(filters).then((data) => {
      setEntries(data.results);
      setCount(data.count);
    });
  }, [kind, success, recipient, page, pageSize]);

  return (
    <>
      <div className="banner b-info">
        Every outbound email is logged here, success or failure — recipient, subject, kind and the bid it
        relates to. Message bodies are never stored, so financial detail in a bid email can't leak through
        this screen.
      </div>

      <div className="card">
        <div className="cbody tools">
          <select
            className="inp"
            style={{ width: "auto" }}
            value={kind}
            onChange={(e) => {
              setKind(e.target.value as SentEmailKind | "");
              setPage(1);
            }}
          >
            <option value="">All kinds</option>
            {Object.entries(KIND_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
          <select
            className="inp"
            style={{ width: "auto" }}
            value={success}
            onChange={(e) => {
              setSuccess(e.target.value as "" | "true" | "false");
              setPage(1);
            }}
          >
            <option value="">Sent + failed</option>
            <option value="true">Sent only</option>
            <option value="false">Failed only</option>
          </select>
          <input
            className="inp"
            style={{ flex: "1 1 220px" }}
            placeholder="Recipient contains…"
            value={recipient}
            onChange={(e) => {
              setRecipient(e.target.value);
              setPage(1);
            }}
          />
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Email log</h2>
          <span className="scope">{count.toLocaleString()} entries</span>
        </div>
        <div className="tscroll tall">
          {entries === null ? (
            <div className="cbody">
              <Skeleton height={300} />
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>When</th>
                  <th>Recipient</th>
                  <th>Kind</th>
                  <th>Subject</th>
                  <th>Bid</th>
                  <th>Status</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td className="num" style={{ whiteSpace: "nowrap" }}>
                      {formatFullDateTime(e.created_at)}
                    </td>
                    <td className="num" style={{ fontSize: 11.5 }}>
                      {e.to_email}
                    </td>
                    <td>{KIND_LABELS[e.kind] ?? e.kind}</td>
                    <td className="trunc" style={{ maxWidth: 260 }} title={e.subject}>
                      {e.subject}
                    </td>
                    <td className="num" style={{ fontSize: 11.5 }}>
                      {e.bid_reference ?? "—"}
                    </td>
                    <td>
                      <span className={`tag ${e.success ? "t-won" : "t-lost"}`}>
                        {e.success ? "Sent" : "Failed"}
                      </span>
                    </td>
                    <td className="trunc" style={{ maxWidth: 220, color: "var(--danger)" }} title={e.error}>
                      {e.error || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        {entries !== null && (
          <Pager
            page={page}
            pageSize={pageSize}
            total={count}
            onPageChange={setPage}
            onPageSizeChange={(size) => {
              setPageSize(size);
              setPage(1);
            }}
          />
        )}
      </div>
    </>
  );
}
