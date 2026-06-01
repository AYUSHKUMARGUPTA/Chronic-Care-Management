import React, { useEffect, useState } from "react";
import { approveAlert, rejectAlert, fetchPatientAlerts } from "../api";

export default function ValidationPanel({ patientId, approver = "clinician@example.com" }) {
  const [alerts, setAlerts] = useState([]);
  const [processing, setProcessing] = useState({});
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!patientId) return;
    let mounted = true;
    async function load() {
      try {
        const data = await fetchPatientAlerts(patientId);
        if (mounted) setAlerts(data);
      } catch (e) {
        console.error(e);
      }
    }
    load();
    return () => (mounted = false);
  }, [patientId]);

  function timeAgo(isoDate) {
    if (!isoDate) return "unknown";
    const d = new Date(isoDate);
    const diff = Math.floor((Date.now() - d.getTime()) / 1000);
    if (diff < 60) return `${diff}s ago`;
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
  }

  async function handleApprove(id) {
    const ok = window.confirm("Approve this provisional alert? This action is final.");
    if (!ok) return;
    setProcessing((p) => ({ ...p, [id]: true }));
    try {
      await approveAlert(id, approver);
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, status: "CONFIRMED", approved_by: approver, approved_at: new Date().toISOString() } : a)));
      setNotice("Alert approved");
      setTimeout(() => setNotice(""), 2500);
    } catch (e) {
      console.error(e);
      setNotice("Failed to approve alert");
      setTimeout(() => setNotice(""), 2500);
    } finally {
      setProcessing((p) => ({ ...p, [id]: false }));
    }
  }

  async function handleReject(id) {
    const ok = window.confirm("Reject this provisional alert? This will mark it as rejected.");
    if (!ok) return;
    setProcessing((p) => ({ ...p, [id]: true }));
    try {
      await rejectAlert(id, approver);
      setAlerts((prev) => prev.map((a) => (a.id === id ? { ...a, status: "REJECTED", approved_by: approver, approved_at: new Date().toISOString() } : a)));
      setNotice("Alert rejected");
      setTimeout(() => setNotice(""), 2500);
    } catch (e) {
      console.error(e);
      setNotice("Failed to reject alert");
      setTimeout(() => setNotice(""), 2500);
    } finally {
      setProcessing((p) => ({ ...p, [id]: false }));
    }
  }

  if (!patientId) return null;

  return (
    <div className="validation-panel">
      <h4>Alert History</h4>
      {notice && <div className="notice">{notice}</div>}
      {alerts.length === 0 && <p className="muted">No alerts for this patient.</p>}
      <ul>
        {alerts.map((a) => (
          <li key={`vp-${a.id}`} className={`alert-row status-${a.status.toLowerCase()}`}>
            <div className="alert-main">
              <div className="alert-title">
                <strong>{a.alert_type}</strong>
                <span className={`badge badge-${a.status.toLowerCase()}`}>{a.status}</span>
              </div>
              <div className="alert-message">{a.message}</div>
              <div className="meta">Created: {new Date(a.created_at).toLocaleString()} • {timeAgo(a.created_at)}</div>
              {a.approved_by && (
                <div className="meta">Reviewed by: {a.approved_by} • {a.approved_at ? new Date(a.approved_at).toLocaleString() : ""}</div>
              )}
            </div>
            {a.status === "PROVISIONAL" && (
              <div className="actions">
                <button disabled={!!processing[a.id]} onClick={() => handleApprove(a.id)} className="approve">
                  {processing[a.id] ? "Approving..." : "Approve"}
                </button>
                <button disabled={!!processing[a.id]} onClick={() => handleReject(a.id)} className="reject">
                  {processing[a.id] ? "Rejecting..." : "Reject"}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
