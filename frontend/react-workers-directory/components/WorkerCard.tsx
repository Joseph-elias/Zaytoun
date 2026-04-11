import type { Worker } from "../data/mock";

type WorkerCardProps = {
  worker: Worker;
};

export function WorkerCard({ worker }: WorkerCardProps) {
  return (
    <article className="glass-soft border-[#c9d5b6] p-4 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:shadow-lg">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <img src="/workers-directory-bg.png" alt="" className="h-14 w-14 rounded-xl object-cover" />
          <div>
            <h3 className="text-2xl font-semibold text-[#24361d]">{worker.name}</h3>
            <p className="text-sm text-[#55694a]">Village {worker.village}</p>
          </div>
        </div>
        <span className="rounded-full border border-[#b2cd96] bg-[#deebcf] px-3 py-1 text-xs font-semibold text-[#2f6127]">
          {worker.available ? "Available" : "Busy"}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm text-[#3f5333]">
        <p>Distance {worker.distanceKm.toFixed(2)} km</p>
        <p>{worker.phone}</p>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
        <div className="space-y-1 text-sm font-medium text-[#2f4525]">
          <p>Men: P{worker.menRate}/day</p>
          <p>Women: P{worker.womenRate}/day</p>
        </div>
        <button
          type="button"
          className="rounded-xl bg-gradient-to-b from-[#5e8342] to-[#335023] px-5 py-2.5 text-sm font-semibold text-white transition duration-200 hover:brightness-95"
        >
          View Details
        </button>
      </div>
    </article>
  );
}
