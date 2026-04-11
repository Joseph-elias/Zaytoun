export function FiltersSection() {
  const inputBase =
    "field-focus h-12 w-full rounded-xl border border-[#b8c5a0] bg-[#fbfdf6] px-4 text-[#2f4124] placeholder:text-[#8a9779] transition duration-200";

  return (
    <section className="glass-soft p-5 md:p-7">
      <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <h2 className="text-4xl font-semibold text-[#2a3c20]">Filters</h2>
        <span className="inline-flex items-center rounded-full border border-[#d5ddc4] bg-[#f4f7ea] px-4 py-2 text-sm font-medium text-[#445739]">
          Live weather: 18.5C, feels 16.0C, partly cloudy
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f]">
          Village
          <input className={inputBase} placeholder="Enter village or area..." />
        </label>

        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f]">
          Availability
          <select className={inputBase} defaultValue="all">
            <option value="all">All</option>
            <option value="available">Available</option>
            <option value="busy">Busy</option>
          </select>
        </label>

        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f]">
          Work Date
          <input className={inputBase} type="date" />
        </label>

        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f]">
          Sort
          <select className={inputBase} defaultValue="newest">
            <option value="newest">Newest</option>
            <option value="distance">Distance</option>
          </select>
        </label>

        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f]">
          Max Distance (km)
          <input className={inputBase} type="number" placeholder="e.g. 25" />
        </label>

        <div className="flex items-end">
          <button
            type="button"
            className="h-12 rounded-xl border border-[#b8c7a2] bg-[#f6f9ed] px-6 text-sm font-semibold text-[#334928] transition duration-200 hover:bg-[#eef4e0]"
          >
            Use My Location
          </button>
        </div>

        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f]">
          Rate Type
          <select className={inputBase} defaultValue="any">
            <option value="any">Any</option>
            <option value="day">Per Day</option>
            <option value="hour">Per Hour</option>
          </select>
        </label>

        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f]">
          Min Men Rate
          <div className="relative">
            <input className={`${inputBase} pr-16`} placeholder="0" />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-[#687a58]">P/day</span>
          </div>
        </label>

        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f]">
          Max Women Rate
          <div className="relative">
            <input className={`${inputBase} pr-16`} placeholder="0" />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-[#687a58]">P/day</span>
          </div>
        </label>

        <label className="space-y-1 text-sm font-semibold text-[#3a4e2f] md:col-span-2 xl:col-span-1">
          Max Men Rate
          <div className="relative">
            <input className={`${inputBase} pr-16`} placeholder="0" />
            <span className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-[#687a58]">P/day</span>
          </div>
        </label>
      </div>

      <div className="mt-6 flex justify-end">
        <button
          type="button"
          className="h-14 w-full rounded-xl bg-gradient-to-b from-[#5f8343] to-[#2f4a22] px-10 text-lg font-semibold text-white shadow-lg transition duration-200 hover:brightness-95 md:w-auto"
        >
          Apply Filters
        </button>
      </div>
    </section>
  );
}
