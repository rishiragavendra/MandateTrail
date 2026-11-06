"use client";
import { useEffect, useState, type ReactNode } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import {
  Orbit,
  LayoutDashboard,
  Bot,
  ShieldCheck,
  ArrowLeftRight,
  GitBranch,
  Network,
  CheckCheck,
  FlaskConical,
  FileCheck2,
  Settings,
  Search,
  Bell,
  PanelLeftClose,
  PanelLeftOpen,
  ArrowUpRight,
  ArrowRight,
  Plus,
  Play,
  Download,
  RefreshCw,
  LogOut,
  X,
  Check,
  Lock,
  Activity,
  ChevronRight,
  AlertTriangle,
  LoaderCircle,
  Radio,
  KeyRound,
  ShieldAlert,
  Eye,
  ChevronDown,
} from "lucide-react";
import { api, setCsrf, money, short, when, type Json } from "../lib/api";
import Provenance from "../components/provenance";
import { ThemeToggle } from "../components/theme-provider";

const client = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});
const navigation = [
  ["Overview", LayoutDashboard],
  ["Agents", Bot],
  ["Mandates", ShieldCheck],
  ["Transactions", ArrowLeftRight],
  ["Workflows", GitBranch],
  ["Provenance", Network],
  ["Approvals", CheckCheck],
  ["Security Lab", FlaskConical],
  ["Evidence", FileCheck2],
  ["Settings", Settings],
] as const;
const colors = ["var(--chart-allow)", "var(--chart-observe)", "var(--chart-escalate)", "var(--chart-deny)"];
const statusClass = (v: string) =>
  ["ALLOW", "COMPLETED", "ACTIVE", "SIGNED", "VERIFIED_REGISTRY"].includes(v)
    ? "good"
    : ["DENY", "BLOCKED", "REVOKED", "FAILED"].includes(v)
      ? "bad"
      : "warn";
function Badge({ value }: { value: string }) {
  return (
    <span className={"badge " + statusClass(value)}>
      <i />
      {value.replaceAll("_", " ")}
    </span>
  );
}
function Button({
  children,
  onClick,
  secondary = false,
  disabled = false,
}: {
  children: ReactNode;
  onClick?: () => void;
  secondary?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      className={secondary ? "button secondary" : "button"}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}
function Panel({
  title,
  sub,
  children,
  action,
}: {
  title: string;
  sub?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-head">
        <div>
          <h3>{title}</h3>
          {sub && <p>{sub}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
function JsonView({ data }: { data: unknown }) {
  return <pre className="json">{JSON.stringify(data, null, 2)}</pre>;
}
function Empty({
  text = "No records yet. Run a procurement workflow to get started.",
}: {
  text?: string;
}) {
  return (
    <div className="empty">
      <Orbit size={30} />
      <p>{text}</p>
    </div>
  );
}
function App() {
  const qc = useQueryClient();
  const [user, setUser] = useState<Json | null>(null);
  const [boot, setBoot] = useState(true);
  const [page, setPage] = useState("Overview");
  const [collapsed, setCollapsed] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [modal, setModal] = useState<string | null>(null);
  const [detail, setDetail] = useState<Json | null>(null);
  const [detailTab, setDetailTab] = useState("Overview");
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("");
  const [wf, setWf] = useState("");
  const [scenario, setScenario] = useState("cross_session");
  const [environments, setEnvironments] = useState([
    "baseline",
    "basic",
    "protected",
  ]);
  const [labResult, setLabResult] = useState<Json | null>(null);
  const [verification, setVerification] = useState<Json | null>(null);
  const [replay, setReplay] = useState(0);
  const [replaying, setReplaying] = useState(false);
  const reduced = useReducedMotion();
  const loginForm = useForm<{ email: string; password: string }>({
    defaultValues: { email: "admin@mandatetrail.local", password: "" },
  });
  const [form, setForm] = useState<Json>({});
  useEffect(() => {
    api("/auth/me")
      .then((u) => {
        setUser(u);
        setCsrf(u.csrf);
      })
      .catch(() => {})
      .finally(() => setBoot(false));
  }, []);
  const query = (key: string, path: string, enabled = true) =>
    useQuery<Json>({
      queryKey: [key, user?.id],
      queryFn: () => api(path),
      enabled: !!user && enabled,
      refetchInterval: key === "dashboard" ? 8000 : false,
    });
  const dash = query("dashboard", "/dashboard");
  const agents = query("agents", "/agents");
  const mandates = query("mandates", "/mandates");
  const suppliers = query("suppliers", "/suppliers");
  const workflows = query("workflows", "/workflows");
  const approvals = query("approvals", "/approvals");
  const tx = useQuery<Json>({
    queryKey: ["transactions", user?.id, search, filter],
    queryFn: () =>
      api(
        "/transactions?q=" + encodeURIComponent(search) + "&status=" + filter,
      ),
    enabled: !!user,
  });
  const alerts = query("alerts", "/alerts");
  const settings = query("settings", "/settings");
  const scenarios = query("scenarios", "/redteam/scenarios");
  const metrics = query("metrics", "/redteam/metrics");
  const runs = query("runs", "/redteam/runs");
  const audit = useQuery<Json[]>({
    queryKey: ["audit", user?.id, wf],
    queryFn: () => api("/audit" + (wf ? "?workflow=" + wf : "")),
    enabled: !!user,
  });
  const graph = useQuery<Json>({
    queryKey: ["graph", user?.id, wf],
    queryFn: () => api("/provenance/" + wf),
    enabled: !!user && !!wf,
  });
  const workflow = useQuery<Json>({
    queryKey: ["workflow", user?.id, wf],
    queryFn: () => api("/workflows/" + wf),
    enabled: !!user && !!wf,
  });
  const aa = (agents.data || []) as Json[];
  const mm = (mandates.data || []) as Json[];
  const ss = (suppliers.data || []) as Json[];
  const ww = (workflows.data || []) as Json[];
  const ap = (approvals.data || []) as Json[];
  const lookup = (id: string) => ss.find((s) => s.id === id)?.name || short(id);
  useEffect(() => {
    if (!wf && ww.length) setWf(ww[0].id);
  }, [ww, wf]);
  useEffect(() => {
    if (!replaying) return;
    const timer = setInterval(
      () =>
        setReplay((v) => {
          if (v >= (workflow.data?.events?.length || 0)) {
            setReplaying(false);
            return v;
          }
          return v + 1;
        }),
      reduced ? 50 : 450,
    );
    return () => clearInterval(timer);
  }, [replaying, workflow.data, reduced]);
  async function act(
    fn: () => Promise<unknown>,
    message = "Saved successfully",
  ) {
    setBusy(true);
    setError("");
    try {
      const result = await fn();
      await qc.invalidateQueries();
      if (message) setNotice(message);
      return result;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function go(name: string) {
    setPage(name);
    setSearch("");
    setFilter("");
    setDetail(null);
  }
  function openForm(name: string) {
    setForm({
      agent_id: aa[0]?.id,
      mandate_id: mm.find((m) => m.status === "ACTIVE")?.id,
      supplier_id: ss[0]?.id,
      per_transaction: 500000,
      aggregate: 1500000,
      approval_above: 100000,
      amount_minor: 48000,
      invoice_ref: "INV-" + Date.now(),
      poison: false,
      simulator_outcome: 'COMPLETED',
      currency: "INR",
      name: "",
      beneficiary_ref: "BEN-",
    });
    setModal(name);
    setError("");
  }
  async function submit() {
    const result = (await act(
      async () => {
        if (modal === "Register agent") {
          const v = z.string().min(2).parse(form.name);
          return api("/agents", {
            name: v,
            capabilities: settings.data?.tools || [],
          });
        }
        if (modal === "Create mandate")
          return api("/mandates", {
            name: form.name,
            agent_id: form.agent_id,
            suppliers: [form.supplier_id],
            currency: form.currency,
            per_transaction: Number(form.per_transaction),
            aggregate: Number(form.aggregate),
            approval_above: Number(form.approval_above),
          });
        if (modal === "Add supplier")
          return api("/suppliers", {
            name: form.name,
            beneficiary_ref: form.beneficiary_ref,
          });
        return api("/procurement/run", {
          mandate_id: form.mandate_id,
          supplier_id: form.supplier_id,
          amount_minor: Number(form.amount_minor),
          invoice_ref: form.invoice_ref,
          poison: form.poison,
          simulator_outcome: form.simulator_outcome,
        });
      },
      modal === "Procurement workflow"
        ? "Workflow completed · inspect the recorded decision"
        : "Saved successfully",
    )) as Json | undefined;
    if (result) {
      setModal(null);
      if (result.token_once)
        setDetail({
          title: "Agent registered · copy token now",
          token_once: result.token_once,
          note: "Shown once. Keep private; this token cannot approve payments.",
        });
      else if (result.payload) {
        setDetail(result);
        setWf(result.payload.workflow_id);
      }
    }
  }
  async function showTx(t: Json) {
    const result = (await act(() => api("/transactions/" + t.id), "")) as
      Json | undefined;
    if (result) {
      setDetail(result);
      setDetailTab("Overview");
    }
  }
  const exportEvidence = () => {
    if (wf) window.open("/api/v1/evidence/" + wf, "_blank", "noopener");
  };
  const workflowSelect = (
    <select
      aria-label="Select workflow"
      value={wf}
      onChange={(e) => {
        setWf(e.target.value);
        setReplay(0);
        setReplaying(false);
      }}
    >
      <option value="">Select workflow</option>
      {ww.map((w) => (
        <option key={w.id} value={w.id}>
          {short(w.id)} · {w.title}
        </option>
      ))}
    </select>
  );
  function Transactions({ items }: { items: Json[] }) {
    return items.length ? (
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>TRANSACTION / SUPPLIER</th>
              <th>AMOUNT</th>
              <th>POLICY</th>
              <th>EXECUTION</th>
              <th>TIME</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((t) => (
              <tr
                key={t.id}
                onClick={() => showTx(t)}
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === "Enter") showTx(t);
                }}
              >
                <td>
                  <strong>{lookup(t.payload.supplier_id)}</strong>
                  <small className="mono">{short(t.id)}</small>
                </td>
                <td>
                  {money(t.payload.amount_minor, t.payload.currency)}
                  <small>{t.payload.invoice_ref}</small>
                </td>
                <td>
                  <Badge value={t.decision.outcome} />
                </td>
                <td>
                  <Badge value={t.outcome} />
                </td>
                <td className="muted">
                  {new Date(t.created).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </td>
                <td>
                  <ChevronRight size={16} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    ) : (
      <Empty />
    );
  }
  if (boot)
    return (
      <div className="loading">
        <Orbit className="spin" />
        Connecting to orbital control…
      </div>
    );
  if (!user)
    return (
      <main className="login">
        <div className="login-theme-control"><ThemeToggle /></div>
        <div className="login-art">
          <div className="brand">
            <Orbit size={30} />
            <span>
              MandateTrail<small>ORBITAL INTELLIGENCE</small>
            </span>
          </div>
          <div className="login-copy">
            <span className="eyebrow">FINANCIAL AGENT SECURITY</span>
            <h1>
              Every action
              <br />
              has an origin.
            </h1>
            <p>Every transaction needs authority.</p>
            <div className="orbit-hero">
              <div />
              <div />
              <div />
              <ShieldCheck size={64} />
              <i />
              <i />
              <i />
            </div>
            <span className="badge good">
              <i />
              SYNTHETIC SANDBOX · NO REAL MONEY
            </span>
          </div>
          <small>Authority. Provenance. Integrity.</small>
        </div>
        <section className="login-form">
          <ShieldCheck size={34} className="blue" />
          <h2>Welcome to mission control</h2>
          <p className="muted">Sign in to your local MandateTrail sandbox.</p>
          <form
            onSubmit={loginForm.handleSubmit(async (values) => {
              await act(async () => {
                const u = await api("/auth/login", values);
                setCsrf(u.csrf);
                setUser(u);
                return u;
              }, "Signed in");
            })}
          >
            <label>
              Email
              <input
                type="email"
                autoComplete="username"
                {...loginForm.register("email", { required: true })}
              />
            </label>
            <label>
              Password
              <input
                type="password"
                autoComplete="current-password"
                {...loginForm.register("password", { required: true })}
              />
            </label>
            {error && (
              <div className="error" role="alert">
                {error}
              </div>
            )}
            <button className="button" type="submit" disabled={busy}>
              {busy ? (
                <LoaderCircle className="spin" size={16} />
              ) : (
                <Lock size={16} />
              )}
              Enter command center
              <ArrowRight size={16} />
            </button>
          </form>
          <div className="hint">
            <KeyRound size={17} />
            <span>
              Your generated password is in{" "}
              <code>backend/data/DEMO_CREDENTIALS.txt</code>. The launcher
              displays its location.
            </span>
          </div>
          <p className="tiny muted">
            Local development prototype · Ed25519-signed authority · simulated
            payments
          </p>
        </section>
      </main>
    );
  return (
    <div className={"shell " + (collapsed ? "compact" : "")}>
      <aside>
        <div className="brand">
          <Orbit size={30} />
          {!collapsed && (
            <span>
              MandateTrail<small>ORBITAL INTELLIGENCE</small>
            </span>
          )}
        </div>
        <div className="workspace-mark">
          {collapsed ? (
            "OI"
          ) : (
            <>
              {" "}
              <span className="workspace-icon">O</span>
              <span>
                Orbital Industries<small>Synthetic workspace</small>
              </span>
              <ChevronDown size={14} />
            </>
          )}
        </div>
        <p className="nav-label">{collapsed ? "···" : "COMMAND CENTER"}</p>
        <nav>
          {navigation.map(([name, Icon]) => (
            <button
              key={name}
              className={page === name ? "active" : ""}
              title={name}
              onClick={() => go(name)}
            >
              <Icon size={19} />
              {!collapsed && (
                <>
                  <span>{name}</span>
                  {name === "Approvals" && dash.data?.pending_approvals > 0 && (
                    <em>{dash.data?.pending_approvals}</em>
                  )}
                  {name === "Security Lab" && (
                    <small className="lab-label">LAB</small>
                  )}
                </>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          {!collapsed && (
            <div className="shield-status">
              <ShieldCheck size={19} />
              <div>
                Execution boundary active
                <small>Synthetic payment adapter</small>
              </div>
              <i className="dot" />
            </div>
          )}
          <button onClick={() => setCollapsed(!collapsed)}>
            {collapsed ? (
              <PanelLeftOpen size={19} />
            ) : (
              <>
                <PanelLeftClose size={19} />
                Collapse navigation
              </>
            )}
          </button>
        </div>
      </aside>
      <div className="main-shell">
        <header>
          <div className="breadcrumb">
            Workspace <ChevronRight size={13} />
            <strong>{page}</strong>
          </div>
          <div className="header-right">
            <ThemeToggle />
            <label className="global-search">
              <Search size={15} />
              <input
                placeholder="Search transactions…"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage("Transactions");
                }}
              />
              <kbd>/</kbd>
            </label>
            <span className="sandbox">
              <i />
              SANDBOX
            </span>
            <button
              className="icon-button"
              title="Open security alerts"
              onClick={() => {
                setDetail({
                  title: "Security notifications",
                  alerts: alerts.data || [],
                });
              }}
            >
              <Bell size={19} />
              {dash.data?.critical_alerts > 0 && (
                <i className="notification-dot" />
              )}
            </button>
            <button
              className="avatar"
              title={user.email}
              onClick={() => go("Settings")}
            >
              OI
            </button>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                ORBITAL INTELLIGENCE / {page.toUpperCase()}
              </div>
              <h1>
                {page === "Overview"
                  ? "Security command center"
                  : page === "Security Lab"
                    ? "RedTeamLab"
                    : page === "Evidence"
                      ? "ForensicLedger"
                      : page === "Provenance"
                        ? "Follow every financial field"
                        : page}
              </h1>
              <p>
                {page === "Overview"
                  ? "A clear line of sight from agent intent to authorized execution."
                  : page === "Security Lab"
                    ? "Reproduce adversarial workflows. Compare actual control outcomes."
                    : page === "Approvals"
                      ? "Human authority, bound to the exact transaction payload."
                      : "Authority, data lineage, and execution evidence in one workspace."}
              </p>
            </div>
            <div className="actions">
              <span className="live-label">
                <Radio size={14} />
                LOCAL SANDBOX
              </span>
              {["Overview", "Transactions", "Workflows"].includes(page) && (
                <Button onClick={() => openForm("Procurement workflow")}>
                  <Plus size={16} />
                  New workflow
                </Button>
              )}
            </div>
          </div>
          {error && (
            <div className="error" role="alert">
              <AlertTriangle size={17} />
              {error}
              <button onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {[dash, agents, mandates, tx, workflows, graph, workflow].some(
            (q) => q.isError,
          ) && (
            <div className="error">
              A data request failed.{" "}
              <button onClick={() => qc.invalidateQueries()}>
                Retry connection
              </button>
            </div>
          )}
          <AnimatePresence mode="wait">
            <motion.div
              key={page}
              initial={reduced ? false : { opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.18 }}
            >
              {page === "Overview" && (
                <>
                  <div className="hero-strip">
                    <div>
                      <span className="eyebrow">
                        <span className="dot" />
                        EXECUTIONSHIELD ONLINE
                      </span>
                      <h2>
                        Trust is a chain.
                        <br />
                        <span>Keep every link verified.</span>
                      </h2>
                      <p>
                        Signed mandates. Persistent provenance. Deterministic
                        enforcement.
                      </p>
                      <button
                        className="text-button"
                        onClick={() => go("Security Lab")}
                      >
                        Explore the security lab
                        <ArrowUpRight size={16} />
                      </button>
                    </div>
                    <div className="orbital-map">
                      <div className="orbit-ring r1" />
                      <div className="orbit-ring r2" />
                      <div className="orbit-ring r3" />
                      <div className="core-node">
                        <ShieldCheck size={35} />
                      </div>
                      {aa.slice(0, 3).map((a, i) => (
                        <button
                          key={a.id}
                          className={"agent-orbit agent-" + i}
                          onClick={() =>
                            act(
                              async () =>
                                setDetail(await api("/agents/" + a.id)),
                              "",
                            )
                          }
                          title={a.name}
                        >
                          <Bot size={18} />
                          <span>
                            {a.name.split("·")[0]}
                            <small>
                              {a.active ? "ACTIVE AGENT" : "INACTIVE"}
                            </small>
                          </span>
                          <i className="dot" />
                        </button>
                      ))}
                      <span className="telemetry t1">AUTHORITY VERIFIED</span>
                      <span className="telemetry t2">
                        PROVENANCE / CONTINUOUS
                      </span>
                    </div>
                  </div>
                  <div className="metric-grid">
                    {[
                      [
                        "Registered agents",
                        dash.data?.agents,
                        Bot,
                        "Registered identities",
                      ],
                      [
                        "Inspected actions",
                        dash.data?.inspected,
                        Activity,
                        "Persisted policy evaluations",
                      ],
                      [
                        "Denied actions",
                        dash.data?.decisions?.DENY,
                        ShieldAlert,
                        "Stopped by deterministic policy",
                      ],
                      [
                        "Simulated executions",
                        dash.data?.simulated_executions,
                        CheckCheck,
                        "Confirmed simulator receipts",
                      ],
                    ].map(([label, value, Icon, sub]) => {
                      const I = Icon as typeof Bot;
                      return (
                        <div className="metric" key={String(label)}>
                          <div>
                            <span>{String(label)}</span>
                            <I size={18} />
                          </div>
                          <strong>
                            {value === undefined ? "—" : String(value)}
                          </strong>
                          <small>{String(sub)}</small>
                        </div>
                      );
                    })}
                  </div>
                  <div className="dashboard-grid">
                    <Panel
                      title="Recent financial activity"
                      sub="Actual transactions · seeded synthetic demonstration"
                      action={
                        <button
                          className="text-button"
                          onClick={() => go("Transactions")}
                        >
                          View all
                          <ArrowUpRight size={14} />
                        </button>
                      }
                    >
                      <Transactions
                        items={dash.data?.recent_transactions || []}
                      />
                    </Panel>
                    <Panel
                      title="Policy decision distribution"
                      sub="Backend-derived · all sandbox actions"
                    >
                      <div className="chart">
                        <ResponsiveContainer width="100%" height={180}>
                          <PieChart>
                            <Pie
                              data={Object.entries(
                                dash.data?.decisions || {},
                              ).map(([name, value]) => ({ name, value }))}
                              dataKey="value"
                              innerRadius={58}
                              outerRadius={80}
                              paddingAngle={5}
                            >
                              {colors.map((color) => (
                                <Cell key={color} fill={color} stroke="none" />
                              ))}
                            </Pie>
                            <Tooltip
                              contentStyle={{
                                background: "var(--popover)",
                                color: "var(--popover-foreground)",
                                border: "1px solid var(--border)",
                                borderRadius: 8,
                              }}
                            />
                          </PieChart>
                        </ResponsiveContainer>
                        <div className="chart-center">
                          <strong>{dash.data?.inspected ?? 0}</strong>
                          <small>ACTIONS</small>
                        </div>
                      </div>
                      <div className="legend">
                        {Object.entries(dash.data?.decisions || {}).map(
                          ([name, value], i) => (
                            <div key={name}>
                              <span>
                                <i style={{ background: colors[i] }} />
                                {name}
                              </span>
                              <b>{String(value)}</b>
                            </div>
                          ),
                        )}
                      </div>
                    </Panel>
                  </div>
                  <div className="dashboard-grid">
                    <Panel
                      title="Live security activity"
                      sub="Recent persisted events · refreshed every 8 seconds"
                      action={
                        <span className="badge good">
                          <i />
                          CONNECTED
                        </span>
                      }
                    >
                      <div className="activity-feed">
                        {(dash.data?.activity || [])
                          .slice(0, 6)
                          .map((e: Json) => (
                            <div key={e.id}>
                              <span
                                className={
                                  "event-icon " +
                                  (e.type.includes("blocked") ? "bad" : "blue")
                                }
                              >
                                <Activity size={15} />
                              </span>
                              <div>
                                <strong>
                                  {e.type
                                    .replaceAll(".", " / ")
                                    .replaceAll("_", " ")}
                                </strong>
                                <small className="mono">
                                  {short(e.workflow || e.id)}
                                </small>
                              </div>
                              <time>
                                {new Date(e.timestamp).toLocaleTimeString()}
                              </time>
                            </div>
                          ))}
                      </div>
                    </Panel>
                    <Panel
                      title="Attention required"
                      sub="Financial exceptions and human review"
                    >
                      <button
                        className="attention-row"
                        onClick={() => go("Approvals")}
                      >
                        <span className="event-icon warn">
                          <CheckCheck size={19} />
                        </span>
                        <div>
                          <strong>
                            {dash.data?.pending_approvals ?? 0} pending
                            approvals
                          </strong>
                          <small>Review exact payloads before signing</small>
                        </div>
                        <ChevronRight size={17} />
                      </button>
                      <button
                        className="attention-row"
                        onClick={() =>
                          setDetail({
                            title: "Security alerts",
                            alerts: alerts.data || [],
                          })
                        }
                      >
                        <span className="event-icon bad">
                          <ShieldAlert size={19} />
                        </span>
                        <div>
                          <strong>
                            {dash.data?.critical_alerts ?? 0} critical alerts
                          </strong>
                          <small>Inspect policy and lineage evidence</small>
                        </div>
                        <ChevronRight size={17} />
                      </button>
                      <div className="lab-callout">
                        <FlaskConical size={25} />
                        <h4>Put the boundary to the test.</h4>
                        <p>
                          Run the cross-session poisoning scenario against three
                          environments.
                        </p>
                        <button
                          className="text-button"
                          onClick={() => go("Security Lab")}
                        >
                          Launch RedTeamLab
                          <ArrowRight size={15} />
                        </button>
                      </div>
                    </Panel>
                  </div>
                </>
              )}
              {page === "Agents" && (
                <>
                  <div className="toolbar">
                    <p>
                      {aa.length} registered identities · capabilities enforced
                      at gateway
                    </p>
                    <Button onClick={() => openForm("Register agent")}>
                      <Plus size={16} />
                      Register agent
                    </Button>
                  </div>
                  <div className="cards">
                    {aa.map((a) => (
                      <Panel
                        key={a.id}
                        title={a.name}
                        sub={short(a.id)}
                        action={
                          <Badge value={a.active ? "ACTIVE" : "INACTIVE"} />
                        }
                      >
                        <div className="agent-symbol">
                          <Bot size={32} />
                        </div>
                        <p className="muted">
                          {a.capabilities.length} controlled capabilities
                        </p>
                        <div className="tags">
                          {a.capabilities.map((t: string) => (
                            <span key={t}>{t}</span>
                          ))}
                        </div>
                        <div className="card-actions">
                          <Button
                            secondary
                            onClick={() =>
                              act(
                                async () =>
                                  setDetail(await api("/agents/" + a.id)),
                                "",
                              )
                            }
                          >
                            <Eye size={15} />
                            Inspect
                          </Button>
                          <Button
                            secondary
                            onClick={() =>
                              act(
                                () => api("/agents/" + a.id + "/toggle", {}),
                                "Agent state updated",
                              )
                            }
                          >
                            {a.active ? "Deactivate" : "Activate"}
                          </Button>
                        </div>
                      </Panel>
                    ))}
                  </div>
                </>
              )}
              {page === "Mandates" && (
                <>
                  <div className="toolbar">
                    <p>Ed25519-signed authority · integer minor-unit budgets</p>
                    <Button onClick={() => openForm("Create mandate")}>
                      <Plus size={16} />
                      Create mandate
                    </Button>
                  </div>
                  <div className="cards">
                    {mm.map((m) => (
                      <Panel
                        key={m.id}
                        title={m.name}
                        sub={"Version " + m.version + " · " + short(m.id)}
                        action={<Badge value={m.status} />}
                      >
                        <div className="mandate-limit">
                          <small>PER-TRANSACTION CEILING</small>
                          <strong>
                            {money(m.per_transaction, m.currency)}
                          </strong>
                        </div>
                        <div className="budget-label">
                          <span>Reserved / committed</span>
                          <b>
                            {money(m.spent, m.currency)} /{" "}
                            {money(m.aggregate, m.currency)}
                          </b>
                        </div>
                        <div className="progress">
                          <i
                            style={{
                              width:
                                Math.min(100, (m.spent / m.aggregate) * 100) +
                                "%",
                            }}
                          />
                        </div>
                        <dl>
                          <dt>Agent</dt>
                          <dd>
                            {aa.find((a) => a.id === m.agent_id)?.name ||
                              short(m.agent_id)}
                          </dd>
                          <dt>Expires</dt>
                          <dd>{when(m.expires)}</dd>
                          <dt>Signature</dt>
                          <dd className={m.signature_valid ? "good" : "bad"}>
                            {m.signature_valid
                              ? "Verified authority"
                              : "Inactive / invalid authority"}
                          </dd>
                          <dt>Digest</dt>
                          <dd className="mono">{short(m.digest)}</dd>
                        </dl>
                        <div className="card-actions">
                          <Button
                            secondary
                            onClick={() =>
                              act(async () => {
                                const v = await api(
                                  "/mandates/" + m.id + "/verify",
                                  {},
                                );
                                setDetail({
                                  title: "Mandate verification",
                                  ...v,
                                });
                              }, "Verification complete")
                            }
                          >
                            Verify
                          </Button>
                          <Button
                            secondary
                            disabled={m.status !== "ACTIVE"}
                            onClick={() =>
                              act(
                                () => api("/mandates/" + m.id + "/version", {}),
                                "New version signed",
                              )
                            }
                          >
                            New version
                          </Button>
                          <Button
                            secondary
                            disabled={m.status !== "ACTIVE"}
                            onClick={() =>
                              act(
                                () => api("/mandates/" + m.id + "/revoke", {}),
                                "Mandate revoked",
                              )
                            }
                          >
                            Revoke
                          </Button>
                          <Button
                            secondary
                            disabled={m.status !== "ACTIVE"}
                            onClick={() =>
                              act(
                                () => api("/mandates/" + m.id + "/expire", {}),
                                "Mandate expired",
                              )
                            }
                          >
                            Expire
                          </Button>
                        </div>
                      </Panel>
                    ))}
                  </div>
                </>
              )}
              {page === "Transactions" && (
                <Panel
                  title="Transaction registry"
                  sub={`${tx.data?.total ?? 0} matching records · select any row for full evidence`}
                  action={
                    <select
                      value={filter}
                      onChange={(e) => setFilter(e.target.value)}
                      aria-label="Filter outcome"
                    >
                      <option value="">All outcomes</option>
                      {[
                        "ALLOW",
                        "DENY",
                        "ESCALATE",
                        "COMPLETED",
                        "BLOCKED",
                        "AWAITING_APPROVAL",
                        "OUTCOME_UNKNOWN",
                      ].map((v) => (
                        <option key={v}>{v}</option>
                      ))}
                    </select>
                  }
                >
                  <div className="table-search">
                    <Search size={16} />
                    <input
                      placeholder="Search supplier ID, invoice, workflow, agent, date, or transaction…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </div>
                  <Transactions items={tx.data?.items || []} />
                </Panel>
              )}
              {page === "Workflows" && (
                <>
                  <div className="toolbar">
                    {workflowSelect}
                    <Button
                      secondary
                      onClick={() => {
                        setReplay(0);
                        setReplaying(true);
                      }}
                      disabled={!wf || replaying}
                    >
                      <Play size={15} />
                      Replay recorded events
                    </Button>
                  </div>
                  <div className="two-column">
                    <Panel
                      title="Workflow timeline"
                      sub="Read-only replay · original persisted timestamps"
                    >
                      {(workflow.data?.events || [])
                        .slice(0, replaying ? replay : undefined)
                        .map((e: Json) => (
                          <button
                            className="timeline-item"
                            key={e.id}
                            onClick={() => setDetail(e)}
                          >
                            <span className="timeline-dot" />
                            <div>
                              <small>
                                {when(e.timestamp)} ·{" "}
                                {short(e.session || "workflow")}
                              </small>
                              <strong>
                                {e.type
                                  .replaceAll(".", " → ")
                                  .replaceAll("_", " ")}
                              </strong>
                              <span className="mono">{short(e.actor)}</span>
                            </div>
                            <ChevronRight size={15} />
                          </button>
                        ))}
                      {!wf && <Empty />}
                    </Panel>
                    <Panel
                      title="Session continuity"
                      sub="Relationships recorded in the database"
                    >
                      {(workflow.data?.sessions || []).map((s: Json) => (
                        <div className="session-card" key={s.id}>
                          <GitBranch size={20} />
                          <strong>{s.label}</strong>
                          <small className="mono">{s.id}</small>
                          <p>
                            {s.parent_session_id
                              ? "Continues " + short(s.parent_session_id)
                              : "Original intake session"}
                          </p>
                        </div>
                      ))}
                      <Button secondary onClick={() => go("Provenance")}>
                        <Network size={15} />
                        Inspect data lineage
                      </Button>
                    </Panel>
                  </div>
                </>
              )}
              {page === "Provenance" && (
                <>
                  <div className="toolbar">
                    {workflowSelect}
                    <span className="muted tiny">
                      Click a node to inspect its origin · scroll to zoom · drag
                      to pan
                    </span>
                  </div>
                  <Panel
                    title="Field-level lineage"
                    sub="Only recorded source and derivation edges are rendered"
                    action={
                      <span className="badge warn">
                        <i />
                        UNVERIFIED ORIGINS RETAIN TRUST LABEL
                      </span>
                    }
                  >
                    {graph.data ? (
                      <Provenance graph={graph.data} onSelect={setDetail} />
                    ) : (
                      <Empty text="Select a workflow to trace its recorded financial fields." />
                    )}
                  </Panel>
                </>
              )}
              {page === "Approvals" && (
                <>
                  <div className="info-bar">
                    <Lock size={18} />
                    Approval signatures cover the canonical payload digest,
                    nonce, expiration, transaction, and human approver. Hard
                    denials cannot be overridden.
                  </div>
                  <div className="cards">
                    {ap.map((a) => (
                      <Panel
                        key={a.id}
                        title={lookup(a.payload.supplier_id)}
                        sub={short(a.transaction_id)}
                        action={<Badge value={a.status} />}
                      >
                        <div className="mandate-limit">
                          <small>EXACT AMOUNT TO AUTHORIZE</small>
                          <strong>
                            {money(a.payload.amount_minor, a.payload.currency)}
                          </strong>
                        </div>
                        <dl>
                          <dt>Beneficiary</dt>
                          <dd className="mono">{a.payload.beneficiary_ref}</dd>
                          <dt>Invoice</dt>
                          <dd>{a.payload.invoice_ref}</dd>
                          <dt>Expires</dt>
                          <dd>{when(a.expires)}</dd>
                          <dt>Payload digest</dt>
                          <dd className="mono">{short(a.digest)}</dd>
                        </dl>
                        <div className="tags">
                          {a.policy.reason_codes.map((r: string) => (
                            <span key={r}>{r}</span>
                          ))}
                        </div>
                        <div className="card-actions">
                          <Button
                            secondary
                            onClick={() =>
                              setDetail({
                                title: "Exact approval payload",
                                ...a,
                              })
                            }
                          >
                            Review payload
                          </Button>
                          {a.status === "PENDING" && (
                            <Button
                              onClick={() =>
                                act(
                                  () => api("/approvals/" + a.id + "/sign", {}),
                                  "Exact payload signed",
                                )
                              }
                              disabled={busy}
                            >
                              <Check size={15} />
                              Sign approval
                            </Button>
                          )}
                          {a.status === "SIGNED" && (
                            <Button
                              onClick={() =>
                                act(
                                  () =>
                                    api("/executions", {
                                      transaction_id: a.transaction_id,
                                      approval_id: a.id,
                                    }),
                                  "Execution revalidated and recorded",
                                )
                              }
                              disabled={busy}
                            >
                              <Play size={15} />
                              Execute
                            </Button>
                          )}
                          {["SIGNED", "PENDING"].includes(a.status) && (
                            <Button
                              secondary
                              onClick={() =>
                                act(
                                  () =>
                                    api("/approvals/" + a.id + "/revoke", {}),
                                  "Approval revoked",
                                )
                              }
                            >
                              Revoke
                            </Button>
                          )}
                        </div>
                      </Panel>
                    ))}
                  </div>
                  {!ap.length && (
                    <Empty text="No approval requests. Create a workflow above the mandate's approval threshold." />
                  )}
                </>
              )}
              {page === "Security Lab" && (
                <>
                  <div className="info-bar">
                    <FlaskConical size={18} />
                    Isolated synthetic trials · deterministic procurement agent
                    · results measure configured controls, not general AI
                    security.
                  </div>
                  <Panel
                    title="Scenario control"
                    sub="The same synthetic inputs run against each selected environment"
                  >
                    <div className="lab-controls">
                      <label>
                        SCENARIO
                        <select
                          value={scenario}
                          onChange={(e) => setScenario(e.target.value)}
                        >
                          {((scenarios.data || []) as Json[]).map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.attack ? "ATTACK" : "BENIGN"} · {s.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <div className="environment-checks">
                        {["baseline", "basic", "protected"].map((e) => (
                          <label key={e}>
                            <input
                              type="checkbox"
                              checked={environments.includes(e)}
                              onChange={(ev) =>
                                setEnvironments((prev) =>
                                  ev.target.checked
                                    ? [...prev, e]
                                    : prev.filter((x) => x !== e),
                                )
                              }
                            />
                            {e === "protected"
                              ? "MandateTrail"
                              : e === "basic"
                                ? "Basic controls"
                                : "Baseline"}
                          </label>
                        ))}
                      </div>
                      <Button
                        disabled={busy || !environments.length}
                        onClick={() =>
                          act(async () => {
                            const result = await api("/redteam/runs", {
                              scenario,
                              environments,
                            });
                            setLabResult(result);
                          }, "Scenario run recorded")
                        }
                      >
                        {busy ? (
                          <LoaderCircle className="spin" size={15} />
                        ) : (
                          <Play size={15} />
                        )}
                        Run scenario
                      </Button>
                      <Button
                        secondary
                        disabled={busy}
                        onClick={() =>
                          act(async () => {
                            await api("/redteam/reset", {});
                            setLabResult(null);
                          }, "Fresh trial view ready; evidence retained")
                        }
                      >
                        <RefreshCw size={15} />
                        Reset
                      </Button>
                    </div>
                  </Panel>
                  {labResult && (
                    <div className="comparison-grid">
                      {labResult.results.map((r: Json) => (
                        <Panel
                          key={r.environment}
                          title={
                            r.environment === "protected"
                              ? "MandateTrail Protected"
                              : r.environment === "basic"
                                ? "Basic Controls"
                                : "Unprotected Baseline"
                          }
                          sub={
                            r.attack ? "Adversarial trial" : "Benign control"
                          }
                          action={
                            <Badge
                              value={
                                r.attack_success
                                  ? "COMPLETED"
                                  : r.detected
                                    ? "BLOCKED"
                                    : r.completed
                                      ? "COMPLETED"
                                      : "ESCALATE"
                              }
                            />
                          }
                        >
                          <div
                            className={
                              "trial-outcome " +
                              (r.attack_success
                                ? "bad"
                                : r.detected
                                  ? "good"
                                  : "blue")
                            }
                          >
                            {r.attack
                              ? r.attack_success
                                ? "Unauthorized simulation succeeded"
                                : "Attack prevented / held"
                              : r.completed
                                ? "Benign workflow completed"
                                : "Workflow interrupted"}
                          </div>
                          {r.timeline.map((t: Json, i: number) => (
                            <motion.div
                              initial={reduced ? false : { opacity: 0, y: 6 }}
                              animate={{ opacity: 1, y: 0 }}
                              transition={{ delay: reduced ? 0 : i * 0.15 }}
                              className="trial-event"
                              key={i}
                            >
                              <span>{String(i + 1).padStart(2, "0")}</span>
                              <div>
                                <strong>{t.outcome}</strong>
                                {t.reason_codes.map((v: string) => (
                                  <small className="mono" key={v}>
                                    {v}
                                  </small>
                                ))}
                              </div>
                            </motion.div>
                          ))}
                          <p className="tiny muted">
                            Policy latency {r.latency_ms.toFixed(2)} ms ·{" "}
                            {r.executions} simulated submissions
                          </p>
                          <Button
                            secondary
                            onClick={() => act(async () => {
                              const evidence = await api('/redteam/runs/' + labResult.id + '/evidence?environment=' + r.environment);
                              setDetail({title: 'Persisted trial evidence', ...evidence});
                            }, '')}
                          >
                            <FileCheck2 size={14} />
                            Inspect evidence
                          </Button>
                        </Panel>
                      ))}
                    </div>
                  )}
                  <Panel
                    title="Measured trial results"
                    sub="Raw counts and denominators · accumulated in the current trial view"
                  >
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>MEASURE</th>
                            <th>BASELINE</th>
                            <th>BASIC CONTROLS</th>
                            <th>MANDATETRAIL</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            "attack_success_rate",
                            "attack_detection_rate",
                            "false_intervention_rate",
                            "benign_completion_rate",
                            "payload_integrity_rate",
                            "cross_session_detection_rate",
                            "audit_completeness",
                          ].map((key) => (
                            <tr key={key}>
                              <td>{key.replaceAll("_", " ")}</td>
                              {["baseline", "basic", "protected"].map((env) => {
                                const v = metrics.data?.[env]?.[key];
                                return (
                                  <td className="mono" key={env}>
                                    {v?.denominator
                                      ? `${v.percent}% (${v.numerator}/${v.denominator})`
                                      : "— (0 trials)"}
                                  </td>
                                );
                              })}
                            </tr>
                          ))}
                          <tr>
                            <td>Decision latency · median / p95</td>
                            {["baseline", "basic", "protected"].map((env) => (
                              <td key={env}>
                                {metrics.data?.[
                                  env
                                ]?.latency_median_ms?.toFixed(2) ?? "—"}{" "}
                                /{" "}
                                {metrics.data?.[env]?.latency_p95_ms?.toFixed(
                                  2,
                                ) ?? "—"}{" "}
                                ms
                              </td>
                            ))}
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </Panel>
                  <Panel
                    title="Run history"
                    sub="Reopen persisted simulation results"
                  >
                    {((runs.data || []) as Json[]).slice(0, 10).map((r) => (
                      <button
                        key={r.id}
                        className="history-row"
                        onClick={() => setLabResult(r)}
                      >
                        <FlaskConical size={16} />
                        <strong>{r.scenario.replaceAll("_", " ")}</strong>
                        <span className="mono muted">{when(r.created)}</span>
                        <ChevronRight size={16} />
                      </button>
                    ))}
                  </Panel>
                </>
              )}
              {page === "Evidence" && (
                <>
                  <div className="toolbar">
                    {workflowSelect}
                    <div className="actions">
                      <Button
                        secondary
                        disabled={busy}
                        onClick={() =>
                          act(
                            async () =>
                              setVerification(await api("/audit/verify", {})),
                            "Forensic chain verification completed",
                          )
                        }
                      >
                        {busy ? (
                          <LoaderCircle className="spin" size={16} />
                        ) : (
                          <ShieldCheck size={16} />
                        )}
                        Verify audit chain
                      </Button>
                      <Button disabled={!wf} onClick={exportEvidence}>
                        <Download size={16} />
                        Export evidence JSON
                      </Button>
                    </div>
                  </div>
                  {verification && (
                    <div
                      className={
                        "verification " + (verification.valid ? "good" : "bad")
                      }
                    >
                      <ShieldCheck size={26} />
                      <div>
                        <strong>
                          {verification.valid
                            ? "Cryptographic chain verified"
                            : "Integrity failure detected"}
                        </strong>
                        <p>
                          {verification.events_checked} events recomputed ·
                          signed checkpoints verified · head{" "}
                          {short(verification.head_hash)}
                        </p>
                      </div>
                    </div>
                  )}
                  <Panel
                    title="Forensic event ledger"
                    sub="Append-only events · individually signed hash-chain entries"
                  >
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>EVENT / TIMESTAMP</th>
                            <th>ACTOR</th>
                            <th>WORKFLOW</th>
                            <th>EVENT HASH</th>
                            <th />
                          </tr>
                        </thead>
                        <tbody>
                          {(audit.data || []).map((e) => (
                            <tr key={e.id} onClick={() => setDetail(e)}>
                              <td>
                                <strong>{e.type}</strong>
                                <small>{when(e.timestamp)}</small>
                              </td>
                              <td className="mono">{short(e.actor)}</td>
                              <td className="mono">
                                {short(e.workflow || "Organization")}
                              </td>
                              <td className="mono">{short(e.hash)}</td>
                              <td>
                                <ChevronRight size={15} />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </Panel>
                </>
              )}
              {page === "Settings" && (
                <div className="two-column">
                  <Panel
                    title="Workspace & security"
                    sub="Local Orbital Industries sandbox"
                  >
                    <dl>
                      <dt>Environment</dt>
                      <dd>
                        <Badge value="SANDBOX" />
                      </dd>
                      <dt>Policy</dt>
                      <dd>{settings.data?.policy_version}</dd>
                      <dt>Database</dt>
                      <dd>{settings.data?.database}</dd>
                      <dt>Signing key ID</dt>
                      <dd className="mono">{settings.data?.key_id}</dd>
                      <dt>Your role</dt>
                      <dd>{user.role}</dd>
                      <dt>Signed in as</dt>
                      <dd>{user.email}</dd>
                    </dl>
                    <p className="tiny muted">Public verification key</p>
                    <pre className="hash">{settings.data?.public_key}</pre>
                    <Button
                      secondary
                      onClick={() =>
                        act(async () => {
                          await api("/auth/logout", {});
                          setUser(null);
                          setCsrf("");
                          qc.clear();
                        }, "Signed out")
                      }
                    >
                      <LogOut size={15} />
                      Sign out
                    </Button>
                  </Panel>
                  <Panel
                    title="Prototype boundaries"
                    sub="Read before extending this sandbox"
                  >
                    {settings.data?.limitations.map((v: string) => (
                      <p className="limitation" key={v}>
                        <ShieldAlert size={16} />
                        {v}
                      </p>
                    ))}
                    <p className="muted tiny">
                      No production certification, regulatory approval, or live
                      payment integration is claimed.
                    </p>
                  </Panel>
                  <Panel
                    title="Verified supplier registry"
                    sub="Only authorized finance owners can register trusted beneficiaries"
                    action={
                      <Button
                        secondary
                        onClick={() => openForm("Add supplier")}
                      >
                        <Plus size={15} />
                        Add supplier
                      </Button>
                    }
                  >
                    {ss.map((s) => (
                      <div className="supplier-row" key={s.id}>
                        <strong>{s.name}</strong>
                        <span className="mono">{s.beneficiary_ref}</span>
                        <span className="muted">{s.account_mask}</span>
                      </div>
                    ))}
                  </Panel>
                </div>
              )}
            </motion.div>
          </AnimatePresence>
          <footer>
            <span>
              <Orbit size={13} />
              MandateTrail · Orbital Intelligence
            </span>
            <span>Synthetic data only. No real funds are moved.</span>
          </footer>
        </main>
      </div>
      <AnimatePresence>
        {notice && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="toast"
            role="status"
          >
            <Check size={17} />
            {notice}
            <button onClick={() => setNotice("")}>
              <X size={14} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
      {busy && <div className="busy-bar" />}
      <AnimatePresence>
        {modal && (
          <div className="overlay" onClick={() => setModal(null)}>
            <motion.section
              role="dialog"
              aria-modal="true"
              aria-label={modal}
              className="modal"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="panel-head">
                <h2>{modal}</h2>
                <button
                  className="icon-button"
                  onClick={() => setModal(null)}
                  aria-label="Close"
                >
                  <X />
                </button>
              </div>
              <p className="muted">
                All financial values below use integer minor units (100 = ₹1).
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  submit();
                }}
              >
                {["Register agent", "Create mandate", "Add supplier"].includes(
                  modal,
                ) && (
                  <label>
                    Name
                    <input
                      required
                      minLength={2}
                      maxLength={100}
                      value={form.name}
                      onChange={(e) =>
                        setForm({ ...form, name: e.target.value })
                      }
                    />
                  </label>
                )}
                {modal === "Create mandate" && (
                  <>
                    <label>
                      Authorized agent
                      <select
                        value={form.agent_id}
                        onChange={(e) =>
                          setForm({ ...form, agent_id: e.target.value })
                        }
                      >
                        {aa.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.name}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Currency
                      <input
                        required
                        pattern="[A-Z]{3}"
                        value={form.currency}
                        onChange={(e) =>
                          setForm({ ...form, currency: e.target.value })
                        }
                      />
                    </label>
                  </>
                )}
                {["Create mandate", "Procurement workflow"].includes(modal) && (
                  <label>
                    Approved supplier
                    <select
                      value={form.supplier_id}
                      onChange={(e) =>
                        setForm({ ...form, supplier_id: e.target.value })
                      }
                    >
                      {ss.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                {modal === "Create mandate" &&
                  ["per_transaction", "aggregate", "approval_above"].map(
                    (k) => (
                      <label key={k}>
                        {k.replaceAll("_", " ")} · minor units
                        <input
                          required
                          type="number"
                          min={k === "approval_above" ? 0 : 1}
                          step="1"
                          value={form[k]}
                          onChange={(e) =>
                            setForm({ ...form, [k]: e.target.value })
                          }
                        />
                      </label>
                    ),
                  )}
                {modal === "Add supplier" && (
                  <label>
                    Verified synthetic beneficiary reference
                    <input
                      required
                      pattern="BEN-[A-Z0-9-]{3,40}"
                      value={form.beneficiary_ref}
                      onChange={(e) =>
                        setForm({ ...form, beneficiary_ref: e.target.value })
                      }
                    />
                  </label>
                )}
                {modal === "Procurement workflow" && (
                  <>
                    <label>
                      Mandate
                      <select
                        value={form.mandate_id}
                        onChange={(e) =>
                          setForm({ ...form, mandate_id: e.target.value })
                        }
                      >
                        {mm
                          .filter((m) => m.status === "ACTIVE")
                          .map((m) => (
                            <option key={m.id} value={m.id}>
                              {m.name} · v{m.version}
                            </option>
                          ))}
                      </select>
                    </label>
                    <label>
                      Invoice reference
                      <input
                        required
                        value={form.invoice_ref}
                        onChange={(e) =>
                          setForm({ ...form, invoice_ref: e.target.value })
                        }
                      />
                    </label>
                    <label>
                      Amount · minor units
                      <input
                        type="number"
                        required
                        min="1"
                        step="1"
                        value={form.amount_minor}
                        onChange={(e) =>
                          setForm({ ...form, amount_minor: e.target.value })
                        }
                      />
                    </label>
                    <label>Simulator result
                      <select value={form.simulator_outcome} onChange={e => setForm({...form, simulator_outcome:e.target.value})}>
                        {['COMPLETED','FAILED','TIMED_OUT','OUTCOME_UNKNOWN'].map(value => <option key={value}>{value}</option>)}
                      </select>
                    </label>
                    <label className="check-label">
                      <input
                        type="checkbox"
                        checked={form.poison}
                        onChange={(e) =>
                          setForm({ ...form, poison: e.target.checked })
                        }
                      />
                      Introduce a synthetic cross-session beneficiary attack
                    </label>
                  </>
                )}
                {error && <div className="error">{error}</div>}
                <div className="card-actions">
                  <Button secondary onClick={() => setModal(null)}>
                    Cancel
                  </Button>
                  <button className="button" disabled={busy} type="submit">
                    {busy ? (
                      <LoaderCircle className="spin" size={16} />
                    ) : (
                      <Check size={16} />
                    )}{" "}
                    {modal === "Procurement workflow"
                      ? "Run monitored workflow"
                      : "Create & persist"}
                  </button>
                </div>
              </form>
            </motion.section>
          </div>
        )}
      </AnimatePresence>
      <AnimatePresence>
        {detail && (
          <div className="drawer-overlay" onClick={() => setDetail(null)}>
            <motion.section
              role="dialog"
              aria-modal="true"
              aria-label="Record inspector"
              className="drawer"
              initial={reduced ? false : { x: 500 }}
              animate={{ x: 0 }}
              exit={{ x: 500 }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="panel-head">
                <div>
                  <span className="eyebrow">RECORD INSPECTOR</span>
                  <h2>
                    {detail.title ||
                      detail.label ||
                      (detail.payload
                        ? "Transaction detail"
                        : "Evidence & metadata")}
                  </h2>
                </div>
                <button
                  className="icon-button"
                  aria-label="Close inspector"
                  onClick={() => setDetail(null)}
                >
                  <X />
                </button>
              </div>
              {detail.payload && detail.decision && (
                <>
                  <div className="transaction-amount">
                    {money(
                      detail.payload.amount_minor,
                      detail.payload.currency,
                    )}
                    <Badge value={detail.outcome} />
                  </div>
                  <div className="verification-path">
                    {[
                      "Payment requested",
                      "Mandate verification",
                      "Provenance validation",
                      "Policy evaluation",
                      "Execution decision",
                    ].map((step, i) => (
                      <div key={step}>
                        <span>{i + 1}</span>
                        {step}
                      </div>
                    ))}
                  </div>
                  <div className="tabs">
                    {[
                      "Overview",
                      "Policy Checks",
                      "Provenance",
                      "Approval",
                      "Execution",
                      "Evidence",
                    ].map((t) => (
                      <button
                        key={t}
                        className={detailTab === t ? "active" : ""}
                        onClick={() => setDetailTab(t)}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                  {detailTab === "Overview" && (
                    <>
                      <dl>
                        <dt>Supplier</dt>
                        <dd>{lookup(detail.payload.supplier_id)}</dd>
                        <dt>Beneficiary</dt>
                        <dd className="mono">
                          {detail.payload.beneficiary_ref}
                        </dd>
                        <dt>Invoice</dt>
                        <dd>{detail.payload.invoice_ref}</dd>
                        <dt>Agent</dt>
                        <dd className="mono">
                          {short(detail.payload.agent_id)}
                        </dd>
                        <dt>Workflow</dt>
                        <dd className="mono">{short(detail.parent)}</dd>
                        <dt>Digest</dt>
                        <dd className="mono">{short(detail.digest)}</dd>
                      </dl>
                      <p className="muted">
                        {detail.decision.outcome === "DENY"
                          ? "The proposed payment violates a mandatory authorization or provenance rule."
                          : detail.decision.outcome === "ESCALATE"
                            ? "Human review is required before the exact payload can proceed."
                            : "Mandatory controls passed; execution outcome is recorded separately."}
                      </p>
                    </>
                  )}
                  {detailTab === "Policy Checks" && (
                    <>
                      <Badge value={detail.decision.outcome} />
                      {detail.decision.reason_codes.map((r: string) => (
                        <div className="reason" key={r}>
                          <ShieldCheck size={17} />
                          <div>
                            <strong>
                              {r.replaceAll("_", " ").toLowerCase()}
                            </strong>
                            <small className="mono">{r}</small>
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                  {detailTab === "Provenance" && (
                    <>
                      <JsonView data={detail.payload.provenance_refs} />
                      <Button
                        secondary
                        onClick={() => {
                          setWf(detail.payload.workflow_id);
                          go("Provenance");
                        }}
                      >
                        <Network size={15} />
                        Open recorded lineage
                      </Button>
                    </>
                  )}
                  {detailTab === "Approval" && (
                    <JsonView data={detail.approvals || []} />
                  )}{" "}
                  {detailTab === "Execution" && (
                    <JsonView
                      data={detail.receipts || { outcome: detail.outcome }}
                    />
                  )}
                  {detailTab === "Evidence" && (
                    <>
                      <JsonView
                        data={{
                          payload: detail.payload,
                          digest: detail.digest,
                        }}
                      />
                      <Button
                        onClick={() =>
                          window.open(
                            "/api/v1/evidence/" + detail.parent,
                            "_blank",
                            "noopener",
                          )
                        }
                      >
                        <Download size={16} />
                        Export workflow evidence
                      </Button>
                    </>
                  )}
                </>
              )}
              {!(detail.payload && detail.decision) && (
                <JsonView data={detail} />
              )}{" "}
              {detail.alerts &&
                detail.alerts.map((a: Json) => (
                  <div key={a.id} className="reason">
                    <Badge value={a.status} />
                    <strong>{a.title}</strong>
                    {a.status === "OPEN" && (
                      <Button
                        secondary
                        onClick={() =>
                          act(
                            () => api("/alerts/" + a.id + "/resolve", {}),
                            "Alert resolved",
                          )
                        }
                      >
                        Resolve {short(a.id)}
                      </Button>
                    )}
                  </div>
                ))}
            </motion.section>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
export default function Page() {
  return (
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>
  );
}
