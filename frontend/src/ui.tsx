import { AnimatePresence, motion, type HTMLMotionProps } from "framer-motion";
import type { ReactNode } from "react";

export function Button({
  className = "",
  ...props
}: HTMLMotionProps<"button">) {
  return (
    <motion.button
      whileHover={{ y: -1 }}
      whileTap={{ scale: 0.98 }}
      className={`ds-button ${className}`}
      {...props}
    />
  );
}

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.article
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ borderColor: "#3b5680" }}
      className={`panel ${className}`}
    >
      {children}
    </motion.article>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "success" | "warning" | "danger";
}) {
  return <span className={`badge ${tone}`}>{children}</span>;
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <span className={`skeleton ${className}`} aria-label="Загрузка" />;
}

export function Drawer({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.button
            className="drawer-backdrop"
            aria-label="Закрыть панель"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
          <motion.aside
            className="drawer"
            role="dialog"
            aria-modal="true"
            aria-label={title}
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", damping: 30, stiffness: 260 }}
          >
            <header>
              <div>
                <span className="eyebrow">ДЕТАЛИ МЕТРИКИ</span>
                <h2>{title}</h2>
              </div>
              <Button
                className="icon-button"
                onClick={onClose}
                aria-label="Закрыть"
              >
                ×
              </Button>
            </header>
            <div className="drawer-content">{children}</div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

export function ChartContainer({
  title,
  caption,
  children,
  action,
}: {
  title: string;
  caption?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <Card className="chart-container">
      <div className="section-head">
        <div>
          <span className="section-label">{caption}</span>
          <h2>{title}</h2>
        </div>
        {action}
      </div>
      {children}
    </Card>
  );
}

export function KpiCard({
  icon,
  title,
  value,
  delta,
  points,
  onClick,
}: {
  icon: string;
  title: string;
  value: number;
  delta?: number | null;
  points: number[];
  onClick: () => void;
}) {
  const coordinates = points
    .map((point, index) => `${index * 26},${42 - point * 0.32}`)
    .join(" ");
  return (
    <motion.button
      className="kpi-card"
      onClick={onClick}
      whileHover={{ y: -4 }}
      whileTap={{ scale: 0.99 }}
    >
      <div className="kpi-top">
        <span className="kpi-icon">{icon}</span>
        <span className={delta == null ? "neutral" : delta >= 0 ? "good" : "critical"}>
          {delta == null ? "Нет сравнения" : `${delta >= 0 ? "+" : ""}${delta.toFixed(1)}%`}
        </span>
      </div>
      <span>{title}</span>
      <strong>{value.toFixed(1)}</strong>
      <svg viewBox="0 0 130 48" aria-hidden="true">
        <polyline
          points={coordinates}
          fill="none"
          stroke={value >= 60 ? "#22c55e" : "#f59e0b"}
          strokeWidth="3"
          strokeLinecap="round"
        />
      </svg>
    </motion.button>
  );
}

export function Timeline({
  items,
}: {
  items: Array<{ title: string; detail: string; done?: boolean }>;
}) {
  return (
    <ol className="activity-timeline">
      {items.map((item, index) => (
        <li className={item.done ? "done" : ""} key={item.title}>
          <span>{item.done ? "✓" : index + 1}</span>
          <div>
            <b>{item.title}</b>
            <small>{item.detail}</small>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function Modal({
  open,
  title,
  children,
  onClose,
}: {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <Drawer open={open} title={title} onClose={onClose}>
      {children}
    </Drawer>
  );
}

export function WizardStep({
  number,
  active,
  done,
}: {
  number: number;
  active: boolean;
  done: boolean;
}) {
  return (
    <span className={active || done ? "active" : ""}>
      {done ? "✓" : number}
    </span>
  );
}
