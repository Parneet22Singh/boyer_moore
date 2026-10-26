const algorithmNames = {
  naive: "naive",
  horspool: "Horspool",
  "BM-bc": "BM-bc",
  "BM-bc-ext": "BM-bc-ext",
  "BM-gs": "BM-gs",
  "BM-full": "BM-full",
  "BM-full-ext": "BM-full-ext",
  "BM-galil": "BM-galil",
};

let benchmarkData = null;
let chartMetric = "average_ms";

const $ = (selector) => document.querySelector(selector);
const searchForm = $("#search-form");
const searchButton = $("#search-button");
const sourceInput = $("#source-input");
const patternInput = $("#pattern-input");
const searchResults = $("#search-results");
const searchError = $("#search-error");

function formatNumber(value, digits = 0) {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
}

function showError(element, message) {
  element.textContent = message;
  element.hidden = false;
}

function escapeAndHighlight(container, text, start, end) {
  container.append(document.createTextNode(text.slice(0, start)));
  const mark = document.createElement("mark");
  mark.textContent = text.slice(start, end);
  container.append(mark, document.createTextNode(text.slice(end)));
}

function renderMatches(data) {
  const list = $("#matches-list");
  list.replaceChildren();
  $("#metric-matches").textContent = formatNumber(data.total_matches);
  $("#metric-comparisons").textContent = formatNumber(data.comparisons);
  $("#metric-time").textContent = `${Number(data.elapsed_ms).toFixed(3)} ms`;
  $("#result-count").textContent = `(${formatNumber(data.total_matches)})`;
  $("#result-meta").textContent = `${algorithmNames[data.algorithm] || data.algorithm} · case sensitive`;
  $("#matches-subtitle").textContent = data.total_matches
    ? `Showing ${formatNumber(data.matches.length)}${data.results_truncated ? " of " + formatNumber(data.total_matches) : ""}`
    : "No occurrences in this text";

  if (data.matches.length === 0) {
    const empty = document.createElement("div");
    empty.className = "empty-matches";
    empty.textContent = "No matches found. Try a different pattern or add more text.";
    list.append(empty);
  } else {
    for (const match of data.matches) {
      const row = document.createElement("div");
      row.className = "match-row";
      const location = document.createElement("div");
      location.className = "match-location";
      const lineNumber = document.createElement("strong");
      lineNumber.textContent = formatNumber(match.line);
      location.append(lineNumber, document.createTextNode(`:${formatNumber(match.column)}`));
      const content = document.createElement("div");
      content.className = "match-text";
      escapeAndHighlight(content, match.text, match.start, match.end);
      row.append(location, content);
      list.append(row);
    }
  }
  searchResults.hidden = false;
  searchResults.scrollIntoView({ behavior: "smooth", block: "start" });
}

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  searchError.hidden = true;
  searchResults.hidden = true;
  searchButton.disabled = true;
  searchButton.querySelector("span").textContent = "Searching…";
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        pattern: patternInput.value,
        text: sourceInput.value,
        algorithm: $("#algorithm-select").value,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The search request failed.");
    renderMatches(data);
  } catch (error) {
    showError(searchError, error.message || "Could not connect to the local BM Search server.");
  } finally {
    searchButton.disabled = false;
    searchButton.querySelector("span").textContent = "Find matches";
  }
});

sourceInput.addEventListener("input", () => {
  $("#character-count").textContent = `${formatNumber(sourceInput.value.length)} character${sourceInput.value.length === 1 ? "" : "s"}`;
});

$("#file-input").addEventListener("change", async (event) => {
  const [file] = event.target.files;
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    showError(searchError, "Choose a text file smaller than 2 MB.");
    event.target.value = "";
    return;
  }
  try {
    sourceInput.value = await file.text();
    sourceInput.dispatchEvent(new Event("input"));
    searchError.hidden = true;
  } catch {
    showError(searchError, "Could not read that file. Try a plain-text or UTF-8 encoded file.");
  }
});

function formatScenario(name) {
  return name.replaceAll("^n", "ⁿ").replaceAll("^m", "ᵐ").replaceAll("-", " ");
}

function renderChart() {
  if (!benchmarkData) return;
  const chart = $("#algorithm-chart");
  chart.replaceChildren();
  const summaries = benchmarkData.summary;
  const maximum = Math.max(...summaries.map((row) => row[chartMetric]), 0.000001);
  for (const row of summaries) {
    const entry = document.createElement("div");
    entry.className = "bar-row";
    const name = document.createElement("div");
    name.className = "bar-name";
    name.textContent = row.algorithm;
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    fill.style.width = `${Math.max(3, ((maximum - row[chartMetric]) / maximum) * 100)}%`;
    track.append(fill);
    const value = document.createElement("div");
    value.className = "bar-value";
    value.textContent = chartMetric === "average_ms"
      ? `${Number(row[chartMetric]).toFixed(3)} ms`
      : Number(row[chartMetric]).toFixed(3);
    entry.append(name, track, value);
    chart.append(entry);
  }
  $("#chart-unit").textContent = chartMetric === "average_ms"
    ? "AVERAGE TIME · MILLISECONDS"
    : "AVERAGE CHARACTER COMPARISONS · PER TEXT CHARACTER";
}

function renderTable() {
  if (!benchmarkData) return;
  const selectedScenario = $("#scenario-filter").value;
  const body = $("#benchmark-table");
  body.replaceChildren();
  const records = selectedScenario === "all"
    ? benchmarkData.records
    : benchmarkData.records.filter((record) => record.scenario === selectedScenario);
  for (const record of records) {
    const row = document.createElement("tr");
    const scenario = document.createElement("td");
    scenario.textContent = formatScenario(record.scenario);
    const category = document.createElement("span");
    category.className = "category-pill";
    category.textContent = record.category === "Edge case" ? "edge" : "text";
    scenario.append(category);

    const algorithm = document.createElement("td");
    algorithm.textContent = record.algorithm;
    const sizes = document.createElement("td");
    sizes.textContent = `${formatNumber(record.text_length)} / ${formatNumber(record.pattern_length)}`;
    const hits = document.createElement("td");
    hits.textContent = formatNumber(record.matches);
    const comparisons = document.createElement("td");
    comparisons.textContent = Number(record.comparisons_per_char).toFixed(3);
    const time = document.createElement("td");
    time.textContent = `${Number(record.elapsed_ms).toFixed(3)} ms`;
    row.append(scenario, algorithm, sizes, hits, comparisons, time);
    body.append(row);
  }
}

function renderBenchmark(data) {
  benchmarkData = data;
  $("#benchmark-empty").hidden = true;
  $("#benchmark-results").hidden = false;
  $("#scenario-total").textContent = formatNumber(data.scenarios.length);
  $("#fastest-name").textContent = data.best_time;
  const fastest = data.summary.find((row) => row.algorithm === data.best_time);
  $("#fastest-time").textContent = `${Number(fastest.average_ms).toFixed(3)} ms mean runtime`;
  $("#fewest-name").textContent = data.best_comparisons;
  const fewest = data.summary.find((row) => row.algorithm === data.best_comparisons);
  $("#fewest-name").title = `${Number(fewest.average_comparisons_per_char).toFixed(3)} comparisons per character`;
  $("#fewest-name").nextElementSibling.textContent = `${Number(fewest.average_comparisons_per_char).toFixed(3)} average per character`;
  $("#run-stamp").textContent = `${formatNumber(data.size)} chars · ${data.repetitions} timing run${data.repetitions === 1 ? "" : "s"} · all 8 algorithms`;

  const filter = $("#scenario-filter");
  const previous = filter.value;
  filter.replaceChildren(new Option("All scenarios", "all"));
  for (const scenario of data.scenarios) filter.add(new Option(formatScenario(scenario), scenario));
  filter.value = data.scenarios.includes(previous) ? previous : "all";
  renderChart();
  renderTable();
  $("#benchmark-results").scrollIntoView({ behavior: "smooth", block: "start" });
}

$("#benchmark-button").addEventListener("click", async () => {
  const button = $("#benchmark-button");
  const errorBox = $("#benchmark-error");
  button.disabled = true;
  button.querySelector("span").textContent = "Benchmarking…";
  errorBox.hidden = true;
  $("#benchmark-progress").hidden = false;
  try {
    const response = await fetch("/api/benchmark", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        size: Number($("#benchmark-size").value),
        repetitions: Number($("#benchmark-repetitions").value),
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "The benchmark request failed.");
    renderBenchmark(data);
  } catch (error) {
    showError(errorBox, error.message || "Could not connect to the local BM Search server.");
  } finally {
    button.disabled = false;
    button.querySelector("span").textContent = "Run all benchmarks";
    $("#benchmark-progress").hidden = true;
  }
});

document.querySelectorAll(".chart-tab").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".chart-tab").forEach((tab) => tab.classList.remove("active"));
    button.classList.add("active");
    chartMetric = button.dataset.metric;
    renderChart();
  });
});

$("#scenario-filter").addEventListener("change", renderTable);

function navigate(viewName) {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.toggle("active", item.dataset.view === viewName);
  });
  document.querySelectorAll(".view-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${viewName}-view`);
  });
  $("#breadcrumb-current").textContent = viewName === "search" ? "Pattern search" : "Algorithm lab";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

document.querySelectorAll("[data-view]").forEach((button) => {
  button.addEventListener("click", () => navigate(button.dataset.view));
});

$("#current-date").textContent = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "2-digit",
  year: "numeric",
}).format(new Date()).toUpperCase();
