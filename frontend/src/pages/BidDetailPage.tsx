import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { deleteBid, fetchBid, updateBid, type BidDetail, type BidWritePayload } from "../api/bids";
import { downloadBidDetailPdf } from "../api/exports";
import { useAuth } from "../auth/AuthContext";
import { BidForm } from "../bid-form/BidForm";
import { ConflictBanner } from "../bid-detail/ConflictBanner";
import { CostBreakdown } from "../bid-detail/CostBreakdown";
import { DetailFields } from "../bid-detail/DetailFields";
import { HistoryTimeline } from "../bid-detail/HistoryTimeline";
import { MilestoneFlowchart } from "../bid-detail/MilestoneFlowchart";
import { Modal } from "../components/Modal";
import { useToast } from "../components/ToastContext";
import { Skeleton } from "../dashboard/Skeleton";

export function BidDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [bid, setBid] = useState<BidDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(() => {
    if (!id) return;
    setLoading(true);
    fetchBid(id).then((data) => {
      setBid(data);
      setLoading(false);
    });
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading || !bid || !id) {
    return (
      <div className="card">
        <div className="cbody">
          <Skeleton height={300} />
        </div>
      </div>
    );
  }

  const isEditorOrAbove = user?.role === "editor" || user?.role === "admin";
  const isAdmin = user?.role === "admin";

  async function handleSave(payload: BidWritePayload) {
    await updateBid(id!, payload);
    showToast("Bid updated");
    setEditing(false);
    load();
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteBid(id!);
      showToast("Bid deleted");
      navigate("/bids");
    } finally {
      setDeleting(false);
    }
  }

  if (editing) {
    return (
      <div className="card">
        <div className="chead">
          <h2>Edit bid — {bid.reference}</h2>
        </div>
        <div className="cbody">
          <BidForm initial={bid} submitLabel="Save changes" onSubmit={handleSave} onCancel={() => setEditing(false)} />
        </div>
      </div>
    );
  }

  return (
    <>
      {isEditorOrAbove && bid.conflicts.length > 0 && (
        <ConflictBanner conflicts={bid.conflicts} onResolved={load} />
      )}

      <MilestoneFlowchart bid={bid} />

      <div className="grid c2">
        <div className="card">
          <div className="chead">
            <h2>{bid.client.name}</h2>
            <span className="scope">{bid.reference}</span>
            <div className="hgap" />
            <button className="btn btn-s btn-sm" onClick={() => downloadBidDetailPdf(bid.id, bid.reference)}>
              Download PDF
            </button>
            {isEditorOrAbove && (
              <button className="btn btn-s btn-sm" onClick={() => setEditing(true)}>
                Edit
              </button>
            )}
            {isAdmin && (
              <button className="btn btn-d btn-sm" onClick={() => setShowDeleteConfirm(true)}>
                Delete
              </button>
            )}
          </div>
          <div className="cbody">
            <DetailFields bid={bid} />
          </div>
        </div>

        <div className="card">
          <div className="chead">
            <h2>History</h2>
          </div>
          <div className="cbody">
            <HistoryTimeline bidId={bid.id} />
          </div>
        </div>
      </div>

      <CostBreakdown bid={bid} />

      <Modal
        open={showDeleteConfirm}
        onClose={() => setShowDeleteConfirm(false)}
        title="Delete bid"
        footer={
          <>
            <button className="btn btn-s" onClick={() => setShowDeleteConfirm(false)} disabled={deleting}>
              Cancel
            </button>
            <button className="btn btn-d" onClick={handleDelete} disabled={deleting}>
              {deleting ? "Deleting…" : "Delete"}
            </button>
          </>
        }
      >
        <p>
          Delete <strong>{bid.reference}</strong> — {bid.client.name}
          {bid.description ? ` (${bid.description.slice(0, 80)})` : ""}? It disappears from the register, but the
          record and its history are kept.
        </p>
      </Modal>
    </>
  );
}
