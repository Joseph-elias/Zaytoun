import { HeroHeader } from "../components/HeroHeader";
import { MainPanel } from "../components/MainPanel";

export default function Page() {
  return (
    <main className="bg-scenic min-h-screen w-full">
      <HeroHeader title="Workers Directory" subtitle="Find and manage available agricultural workers." />
      <MainPanel />
    </main>
  );
}
