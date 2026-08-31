import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  UserCheck,
  UserX,
  Plus,
  Trash2,
  Edit3,
  Save,
  X,
  Upload,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Shield,
  ShieldAlert,
  Info,
  Camera,
} from 'lucide-react';
import { FaceRecord, FaceRole, CreateFacePayload, UpdateFacePayload } from '../types/face';
import { getFaces, createFace, updateFace, deleteFace } from '../api/faces';

// ─── Types ────────────────────────────────────────────────────────────────────

interface StatusMsg {
  type: 'success' | 'error' | 'info';
  text: string;
}

// ─── Main Component ───────────────────────────────────────────────────────────

export const FaceRegistryPage: React.FC = () => {
  const [faces, setFaces] = useState<FaceRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<StatusMsg | null>(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addRole, setAddRole] = useState<FaceRole>('SOLDIER');
  const [editingId, setEditingId] = useState<string | null>(null);

  const loadFaces = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await getFaces();
      setFaces(data);
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to load face registry' });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFaces();
  }, [loadFaces]);

  const soldiers = faces.filter((f) => f.role === 'SOLDIER');
  const intruders = faces.filter((f) => f.role === 'INTRUDER');

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Remove "${name}" from the face registry?`)) return;
    try {
      await deleteFace(id);
      setStatusMsg({ type: 'success', text: `"${name}" removed from registry.` });
      loadFaces();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to delete face record' });
    }
  };

  const handleEdit = (id: string) => {
    setEditingId(id);
  };

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden">
      {/* ── Page Header ── */}
      <div className="flex-shrink-0 bg-[#0c141f] border-b border-[#232a36] px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded bg-violet-500/10 border border-violet-500/30 flex items-center justify-center">
              <UserCheck className="w-4 h-4 text-violet-400" />
            </div>
            <div>
              <h1 className="text-sm font-bold text-slate-100 uppercase tracking-widest font-mono">
                Face Registry
              </h1>
              <p className="text-[11px] text-slate-500 font-mono">
                {soldiers.length} soldiers · {intruders.length} intruders · Recognition{' '}
                <span className="text-emerald-400 font-semibold">ACTIVE</span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={loadFaces}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-[11px] font-mono transition"
            >
              <RefreshCw className={`w-3 h-3 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={() => { setAddRole('SOLDIER'); setShowAddModal(true); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-600/80 hover:bg-emerald-500 border border-emerald-500/50 text-white text-[11px] font-mono font-semibold transition"
            >
              <Shield className="w-3.5 h-3.5" />
              Add Soldier
            </button>
            <button
              onClick={() => { setAddRole('INTRUDER'); setShowAddModal(true); }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-rose-700/80 hover:bg-rose-600 border border-rose-600/50 text-white text-[11px] font-mono font-semibold transition"
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              Add Intruder
            </button>
          </div>
        </div>
      </div>

      {/* ── Status Message ── */}
      {statusMsg && (
        <div
          className={`mx-6 mt-3 p-3 rounded-lg border text-xs flex items-center space-x-2 flex-shrink-0 ${
            statusMsg.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
              : statusMsg.type === 'info'
              ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400'
          }`}
        >
          {statusMsg.type === 'success' ? (
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
          ) : statusMsg.type === 'info' ? (
            <Info className="w-4 h-4 flex-shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
          )}
          <span className="flex-1">{statusMsg.text}</span>
          <button onClick={() => setStatusMsg(null)} className="ml-auto opacity-60 hover:opacity-100">
            <X className="w-3 h-3" />
          </button>
        </div>
      )}

      {/* ── Info Banner ── */}
      <div className="mx-6 mt-3 p-3 rounded-lg bg-blue-500/5 border border-blue-500/20 text-[11px] text-blue-400 flex items-start space-x-2 flex-shrink-0 font-mono">
        <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
        <span>
          <strong>How it works:</strong> Soldier faces suppress security alerts when recognized by the
          edge camera. Intruder faces trigger an instant <strong>CRITICAL</strong> incident alert. The
          edge engine syncs this registry every 30 seconds. For best accuracy, upload a clear
          front-facing photo (min 100×100 px).
        </span>
      </div>

      {/* ── Two-column Sections ── */}
      <div className="flex-1 overflow-y-auto p-6 grid grid-cols-1 xl:grid-cols-2 gap-6 min-h-0">
        {/* Soldiers Section */}
        <FaceSection
          title="Soldiers & Officials"
          subtitle="Recognized personnel — alerts suppressed"
          role="SOLDIER"
          records={soldiers}
          accentColor="emerald"
          icon={<Shield className="w-4 h-4 text-emerald-400" />}
          onDelete={handleDelete}
          onEdit={handleEdit}
          editingId={editingId}
          setEditingId={setEditingId}
          onRefresh={loadFaces}
          onAdd={() => { setAddRole('SOLDIER'); setShowAddModal(true); }}
          setStatusMsg={setStatusMsg}
        />

        {/* Intruders Section */}
        <FaceSection
          title="Known Intruders"
          subtitle="Flagged individuals — instant critical alert"
          role="INTRUDER"
          records={intruders}
          accentColor="rose"
          icon={<ShieldAlert className="w-4 h-4 text-rose-400" />}
          onDelete={handleDelete}
          onEdit={handleEdit}
          editingId={editingId}
          setEditingId={setEditingId}
          onRefresh={loadFaces}
          onAdd={() => { setAddRole('INTRUDER'); setShowAddModal(true); }}
          setStatusMsg={setStatusMsg}
        />
      </div>

      {/* ── Add Modal ── */}
      {showAddModal && (
        <AddFaceModal
          role={addRole}
          onClose={() => setShowAddModal(false)}
          onSaved={() => { setShowAddModal(false); loadFaces(); setStatusMsg({ type: 'success', text: 'Face record saved successfully.' }); }}
          setStatusMsg={setStatusMsg}
        />
      )}
    </div>
  );
};

// ─── Face Section ─────────────────────────────────────────────────────────────

interface FaceSectionProps {
  title: string;
  subtitle: string;
  role: FaceRole;
  records: FaceRecord[];
  accentColor: 'emerald' | 'rose';
  icon: React.ReactNode;
  onDelete: (id: string, name: string) => void;
  onEdit: (id: string) => void;
  editingId: string | null;
  setEditingId: (id: string | null) => void;
  onRefresh: () => void;
  onAdd: () => void;
  setStatusMsg: (msg: StatusMsg | null) => void;
}

const FaceSection: React.FC<FaceSectionProps> = ({
  title,
  subtitle,
  role,
  records,
  accentColor,
  icon,
  onDelete,
  onEdit,
  editingId,
  setEditingId,
  onRefresh,
  onAdd,
  setStatusMsg,
}) => {
  const borderColor = accentColor === 'emerald' ? 'border-emerald-500/20' : 'border-rose-500/20';
  const bgColor = accentColor === 'emerald' ? 'bg-emerald-500/5' : 'bg-rose-500/5';
  const titleColor = accentColor === 'emerald' ? 'text-emerald-400' : 'text-rose-400';
  const badgeBg = accentColor === 'emerald' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300';

  return (
    <div className={`rounded-lg border ${borderColor} ${bgColor} flex flex-col min-h-[300px]`}>
      {/* Section Header */}
      <div className="p-4 border-b border-slate-800/60 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          {icon}
          <div>
            <div className={`text-xs font-bold font-mono uppercase tracking-wider ${titleColor}`}>
              {title}
            </div>
            <div className="text-[10px] text-slate-500 font-mono">{subtitle}</div>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded ${badgeBg}`}>
            {records.length} enrolled
          </span>
          <button
            onClick={onAdd}
            className={`flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-mono font-semibold transition ${
              accentColor === 'emerald'
                ? 'bg-emerald-600/30 hover:bg-emerald-600/60 border border-emerald-500/40 text-emerald-300'
                : 'bg-rose-700/30 hover:bg-rose-600/60 border border-rose-500/40 text-rose-300'
            }`}
          >
            <Plus className="w-3 h-3" />
            Add
          </button>
        </div>
      </div>

      {/* Records Grid */}
      <div className="flex-1 p-4 overflow-y-auto">
        {records.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center space-y-2">
            <div className={`opacity-20 ${titleColor}`}>
              {role === 'SOLDIER' ? (
                <Shield className="w-10 h-10" />
              ) : (
                <ShieldAlert className="w-10 h-10" />
              )}
            </div>
            <div className="text-xs text-slate-500 font-mono">No {role.toLowerCase()} faces enrolled</div>
            <button
              onClick={onAdd}
              className="text-[11px] text-slate-400 hover:text-slate-200 underline font-mono transition"
            >
              + Add first entry
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {records.map((record) =>
              editingId === record.id ? (
                <EditFaceCard
                  key={record.id}
                  record={record}
                  accentColor={accentColor}
                  onCancel={() => setEditingId(null)}
                  onSaved={() => { setEditingId(null); onRefresh(); setStatusMsg({ type: 'success', text: `"${record.name}" updated.` }); }}
                />
              ) : (
                <FaceCard
                  key={record.id}
                  record={record}
                  accentColor={accentColor}
                  onDelete={() => onDelete(record.id, record.name)}
                  onEdit={() => onEdit(record.id)}
                />
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Face Card ────────────────────────────────────────────────────────────────

interface FaceCardProps {
  record: FaceRecord;
  accentColor: 'emerald' | 'rose';
  onDelete: () => void;
  onEdit: () => void;
}

const FaceCard: React.FC<FaceCardProps> = ({ record, accentColor, onDelete, onEdit }) => {
  const borderColor = accentColor === 'emerald' ? 'border-emerald-500/20 hover:border-emerald-500/50' : 'border-rose-500/20 hover:border-rose-500/50';
  const badgeColor = accentColor === 'emerald' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300';

  return (
    <div
      className={`group relative rounded-lg border ${borderColor} bg-slate-900/60 overflow-hidden transition-all`}
    >
      {/* Photo */}
      <div className="aspect-square bg-slate-800/60 flex items-center justify-center overflow-hidden">
        {record.image_b64 ? (
          <img
            src={`data:image/jpeg;base64,${record.image_b64}`}
            alt={record.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center justify-center text-slate-600">
            <UserCheck className="w-8 h-8" />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-2">
        <div className="text-[11px] font-bold text-slate-200 font-mono truncate">{record.name}</div>
        <div className={`text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded mt-1 inline-block ${badgeColor}`}>
          {record.role}
        </div>
        {record.notes && (
          <div className="text-[10px] text-slate-500 font-mono mt-1 truncate">{record.notes}</div>
        )}
        <div className="text-[9px] text-slate-600 font-mono mt-0.5">
          {new Date(record.created_at).toLocaleDateString()}
        </div>
      </div>

      {/* Action overlay */}
      <div className="absolute inset-0 bg-slate-950/80 opacity-0 group-hover:opacity-100 transition flex items-center justify-center gap-2">
        <button
          onClick={onEdit}
          className="p-2 rounded bg-slate-700 hover:bg-slate-600 text-slate-200 transition"
          title="Edit"
        >
          <Edit3 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={onDelete}
          className="p-2 rounded bg-rose-700/60 hover:bg-rose-600 text-rose-300 transition"
          title="Delete"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

// ─── Edit Face Card ───────────────────────────────────────────────────────────

interface EditFaceCardProps {
  record: FaceRecord;
  accentColor: 'emerald' | 'rose';
  onCancel: () => void;
  onSaved: () => void;
}

const EditFaceCard: React.FC<EditFaceCardProps> = ({ record, accentColor, onCancel, onSaved }) => {
  const [name, setName] = useState(record.name);
  const [role, setRole] = useState<FaceRole>(record.role);
  const [notes, setNotes] = useState(record.notes || '');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      const patch: UpdateFacePayload = { name, role, notes: notes || undefined };
      await updateFace(record.id, patch);
      onSaved();
    } catch {
      // swallow; parent will show error via refresh
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-lg border border-blue-500/40 bg-slate-900 p-3 space-y-2">
      <input
        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100 font-mono"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="Name"
      />
      <select
        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 font-mono"
        value={role}
        onChange={(e) => setRole(e.target.value as FaceRole)}
      >
        <option value="SOLDIER">SOLDIER</option>
        <option value="INTRUDER">INTRUDER</option>
      </select>
      <input
        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-100 font-mono"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Notes (rank, unit…)"
      />
      <div className="flex gap-1.5">
        <button
          onClick={handleSave}
          disabled={saving || !name}
          className="flex-1 flex items-center justify-center gap-1 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-[10px] font-mono rounded transition"
        >
          <Save className="w-3 h-3" />
          {saving ? 'Saving…' : 'Save'}
        </button>
        <button
          onClick={onCancel}
          className="p-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-400 transition"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    </div>
  );
};

// ─── Add Face Modal ───────────────────────────────────────────────────────────

interface AddFaceModalProps {
  role: FaceRole;
  onClose: () => void;
  onSaved: () => void;
  setStatusMsg: (msg: StatusMsg | null) => void;
}

const AddFaceModal: React.FC<AddFaceModalProps> = ({ role: initialRole, onClose, onSaved, setStatusMsg }) => {
  const [name, setName] = useState('');
  const [selectedRole, setSelectedRole] = useState<FaceRole>(initialRole);
  const [notes, setNotes] = useState('');
  const [imageB64, setImageB64] = useState<string | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const processFile = (file: File) => {
    if (!file.type.startsWith('image/')) {
      setStatusMsg({ type: 'error', text: 'Please upload an image file (JPEG, PNG, etc.)' });
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result as string;
      // result is data:image/jpeg;base64,XXXXX
      const b64 = result.split(',')[1];
      setImageB64(b64);
      setImagePreview(result);
    };
    reader.readAsDataURL(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) processFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  };

  const handleSave = async () => {
    if (!name || !imageB64) return;
    setIsSaving(true);
    try {
      const payload: CreateFacePayload = {
        name,
        role: selectedRole,
        image_b64: imageB64,
        notes: notes || undefined,
      };
      await createFace(payload);
      onSaved();
    } catch (err: any) {
      setStatusMsg({ type: 'error', text: err.message || 'Failed to save face record' });
    } finally {
      setIsSaving(false);
    }
  };

  const isIntruder = selectedRole === 'INTRUDER';
  const accentBg = isIntruder ? 'from-rose-900/40' : 'from-emerald-900/30';
  const accentBorder = isIntruder ? 'border-rose-500/30' : 'border-emerald-500/30';
  const accentBtn = isIntruder ? 'bg-rose-700 hover:bg-rose-600' : 'bg-emerald-700 hover:bg-emerald-600';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm">
      <div className={`w-full max-w-md bg-gradient-to-b ${accentBg} to-slate-900 border ${accentBorder} rounded-xl shadow-2xl overflow-hidden`}>
        {/* Modal Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {isIntruder ? (
              <ShieldAlert className="w-4 h-4 text-rose-400" />
            ) : (
              <Shield className="w-4 h-4 text-emerald-400" />
            )}
            <span className="text-sm font-bold text-slate-100 font-mono">
              Enroll {isIntruder ? 'Known Intruder' : 'Soldier / Official'}
            </span>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-slate-300 transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-5 space-y-4">
          {/* Role Toggle */}
          <div>
            <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
              Registry Type
            </label>
            <div className="mt-1.5 flex rounded-lg overflow-hidden border border-slate-700">
              <button
                onClick={() => setSelectedRole('SOLDIER')}
                className={`flex-1 py-2 text-[11px] font-mono font-semibold transition flex items-center justify-center gap-1.5 ${
                  selectedRole === 'SOLDIER'
                    ? 'bg-emerald-700/60 text-emerald-200'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                <Shield className="w-3 h-3" />
                Soldier / Official
              </button>
              <button
                onClick={() => setSelectedRole('INTRUDER')}
                className={`flex-1 py-2 text-[11px] font-mono font-semibold transition flex items-center justify-center gap-1.5 ${
                  selectedRole === 'INTRUDER'
                    ? 'bg-rose-700/60 text-rose-200'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                <ShieldAlert className="w-3 h-3" />
                Known Intruder
              </button>
            </div>
          </div>

          {/* Name */}
          <div>
            <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
              Full Name / ID
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={isIntruder ? 'e.g. Suspect-Alpha-7' : 'e.g. Cpl. Ravi Kumar'}
              className="mt-1.5 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono placeholder:text-slate-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Notes */}
          <div>
            <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
              Notes (optional)
            </label>
            <input
              type="text"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={isIntruder ? 'e.g. Last seen border sector 4' : 'e.g. 3 RAJPUT, Sector 4'}
              className="mt-1.5 w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono placeholder:text-slate-600 focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Photo Upload */}
          <div>
            <label className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
              Reference Photo *
            </label>
            <div
              className={`mt-1.5 border-2 border-dashed rounded-lg transition cursor-pointer ${
                dragOver
                  ? 'border-blue-400 bg-blue-500/10'
                  : 'border-slate-700 hover:border-slate-500'
              }`}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              {imagePreview ? (
                <div className="relative">
                  <img
                    src={imagePreview}
                    alt="Preview"
                    className="w-full h-40 object-cover rounded-lg"
                  />
                  <div className="absolute inset-0 bg-slate-950/40 flex items-center justify-center rounded-lg opacity-0 hover:opacity-100 transition">
                    <span className="text-[11px] font-mono text-slate-200">Click to change</span>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-slate-500 space-y-2">
                  <Upload className="w-6 h-6" />
                  <span className="text-[11px] font-mono">
                    Drag & drop or click to upload photo
                  </span>
                  <span className="text-[10px] font-mono text-slate-600">
                    JPEG, PNG — front-facing, min 100×100 px
                  </span>
                </div>
              )}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {/* Intruder warning */}
          {isIntruder && (
            <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-[10px] text-rose-400 font-mono flex items-start gap-2">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
              <span>
                This person will trigger a <strong>CRITICAL</strong> incident alert immediately when
                recognized by any active camera.
              </span>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-4 border-t border-slate-800 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isSaving || !name || !imageB64}
            className={`flex items-center gap-2 px-5 py-2 rounded-lg ${accentBtn} disabled:opacity-50 text-white text-xs font-mono font-semibold transition`}
          >
            {isSaving ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            {isSaving ? 'Processing…' : 'Enroll Face'}
          </button>
        </div>
      </div>
    </div>
  );
};
