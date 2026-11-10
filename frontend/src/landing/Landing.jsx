import { MotionConfig } from "framer-motion";
import { useEffect } from "react";
import Footer from "./Footer.jsx";
import Hero from "./Hero.jsx";
import Nav from "./Nav.jsx";
import { About, Applications, FinalCTA, HowItWorks, Technology, TrustStrip } from "./Sections.jsx";
import { useSiteData } from "./useSiteData.js";
import { BRAND } from "../brand.js";

/** Product website (UI.MD, branding per UPDATE.MD). The inspection console lives under /app. */
export default function Landing() {
  const data = useSiteData();
  useEffect(() => {
    document.title = `${BRAND.name} - ${BRAND.tagline}`;
    document.documentElement.style.scrollBehavior = "smooth";
    return () => { document.documentElement.style.scrollBehavior = ""; };
  }, []);

  return (
    <MotionConfig reducedMotion="user">
      <div className="site min-h-screen">
        <a href="#platform" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-full focus:bg-lime focus:px-4 focus:py-2 focus:text-brand-ink">Skip to content</a>
        <Nav />
        <main>
          <Hero data={data} />
          <TrustStrip />
          <About data={data} />
          <HowItWorks />
          <Technology data={data} />
          <Applications />
          <FinalCTA />
        </main>
        <Footer />
      </div>
    </MotionConfig>
  );
}
