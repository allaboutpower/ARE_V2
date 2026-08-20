"use client";

import {
  Column,
  DataTable,
  Grid,
  InlineNotification,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  Tile,
} from "@carbon/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { listPrompts, PromptListItem } from "../lib/api";

const headers = [
  { key: "filename", header: "檔名" },
  { key: "week", header: "週次" },
  { key: "created_at", header: "產生時間" },
];

export default function PromptsPage() {
  const router = useRouter();
  const [prompts, setPrompts] = useState<PromptListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listPrompts()
      .then(setPrompts)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, []);

  const rows = prompts.map((p) => ({
    id: String(p.id),
    filename: p.filename,
    week: `week ${p.week_index}（${p.week_date}）`,
    created_at: new Date(p.created_at).toLocaleString(),
  }));

  return (
    <Grid>
      <Column lg={16} md={8} sm={4}>
        <h1 style={{ marginBottom: "1.5rem" }}>歷史 Prompt</h1>

        {error && (
          <InlineNotification
            kind="error"
            title="錯誤"
            subtitle={error}
            onCloseButtonClick={() => setError(null)}
            className="are-tile"
          />
        )}

        {prompts.length === 0 && !error && <Tile>目前還沒有產生過任何 prompt。</Tile>}

        {prompts.length > 0 && (
          <DataTable rows={rows} headers={headers}>
            {({ rows, headers, getHeaderProps, getRowProps, getTableProps }) => (
              <TableContainer>
                <Table {...getTableProps()}>
                  <TableHead>
                    <TableRow>
                      {headers.map((header) => (
                        <TableHeader {...getHeaderProps({ header })} key={header.key}>
                          {header.header}
                        </TableHeader>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((row) => (
                      <TableRow
                        {...getRowProps({ row })}
                        key={row.id}
                        onClick={() => router.push(`/prompts/${row.id}`)}
                        style={{ cursor: "pointer" }}
                      >
                        {row.cells.map((cell) => (
                          <TableCell key={cell.id}>{cell.value}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </DataTable>
        )}
      </Column>
    </Grid>
  );
}
