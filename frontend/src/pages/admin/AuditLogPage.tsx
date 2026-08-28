import { useEffect, useState } from "react";

import { downloadAuditCsv, fetchAuditEntries, type AuditEntryItem, type AuditFilters } from "../../api/audit";
import { fetchUsers, type AdminUser } from "../../api/accounts";
import { Pager } from "../../register/Pager";
import { Skeleton } from "../../dashboard/Skeleton";
import { formatFullDateTime } from "../../lib/dateUtils";

const ACTION_LABELS: Record<string, string> = {
  sign_in: "Sign in",
  sign_in_failed: "Failed sign in",
  sign_out: "Sign out",
  session_revoke: "Session revoked",
  bid_create: "Bid created",
  bid_update: "Bid updated",
  bid_soft_delete: "Bid deleted",
  bid_restore: "Bid restored",
  conflict_resolution: "Conflict resolved",
  user_create: "User created",
  user_update: "User updated",
  role_change: "Role changed",
  password_reset: "Password reset",
  password_change: "Password changed",
  manual_sync_trigger: "Manual sync triggered",
};

export function AuditLogPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [actor, setActor] = useState<string>("");
  const [action, setAction] = useState<string>("");
  const [createdAfter, setCreatedAfter] = useState("");
  const [createdBefore, setCreatedBefore] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const [entries, setEntries] = useState<AuditEntryItem[] | null>(null);
  const [count, setCount] = useState(0);

  useEffect(() => {
    fetchUsers().then(setUsers);
  }, []);

  useEffect(() => {
    const filters: AuditFilters = { page, page_size: pageSize };
    if (actor) filters.actor = Number(actor);
    if (action) filters.action = action;
    if (createdAfter) filters.created_after = createdAfter;
    if (createdBefore) filters.created_before = createdBefore;

    setEntries(null);
    fetchAuditEntries(filters).then((data) => {
      setEntries(data.results);
      setCount(data.count);
    });
  }, [actor, action, createdAfter, createdBefore, page, pageSize]);

  function handleExport() {
    const filters: AuditFilters = {};
    if (actor) filters.actor = Number(actor);
    if (action) filters.action = action;
    if (createdAfter) filters.created_after = createdAfter;
    if (createdBefore) filters.created_before = createdBefore;
    downloadAuditCsv(filters);
  }

  return (
    <>
      <div className="banner b-info">
        Every create, edit, delete, sign-in and sync is recorded against the account that caused it. Entries
        cannot be edited or removed, including by admins.
      </div>

      <div className="card">
        <div className="cbody tools">
          <select
            className="inp"
            style={{ width: "auto" }}
            value={actor}
            onChange={(e) => {
              setActor(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All users</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.full_name || u.email}
              </option>
            ))}
          </select>
          <select
            className="inp"
            style={{ width: "auto" }}
            value={action}
            onChange={(e) => {
              setAction(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All actions</option>
            {Object.entries(ACTION_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
          <input
            type="date"
            className="inp"
            style={{ width: "auto" }}
            value={createdAfter}
            onChange={(e) => {
              setCreatedAfter(e.target.value);
              setPage(1);
            }}
          />
          <input
            type="date"
            className="inp"
            style={{ width: "auto" }}
            value={createdBefore}
            onChange={(e) => {
              setCreatedBefore(e.target.value);
              setPage(1);
            }}
          />
          <button className="btn btn-s" onClick={handleExport}>
            Export CSV
          </button>
        </div>
      </div>

      <div className="card">
        <div className="chead">
          <h2>Audit log</h2>
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
                  <th>Who</th>
                  <th>Action</th>
                  <th>Bid</th>
                  <th>Field</th>
                  <th>From</th>
                  <th>To</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <tr key={e.id}>
                    <td className="num" style={{ whiteSpace: "nowrap" }}>
                      {formatFullDateTime(e.created_at)}
                    </td>
                    <td>
                      <b>{e.actor_email ?? e.actor_label ?? "System (sync)"}</b>
                    </td>
                    <td>{ACTION_LABELS[e.action] ?? e.action}</td>
                    <td className="num" style={{ fontSize: 11.5 }}>
                      {e.bid_reference ?? "—"}
                    </td>
                    <td style={{ color: "var(--muted)" }}>{e.field || "—"}</td>
                    <td>{e.old_value || "—"}</td>
                    <td>
                      <b>{e.new_value || "—"}</b>
                    </td>
                    <td className="num" style={{ fontSize: 11, color: "var(--muted)" }}>
                      {e.ip || "—"}
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
