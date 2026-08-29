import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { BidForm } from "./BidForm";

// Isolated from the network entirely — the create/edit form's comboboxes and
// selects load their options from the API, which isn't the concern here.
vi.mock("./useFormOptions", () => ({
  useFormOptions: () => ({
    names: {
      client: [],
      cam: [],
      sales_resource: [],
      bid_manager: [],
      stage: [],
      initiation_mode: [],
      procurement_type: [],
      security_mode: [],
      submission_status: [],
      result: [],
      bg_bank: [],
    },
    teams: [],
    people: [],
    loading: false,
  }),
}));

// ComboInput/labels aren't <label for=id>-associated with their inputs, so
// getByLabelText can't find them — walk from the label text to its sibling
// input instead, the way a reader of the rendered DOM would.
function inputAfterLabel(labelText: string): HTMLInputElement | HTMLTextAreaElement {
  const label = screen.getByText(labelText, { selector: "label" });
  return label.nextElementSibling as HTMLInputElement | HTMLTextAreaElement;
}

afterEach(() => {
  cleanup();
});

describe("BidForm", () => {
  it("keeps what the user typed and shows an inline error after a failed submit", async () => {
    const onSubmit = vi.fn().mockRejectedValue({
      response: { data: { non_field_errors: ["Something went wrong. Please try again."] } },
    });

    render(<BidForm onSubmit={onSubmit} onCancel={() => {}} submitLabel="Create bid" />);

    fireEvent.change(inputAfterLabel("Client"), { target: { value: "Acme Corp" } });
    fireEvent.change(inputAfterLabel("Description"), { target: { value: "A large government tender" } });
    fireEvent.change(inputAfterLabel("Submission date"), { target: { value: "2026-09-01" } });

    fireEvent.click(screen.getByRole("button", { name: "Create bid" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    await screen.findByText("Something went wrong. Please try again.");

    expect(inputAfterLabel("Client").value).toBe("Acme Corp");
    expect(inputAfterLabel("Description").value).toBe("A large government tender");
    expect(inputAfterLabel("Submission date").value).toBe("2026-09-01");
  });
});
