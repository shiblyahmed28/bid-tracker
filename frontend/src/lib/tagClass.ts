const RESULT_TAG: Record<string, string> = {
  WON: "t-won",
  LOWEST: "t-won",
  QUALIFIED: "t-won",
  "SHORT LISTED": "t-won",
  LOST: "t-lost",
  DISQUALIFIED: "t-lost",
  PENDING: "t-pend",
  CANCELLED: "t-no",
};

const SUBMISSION_STATUS_TAG: Record<string, string> = {
  SUBMITTED: "t-sub",
  "NOT SUBMITTED": "t-no",
};

export function resultTagClass(value: string): string {
  return RESULT_TAG[value] ?? "t-unk";
}

export function submissionStatusTagClass(value: string): string {
  return SUBMISSION_STATUS_TAG[value] ?? "t-unk";
}
