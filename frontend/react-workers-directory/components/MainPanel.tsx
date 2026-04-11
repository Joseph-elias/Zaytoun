"use client";

import dynamic from "next/dynamic";
import { workers } from "../data/mock";
import { FiltersSection } from "./FiltersSection";
import { TabsBar } from "./TabsBar";
import { WorkerCard } from "./WorkerCard";

const MapSection = dynamic(() => import("./MapSection").then((m) => m.MapSection), { ssr: false });

export function MainPanel() {
  return (
    <section className="mx-auto mb-10 w-full max-w-[1240px] px-4 md:px-8">
      <div className="glass-panel p-5 md:p-7">
        <div className="mb-6 grid gap-4 rounded-2xl border border-[#cfd8bf] bg-[#f2f5e8]/95 p-4 md:grid-cols-[auto_1fr_auto] md:items-center">
          <div className="flex items-center gap-3">
            <div className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-b from-[#5f8241] to-[#395726] text-sm font-bold text-white">
              JE
            </div>
            <div>
              <p className="text-base font-semibold text-[#23341c]">Joseph Elias Al Khoury</p>
              <p className="text-xs uppercase tracking-wide text-[#5f7150]">Farmer</p>
            </div>
          </div>

          <TabsBar active="Workers Directory" />

          <button
            type="button"
            className="h-11 rounded-xl border border-[#bfd0a5] bg-[#f3f7e8] px-5 text-sm font-semibold text-[#314726] transition duration-200 hover:bg-[#eaf1db]"
          >
            Logout
          </button>
        </div>

        <FiltersSection />

        <section className="mt-6 grid gap-5 xl:grid-cols-[1fr_1.1fr]">
          <div className="space-y-4">
            <h3 className="text-4xl font-semibold text-[#f8f6eb]">2 workers available</h3>
            {workers.map((worker) => (
              <WorkerCard key={worker.id} worker={worker} />
            ))}
          </div>
          <MapSection workers={workers} />
        </section>
      </div>
    </section>
  );
}
