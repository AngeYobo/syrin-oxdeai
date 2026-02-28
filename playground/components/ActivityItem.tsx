"use client";

interface ActivityItemProps {
  label: string;
  kind?: "status" | "hook";
}

export function ActivityItem({ label, kind = "status" }: ActivityItemProps) {
  return (
    <div className={`activity-item ${kind}`}>
      {kind === "hook" && <span className="activity-badge">[Hook]</span>}
      <span className="activity-label">{label}</span>
    </div>
  );
}
