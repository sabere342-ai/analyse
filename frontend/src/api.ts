export type Metric = {
  value: string | null;
  status: string;
  reason: string | null;
};
export type Evidence = {
  batch_id: string;
  occurrence?: number;
  location?: Record<string, string | number>;
};
export type Product = {
  barcode: string;
  name: string;
  category: string;
  stock: string | null;
  available: string | null;
  sold: string | null;
  returned: string | null;
  net_units: string | null;
  velocity: Metric;
  coverage: Metric;
  sell_through: Metric;
  net_sales: Metric;
  reported_net_sales?: Metric;
  replenishment_units: string | null;
  classification: string;
  evidence: Evidence[];
};
export type Representative = {
  rep: string;
  rank: number | null;
  net_sales: Metric;
  gross_sales: Metric;
  discount_rate: Metric;
  net_discount?: Metric;
  return_rate: Metric;
  target_achievement: Metric;
  profit_contribution: Metric;
  sold: Metric;
  returned: Metric;
};
export type Recommendation = {
  subject: string;
  barcode: string;
  observation: string;
  action: string;
  impact: string;
  quality: string;
  evidence: Evidence[];
};
export type Report = {
  period: { start: string; end: string; scope: string; stock_asof?: string };
  currency: string;
  sales_complete: boolean;
  sales_coverage?: "store" | "assigned_only";
  demand_source?: string;
  source_comparison?: {
    status: string;
    reported_sold?: string;
    reported_returned?: string;
    movement_sold?: string;
    movement_returned?: string;
    unassigned_sold?: string;
    unassigned_returned?: string;
    differences: {
      barcode: string;
      reported_sold: string;
      reported_returned: string;
      movement_sold: string;
      movement_returned: string;
      evidence: Evidence[];
    }[];
  };
  snapshot_date: string | null;
  warnings: string[];
  metrics: Record<string, Metric>;
  products: Product[];
  representatives: Representative[];
  categories: {
    category: string;
    stock: string | null;
    net_units: string | null;
    net_sales: Metric;
    contribution: Metric;
    incoming: string | null;
    outgoing: string | null;
  }[];
  recommendations: Recommendation[];
  trend: { net_sales_change: Metric };
  sources: {
    batch_id: string;
    report_type: string;
    start: string;
    end: string;
  }[];
};
export type Row = {
  occurrence: number;
  kind: string;
  data: Record<string, string>;
  issues: string[];
  diagnostics?: {
    field: string;
    column: string;
    value: string;
    expected: string;
    issue: string;
  }[];
  raw: {
    cells: string[];
    logical_cells?: string[];
    location: Record<string, string | number>;
  };
  continuation?: Record<string, string | number>;
};
export type Batch = {
  id: string;
  filename: string;
  checksum: string;
  report_type: string;
  status: string;
  start: string;
  end: string;
  scope: string;
  issues: string[];
  rows?: Row[];
  reconciliation: {
    details: number;
    excluded: number;
    totals: Record<string, string>;
    checks: Record<
      string,
      {
        expected: string;
        actual: string;
        matches: boolean;
        difference?: string;
      }
    >;
  };
  metadata: Record<string, unknown>;
  created_at: string;
};
export type Rules = {
  target_cover_days: number;
  lead_time_days: number;
  min_history_days: number;
  dead_no_sale_days: number;
  max_cover_days: number;
  slow_velocity: string;
  return_alert_rate: string;
  discount_alert_rate: string;
  minimum_margin_rate: string;
  safety_units: string;
};

export type AnalysisFilters = {
  start: string;
  end: string;
  scope: string;
  stock_asof: string;
};
export type ImportComparison = {
  new_products: number;
  existing_products: number;
  changed_stock_products: number;
  previous_snapshot_date: string | null;
  stock_changes: {
    barcode: string;
    name: string;
    previous: string;
    incoming: string;
    difference: string;
  }[];
  overlaps: { id: string; filename: string; start: string; end: string }[];
  can_accept: boolean;
};

export function analysisFilters(
  batches: Batch[],
  preferredScope?: string,
): AnalysisFilters | null {
  const active = batches.filter(
    (b) =>
      b.status === "accepted" &&
      (!preferredScope || b.scope === preferredScope),
  );
  const newest = (kind: string) =>
    active
      .filter((b) => b.report_type === kind)
      .sort(
        (a, b) =>
          b.end.localeCompare(a.end) ||
          b.created_at.localeCompare(a.created_at),
      )[0];
  const basis =
    newest("sales") ?? newest("movement") ?? newest("snapshot") ?? active[0];
  if (!basis) return null;
  const stock = active
    .filter((b) => b.report_type === "snapshot" && b.scope === basis.scope)
    .sort((a, b) => b.end.localeCompare(a.end))[0];
  return {
    start: basis.start,
    end: basis.end,
    scope: basis.scope,
    stock_asof: stock?.end ?? basis.end,
  };
}

export const labels: Record<string, string> = {
  reported_net_sales: "صافي القيمة في تقرير المندوبين فقط",
  reported_net_discount: "صافي الخصم في تقرير المندوبين فقط",
  net_discount: "صافي الخصم بعد عكس خصم المرتجعات",
  source_conflict: "تعارض بين مصادر المبيعات",
  pos_source_validation_failed:
    "مطابقة تفاصيل أو مجاميع تقرير POS فشلت؛ راجع الصفوف المحددة",
  source_period_does_not_match_import_metadata:
    "تواريخ الاستيراد مختلفة عن الفترة المطبوعة في التقرير",
  source_report_type_mismatch: "نوع التقرير المختار مختلف عن محتوى الملف",
  pos_fixed_profile_requires_empty_column_map:
    "التنسيق المعاير له أعمدة ثابتة؛ امسح تعيين الأعمدة المخصص أو اختار الجدول العام",
  discount_alert_rate: "حد تنبيه الخصومات ٪",
  minimum_margin_rate: "أقل هامش ربح قبل التنبيه ٪",
  gross_sales: "إجمالي المبيعات",
  discounts: "الخصومات",
  sales_returns: "قيمة المرتجعات",
  net_sales: "صافي المبيعات",
  cogs: "تكلفة البضاعة المباعة",
  gross_profit: "مجمل الربح",
  gross_margin: "هامش الربح ٪",
  expenses: "المصروفات",
  operating_profit: "الربح التشغيلي",
  stock: "رصيد المخزون",
  sold: "الوحدات المباعة",
  returned: "الوحدات المرتجعة",
  inventory_cost_value: "قيمة المخزون بالتكلفة",
  slow_stock_capital: "رأس المال في المخزون البطيء",
  snapshot: "جرد المخزون",
  sales: "مبيعات المندوبين",
  movement: "حركة المخزون",
  costs: "تكاليف المخزون",
  targets: "أهداف المندوبين",
  accepted: "مقبول",
  staged: "قيد المراجعة",
  rejected: "مرفوض",
  rolled_back: "تم التراجع",
  insufficient_history: "تاريخ غير كافٍ للتصنيف",
  zero_sales: "بلا مبيعات في الفترة",
  slow: "بطيء الحركة",
  potentially_dead: "ركود محتمل",
  target_cover_days: "أيام التغطية المستهدفة بعد مهلة التوريد",
  lead_time_days: "مهلة التوريد بالأيام",
  min_history_days: "أقل تاريخ للتصنيف",
  dead_no_sale_days: "فترة مراجعة الركود",
  max_cover_days: "أقصى تغطية قبل التنبيه",
  slow_velocity: "حد بطء الحركة (قطعة/يوم)",
  return_alert_rate: "حد تنبيه المرتجعات ٪",
  safety_units: "وحدات الأمان",
  no_detail_records: "مفيش صفوف تفاصيل صالحة",
  report_coverage_confirmation_required: "أكد اكتمال تغطية التقرير",
  row_issues_require_corrected_reimport:
    "فيه صفوف محتاجة تصحيح أو تعيين أعمدة ثم إعادة رفع",
  source_total_mismatch: "إجمالي الصفوف مش مطابق للمصدر",
  overlapping_accepted_coverage_rollback_explicitly_first:
    "فيه تقرير مقبول لنفس التغطية؛ راجعه وتراجع عنه صراحةً قبل الاستبدال",
  authentication_required: "سجّل الدخول أولًا",
  upload_too_large: "حجم الملف أكبر من الحد الموضح في شاشة الاستيراد",
  empty_or_oversized_file: "الملف فارغ أو أكبر من الحد المسموح",
  owner_setup_requires_invitation:
    "افتح رابط تفعيل المالك الخاص بيك لإنشاء الحساب",
  invalid_credentials: "كلمة المرور غير صحيحة",
  login_rate_limited: "محاولات كتير؛ جرّب بعد خمس دقائق",
  numeric_barcode_requires_text_source:
    "الباركود خلية رقمية؛ نحتاج مصدرًا نصيًا يحافظ على الأصفار",
  workbook_formula_requires_review: "الصف فيه معادلة Excel تحتاج مراجعة",
  financial_semantics_not_confirmed: "معاني الأعمدة المالية محتاجة تأكيد",
  header_mapping_required: "عيّن الأعمدة أو استخدم القالب الموحد",
  sales_money_relationship_mismatch:
    "العلاقة بين المبيعات والخصم والمرتجع غير مطابقة",
  missing_or_invalid_barcode: "باركود مفقود أو غير صالح",
  pdf_layout_requires_adapter_no_table_or_text_layer:
    "تنسيق PDF محتاج تعيين متخصص أو نسخة CSV/Excel؛ لم نجد جدولًا قابلًا للاستخراج",
  source_still_required: "المصدر مطلوب لدفعة نشطة",
  batch_not_validated: "الدفعة غير جاهزة للقبول",
  password_length_12_to_256: "كلمة المرور من 12 إلى 256 حرفًا",
  invalid_import_metadata: "راجع تواريخ وبيانات الاستيراد",
  no_rows_in_selected_source:
    "لم نجد صفوف بيانات؛ راجع أسماء أوراق Excel المختارة ومحتوى الملف",
  selected_worksheet_not_found:
    "اسم ورقة Excel مختارة غير موجود؛ انقله كما يظهر في الملف بالضبط",
  invalid_xls_signature:
    "الملف ليس XLS حقيقيًا؛ افتحه في Excel واحفظه بصيغة XLSX ثم ارفعه",
  invalid_xlsx_signature: "الملف ليس XLSX صالحًا؛ احفظ نسخة جديدة من Excel",
  csv_delimiter_requires_selection:
    "تعذر اكتشاف فاصل CSV؛ اختاره من خيارات الأعمدة والترميز",
  parser_resource_limit_or_failure:
    "تعذر قراءة الملف ضمن حدود المعالجة؛ جرّب اختيار ورقة البيانات فقط أو رفع نسخة CSV",
  parser_timeout: "استخراج الملف تجاوز الوقت المسموح",
  UnicodeDecodeError:
    "ترميز الملف مش UTF-8؛ اختار Windows Arabic وأعد فحص الملف",
  invalid_csv_quoting_or_field_size:
    "CSV فيه علامات تنصيص غير مغلقة أو خلية طويلة؛ أعد تصديره بعلامات تنصيص صحيحة",
  check_numeric_barcode_columns:
    "فيه خلايا رقمية؛ تأكد أن الباركود محفوظ كنص، لأن الأصفار المفقودة لا يمكن استعادتها تلقائيًا",
  subtotal_requires_numeric_evidence:
    "المجموع الفرعي بدون قيمة مستقلة قابلة للمطابقة؛ استخدم جدولًا بمجاميع واضحة",
  unsupported_file_type:
    "نوع الملف غير مدعوم؛ استخدم PDF نصي أو CSV أو XLS أو XLSX",
  extracted_text_limit:
    "النص المستخرج أكبر من حد المعالجة؛ اختار ورقة البيانات أو قسّم المصدر لفترات غير متداخلة",
  row_or_column_limit:
    "الملف تجاوز حدود الصفوف أو الأعمدة؛ اختار أوراق البيانات فقط وأزل التنسيق الزائد من نسخة جديدة",
};
export function message(code: string): string {
  return (
    labels[code] ??
    (code.startsWith("independent_source_total_required:")
      ? `أدخل إجمالي المصدر المستقل للحقل ${code.split(":")[1]}`
      : `تعذر إكمال العملية (${code})`)
  );
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("X-Requested-With", "Madrid");
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch("/api" + path, {
    ...options,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    const error: { detail?: unknown } = await response.json().catch(() => ({}));
    if (
      response.status === 401 &&
      (!path.startsWith("/auth/") || path === "/auth/logout")
    )
      window.dispatchEvent(new Event("madrid:session-expired"));
    throw new Error(
      typeof error.detail === "string"
        ? message(error.detail)
        : "راجع المدخلات وحاول تاني",
    );
  }
  return response.json() as Promise<T>;
}

export function metric(value?: Metric): string {
  return value?.value ?? "غير متاح";
}
