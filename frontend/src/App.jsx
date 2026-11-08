import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import RoomHero from './components/RoomHero';
import MultiRoomGrid from './components/MultiRoomGrid';
import AlertsPanel from './components/AlertsPanel';
import AuditTimeline from './components/AuditTimeline';
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

export default function App() {
  const [overview, setOverview] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [room204Detail, setRoom204Detail] = useState(null);
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [injectionMode, setInjectionModeState] = useState('NORMAL');
  const [isWsConnected, setIsWsConnected] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  const wsRef = useRef(null);

  const loadState = useCallback(async () => {
    try {
      const [ovData, roomsData, alertsData, auditData] = await Promise.all([
        fetchOverview(),
        fetchRooms(),
        fetchAlerts(),
        fetchAuditEvents(50),
      ]);

      setOverview(ovData);
      setRooms(roomsData);
      setAlerts(alertsData);
      setAuditEvents(auditData);

      const r204 = roomsData.find((r) => r.room.room_code === 'ROOM-204');
      if (r204) {
        setRoom204Detail(r204);
        const telem = await fetchRoomTelemetry(r204.room.id, 40);
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

      socket.onopen = () => setIsWsConnected(true);

      socket.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          handleWebSocketMessage(msg);
        } catch (e) {}
      };

      socket.onclose = () => {
        setIsWsConnected(false);
        setTimeout(connectWs, 3000);
      };

      socket.onerror = () => socket.close();
    }

    connectWs();
    const interval = setInterval(loadState, 4000);

    return () => {
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [loadState]);

  const handleWebSocketMessage = (msg) => {
    const { type, payload } = msg;

    if (type === 'TELEMETRY_UPDATED') {
      if (payload.room_code === 'ROOM-204') {
        setTelemetryHistory((prev) => [...prev, payload].slice(-40));
        setRoom204Detail((prev) => {
          if (!prev) return prev;
          return { ...prev, latest_telemetry: payload };
        });
      }
    } else if (type === 'DEVICE_HEARTBEAT' || type === 'DEVICE_STATUS') {
      loadState();
    } else if (type === 'ALERT_RAISED' || type === 'ALERT_ACKNOWLEDGED') {
      fetchAlerts().then(setAlerts);
      fetchOverview().then(setOverview);
    } else if (type === 'AUDIT_EVENT') {
      setAuditEvents((prev) => [payload, ...prev.slice(0, 49)]);
    } else if (type === 'AUTHORISATION_UPDATED' || type === 'DEMO_RESET') {
      loadState();
    }
  };

  const handleCreateDemoBooking = async (roomId) => {
    setIsActionLoading(true);
    try {
      const now = new Date();
      const end = new Date(now.getTime() + 24 * 60 * 60 * 1000);
      await createBooking({
        room_id: roomId,
        guest_label: 'Hackathon VIP Guest',
        start_at: now.toISOString(),
        end_at: end.toISOString(),
        booking_status: 'confirmed',
      });
      await loadState();
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleConfirmPayment = async (bookingId) => {
    setIsActionLoading(true);
    try {
      await updatePayment(bookingId, 'confirmed');
      await loadState();
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleCancelBooking = async (bookingId) => {
    setIsActionLoading(true);
    try {
      await cancelBooking(bookingId);
      await loadState();
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleSetInjection = async (roomId, mode) => {
    setInjectionModeState(mode);
    await setInjectionMode(roomId, mode);
  };

  const handleAcknowledgeAlert = async (alertId) => {
    await acknowledgeAlert(alertId, 'Lead Operator');
    const updatedAlerts = await fetchAlerts();
    setAlerts(updatedAlerts);
    fetchOverview().then(setOverview);
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

  return (
    <div className="min-h-screen bg-[#070B14] text-slate-100 flex flex-col font-sans">
      <Header
        overview={overview}
        isWsConnected={isWsConnected}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        <RoomHero
          roomDetail={room204Detail}
          telemetryHistory={telemetryHistory}
          injectionMode={injectionMode}
          onConfirmPayment={handleConfirmPayment}
          onCreateBooking={handleCreateDemoBooking}
          onCancelBooking={handleCancelBooking}
          onSetInjection={handleSetInjection}
          isActionLoading={isActionLoading}
        />

        <MultiRoomGrid
          rooms={rooms}
          onSelectRoom={(id) => console.log('Selected room', id)}
        />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AlertsPanel
            alerts={alerts}
            onAcknowledgeAlert={handleAcknowledgeAlert}
          />
          <AuditTimeline
            events={auditEvents}
          />
        </div>
      </main>

      <footer className="border-t border-slate-800/80 bg-[#0A0E1A] py-4 text-center text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>PegPower | Workpeg Peg Prototype (1 × MXChip AZ3166 IoT DevKit + Virtual Simulation Plane)</span>
          <span className="text-amber-500/80 font-mono text-[11px]">
            Notice: All electrical measurements are software-simulated.
          </span>
        </div>
      </footer>
    </div>
  );
}
