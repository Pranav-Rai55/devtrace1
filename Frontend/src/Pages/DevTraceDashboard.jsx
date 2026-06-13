import React from "react";
import { useLocation, useNavigate } from "react-router-dom";

const Dashboard = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const report = location.state?.report;

  if (!report) {
    return (
      <div style={{ minHeight: "100vh", background: "#060910", display: "flex", alignItems: "center", justifyContent: "center", color: "#dde6f0" }}>
        <div>
          <p>No analysis report found.</p>
          <button onClick={() => navigate("/")} style={{ marginTop: "20px", padding: "10px 20px", background: "#6c63ff", color: "#fff", border: "none", borderRadius: "8px", cursor: "pointer" }}>
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", background: "#060910", color: "#dde6f0", fontFamily: "Space Grotesk, sans-serif", padding: "28px" }}>
      <div style={{ maxWidth: "1480px", margin: "0 auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "28px" }}>
          <div>
            <div style={{ fontSize: "24px", fontWeight: 800, marginBottom: "6px" }}>Analysis Report</div>
            <div style={{ fontSize: "12px", color: "#6b8099" }}>
              {report.repo_name} • {report.total_files_analyzed} files • {report.total_lines_of_code} lines
            </div>
          </div>
          <button style={{ padding: "6px 12px", background: "#6c63ff", border: "none", color: "#fff", borderRadius: "6px", cursor: "pointer", fontSize: "12px", fontWeight: 600 }} onClick={() => navigate("/")}>
            ← New Analysis
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "14px", marginBottom: "24px" }}>
          <div style={{ background: "#0c1118", border: "1px solid #18263a", borderRadius: "16px", padding: "20px" }}>
            <div style={{ fontSize: "11px", color: "#6b8099", marginBottom: "8px", fontWeight: 500 }}>Quality Score</div>
            <div style={{ fontSize: "46px", fontWeight: 800, color: "#22d3a0" }}>{report.quality_score?.value || "—"}</div>
          </div>
          <div style={{ background: "#0c1118", border: "1px solid #18263a", borderRadius: "16px", padding: "20px" }}>
            <div style={{ fontSize: "11px", color: "#6b8099", marginBottom: "8px", fontWeight: 500 }}>Security Risks</div>
            <div style={{ fontSize: "46px", fontWeight: 800, color: "#ff4d6a" }}>{report.security_risks?.value || "—"}</div>
          </div>
          <div style={{ background: "#0c1118", border: "1px solid #18263a", borderRadius: "16px", padding: "20px" }}>
            <div style={{ fontSize: "11px", color: "#6b8099", marginBottom: "8px", fontWeight: 500 }}>Maintainability</div>
            <div style={{ fontSize: "46px", fontWeight: 800, color: "#38bdf8" }}>{report.maintainability?.value || "—"}</div>
          </div>
          <div style={{ background: "#0c1118", border: "1px solid #18263a", borderRadius: "16px", padding: "20px" }}>
            <div style={{ fontSize: "11px", color: "#6b8099", marginBottom: "8px", fontWeight: 500 }}>Tech Debt (hrs)</div>
            <div style={{ fontSize: "46px", fontWeight: 800, color: "#fbbf24" }}>{report.estimated_tech_debt_hours?.value || "—"}</div>
          </div>
        </div>

        <div style={{ background: "#0c1118", border: "1px solid #18263a", borderRadius: "16px", padding: "20px", marginBottom: "24px" }}>
          <div style={{ fontSize: "11px", color: "#6b8099", marginBottom: "8px", fontWeight: 500 }}>Executive Summary</div>
          <p style={{ color: "#6b8099", lineHeight: 1.6, margin: 0 }}>{report.executive_summary || "No summary available"}</p>
        </div>

        {report.actionable_insights && report.actionable_insights.length > 0 && (
          <>
            <div style={{ fontSize: "16px", fontWeight: 700, marginBottom: "16px", marginTop: "28px" }}>Actionable Insights</div>
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {report.actionable_insights.slice(0, 10).map((insight, i) => (
                <div key={i} style={{ background: "#0c1118", border: "1px solid #18263a", borderLeft: insight.severity === "HIGH" ? "3px solid #ff4d6a" : "3px solid #fbbf24", borderRadius: "16px", padding: "20px" }}>
                  <div style={{ fontSize: "12px", fontWeight: 600, marginBottom: "4px" }}>{insight.category}: {insight.title}</div>
                  <div style={{ fontSize: "12px", color: "#6b8099" }}>{insight.description}</div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
