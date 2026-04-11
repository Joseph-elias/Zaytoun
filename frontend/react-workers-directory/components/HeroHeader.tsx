type HeroHeaderProps = {
  title: string;
  subtitle: string;
};

export function HeroHeader({ title, subtitle }: HeroHeaderProps) {
  return (
    <header className="mx-auto w-full max-w-[1240px] px-4 pt-8 pb-4 md:px-8 md:pt-10">
      <div className="flex items-center gap-3">
        <img src="/zaytoun-logo.png" alt="Zaytoun logo" className="h-10 w-auto md:h-12" />
        <span className="text-4xl font-semibold tracking-tight text-[#f4f3ea] md:text-5xl">Zaytoun</span>
      </div>
      <h1 className="mt-8 max-w-[12ch] text-5xl font-semibold leading-[0.95] text-[#faf8ee] md:text-7xl">{title}</h1>
      <p className="mt-3 text-lg text-[#d8dfcb] md:text-2xl">{subtitle}</p>
    </header>
  );
}
