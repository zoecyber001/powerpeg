import React from 'react';
import { Cpu, RotateCcw } from 'lucide-react';

export default function DiagnosticsView({
  room204Detail,
  injectionMode,
  onSetInjection,
  onResetDemo,
  isResetting
}) {
  const device = room204Detail?.device;
  const roomCode = room204Detail?.room?.room_code || 'ROOM-204';
  const relayState = device?.reported_relay_state || 'OFF';
  const isOnline = device?.connection_status === 'online';
  const isRogue = injectionMode === 'FORCE_ROGUE_DRAW';

  const facts = [
    { label: 'Device', value: device?.device_code || 'AZ3166-01' },
    { label: 'Firmware', value: `v${device?.firmware_version || '1.2.0'}` },
    { label: 'Heartbeat', value: device?.last_seen_at ? new Date(device.last_seen_at).toLocaleTimeString() : 'never' },
    { label: 'Relay', value: relayState === 'ON' ? 'closed' : 'open' },
  ];

  const scenarios = [
    {
      id: 'FORCE_ROGUE_DRAW',
      active: isRogue,
      title: 'Rogue draw',
      body: 'Inject 1.45 kW into a vacant, unpaid room and let the reconciliation loop catch it.',
    },
    {
      id: 'NORMAL',
      active: !isRogue,
      title: 'Normal baseline',
      body: 'Return the simulator to the standard occupied-room load profile.',
    },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-base font-medium text-ink">Switch diagnostics</h2>
        <p className="mt-0.5 text-xs text-ink-3">
          Edge device state and scenario controls, all software
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className="rounded-card border border-line bg-surface p-4 shadow-card">
          <div className="mb-3 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Cpu className="h-3.5 w-3.5 text-ink-4" />
              <h3 className="text-xs font-medium text-ink">AZ3166 switch</h3>
            </div>
            <span className="flex items-center gap-1.5 font-mono text-[10px] text-ink-3">
              <span className={`h-1.5 w-1.5 rounded-full ${isOnline ? 'bg-moss' : 'bg-ink-4'}`} />
              {isOnline ? 'online' : 'offline'}
            </span>
          </div>

          <div className="rounded-panel border border-[#2A2723] bg-[#0C0B0A] px-3 py-4 font-mono">
            <div className="flex items-center justify-between border-b border-[#26231F] pb-1.5 text-[9px] text-[#8C8579]">
              <span>OLED 128×64 · SSD1306</span>
              <span>I²C</span>
            </div>
            <div className="py-4 text-center text-[#D9D3C7]">
              <div className="text-[9px] tracking-[0.14em] text-[#8C8579]">PEGPOWER PMS</div>
              <div className="mt-1.5 text-[17px] font-medium tracking-wide">{roomCode}</div>
              <div className="mt-2 text-[11px]">
                <span className="text-[#8C8579]">CIRCUIT </span>
                <span className={relayState === 'ON' ? 'text-[#D8A657]' : 'text-[#8C8579]'}>
                  [{relayState}]
                </span>
              </div>
            </div>
            <div className="border-t border-[#26231F] pt-1.5 text-center text-[9px] text-[#8C8579]">
              RGB {relayState === 'ON' ? 'AMBER · ARMED' : 'DARK · SAFE'}
            </div>
          </div>

          <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 border-t border-line pt-3">
            {facts.map(fact => (
              <div key={fact.label}>
                <dt className="text-[10px] text-ink-3">{fact.label}</dt>
                <dd className="num mt-0.5 truncate font-mono text-[11px] text-ink">{fact.value}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="rounded-card border border-line bg-surface p-4 shadow-card">
          <h3 className="text-xs font-medium text-ink">Scenario lab</h3>
          <p className="mt-1 text-[11px] leading-relaxed text-ink-3">
            When a room draws power without a paid folio, the reconciliation loop raises an
            incident on the next two-second pass.
          </p>

          <div className="mt-3 space-y-1.5">
            {scenarios.map(scenario => (
              <button
                key={scenario.id}
                onClick={() => onSetInjection(room204Detail?.room?.id, scenario.id)}
                aria-pressed={scenario.active}
                className={`flex w-full items-start justify-between gap-3 rounded-panel border px-3 py-2.5 text-left transition-colors duration-150 ${
                  scenario.active
                    ? 'border-line-strong bg-paper'
                    : 'border-line hover:border-line-strong'
                }`}
              >
                <span className="min-w-0">
                  <span className="block text-xs font-medium text-ink">{scenario.title}</span>
                  <span className="mt-0.5 block text-[11px] leading-snug text-ink-3">
                    {scenario.body}
                  </span>
                </span>
                <span className={`shrink-0 font-mono text-[10px] ${scenario.active ? 'text-brass-ink' : 'text-ink-4'}`}>
                  {scenario.active ? 'active' : 'run'}
                </span>
              </button>
            ))}
          </div>

          <div className="mt-3 flex items-center justify-between border-t border-line pt-3">
            <span className="text-[11px] text-ink-3">Reset the seeded demo state</span>
            <button
              onClick={onResetDemo}
              disabled={isResetting}
              className="flex h-8 items-center gap-1.5 rounded-control border border-line px-2.5 text-xs text-ink-2 transition-colors duration-150 hover:border-line-strong hover:text-ink disabled:opacity-50"
            >
              <RotateCcw className={`h-3 w-3 ${isResetting ? 'animate-spin' : ''}`} />
              <span>{isResetting ? 'Resetting' : 'Reset'}</span>
            </button>
          </div>
        </section>
      </div>

      <section className="rounded-card border border-line bg-surface p-4 shadow-card">
        <h3 className="text-xs font-medium text-ink">What is real here</h3>
        <div className="mt-3 grid grid-cols-1 gap-4 text-[11px] leading-relaxed text-ink-2 sm:grid-cols-3">
          <div className="border-t border-line pt-2.5">
            <p className="mb-1 font-medium text-ink">Workpeg hooks</p>
            <p>
              Payment and booking writes run through Workpeg, and
              <span className="font-mono text-[10px]"> on_payment_post_save </span>
              is what asks the relay to close.
            </p>
          </div>
          <div className="border-t border-line pt-2.5">
            <p className="mb-1 font-medium text-ink">No mains voltage</p>
            <p>
              The AZ3166 drives a simulated relay, the OLED and the RGB LED. Nothing here
              switches real mains power.
            </p>
          </div>
          <div className="border-t border-line pt-2.5">
            <p className="mb-1 font-medium text-ink">Two-second loop</p>
            <p>
              Voltage, current and kW come from a software simulator; reconciliation runs
              every two seconds against the folio.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
