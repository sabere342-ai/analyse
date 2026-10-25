import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowDownToLine,
  ArrowUpFromLine,
  BarChart3,
  Box,
  Check,
  ChevronLeft,
  ClipboardList,
  FileSpreadsheet,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  Settings,
  ShieldCheck,
  Store,
  TrendingUp,
  Users,
  X,
} from "lucide-react";
import { analysisFilters, api, labels, message, metric } from "./api";
import type {
  AnalysisFilters,
  Batch,
  ImportComparison,
  Report,
  Rules,
} from "./api";
import "./style.css";
import { ImportInspection } from "./ImportInspection";
import { parseMapping, selectedSheets } from "./import-options";
import type { ParserOptions, SheetMode } from "./import-options";

type Page =
  "overview" | "inventory" | "representatives" | "imports" | "settings";
const navigation: { id: Page; label: string; icon: typeof Box }[] = [
  { id: "overview", label: "نظرة عامة", icon: LayoutDashboard },
  { id: "inventory", label: "المخزون والمنتجات", icon: Box },
  { id: "representatives", label: "أداء المندوبين", icon: Users },
  { id: "imports", label: "استيراد ومراجعة", icon: ArrowUpFromLine },
  { id: "settings", label: "الإعدادات والسجل", icon: Settings },
];
function localDay(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
function App() {
  const [auth, setAuth] = useState<{
    initialized: boolean;
    authenticated: boolean;
    cloud?: boolean;
    max_upload_bytes?: number;
  } | null>(null);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [page, setPage] = useState<Page>("overview"),
    [open, setOpen] = useState(false);
  const [start, setStart] = useState(localDay().slice(0, 8) + "01"),
    [end, setEnd] = useState(localDay()),
    [stockAsOf, setStockAsOf] = useState(localDay()),
    [scope, setScope] = useState("store");
  const [report, setReport] = useState<Report | null>(null),
    [busy, setBusy] = useState(false),
    [batch, setBatch] = useState<Batch | null>(null),
    [batches, setBatches] = useState<Batch[]>([]),
    [applied, setApplied] = useState<AnalysisFilters | null>(null);
  const reportRequest = useRef(0);
  const datasetRequest = useRef(0);
  useEffect(() => {
    const expired = () => {
      reportRequest.current += 1;
      datasetRequest.current += 1;
      setAuth((current) =>
        current ? { ...current, authenticated: false } : current,
      );
      setReport(null);
      setBatch(null);
      setBatches([]);
      setApplied(null);
      setBusy(false);
      setNotice("");
      setError("انتهت الجلسة؛ سجّل الدخول لمتابعة العمل");
    };
    window.addEventListener("madrid:session-expired", expired);
    return () => window.removeEventListener("madrid:session-expired", expired);
  }, []);
  const fail = useCallback(
    (e: unknown) =>
      setError(e instanceof Error ? e.message : "حصل خطأ؛ حاول تاني"),
    [],
  );
  const load = useCallback(
    async (filters: AnalysisFilters) => {
      const request = ++reportRequest.current;
      setBusy(true);
      setReport(null);
      setError("");
      setApplied(filters);
      try {
        const result = await api<Report>(
          `/analytics?${new URLSearchParams(filters)}`,
        );
        if (request === reportRequest.current) setReport(result);
      } catch (e) {
        if (request === reportRequest.current) fail(e);
      } finally {
        if (request === reportRequest.current) setBusy(false);
      }
    },
    [fail],
  );
  const refreshDataset = useCallback(
    async (preferredScope?: string) => {
      const request = ++datasetRequest.current;
      const stored = await api<Batch[]>("/batches");
      if (request !== datasetRequest.current) return;
      setBatches(stored);
      const filters = analysisFilters(stored, preferredScope) ?? {
        start: localDay().slice(0, 8) + "01",
        end: localDay(),
        scope: preferredScope ?? "store",
        stock_asof: localDay(),
      };
      setStart(filters.start);
      setEnd(filters.end);
      setScope(filters.scope);
      setStockAsOf(filters.stock_asof);
      await load(filters);
    },
    [load],
  );
  useEffect(() => {
    void api<{
      initialized: boolean;
      authenticated: boolean;
      cloud?: boolean;
      max_upload_bytes?: number;
    }>("/auth/status")
      .then(setAuth)
      .catch(fail);
  }, [fail]);
  useEffect(() => {
    if (auth?.authenticated) void refreshDataset().catch(fail);
    return () => {
      reportRequest.current += 1;
      datasetRequest.current += 1;
    };
  }, [auth?.authenticated, refreshDataset, fail]);
  useEffect(() => {
    if ("serviceWorker" in navigator && import.meta.env.PROD)
      void navigator.serviceWorker.register("/sw.js");
  }, []);
  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const password = String(new FormData(event.currentTarget).get("password"));
    try {
      if (!auth?.initialized)
        await api("/auth/setup", {
          method: "POST",
          headers: {
            "X-Madrid-Setup":
              new URLSearchParams(window.location.hash.slice(1)).get("setup") ||
              "",
          },
          body: JSON.stringify({ password }),
        });
      if (window.location.hash.startsWith("#setup="))
        window.history.replaceState(
          null,
          "",
          window.location.pathname + window.location.search,
        );
      await api("/auth/login", {
        method: "POST",
        body: JSON.stringify({ password }),
      });
      setAuth({
        initialized: true,
        authenticated: true,
        cloud: auth?.cloud,
        max_upload_bytes: auth?.max_upload_bytes,
      });
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      reportRequest.current += 1;
      datasetRequest.current += 1;
      setError("");
      setNotice("");
      setApplied(null);
      setBusy(false);
      setAuth({
        initialized: true,
        authenticated: false,
        cloud: auth?.cloud,
        max_upload_bytes: auth?.max_upload_bytes,
      });
      setReport(null);
      setBatch(null);
      setBatches([]);
    } catch {
      setError(
        "تعذر تأكيد تسجيل الخروج من الخادم. لو الاتصال انقطع فالجلسة قد تظل نشطة؛ حاول تسجيل الخروج مرة أخرى",
      );
    }
  }
  async function review(id: string) {
    setBusy(true);
    try {
      setBatch(await api<Batch>("/batches/" + id));
      setPage("imports");
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  async function act(action: string) {
    if (!batch) return;
    let reason = "";
    if (action !== "accept") {
      reason = window.prompt("سبب الإجراء (بيتحفظ في سجل المراجعة)") ?? "";
      if (!reason.trim()) return;
    }
    setBusy(true);
    try {
      setBatch(
        await api<Batch>(`/batches/${batch.id}/action`, {
          method: "POST",
          body: JSON.stringify({ action, reason }),
        }),
      );
      await refreshDataset(batch.scope);
      setNotice(
        action === "accept"
          ? "تم اعتماد الملف وتحديث البيانات والتحليل للفترة المناسبة؛ افتح نظرة عامة لعرض النتائج والنصائح"
          : "تم تحديث حالة الملف وإعادة التحليل من البيانات المقبولة المتبقية",
      );
    } catch (e) {
      fail(e);
    } finally {
      setBusy(false);
    }
  }
  if (!auth)
    return (
      <main className="auth">
        <Store size={40} />
        <p role="status">بنجهّز مساحة العمل…</p>
        {error && <p role="alert">{error}</p>}
      </main>
    );
  if (!auth.authenticated)
    return (
      <main className="auth">
        <div className="auth-card">
          <div className="brand-mark">
            <Store />
          </div>
          <span className="eyebrow">MADRID RETAIL INTELLIGENCE</span>
          <h1>
            قرارات أوضح.
            <br />
            تجارة أذكى.
          </h1>
          <p>افهم حركة محلك من تقاريرك، بأرقام تقدر تراجع مصدرها.</p>
          <form onSubmit={signIn}>
            <label htmlFor="password">
              {auth.initialized ? "كلمة المرور" : "عيّن كلمة مرور المالك"}
            </label>
            <input
              id="password"
              name="password"
              type="password"
              minLength={12}
              maxLength={256}
              autoComplete={
                auth.initialized ? "current-password" : "new-password"
              }
              required
              placeholder="12 حرف على الأقل"
            />
            <button className="primary wide" disabled={busy}>
              {auth.initialized
                ? "دخول مساحة العمل"
                : auth.cloud
                  ? "إنشاء حساب المالك"
                  : "إنشاء الحساب المحلي"}
            </button>
          </form>
          {error && (
            <p className="alert" role="alert">
              {error}
            </p>
          )}
          <small>
            <ShieldCheck size={14} />{" "}
            {auth.cloud
              ? "بياناتك محفوظة في قاعدة خاصة على الاستضافة."
              : "بياناتك محفوظة محليًا."}{" "}
            مفيش خدمات AI خارجية.
          </small>
        </div>
      </main>
    );
  const title = navigation.find((n) => n.id === page)?.label;
  return (
    <div className="shell">
      <aside className={open ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <div className="brand-mark">
            <Store />
          </div>
          <div>
            <strong>
              مدريد<span>ذكاء التجزئة</span>
            </strong>
          </div>
          <button
            className="icon-button mobile-close"
            aria-label="إغلاق القائمة"
            onClick={() => setOpen(false)}
          >
            <X />
          </button>
        </div>
        <div className="store-card">
          <span className="status-dot" />
          <div>
            مساحة المحل<small>تحليلات مستقلة عن الـPOS</small>
          </div>
        </div>
        <nav aria-label="التنقل الرئيسي">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              aria-current={page === id ? "page" : undefined}
              className={page === id ? "nav-item active" : "nav-item"}
              onClick={() => {
                setPage(id);
                setOpen(false);
              }}
            >
              <Icon size={19} />
              {label}
              {id === "imports" && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <ShieldCheck size={20} />
          <strong>كل رقم له مصدر</strong>
          <p>البيانات المقبولة بس هي اللي بتدخل التحليلات.</p>
        </div>
        <button className="nav-item logout" onClick={() => void logout()}>
          <LogOut size={18} />
          تسجيل الخروج
        </button>
      </aside>
      {open && (
        <button
          className="scrim"
          aria-label="إغلاق القائمة"
          onClick={() => setOpen(false)}
        />
      )}
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="فتح القائمة"
              onClick={() => setOpen(true)}
            >
              <Menu />
            </button>
            <span>مساحة العمل</span>
            <ChevronLeft size={14} />
            <strong>{title}</strong>
          </div>
          <div className="owner">
            <span className="avatar">م</span>
            <div>
              مدير المحل<small>حساب المالك</small>
            </div>
          </div>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <span className="eyebrow">من البيانات للقرار</span>
              <h1>{page === "overview" ? "الصورة الكاملة لمحلك" : title}</h1>
              <p>
                {page === "overview"
                  ? "تابع البيع والمخزون، واعرف فين الخطوة الجاية."
                  : "أرقام واضحة، وتفاصيل تقدر ترجع لمصدرها."}
              </p>
            </div>
            <button
              className="primary"
              onClick={() => {
                setPage("imports");
                setBatch(null);
              }}
            >
              <ArrowUpFromLine size={17} /> استيراد تقرير
            </button>
          </div>
          {error && (
            <div className="alert" role="alert">
              {error}
              <button aria-label="إغلاق الخطأ" onClick={() => setError("")}>
                <X size={16} />
              </button>
            </div>
          )}
          {notice && (
            <div className="success" role="status">
              {notice}
              <button aria-label="إغلاق الرسالة" onClick={() => setNotice("")}>
                <X size={16} />
              </button>
            </div>
          )}
          <form
            className="filters"
            onSubmit={(e) => {
              e.preventDefault();
              void load({ start, end, scope, stock_asof: stockAsOf });
            }}
          >
            <div className="filter-title">
              <BarChart3 size={18} /> فترة التحليل
            </div>
            <label>
              من
              <input
                aria-label="بداية فترة التحليل"
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
                required
              />
            </label>
            <label>
              إلى
              <input
                aria-label="نهاية فترة التحليل"
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
                required
                min={start}
              />
            </label>
            <label>
              الجرد حتى
              <input
                aria-label="تاريخ رصيد المخزون"
                type="date"
                value={stockAsOf}
                onChange={(e) => setStockAsOf(e.target.value)}
                required
              />
            </label>
            <label>
              نطاق التقرير
              <input
                aria-label="نطاق التحليل"
                value={scope}
                onChange={(e) => setScope(e.target.value)}
                required
              />
            </label>
            <button className="secondary" disabled={busy}>
              تحديث النتائج
            </button>
            {report && (
              <span
                className={
                  "data-badge " +
                  (report.sales_complete &&
                  report.source_comparison?.status !== "mismatch" &&
                  report.sales_coverage !== "assigned_only"
                    ? "good"
                    : "")
                }
              >
                {report.sales_coverage === "assigned_only"
                  ? report.demand_source === "movement"
                    ? "الوحدات من الحركة؛ القيم للمندوبين فقط"
                    : "قيم المندوبين فقط؛ إجمالي الوحدات غير متاح"
                  : report.source_comparison?.status === "mismatch"
                    ? "مصادر البيع غير متطابقة"
                    : report.sales_complete
                      ? "مبيعات الفترة مكتملة"
                      : "تغطية البيانات غير مكتملة"}
              </span>
            )}
          </form>
          <div className="hint" role="status">
            {batches.filter((b) => b.status === "accepted").length} ملف معتمد في
            البيانات
            {" · "}
            {batches.filter((b) => b.status === "staged").length} ملف تحت
            المراجعة
            {batches.some((b) => b.status === "staged") && (
              <button
                className="text-button"
                onClick={() => setPage("imports")}
              >
                راجع الملفات المعلقة لاعتمادها وإدخالها في التحليل
              </button>
            )}
          </div>
          {report && applied && (
            <p className="hint">
              النتائج المعروضة: {applied.start} إلى {applied.end}
              {" · "}الجرد حتى {applied.stock_asof}. لتطبيق تغيير الفلاتر اضغط
              تحديث النتائج.
            </p>
          )}
          {busy && (
            <div className="loading" role="status">
              جاري التحميل والمراجعة…
            </div>
          )}
          {page === "overview" && report && (
            <Overview
              report={report}
              onReview={review}
              onImport={() => setPage("imports")}
            />
          )}
          {page === "inventory" && report && (
            <Inventory report={report} onReview={review} />
          )}
          {page === "representatives" && report && (
            <Representatives report={report} />
          )}
          {page === "imports" && (
            <Imports
              batch={batch}
              setBatch={(value) => {
                setBatch(value);
                void api<Batch[]>("/batches").then(setBatches).catch(fail);
              }}
              review={review}
              act={act}
              busy={busy}
              fail={fail}
              defaults={{ start, end, scope }}
              maxUploadBytes={auth.max_upload_bytes ?? 20 * 1024 * 1024}
              analyze={() => setPage("overview")}
            />
          )}
          {page === "settings" && (
            <SettingsPage fail={fail} notify={setNotice} />
          )}
          {(page === "overview" ||
            page === "inventory" ||
            page === "representatives") &&
            report && (
              <div className="export-bar">
                <span>
                  <ArrowDownToLine size={17} /> تصدير نفس الفترة والنطاق
                </span>
                {["xlsx", "csv", "pdf"].map((kind) => (
                  <a
                    className="secondary"
                    key={kind}
                    href={`/api/exports/${kind}?${new URLSearchParams(applied ?? { start, end, scope, stock_asof: stockAsOf })}`}
                    download
                  >
                    {kind.toUpperCase()}
                  </a>
                ))}
              </div>
            )}
          <footer>
            مدريد · ذكاء التجزئة{" "}
            <span>مؤشرات قابلة للمراجعة، من غير افتراضات مخفية.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}

function Overview({
  report: r,
  onReview,
  onImport,
}: {
  report: Report;
  onReview: (id: string) => void;
  onImport: () => void;
}) {
  const cards = [
    {
      key:
        r.sales_coverage === "assigned_only" ||
        r.source_comparison?.status === "mismatch"
          ? "reported_net_sales"
          : "net_sales",
      icon: TrendingUp,
      sub:
        r.sales_coverage === "assigned_only"
          ? "لا تشمل القيمة المالية للمبيعات بدون مندوب"
          : "بعد الخصم والمرتجعات",
      tone: "green",
    },
    {
      key: "gross_profit",
      icon: BarChart3,
      sub: "متاح مع تكلفة بيع موثوقة",
      tone: "orange",
    },
    {
      key: "stock",
      icon: Box,
      sub: r.snapshot_date ? `آخر جرد: ${r.snapshot_date}` : "محتاج تقرير جرد",
      tone: "blue",
    },
    {
      key: "operating_profit",
      icon: FileSpreadsheet,
      sub: "بعد المصروفات المتحققة",
      tone: "purple",
    },
  ];
  return (
    <>
      {r.warnings.map((w) => (
        <div className="hint" key={w}>
          {w}
        </div>
      ))}
      {r.source_comparison &&
        ["mismatch", "explained_unassigned"].includes(
          r.source_comparison.status,
        ) && (
          <section className="panel" aria-label="مقارنة مصادر البيع">
            <div className="section-title">
              <div>
                <h2>
                  {r.source_comparison?.status === "explained_unassigned"
                    ? "مبيعات بدون مندوب تفسر فرق نطاق التقريرين"
                    : "فرق محتاج تفسير بين تقارير البيع"}
                </h2>
                <p>
                  {r.source_comparison.status === "explained_unassigned"
                    ? "حركة المخزون هي الإجمالي؛ فرق الوحدات يوضح البيع والمرتجع بدون مندوب حسب تأكيدك. لا يتم جمع الإجمالي مع مكوناته."
                    : "المصدران مختلفان؛ إجمالي المحل والطلب غير معتمدين لحين تفسير الفرق."}
                </p>
              </div>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>المصدر</th>
                    <th>الوحدات المباعة</th>
                    <th>الوحدات المرتجعة</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>تقرير المندوبين</td>
                    <td>{r.source_comparison.reported_sold}</td>
                    <td>{r.source_comparison.reported_returned}</td>
                  </tr>
                  {r.source_comparison?.status === "explained_unassigned" && (
                    <tr>
                      <td>بدون مندوب — فرق وحدات مؤكد النطاق</td>
                      <td>{r.source_comparison.unassigned_sold}</td>
                      <td>{r.source_comparison.unassigned_returned}</td>
                    </tr>
                  )}
                  <tr>
                    <td>حركة المخزون: بيع ومرتجع بيع فقط</td>
                    <td>{r.source_comparison.movement_sold}</td>
                    <td>{r.source_comparison.movement_returned}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <details>
              <summary>فروق المنتجات ودليل المصدر</summary>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>الباركود</th>
                      <th>مباع: المندوبين / الحركة</th>
                      <th>مرتجع: المندوبين / الحركة</th>
                      <th>الدليل</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.source_comparison.differences.map((d) => (
                      <tr key={d.barcode}>
                        <td>
                          <bdi>{d.barcode}</bdi>
                        </td>
                        <td>
                          <bdi>
                            {d.reported_sold} / {d.movement_sold}
                          </bdi>
                        </td>
                        <td>
                          <bdi>
                            {d.reported_returned} / {d.movement_returned}
                          </bdi>
                        </td>
                        <td>
                          {d.evidence[0] && (
                            <button
                              className="text-button"
                              onClick={() => onReview(d.evidence[0].batch_id)}
                            >
                              راجع المصدر
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </section>
        )}
      <div className="metric-grid">
        {cards.map(({ key, icon: Icon, sub, tone }) => (
          <article className="metric-card" key={key}>
            <div className="metric-top">
              <span>{labels[key]}</span>
              <span className={"metric-icon " + tone}>
                <Icon size={19} />
              </span>
            </div>
            <strong
              className={r.metrics[key]?.value == null ? "unavailable" : ""}
            >
              {metric(r.metrics[key])}
              {r.metrics[key]?.value != null && (
                <small>{key === "stock" ? "قطعة" : r.currency}</small>
              )}
            </strong>
            <p>{sub}</p>
          </article>
        ))}
      </div>
      {!r.sources.length ? (
        <div className="empty panel">
          <FileSpreadsheet size={40} />
          <h2>أول قرار بيبدأ بتقرير</h2>
          <p>
            ارفع تقرير POS، راجع الصفوف والإجماليات، وبعد قبوله هتظهر المؤشرات
            هنا.
          </p>
          <button className="primary" onClick={onImport}>
            ابدأ استيراد تقرير
          </button>
          <small>
            مفيش بيانات محل محمّلة تلقائيًا، والأرقام غير المتاحة مش صفر.
          </small>
        </div>
      ) : (
        <div className="overview-grid">
          <section className="panel">
            <div className="section-title">
              <div>
                <h2>المنتجات الأكثر بيعًا</h2>
                <p>حسب صافي الوحدات في مصدر المبيعات للفترة المحددة</p>
              </div>
              <span className="pill">{r.products.length} منتج</span>
            </div>
            {r.products.slice(0, 5).map((p, i) => (
              <div className="rank-row" key={p.barcode}>
                <span className="rank">{String(i + 1).padStart(2, "0")}</span>
                <div>
                  <strong>{p.name}</strong>
                  <small>
                    <bdi>{p.barcode}</bdi> · {p.category}
                  </small>
                </div>
                <div className="rank-value">
                  <bdi>{p.net_units ?? "غير متاح"}</bdi>
                  <small>صافي قطعة</small>
                </div>
              </div>
            ))}
          </section>
          <section className="panel recommendations">
            <div className="section-title">
              <div>
                <h2>خطوتك الجاية</h2>
                <p>اقتراحات بقواعد واضحة، مش أوامر تلقائية</p>
              </div>
              <span className="metric-icon orange">
                <TrendingUp size={19} />
              </span>
            </div>
            {r.recommendations.length ? (
              r.recommendations.slice(0, 5).map((rec, i) => (
                <article className="recommendation" key={i}>
                  <strong>{rec.action}</strong>
                  <p>
                    {rec.subject}: {rec.observation}
                  </p>
                  <small>{rec.impact}</small>
                  {rec.evidence[0] && (
                    <button
                      className="text-button"
                      onClick={() => onReview(rec.evidence[0].batch_id)}
                    >
                      راجع الدليل <ChevronLeft size={14} />
                    </button>
                  )}
                </article>
              ))
            ) : (
              <div className="quiet">
                <ShieldCheck size={28} />
                <p>مفيش توصيات مدعومة بالشروط الحالية.</p>
                <small>
                  ده مش دليل إن كل المنتجات سليمة؛ راجع تغطية البيانات والتاريخ.
                </small>
              </div>
            )}
          </section>
        </div>
      )}
      <section className="panel">
        <div className="section-title">
          <div>
            <h2>المؤشرات المالية</h2>
            <p>التكلفة والمصروفات المفقودة لا تُعتبر صفرًا</p>
          </div>
          <span className="pill">{r.currency}</span>
        </div>
        <div className="financial-grid">
          {Object.entries(r.metrics)
            .filter(([key]) => !["sold", "returned", "stock"].includes(key))
            .map(([key, m]) => (
              <div className="financial-item" key={key}>
                <span>{labels[key]}</span>
                <strong>
                  <bdi>{metric(m)}</bdi>
                </strong>
              </div>
            ))}
        </div>
        <p className="muted">
          تغير صافي المبيعات عن الفترة السابقة المساوية:{" "}
          <bdi>{metric(r.trend.net_sales_change)}</bdi>{" "}
          {r.trend.net_sales_change.value !== null ? "٪" : ""}
        </p>
      </section>
      {!!r.categories.length && (
        <section className="panel">
          <div className="section-title">
            <h2>حركة التصنيفات</h2>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>التصنيف</th>
                  <th>الرصيد</th>
                  <th>صافي الوحدات</th>
                  <th>صافي المبيعات</th>
                  <th>المساهمة ٪</th>
                  <th>وارد</th>
                  <th>صادر</th>
                </tr>
              </thead>
              <tbody>
                {r.categories.map((c) => (
                  <tr key={c.category}>
                    <td>{c.category}</td>
                    <td>{c.stock ?? "غير متاح"}</td>
                    <td>{c.net_units ?? "غير متاح"}</td>
                    <td>{metric(c.net_sales)}</td>
                    <td>{metric(c.contribution)}</td>
                    <td>{c.incoming ?? "غير متاح"}</td>
                    <td>{c.outgoing ?? "غير متاح"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}

function Inventory({
  report: r,
  onReview,
}: {
  report: Report;
  onReview: (id: string) => void;
}) {
  const [search, setSearch] = useState(""),
    [classification, setClassification] = useState("");
  const products = r.products.filter(
    (p) =>
      (p.name + " " + p.barcode + " " + p.category).includes(search) &&
      (!classification || p.classification === classification),
  );
  return (
    <section className="panel">
      <div className="section-title">
        <div>
          <h2>كل منتج، والصورة وراه</h2>
          <p>
            الرصيد حسب آخر جرد مناسب، والتغطية تحتاج مبيعات مكتملة ورصيدًا
            متزامنًا.
          </p>
        </div>
      </div>
      <div className="table-tools">
        <label className="search">
          <Search size={17} />
          <input
            aria-label="ابحث عن منتج"
            placeholder="اسم المنتج، الباركود أو التصنيف"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        <select
          aria-label="تصنيف الحركة"
          value={classification}
          onChange={(e) => setClassification(e.target.value)}
        >
          <option value="">كل الحالات</option>
          {[
            "zero_sales",
            "slow",
            "potentially_dead",
            "insufficient_history",
          ].map((k) => (
            <option key={k} value={k}>
              {labels[k]}
            </option>
          ))}
        </select>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>المنتج</th>
              <th>الرصيد / المتاح</th>
              <th>المباع / المرتجع</th>
              <th>صافي الوحدات</th>
              <th>قطعة / يوم</th>
              <th>تغطية يوم</th>
              <th>Sell-through ٪</th>
              <th>حالة الحركة</th>
              <th>المصدر</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p) => (
              <tr key={p.barcode}>
                <td>
                  <strong>{p.name}</strong>
                  <small>
                    <bdi>{p.barcode}</bdi> · {p.category}
                  </small>
                </td>
                <td>
                  <bdi>
                    {p.stock ?? "—"} / {p.available ?? "—"}
                  </bdi>
                </td>
                <td>
                  <bdi>
                    {p.sold ?? "—"} / {p.returned ?? "—"}
                  </bdi>
                </td>
                <td>{p.net_units ?? "غير متاح"}</td>
                <td>{metric(p.velocity)}</td>
                <td>{metric(p.coverage)}</td>
                <td>{metric(p.sell_through)}</td>
                <td>
                  <span className="pill">{labels[p.classification]}</span>
                </td>
                <td>
                  {p.evidence[0] && (
                    <button
                      className="text-button"
                      onClick={() => onReview(p.evidence[0].batch_id)}
                    >
                      راجع
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!products.length && (
          <div className="quiet">
            مفيش منتجات مطابقة أو بيانات مقبولة للفترة دي.
          </div>
        )}
      </div>
    </section>
  );
}

function Representatives({ report: r }: { report: Report }) {
  return (
    <section className="panel">
      <div className="section-title">
        <div>
          <h2>أداء المندوبين</h2>
          <p>
            الترتيب حسب صافي المبيعات، ومش مقياس للكفاءة بدون ساعات عمل وفرص بيع
            متقاربة.
          </p>
        </div>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>الترتيب</th>
              <th>المندوب</th>
              <th>صافي المبيعات</th>
              <th>المباع</th>
              <th>المرتجع</th>
              <th>مرتجعات ٪</th>
              <th>خصم ٪</th>
              <th>صافي الخصم بعد المرتجعات</th>
              <th>تحقيق الهدف ٪</th>
              <th>المساهمة في الربح</th>
            </tr>
          </thead>
          <tbody>
            {r.representatives.map((p) => (
              <tr key={p.rep}>
                <td>{p.rank ?? "—"}</td>
                <td>
                  <strong>{p.rep}</strong>
                </td>
                <td>{metric(p.net_sales)}</td>
                <td>{metric(p.sold)}</td>
                <td>{metric(p.returned)}</td>
                <td>{metric(p.return_rate)}</td>
                <td>{metric(p.discount_rate)}</td>
                <td>{metric(p.net_discount)}</td>
                <td>{metric(p.target_achievement)}</td>
                <td>{metric(p.profit_contribution)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!r.representatives.length && (
          <div className="quiet">
            ارفع تقرير مبيعات فيه عمود المندوب، وراجعه واقبله لعرض الأداء.
          </div>
        )}
      </div>
    </section>
  );
}

export function Imports({
  batch,
  setBatch,
  review,
  act,
  busy,
  fail,
  defaults,
  maxUploadBytes,
  analyze = () => {},
}: {
  batch: Batch | null;
  setBatch: (b: Batch | null) => void;
  review: (id: string) => void;
  act: (action: string) => void;
  busy: boolean;
  fail: (e: unknown) => void;
  defaults: { start: string; end: string; scope: string };
  maxUploadBytes: number;
  analyze?: () => void;
}) {
  const [list, setList] = useState<Batch[]>([]),
    [type, setType] = useState("snapshot"),
    [uploading, setUploading] = useState(false),
    [rowPage, setRowPage] = useState(0),
    [comparison, setComparison] = useState<ImportComparison | null>(null),
    [uploadError, setUploadError] = useState(""),
    [importStart, setImportStart] = useState(defaults.end),
    [importEnd, setImportEnd] = useState(defaults.end);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [mappingText, setMappingText] = useState("{}");
  const [sheets, setSheets] = useState("");
  const [sheetMode, setSheetMode] = useState<SheetMode>("all");
  const [parserOptions, setParserOptions] = useState<ParserOptions>({
    encoding: "utf-8-sig",
    delimiter: "auto",
    pdf_profile: "auto",
  });
  const [inspectionReady, setInspectionReady] = useState(false);
  const [sourceDates, setSourceDates] = useState(true);
  let mappingIssue = "";
  try {
    parseMapping(mappingText);
  } catch (e) {
    mappingIssue = e instanceof Error ? e.message : "تعيين الأعمدة غير صالح";
  }
  const clearMapping = () => {
    setMapping({});
    setMappingText("{}");
  };
  function changeParser(field: keyof ParserOptions, value: string) {
    setParserOptions((current) => ({ ...current, [field]: value }));
    clearMapping();
    setInspectionReady(false);
  }
  useEffect(() => {
    void api<Batch[]>("/batches").then(setList).catch(fail);
  }, [batch, fail]);
  useEffect(() => setRowPage(0), [batch?.id]);
  useEffect(() => {
    setComparison(null);
    if (!batch) return;
    let current = true;
    void api<ImportComparison>(`/batches/${batch.id}/comparison`)
      .then((result) => {
        if (current) setComparison(result);
      })
      .catch((error) => {
        if (current) fail(error);
      });
    return () => {
      current = false;
    };
  }, [batch, fail]);
  async function upload(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setUploading(true);
    setUploadError("");
    try {
      const f = new FormData(event.currentTarget);
      const column_map = parseMapping(String(f.get("mapping") || "{}"));
      const selected = selectedSheets(sheets, sheetMode);
      if (!inspectionReady)
        throw new Error(
          "أعد فحص الملف بالخيارات والأوراق الحالية قبل تجهيز المراجعة",
        );
      const expected: Record<string, string> = {};
      const total = String(f.get("expected") || "");
      const primary = {
        snapshot: "quantity",
        sales: "net_quantity",
        movement: "net_quantity",
        costs: "cost",
        expenses: "amount",
        targets: "target",
      }[type]!;
      if (total) expected[primary] = total;
      if (f.get("net_total")) expected.net = String(f.get("net_total"));
      const spec = {
        report_type: type,
        start: f.get("start"),
        end: f.get("end"),
        scope: f.get("scope"),
        currency: f.get("currency"),
        expected,
        column_map,
        complete: f.has("complete"),
        financial_verified: f.has("financial_verified"),
        reservation_verified: f.has("reservation_verified"),
        availability_verified: f.has("availability_verified"),
        ...parserOptions,
        sheet_mode: sheetMode,
        sheets: selected,
        source_dates: f.has("source_dates") ? "report" : "manual",
        sales_coverage: f.get("sales_coverage") || "store",
        note: f.get("note"),
      };
      const body = new FormData();
      body.set("file", f.get("file") as File);
      body.set("spec", JSON.stringify(spec));
      const imported = await api<Batch>("/imports", { method: "POST", body });
      setBatch(imported);
      if (imported.start && imported.end) {
        setImportStart(imported.start);
        setImportEnd(imported.end);
      }
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "تعذر قراءة الملف");
      fail(e);
    } finally {
      setUploading(false);
    }
  }
  return (
    <>
      <section className="panel">
        <div className="section-title">
          <div>
            <h2>استيراد تقرير جديد</h2>
            <p>
              رفع الملف بيجهّز دفعة مراجعة؛ القبول خطوة منفصلة بعد مطابقة
              المصدر.
            </p>
          </div>
          <FileSpreadsheet size={26} />
        </div>
        <form onSubmit={upload} className="import-form">
          <div className="form-grid">
            <label>
              نوع التقرير
              <select
                name="type"
                value={type}
                onChange={(e) => {
                  const next = e.target.value;
                  setType(next);
                  clearMapping();
                  setInspectionReady(false);
                  setImportStart(
                    next === "snapshot" || next === "costs"
                      ? defaults.end
                      : defaults.start,
                  );
                  setImportEnd(defaults.end);
                }}
              >
                {[
                  "snapshot",
                  "sales",
                  "movement",
                  "costs",
                  "expenses",
                  "targets",
                ].map((k) => (
                  <option value={k} key={k}>
                    {labels[k]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              من / تاريخ الجرد
              <input
                type="date"
                name="start"
                value={importStart}
                onChange={(e) => {
                  setImportStart(e.target.value);
                  if (type === "snapshot" || type === "costs")
                    setImportEnd(e.target.value);
                }}
                required
              />
            </label>
            <label>
              إلى / نفس تاريخ الجرد
              <input
                type="date"
                name="end"
                value={importEnd}
                onChange={(e) => {
                  setImportEnd(e.target.value);
                  if (type === "snapshot" || type === "costs")
                    setImportStart(e.target.value);
                }}
                required
              />
            </label>
            <label>
              نطاق التغطية
              <input
                name="scope"
                defaultValue={defaults.scope}
                maxLength={100}
                required
              />
            </label>
            <label>
              العملة
              <select name="currency" defaultValue="EGP">
                {["EGP", "USD", "EUR", "SAR", "AED", "GBP"].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
            <label>
              إجمالي المصدر المستقل
              <input
                name="expected"
                inputMode="decimal"
                placeholder={
                  type === "sales"
                    ? "صافي الوحدات"
                    : type === "snapshot"
                      ? "إجمالي الكمية"
                      : "الإجمالي الموافق للقالب"
                }
              />
            </label>
            {type === "sales" && (
              <label>
                صافي القيمة من المصدر
                <input
                  name="net_total"
                  inputMode="decimal"
                  placeholder="مطلوب لو فيه أعمدة مالية"
                />
              </label>
            )}
          </div>
          {type === "sales" && (
            <label>
              نطاق تقرير المبيعات
              <select name="sales_coverage" defaultValue="store">
                <option value="store">يشمل كل مبيعات المحل</option>
                <option value="assigned_only">
                  المبيعات المنسوبة للمندوبين فقط
                </option>
              </select>
              <small>
                لو فيه مبيعات بدون مندوب مش ظاهرة هنا، اختار المندوبين فقط ودوّن
                السبب في ملاحظة المصدر؛ الوحدات الكلية تحتاج تقرير حركة مكتملًا.
              </small>
            </label>
          )}
          <ImportInspection
            maxBytes={maxUploadBytes}
            type={type}
            mapping={mapping}
            onMapping={(next) => {
              setMapping(next);
              setMappingText(JSON.stringify(next));
            }}
            sheets={sheets}
            onSheets={setSheets}
            sheetMode={sheetMode}
            onSheetMode={setSheetMode}
            options={parserOptions}
            onReady={setInspectionReady}
            onSourceChange={() => {
              clearMapping();
              setInspectionReady(false);
            }}
            onDetected={(kind, period) => {
              if (kind !== type) clearMapping();
              setType(kind);
              if (period && sourceDates) {
                setImportStart(period.start);
                setImportEnd(period.end);
              }
            }}
          />
          <p className="hint">
            الجرد والتكاليف: تاريخ البداية والنهاية لازم يكونوا نفس اليوم. تنسيق
            تقارير الجرد والمندوبين والحركة المعاير بيتعرف تلقائيًا؛ راجع الصفوف
            ومطابقة الإجماليات قبل القبول.
          </p>
          <label>
            <input
              type="checkbox"
              name="source_dates"
              checked={sourceDates}
              onChange={(event) => setSourceDates(event.target.checked)}
            />
            قراءة تاريخ أو فترة التقرير تلقائيًا من PDF المعروف
            <small>
              التنسيقات المعروفة تستخدم التاريخ المطبوع وتعرضه للمراجعة. Excel
              وCSV والتنسيقات العامة تستخدم التواريخ المدخلة أعلاه.
            </small>
          </label>
          <details>
            <summary>خيارات الأعمدة والترميز</summary>
            <label>
              أسماء أوراق Excel المختارة يدويًا
              <textarea
                name="sheets"
                value={sheets}
                disabled={sheetMode === "all"}
                onChange={(event) => {
                  setSheets(event.target.value);
                  setInspectionReady(false);
                }}
                dir="auto"
                placeholder="في وضع الأوراق المختارة: اسم ورقة واحد في كل سطر"
              />
              <small>
                اكتب الاسم كما يظهر في Excel لاختيار أوراق البيانات فقط. كل ورقة
                تحتاج عناوين أعمدتها؛ مطابقة الإجماليات تتم لكل ورقة قبل
                التجميع.
              </small>
            </label>
            <div className="form-grid">
              <label>
                تنسيق PDF
                <select
                  name="pdf_profile"
                  value={parserOptions.pdf_profile}
                  onChange={(event) =>
                    changeParser("pdf_profile", event.target.value)
                  }
                >
                  <option value="auto">اكتشاف تلقائي</option>
                  <option value="arabic_pos_v1">
                    تقارير POS العربية المعايرة
                  </option>
                  <option value="generic">جدول عام بتعيين الأعمدة</option>
                </select>
              </label>
              <label>
                ترميز CSV
                <select
                  name="encoding"
                  value={parserOptions.encoding}
                  onChange={(event) =>
                    changeParser("encoding", event.target.value)
                  }
                >
                  <option value="utf-8-sig">UTF-8</option>
                  <option value="cp1256">Windows Arabic</option>
                </select>
              </label>
              <label>
                الفاصل
                <select
                  name="delimiter"
                  value={parserOptions.delimiter}
                  onChange={(event) =>
                    changeParser("delimiter", event.target.value)
                  }
                >
                  <option value="auto">اكتشاف تلقائي</option>
                  <option value=",">Comma</option>
                  <option value=";">Semicolon</option>
                  <option value={"\t"}>Tab</option>
                </select>
              </label>
            </div>
            <label>
              تعيين الأعمدة (canonical → source header)
              <textarea
                name="mapping"
                dir="ltr"
                placeholder={'{"barcode":"كود الصنف","quantity":"الرصيد"}'}
                value={mappingText}
                onChange={(event) => {
                  setMappingText(event.target.value);
                  try {
                    setMapping(parseMapping(event.target.value));
                  } catch {
                    setMapping({});
                  }
                }}
              />
              {mappingIssue && (
                <small role="alert">
                  {mappingIssue}؛ صحح النص قبل الاستيراد.
                </small>
              )}
            </label>
            <small>
              معاني الأعمدة والأشكال المدعومة موضحة في القوالب. لا يتم استنتاج
              معنى Discount تلقائيًا.
            </small>
          </details>
          <label>
            ملاحظة المصدر والمعاني المتحققة
            <textarea
              name="note"
              maxLength={1000}
              placeholder="مثال: إجمالي الكمية مطابق لتذييل التقرير؛ العملة بدون ضريبة"
            />
          </label>
          <div className="confirmations">
            <label>
              <input type="checkbox" name="complete" /> أؤكد إن نطاق وفترة
              التقرير مكتملين، وإن الإجمالي المدخل من المصدر
            </label>
            <label>
              <input type="checkbox" name="financial_verified" /> تحققت من معاني
              المال والخصومات والمرتجعات والعملة والتكلفة إن وجدت
            </label>
            <label>
              <input type="checkbox" name="reservation_verified" /> تحققت إن
              المتاح = الرصيد − المحجوز
            </label>
            <label>
              <input type="checkbox" name="availability_verified" /> أيام
              التوافر وعمر المنتج موثقان إن تم إدخالهما
            </label>
          </div>
          <div className="form-actions">
            <button
              className="primary"
              disabled={
                uploading ||
                busy ||
                !inspectionReady ||
                !!mappingIssue ||
                (sheetMode === "selected" &&
                  !sheets.split(/\r?\n/).some(Boolean))
              }
            >
              {uploading ? "جاري الاستخراج…" : "استخراج وتجهيز المراجعة"}
            </button>
            <a className="secondary" href={`/api/templates/${type}`} download>
              <ArrowDownToLine size={15} /> قالب تجريبي {labels[type]}
            </a>
          </div>
          {uploadError && (
            <p className="alert" role="alert">
              {uploadError}
            </p>
          )}
        </form>
      </section>
      {batch && (
        <section className="panel review" aria-label="مراجعة الدفعة">
          <div className="section-title">
            <div>
              <h2>
                مراجعة: <bdi>{batch.filename}</bdi>
              </h2>
              <p>
                {labels[batch.report_type]} · {batch.start} إلى {batch.end} ·{" "}
                {batch.scope}
              </p>
            </div>
            <span
              className={"pill " + (batch.status === "accepted" ? "good" : "")}
            >
              {labels[batch.status]}
            </span>
          </div>
          <small className="checksum">
            SHA-256: <bdi>{batch.checksum}</bdi>
          </small>
          <div className="review-stats">
            <span>
              <strong>{batch.reconciliation.details}</strong> صف تفاصيل
            </span>
            <span>
              <strong>{batch.reconciliation.excluded}</strong> عنوان / مجموع /
              استمرار
            </span>
            <span>
              <strong>{batch.issues.length}</strong> ملاحظة مانعة
            </span>
          </div>
          <p className="hint">
            {batch.status === "staged"
              ? "تم استخراج الملف وحفظه للمراجعة. لا يدخل في المخزون أو المبيعات والتحليل إلا بعد قبول البيانات أدناه."
              : batch.status === "accepted"
                ? "هذا الملف معتمد ومشارك في البيانات والتحليل."
                : "هذا الملف محفوظ في السجل ولا يشارك في التحليل."}
          </p>
          {comparison && (
            <div aria-label="مطابقة الملف مع البيانات الموجودة">
              <div className="review-stats">
                <span>
                  <strong>{comparison.existing_products}</strong> صنف موجود بنفس
                  الباركود
                </span>
                <span>
                  <strong>{comparison.new_products}</strong> صنف جديد
                </span>
                {batch.report_type === "snapshot" && (
                  <span>
                    <strong>{comparison.changed_stock_products}</strong> صنف
                    تغير رصيده عن الجرد السابق
                  </span>
                )}
              </div>
              {batch.report_type === "snapshot" && (
                <p className="hint">
                  الجرد رصيد بتاريخ محدد؛ يحل أحدث جرد محل الرصيد المعروض ولا
                  يُضاف إليه.
                </p>
              )}
              {comparison.overlaps.map((overlap) => (
                <p className="alert" key={overlap.id}>
                  يوجد ملف معتمد لنفس النوع والنطاق والفترة: {overlap.filename}{" "}
                  ({overlap.start} إلى {overlap.end}). راجع الملف السابق وتراجع
                  عنه بسبب موثق إذا كان الجديد تصحيحًا له؛ لن تتم مضاعفة
                  البيانات.
                  <button
                    className="text-button"
                    onClick={() => review(overlap.id)}
                  >
                    فتح الملف المعتمد
                  </button>
                </p>
              ))}
              {comparison.stock_changes.length > 0 && (
                <details>
                  <summary>
                    تغيرات الرصيد مقارنة بجرد{" "}
                    {comparison.previous_snapshot_date}
                  </summary>
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>الباركود</th>
                          <th>الصنف</th>
                          <th>الرصيد السابق</th>
                          <th>رصيد الملف</th>
                          <th>الفرق</th>
                        </tr>
                      </thead>
                      <tbody>
                        {comparison.stock_changes.map((change) => (
                          <tr key={change.barcode}>
                            <td>
                              <bdi>{change.barcode}</bdi>
                            </td>
                            <td>{change.name}</td>
                            <td>{change.previous}</td>
                            <td>{change.incoming}</td>
                            <td>{change.difference}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <small>
                    أول 20 تغيرًا؛ الفرق بين رصيدين وليس حركة بيع أو شراء.
                  </small>
                </details>
              )}
            </div>
          )}
          {batch.issues.map((i) => (
            <p className="alert" key={i}>
              {message(i)}
            </p>
          ))}
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>المؤشر</th>
                  <th>المصدر</th>
                  <th>مجموع الصفوف</th>
                  <th>الفرق (الصفوف − المصدر)</th>
                  <th>المطابقة</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(batch.reconciliation.checks).map(([k, c]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{c.expected}</td>
                    <td>{c.actual}</td>
                    <td>{c.difference ?? "—"}</td>
                    <td>{c.matches ? "✓ مطابق" : "غير مطابق"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <details>
            <summary>الصفوف الخام والمطبعة ودليل المصدر</summary>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>الموضع</th>
                    <th>نوع الصف</th>
                    <th>القيم المطبعة</th>
                    <th>النص الخام</th>
                    <th>الملاحظات</th>
                  </tr>
                </thead>
                <tbody>
                  {batch.rows
                    ?.slice(rowPage * 50, (rowPage + 1) * 50)
                    .map((row) => (
                      <tr key={row.occurrence}>
                        <td>
                          <code>{JSON.stringify(row.raw.location)}</code>
                          {row.continuation && (
                            <small>
                              استمرار: {JSON.stringify(row.continuation)}
                            </small>
                          )}
                        </td>
                        <td>{row.kind}</td>
                        <td>
                          <pre>{JSON.stringify(row.data, null, 2)}</pre>
                        </td>
                        <td>
                          {(row.raw.logical_cells ?? row.raw.cells).join(" | ")}
                        </td>
                        <td>
                          {row.issues.map((i) => (
                            <p key={i}>{message(i)}</p>
                          ))}
                          {row.diagnostics?.map((diagnostic, index) => (
                            <p key={index}>
                              عمود <bdi>{diagnostic.column}</bdi> · القيمة:{" "}
                              <bdi>{diagnostic.value || "فارغة"}</bdi>
                              <br />
                              المطلوب: <bdi>{diagnostic.expected}</bdi>؛ صحح
                              المصدر أو تعيين الأعمدة وأعد الرفع.
                            </p>
                          ))}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <button
                className="secondary"
                disabled={rowPage === 0}
                onClick={() => setRowPage((p) => p - 1)}
              >
                السابق
              </button>
              <span>
                صفحة {rowPage + 1} من{" "}
                {Math.max(1, Math.ceil((batch.rows?.length ?? 0) / 50))}
              </span>
              <button
                className="secondary"
                disabled={(rowPage + 1) * 50 >= (batch.rows?.length ?? 0)}
                onClick={() => setRowPage((p) => p + 1)}
              >
                التالي
              </button>
            </div>
          </details>
          <div className="form-actions">
            {batch.status === "staged" && (
              <>
                <button
                  className="primary"
                  disabled={busy || !comparison?.can_accept}
                  onClick={() => act("accept")}
                >
                  <Check size={17} />
                  قبول البيانات
                </button>
                <button
                  className="secondary danger"
                  disabled={busy}
                  onClick={() => act("reject")}
                >
                  رفض الدفعة
                </button>
              </>
            )}
            {batch.status === "accepted" && (
              <>
                <button className="primary" onClick={analyze}>
                  عرض التحليل والنصائح المحدثة
                </button>
                <button
                  className="secondary danger"
                  disabled={busy}
                  onClick={() => act("rollback")}
                >
                  تراجع موثق عن الدفعة
                </button>
              </>
            )}
            <button className="text-button" onClick={() => setBatch(null)}>
              إغلاق المراجعة
            </button>
          </div>
        </section>
      )}
      <section className="panel">
        <div className="section-title">
          <h2>سجل الاستيراد</h2>
          <span className="pill">{list.length} دفعة</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>الملف</th>
                <th>النوع</th>
                <th>الفترة</th>
                <th>الحالة</th>
                <th>التفاصيل</th>
              </tr>
            </thead>
            <tbody>
              {list.map((b) => (
                <tr key={b.id}>
                  <td>
                    <bdi>{b.filename}</bdi>
                  </td>
                  <td>{labels[b.report_type]}</td>
                  <td>
                    <bdi>
                      {b.start} — {b.end}
                    </bdi>
                  </td>
                  <td>
                    <span className="pill">{labels[b.status]}</span>
                  </td>
                  <td>
                    <button
                      className="text-button"
                      onClick={() => review(b.id)}
                    >
                      مراجعة
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!list.length && (
            <div className="quiet">لسه مفيش تقارير مستوردة.</div>
          )}
        </div>
      </section>
    </>
  );
}

function SettingsPage({
  fail,
  notify,
}: {
  fail: (e: unknown) => void;
  notify: (s: string) => void;
}) {
  const [rules, setRules] = useState<Rules | null>(null),
    [audit, setAudit] = useState<
      {
        id: number;
        action: string;
        at: string;
        reason: string;
        batch_id: string | null;
      }[]
    >([]);
  useEffect(() => {
    void api<Rules>("/settings").then(setRules).catch(fail);
    void api<typeof audit>("/audit").then(setAudit).catch(fail);
  }, [fail]);
  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try {
      await api("/settings", { method: "PUT", body: JSON.stringify(rules) });
      notify("تم حفظ حدود التوصيات وتسجيل التغيير");
    } catch (error) {
      fail(error);
    }
  }
  return (
    <>
      <section className="panel">
        <div className="section-title">
          <div>
            <h2>قواعد واضحة، تحت سيطرتك</h2>
            <p>
              القيم دي نقطة بداية قابلة للتعديل؛ راجعها حسب موسم المحل ومدة
              التوريد.
            </p>
          </div>
          <Settings size={24} />
        </div>
        {rules && (
          <form onSubmit={save}>
            <div className="form-grid">
              {Object.entries(rules).map(([key, value]) => (
                <label key={key}>
                  {labels[key]}
                  <input
                    inputMode="decimal"
                    value={value}
                    onChange={(e) =>
                      setRules({
                        ...rules,
                        [key]:
                          typeof value === "number"
                            ? Number(e.target.value)
                            : e.target.value,
                      })
                    }
                    required
                  />
                </label>
              ))}
            </div>
            <button className="primary">حفظ القواعد</button>
          </form>
        )}
        <p className="hint">
          لتسجيل المصروفات والتكاليف والأهداف: استخدم صفحة الاستيراد والقالب
          الموافق. تكلفة المخزون لا تتحول تلقائيًا لتكلفة مبيعات تاريخية.
        </p>
      </section>
      <section className="panel">
        <div className="section-title">
          <h2>سجل المراجعة والتغييرات</h2>
          <ClipboardList size={24} />
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>الوقت</th>
                <th>الإجراء</th>
                <th>الدفعة</th>
                <th>السبب</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((a) => (
                <tr key={a.id}>
                  <td>
                    <bdi>{new Date(a.at).toLocaleString("ar-EG")}</bdi>
                  </td>
                  <td>{labels[a.action] ?? a.action}</td>
                  <td>
                    <code>{a.batch_id?.slice(0, 8) ?? "—"}</code>
                  </td>
                  <td>{a.reason || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </>
  );
}

export { Overview };
const root = document.getElementById("root");
if (root)
  createRoot(root).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>,
  );
