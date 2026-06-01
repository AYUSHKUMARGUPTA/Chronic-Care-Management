export const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

export async function fetchClinicianCards() {
  const response = await fetch(`${API_BASE}/patients/dashboard/clinician`);
  if (!response.ok) {
    throw new Error(`Failed to load dashboard data: ${response.status}`);
  }
  return response.json();
}

export async function fetchPatientSummary(patientId) {
  const response = await fetch(`${API_BASE}/patients/${patientId}/summary`);
  if (!response.ok) {
    throw new Error(`Failed to load patient summary: ${response.status}`);
  }
  return response.json();
}

export async function fetchPatientBpTrend(patientId) {
  const response = await fetch(`${API_BASE}/patients/${patientId}/bp-trend`);
  if (!response.ok) {
    throw new Error(`Failed to load BP trend: ${response.status}`);
  }
  return response.json();
}

export async function seedDemoPatient() {
  const response = await fetch(`${API_BASE}/ingestion/demo-seed`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Failed to seed demo patient: ${response.status}`);
  }
  return response.json();
}

export async function resetDemoPatients() {
  const response = await fetch(`${API_BASE}/ingestion/demo-seed`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(`Failed to reset demo patients: ${response.status}`);
  }
  return response.json();
}

export async function approveAlert(alertId, approver) {
  const response = await fetch(`${API_BASE}/validation/${alertId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approver }),
  });
  if (!response.ok) throw new Error(`Approve failed: ${response.status}`);
  return response.json();
}

export async function rejectAlert(alertId, approver) {
  const response = await fetch(`${API_BASE}/validation/${alertId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approver }),
  });
  if (!response.ok) throw new Error(`Reject failed: ${response.status}`);
  return response.json();
}

export async function fetchPatientAlerts(patientId) {
  const response = await fetch(`${API_BASE}/alerts/patient/${patientId}`);
  if (!response.ok) throw new Error(`Failed to fetch patient alerts: ${response.status}`);
  return response.json();
}
