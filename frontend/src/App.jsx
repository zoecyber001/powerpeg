import React, { useState, useEffect, useCallback, useRef } from 'react';
import Sidebar from './components/Sidebar';
import PitchRibbon from './components/PitchRibbon';
import ToastNotification from './components/ToastNotification';
import ExecutiveBento from './components/ExecutiveBento';
import RoomCard from './components/RoomCard';
import RoomRackTable from './components/RoomRackTable';
import RoomModal from './components/RoomModal';
import CheckInModal from './components/CheckInModal';
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
import { AlertOctagon, LayoutGrid, Table } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('rooms');
  const [viewMode, setViewMode] = useState('grid');
  const [overview, setOverview] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [telemetryRoom, setTelemetryRoom] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [roomFilter, setRoomFilter] = useState('all');
  const [selectedRoomId, setSelectedRoomId] = useState(null);
  const [checkInRoomTarget, setCheckInRoomTarget] = useState(null);
  const [injectionMode, setInjectionModeState] = useState('NORMAL');
  const [currentScenario, setCurrentScenario] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [toast, setToast] = useState(null);

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

      // Follow the circuit that is actually live, so the trace and its label
      // agree. Fall back to the AZ3166 room when nothing is authorised.
      const traced = roomsData.find(r => r.authorisation?.authorised)
        || roomsData.find(r => r.device?.device_type === 'AZ3166');
      if (traced) {
        setTelemetryRoom({ id: traced.room.id, code: traced.room.room_code });
        const telem = await fetchRoomTelemetry(traced.room.id, 30);
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
    const interval = setInterval(loadState, 3000);

    return () => {
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [loadState]);

  const handleWebSocketMessage = (msg) => {
    const { type, payload } = msg;

    if (type === 'TELEMETRY_UPDATED') {
      if (payload.room_id === telemetryRoom?.id) {
        setTelemetryHistory((prev) => [...prev, payload].slice(-30));
      }
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

  const handleCheckInSubmit = async ({ roomId, guestLabel, nights, settlePaymentNow }) => {
    setIsLoading(true);
    try {
      const now = new Date();
      const end = new Date(now.getTime() + nights * 24 * 60 * 60 * 1000);
      const bRes = await createBooking({
        room_id: roomId,
        guest_label: guestLabel,
        start_at: now.toISOString(),
        end_at: end.toISOString(),
        booking_status: 'confirmed',
      });

      if (settlePaymentNow && bRes?.id) {
        await updatePayment(bRes.id, 'confirmed');
        setToast({
          type: 'success',
          title: 'Checked in, circuit closed',
          message: `${guestLabel} is in. The payment hook confirmed and dispatched POWER_ON.`,
          workpegHook: 'pegpower.on_payment_post_save',
        });
      } else {
        setToast({
          type: 'warning',
          title: 'Checked in, payment pending',
          message: `${guestLabel} is registered. Power stays locked until the folio settles.`,
          workpegHook: 'pegpower.bookings.create',
        });
      }

      setCheckInRoomTarget(null);
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleConfirmPayment = async (bookingId) => {
    setIsLoading(true);
    try {
      await updatePayment(bookingId, 'confirmed');
      setToast({
        type: 'success',
        title: 'Folio settled, circuit closed',
        message: 'The payment hook evaluated the authorisation and switched the relay on.',
        workpegHook: 'pegpower.on_payment_post_save',
      });
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleCheckOut = async (bookingId) => {
    setIsLoading(true);
    try {
      await cancelBooking(bookingId);
      setToast({
        type: 'info',
        title: 'Checked out, circuit open',
        message: 'Guest departed and the circuit opened, so standby draw stops.',
        workpegHook: 'pegpower.authorisation.revoke',
      });
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleHousekeeping = async (roomId) => {
    setIsLoading(true);
    try {
      await fetch('/api/authorisations/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id: roomId,
          authorised: true,
          reason: 'Housekeeping cleaning (30m turnover)',
          duration_minutes: 30,
        }),
      });
      setToast({
        type: 'info',
        title: 'Housekeeping access granted',
        message: 'Cleaning circuit open for 30 minutes, then it expires on its own.',
        workpegHook: 'pegpower.override.housekeeping',
      });
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleAcknowledgeAlert = async (alertId) => {
    await acknowledgeAlert(alertId, 'Sarah Jenkins (Front Desk)');
    setToast({
      type: 'success',
      title: 'Incident acknowledged',
      message: 'Cleared from the active incident log.',
    });
    await loadState();
  };

  const handleManualOverride = async (roomId, targetAuth, reason, duration) => {
    setIsLoading(true);
    try {
      await fetch('/api/authorisations/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          room_id: roomId,
          authorised: targetAuth,
          reason: reason || 'Manual front desk override',
          duration_minutes: duration || 30,
        }),
      });
      setToast({
        type: targetAuth ? 'success' : 'warning',
        title: targetAuth ? 'Staff power override on' : 'Emergency cutoff enforced',
        message: `Circuit set to ${targetAuth ? 'closed (live)' : 'open (cut off)'}.`,
        workpegHook: 'pegpower.audit.override',
      });
      await loadState();
    } finally {
      setIsLoading(false);
    }
  };

  const handleSetInjection = async (roomId, mode) => {
    setInjectionModeState(mode);
    await setInjectionMode(roomId, mode);
    if (mode === 'FORCE_ROGUE_DRAW') {
      setToast({
        type: 'error',
        title: 'Rogue draw injected',
        message: '1.45 kW into Room 204. The anomaly detector is reconciling.',
      });
    } else {
      setToast({
        type: 'success',
        title: 'Baseline restored',
        message: 'The simulator is back on the standard guest load profile.',
      });
    }
  };

  const handleResetDemo = async () => {
    setIsResetting(true);
    try {
      await resetDemo();
      setInjectionModeState('NORMAL');
      setCurrentScenario(null);
      setToast({
        type: 'info',
        title: 'Demo data reset',
        message: 'Clean seed state restored.',
      });
      await loadState();
    } finally {
      setIsResetting(false);
    }
  };

  const handleRunPitchScenario = async (scenarioId) => {
    setCurrentScenario(scenarioId);
    const room204 = rooms.find(r => r.room.room_code === 'ROOM-204');
    if (!room204) return;

    if (scenarioId === 'CHECK_IN_FLOW') {
      if (!room204.active_booking) {
        await handleCheckInSubmit({
          roomId: room204.room.id,
          guestLabel: 'Elena Rostova (Judge Demo)',
          nights: 2,
          settlePaymentNow: true,
        });
      } else if (room204.active_booking.payment?.payment_status === 'pending') {
        await handleConfirmPayment(room204.active_booking.id);
      }
    } else if (scenarioId === 'CHECK_OUT_FLOW') {
      if (room204.active_booking) {
        await handleCheckOut(room204.active_booking.id);
      } else {
        const room101 = rooms.find(r => r.room.room_code === 'ROOM-101');
        if (room101?.active_booking) {
          await handleCheckOut(room101.active_booking.id);
        }
      }
    } else if (scenarioId === 'ROGUE_DRAW_ALERT') {
      await handleSetInjection(room204.room.id, 'FORCE_ROGUE_DRAW');
    } else if (scenarioId === 'HOUSEKEEPING_OVERRIDE') {
      await handleHousekeeping(room204.room.id);
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

  const liveCircuits = rooms.filter(r => r.authorisation?.authorised).length;
  const occupiedRooms = rooms.filter(r => !!r.active_booking).length;

  const filterOptions = [
    { id: 'all', label: 'All rooms', count: rooms.length },
    { id: 'active', label: 'Live', count: liveCircuits },
    { id: 'vacant', label: 'Vacant', count: rooms.filter(r => !r.active_booking).length },
  ];

  return (
    <div className="flex min-h-screen bg-paper text-ink">
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        activeAlertCount={activeAlerts.length}
        onResetDemo={handleResetDemo}
        isResetting={isResetting}
      />

      <div className="flex h-screen min-w-0 flex-1 flex-col overflow-y-auto">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-4 border-b border-line bg-paper px-6 py-3 lg:px-8">
          <div className="min-w-0">
            <h1 className="truncate text-[13px] font-medium text-ink">
              The Grand Palm Resort &amp; Spa
            </h1>
            <p className="num truncate font-mono text-[10px] text-ink-3">
              Front desk · {occupiedRooms} occupied · {liveCircuits} of {rooms.length} circuits live
            </p>
          </div>

          <div className="flex items-center gap-4">
            <span className="hidden items-center gap-2 sm:flex">
              <span className={`h-1.5 w-1.5 rounded-full ${liveCircuits > 0 ? 'bg-brass' : 'bg-ink-4'}`} />
              <span className="num font-mono text-[10px] text-ink-2">
                {telemetryHistory.length > 0 ? 'telemetry 2s' : 'telemetry idle'}
              </span>
            </span>
          </div>
        </header>

        <PitchRibbon
          onRunScenario={handleRunPitchScenario}
          isResetting={isResetting}
          currentScenario={currentScenario}
        />

        <main className="mx-auto w-full max-w-[1400px] flex-1 space-y-5 px-6 py-6 lg:px-8">
          {activeAlerts.length > 0 && activeTab !== 'alerts' && (
            <div className="flex flex-col gap-3 rounded-card border border-brick/25 bg-brick-soft px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3">
                <AlertOctagon className="mt-0.5 h-4 w-4 shrink-0 text-brick-ink" />
                <div>
                  <p className="text-[13px] font-medium text-brick-ink">
                    Electricity in use with no paid booking
                  </p>
                  <p className="mt-0.5 text-xs leading-relaxed text-brick-ink/85">
                    {activeAlerts[0].description}
                  </p>
                </div>
              </div>

              <div className="flex shrink-0 items-center gap-3 pl-7 sm:pl-0">
                <button
                  onClick={() => setActiveTab('alerts')}
                  className="text-xs text-brick-ink/85 underline decoration-brick/30 underline-offset-2 transition-colors duration-150 hover:text-brick-ink"
                >
                  Review incident
                </button>
                <button
                  onClick={() => handleAcknowledgeAlert(activeAlerts[0].id)}
                  className="rounded-control bg-ink px-3 py-1.5 text-xs font-medium text-paper transition-colors duration-150 hover:bg-ink-2"
                >
                  Acknowledge
                </button>
              </div>
            </div>
          )}

          {activeTab === 'rooms' && (
            <div className="animate-rise space-y-6">
              <ExecutiveBento overview={overview} rooms={rooms} />

              <div className="flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-base font-medium text-ink">Rooms &amp; circuits</h2>
                  <p className="mt-0.5 text-xs text-ink-3">
                    Check-in releases power, checkout cuts it
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex items-center gap-0.5 rounded-control border border-line bg-surface p-0.5">
                    <button
                      onClick={() => setViewMode('grid')}
                      aria-pressed={viewMode === 'grid'}
                      title="Cards"
                      className={`flex h-7 w-7 items-center justify-center rounded-[6px] transition-colors duration-150 ${
                        viewMode === 'grid' ? 'bg-paper text-ink' : 'text-ink-4 hover:text-ink'
                      }`}
                    >
                      <LayoutGrid className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setViewMode('table')}
                      aria-pressed={viewMode === 'table'}
                      title="Rack sheet"
                      className={`flex h-7 w-7 items-center justify-center rounded-[6px] transition-colors duration-150 ${
                        viewMode === 'table' ? 'bg-paper text-ink' : 'text-ink-4 hover:text-ink'
                      }`}
                    >
                      <Table className="h-4 w-4" />
                    </button>
                  </div>

                  <div className="flex items-center gap-0.5 rounded-control border border-line bg-surface p-0.5">
                    {filterOptions.map(option => (
                      <button
                        key={option.id}
                        onClick={() => setRoomFilter(option.id)}
                        aria-pressed={roomFilter === option.id}
                        className={`flex h-7 items-center gap-1.5 rounded-[6px] px-2.5 text-xs transition-colors duration-150 ${
                          roomFilter === option.id ? 'bg-paper text-ink' : 'text-ink-3 hover:text-ink'
                        }`}
                      >
                        <span>{option.label}</span>
                        <span className="num font-mono text-[10px] text-ink-4">{option.count}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {viewMode === 'grid' ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {filteredRooms.map(r => (
                    <RoomCard
                      key={r.room.id}
                      roomDetail={r}
                      onCheckIn={(detail) => setCheckInRoomTarget(detail.room)}
                      onConfirmPayment={handleConfirmPayment}
                      onCheckOut={handleCheckOut}
                      onHousekeeping={handleHousekeeping}
                      onAcknowledgeAlert={handleAcknowledgeAlert}
                      onOpenDetails={(id) => setSelectedRoomId(id)}
                      isLoading={isLoading}
                    />
                  ))}
                </div>
              ) : (
                <RoomRackTable
                  rooms={filteredRooms}
                  onCheckIn={(detail) => setCheckInRoomTarget(detail.room)}
                  onConfirmPayment={handleConfirmPayment}
                  onCheckOut={handleCheckOut}
                  onHousekeeping={handleHousekeeping}
                  onOpenDetails={(id) => setSelectedRoomId(id)}
                  isLoading={isLoading}
                />
              )}
            </div>
          )}

          {activeTab === 'energy' && (
            <div className="animate-rise">
              <EnergyView
                rooms={rooms}
                telemetryHistory={telemetryHistory}
                roomCode={telemetryRoom?.code || 'ROOM-204'}
              />
            </div>
          )}

          {activeTab === 'alerts' && (
            <div className="animate-rise">
              <AlertsView
                alerts={alerts}
                onAcknowledgeAlert={handleAcknowledgeAlert}
                onOpenRoom={(id) => {
                  setSelectedRoomId(id);
                  setActiveTab('rooms');
                }}
                rooms={rooms}
              />
            </div>
          )}

          {activeTab === 'audit' && (
            <div className="animate-rise">
              <AuditView events={auditEvents} />
            </div>
          )}

          {activeTab === 'tools' && (
            <div className="animate-rise">
              <DiagnosticsView
                room204Detail={room204Detail}
                injectionMode={injectionMode}
                onSetInjection={handleSetInjection}
                onResetDemo={handleResetDemo}
                isResetting={isResetting}
              />
            </div>
          )}
        </main>

        <CheckInModal
          isOpen={!!checkInRoomTarget}
          room={checkInRoomTarget}
          onClose={() => setCheckInRoomTarget(null)}
          onSubmit={handleCheckInSubmit}
          isLoading={isLoading}
        />

        <RoomModal
          roomDetail={selectedRoomDetail}
          telemetryHistory={selectedRoomDetail?.room?.id === telemetryRoom?.id ? telemetryHistory : []}
          onClose={() => setSelectedRoomId(null)}
          onManualOverride={handleManualOverride}
          isOverriding={isLoading}
        />

        <ToastNotification
          toast={toast}
          onClose={() => setToast(null)}
        />
      </div>
    </div>
  );
}
