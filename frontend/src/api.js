const BASE_URL = '/api';

export async function fetchOverview() {
  const res = await fetch(`${BASE_URL}/overview`);
  return res.json();
}

export async function fetchRooms() {
  const res = await fetch(`${BASE_URL}/rooms`);
  return res.json();
}

export async function fetchRoom(id) {
  const res = await fetch(`${BASE_URL}/rooms/${id}`);
  return res.json();
}

export async function createBooking(data) {
  const res = await fetch(`${BASE_URL}/bookings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

export async function updatePayment(bookingId, paymentStatus) {
  const res = await fetch(`${BASE_URL}/bookings/${bookingId}/payment`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ payment_status: paymentStatus }),
  });
  return res.json();
}

export async function cancelBooking(bookingId) {
  const res = await fetch(`${BASE_URL}/bookings/${bookingId}/cancel`, {
    method: 'POST',
  });
  return res.json();
}

export async function fetchRoomTelemetry(roomId, limit = 40) {
  const res = await fetch(`${BASE_URL}/rooms/${roomId}/telemetry?limit=${limit}`);
  return res.json();
}

export async function setInjectionMode(roomId, mode) {
  const res = await fetch(`${BASE_URL}/simulator/rooms/${roomId}/injection?mode=${mode}`, {
    method: 'POST',
  });
  return res.json();
}

export async function fetchAlerts(statusFilter = '') {
  const url = statusFilter ? `${BASE_URL}/alerts?status_filter=${statusFilter}` : `${BASE_URL}/alerts`;
  const res = await fetch(url);
  return res.json();
}

export async function acknowledgeAlert(alertId, acknowledgedBy = 'Admin') {
  const res = await fetch(`${BASE_URL}/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ acknowledged_by: acknowledgedBy }),
  });
  return res.json();
}

export async function fetchAuditEvents(limit = 50) {
  const res = await fetch(`${BASE_URL}/audit-events?limit=${limit}`);
  return res.json();
}

export async function resetDemo() {
  const res = await fetch(`${BASE_URL}/demo/reset`, { method: 'POST' });
  return res.json();
}
