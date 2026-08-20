"use client";

import { ArrowRight } from "@carbon/icons-react";
import { Button, Column, Grid } from "@carbon/react";
import { useRouter } from "next/navigation";

export default function Home() {
  const router = useRouter();

  return (
    <Grid className="are-landing">
      <Column lg={{ span: 8, offset: 4 }} md={8} sm={4}>
        <div className="are-landing-content">
          <h1 className="are-landing-title">ARE — Analytical Reasoning Engine</h1>
          <p className="are-landing-subtitle">
            上傳週序列 CSV，自動跑完 STL 特徵計算與因子比對，
            產生證據限定式（evidence-conditioned）prompt，並存進資料庫供後續查看。
          </p>
          <Button
            size="lg"
            renderIcon={ArrowRight}
            onClick={() => router.push("/upload")}
          >
            Get Started
          </Button>
        </div>
      </Column>
    </Grid>
  );
}
