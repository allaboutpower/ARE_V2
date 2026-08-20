"use client";

import {
  Accordion,
  AccordionItem,
  Breadcrumb,
  BreadcrumbItem,
  CodeSnippet,
  Column,
  Grid,
  InlineNotification,
  Tile,
} from "@carbon/react";
import { use, useEffect, useState } from "react";
import { getPrompt, PromptDetail } from "../../lib/api";

export default function PromptDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [prompt, setPrompt] = useState<PromptDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getPrompt(Number(id))
      .then(setPrompt)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [id]);

  return (
    <Grid>
      <Column lg={16} md={8} sm={4}>
        <Breadcrumb style={{ marginBottom: "1.5rem" }}>
          <BreadcrumbItem href="/prompts">歷史 Prompt</BreadcrumbItem>
        </Breadcrumb>

        {error && (
          <InlineNotification
            kind="error"
            title="錯誤"
            subtitle={error}
            onCloseButtonClick={() => setError(null)}
            className="are-tile"
          />
        )}

        {prompt && (
          <Tile className="are-tile">
            <h3 style={{ marginBottom: "1rem" }}>
              {prompt.filename} — week {prompt.week_index}（{prompt.week_date}）
            </h3>
            <div className="are-output-box">
              <CodeSnippet type="multi" feedback="已複製！">
                {prompt.prompt_text}
              </CodeSnippet>
            </div>

            <div className="are-evidence-accordion" style={{ marginTop: "1.5rem" }}>
              <Accordion>
                <AccordionItem title="Evidence Package">
                  <div className="are-output-box">
                    <CodeSnippet type="multi" feedback="已複製！">
                      {JSON.stringify(prompt.evidence_package, null, 2)}
                    </CodeSnippet>
                  </div>
                </AccordionItem>
              </Accordion>
            </div>
          </Tile>
        )}
      </Column>
    </Grid>
  );
}
