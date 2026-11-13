import React from 'react';
import { Cpu } from 'lucide-react';

export default function AZ3166DigitalTwin({
  device,
  roomCode = 'ROOM-204',
  telemetry,
  isOverridden = false
}) {
  const relayState = device?.reported_relay_state || 'OFF';
  const isOnline = device?.connection_status === 'online';
  const isEnergized = relayState === 'ON';

  const voltage = telemetry?.voltage?.toFixed(1) || (isEnergized ? '230.2' : '0.0');
  const current = telemetry?.current?.toFixed(2) || (isEnergized ? '1.85' : '0.00');
  const power = telemetry?.power?.toFixed(2) || (isEnergized ? '0.42' : '0.00');

  const led = isOverridden ? 'bg-brass' : isEnergized ? 'bg-brass' : 'bg-ink-4';
  const ledLabel = isOverridden ? 'amber, override' : isEnergized ? 'amber, armed' : 'dark, cut off';

  return (
    <div className="rounded-card border border-line bg-surface p-3.5">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="h-3.5 w-3.5 text-ink-4" />
          <span className="text-xs font-medium text-ink">AZ3166 hardware twin</span>
        </div>
        <span className="flex items-center gap-1.5 font-mono text-[10px] text-ink-3">
          <span className={`h-1.5 w-1.5 rounded-full ${isOnline ? 'bg-moss' : 'bg-ink-4'}`} />
          {isOnline ? 'link up' : 'offline'}
        </span>
      </div>

      {/* The one dark object on the page: an actual OLED panel. */}
      <div className="rounded-panel border border-[#2A2723] bg-[#0C0B0A] px-3 py-3 font-mono">
        <div className="flex items-center justify-between border-b border-[#26231F] pb-1.5 text-[9px] text-[#8C8579]">
          <span>OLED 128×64 · SSD1306</span>
          <span>{device?.device_code || 'AZ3166-01'}</span>
        </div>

        <div className="py-3 text-center text-[#D9D3C7]">
          <div className="text-[9px] tracking-[0.14em] text-[#8C8579]">PEGPOWER PMS</div>
          <div className="mt-1 text-[15px] font-medium tracking-wide">{roomCode}</div>
          <div className="mt-1.5 flex items-center justify-center gap-2 text-[11px]">
            <span className="text-[#8C8579]">CIRCUIT</span>
            <span className={isEnergized ? 'text-[#D8A657]' : 'text-[#8C8579]'}>
              [{relayState}] {isEnergized ? 'CLOSED' : 'OPEN'}
            </span>
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-[#26231F] pt-1.5 text-[10px] text-[#8C8579]">
          <span className="num">V {voltage} · I {current} · {power} kW</span>
          <span>{isOverridden ? 'HOUSEKEEPING' : isEnergized ? 'ARMED' : 'SAFE'}</span>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-line pt-2.5">
        <span className="flex items-center gap-1.5 text-[10px] text-ink-3">
          <span className={`h-1.5 w-1.5 rounded-full ${led}`} />
          LED {ledLabel}
        </span>
        <span className="font-mono text-[10px] text-ink-3">
          relay {isEnergized ? 'closed' : 'open'}
        </span>
      </div>
    </div>
  );
}
