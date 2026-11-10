import { motion, useMotionValue, useReducedMotion, useScroll, useSpring, useTransform } from "framer-motion";
import { Play } from "lucide-react";
import { useRef } from "react";
import { AnalyticsCard, BatchCard, ClassificationCard, GradCamCard, SurfaceCard } from "./HeroCards.jsx";
import { Eyebrow, GhostButton, LimeButton } from "./primitives.jsx";
import { BRAND } from "../brand.js";

/** A soft drifting cloud made of a radial gradient (cheap to animate - no CSS blur filter). */
function Cloud({ className, duration = 40, dx = 60, delay = 0 }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      aria-hidden
      className={`pointer-events-none absolute rounded-[50%] bg-[radial-gradient(ellipse_at_center,rgba(255,255,255,0.85)_0%,rgba(255,255,255,0.35)_40%,rgba(255,255,255,0)_70%)] ${className}`}
      animate={reduce ? undefined : { x: [0, dx, 0] }}
      transition={{ duration, repeat: Infinity, ease: "easeInOut", delay }}
    />
  );
}

/** Wraps a floating card: entrance + mouse/scroll parallax by depth + idle bob. */
function Floating({ children, depth, mx, my, scrollY, className, rotate = 0, delay = 0, bob = 10 }) {
  const reduce = useReducedMotion();
  const x = useTransform(mx, (v) => v * depth * 36);
  const yMouse = useTransform(my, (v) => v * depth * 26);
  const yScroll = useTransform(scrollY, [0, 1], [0, -160 * depth]);
  const y = useTransform([yMouse, yScroll], ([a, b]) => a + b);
  return (
    <motion.div className={`absolute ${className}`} style={reduce ? undefined : { x, y, zIndex: Math.round(depth * 10) }}>
      <motion.div
        initial={{ opacity: 0, y: 50, scale: 0.92, rotate: rotate * 2 }}
        animate={{ opacity: 1, y: 0, scale: 1, rotate }}
        transition={{ duration: 1.1, delay: 0.5 + delay, ease: [0.22, 1, 0.36, 1] }}
      >
        <motion.div
          animate={reduce ? undefined : { y: [0, -bob, 0], rotate: [0, rotate > 0 ? 1 : -1, 0] }}
          transition={{ duration: 6 + depth * 3, repeat: Infinity, ease: "easeInOut", delay: delay * 2 }}
          whileHover={{ scale: 1.04, rotate: 0 }}
        >
          {children}
        </motion.div>
      </motion.div>
    </motion.div>
  );
}

export default function Hero({ data }) {
  const ref = useRef(null);
  const reduce = useReducedMotion();
  const mxRaw = useMotionValue(0), myRaw = useMotionValue(0);
  const mx = useSpring(mxRaw, { stiffness: 60, damping: 18 });
  const my = useSpring(myRaw, { stiffness: 60, damping: 18 });
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const headY = useTransform(scrollYProgress, [0, 1], [0, 120]);
  const headO = useTransform(scrollYProgress, [0, 0.7], [1, 0]);

  const onMove = (e) => {
    if (reduce) return;
    const r = ref.current.getBoundingClientRect();
    mxRaw.set((e.clientX - r.left) / r.width - 0.5);
    myRaw.set((e.clientY - r.top) / r.height - 0.5);
  };

  const { brand, overview, batch, live } = data;

  return (
    <section ref={ref} onMouseMove={onMove} id="top"
             className="relative isolate overflow-hidden bg-gradient-to-b from-[#0670B3] via-brand to-brand-electric text-white xl:min-h-[980px]">
      {/* atmosphere */}
      <div aria-hidden className="absolute inset-0 animate-gradient bg-[linear-gradient(120deg,rgba(7,91,150,0.55),rgba(22,169,245,0.0),rgba(7,91,150,0.45))]" />
      <div aria-hidden className="grid-lines mask-fade-b absolute inset-0 opacity-60" />
      <motion.div aria-hidden className="absolute left-1/2 top-[-20%] h-[900px] w-[900px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(255,255,255,0.35),rgba(255,255,255,0)_60%)]"
                  animate={reduce ? undefined : { opacity: [0.6, 1, 0.6], scale: [1, 1.06, 1] }} transition={{ duration: 9, repeat: Infinity, ease: "easeInOut" }} />
      <Cloud className="-left-40 top-28 h-56 w-[620px] opacity-70" duration={46} dx={80} />
      <Cloud className="-right-48 top-52 h-64 w-[700px] opacity-60" duration={52} dx={-90} delay={3} />
      <Cloud className="left-[18%] top-[62%] h-48 w-[560px] opacity-50" duration={40} dx={70} delay={6} />
      <Cloud className="-right-20 top-[78%] h-72 w-[820px] opacity-70" duration={58} dx={-60} delay={2} />

      {/* steel strip in perspective - real NEU-CLS images, moving like a production line */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 h-[340px] [perspective:900px]">
        <div className="absolute inset-x-[-20%] bottom-[-60px] h-[420px] origin-bottom bg-[url('/brand/strip.jpg')] bg-[length:1100px_100%] opacity-30 mix-blend-luminosity [transform:rotateX(62deg)]"
             style={{ animation: reduce ? undefined : "strip 30s linear infinite", maskImage: "linear-gradient(to top, #000 10%, transparent 85%)", WebkitMaskImage: "linear-gradient(to top, #000 10%, transparent 85%)" }} />
      </div>
      <style>{"@keyframes strip { from { background-position: 0 0 } to { background-position: 1100px 0 } }"}</style>

      {/* headline */}
      <motion.div style={reduce ? undefined : { y: headY, opacity: headO }} className="relative z-20 mx-auto flex max-w-[880px] flex-col items-center px-6 pt-36 text-center sm:pt-44">
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.7 }}>
          <Eyebrow light>{BRAND.descriptor} · {BRAND.maker}</Eyebrow>
        </motion.div>
        <motion.h1
          initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.9, delay: 0.1, ease: [0.22, 1, 0.36, 1] }}
          className="mt-6 font-display text-[42px] font-semibold leading-[0.98] tracking-[-0.04em] sm:text-6xl lg:text-[78px]"
        >
          Precision in Every<br />
          <span className="relative inline-block whitespace-nowrap text-lime">
            Inspection.
            <motion.span aria-hidden className="absolute -bottom-1 left-0 h-[6px] w-full origin-left rounded-full bg-lime/70 sm:-bottom-2"
                         initial={{ scaleX: 0 }} animate={{ scaleX: 1 }} transition={{ duration: 1, delay: 0.9, ease: [0.22, 1, 0.36, 1] }} />
          </span>
        </motion.h1>
        <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.25 }}
                  className="mt-7 max-w-2xl text-balance text-base leading-relaxed text-white/85 sm:text-lg">
          {BRAND.description}
        </motion.p>
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, delay: 0.4 }}
                    className="mt-9 flex flex-col items-center gap-3 sm:flex-row">
          <LimeButton to="/app" size="lg">Explore Platform</LimeButton>
          <GhostButton to="/app/batch" icon={Play} size="lg">View Demo</GhostButton>
        </motion.div>
      </motion.div>

      {/* floating cards - desktop: free-floating at different depths */}
      <div className="pointer-events-none absolute inset-0 z-10 mx-auto hidden max-w-[1440px] xl:block">
        <Floating depth={1} mx={mx} my={my} scrollY={scrollYProgress} rotate={-6} delay={0} className="pointer-events-auto left-[1.5%] top-[190px] w-[240px]">
          <SurfaceCard brand={brand} />
        </Floating>
        <Floating depth={0.55} mx={mx} my={my} scrollY={scrollYProgress} rotate={4} delay={0.15} className="pointer-events-auto left-[4%] top-[575px] w-[236px]">
          <ClassificationCard brand={brand} />
        </Floating>
        <Floating depth={0.9} mx={mx} my={my} scrollY={scrollYProgress} rotate={5} delay={0.08} className="pointer-events-auto right-[2%] top-[165px] w-[250px]">
          <AnalyticsCard overview={overview} live={live} />
        </Floating>
        <Floating depth={0.65} mx={mx} my={my} scrollY={scrollYProgress} rotate={-4} delay={0.22} className="pointer-events-auto right-[4%] top-[555px] w-[250px]">
          <GradCamCard />
        </Floating>
        <Floating depth={0.4} mx={mx} my={my} scrollY={scrollYProgress} rotate={0} delay={0.3} bob={6} className="pointer-events-auto left-[calc(50%-165px)] top-[730px] w-[330px]">
          <BatchCard batch={batch} live={live} />
        </Floating>
      </div>

      {/* tablet / mobile: reorganised, stacked */}
      <div className="relative z-10 mx-auto mt-14 grid max-w-3xl gap-4 px-5 pb-28 sm:grid-cols-2 xl:hidden">
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="sm:-rotate-2"><SurfaceCard brand={brand} /></motion.div>
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} className="sm:mt-8 sm:rotate-2"><AnalyticsCard overview={overview} live={live} /></motion.div>
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }} className="hidden sm:block sm:-mt-4 sm:rotate-1"><GradCamCard /></motion.div>
        <motion.div initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }} className="sm:mt-4 sm:-rotate-1"><BatchCard batch={batch} live={live} /></motion.div>
      </div>

      <div aria-hidden className="absolute inset-x-0 bottom-0 z-10 h-40 bg-gradient-to-b from-transparent to-white" />
    </section>
  );
}
