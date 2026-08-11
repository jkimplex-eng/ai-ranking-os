import {
  forceCenter,
  forceLink,
  forceManyBody,
  forceSimulation,
  type SimulationNodeDatum,
} from "d3-force";
import { useMemo, useState } from "react";

type ChartPoint = { value: number; label: string; researchId?: number };

export function AreaLineChart({ points: values, onSelect }: { points: ChartPoint[]; onSelect?: (researchId: number) => void }) {
  const [range, setRange] = useState<"3" | "6" | "ALL">("3");
  const [hover, setHover] = useState<number>();
  const shown =
    range === "3"
      ? values.slice(-3)
      : range === "6"
        ? values.slice(-6)
        : values;
  const step = 520 / Math.max(shown.length - 1, 1);
  const polyline = shown
    .map((point, index) => `${20 + index * step},${185 - point.value * 1.45}`)
    .join(" ");
  return (
    <div className="interactive-chart">
      <div className="chart-controls">
        {(["3", "6", "ALL"] as const).map((item) => (
          <button
            className={range === item ? "active" : ""}
            onClick={() => setRange(item)}
            key={item}
          >
            {item === "ALL" ? "Все" : `${item} точки`}
          </button>
        ))}
      </div>
      <svg viewBox="0 0 560 210" role="img" aria-label="Динамика AI Visibility">
        <defs>
          <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#3b82f6" stopOpacity=".4" />
            <stop offset="1" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
        </defs>
        <polygon points={`20,195 ${polyline} 540,195`} fill="url(#trend-fill)" />
        <polyline
          points={polyline}
          fill="none"
          stroke="#6da2ff"
          strokeWidth="4"
          strokeLinecap="round"
        />
        {shown.map((point, index) => (
          <g
            key={index}
            onMouseEnter={() => setHover(index)}
            onMouseLeave={() => setHover(undefined)}
          >
            <circle
              cx={20 + index * step}
              cy={185 - point.value * 1.45}
              r="12"
              fill="transparent"
            />
            <circle
              cx={20 + index * step}
              cy={185 - point.value * 1.45}
              r={hover === index ? 6 : 4}
              fill="#0d1625"
              stroke="#8fb4ff"
              strokeWidth="3"
                onClick={() => point.researchId != null && onSelect?.(point.researchId)}
              className={onSelect ? "chart-point-link" : undefined}
            />
            {hover === index && (
              <g>
                <rect
                  x={Math.min(470, Math.max(5, 20 + index * step - 35))}
                  y={128 - point.value * 0.9}
                  width="116"
                  height="42"
                  rx="8"
                  fill="#263854"
                />
                <text
                  x={Math.min(505, Math.max(58, 20 + index * step + 22))}
                  y={145 - point.value * 0.9}
                  fill="white"
                  textAnchor="middle"
                  fontSize="12"
                >
                  {point.value.toFixed(1)}{point.researchId != null ? ` · #${point.researchId}` : ""}
                </text>
                <text x={Math.min(505, Math.max(58, 20 + index * step + 22))} y={160 - point.value * 0.9} fill="#b8c7dc" textAnchor="middle" fontSize="9">{point.label}</text>
              </g>
            )}
          </g>
        ))}
      </svg>
    </div>
  );
}

export function RadarChart({
  values,
  labels,
}: {
  values: number[];
  labels: string[];
}) {
  const center = 130,
    radius = 92,
    count = values.length;
  const point = (value: number, index: number) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / count;
    const r = (radius * value) / 100;
    return [center + Math.cos(angle) * r, center + Math.sin(angle) * r];
  };
  const axes = labels.map((_, i) => point(100, i));
  const shape = values.map((v, i) => point(v, i).join(",")).join(" ");
  return (
    <svg
      className="radar"
      viewBox="0 0 260 260"
      role="img"
      aria-label="Радар показателей"
    >
      {[0.25, 0.5, 0.75, 1].map((level) => (
        <polygon
          key={level}
          points={axes
            .map(
              ([x, y]) =>
                `${center + (x - center) * level},${center + (y - center) * level}`,
            )
            .join(" ")}
          fill="none"
          stroke="#2b3a51"
        />
      ))}
      {axes.map(([x, y], i) => (
        <g key={labels[i]}>
          <line x1={center} y1={center} x2={x} y2={y} stroke="#2b3a51" />
          <text
            x={center + (x - center) * 1.18}
            y={center + (y - center) * 1.13}
            textAnchor="middle"
            fill="#9dacbf"
            fontSize="9"
          >
            {labels[i]}
          </text>
        </g>
      ))}
      <polygon
        points={shape}
        fill="#3b82f644"
        stroke="#6ea1ff"
        strokeWidth="2"
      />
    </svg>
  );
}

export function Heatmap({ values }: { values: number[] }) {
  return (
    <div
      className="heatmap"
      role="img"
      aria-label="Тепловая карта присутствия моделей"
    >
      {["OpenAI", "Claude", "Gemini", "DeepSeek", "Perplexity"].map(
        (model, row) => (
          <div key={model}>
            <span>{model}</span>
            {[0, 1, 2, 3].map((cell) => {
              const value = Math.max(
                10,
                Math.min(
                  100,
                  (values[(row + cell) % values.length] || 60) - cell * 4,
                ),
              );
              return (
                <button
                  title={`${model}: ${value}%`}
                  style={{
                    background: `rgba(59,130,246,${0.12 + value / 120})`,
                  }}
                  key={cell}
                >
                  {value}
                </button>
              );
            })}
          </div>
        ),
      )}
    </div>
  );
}

export function Treemap({ sources }: { sources: number }) {
  const items = [
    ["Отраслевые СМИ", 38],
    ["Каталоги", 26],
    ["Обзоры", 20],
    ["Соцсети", 16],
  ] as const;
  return (
    <div className="treemap" aria-label={`${sources} источника знаний`}>
      {items.map(([name, size]) => (
        <button
          key={name}
          style={{ flexGrow: size }}
          title={`${name}: ${size}%`}
        >
          <b>{name}</b>
          <span>{size}%</span>
        </button>
      ))}
    </div>
  );
}

type GraphNode = SimulationNodeDatum & { id: string; group: string };
export function NetworkGraph({ brand }: { brand: string }) {
  const [query, setQuery] = useState("");
  const [zoom, setZoom] = useState(1);
  const [dragging, setDragging] = useState<string>();
  const [offsets, setOffsets] = useState<
    Record<string, { x: number; y: number }>
  >({});
  const base = useMemo<GraphNode[]>(
    () => [
      { id: brand, group: "brand" },
      { id: "OpenAI", group: "model" },
      { id: "Claude", group: "model" },
      { id: "Gemini", group: "model" },
      { id: "Industry Media", group: "source" },
      { id: "Product", group: "entity" },
    ],
    [brand],
  );
  const nodes = useMemo(() => {
    const copy = base.map((item) => ({ ...item }));
    const links = copy
      .slice(1)
      .map((node) => ({ source: copy[0].id, target: node.id }));
    const simulation = forceSimulation(copy)
      .force("charge", forceManyBody().strength(-280))
      .force("center", forceCenter(240, 150))
      .force(
        "link",
        forceLink(links)
          .id((node) => String((node as GraphNode).id))
          .distance(100),
      )
      .stop();
    for (let i = 0; i < 120; i++) simulation.tick();
    simulation.stop();
    return copy;
  }, [base]);
  return (
    <div className="network-wrap">
      <div className="graph-tools">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Найти сущность…"
        />
        <div className="graph-zoom">
          <button
            onClick={() => setZoom((value) => Math.max(0.7, value - 0.15))}
            aria-label="Уменьшить граф"
          >
            −
          </button>
          <span>{Math.round(zoom * 100)}%</span>
          <button
            onClick={() => setZoom((value) => Math.min(1.6, value + 0.15))}
            aria-label="Увеличить граф"
          >
            +
          </button>
        </div>
      </div>
      <svg
        className="network"
        viewBox="0 0 480 300"
        role="img"
        aria-label="Граф знаний"
      >
        <g
          transform={`translate(${240 * (1 - zoom)} ${150 * (1 - zoom)}) scale(${zoom})`}
        >
          {nodes.slice(1).map((node) => (
            <line
              key={node.id}
              x1={nodes[0]?.x}
              y1={nodes[0]?.y}
              x2={(node.x ?? 0) + (offsets[node.id]?.x ?? 0)}
              y2={(node.y ?? 0) + (offsets[node.id]?.y ?? 0)}
              stroke="#34465f"
            />
          ))}
          {nodes.map((node) => {
            const faded =
              query && !node.id.toLowerCase().includes(query.toLowerCase());
            return (
              <g
                key={node.id}
                opacity={faded ? 0.35 : 1}
                className="graph-node"
                transform={`translate(${offsets[node.id]?.x ?? 0} ${offsets[node.id]?.y ?? 0})`}
                onPointerDown={(event) => {
                  setDragging(node.id);
                  event.currentTarget.setPointerCapture(event.pointerId);
                }}
                onPointerMove={(event) => {
                  if (dragging !== node.id) return;
                  setOffsets((current) => ({
                    ...current,
                    [node.id]: {
                      x: (current[node.id]?.x ?? 0) + event.movementX / zoom,
                      y: (current[node.id]?.y ?? 0) + event.movementY / zoom,
                    },
                  }));
                }}
                onPointerUp={() => setDragging(undefined)}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={node.group === "brand" ? 25 : 16}
                  fill={
                    node.group === "brand"
                      ? "#3b82f6"
                      : node.group === "source"
                        ? "#f59e0b"
                        : "#263d62"
                  }
                />
                <text
                  x={node.x}
                  y={(node.y || 0) + 35}
                  textAnchor="middle"
                  fill="#c8d4e6"
                  fontSize="10"
                >
                  {node.id}
                </text>
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
}
