import React, { useState } from 'react';
import { 
  AlertTriangle, AlertOctagon, CheckCircle2, ShieldAlert, 
  ArrowRight, Clock, Building2, Zap, Check
} from 'lucide-react';

export default function AlertsView({ 
  alerts, 
  onAcknowledgeAlert, 
  onOpenRoom,
  rooms = [] 
}) {
  const [filter, setFilter] = useState('ACTIVE');

  const activeAlerts = (alerts || []).filter(a => a.status === 'ACTIVE');
  const acknowledgedAlerts = (alerts || []).filter(a => a.status !== 'ACTIVE');

  const displayedAlerts = filter === 'ACTIVE' ? activeAlerts : acknowledgedAlerts;

  const getRoomForAlert = (alert) => {
    return rooms.find(r => r.room.id === alert.room_id) || null;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
            Incident & Anomaly Center
          </h2>
          <p className="text-xs font-medium text-slate-500 mt-0.5">
            Real-time reconciliation of room payment status versus electrical draw
          </p>
        </div>

        <div className="flex items-center gap-2 p-1 bg-slate-100 rounded-xl">
          <button
            onClick={() => setFilter('ACTIVE')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              filter === 'ACTIVE'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Active Incidents ({activeAlerts.length})
          </button>
          <button
            onClick={() => setFilter('RESOLVED')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              filter === 'RESOLVED'
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Resolved ({acknowledgedAlerts.length})
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-500">Active Conflicts</span>
            <div className={`h-7 w-7 rounded-lg flex items-center justify-center ${
              activeAlerts.length > 0 ? 'bg-rose-100 text-rose-600' : 'bg-slate-100 text-slate-400'
            }`}>
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <span className="text-2xl font-extrabold text-slate-900 font-mono">
            {activeAlerts.length}
          </span>
          <p className="text-[11px] text-slate-400 mt-1">Requires staff attention</p>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-500">Theft Prevention Saved</span>
            <div className="h-7 w-7 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center">
              <Zap className="h-4 w-4" />
            </div>
          </div>
          <span className="text-2xl font-extrabold text-emerald-600 font-mono">
            $38.50
          </span>
          <p className="text-[11px] text-slate-400 mt-1">Unbilled power halted</p>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-500">Circuit Reconciliation</span>
            <div className="h-7 w-7 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <span className="text-2xl font-extrabold text-slate-900">
            100%
          </span>
          <p className="text-[11px] text-slate-400 mt-1">Automated 2-second polling</p>
        </div>
      </div>

      <div className="space-y-3">
        {displayedAlerts.length === 0 ? (
          <div className="bg-white border border-slate-200/80 rounded-2xl p-12 text-center shadow-card">
            <div className="h-12 w-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="h-6 w-6" />
            </div>
            <h3 className="text-base font-extrabold text-slate-900">
              {filter === 'ACTIVE' ? 'All Circuits Reconciled' : 'No Resolved Incidents'}
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 leading-relaxed">
              {filter === 'ACTIVE'
                ? 'Every active room with power draw has a confirmed booking. Zero rogue or unauthorized electricity usage detected across the property.'
                : 'No archived incidents found for this session.'}
            </p>
          </div>
        ) : (
          displayedAlerts.map(alert => {
            const isCritical = alert.severity === 'CRITICAL';
            const roomData = getRoomForAlert(alert);

            return (
              <div
                key={alert.id}
                className={`bg-white border rounded-2xl p-5 shadow-card transition flex flex-col md:flex-row md:items-center justify-between gap-4 ${
                  alert.status === 'ACTIVE'
                    ? isCritical 
                      ? 'border-rose-300 ring-2 ring-rose-50' 
                      : 'border-amber-300 ring-2 ring-amber-50'
                    : 'border-slate-200 opacity-75'
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`h-10 w-10 rounded-xl flex items-center justify-center shrink-0 ${
                    alert.status === 'ACTIVE'
                      ? isCritical ? 'bg-rose-100 text-rose-600' : 'bg-amber-100 text-amber-600'
                      : 'bg-slate-100 text-slate-500'
                  }`}>
                    <AlertOctagon className="h-5 w-5" />
                  </div>

                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider ${
                        isCritical ? 'bg-rose-600 text-white' : 'bg-amber-500 text-white'
                      }`}>
                        {alert.severity}
                      </span>
                      <span className="font-extrabold text-sm text-slate-900">
                        {alert.alert_type.replace(/_/g, ' ')}
                      </span>
                      <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>

                    <p className="text-xs text-slate-600 font-medium leading-relaxed max-w-2xl">
                      {alert.description}
                    </p>

                    {roomData && (
                      <div className="flex items-center gap-2 mt-2 text-xs font-semibold text-slate-500">
                        <Building2 className="h-3.5 w-3.5 text-slate-400" />
                        <span>{roomData.room.room_code} ({roomData.room.display_name})</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100">
                  {roomData && onOpenRoom && (
                    <button
                      onClick={() => onOpenRoom(roomData.room.id)}
                      className="px-3 py-1.5 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 text-xs font-semibold transition"
                    >
                      Room Details
                    </button>
                  )}

                  {alert.status === 'ACTIVE' && (
                    <button
                      onClick={() => onAcknowledgeAlert(alert.id)}
                      className="px-4 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold transition shadow-sm flex items-center gap-1.5"
                    >
                      <Check className="h-3.5 w-3.5" />
                      <span>Acknowledge</span>
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
