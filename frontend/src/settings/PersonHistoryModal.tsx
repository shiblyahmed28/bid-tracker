import { useEffect, useState } from "react";

import {
  fetchPersonEngagements,
  fetchWelcomeEmailSettings,
  sendWelcomeEmail,
  type PersonEngagement,
  type PersonEngagementHistory,
  type SettingsPerson,
} from "../api/settings";
import { Modal } from "../components/Modal";
import { useToast } from "../components/ToastContext";
import { EmptyState, Skeleton } from "../dashboard/Skeleton";
import { formatDMY, formatFullDateTime } from "../lib/dateUtils";

interface PersonHistoryModalProps {
  person: SettingsPerson;
  onClose: () => void;
}

/** §Phase 20 item 4 (engagement history) and item 5 (per-bid welcome email
 * send/resend) — the two live together here since both are scoped to one
 * (person, bid) pair. */
export function PersonHistoryModal({ person, onClose }: PersonHistoryModalProps) {
  const { showToast } = useToast();
  const [history, setHistory] = useState<PersonEngagementHistory | null>(null);
  const [welcomeEmailsEnabled, setWelcomeEmailsEnabled] = useState<boolean | null>(null);
  const [sendingId, setSendingId] = useState<number | null>(null);

  function load() {
    fetchPersonEngagements(person.id).then(setHistory);
    fetchWelcomeEmailSettings().then((s) => setWelcomeEmailsEnabled(s.enabled));
  }

  useEffect(load, [person.id]);

  async function handleSend(engagement: PersonEngagement) {
    setSendingId(engagement.id);
    try {
      const updated = await sendWelcomeEmail(engagement.id);
      setHistory((prev) =>
        prev
          ? { ...prev, engagements: prev.engagements.map((e) => (e.id === updated.id ? updated : e)) }
          : prev
      );
      showToast(`Welcome email sent to ${person.canonical_name}`);
    } catch (err: any) {
      showToast(err?.response?.data?.detail ?? "Could not send that email.");
    } finally {
      setSendingId(null);
    }
  }

  return (
    <Modal open onClose={onClose} title={`Engagement history — ${person.canonical_name}`}>
      {welcomeEmailsEnabled === false && (
        <div className="banner b-warn" style={{ marginBottom: 14 }}>
          Welcome emails are currently turned off — enable them under Notifications settings before sending.
        </div>
      )}
      {!person.email && (
        <div className="banner b-warn" style={{ marginBottom: 14 }}>
          {person.canonical_name} has no email on file — add one before a welcome email can be sent.
        </div>
      )}

      {history === null ? (
        <Skeleton height={200} />
      ) : history.engagements.length === 0 ? (
        <EmptyState message="Not engaged on any bid yet" />
      ) : (
        <>
          <div className="tscroll">
            <table>
              <thead>
                <tr>
                  <th>Bid</th>
                  <th>Submission</th>
                  <th>Engaged</th>
                  <th className="num">Days</th>
                  <th className="num">Convenience bill</th>
                  <th>Welcome email</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {history.engagements.map((engagement) => (
                  <tr key={engagement.id}>
                    <td>
                      <b>{engagement.bid.reference}</b>
                      <div className="hint" style={{ textTransform: "none" }}>
                        {engagement.bid.client_name}
                      </div>
                    </td>
                    <td className="num">{formatDMY(engagement.bid.submission_date)}</td>
                    <td className="num">
                      {engagement.engaged_from
                        ? `${formatDMY(engagement.engaged_from)} → ${formatDMY(engagement.engaged_to)}`
                        : "—"}
                    </td>
                    <td className="num">{engagement.days}</td>
                    <td className="num">{engagement.convenience_bill}</td>
                    <td>
                      {engagement.welcome_email_sent_at ? (
                        <span className="tag t-sub" title={formatFullDateTime(engagement.welcome_email_sent_at)}>
                          Sent {formatDMY(engagement.welcome_email_sent_at.slice(0, 10))}
                        </span>
                      ) : (
                        <span className="tag t-pend">Not sent</span>
                      )}
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <button
                        className="btn btn-s btn-sm"
                        disabled={!person.email || sendingId === engagement.id}
                        onClick={() => handleSend(engagement)}
                      >
                        {sendingId === engagement.id
                          ? "Sending…"
                          : engagement.welcome_email_sent_at
                            ? "Resend"
                            : "Send"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="cbody" style={{ display: "flex", gap: 24 }}>
            <span>
              Total days: <b className="num">{history.totals.days}</b>
            </span>
            <span>
              Total convenience bill: <b className="num">{history.totals.convenience_bill}</b>
            </span>
          </div>
        </>
      )}
    </Modal>
  );
}
