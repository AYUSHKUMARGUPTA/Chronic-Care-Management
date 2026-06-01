import { useEffect, useMemo, useState } from "react";
import {
  fetchClinicianCards,
  fetchPatientBpTrend,
  fetchPatientSummary,
  resetDemoPatients,
  seedDemoPatient,
} from "./api";
import NotificationPane from "./components/NotificationPane";
import ValidationPanel from "./components/ValidationPanel";

function StatCard({ label, value, onClick, active }) {
  return (
    <div
      className={`stat-card${onClick ? " stat-card-clickable" : ""}${active ? " stat-card-active" : ""}`}
      onClick={onClick}
    >
      <p className="stat-label">{label}</p>
      <h3>{value}</h3>
    </div>
  );
}

function RiskBadge({ risk }) {
  return <span className={`badge risk-${risk.toLowerCase()}`}>{risk}</span>;
}

function MiniTrendChart({ points = [] }) {
  if (!points.length) {
    return <p className="muted">No BP trend data available.</p>;
  }

  const width = 320;
  const height = 120;
  const pad = 12;
  const allValues = points.flatMap((p) => [p.systolic, p.diastolic]);
  const minValue = Math.min(...allValues, 70);
  const maxValue = Math.max(...allValues, 180);
  const range = Math.max(maxValue - minValue, 1);
  const stepX = points.length > 1 ? (width - pad * 2) / (points.length - 1) : 0;
  const SYS_THRESHOLD = 140;
  const DIA_THRESHOLD = 90;

  function pointToXY(index, value) {
    const x = pad + index * stepX;
    const y = height - pad - ((value - minValue) / range) * (height - pad * 2);
    return [x, y];
  }

  function valueToY(value) {
    return height - pad - ((value - minValue) / range) * (height - pad * 2);
  }

  function makePath(selector) {
    return points
      .map((p, idx) => {
        const [x, y] = pointToXY(idx, selector(p));
        return `${idx === 0 ? "M" : "L"} ${x} ${y}`;
      })
      .join(" ");
  }

  return (
    <div className="mini-chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} className="mini-chart">
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} className="axis-line" />
        <line
          x1={pad}
          y1={valueToY(SYS_THRESHOLD)}
          x2={width - pad}
          y2={valueToY(SYS_THRESHOLD)}
          className="threshold-systolic"
        />
        <line
          x1={pad}
          y1={valueToY(DIA_THRESHOLD)}
          x2={width - pad}
          y2={valueToY(DIA_THRESHOLD)}
          className="threshold-diastolic"
        />
        <path d={makePath((p) => p.systolic)} className="line-systolic" />
        <path d={makePath((p) => p.diastolic)} className="line-diastolic" />
        {points.map((p, idx) => {
          const [sx, sy] = pointToXY(idx, p.systolic);
          return (
            <circle
              key={`s-${idx}`}
              cx={sx}
              cy={sy}
              r="2.6"
              className={p.systolic >= SYS_THRESHOLD ? "point-high-systolic" : "point-systolic"}
            />
          );
        })}
        {points.map((p, idx) => {
          const [dx, dy] = pointToXY(idx, p.diastolic);
          return (
            <circle
              key={`d-${idx}`}
              cx={dx}
              cy={dy}
              r="2.6"
              className={p.diastolic >= DIA_THRESHOLD ? "point-high-diastolic" : "point-diastolic"}
            />
          );
        })}
      </svg>
      <div className="chart-legend">
        <span className="legend-item">
          <span className="legend-dot systolic" /> Systolic
        </span>
        <span className="legend-item">
          <span className="legend-dot diastolic" /> Diastolic
        </span>
        <span className="legend-item">
          <span className="legend-dot threshold" /> Threshold
        </span>
      </div>
      <p className="chart-footnote">
        {points[0].observed_on} to {points[points.length - 1].observed_on}
      </p>
    </div>
  );
}

function getTrendStatus(points = []) {
  if (points.length < 3) {
    return "Insufficient Data";
  }

  const recent = points.slice(-3);
  const first = recent[0];
  const last = recent[recent.length - 1];
  const firstScore = first.systolic + first.diastolic;
  const lastScore = last.systolic + last.diastolic;
  const delta = lastScore - firstScore;

  if (delta <= -8) {
    return "Improving";
  }
  if (delta >= 8) {
    return "Worsening";
  }
  return "Stable";
}

export default function App() {
  const [cards, setCards] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const [selectedSummary, setSelectedSummary] = useState(null);
  const [selectedTrend, setSelectedTrend] = useState([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [seeding, setSeeding] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [seedMessage, setSeedMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");

  async function loadDashboardData() {
    try {
      setLoading(true);
      setError("");
      const data = await fetchClinicianCards();
      setCards(data);
    } catch (err) {
      setError(err.message || "Unable to load data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, []);

  useEffect(() => {
    if (!selectedPatientId) {
      setSelectedSummary(null);
      setSelectedTrend([]);
      return;
    }

    async function loadSummary() {
      try {
        setDetailLoading(true);
        setDetailError("");
        const [summaryData, trendData] = await Promise.all([
          fetchPatientSummary(selectedPatientId),
          fetchPatientBpTrend(selectedPatientId),
        ]);
        setSelectedSummary(summaryData);
        setSelectedTrend(trendData);
      } catch (err) {
        setDetailError(err.message || "Unable to load patient summary");
      } finally {
        setDetailLoading(false);
      }
    }

    loadSummary();
  }, [selectedPatientId]);

  const metrics = useMemo(() => {
    const high = cards.filter((c) => c.risk_level === "HIGH").length;
    const medium = cards.filter((c) => c.risk_level === "MEDIUM").length;
    const low = cards.filter((c) => c.risk_level === "LOW").length;
    return { high, medium, low, total: cards.length };
  }, [cards]);

  const filteredCards = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return cards.filter((c) => {
      const matchesName = !q || c.full_name.toLowerCase().includes(q);
      const matchesRisk = riskFilter === "ALL" || c.risk_level === riskFilter;
      return matchesName && matchesRisk;
    });
  }, [cards, searchQuery, riskFilter]);

  async function handleSeedDemoPatient() {
    try {
      setSeeding(true);
      setSeedMessage("");
      const result = await seedDemoPatient();
      await loadDashboardData();
      setSeedMessage(`Seeded ${result.patient.full_name}`);
    } catch (err) {
      setSeedMessage(err.message || "Unable to seed demo patient");
    } finally {
      setSeeding(false);
    }
  }

  async function handleResetDemoPatients() {
    try {
      setResetting(true);
      setSeedMessage("");
      const result = await resetDemoPatients();
      setSelectedPatientId(null);
      setSelectedSummary(null);
      setSelectedTrend([]);
      await loadDashboardData();
      setSeedMessage(`Reset complete: removed ${result.deleted_patients} demo patient(s)`);
    } catch (err) {
      setSeedMessage(err.message || "Unable to reset demo patients");
    } finally {
      setResetting(false);
    }
  }

  return (
    <main className="page">
      <header>
        <h1>Hypertension Clinician Dashboard</h1>
        <p>Care-gap monitoring vertical slice</p>
        <NotificationPane />
        <div className="header-actions">
          <button className="seed-button" onClick={handleSeedDemoPatient} disabled={seeding}>
            {seeding ? "Seeding..." : "Load Demo Patient"}
          </button>
          <button
            className="reset-button"
            onClick={handleResetDemoPatients}
            disabled={resetting || seeding}
          >
            {resetting ? "Resetting..." : "Reset Demo Data"}
          </button>
          {seedMessage && <span className="seed-message">{seedMessage}</span>}
        </div>
      </header>

      <section className="stats-grid">
        <StatCard
          label="Total Patients"
          value={metrics.total}
          onClick={() => setRiskFilter("ALL")}
          active={riskFilter === "ALL"}
        />
        <StatCard
          label="High Risk"
          value={metrics.high}
          onClick={() => setRiskFilter(riskFilter === "HIGH" ? "ALL" : "HIGH")}
          active={riskFilter === "HIGH"}
        />
        <StatCard
          label="Medium Risk"
          value={metrics.medium}
          onClick={() => setRiskFilter(riskFilter === "MEDIUM" ? "ALL" : "MEDIUM")}
          active={riskFilter === "MEDIUM"}
        />
        <StatCard
          label="Low Risk"
          value={metrics.low}
          onClick={() => setRiskFilter(riskFilter === "LOW" ? "ALL" : "LOW")}
          active={riskFilter === "LOW"}
        />
      </section>

      {loading && <p className="status">Loading dashboard...</p>}
      {error && (
        <div className="error-banner">
          <p className="error">{error}</p>
          <button className="retry-button" onClick={loadDashboardData}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && (
        <section className="split-layout">
          <div className="table-wrap">
            {cards.length > 0 && (
              <div className="search-bar-wrap">
                <input
                  className="search-bar"
                  type="search"
                  placeholder="Search patients by name…"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
                <div className="risk-filter-pills">
                  {["ALL", "HIGH", "MEDIUM", "LOW"].map((level) => (
                    <button
                      key={level}
                      className={`risk-pill risk-pill-${level.toLowerCase()}${riskFilter === level ? " active" : ""}`}
                      onClick={() => setRiskFilter(level)}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {cards.length === 0 ? (
              <div className="empty-state">
                <h3>No patient records yet</h3>
                <p>Use <strong>Load Demo Patient</strong> to populate the dashboard for evaluation.</p>
              </div>
            ) : filteredCards.length === 0 ? (
              <div className="empty-state">
                <h3>No patients match your filters</h3>
                <p>
                  {searchQuery && `Name: "${searchQuery}"`}
                  {searchQuery && riskFilter !== "ALL" && " · "}
                  {riskFilter !== "ALL" && `Risk: ${riskFilter}`}
                </p>
              </div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>Patient</th>
                    <th>Risk</th>
                    <th>Latest BP</th>
                    <th>Active Alerts</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredCards.map((card) => (
                    <tr
                      key={card.patient_id}
                      className={selectedPatientId === card.patient_id ? "selected-row" : ""}
                      onClick={() => setSelectedPatientId(card.patient_id)}
                    >
                      <td>{card.full_name}</td>
                      <td>
                        <RiskBadge risk={card.risk_level} />
                      </td>
                      <td>{card.last_bp}</td>
                      <td>
                        {card.alerts.length === 0 ? (
                          <span className="muted">No active alerts</span>
                        ) : (
                          <ul>
                            {card.alerts.map((alert, idx) => (
                              <li key={`${card.patient_id}-${idx}`}>{alert}</li>
                            ))}
                          </ul>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <aside className="detail-panel">
            <h2>Patient Detail</h2>
            {!selectedPatientId && <p className="muted">Select a patient to view details.</p>}
            {detailLoading && <p className="status">Loading patient summary...</p>}
            {detailError && <p className="error">{detailError}</p>}
            {selectedSummary && !detailLoading && !detailError && (
              <div className="detail-content">
                <p>
                  <strong>Risk:</strong> <RiskBadge risk={selectedSummary.risk_level} />
                </p>
                <p>
                  <strong>Reasoning Summary:</strong> {selectedSummary.summary}
                </p>
                <p>
                  <strong>Last BP:</strong> {selectedSummary.context?.context?.last_bp || "unknown"}
                </p>
                <p>
                  <strong>Last Visit:</strong>{" "}
                  {selectedSummary.context?.context?.last_visit || "unknown"}
                </p>
                <p>
                  <strong>Conditions:</strong>{" "}
                  {(selectedSummary.context?.context?.conditions || []).join(", ") || "none"}
                </p>
                <div>
                  <strong>BP Trend:</strong>
                  <MiniTrendChart points={selectedTrend} />
                  <p className="trend-status">
                    <strong>Trend Status:</strong>{" "}
                    <span className={`trend-pill ${getTrendStatus(selectedTrend).toLowerCase().replace(" ", "-")}`}>
                      {getTrendStatus(selectedTrend)}
                    </span>
                  </p>
                </div>
                <div>
                  <strong>Alerts:</strong>
                  {selectedSummary.alerts.length === 0 ? (
                    <p className="muted">No active alerts</p>
                  ) : (
                    <ul>
                      {selectedSummary.alerts.map((alert, idx) => (
                        <li key={`summary-alert-${idx}`}>{alert}</li>
                      ))}
                    </ul>
                  )}
                  <ValidationPanel patientId={selectedPatientId} />
                </div>
              </div>
            )}
          </aside>
        </section>
      )}
    </main>
  );
}
