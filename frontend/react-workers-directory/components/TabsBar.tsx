import { navItems } from "../data/mock";

type TabsBarProps = {
  active: string;
};

export function TabsBar({ active }: TabsBarProps) {
  return (
    <div className="flex w-full flex-wrap gap-2 overflow-x-auto md:flex-nowrap">
      {navItems.map((item) => {
        const isActive = item === active;
        return (
          <button
            key={item}
            type="button"
            className={[
              "rounded-xl border px-4 py-2.5 text-sm font-semibold whitespace-nowrap transition duration-200",
              isActive
                ? "border-[#46652f] bg-gradient-to-b from-[#5a7c3e] to-[#355127] text-white shadow-md"
                : "border-[#c7d2b6] bg-[#f4f6ea] text-[#33472a] hover:bg-[#ecf1df]",
            ].join(" ")}
          >
            {item}
          </button>
        );
      })}
    </div>
  );
}
