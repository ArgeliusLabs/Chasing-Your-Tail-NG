"use strict";
const byId = (id) => document.getElementById(id);
const text = (id, value) => { byId(id).textContent = value; };
const when = (seconds) => seconds == null ? "Never" : new Date(seconds * 1000).toLocaleString();
let pending = false;
async function refresh() {
  if (pending) return;
  pending = true;
  try {
    const response = await fetch(`/api/report?window=${encodeURIComponent(byId("window").value)}`, {cache: "no-store"});
    const report = await response.json();
    if (!response.ok) throw new Error(report.error || "Could not read the observation store");
    byId("error").hidden = true;
    const status = report.storage;
    text("freshness", {empty: "No data", stale: "Stale", clock_ahead: "Check clock", recent_observations: "Recent"}[status.state] || "Unknown");
    text("age", `Newest: ${when(status.newest_observed_at)}`);
    text("identifiers", report.observed_identifiers.toLocaleString());
    text("recurring", report.results.filter((row) => row.state !== "observed").length.toLocaleString());
    text("stored", status.observations.toLocaleString());
    text("updated", `Updated ${new Date().toLocaleTimeString()}`);
    const tbody = byId("radios").querySelector("tbody");
    tbody.replaceChildren();
    const sorted = report.results.sort((a, b) => Number(b.state !== "observed") - Number(a.state !== "observed") || b.last_observed_at - a.last_observed_at);
    for (const row of sorted.slice(0, 200)) {
      const tr = document.createElement("tr");
      const values = [row.address, row.state.replaceAll("_", " "), `${row.observations} / ${row.time_buckets}`, when(row.last_observed_at), row.directed_ssids.join(", ") || (row.directed_ssid_hex.length ? "Binary SSID (see JSON report)" : "No named probe")];
      values.forEach((value, index) => {
        const td = document.createElement("td");
        td.textContent = value;
        if (index === 0) {
          const detail = document.createElement("small");
          detail.textContent = `${row.protocol} · ${row.session} · ${row.observer}`;
          td.append(detail);
        }
        if (index === 1) {
          const detail = document.createElement("small");
          detail.textContent = `${Math.round(row.span_seconds)}s span · ${row.distinct_observer_locations} observer locations`;
          td.append(detail);
        }
        tr.append(td);
      });
      tbody.append(tr);
    }
    byId("empty").hidden = sorted.length !== 0;
    byId("radios").hidden = sorted.length === 0;
    byId("overflow").hidden = sorted.length <= 200;
    text("overflow", "Showing the first 200 identifiers; the CLI JSON report contains all results.");
    text("diagnostics", `${status.sources.length} capture source records. Coverage: unknown. GPS: ${status.gps}.`);
    byId("sources").replaceChildren();
    for (const source of status.sources) {
      const li = document.createElement("li");
      const skipped = Object.entries(source.skipped).map(([key, count]) => `${key}: ${count}`).join(", ") || "none";
      li.textContent = `${source.path} — ${source.rows_read} rows read; ${source.inserted} inserted; last checked ${when(source.checked_at)}. Skipped: ${skipped}.`;
      byId("sources").append(li);
    }
  } catch (error) {
    text("error", `Dashboard unavailable: ${error.message}. Previously shown data may be stale.`);
    byId("error").hidden = false;
    text("freshness", "Unavailable");
    text("updated", "Refresh failed");
  } finally {
    pending = false;
  }
}
byId("window").addEventListener("change", refresh);
refresh();
setInterval(refresh, 5000);
