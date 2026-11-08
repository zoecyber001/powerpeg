import React, { useState, useEffect, useCallback, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ExecutiveBento from './components/ExecutiveBento';
import RoomCard from './components/RoomCard';
import RoomModal from './components/RoomModal';
import EnergyView from './components/EnergyView';
import AlertsView from './components/AlertsView';
import AuditView from './components/AuditView';
import DiagnosticsView from './components/DiagnosticsView';
import {
  fetchOverview,
  fetchRooms,
  fetchRoomTelemetry,
  fetchAlerts,
  fetchAuditEvents,
  createBooking,
  updatePayment,
  cancelBooking,
  setInjectionMode,
  acknowledgeAlert,
  resetDemo,
} from './api';
import { AlertOctagon, Check, ArrowRight, ShieldCheck } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('rooms');
  const [overview, setOverview] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [roomFilter, setRoomFilter] = useState('all');
  const [selectedRoomId, setSelectedRoomId] = useState(null);
  const [injectionMode, setInjectionModeState] = useState('NORMAL');
  const [isLoading, setIsLoading] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  const wsRef = useRef(null);

  const loadState = useCallback(async () => {
    try {
      const [ovData, roomsData, alertsData, auditData] = await Promise.all([
        fetchOverview(),
        fetchRooms(),
        fetchAlerts(),
        fetchAuditEvents(40),
      ]);

      setOverview(ovData);
      setRooms(roomsData);
      setAlerts(alertsData);
      setAuditEvents(auditData);

      const r204 = roomsData.find(r => r.room.room_code === 'ROOM-204');
      if (r204) {
        const telem = await fetchRoomTelemetry(r204.room.id, 30);
        setTelemetryHistory(telem);
      }
    } catch (err) {
      console.error('Error fetching state:', err);
    }
  }, []);

  useEffect(() => {
    loadState();

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    function connectWs() {
      const socket = new WebSocket(wsUrl);
      wsRef.current = socket;

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleWebSocketMessage(msg);
        } catch (e) {}
      };

      socket.onclose = () => {
        setTimeout(connectWs, 3000);
      };

      socket.onerror = () => socket.close();
    }

    connectWs();
    const interval = setInterval(loadState, 3500);

    return () => {
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [loadState]);

  const handleWebSocketMessage = (msg) => {
    const { type, payload } = msg;

    if (type === 'TELEMETRY_UPDATED' && payload.room_code === 'ROOM-204') {
      setTelemetryHistory((prev) => [...prev, payload].slice(-30));
      setRooms((prev) => prev.map(r => {
        if (r.room.id === payload.room_id) {
          return { ...r, latest_telemetry: payload };
        }
        return r;
      }));
    } else if (
      type === 'DEVICE_HEARTBEAT' ||
      type === 'DEVICE_STATUS' ||
      type === 'ALERT_RAISED' ||
      type === 'ALERT_ACKNOWLEDGED' ||
      type === 'AUTHORISATION_UPDATED' ||
      type === 'DEMO_RESET'
    ) {
      loadState();
    } else if (type === 'AUDIT_EVENT') {
      setAuditEvents((prev) => [payload, ...prev.slice(0, 39)]);
    }
  };

  const handleCheckIn = async (roomId) => {
    setIsLoading(true);
    try {
      const now = new Date();
      const end = new Date(now.getTime() + 24 * 60 * 60 * 1000);
      await createBooking({
        room_id: roomId,
        guest_label: 'Alice Johnson',
        start_at: now.toISOString(),
        end_at: end.toISOString(),
        booking_status: 'confirmed',
      });
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmPayment = async (bookingId) => {
    setIsLoading(true);
    try {
      await updatePayment(bookingId, 'confirmed');
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleCheckOut = async (bookingId) => {
    setIsLoading(true);
    try {
      await cancelBooking(bookingId);
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    await acknowledgeAlert(alertId, 'Sarah Jenkins');
    await loadState();
  };

  const handleManualOverride = async (roomId, targetAuth, reason) => {
    setIsLoading(true);
    try {
      await fetch('/api/authorisations/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id: roomId,
          authorised: targetAuth,
          reason: reason || 'Front desk manager override',
          duration_minutes: 60,
        }),
      });
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetInjection = async (roomId, mode) => {
    setInjectionModeState(mode);
    await setInjectionMode(roomId, mode);
  };

  const handleResetDemo = async () => {
    setIsResetting(true);
    try {
      await resetDemo();
      setInjectionModeState('NORMAL');
      await loadState();
    } finally {
      setIsResetting(false);
    }
  };

  const activeAlerts = alerts.filter(a => a.status === 'ACTIVE');
  const room204Detail = rooms.find(r => r.room.room_code === 'ROOM-204');
  const selectedRoomDetail = rooms.find(r => r.room.id === selectedRoomId);

  const filteredRooms = rooms.filter(r => {
    if (roomFilter === 'active') return r.authorisation?.authorised;
    if (roomFilter === 'vacant') return !r.active_booking;
    return true;
  });

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 flex font-sans antialiased">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeAlertCount={activeAlerts.length}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
      />

      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto h-screen">
        <header className="bg-white border-b border-slate-200/90 px-8 py-4 sticky top-0 z-30 flex items-center justify-between">
          <div>
            <h1 className="text-base font-extrabold text-slate-900 tracking-tight">
              The Grand Palm Resort & Spa
            </h1>
            <p className="text-[11px] font-medium text-slate-400">
              Front Desk Hospitality Portal • Ocean Wing Circuit Controls
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200 text-xs font-semibold">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>Workpeg Live Sync</span>
            </div>
          </div>
        </header>

        <main className="flex-1 p-8 space-y-6 max-w-7xl w-full mx-auto">
          {activeAlerts.length > 0 && activeTab !== 'alerts' && (
            <div className="p-4 rounded-2xl bg-rose-50 border border-rose-300 text-rose-900 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm animate-pulse-gentle">
              <div className="flex items-start gap-3">
                <div className="h-9 w-9 rounded-xl bg-rose-100 text-rose-600 flex items-center justify-center shrink-0 mt-0.5">
                  <AlertOctagon className="h-5 w-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-extrabold text-sm text-rose-900">
                      Circuit Anomaly Detected
                    </span>
                    <span className="text-[10px] font-extrabold uppercase bg-rose-600 text-white px-1.5 py-0.5 rounded">
                      CRITICAL
                    </span>
                  </div>
                  <p className="text-xs text-rose-800 font-medium mt-0.5">
                    {activeAlerts[0].description}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => setActiveTab('alerts')}
                  className="px-3.5 py-1.5 rounded-xl border border-rose-300 text-rose-800 hover:bg-rose-100 text-xs font-semibold transition"
                >
                  View Details
                </button>
                <button
                  onClick={() => handleAcknowledgeAlert(activeAlerts[0].id)}
                  className="px-4 py-1.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-semibold transition shadow-sm flex items-center gap-1.5"
                >
                  <Check className="h-3.5 w-3.5" />
                  <span>Acknowledge</span>
                </button>
              </div>
            </div>
          )}

          {activeTab === 'rooms' && (
            <div className="space-y-6">
              <ExecutiveBento overview={overview} rooms={rooms} />

              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pt-2">
                <div>
                  <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
                    Guest Rooms & Power Access
                  </h2>
                  <p className="text-xs font-medium text-slate-500 mt-0.5">
                    1-click guest check-in, automated payment power release, and instant checkout cutoff
                  </p>
                </div>

                <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl">
                  <button
                    onClick={() => setRoomFilter('all')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                      roomFilter === 'all'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    All Rooms ({rooms.length})
                  </button>
                  <button
                    onClick={() => setRoomFilter('active')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                      roomFilter === 'active'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    Powered ({rooms.filter(r => r.authorisation?.authorised).length})
                  </button>
                  <button
                    onClick={() => setRoomFilter('vacant')}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition ${
                      roomFilter === 'vacant'
                        ? 'bg-white text-slate-900 shadow-sm'
                        : 'text-slate-500 hover:text-slate-900'
                    }`}
                  >
                    Vacant ({rooms.filter(r => !r.active_booking).length})
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredRooms.map(r => (
                  <RoomCard
                    key={r.room.id}
                    roomDetail={r}
                    onCheckIn={handleCheckIn}
                    onConfirmPayment={handleConfirmPayment}
                    onCheckOut={handleCheckOut}
                    onAcknowledgeAlert={handleAcknowledgeAlert}
                    onOpenDetails={(id) => setSelectedRoomId(id)}
                    isLoading={isLoading}
                  />
                ))}
              </div>
            </div>
          )}

          {activeTab === 'energy' && (
            <EnergyView rooms={rooms} telemetryHistory={telemetryHistory} />
          )}

          {activeTab === 'alerts' && (
            <AlertsView
              alerts={alerts}
              onAcknowledgeAlert={handleAcknowledgeAlert}
              onOpenRoom={(id) => {
                setSelectedRoomId(id);
                setActiveTab('rooms');
              }}
              rooms={rooms}
            />
          )}

          {activeTab === 'audit' && (
            <AuditView events={auditEvents} />
          )}

          {activeTab === 'tools' && (
            <DiagnosticsView
              room204Detail={room204Detail}
              injectionMode={injectionMode}
              onSetInjection={handleSetInjection}
              onResetDemo={handleResetDemo}
              isResetting={isResetting}
            />
          )}
        </main>

        <RoomModal
          roomDetail={selectedRoomDetail}
          telemetryHistory={selectedRoomDetail?.room?.room_code === 'ROOM-204' ? telemetryHistory : []}
          onClose={() => setSelectedRoomId(null)}
          onManualOverride={handleManualOverride}
          isOverriding={isLoading}
        />
      </div>
    </div>
  );
}
