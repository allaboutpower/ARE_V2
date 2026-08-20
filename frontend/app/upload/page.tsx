"use client";

import {
  Accordion,
  AccordionItem,
  Button,
  Column,
  CodeSnippet,
  Dropdown,
  FileUploader,
  Grid,
  InlineLoading,
  InlineNotification,
  Tile,
} from "@carbon/react";
import { useState } from "react";
import { fetchWeeks, generatePrompt, PromptDetail, WeekOption } from "../lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [weeks, setWeeks] = useState<WeekOption[]>([]);
  const [selectedWeek, setSelectedWeek] = useState<WeekOption | null>(null);
  const [result, setResult] = useState<PromptDetail | null>(null);
  const [loading, setLoading] = useState<"weeks" | "prompt" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleFileAdded(
    _event: React.SyntheticEvent<HTMLElement>,
    content: { addedFiles: File[] },
  ) {
    const f = content.addedFiles[0] ?? null;
    setFile(f);
    setWeeks([]);
    setSelectedWeek(null);
    setResult(null);
    setError(null);
    if (!f) return;

    setLoading("weeks");
    try {
      const res = await fetchWeeks(f);
      setWeeks(res.weeks);
      if (res.weeks.length > 0) setSelectedWeek(res.weeks[0]);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(null);
    }
  }

  async function handleGenerate() {
    if (!file || selectedWeek === null) return;
    setError(null);
    setLoading("prompt");
    try {
      const prompt = await generatePrompt(file, selectedWeek.week_index);
      setResult(prompt);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(null);
    }
  }

  return (
    <Grid className="are-page">
      <Column lg={16} md={8} sm={4}>
        <h1 style={{ marginBottom: "1.5rem" }}>上傳 CSV 產生 Prompt</h1>
      </Column>

      <Column lg={10} md={8} sm={4}>
        <Tile className="are-tile">
          <FileUploader
            labelTitle="上傳週序列 CSV"
            labelDescription="欄位需含 date, revenue, marketing_cost, is_holiday_week, competitor_price_change"
            buttonLabel="選擇檔案"
            accept={[".csv"]}
            filenameStatus="edit"
            multiple={false}
            onAddFiles={handleFileAdded}
            onDelete={() => {
              setFile(null);
              setWeeks([]);
              setSelectedWeek(null);
              setResult(null);
            }}
          />
          {loading === "weeks" && (
            <InlineLoading description="解析 CSV、計算週次中…" style={{ marginTop: "1rem" }} />
          )}
        </Tile>

        {error && (
          <InlineNotification
            kind="error"
            title="錯誤"
            subtitle={error}
            onCloseButtonClick={() => setError(null)}
            className="are-tile"
          />
        )}

        {weeks.length > 0 && (
          <Tile className="are-tile">
            <Dropdown
              id="week-select"
              className="are-week-select"
              titleText="選擇週次"
              label="選擇週次"
              items={weeks}
              itemToString={(w: WeekOption | null) =>
                w ? `week ${w.week_index}（${w.week_date}）` : ""
              }
              selectedItem={selectedWeek}
              onChange={(e: { selectedItem: WeekOption | null }) =>
                setSelectedWeek(e.selectedItem)
              }
            />
            <div className="are-actions">
              <Button onClick={handleGenerate} disabled={loading === "prompt"}>
                {loading === "prompt" ? "產生中…" : "產生 Prompt"}
              </Button>
            </div>
          </Tile>
        )}
      </Column>

      {result && (
        <Column lg={16} md={8} sm={4}>
          <Tile className="are-tile">
            <h3 style={{ marginBottom: "1rem" }}>Prompt(已存入 DB，id #{result.id})</h3>
            <div className="are-output-box">
              <CodeSnippet type="multi" feedback="已複製！">
                {result.prompt_text}
              </CodeSnippet>
            </div>

            <div className="are-evidence-accordion" style={{ marginTop: "1.5rem" }}>
              <Accordion>
                <AccordionItem title="Evidence Package">
                  <div className="are-output-box">
                    <CodeSnippet type="multi" feedback="已複製！">
                      {JSON.stringify(result.evidence_package, null, 2)}
                    </CodeSnippet>
                  </div>
                </AccordionItem>
              </Accordion>
            </div>
          </Tile>
        </Column>
      )}
    </Grid>
  );
}
