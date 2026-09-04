import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Zone, FenceLine } from '../../types/camera';

// ─── Constants ──────────────────────────────────────────────────────────────
const NATIVE_W = 1920;
const NATIVE_H = 1080;
const CLOSE_THRESHOLD_PX = 16; // px to auto-close polygon when near first point

// ─── Colour helpers ──────────────────────────────────────────────────────────
const ZONE_COLOURS: Record<string, string> = {
  restricted: '#ef4444',
  loitering: '#f59e0b',
  buffer: '#3b82f6',
};
const SEVERITY_COLOURS: Record<string, string> = {
  low: '#22c55e',
  medium: '#f59e0b',
  high: '#ef4444',
  critical: '#a855f7',
};
function zoneColor(z: Zone) {
  return ZONE_COLOURS[z.type || 'restricted'] || '#ef4444';
}
function fenceColor(l: FenceLine) {
  return SEVERITY_COLOURS[l.severity || 'high'] || '#ef4444';
}

// ─── Types ───────────────────────────────────────────────────────────────────
export type DrawingMode = 'idle' | 'polygon' | 'line';

interface Point {
  x: number;
  y: number;
}

export interface ZoneEditorProps {
  mode: 'zones' | 'fences';
  drawingActive: boolean;
  existingZones: Zone[];
  existingLines: FenceLine[];
  /** Called with native-resolution polygon once user closes the shape */
  onPolygonComplete: (polygon: [number, number][]) => void;
  /** Called with native-resolution start/end once user places the second point */
  onLineComplete: (start: [number, number], end: [number, number]) => void;
  /** Notifies parent that user cleared the draft */
  onClear: () => void;
  /** Notifies parent that drawing finished (so parent can disable drawingActive) */
  onDrawingDone: () => void;
}

// ─── Coordinate mapping ───────────────────────────────────────────────────────
/** Map a point in SVG/rendered-display space → camera native resolution */
function toNative(p: Point, renderedW: number, renderedH: number): [number, number] {
  return [
    Math.round((p.x / renderedW) * NATIVE_W),
    Math.round((p.y / renderedH) * NATIVE_H),
  ];
}

/** Map a native-resolution point → SVG display space */
function toDisplay(n: [number, number], renderedW: number, renderedH: number): Point {
  return {
    x: (n[0] / NATIVE_W) * renderedW,
    y: (n[1] / NATIVE_H) * renderedH,
  };
}

// ─── Component ───────────────────────────────────────────────────────────────
export const ZoneEditor: React.FC<ZoneEditorProps> = ({
  mode,
  drawingActive,
  existingZones,
  existingLines,
  onPolygonComplete,
  onLineComplete,
  onClear,
  onDrawingDone,
}) => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Rendered container size (updates on resize)
  const [size, setSize] = useState<{ w: number; h: number }>({ w: NATIVE_W, h: NATIVE_H });

  // Draft state
  const [draftPoints, setDraftPoints] = useState<Point[]>([]);
  const [cursorPos, setCursorPos] = useState<Point | null>(null);
  const [lineStart, setLineStart] = useState<Point | null>(null);
  const [lineEnd, setLineEnd] = useState<Point | null>(null);

  // Dragging a vertex of the draft polygon
  const draggingIdxRef = useRef<number | null>(null);

  // ── Size observer ──────────────────────────────────────────────────────────
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) setSize({ w: width, h: height });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // ── Reset draft when drawingActive changes off ─────────────────────────────
  useEffect(() => {
    if (!drawingActive) {
      setDraftPoints([]);
      setCursorPos(null);
      setLineStart(null);
      setLineEnd(null);
    }
  }, [drawingActive]);

  // ── SVG coordinate helper ─────────────────────────────────────────────────
  const getSvgPoint = useCallback(
    (e: React.MouseEvent<SVGSVGElement>): Point => {
      const svg = svgRef.current!;
      const rect = svg.getBoundingClientRect();
      return {
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
      };
    },
    []
  );

  // ── Polygon helpers ───────────────────────────────────────────────────────
  const isNearFirst = useCallback(
    (p: Point): boolean => {
      if (draftPoints.length < 3) return false;
      const first = draftPoints[0];
      const dx = p.x - first.x;
      const dy = p.y - first.y;
      return Math.sqrt(dx * dx + dy * dy) < CLOSE_THRESHOLD_PX;
    },
    [draftPoints]
  );

  const closeDraftPolygon = useCallback(() => {
    if (draftPoints.length < 3) return;
    const native = draftPoints.map((p) => toNative(p, size.w, size.h)) as [number, number][];
    onPolygonComplete(native);
    setDraftPoints([]);
    setCursorPos(null);
    onDrawingDone();
  }, [draftPoints, size, onPolygonComplete, onDrawingDone]);

  // ── Mouse handlers ────────────────────────────────────────────────────────
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!drawingActive) return;
      setCursorPos(getSvgPoint(e));
    },
    [drawingActive, getSvgPoint]
  );

  const handleMouseLeave = useCallback(() => {
    setCursorPos(null);
  }, []);

  const handleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!drawingActive) return;
      // Ignore if we were dragging
      if (draggingIdxRef.current !== null) return;

      const pt = getSvgPoint(e);

      if (mode === 'zones') {
        if (isNearFirst(pt)) {
          closeDraftPolygon();
        } else {
          setDraftPoints((prev) => [...prev, pt]);
        }
      } else {
        // fences — line mode
        if (!lineStart) {
          setLineStart(pt);
          setLineEnd(null);
        } else {
          // Complete the line
          const s = toNative(lineStart, size.w, size.h);
          const en = toNative(pt, size.w, size.h);
          onLineComplete(s, en);
          setLineStart(null);
          setLineEnd(null);
          onDrawingDone();
        }
      }
    },
    [
      drawingActive,
      mode,
      getSvgPoint,
      isNearFirst,
      closeDraftPolygon,
      lineStart,
      size,
      onLineComplete,
      onDrawingDone,
    ]
  );

  const handleDoubleClick = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (!drawingActive || mode !== 'zones') return;
      e.preventDefault();
      closeDraftPolygon();
    },
    [drawingActive, mode, closeDraftPolygon]
  );

  // ── Vertex drag handlers ──────────────────────────────────────────────────
  const handleVertexMouseDown = useCallback(
    (e: React.MouseEvent<SVGCircleElement>, idx: number) => {
      e.stopPropagation();
      draggingIdxRef.current = idx;

      const onMove = (ev: MouseEvent) => {
        const svg = svgRef.current!;
        const rect = svg.getBoundingClientRect();
        const pt = { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
        setDraftPoints((prev) => {
          const copy = [...prev];
          copy[idx] = pt;
          return copy;
        });
      };
      const onUp = () => {
        draggingIdxRef.current = null;
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    },
    []
  );

  // Line endpoint drag
  const handleLineEndpointDrag = useCallback(
    (which: 'start' | 'end', e: React.MouseEvent<SVGCircleElement>) => {
      e.stopPropagation();
      draggingIdxRef.current = which === 'start' ? -1 : -2;

      const onMove = (ev: MouseEvent) => {
        const svg = svgRef.current!;
        const rect = svg.getBoundingClientRect();
        const pt = { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
        if (which === 'start') setLineStart(pt);
        else setLineEnd(pt);
      };
      const onUp = () => {
        draggingIdxRef.current = null;
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
      };
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    },
    []
  );

  // ── Undo last vertex ──────────────────────────────────────────────────────
  const handleUndo = () => {
    setDraftPoints((prev) => prev.slice(0, -1));
  };

  // ── Clear all ─────────────────────────────────────────────────────────────
  const handleClear = () => {
    setDraftPoints([]);
    setLineStart(null);
    setLineEnd(null);
    setCursorPos(null);
    onClear();
  };

  // ─── Render helpers ───────────────────────────────────────────────────────

  /** Polygon points string for <polygon> element */
  const polyPoints = (pts: Point[]) =>
    pts.map((p) => `${p.x},${p.y}`).join(' ');

  /** Arrow marker id */
  const ARROW_MARKER = 'zone-editor-arrow';

  // cursor line preview (polygon mode)
  const previewLine =
    drawingActive && mode === 'zones' && draftPoints.length > 0 && cursorPos
      ? { from: draftPoints[draftPoints.length - 1], to: cursorPos }
      : null;

  // fence preview line (second point not yet placed)
  const fencePreview =
    drawingActive && mode === 'fences' && lineStart && cursorPos && !lineEnd
      ? { from: lineStart, to: cursorPos }
      : null;

  // Snap indicator (near-first point highlight)
  const snapActive = drawingActive && mode === 'zones' && cursorPos && isNearFirst(cursorPos);

  const cursor = drawingActive ? 'crosshair' : 'default';

  return (
    <div
      ref={containerRef}
      style={{ position: 'absolute', inset: 0, pointerEvents: drawingActive ? 'auto' : 'none' }}
    >
      {/* ── Drawing controls overlay ── */}
      {drawingActive && (
        <div
          style={{
            position: 'absolute',
            top: 8,
            left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 30,
            display: 'flex',
            gap: 6,
            background: 'rgba(7,14,25,0.82)',
            borderRadius: 6,
            padding: '4px 8px',
            border: '1px solid rgba(255,255,255,0.10)',
            backdropFilter: 'blur(4px)',
          }}
        >
          {mode === 'zones' && (
            <>
              <span style={{ color: '#94a3b8', fontSize: 10, fontFamily: 'monospace', alignSelf: 'center' }}>
                {draftPoints.length === 0
                  ? 'CLICK TO PLACE FIRST VERTEX'
                  : draftPoints.length < 3
                  ? `${draftPoints.length} VERTICES — NEED ≥3`
                  : 'CLICK NEAR FIRST POINT OR DOUBLE-CLICK TO CLOSE'}
              </span>
              {draftPoints.length > 0 && (
                <button
                  onMouseDown={(e) => e.stopPropagation()}
                  onClick={(e) => { e.stopPropagation(); handleUndo(); }}
                  style={btnStyle}
                  title="Undo last vertex"
                >
                  ↩ Undo
                </button>
              )}
            </>
          )}
          {mode === 'fences' && (
            <span style={{ color: '#94a3b8', fontSize: 10, fontFamily: 'monospace', alignSelf: 'center' }}>
              {!lineStart ? 'CLICK START POINT' : 'CLICK END POINT'}
            </span>
          )}
          <button
            onMouseDown={(e) => e.stopPropagation()}
            onClick={(e) => { e.stopPropagation(); handleClear(); }}
            style={{ ...btnStyle, color: '#f87171' }}
            title="Cancel drawing"
          >
            ✕ Cancel
          </button>
        </div>
      )}

      {/* ── SVG Canvas ── */}
      <svg
        ref={svgRef}
        width={size.w}
        height={size.h}
        viewBox={`0 0 ${size.w} ${size.h}`}
        style={{ position: 'absolute', inset: 0, cursor, userSelect: 'none' }}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <defs>
          <marker
            id={ARROW_MARKER}
            markerWidth="8"
            markerHeight="8"
            refX="6"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L0,6 L9,3 z" fill="#facc15" />
          </marker>
        </defs>

        {/* ── Existing zones (read-only overlays) ── */}
        {existingZones.map((z) => {
          if (!z.polygon || z.polygon.length < 3) return null;
          const displayPts = z.polygon.map((n) => toDisplay(n, size.w, size.h));
          const color = zoneColor(z);
          return (
            <g key={`zone-${z.name}`}>
              <polygon
                points={polyPoints(displayPts)}
                fill={`${color}28`}
                stroke={color}
                strokeWidth={1.5}
                strokeDasharray="5 3"
              />
              {/* Zone label */}
              {displayPts.length > 0 && (
                <text
                  x={displayPts.reduce((s, p) => s + p.x, 0) / displayPts.length}
                  y={displayPts.reduce((s, p) => s + p.y, 0) / displayPts.length}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={9}
                  fontFamily="monospace"
                  fill={color}
                  style={{ pointerEvents: 'none', textShadow: '0 0 4px #000' }}
                >
                  {z.name}
                </text>
              )}
            </g>
          );
        })}

        {/* ── Existing fences (read-only overlays) ── */}
        {existingLines.map((l) => {
          const s = toDisplay(l.start, size.w, size.h);
          const en = toDisplay(l.end, size.w, size.h);
          const color = fenceColor(l);
          const mid = { x: (s.x + en.x) / 2, y: (s.y + en.y) / 2 };
          return (
            <g key={`fence-${l.name}`}>
              <line
                x1={s.x} y1={s.y} x2={en.x} y2={en.y}
                stroke={color}
                strokeWidth={2}
                strokeDasharray="6 3"
                markerEnd={`url(#${ARROW_MARKER})`}
              />
              <circle cx={s.x} cy={s.y} r={4} fill={color} />
              <circle cx={en.x} cy={en.y} r={4} fill={color} />
              <text
                x={mid.x} y={mid.y - 6}
                textAnchor="middle"
                fontSize={9}
                fontFamily="monospace"
                fill={color}
                style={{ pointerEvents: 'none' }}
              >
                {l.name}
              </text>
            </g>
          );
        })}

        {/* ── Draft polygon ── */}
        {draftPoints.length >= 2 && (
          <polygon
            points={polyPoints(draftPoints)}
            fill="rgba(59,130,246,0.15)"
            stroke="#3b82f6"
            strokeWidth={1.5}
          />
        )}

        {/* ── Preview line (polygon mode) ── */}
        {previewLine && (
          <line
            x1={previewLine.from.x} y1={previewLine.from.y}
            x2={previewLine.to.x} y2={previewLine.to.y}
            stroke="#3b82f6"
            strokeWidth={1}
            strokeDasharray="4 3"
            style={{ pointerEvents: 'none' }}
          />
        )}

        {/* ── Draft polygon vertices ── */}
        {draftPoints.map((p, i) => {
          const isFirst = i === 0;
          const snapHighlight = isFirst && snapActive;
          return (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r={snapHighlight ? 8 : 5}
              fill={snapHighlight ? '#22c55e' : '#3b82f6'}
              stroke="#fff"
              strokeWidth={1.5}
              style={{ cursor: 'move' }}
              onMouseDown={(e) => handleVertexMouseDown(e, i)}
            />
          );
        })}

        {/* ── Fence draft line + endpoints ── */}
        {lineStart && (
          <>
            {fencePreview && (
              <line
                x1={lineStart.x} y1={lineStart.y}
                x2={fencePreview.to.x} y2={fencePreview.to.y}
                stroke="#facc15"
                strokeWidth={1.5}
                strokeDasharray="5 3"
                style={{ pointerEvents: 'none' }}
              />
            )}
            {lineEnd && (
              <line
                x1={lineStart.x} y1={lineStart.y}
                x2={lineEnd.x} y2={lineEnd.y}
                stroke="#facc15"
                strokeWidth={2}
                markerEnd={`url(#${ARROW_MARKER})`}
              />
            )}
            <circle
              cx={lineStart.x} cy={lineStart.y} r={6}
              fill="#facc15" stroke="#fff" strokeWidth={1.5}
              style={{ cursor: 'move' }}
              onMouseDown={(e) => handleLineEndpointDrag('start', e)}
            />
            {lineEnd && (
              <circle
                cx={lineEnd.x} cy={lineEnd.y} r={6}
                fill="#facc15" stroke="#fff" strokeWidth={1.5}
                style={{ cursor: 'move' }}
                onMouseDown={(e) => handleLineEndpointDrag('end', e)}
              />
            )}
          </>
        )}
      </svg>
    </div>
  );
};

// ─── Inline button style ──────────────────────────────────────────────────────
const btnStyle: React.CSSProperties = {
  background: 'rgba(255,255,255,0.07)',
  border: '1px solid rgba(255,255,255,0.12)',
  borderRadius: 4,
  color: '#cbd5e1',
  fontSize: 10,
  fontFamily: 'monospace',
  padding: '2px 7px',
  cursor: 'pointer',
};
