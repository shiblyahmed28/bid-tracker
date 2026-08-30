import type { BidDetail } from "../api/bids";
import { formatDMY, todayISO } from "../lib/dateUtils";

interface MilestoneNode {
  key: string;
  label: string;
  /** Representative ISO date used for ordering/today-position — for the
   * Engagement node (a date range) this is engaged_from. */
  date: string | null;
  detail: string;
}

function buildMilestones(bid: BidDetail): MilestoneNode[] {
  return [
    { key: "published", label: "Published", date: bid.published_date, detail: formatDMY(bid.published_date) },
    {
      key: "prebid",
      label: "Pre-bid",
      date: bid.prebid_date,
      detail: bid.prebid_date
        ? `${formatDMY(bid.prebid_date)}${bid.prebid_time ? ", " + bid.prebid_time.slice(0, 5) : ""}`
        : "",
    },
    { key: "initiation", label: "Initiation", date: bid.initiation_date, detail: formatDMY(bid.initiation_date) },
    {
      key: "engagement",
      label: "Engagement",
      date: bid.engagement_from,
      detail: bid.engagement_from ? `${formatDMY(bid.engagement_from)} → ${formatDMY(bid.engagement_to)}` : "",
    },
    { key: "bg_issue", label: "BG issue", date: bid.bg_issue_date, detail: formatDMY(bid.bg_issue_date) },
    {
      key: "submission",
      label: "Submission",
      date: bid.submission_date,
      detail: bid.submission_date
        ? `${formatDMY(bid.submission_date)}${bid.submission_time ? ", " + bid.submission_time.slice(0, 5) : ""}`
        : "",
    },
  ];
}

/** §Phase 22 item 1 — the six milestones always render in this fixed order,
 * regardless of what the actual dates say (real bids often have initiation
 * before published). A node whose date is earlier than the nearest dated
 * node before it gets a warning marker instead of being silently reordered.
 * ISO date strings ("YYYY-MM-DD") compare correctly with plain `<`/`>`. */
export function MilestoneFlowchart({ bid }: { bid: BidDetail }) {
  const today = todayISO();
  const milestones = buildMilestones(bid);

  const warnings: (string | null)[] = [];
  let lastDated: { label: string; date: string } | null = null;
  for (const m of milestones) {
    if (!m.date) {
      warnings.push(null);
      continue;
    }
    warnings.push(
      lastDated && m.date < lastDated.date
        ? `Earlier than ${lastDated.label} (${formatDMY(lastDated.date)}) — shown in its fixed position, not reordered.`
        : null
    );
    lastDated = { label: m.label, date: m.date };
  }

  // Today falls between the last node with date <= today and the first with
  // date > today. If every dated node is in the past (or there are none),
  // todayIndex lands at the end; if every dated node is in the future, at 0.
  const firstFutureIndex = milestones.findIndex((m) => m.date !== null && m.date > today);
  const todayIndex = firstFutureIndex === -1 ? milestones.length : firstFutureIndex;

  const submissionOverdue =
    bid.submission_date !== null && bid.submission_date < today && bid.submission_status !== "SUBMITTED";

  return (
    <div className="card">
      <div className="chead">
        <h2>Milestones</h2>
        <span className="scope">Fixed order · today marked · greyed = not recorded</span>
      </div>
      <div className="cbody">
        <div className="mflow">
          {todayIndex === 0 && <span className="mflow-today-standalone">Today</span>}
          {milestones.map((m, index) => {
            const isSubmission = m.key === "submission";
            const overdue = isSubmission && submissionOverdue;
            const missing = !m.date;
            const past = m.date !== null && m.date <= today;
            const stateClass = missing ? "is-missing" : overdue ? "is-overdue" : past ? "is-past" : "is-future";

            return (
              <div className="mflow-item" key={m.key}>
                <div className={`mnode ${stateClass}`}>
                  <div className="mnode-dot" />
                  <div className="mnode-text">
                    <div className="mnode-label">
                      {m.label}
                      {warnings[index] && (
                        <span className="mnode-warn" title={warnings[index]!}>
                          ⚠
                        </span>
                      )}
                    </div>
                    <div className="mnode-detail">{missing ? "Not recorded" : m.detail}</div>
                    {overdue && <div className="mnode-overdue-label">Passed, not submitted</div>}
                  </div>
                </div>
                {index < milestones.length - 1 && (
                  <div className="mflow-connector">
                    {index + 1 === todayIndex && <span className="mflow-today-chip">Today</span>}
                  </div>
                )}
              </div>
            );
          })}
          {todayIndex === milestones.length && <span className="mflow-today-standalone">Today</span>}
        </div>
      </div>
    </div>
  );
}
