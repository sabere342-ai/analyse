import { useEffect, useRef, useState } from "react";
import { api, labels, message } from "./api";
import { selectedSheets } from "./import-options";
import type { ParserOptions, SheetMode } from "./import-options";

type Sheet = {
  name: string;
  report_type: string | null;
  columns: string[];
  preview: string[][];
  rows: number;
  status: string;
};
type Inspection = {
  filename: string;
  size: number;
  format: string;
  status: string;
  sheets: Sheet[];
  worksheet_names?: string[];
  issues: string[];
  pages: number;
  source_period?: { start: string; end: string } | null;
};
const statuses: Record<string, string> = {
  RECOGNIZED: "الأعمدة معروفة — راجع المعاني والإجماليات قبل القبول",
  NEEDS_MAPPING: "يحتاج تعيين أعمدة أو اختيار ورقة البيانات",
  NEEDS_REVIEW: "يحتاج مراجعة الخيارات والقيم",
  UNSUPPORTED: "التنسيق غير مدعوم؛ صدّر جدول CSV أو Excel نصي",
  INVALID: "الملف غير صالح للقراءة؛ راجع السبب وأعد حفظه",
};
const fields: Record<string, string[]> = {
  snapshot: [
    "barcode",
    "name",
    "quantity",
    "category",
    "reserved",
    "available",
  ],
  sales: [
    "barcode",
    "name",
    "sold",
    "returned",
    "rep",
    "net",
    "gross",
    "discount",
    "return_value",
    "cogs",
  ],
  movement: [
    "barcode",
    "name",
    "date",
    "kind",
    "incoming",
    "outgoing",
    "reference",
  ],
  costs: ["barcode", "cost", "name"],
  expenses: ["date", "category", "amount", "reference"],
  targets: ["rep", "target"],
};
const fieldLabels: Record<string, string> = {
  barcode: "الباركود",
  name: "اسم الصنف",
  quantity: "الكمية",
  category: "التصنيف",
  reserved: "المحجوز",
  available: "المتاح",
  rep: "المندوب",
  net: "صافي القيمة",
  gross: "المبيعات قبل الخصم",
  discount: "خصم المبيعات",
  return_value: "قيمة المرتجعات",
  date: "التاريخ",
  kind: "نوع الحركة",
  incoming: "الوارد",
  outgoing: "الصادر",
  reference: "المرجع",
  cost: "تكلفة الوحدة",
  amount: "المبلغ",
  target: "الهدف",
};

export function ImportInspection({
  maxBytes,
  type,
  mapping,
  onMapping,
  sheets,
  onSheets,
  onDetected,
  sheetMode = "all",
  onSheetMode = () => {},
  options = { encoding: "utf-8-sig", delimiter: "auto", pdf_profile: "auto" },
  onReady = () => {},
  onSourceChange = () => {},
}: {
  maxBytes: number;
  type: string;
  mapping: Record<string, string>;
  onMapping: (mapping: Record<string, string>) => void;
  sheets: string;
  onSheets: (sheets: string) => void;
  sheetMode?: SheetMode;
  onSheetMode?: (mode: SheetMode) => void;
  options?: ParserOptions;
  onReady?: (ready: boolean) => void;
  onSourceChange?: () => void;
  onDetected: (
    type: string,
    period?: { start: string; end: string } | null,
  ) => void;
}) {
  const [result, setResult] = useState<Inspection | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const request = useRef(0);
  const input = useRef<HTMLInputElement>(null);
  const fileRef = useRef<File | undefined>(undefined);
  const [worksheetNames, setWorksheetNames] = useState<string[]>([]);
  const key = (kind: string, mode: SheetMode, names: string) =>
    JSON.stringify([kind, options, mode, names]);
  const context = key(type, sheetMode, sheets);
  const inspectedContext = useRef(context);
  useEffect(() => {
    if (inspectedContext.current !== context) {
      request.current += 1;
      inspectedContext.current = context;
      setResult(null);
      setBusy(false);
      onReady(false);
      if (fileRef.current)
        setError(
          "الخيارات أو الأوراق اتغيرت؛ أعد فحص الملف قبل تجهيز المراجعة",
        );
    }
  }, [context]);
  useEffect(
    () => () => {
      request.current += 1;
    },
    [],
  );
  function sourceChanged(file?: File) {
    fileRef.current = file;
    setWorksheetNames([]);
    onSourceChange();
    onMapping({});
    onSheets("");
    onSheetMode("all");
    inspectedContext.current = key(type, "all", "");
    void inspect(file, "all", "");
  }
  async function inspect(file?: File, mode = sheetMode, names = sheets) {
    const generation = ++request.current;
    setResult(null);
    setError("");
    setBusy(false);
    onReady(false);
    if (!file) return;
    if (file.size > maxBytes) {
      setError(message("upload_too_large"));
      return;
    }
    setBusy(true);
    let selected: string[];
    try {
      selected = selectedSheets(names, mode);
    } catch (e) {
      setError((e as Error).message);
      setBusy(false);
      return;
    }
    const body = new FormData();
    body.set("file", file);
    body.set(
      "spec",
      JSON.stringify({
        report_type: type,
        ...options,
        sheet_mode: mode,
        sheets: selected,
      }),
    );
    try {
      const inspection = await api<Inspection>("/imports/inspect", {
        method: "POST",
        body,
      });
      if (generation !== request.current) return;
      setResult(inspection);
      if (inspection.worksheet_names?.length || inspection.sheets.length)
        setWorksheetNames(
          inspection.worksheet_names ??
            inspection.sheets.map((sheet) => sheet.name),
        );
      const kinds = [
        ...new Set(
          inspection.sheets.map((sheet) => sheet.report_type).filter(Boolean),
        ),
      ];
      if (kinds.length === 1) {
        inspectedContext.current = key(kinds[0]!, mode, names);
        onDetected(kinds[0]!, inspection.source_period);
      }
      onReady(
        inspection.sheets.length > 0 &&
          !["INVALID", "UNSUPPORTED"].includes(inspection.status),
      );
    } catch (e) {
      if (generation === request.current)
        setError(e instanceof Error ? e.message : "تعذر فحص الملف");
    } finally {
      if (generation === request.current) setBusy(false);
    }
  }
  const selected = sheets.split(/\r?\n/).filter(Boolean);
  const columns = [
    ...new Set(
      (result?.sheets ?? [])
        .filter((sheet) => sheetMode === "all" || selected.includes(sheet.name))
        .flatMap((sheet) => sheet.columns)
        .filter(Boolean),
    ),
  ];
  return (
    <>
      <div
        className="upload-box"
        onDragOver={(event) => event.preventDefault()}
        onDrop={(event) => {
          event.preventDefault();
          const file = event.dataTransfer.files[0];
          if (file && input.current) {
            const transfer = new DataTransfer();
            transfer.items.add(file);
            input.current.files = transfer.files;
            sourceChanged(file);
          }
        }}
      >
        <label>
          اختار ملف التقرير
          <input
            ref={input}
            name="file"
            type="file"
            accept=".pdf,.csv,.xls,.xlsx"
            required
            onChange={(event) => sourceChanged(event.target.files?.[0])}
          />
        </label>
        <small>
          اسحب الملف هنا أو اختاره · PDF / CSV / XLS / XLSX · حد{" "}
          {maxBytes / 1024 / 1024} MB
        </small>
        <button
          type="button"
          className="secondary"
          disabled={busy || !input.current?.files?.length}
          onClick={() => void inspect(input.current?.files?.[0])}
        >
          إعادة فحص الملف بالخيارات الحالية
        </button>
      </div>
      {busy && <p role="status">جاري فحص بنية الملف والأعمدة…</p>}
      {error && (
        <p role="alert" className="alert">
          {error}
        </p>
      )}
      {!!worksheetNames.length &&
        fileRef.current?.name.toLowerCase().match(/\.xlsx?$/) && (
          <fieldset>
            <legend>نطاق أوراق Excel</legend>
            <label>
              <input
                type="radio"
                name="worksheet_mode"
                value="all"
                checked={sheetMode === "all"}
                onChange={() => {
                  onSheetMode("all");
                  onSheets("");
                }}
              />
              كل أوراق الملف
            </label>
            <label>
              <input
                type="radio"
                name="worksheet_mode"
                value="selected"
                checked={sheetMode === "selected"}
                onChange={() => onSheetMode("selected")}
              />
              أوراق مختارة فقط
            </label>
            <p>
              {sheetMode === "all"
                ? "كل الأوراق مشمولة في الاستيراد."
                : selected.length
                  ? `سيتم استيراد ${selected.length} ورقة مختارة فقط.`
                  : "اختار ورقة واحدة على الأقل؛ لن يتم استيراد كل الأوراق تلقائيًا."}
            </p>
            {worksheetNames.map((name) => (
              <label key={name}>
                <input
                  type="checkbox"
                  disabled={sheetMode === "all"}
                  checked={sheetMode === "all" || selected.includes(name)}
                  onChange={(event) =>
                    onSheets(
                      (event.target.checked
                        ? [...selected, name]
                        : selected.filter((item) => item !== name)
                      ).join("\n"),
                    )
                  }
                />
                قراءة ورقة {name}
              </label>
            ))}
          </fieldset>
        )}
      {result && (
        <section aria-label="فحص الملف" className="panel">
          <h3>{statuses[result.status]}</h3>
          <p>
            <bdi>{result.filename}</bdi> · {result.size} بايت ·{" "}
            {result.format.toUpperCase()}
            {result.pages > 0 ? ` · ${result.pages} صفحة` : ""}
          </p>
          <p className="hint">
            الفحص لا يعتمد البيانات. اختار الأوراق وعيّن الأعمدة عند الحاجة ثم
            جهّز المراجعة وطابق الإجماليات.
          </p>
          {result.issues.map((issue) => (
            <p key={issue} className="alert">
              {message(issue)}
            </p>
          ))}
          {result.sheets.map((sheet) => (
            <details key={sheet.name} open={result.sheets.length === 1}>
              <summary>
                {sheet.name} · {sheet.rows} صف مصدر ·{" "}
                {sheet.report_type
                  ? labels[sheet.report_type]
                  : "أعمدة غير معروفة"}
              </summary>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      {sheet.columns.map((column, index) => (
                        <th key={index}>{column || `عمود ${index + 1}`}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sheet.preview.map((row, index) => (
                      <tr key={index}>
                        {row.map((cell, col) => (
                          <td key={col}>
                            <bdi>{cell}</bdi>
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          ))}
          {!!columns.length && result.format !== "pdf" && (
            <details open={result.status === "NEEDS_MAPPING"}>
              <summary>تعيين الأعمدة من القائمة</summary>
              <p>
                اختار عمود المصدر لكل حقل مطلوب. التعيين يستخدم أسماء العناوين؛
                الأوراق ذات العناوين المختلفة تحتاج استيرادًا منفصلًا عند
                التعيين اليدوي.
              </p>
              <div className="form-grid">
                {(fields[type] ?? []).map((field) => (
                  <label key={field}>
                    {fieldLabels[field] ?? labels[field] ?? field}
                    <select
                      aria-label={`تعيين ${fieldLabels[field] ?? labels[field] ?? field}`}
                      value={mapping[field] ?? ""}
                      onChange={(event) => {
                        const next = { ...mapping };
                        if (event.target.value)
                          next[field] = event.target.value;
                        else delete next[field];
                        onMapping(next);
                      }}
                    >
                      <option value="">اكتشاف تلقائي / غير موجود</option>
                      {columns.map((column) => (
                        <option key={column} value={column}>
                          {column}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
            </details>
          )}
        </section>
      )}
    </>
  );
}
