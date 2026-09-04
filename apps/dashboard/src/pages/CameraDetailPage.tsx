import React, { useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  Edit3,
  Plus,
  Trash2,
  XCircle,
} from 'lucide-react';
import { Camera, FenceLine, Zone } from '../types/camera';
import { updateCameraFence, updateCameraZones } from '../api/cameras';
import { LiveStream } from '../components/cameras/LiveStream';
import { ZoneEditor } from '../components/cameras/ZoneEditor';
import { EmptyState } from '../components/common/EmptyState';

interface CameraDetailPageProps {
  cameras: Camera[];
  selectedCamera: Camera | null;
  selectedCameraId: string | null;
  onSelectCamera: (id: string) => void;
  onRefresh: () => void;
}

export const CameraDetailPage: React.FC<CameraDetailPageProps> = ({
  cameras,
  selectedCamera,
  selectedCameraId,
  onSelectCamera,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<'zones' | 'fences'>('zones');

  // Form fields — zone
  const [newZoneName, setNewZoneName] = useState<string>('');
  const [newZoneType, setNewZoneType] = useState<'restricted' | 'loitering'>('restricted');
  const [newZoneSeverity, setNewZoneSeverity] = useState<'low' | 'medium' | 'high' | 'critical'>('high');

  // Form fields — fence
  const [newLineName, setNewLineName] = useState<string>('');
  const [newLineSeverity, setNewLineSeverity] = useState<'low' | 'medium' | 'high' | 'critical'>('critical');

  // Drawing state
  const [drawingActive, setDrawingActive] = useState<boolean>(false);
  const [draftPolygon, setDraftPolygon] = useState<[number, number][] | null>(null);
  const [draftLine, setDraftLine] = useState<{ start: [number, number]; end: [number, number] } | null>(null);

  // Status
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  if (cameras.length === 0) {
    return (
      <div className="flex-1 p-6">
        <EmptyState
          title="No cameras available"
          message="Add a camera in Camera Management before configuring zones"
        />
      </div>
    );
  }

  const camera = selectedCamera || cameras[0];

  // ── Drawing callbacks ────────────────────────────────────────────────────
  const handlePolygonComplete = (polygon: [number, number][]) => {
    setDraftPolygon(polygon);
    setDrawingActive(false);
    setStatusMessage({ type: 'success', text: 'Polygon drawn — give it a name and click Save.' });
  };

  const handleLineComplete = (start: [number, number], end: [number, number]) => {
    setDraftLine({ start, end });
    setDrawingActive(false);
    setStatusMessage({ type: 'success', text: 'Tripwire drawn — give it a name and click Save.' });
  };

  const handleClear = () => {
    setDraftPolygon(null);
    setDraftLine(null);
    setStatusMessage(null);
  };

  const handleDrawingDone = () => {
    setDrawingActive(false);
  };

  const startDrawing = () => {
    // Clear current draft when starting a new one
    setDraftPolygon(null);
    setDraftLine(null);
    setStatusMessage(null);
    setDrawingActive(true);
  };

  const cancelDrawing = () => {
    setDrawingActive(false);
    setDraftPolygon(null);
    setDraftLine(null);
    setStatusMessage(null);
  };

  // ── Zone save/delete ─────────────────────────────────────────────────────
  const handleAddZone = async () => {
    if (!newZoneName || !camera) return;
    setIsSaving(true);
    setStatusMessage(null);
    try {
      const currentZones = camera.zones || [];
      const polygon: [number, number][] = draftPolygon || [
        [0, 360],
        [960, 360],
        [960, 720],
        [0, 720],
      ];
      const updatedZones: Zone[] = [
        ...currentZones,
        {
          name: newZoneName,
          type: newZoneType,
          severity: newZoneSeverity,
          polygon,
          classes: ['person'],
        },
      ];
      await updateCameraZones(camera.camera_id, updatedZones);
      setStatusMessage({ type: 'success', text: `Zone '${newZoneName}' saved to edge engine.` });
      setNewZoneName('');
      setDraftPolygon(null);
      onRefresh();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to save zone' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteZone = async (zoneName: string) => {
    if (!camera) return;
    setIsSaving(true);
    setStatusMessage(null);
    try {
      const updatedZones = (camera.zones || []).filter((z) => z.name !== zoneName);
      await updateCameraZones(camera.camera_id, updatedZones);
      setStatusMessage({ type: 'success', text: `Zone '${zoneName}' removed.` });
      onRefresh();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to remove zone' });
    } finally {
      setIsSaving(false);
    }
  };

  // ── Fence save/delete ────────────────────────────────────────────────────
  const handleAddFence = async () => {
    if (!newLineName || !camera) return;
    setIsSaving(true);
    setStatusMessage(null);
    try {
      const currentLines = camera.lines || [];
      const updatedLines: FenceLine[] = [
        ...currentLines,
        {
          name: newLineName,
          start: draftLine?.start || [0, 350],
          end: draftLine?.end || [960, 350],
          direction: 'any',
          severity: newLineSeverity,
          classes: ['person'],
        },
      ];
      await updateCameraFence(camera.camera_id, updatedLines);
      setStatusMessage({ type: 'success', text: `Virtual Fence '${newLineName}' saved to edge engine.` });
      setNewLineName('');
      setDraftLine(null);
      onRefresh();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to save fence' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleDeleteFence = async (lineName: string) => {
    if (!camera) return;
    setIsSaving(true);
    setStatusMessage(null);
    try {
      const updatedLines = (camera.lines || []).filter((l) => l.name !== lineName);
      await updateCameraFence(camera.camera_id, updatedLines);
      setStatusMessage({ type: 'success', text: `Fence '${lineName}' removed.` });
      onRefresh();
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || 'Failed to remove fence' });
    } finally {
      setIsSaving(false);
    }
  };

  // ── Derived state ────────────────────────────────────────────────────────
  const hasDraft = activeTab === 'zones' ? !!draftPolygon : !!draftLine;
  const canSaveZone = !!newZoneName && !isSaving && !drawingActive;
  const canSaveFence = !!newLineName && !isSaving && !drawingActive;

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-4 space-y-3">
      {/* Top Bar: Camera Selector */}
      <div className="flex items-center justify-between bg-slate-900 px-4 py-2.5 rounded-lg border border-slate-800">
        <div className="flex items-center space-x-3">
          <span className="text-xs font-bold text-slate-100 uppercase tracking-wider">
            Select Camera:
          </span>
          <select
            value={camera.camera_id}
            onChange={(e) => onSelectCamera(e.target.value)}
            className="bg-slate-950 border border-slate-700 rounded px-3 py-1 text-xs text-slate-100 font-mono focus:outline-none focus:border-blue-500"
          >
            {cameras.map((c) => (
              <option key={c.camera_id} value={c.camera_id}>
                {c.name || c.camera_id} ({c.camera_id})
              </option>
            ))}
          </select>
        </div>

        <div className="text-xs font-mono text-slate-400">
          Source: <span className="text-slate-200">{camera.source_url}</span>
        </div>
      </div>

      {statusMessage && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center space-x-2 ${
            statusMessage.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
          }`}
        >
          {statusMessage.type === 'success' ? (
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* Main Area */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-3 min-h-0">

        {/* ── Stream Area with ZoneEditor overlay (7 cols) ── */}
        <div className="md:col-span-7 h-full min-h-[280px] relative">
          {/* The LiveStream img + overlay share a positioned container */}
          <div className="relative w-full h-full rounded-sm overflow-hidden">
            <LiveStream camera={camera} className="absolute inset-0 w-full h-full" />
            <ZoneEditor
              mode={activeTab}
              drawingActive={drawingActive}
              existingZones={camera.zones || []}
              existingLines={camera.lines || []}
              onPolygonComplete={handlePolygonComplete}
              onLineComplete={handleLineComplete}
              onClear={handleClear}
              onDrawingDone={handleDrawingDone}
            />
          </div>
        </div>

        {/* ── Configuration Area (5 cols) ── */}
        <div className="md:col-span-5 bg-slate-900 rounded-lg border border-slate-800 flex flex-col h-full overflow-hidden">
          {/* Tabs */}
          <div className="flex border-b border-slate-800 bg-slate-950/60 p-1">
            <button
              onClick={() => { setActiveTab('zones'); cancelDrawing(); }}
              className={`flex-1 py-1.5 text-xs font-semibold rounded transition ${
                activeTab === 'zones'
                  ? 'bg-slate-800 text-slate-100 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Polygon Zones ({camera.zones?.length || 0})
            </button>
            <button
              onClick={() => { setActiveTab('fences'); cancelDrawing(); }}
              className={`flex-1 py-1.5 text-xs font-semibold rounded transition ${
                activeTab === 'fences'
                  ? 'bg-slate-800 text-slate-100 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Virtual Tripwires ({camera.lines?.length || 0})
            </button>
          </div>

          {/* Tab Content */}
          <div className="flex-1 p-3 overflow-y-auto space-y-3 text-xs">
            {activeTab === 'zones' ? (
              <div className="space-y-3">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
                  <div className="font-semibold text-slate-200">Add Polygon Zone</div>

                  {/* Draw on stream button */}
                  <div className="flex items-center gap-2">
                    {!drawingActive ? (
                      <button
                        onClick={startDrawing}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-blue-600/20 hover:bg-blue-600/40 border border-blue-500/40 text-blue-300 text-[11px] font-mono font-semibold transition w-full justify-center"
                      >
                        <Edit3 className="w-3 h-3" />
                        {draftPolygon ? '✓ Re-draw on Stream' : 'Draw on Stream'}
                      </button>
                    ) : (
                      <button
                        onClick={cancelDrawing}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-600/20 hover:bg-rose-600/40 border border-rose-500/40 text-rose-300 text-[11px] font-mono font-semibold transition w-full justify-center"
                      >
                        <XCircle className="w-3 h-3" />
                        Cancel Drawing
                      </button>
                    )}
                  </div>

                  {/* Show drawn coordinates badge */}
                  {draftPolygon && (
                    <div className="px-2 py-1 bg-blue-500/10 border border-blue-500/20 rounded text-[10px] font-mono text-blue-300">
                      ✓ Polygon ready — {draftPolygon.length} vertices
                    </div>
                  )}
                  {!draftPolygon && !drawingActive && (
                    <div className="px-2 py-1 bg-slate-800/60 border border-slate-700/40 rounded text-[10px] font-mono text-slate-500">
                      No polygon drawn — will use default full-frame zone
                    </div>
                  )}

                  <div className="space-y-2">
                    <input
                      type="text"
                      placeholder="Zone Name (e.g. restricted_zone)"
                      value={newZoneName}
                      onChange={(e) => setNewZoneName(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-slate-100 font-mono"
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <select
                        value={newZoneType}
                        onChange={(e) => setNewZoneType(e.target.value as any)}
                        className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200 font-mono"
                      >
                        <option value="restricted">Restricted Zone</option>
                        <option value="loitering">Loitering Zone</option>
                      </select>
                      <select
                        value={newZoneSeverity}
                        onChange={(e) => setNewZoneSeverity(e.target.value as any)}
                        className="bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200 font-mono"
                      >
                        <option value="low">Low Severity</option>
                        <option value="medium">Medium Severity</option>
                        <option value="high">High Severity</option>
                        <option value="critical">Critical Severity</option>
                      </select>
                    </div>
                    <button
                      onClick={handleAddZone}
                      disabled={!canSaveZone}
                      className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded font-semibold transition flex items-center justify-center space-x-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Save Zone to Backend</span>
                    </button>
                  </div>
                </div>

                {/* List of Existing Zones */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Configured Zones:
                  </div>
                  {camera.zones && camera.zones.length > 0 ? (
                    camera.zones.map((z) => (
                      <div
                        key={z.name}
                        className="p-2.5 bg-slate-950 rounded border border-slate-800 flex items-center justify-between"
                      >
                        <div className="font-mono">
                          <div className="font-bold text-slate-200">{z.name}</div>
                          <div className="text-[10px] text-slate-400">
                            Type: {z.type || 'restricted'} • Severity: {z.severity || 'high'} • {z.polygon?.length || 0} pts
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteZone(z.name)}
                          disabled={isSaving}
                          className="p-1 rounded text-rose-400 hover:bg-slate-900"
                          title="Delete Zone"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="text-slate-500 text-[11px]">No zones configured on this camera.</div>
                  )}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 space-y-2">
                  <div className="font-semibold text-slate-200">Add Virtual Tripwire Fence</div>

                  {/* Draw on stream button */}
                  <div className="flex items-center gap-2">
                    {!drawingActive ? (
                      <button
                        onClick={startDrawing}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-yellow-600/20 hover:bg-yellow-600/40 border border-yellow-500/40 text-yellow-300 text-[11px] font-mono font-semibold transition w-full justify-center"
                      >
                        <Edit3 className="w-3 h-3" />
                        {draftLine ? '✓ Re-draw on Stream' : 'Draw on Stream'}
                      </button>
                    ) : (
                      <button
                        onClick={cancelDrawing}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-600/20 hover:bg-rose-600/40 border border-rose-500/40 text-rose-300 text-[11px] font-mono font-semibold transition w-full justify-center"
                      >
                        <XCircle className="w-3 h-3" />
                        Cancel Drawing
                      </button>
                    )}
                  </div>

                  {/* Show drawn line badge */}
                  {draftLine && (
                    <div className="px-2 py-1 bg-yellow-500/10 border border-yellow-500/20 rounded text-[10px] font-mono text-yellow-300">
                      ✓ Line ready — [{draftLine.start[0]},{draftLine.start[1]}] → [{draftLine.end[0]},{draftLine.end[1]}]
                    </div>
                  )}
                  {!draftLine && !drawingActive && (
                    <div className="px-2 py-1 bg-slate-800/60 border border-slate-700/40 rounded text-[10px] font-mono text-slate-500">
                      No line drawn — will use default horizontal line
                    </div>
                  )}

                  <div className="space-y-2">
                    <input
                      type="text"
                      placeholder="Fence Name (e.g. border_line)"
                      value={newLineName}
                      onChange={(e) => setNewLineName(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-slate-100 font-mono"
                    />
                    <select
                      value={newLineSeverity}
                      onChange={(e) => setNewLineSeverity(e.target.value as any)}
                      className="w-full bg-slate-900 border border-slate-800 rounded px-2 py-1 text-slate-200 font-mono"
                    >
                      <option value="low">Low Severity</option>
                      <option value="medium">Medium Severity</option>
                      <option value="high">High Severity</option>
                      <option value="critical">Critical Severity</option>
                    </select>
                    <button
                      onClick={handleAddFence}
                      disabled={!canSaveFence}
                      className="w-full py-1.5 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded font-semibold transition flex items-center justify-center space-x-1.5"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Save Fence to Backend</span>
                    </button>
                  </div>
                </div>

                {/* List of Existing Fences */}
                <div className="space-y-1.5">
                  <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                    Configured Tripwires:
                  </div>
                  {camera.lines && camera.lines.length > 0 ? (
                    camera.lines.map((l) => (
                      <div
                        key={l.name}
                        className="p-2.5 bg-slate-950 rounded border border-slate-800 flex items-center justify-between"
                      >
                        <div className="font-mono">
                          <div className="font-bold text-slate-200">{l.name}</div>
                          <div className="text-[10px] text-slate-400">
                            Direction: {l.direction || 'any'} • Severity: {l.severity || 'critical'}
                          </div>
                        </div>
                        <button
                          onClick={() => handleDeleteFence(l.name)}
                          disabled={isSaving}
                          className="p-1 rounded text-rose-400 hover:bg-slate-900"
                          title="Delete Fence"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))
                  ) : (
                    <div className="text-slate-500 text-[11px]">No tripwires configured on this camera.</div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
