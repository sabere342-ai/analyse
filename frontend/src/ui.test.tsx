import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { metric, message, api, analysisFilters } from "./api";
import type { Batch, Report } from "./api";
import { Imports, Overview } from "./main";

function emptyReport(): Report {
  const missing = {
    value: null,
    status: "unavailable",
    reason: "missing_verified_data",
  };
  return {
    period: { start: "2026-10-01", end: "2026-10-23", scope: "store" },
    currency: "EGP",
    sales_complete: false,
    snapshot_date: null,
    warnings: ["فترة غير مكتملة"],
    metrics: Object.fromEntries(
      ["net_sales", "gross_profit", "stock", "operating_profit"].map((k) => [
        k,
        missing,
      ]),
    ),
    products: [],
    representatives: [],
    categories: [],
    recommendations: [],
    sources: [],
    trend: { net_sales_change: missing },
  };
}
describe("honest financial display", () => {
  it("chooses accepted report dates and keeps the stock date independent", () => {
    const batch = (
      report_type: string,
      start: string,
      end: string,
      status = "accepted",
      scope = "store",
    ) =>
      ({
        report_type,
        start,
        end,
        status,
        scope,
        created_at: "2026-10-25",
      }) as Batch;
    const stock = batch("snapshot", "2020-09-30", "2020-09-30");
    expect(analysisFilters([stock])).toEqual({
      start: stock.start,
      end: stock.end,
      stock_asof: stock.end,
      scope: "store",
    });
    const sales = batch("sales", "2020-09-01", "2020-09-29");
    expect(
      analysisFilters([
        stock,
        sales,
        batch("sales", "2030-01-01", "2030-01-31", "staged"),
      ]),
    ).toEqual({
      start: sales.start,
      end: sales.end,
      stock_asof: stock.end,
      scope: "store",
    });
    expect(
      analysisFilters(
        [
          stock,
          batch("sales", "2030-01-01", "2030-01-31", "accepted", "other"),
        ],
        "store",
      )?.end,
    ).toBe(stock.end);
    expect(
      analysisFilters([batch("sales", "2030-01-01", "2030-01-31", "staged")]),
    ).toBeNull();
  });
  it("keeps exact server decimal strings and distinguishes unavailable from zero", () => {
    expect(
      metric({
        value: "9007199254740993.01",
        status: "available",
        reason: null,
      }),
    ).toBe("9007199254740993.01");
    expect(metric({ value: "0.00", status: "available", reason: null })).toBe(
      "0.00",
    );
    expect(
      metric({ value: null, status: "unavailable", reason: "missing" }),
    ).toBe("غير متاح");
  });
  it("shows incomplete coverage and actionable first import without fake data", () => {
    const onImport = vi.fn();
    render(
      <Overview
        report={emptyReport()}
        onReview={vi.fn()}
        onImport={onImport}
      />,
    );
    expect(screen.getByText("فترة غير مكتملة")).toBeInTheDocument();
    expect(screen.getByText("أول قرار بيبدأ بتقرير")).toBeInTheDocument();
    expect(screen.getAllByText("غير متاح").length).toBeGreaterThan(3);
    fireEvent.click(screen.getByText("ابدأ استيراد تقرير"));
    expect(onImport).toHaveBeenCalledOnce();
  });
  it("renders untrusted report names as text and opens evidence", () => {
    const r = emptyReport();
    r.sources = [
      {
        batch_id: "b1",
        report_type: "snapshot",
        start: "2026-10-23",
        end: "2026-10-23",
      },
    ];
    r.recommendations = [
      {
        subject: "<img src=x onerror=alert(1)>",
        barcode: "000366",
        observation: "رصيد مرتفع",
        action: "راجع الشراء",
        impact: "رأس مال",
        quality: "limited",
        evidence: [{ batch_id: "b1", occurrence: 1, location: { row: 2 } }],
      },
    ];
    const onReview = vi.fn();
    const { container } = render(
      <Overview report={r} onReview={onReview} onImport={vi.fn()} />,
    );
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(/<img src=x/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("راجع الدليل"));
    expect(onReview).toHaveBeenCalledWith("b1");
  });
  it("explains a missing reconciliation total", () =>
    expect(message("independent_source_total_required:quantity")).toContain(
      "إجمالي المصدر",
    ));
  it("shows independent source counts and links a source disagreement to evidence", () => {
    const report = emptyReport();
    report.source_comparison = {
      status: "mismatch",
      reported_sold: "8",
      reported_returned: "1",
      movement_sold: "9",
      movement_returned: "2",
      differences: [
        {
          barcode: "001007",
          reported_sold: "8",
          reported_returned: "1",
          movement_sold: "9",
          movement_returned: "2",
          evidence: [
            { batch_id: "source-a", occurrence: 1, location: { page: 1 } },
          ],
        },
      ],
    };
    const onReview = vi.fn();
    render(<Overview report={report} onReview={onReview} onImport={vi.fn()} />);
    expect(
      screen.getByRole("heading", { name: "فرق محتاج تفسير بين تقارير البيع" }),
    ).toBeInTheDocument();
    expect(screen.getByText("001007")).toBeInTheDocument();
    fireEvent.click(screen.getByText("راجع المصدر"));
    expect(onReview).toHaveBeenCalledWith("source-a");
  });
  it("labels representative money separately when unassigned units are explained", () => {
    const report = emptyReport();
    report.sales_coverage = "assigned_only";
    report.demand_source = "movement";
    report.metrics.reported_net_sales = {
      value: "135.00",
      status: "available",
      reason: null,
    };
    report.source_comparison = {
      status: "explained_unassigned",
      reported_sold: "2",
      reported_returned: "1",
      movement_sold: "3",
      movement_returned: "2",
      unassigned_sold: "1",
      unassigned_returned: "1",
      differences: [],
    };
    render(<Overview report={report} onReview={vi.fn()} onImport={vi.fn()} />);
    const card = screen
      .getAllByText("صافي القيمة في تقرير المندوبين فقط")
      .find((el) => el.closest("article"))!
      .closest("article")!;
    expect(within(card).getByText("135.00")).toBeInTheDocument();
    expect(screen.getByText("صافي المبيعات").closest("div")).toHaveTextContent(
      "غير متاح",
    );
    expect(
      screen.getByText("بدون مندوب — فرق وحدات مؤكد النطاق"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", {
        name: "مبيعات بدون مندوب تفسر فرق نطاق التقريرين",
      }),
    ).toBeInTheDocument();
  });
  it("sends the CSRF boundary header and surfaces errors", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: "authentication_required" }),
    });
    vi.stubGlobal("fetch", fetcher);
    await expect(api("/batches")).rejects.toThrow("سجّل الدخول");
    expect(
      (fetcher.mock.calls[0][1].headers as Headers).get("X-Requested-With"),
    ).toBe("Madrid");
    vi.unstubAllGlobals();
  });
  it("sends selected Excel worksheet names with the import request", async () => {
    const fetcher = vi.fn().mockImplementation((_url, options) =>
      Promise.resolve({
        ok: true,
        json: async () =>
          options?.method === "POST" ? { id: "sheet-review" } : [],
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    try {
      const setBatch = vi.fn();
      const fail = vi.fn();
      render(
        <Imports
          batch={null}
          setBatch={setBatch}
          review={vi.fn()}
          act={vi.fn()}
          busy={false}
          fail={fail}
          defaults={{ start: "2026-10-01", end: "2026-10-24", scope: "store" }}
          maxUploadBytes={4194304}
        />,
      );
      fireEvent.change(screen.getByLabelText(/أوراق Excel المطلوبة/), {
        target: { value: "Stock\n\n Second " },
      });
      fireEvent.submit(
        screen
          .getByRole("button", { name: "استخراج وتجهيز المراجعة" })
          .closest("form")!,
      );
      await vi.waitFor(() =>
        expect(setBatch).toHaveBeenCalledWith({ id: "sheet-review" }),
      );
      const request = fetcher.mock.calls.find(
        ([, options]) => options?.method === "POST",
      )!;
      const spec = JSON.parse(request[1].body.get("spec") as string);
      expect(spec.sheets).toEqual(["Stock", "Second"]);
      expect(fail).not.toHaveBeenCalled();
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
