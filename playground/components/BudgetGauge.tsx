"use client";

interface BudgetGaugeProps {
  text: string | null;
  className?: string;
}

export function BudgetGauge({ text, className }: BudgetGaugeProps) {
  if (!text) return null;

  return <div className={`budget-gauge ${className ?? ""}`.trim()}>{text}</div>;
}
