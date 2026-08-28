import { useParams } from "react-router-dom";

import { Placeholder } from "../components/Placeholder";

export function BidDetailPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <Placeholder
      title="Bid detail"
      description={`The full record for bid ${id} — history, conflicts, notes — arrives in a later phase.`}
    />
  );
}
