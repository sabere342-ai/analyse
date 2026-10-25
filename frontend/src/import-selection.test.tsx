import { useState } from "react";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi } from "vitest";
import { ImportInspection } from "./ImportInspection";
import { parseMapping, selectedSheets } from "./import-options";
import type { SheetMode } from "./import-options";

it("shows all worksheets selected when the importer will read all", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        filename: "sheets.xlsx",
        size: 100,
        format: "xlsx",
        status: "RECOGNIZED",
        issues: [],
        pages: 0,
        sheets: ["First", "Second"].map((name) => ({
          name,
          report_type: "snapshot",
          columns: ["barcode", "name", "quantity"],
          preview: [],
          rows: 3,
          status: "RECOGNIZED",
        })),
      }),
    }),
  );
  function Harness() {
    const [sheets, setSheets] = useState("");
    const [mode, setMode] = useState<SheetMode>("all");
    return (
      <form>
        <ImportInspection
          maxBytes={4194304}
          type="snapshot"
          mapping={{}}
          onMapping={() => {}}
          sheets={sheets}
          onSheets={setSheets}
          onDetected={() => {}}
          sheetMode={mode}
          onSheetMode={setMode}
        />
      </form>
    );
  }
  try {
    render(<Harness />);
    fireEvent.change(screen.getByLabelText("اختار ملف التقرير"), {
      target: { files: [new File(["synthetic"], "sheets.xlsx")] },
    });
    expect(await screen.findByLabelText("قراءة ورقة First")).toBeChecked();
    expect(screen.getByLabelText("قراءة ورقة Second")).toBeChecked();
    fireEvent.click(screen.getByLabelText("أوراق مختارة فقط"));
    fireEvent.click(screen.getByLabelText("قراءة ورقة First"));
    fireEvent.click(screen.getByLabelText("قراءة ورقة First"));
    expect(screen.getByLabelText("أوراق مختارة فقط")).toBeChecked();
    expect(screen.getByLabelText("قراءة ورقة First")).not.toBeChecked();
    expect(
      screen.getByText(/لن يتم استيراد كل الأوراق تلقائيًا/),
    ).toBeVisible();
  } finally {
    vi.unstubAllGlobals();
  }
});

it("rejects empty explicit selections and invalid mapping values without an old valid fallback", () => {
  expect(selectedSheets("", "all")).toEqual([]);
  expect(() => selectedSheets("", "selected")).toThrow("اختار ورقة");
  expect(selectedSheets(" First \nSecond", "selected")).toEqual([
    " First ",
    "Second",
  ]);
  for (const value of ["{", "null", "[]", '{"barcode":4}', '{"barcode":""}'])
    expect(() => parseMapping(value)).toThrow();
});

it("ignores a stale inspection even when the replacement file has the same name and size", async () => {
  let oldResult: (value: unknown) => void = () => {};
  let newResult: (value: unknown) => void = () => {};
  const fetcher = vi
    .fn()
    .mockReturnValueOnce(
      new Promise((resolve) => {
        oldResult = resolve;
      }),
    )
    .mockReturnValueOnce(
      new Promise((resolve) => {
        newResult = resolve;
      }),
    );
  vi.stubGlobal("fetch", fetcher);
  const response = (content: string) => ({
    ok: true,
    json: async () => ({
      filename: "same.csv",
      size: 3,
      format: "csv",
      status: "NEEDS_MAPPING",
      issues: [],
      pages: 0,
      sheets: [
        {
          name: "CSV",
          report_type: null,
          columns: ["Identifier"],
          preview: [[content]],
          rows: 2,
          status: "NEEDS_MAPPING",
        },
      ],
    }),
  });
  try {
    render(
      <form>
        <ImportInspection
          maxBytes={4194304}
          type="snapshot"
          mapping={{}}
          onMapping={() => {}}
          sheets=""
          onSheets={() => {}}
          onDetected={() => {}}
        />
      </form>,
    );
    const input = screen.getByLabelText("اختار ملف التقرير");
    fireEvent.change(input, {
      target: { files: [new File(["old"], "same.csv")] },
    });
    fireEvent.change(input, {
      target: { files: [new File(["new"], "same.csv")] },
    });
    await act(async () => {
      newResult(response("new-source-row"));
    });
    await act(async () => {
      oldResult(response("old-source-row"));
    });
    expect(screen.getByText("new-source-row")).toBeVisible();
    expect(screen.queryByText("old-source-row")).toBeNull();
  } finally {
    vi.unstubAllGlobals();
  }
});
