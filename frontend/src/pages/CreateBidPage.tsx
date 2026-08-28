import { useNavigate } from "react-router-dom";

import { createBid, type BidWritePayload } from "../api/bids";
import { BidForm } from "../bid-form/BidForm";
import { useToast } from "../components/ToastContext";

export function CreateBidPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  async function handleSubmit(payload: BidWritePayload) {
    const bid = await createBid(payload);
    showToast("Bid created");
    navigate(`/bids/${bid.id}`);
  }

  return (
    <div className="card">
      <div className="chead">
        <h2>Create bid</h2>
      </div>
      <div className="cbody">
        <BidForm onSubmit={handleSubmit} onCancel={() => navigate("/bids")} submitLabel="Create bid" />
      </div>
    </div>
  );
}
