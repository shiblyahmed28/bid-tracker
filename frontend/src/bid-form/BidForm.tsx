import { useState, type FormEvent } from "react";

import type { BidDetail, BidWritePayload } from "../api/bids";
import { formatMoneyPreview, parseMoneyPreview } from "../lib/moneyParse";
import { ComboInput } from "./ComboInput";
import { EngagedResourcesSelect } from "./EngagedResourcesSelect";
import { useFormOptions } from "./useFormOptions";

interface FormState {
  clientName: string;
  description: string;
  camName: string;
  salesResourceName: string;
  bidManagerName: string;
  teamId: string;
  engagedIds: number[];
  engagementFrom: string;
  engagementTo: string;
  stage: string;
  initiationMode: string;
  procurementType: string;
  isGoods: boolean;
  isWorks: boolean;
  isService: boolean;
  tenderId: string;
  remarks: string;
  initiationDate: string;
  publishedDate: string;
  prebidDate: string;
  prebidTime: string;
  submissionDate: string;
  submissionTime: string;
  submissionStatus: string;
  result: string;
  securityMode: string;
  securityAmountRaw: string;
  creditFacilityRaw: string;
  bgIssueDate: string;
  bgReference: string;
  bgBank: string;
  bgExpiryDate: string;
}

function initialFormState(bid?: BidDetail | null): FormState {
  return {
    clientName: bid?.client.name ?? "",
    description: bid?.description ?? "",
    camName: bid?.cam?.canonical_name ?? "",
    salesResourceName: bid?.sales_resource?.canonical_name ?? "",
    bidManagerName: bid?.bid_manager?.canonical_name ?? "",
    teamId: bid?.team ? String(bid.team.id) : "",
    engagedIds: bid?.engaged_resources.map((p) => p.id) ?? [],
    engagementFrom: bid?.engagement_from ?? "",
    engagementTo: bid?.engagement_to ?? "",
    stage: bid?.stage ?? "",
    initiationMode: bid?.initiation_mode ?? "",
    procurementType: bid?.procurement_type ?? "",
    isGoods: bid?.is_goods ?? false,
    isWorks: bid?.is_works ?? false,
    isService: bid?.is_service ?? false,
    tenderId: bid?.tender_id ?? "",
    remarks: bid?.remarks ?? "",
    initiationDate: bid?.initiation_date ?? "",
    publishedDate: bid?.published_date ?? "",
    prebidDate: bid?.prebid_date ?? "",
    prebidTime: bid?.prebid_time ?? "",
    submissionDate: bid?.submission_date ?? "",
    submissionTime: bid?.submission_time ?? "",
    submissionStatus: bid?.submission_status ?? "",
    result: bid?.result ?? "",
    securityMode: bid?.security_mode ?? "",
    securityAmountRaw: bid?.security_amount_raw ?? "",
    creditFacilityRaw: bid?.credit_facility_raw ?? "",
    bgIssueDate: bid?.bg_issue_date ?? "",
    bgReference: bid?.bg_reference ?? "",
    bgBank: bid?.bg_bank ?? "",
    bgExpiryDate: bid?.bg_expiry_date ?? "",
  };
}

function buildPayload(form: FormState): BidWritePayload {
  const security = parseMoneyPreview(form.securityAmountRaw);
  const credit = parseMoneyPreview(form.creditFacilityRaw);

  return {
    client_name: form.clientName.trim(),
    description: form.description.trim(),
    cam_name: form.camName.trim(),
    sales_resource_name: form.salesResourceName.trim(),
    bid_manager_name: form.bidManagerName.trim(),
    team: form.teamId ? Number(form.teamId) : null,
    engaged_resources: form.engagedIds,
    engagement_from: form.engagementFrom || null,
    engagement_to: form.engagementTo || null,
    stage: form.stage.trim(),
    initiation_mode: form.initiationMode.trim(),
    procurement_type: form.procurementType.trim(),
    is_goods: form.isGoods,
    is_works: form.isWorks,
    is_service: form.isService,
    tender_id: form.tenderId.trim(),
    initiation_date: form.initiationDate || null,
    published_date: form.publishedDate || null,
    prebid_date: form.prebidDate || null,
    prebid_time: form.prebidTime || null,
    submission_date: form.submissionDate,
    submission_time: form.submissionTime || null,
    submission_status: form.submissionStatus.trim(),
    result: form.result.trim(),
    security_mode: form.securityMode.trim(),
    security_amount_raw: form.securityAmountRaw.trim(),
    security_amount: security.amount,
    security_currency: security.currency,
    credit_facility_raw: form.creditFacilityRaw.trim(),
    credit_facility: credit.amount,
    credit_facility_currency: credit.currency,
    bg_issue_date: form.bgIssueDate || null,
    bg_reference: form.bgReference.trim(),
    bg_bank: form.bgBank.trim(),
    bg_expiry_date: form.bgExpiryDate || null,
    remarks: form.remarks.trim(),
  };
}

function fieldErrors(data: unknown): string[] {
  if (!data || typeof data !== "object") return ["Something went wrong. Please try again."];
  const messages: string[] = [];
  for (const [field, value] of Object.entries(data as Record<string, unknown>)) {
    const text = Array.isArray(value) ? value.join(" ") : String(value);
    messages.push(field === "non_field_errors" ? text : `${field}: ${text}`);
  }
  return messages.length ? messages : ["Something went wrong. Please try again."];
}

interface BidFormProps {
  initial?: BidDetail | null;
  onSubmit: (payload: BidWritePayload) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
}

export function BidForm({ initial, onSubmit, onCancel, submitLabel }: BidFormProps) {
  const { names, teams, people, loading: optionsLoading } = useFormOptions();
  const [form, setForm] = useState<FormState>(() => initialFormState(initial));
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setErrors([]);
    setSubmitting(true);
    try {
      await onSubmit(buildPayload(form));
    } catch (error) {
      const data = (error as { response?: { data?: unknown } })?.response?.data;
      setErrors(fieldErrors(data));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {!initial && (
        <div className="banner b-info">
          App-created bids are never written back to the sheet — they're managed here going forward.
        </div>
      )}

      {errors.length > 0 && (
        <div className="banner b-warn">
          {errors.map((message) => (
            <div key={message}>{message}</div>
          ))}
        </div>
      )}

      <div className="form-section">
        <h3>Core</h3>
        <div className="frow">
          <ComboInput label="Client" value={form.clientName} onChange={(v) => set("clientName", v)} options={names.client} required />
          <ComboInput label="Stage" value={form.stage} onChange={(v) => set("stage", v)} options={names.stage} />
        </div>
        <div className="field">
          <label className="req">Description</label>
          <textarea
            className="inp"
            rows={3}
            value={form.description}
            onChange={(e) => set("description", e.target.value)}
            required
          />
        </div>
        <div className="frow">
          <ComboInput
            label="Procurement type"
            value={form.procurementType}
            onChange={(v) => set("procurementType", v)}
            options={names.procurement_type}
          />
          <ComboInput
            label="Initiation mode"
            value={form.initiationMode}
            onChange={(v) => set("initiationMode", v)}
            options={names.initiation_mode}
          />
        </div>
        <div className="field">
          <label>Delivery type</label>
          <div className="check-row">
            <label>
              <input type="checkbox" checked={form.isGoods} onChange={(e) => set("isGoods", e.target.checked)} />
              Goods
            </label>
            <label>
              <input type="checkbox" checked={form.isWorks} onChange={(e) => set("isWorks", e.target.checked)} />
              Works
            </label>
            <label>
              <input type="checkbox" checked={form.isService} onChange={(e) => set("isService", e.target.checked)} />
              Service
            </label>
          </div>
        </div>
        <div className="frow">
          <div className="field">
            <label>Tender ID</label>
            <input className="inp" value={form.tenderId} onChange={(e) => set("tenderId", e.target.value)} />
          </div>
        </div>
        <div className="field">
          <label>Remarks</label>
          <textarea className="inp" rows={2} value={form.remarks} onChange={(e) => set("remarks", e.target.value)} />
        </div>
      </div>

      <div className="form-section">
        <h3>People</h3>
        <div className="frow3">
          <ComboInput label="CAM" value={form.camName} onChange={(v) => set("camName", v)} options={names.cam} />
          <ComboInput
            label="Sales resource"
            value={form.salesResourceName}
            onChange={(v) => set("salesResourceName", v)}
            options={names.sales_resource}
          />
          <ComboInput
            label="Bid manager"
            value={form.bidManagerName}
            onChange={(v) => set("bidManagerName", v)}
            options={names.bid_manager}
          />
        </div>
      </div>

      <div className="form-section">
        <h3>New fields</h3>
        <div className="frow">
          <div className="field">
            <label>Team</label>
            <select className="inp" value={form.teamId} onChange={(e) => set("teamId", e.target.value)}>
              <option value="">— none —</option>
              {teams.map((team) => (
                <option key={team.value} value={team.value}>
                  {team.label}
                </option>
              ))}
            </select>
          </div>
          <div />
        </div>
        <EngagedResourcesSelect people={people} selectedIds={form.engagedIds} onChange={(ids) => set("engagedIds", ids)} />
        <div className="frow">
          <div className="field">
            <label>Engagement from</label>
            <input
              className="inp"
              type="date"
              value={form.engagementFrom}
              onChange={(e) => set("engagementFrom", e.target.value)}
            />
          </div>
          <div className="field">
            <label>Engagement to</label>
            <input
              className="inp"
              type="date"
              value={form.engagementTo}
              onChange={(e) => set("engagementTo", e.target.value)}
            />
          </div>
        </div>
        {form.engagementFrom && form.engagementTo && (
          <p className="hint">
            {Math.round(
              (new Date(form.engagementTo).getTime() - new Date(form.engagementFrom).getTime()) / 86_400_000
            )}{" "}
            days
          </p>
        )}
      </div>

      <div className="form-section">
        <h3>Dates</h3>
        <div className="frow3">
          <div className="field">
            <label>Initiation date</label>
            <input className="inp" type="date" value={form.initiationDate} onChange={(e) => set("initiationDate", e.target.value)} />
          </div>
          <div className="field">
            <label>Published</label>
            <input className="inp" type="date" value={form.publishedDate} onChange={(e) => set("publishedDate", e.target.value)} />
          </div>
          <div />
        </div>
        <div className="frow3">
          <div className="field">
            <label>Pre-bid date</label>
            <input className="inp" type="date" value={form.prebidDate} onChange={(e) => set("prebidDate", e.target.value)} />
          </div>
          <div className="field">
            <label>Pre-bid time</label>
            <input className="inp" type="time" value={form.prebidTime} onChange={(e) => set("prebidTime", e.target.value)} />
          </div>
          <div />
        </div>
        <div className="frow3">
          <div className="field">
            <label className="req">Submission date</label>
            <input
              className="inp"
              type="date"
              value={form.submissionDate}
              onChange={(e) => set("submissionDate", e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label>Submission time</label>
            <input className="inp" type="time" value={form.submissionTime} onChange={(e) => set("submissionTime", e.target.value)} />
          </div>
          <div />
        </div>
      </div>

      <div className="form-section">
        <h3>Financial</h3>
        <div className="frow">
          <ComboInput
            label="Security mode"
            value={form.securityMode}
            onChange={(v) => set("securityMode", v)}
            options={names.security_mode}
          />
          <ComboInput label="Issuing bank" value={form.bgBank} onChange={(v) => set("bgBank", v)} options={names.bg_bank} />
        </div>
        <div className="frow">
          <div className="field">
            <label>Security amount</label>
            <input
              className="inp"
              value={form.securityAmountRaw}
              onChange={(e) => set("securityAmountRaw", e.target.value)}
              placeholder="e.g. 9,20,000.00 or USD 250000"
            />
            {form.securityAmountRaw && <p className="hint">{formatMoneyPreview(form.securityAmountRaw)}</p>}
          </div>
          <div className="field">
            <label>Credit facility</label>
            <input
              className="inp"
              value={form.creditFacilityRaw}
              onChange={(e) => set("creditFacilityRaw", e.target.value)}
              placeholder="e.g. 9,20,000.00 or USD 250000"
            />
            {form.creditFacilityRaw && <p className="hint">{formatMoneyPreview(form.creditFacilityRaw)}</p>}
          </div>
        </div>
        <div className="frow3">
          <div className="field">
            <label>BG issue date</label>
            <input className="inp" type="date" value={form.bgIssueDate} onChange={(e) => set("bgIssueDate", e.target.value)} />
          </div>
          <div className="field">
            <label>BG expiry date</label>
            <input className="inp" type="date" value={form.bgExpiryDate} onChange={(e) => set("bgExpiryDate", e.target.value)} />
          </div>
          <div className="field">
            <label>BG / reference no.</label>
            <input className="inp" value={form.bgReference} onChange={(e) => set("bgReference", e.target.value)} />
          </div>
        </div>
      </div>

      <div className="form-section">
        <h3>Status</h3>
        <div className="frow">
          <ComboInput
            label="Submission status"
            value={form.submissionStatus}
            onChange={(v) => set("submissionStatus", v)}
            options={names.submission_status}
          />
          <ComboInput label="Result" value={form.result} onChange={(v) => set("result", v)} options={names.result} />
        </div>
      </div>

      <div className="mfoot" style={{ padding: "18px 0 0", borderTop: "1px solid var(--line)", marginTop: 18 }}>
        <button type="button" className="btn btn-s" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
        <button type="submit" className="btn btn-p" disabled={submitting || optionsLoading}>
          {submitting ? "Saving…" : submitLabel}
        </button>
      </div>
    </form>
  );
}
