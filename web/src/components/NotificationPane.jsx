import React, { useEffect, useState } from "react";
import { approveAlert, rejectAlert, API_BASE } from "../api";

export default function NotificationPane() {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    const ws = new WebSocket((import.meta.env.VITE_API_BASE || API_BASE).replace(/^http/, "ws") + "/ws/alerts");
    ws.onmessage = (ev) => {
      try {
        const d = JSON.parse(ev.data);
        setAlerts((prev) => [d, ...prev]);
      } catch (e) {
        // ignore
      }
    };
    return () => ws.close();
  }, []);

  async function handleApprove(id) {
    try {
      await approveAlert(id, "clinician@example.com");
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      console.error(e);
    }
  }

  async function handleReject(id) {
    try {
      await rejectAlert(id, "clinician@example.com");
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      console.error(e);
    }
  }

  if (!alerts.length) return null;

  return (
    <div className="notification-pane">
      <h4>Provisional Alerts</h4>
      <ul>
        {alerts.map((a) => (
          <li key={`alert-${a.id}`} className="notification-item">
            <div className="notification-body">
              <strong>{a.type}</strong> for patient {a.patient_id}: {a.message}
            </div>
            <div className="notification-actions">
              <button onClick={() => handleApprove(a.id)} className="approve">Approve</button>
              <button onClick={() => handleReject(a.id)} className="reject">Reject</button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
