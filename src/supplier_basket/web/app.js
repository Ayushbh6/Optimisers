const state = { session: null, examples: [], selectedCase: "positive_moq_composition", resolvedIssues: [] };
const API_BASE = location.pathname.startsWith("/demos/basket") ? "/api/basket" : "";
const apiPath = (path) => `${API_BASE}${path}`;

const $ = (selector) => document.querySelector(selector);
const money = (value) => `€${Number(value).toFixed(2)}`;
const friendlyDate = (value) => new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));

const scenarioCopy = {
  positive_moq_composition: {
    tag: "Find avoidable stock",
    title: "Can we safely spend less?",
    detail: "The buyer added extra stock to reach the supplier's minimum order.",
  },
  unsafe_cheaper_delivery_loss: {
    tag: "Protect customer deliveries",
    title: "Is the cheaper order actually safe?",
    detail: "A lower-cost edit may leave one booked customer delivery short.",
  },
  no_change_control: {
    tag: "Know when to leave it alone",
    title: "Should we keep the current order?",
    detail: "The buyer's original order may already be the best safe choice.",
  },
};

const issueCopy = {
  "ISS-002": {
    title: "Is the quantity 5 cases or 5 tins?",
    detail: "The export left the unit blank. The buyer's PDF says 5 cases, which equals 60 tins.",
    action: "Confirm 5 cases",
  },
  "ISS-005": {
    title: "What supplier minimum should we use?",
    detail: "The ERP export left this blank. The signed supplier terms say €150.",
    action: "Use signed €150 minimum",
  },
};

async function api(path, options = {}) {
  const response = await fetch(apiPath(path), {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const type = response.headers.get("content-type") || "";
  const payload = type.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) throw new Error(payload.error || `Request failed (${response.status})`);
  return payload;
}

function showNotice(message = "") {
  const notice = $("#notice");
  notice.hidden = !message;
  notice.textContent = message;
}

function scenarioButton(example) {
  const copy = scenarioCopy[example.case_id];
  const button = document.createElement("button");
  button.type = "button";
  button.className = "scenario-option";
  button.dataset.caseId = example.case_id;
  button.setAttribute("role", "radio");
  const tag = document.createElement("span");
  tag.textContent = `${String(Object.keys(scenarioCopy).indexOf(example.case_id) + 1).padStart(2, "0")} / ${copy.tag}`;
  const title = document.createElement("strong");
  title.textContent = copy.title;
  const detail = document.createElement("small");
  detail.textContent = copy.detail;
  button.append(tag, title, detail);
  button.addEventListener("click", () => selectScenario(example.case_id));
  return button;
}

function selectScenario(caseId) {
  state.selectedCase = caseId;
  document.querySelectorAll(".scenario-option").forEach((button) => {
    const selected = button.dataset.caseId === caseId;
    button.classList.toggle("selected", selected);
    button.setAttribute("aria-checked", String(selected));
  });
}

function auditIssue(issue) {
  const row = document.createElement("div");
  row.className = "resolved-item";
  const label = document.createElement("span");
  label.textContent = issue.title;
  const status = document.createElement("strong");
  status.textContent = issue.status === "resolved" ? "Checked" : "Needs confirmation";
  row.append(label, status);
  return row;
}

function actionIssue(issue) {
  const copy = issueCopy[issue.issue_id] || { title: issue.title, detail: issue.detail, action: issue.action_label || "Confirm" };
  const row = document.createElement("div");
  row.className = "action-question";
  const body = document.createElement("div");
  const title = document.createElement("h3");
  title.textContent = copy.title;
  const detail = document.createElement("p");
  detail.textContent = copy.detail;
  body.append(title, detail);
  const button = document.createElement("button");
  button.className = "button primary";
  button.type = "button";
  button.textContent = copy.action;
  button.addEventListener("click", () => resolveIssue(issue.issue_id, button));
  row.append(body, button);
  return row;
}

function basketLines(container, lines) {
  container.replaceChildren();
  lines.forEach((line) => {
    const row = document.createElement("div");
    row.className = "basket-line";
    const left = document.createElement("span");
    const label = document.createElement("strong");
    label.textContent = line.product_name || line.product_id;
    const detail = document.createElement("small");
    detail.textContent = `${line.quantity_units} units · ${money(line.line_value_eur)}`;
    left.append(label, detail);
    const cases = document.createElement("b");
    cases.textContent = `${line.cases} case${line.cases === 1 ? "" : "s"}`;
    row.append(left, cases);
    container.append(row);
  });
}

function render(session) {
  state.session = session;
  showNotice();
  $("#review").hidden = false;
  $("#case-title").textContent = scenarioCopy[session.case_id].title;
  $("#row-count").textContent = session.source_row_count;
  $("#input-hash").textContent = session.input_hash;
  $("#resolved-list").replaceChildren(...session.issues.map(auditIssue));
  const blockers = session.issues.filter((issue) => issue.blocks_planning);
  $("#action-list").replaceChildren(...blockers.map(actionIssue));
  if (blockers.length) {
    $("#check-heading").textContent = "One answer is needed first.";
    $("#check-copy").textContent = "We found a missing detail that changes whether the order is valid. Confirm it before Ledgerline recommends anything.";
    $("#check-status").textContent = "Waiting for you";
    $("#check-status").className = "status-badge warning";
    $("#decision-section").hidden = true;
  } else {
    $("#check-heading").textContent = "The records are ready.";
    $("#check-copy").textContent = "The products, customer orders, stock and supplier terms now agree. Nothing important was guessed silently.";
    $("#check-status").textContent = "Checked";
    $("#check-status").className = "status-badge success";
    renderDecision(session);
  }
}

function renderCharts(decision) {
  const metrics = [
    { title: "Cash to place the order", key: "immediate_cash_eur", format: money, note: "Including delivery charges" },
    { title: "Stock left + commitments", key: "ending_stock_plus_commitments_eur", format: money, note: "At the end of the 28-day replay" },
    { title: "Booked units on time", key: "on_time_units", format: (v) => `${v} / ${decision.selected.booked_units}`, note: "Customer deliveries protected", limit: decision.selected.booked_units },
  ];
  $("#comparison-charts").replaceChildren(...metrics.map((metric) => {
    const figure = document.createElement("figure");
    figure.className = "metric-chart";
    const heading = document.createElement("figcaption");
    heading.textContent = metric.title;
    figure.append(heading);
    const maximum = Math.max(1, Number(decision.buyer[metric.key]), Number(decision.selected[metric.key]), metric.limit || 0);
    ["buyer", "selected"].forEach((side) => {
      const value = Number(decision[side][metric.key]);
      const row = document.createElement("div");
      row.className = `chart-row ${side}`;
      const label = document.createElement("span");
      label.className = "chart-label";
      label.textContent = side === "buyer" ? "Before" : "After";
      const amount = document.createElement("strong");
      amount.textContent = metric.format(value);
      const rail = document.createElement("div");
      rail.className = "chart-rail";
      rail.setAttribute("aria-hidden", "true");
      const bar = document.createElement("div");
      bar.className = "chart-bar";
      bar.style.width = `${100 * value / maximum}%`;
      rail.append(bar);
      row.append(label, amount, rail);
      figure.append(row);
    });
    const note = document.createElement("p");
    note.textContent = metric.note;
    figure.append(note);
    return figure;
  }));
}

function renderDecision(session) {
  const decision = session.decision;
  const accepted = decision.verdict === "accept_proposed";
  $("#decision-section").hidden = false;
  $("#decision-heading").textContent = accepted ? "Less cash. Deliveries protected." : "Keep the current order.";
  $("#verdict-badge").textContent = accepted ? "Change order" : "No change";
  if (accepted) {
    $("#decision-summary").textContent = `Spend ${money(Math.abs(Number(decision.comparison.cash_change_eur)))} less now while keeping all ${decision.selected.booked_units} booked units on time.`;
  } else if (session.case_id === "unsafe_cheaper_delivery_loss") {
    $("#decision-summary").textContent = "Keep the current order. The cheaper option saves €30.00 now, but 12 booked units would arrive late.";
  } else {
    $("#decision-summary").textContent = "Keep the current order. Every cheaper option either breaks a supplier rule or risks a booked delivery.";
  }
  renderCharts(decision);
  $("#before-total").textContent = money(decision.buyer.immediate_cash_eur);
  $("#after-total").textContent = money(decision.selected.immediate_cash_eur);
  $("#before-ending").textContent = money(decision.buyer.ending_stock_plus_commitments_eur);
  $("#after-ending").textContent = money(decision.selected.ending_stock_plus_commitments_eur);
  basketLines($("#before-lines"), decision.buyer.lines);
  basketLines($("#after-lines"), decision.selected.lines);

  const changes = $("#change-list");
  changes.replaceChildren();
  if (!decision.product_changes.length) {
    const item = document.createElement("li");
    item.textContent = "Nothing. Every cheaper edit either breaks a rule or risks a booked delivery.";
    changes.append(item);
  } else {
    decision.product_changes.forEach((change) => {
      const item = document.createElement("li");
      item.textContent = change.selected_cases === 0
        ? `${change.product_name}: remove the ${change.buyer_cases} case; it is not needed for a booked delivery.`
        : `${change.product_name}: add ${change.change_cases} cases so the order still reaches the supplier minimum.`;
      changes.append(item);
    });
  }
  $("#delivery-proof").textContent = `${decision.selected.on_time_units} of ${decision.selected.booked_units} booked units still arrive on time. ${decision.selected.expired_units} units expire.`;
  const risks = $("#risk-list");
  risks.replaceChildren();
  if (!accepted && decision.summary.includes("challenged basket")) {
    const risk = document.createElement("p");
    risk.className = "risk-item";
    risk.textContent = "The tempting cheaper option was tested and rejected because it would make a booked customer delivery late.";
    risks.append(risk);
  }
  $("#export-title").textContent = decision.buyer_action;
  $("#export-note").textContent = `Supplier delivery expected ${friendlyDate(decision.operational_consequences.expected_arrival)}.`;
  const exportQuery = new URLSearchParams({ case_id: session.case_id, issues: state.resolvedIssues.join(",") });
  $("#export-button").href = apiPath(`/api/sessions/${session.session_id}/export?${exportQuery}`);
  $("#search-proof").textContent = `${decision.search_report.physically_replayed} feasible alternatives were replayed through the warehouse; the search was capped at ${decision.search_report.max_alternatives}.`;
  $("#decision-hash").textContent = `Decision fingerprint: ${decision.decision_hash}`;
}

async function loadExample() {
  showNotice();
  state.resolvedIssues = [];
  const button = $("#load-case");
  button.disabled = true;
  button.textContent = "Checking order…";
  try {
    const session = await api("/api/sessions/example", { method: "POST", body: JSON.stringify({ case_id: state.selectedCase }) });
    render(session);
    $("#review").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showNotice(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Review this order";
  }
}

async function resolveIssue(issueId, button) {
  button.disabled = true;
  button.textContent = "Checking…";
  try {
    const resolvedIssues = [...new Set([...state.resolvedIssues, issueId])];
    state.resolvedIssues = resolvedIssues;
    const session = await api(`/api/sessions/${state.session.session_id}/resolve`, { method: "POST", body: JSON.stringify({ case_id: state.selectedCase, issue_id: issueId, resolved_issue_ids: resolvedIssues }) });
    render(session);
    $("#decision-section").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    showNotice(error.message);
    button.disabled = false;
  }
}

async function resetSession() {
  if (!API_BASE && state.session?.session_id) {
    try {
      await api(`/api/sessions/${state.session.session_id}`, { method: "DELETE" });
    } catch (error) {
      showNotice(error.message);
      return;
    }
  }
  state.session = null;
  state.resolvedIssues = [];
  $("#review").hidden = true;
  showNotice();
  $("#scroll-region").scrollTo({ top: 0, behavior: "smooth" });
}

async function init() {
  try {
    const returnLink = $(".studio-back");
    const requestedReturn = new URLSearchParams(location.search).get("return");
    if (requestedReturn) {
      const target = new URL(requestedReturn, location.origin);
      if (["http:", "https:"].includes(target.protocol)) returnLink.href = target.href;
    } else if (location.pathname.startsWith("/demos/")) {
      returnLink.href = "/work/";
    } else {
      returnLink.href = "http://127.0.0.1:4321/work/";
    }
    state.examples = await api("/api/examples");
    $("#scenario-list").replaceChildren(...state.examples.map(scenarioButton));
    selectScenario(state.selectedCase);
    $("#load-case").addEventListener("click", loadExample);
    $("#reset-session").addEventListener("click", resetSession);
  } catch (error) {
    showNotice(error.message);
  }
}

document.addEventListener("DOMContentLoaded", init);
