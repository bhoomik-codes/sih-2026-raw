import React, { useState, useEffect } from 'react';
import { X, ArrowRight, ArrowLeft, Check, Camera as CameraIcon, Video, Globe, HardDrive } from 'lucide-react';
import { CameraCreatePayload, CameraSourceType } from '../../types/camera';

interface WizardProps {
  onClose: () => void;
  onSubmit: (data: CameraCreatePayload) => Promise<void>;
}

export const CameraConnectionWizard: React.FC<WizardProps> = ({ onClose, onSubmit }) => {
  const [step, setStep] = useState(1);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Wizard Data
  const [sourceType, setSourceType] = useState<CameraSourceType>('rtsp');
  const [rtspConfig, setRtspConfig] = useState({ ip: '', port: '554', user: '', pass: '', path: '/stream' });
  const [httpConfig, setHttpConfig] = useState({ url: 'http://192.168.1.100:8080/video' });
  const [usbConfig, setUsbConfig] = useState({ index: '0' });
  const [fileConfig, setFileConfig] = useState({ path: 'data/videos/test_video.mp4' });
  
  const [metadata, setMetadata] = useState({
    camera_id: `CAM-${Math.floor(Math.random() * 10000)}`,
    name: '',
    inference_enabled: true
  });

  const [generatedUrl, setGeneratedUrl] = useState('');

  // Auto-generate URL based on current config
  useEffect(() => {
    switch (sourceType) {
      case 'rtsp':
        let auth = '';
        if (rtspConfig.user || rtspConfig.pass) {
          auth = `${rtspConfig.user}:${rtspConfig.pass}@`;
        }
        setGeneratedUrl(`rtsp://${auth}${rtspConfig.ip || '0.0.0.0'}:${rtspConfig.port}${rtspConfig.path}`);
        break;
      case 'http':
      case 'mjpeg':
        setGeneratedUrl(httpConfig.url);
        break;
      case 'usb':
        setGeneratedUrl(usbConfig.index);
        break;
      case 'file':
        setGeneratedUrl(fileConfig.path);
        break;
    }
  }, [sourceType, rtspConfig, httpConfig, usbConfig, fileConfig]);

  const handleNext = () => {
    setError(null);
    if (step === 2) {
      // Validate
      if (sourceType === 'rtsp' && !rtspConfig.ip) {
        setError('IP Address is required for RTSP.');
        return;
      }
      if (!generatedUrl) {
        setError('Source URL cannot be empty.');
        return;
      }
    }
    if (step < 3) setStep(step + 1);
  };

  const handleSubmit = async () => {
    if (!metadata.camera_id || !metadata.name) {
      setError('Camera ID and Name are required.');
      return;
    }
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      await onSubmit({
        camera_id: metadata.camera_id,
        name: metadata.name,
        source_type: sourceType,
        source_url: generatedUrl,
        inference_enabled: metadata.inference_enabled
      });
      // Close is handled by parent on success
    } catch (err: any) {
      setError(err.message || 'Failed to submit camera');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-lg shadow-xl w-full max-w-2xl overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          <h2 className="text-lg font-semibold text-white">Add New Camera</h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-800 rounded text-slate-400">
            <X size={20} />
          </button>
        </div>

        {/* Progress Bar */}
        <div className="flex bg-slate-950 p-4 border-b border-slate-800">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex-1 flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
                ${step === s ? 'bg-blue-600 text-white' : step > s ? 'bg-green-600 text-white' : 'bg-slate-800 text-slate-400'}`}>
                {step > s ? <Check size={16} /> : s}
              </div>
              {s < 3 && (
                <div className={`flex-1 h-1 mx-2 ${step > s ? 'bg-green-600' : 'bg-slate-800'}`} />
              )}
            </div>
          ))}
        </div>

        {/* Wizard Content */}
        <div className="p-6 flex-1 min-h-[300px]">
          {error && (
            <div className="mb-4 p-3 bg-red-900/30 border border-red-500/50 rounded text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* STEP 1: Type Selection */}
          {step === 1 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium text-white mb-4">Select Source Type</h3>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setSourceType('rtsp')}
                  className={`p-4 rounded-lg border text-left flex flex-col gap-2 transition-colors ${sourceType === 'rtsp' ? 'border-blue-500 bg-blue-900/20' : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'}`}
                >
                  <CameraIcon className={sourceType === 'rtsp' ? 'text-blue-400' : 'text-slate-400'} size={24} />
                  <span className="font-semibold text-white">RTSP IP Camera</span>
                  <span className="text-xs text-slate-400">Standard network camera (CCTV)</span>
                </button>
                <button
                  onClick={() => setSourceType('usb')}
                  className={`p-4 rounded-lg border text-left flex flex-col gap-2 transition-colors ${sourceType === 'usb' ? 'border-blue-500 bg-blue-900/20' : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'}`}
                >
                  <Video className={sourceType === 'usb' ? 'text-blue-400' : 'text-slate-400'} size={24} />
                  <span className="font-semibold text-white">USB Webcam</span>
                  <span className="text-xs text-slate-400">Directly connected camera</span>
                </button>
                <button
                  onClick={() => setSourceType('http')}
                  className={`p-4 rounded-lg border text-left flex flex-col gap-2 transition-colors ${sourceType === 'http' ? 'border-blue-500 bg-blue-900/20' : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'}`}
                >
                  <Globe className={sourceType === 'http' ? 'text-blue-400' : 'text-slate-400'} size={24} />
                  <span className="font-semibold text-white">HTTP / MJPEG</span>
                  <span className="text-xs text-slate-400">Mobile app or legacy IP cam stream</span>
                </button>
                <button
                  onClick={() => setSourceType('file')}
                  className={`p-4 rounded-lg border text-left flex flex-col gap-2 transition-colors ${sourceType === 'file' ? 'border-blue-500 bg-blue-900/20' : 'border-slate-700 hover:border-slate-500 bg-slate-800/50'}`}
                >
                  <HardDrive className={sourceType === 'file' ? 'text-blue-400' : 'text-slate-400'} size={24} />
                  <span className="font-semibold text-white">Local Video File</span>
                  <span className="text-xs text-slate-400">Pre-recorded .mp4, .avi</span>
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: Configuration */}
          {step === 2 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium text-white mb-4">Configure Connection</h3>
              
              {sourceType === 'rtsp' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4">
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-slate-400 mb-1">IP Address / Host</label>
                      <input type="text" value={rtspConfig.ip} onChange={e => setRtspConfig({...rtspConfig, ip: e.target.value})} placeholder="192.168.1.50" className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-400 mb-1">Port</label>
                      <input type="text" value={rtspConfig.port} onChange={e => setRtspConfig({...rtspConfig, port: e.target.value})} placeholder="554" className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-400 mb-1">Username (Optional)</label>
                      <input type="text" value={rtspConfig.user} onChange={e => setRtspConfig({...rtspConfig, user: e.target.value})} placeholder="admin" className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-400 mb-1">Password (Optional)</label>
                      <input type="password" value={rtspConfig.pass} onChange={e => setRtspConfig({...rtspConfig, pass: e.target.value})} placeholder="••••••" className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                    </div>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1">Stream Path</label>
                    <input type="text" value={rtspConfig.path} onChange={e => setRtspConfig({...rtspConfig, path: e.target.value})} placeholder="/cam/realmonitor?channel=1" className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                  </div>
                </div>
              )}

              {(sourceType === 'http' || sourceType === 'mjpeg') && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Stream URL</label>
                  <input type="text" value={httpConfig.url} onChange={e => setHttpConfig({url: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                </div>
              )}

              {sourceType === 'usb' && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Device Index</label>
                  <select value={usbConfig.index} onChange={e => setUsbConfig({index: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white">
                    <option value="0">0 (Default Built-in Webcam)</option>
                    <option value="1">1 (External USB Camera 1)</option>
                    <option value="2">2 (External USB Camera 2)</option>
                    <option value="3">3 (External USB Camera 3)</option>
                  </select>
                </div>
              )}

              {sourceType === 'file' && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">File Path</label>
                  <input type="text" value={fileConfig.path} onChange={e => setFileConfig({path: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                  <p className="text-xs text-slate-500 mt-2">Example: data/videos/test_video.mp4</p>
                </div>
              )}

              <div className="mt-6 p-4 bg-black/50 border border-slate-800 rounded">
                <span className="text-xs text-slate-500 block mb-1">Generated Connection String:</span>
                <code className="text-blue-400 break-all">{generatedUrl}</code>
              </div>
            </div>
          )}

          {/* STEP 3: Review */}
          {step === 3 && (
            <div className="space-y-4">
              <h3 className="text-xl font-medium text-white mb-4">Finalize Details</h3>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Camera ID (Unique)</label>
                  <input type="text" value={metadata.camera_id} onChange={e => setMetadata({...metadata, camera_id: e.target.value})} className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1">Display Name</label>
                  <input type="text" value={metadata.name} onChange={e => setMetadata({...metadata, name: e.target.value})} placeholder="Main Gate" className="w-full bg-slate-950 border border-slate-700 rounded px-3 py-2 text-white" />
                </div>
              </div>

              <div className="flex items-center gap-3 p-3 bg-slate-800/50 border border-slate-700 rounded-lg">
                <input 
                  type="checkbox" 
                  id="inference_enabled"
                  checked={metadata.inference_enabled} 
                  onChange={e => setMetadata({...metadata, inference_enabled: e.target.checked})}
                  className="w-4 h-4 text-blue-600 rounded bg-slate-900 border-slate-700" 
                />
                <div>
                  <label htmlFor="inference_enabled" className="text-sm font-medium text-white block">Run Edge AI Inference</label>
                  <span className="text-xs text-slate-400">If disabled, the stream will only be viewed, not analyzed.</span>
                </div>
              </div>
              
              <div className="mt-4 p-4 bg-black/50 border border-slate-800 rounded space-y-2">
                <div className="flex justify-between"><span className="text-slate-400 text-sm">Source Type:</span> <span className="text-white text-sm font-mono">{sourceType.toUpperCase()}</span></div>
                <div className="flex justify-between"><span className="text-slate-400 text-sm">URL:</span> <span className="text-blue-400 text-sm font-mono break-all">{generatedUrl}</span></div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-800 flex justify-between bg-slate-900">
          <button
            onClick={() => step > 1 ? setStep(step - 1) : onClose()}
            className="px-4 py-2 rounded font-medium text-slate-300 hover:bg-slate-800 flex items-center gap-2"
          >
            {step > 1 ? <><ArrowLeft size={16} /> Back</> : 'Cancel'}
          </button>
          
          <button
            onClick={step === 3 ? handleSubmit : handleNext}
            disabled={isSubmitting}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium flex items-center gap-2 disabled:opacity-50"
          >
            {step === 3 ? (
              isSubmitting ? 'Registering...' : <><Check size={16} /> Register Camera</>
            ) : (
              <>Next <ArrowRight size={16} /></>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
