import { useEffect, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowDown, ArrowRight, ArrowUpRight, BookOpen, Building2, CalendarDays, Check,
  CircleHelp, Compass, GraduationCap, Landmark, Library, Mail, Newspaper,
  MapPin, Menu, Microscope, Phone, ShieldCheck, Sparkles, Users, X,
} from "lucide-react";
import { college, courses } from "./config";
import { api, clearToken, saveToken } from "./api";
import type { AdminFaculty, AdminUser, Application, FacultyMember, Program, UpdateItem, User } from "./api";

const mainLinks = [
  { label: "About", to: "/about" },
  { label: "Academics", to: "/academics" },
  { label: "Admissions", to: "/admissions" },
  { label: "Campus", to: "/campus" },
  { label: "News & Events", to: "/news" },
];

function PageMetadata() {
  const location = useLocation();
  useEffect(() => {
    const titles: Record<string, string> = {
      "/": "Home",
      "/about": "About",
      "/academics": "Academics",
      "/admissions": "Admissions",
      "/faculty": "Faculty",
      "/campus": "Campus",
      "/careers": "Careers",
      "/news": "News & Events",
      "/policies": "Policies & Resources",
      "/contact": "Contact",
      "/login": "Portal Sign In",
      "/register": "Applicant Registration",
      "/verify-email": "Verify Email",
      "/forgot-password": "Recover Account",
      "/reset-password": "Reset Password",
      "/portal": "Applicant Portal",
      "/portal/student": "Student Portal",
      "/portal/faculty": "Faculty Portal",
      "/admin": "Administrator Sign In",
      "/admin/dashboard": "Administration",
    };
    const pageTitle = titles[location.pathname] ?? "Page Not Found";
    document.title = `${pageTitle} | ${college.name}`;
    document.querySelector('meta[name="description"]')?.setAttribute(
      "content",
      `${pageTitle} information from ${college.name}. Institutional details should be verified before publication.`,
    );
    document.querySelector('meta[name="robots"]')?.setAttribute(
      "content",
      location.pathname.startsWith("/portal") || location.pathname.startsWith("/admin") || location.pathname === "/login" || location.pathname === "/verify-email" || location.pathname === "/reset-password" || location.pathname === "/forgot-password" || location.pathname === "/resend-verification"
        ? "noindex, nofollow"
        : "index, follow",
    );
    if (location.pathname === "/verify-email" || location.pathname === "/reset-password") {
      document.querySelector('meta[name="referrer"]')?.setAttribute("content", "no-referrer");
    } else {
      document.querySelector('meta[name="referrer"]')?.setAttribute("content", "strict-origin-when-cross-origin");
    }
  }, [location.pathname]);
  return null;
}

function Logo() {
  return <Link className="brand" to="/" aria-label={`${college.name} home`}>
    <span className="brand-mark"><img src={college.logo} alt="" /></span>
    <span className="brand-text">{college.name}<small>LEARN · DISCOVER · LEAD</small></span>
  </Link>;
}

function Header() {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  return <>
    <div className="announcement"><span>Admissions information for {college.applicationTerm}</span><Link to="/admissions">Explore the process <ArrowRight size={14} /></Link></div>
    <header className="site-header">
      <div className="nav-shell container">
        <Logo />
        <button className="menu-toggle" onClick={() => setOpen(!open)} aria-label={open ? "Close navigation" : "Open navigation"} aria-expanded={open}>
          {open ? <X size={21} /> : <Menu size={21} />}
        </button>
        <nav className={`main-nav ${open ? "is-open" : ""}`} aria-label="Main navigation">
          {mainLinks.map((item) => <NavLink key={item.to} to={item.to} onClick={() => setOpen(false)}>{item.label}</NavLink>)}
          <Link className="mobile-nav-link" to="/contact" onClick={() => setOpen(false)}>Contact</Link>
          <Link className="mobile-nav-link" to="/login" onClick={() => setOpen(false)}>Portal sign in</Link>
        </nav>
        <div className="nav-actions">
          <Link className="portal-link" to="/login">Portal sign in <ArrowUpRight size={14} /></Link>
          <Link className="button button-small" to="/admissions">Apply now <ArrowRight size={15} /></Link>
        </div>
      </div>
    </header>
    {location.pathname !== "/" && <div className="route-progress" aria-hidden="true" />}
  </>;
}

function Footer() {
  return <footer className="site-footer">
    <div className="container footer-main">
      <div className="footer-about"><Logo /><p>A place to learn with purpose, discover new possibilities, and shape what comes next.</p><span className="placeholder-note">Institutional details shown here are placeholders pending official confirmation.</span></div>
      <div className="footer-column"><strong>Explore</strong><Link to="/about">About the college</Link><Link to="/academics">Programs</Link><Link to="/faculty">Faculty directory</Link><Link to="/campus">Campus & facilities</Link></div>
      <div className="footer-column"><strong>Information</strong><Link to="/admissions">Admissions</Link><Link to="/careers">Careers & placements</Link><Link to="/news">News & events</Link><Link to="/policies">Policies & resources</Link></div>
      <div className="footer-column"><strong>Contact</strong><a href={`mailto:${college.email}`}><Mail size={14} />{college.email}</a><a href={`tel:${college.phone}`}><Phone size={14} />{college.phone}</a><span><MapPin size={14} />{college.address}</span></div>
    </div>
    <div className="container footer-bottom"><span>© {new Date().getFullYear()} {college.name}. Institutional information requires verification before publication.</span><Link to="/policies">Privacy · Accessibility · Terms</Link></div>
  </footer>;
}

function PageFrame({ children }: { children: React.ReactNode }) {
  return <><Header />{children}<Footer /></>;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return <span className="eyebrow"><span />{children}</span>;
}

function ProgramCards({ fallback }: { fallback: typeof courses }) {
  const [programs, setPrograms] = useState<Program[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.programs()
      .then(setPrograms)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Program information is unavailable."))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <p className="loading-state" role="status" aria-live="polite">Loading programs…</p>;
  if (error) return <div><p className="form-error" role="status">Live program information is unavailable ({error}). Verify the API is running before relying on course details.</p><div className="course-grid">{fallback.map((course, index) => <article className="course-card" key={course.name}><div className={`course-symbol symbol-${index}`} aria-hidden="true">{course.icon}</div><span className="card-kicker">SAMPLE · {course.school}</span><h3>{course.name}</h3><p>{course.description}</p><span className="sample-label">Illustrative content — verify before publication</span></article>)}</div></div>;
  if (!programs.length) return <EmptyState icon={<BookOpen />} title="Programs will appear here" text="No published academic programs are available yet." />;
  return <div className="course-grid">{programs.map((program, index) => <article className="course-card" key={program.id}><div className={`course-symbol symbol-${index % 3}`} aria-hidden="true">{index + 1}</div><span className="card-kicker">{program.level}</span><h3>{program.name}</h3><p>{program.description}</p><span className="course-link">Program details <ArrowUpRight size={15} /></span></article>)}</div>;
}

function PublicUpdates() {
  const [items, setItems] = useState<UpdateItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    Promise.allSettled([api.news(), api.notices(), api.events()])
      .then((results) => {
        const [newsResult, noticesResult, eventsResult] = results;
        const newsItems = newsResult.status === "fulfilled" ? newsResult.value : [];
        const noticeItems = noticesResult.status === "fulfilled" ? noticesResult.value : [];
        const eventItems = eventsResult.status === "fulfilled" ? eventsResult.value : [];
        const news = newsItems.map((item) => ({ ...item, category: `NEWS · ${item.category}`, date: item.published_at ?? item.created_at ?? "" }));
        const noticesList = noticeItems.map((item) => ({ ...item, category: `NOTICE · ${item.category}`, date: item.created_at ?? "" }));
        const eventsList = eventItems.map((item) => ({ ...item, category: "EVENT", date: item.starts_at ?? "" }));
        setItems([...news, ...noticesList, ...eventsList].sort((a, b) => Date.parse(b.date) - Date.parse(a.date)).slice(0, 3));
        const failures = results.flatMap((result) => result.status === "rejected"
          ? [result.reason instanceof Error ? result.reason.message : "An updates service is unavailable."]
          : []);
        setError([...new Set(failures)].join(" "));
      })
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <div className="container"><p className="loading-state" role="status" aria-live="polite">Loading news and events…</p></div>;
  if (error && !items.length) return <div className="container"><p className="form-error" role="status">Live news and notices are unavailable ({error}).</p></div>;
  if (!items.length) return <div className="container"><EmptyState icon={<Newspaper />} title="News and events will appear here" text="No current published updates are available." /></div>;
  return <>{error && <div className="container"><p className="form-error" role="status">Some live news and notices are unavailable ({error}). Showing the updates that loaded successfully.</p></div>}<div className="container notice-grid">{items.map((item) => <article className="notice-card" key={`${item.category}-${item.id}`}><div className="notice-meta"><span>{item.category}</span><span><CalendarDays size={13} />{item.date ? new Date(item.date).toLocaleDateString() : "Date not set"}</span></div><h3>{item.title}</h3><p>{item.body}</p><Link to="/news" aria-label={`Read more: ${item.title}`}><ArrowUpRight size={16} /></Link></article>)}</div></>;
}

function FacultyDirectory() {
  const [members, setMembers] = useState<FacultyMember[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    api.faculty()
      .then(setMembers)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Faculty directory is unavailable."))
      .finally(() => setLoading(false));
  }, []);
  if (loading) return <p className="loading-state" role="status" aria-live="polite">Loading approved faculty profiles…</p>;
  if (error) return <EmptyState icon={<Users />} title="Faculty directory unavailable" text={error} />;
  if (!members.length) return <EmptyState icon={<Users />} title="Faculty directory in preparation" text="Only institution-approved profiles will appear here." />;
  return <div className="facts-grid">{members.map((member) => <Fact key={member.id} icon={<GraduationCap />} title={member.name} text={[member.designation, member.qualifications, member.research_interests].filter(Boolean).join(" · ")} />)}</div>;
}

function Home() {
  return <PageFrame>
    <main>
      <section className="hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <Eyebrow>YOUR FUTURE STARTS HERE</Eyebrow>
            <h1>Big ideas.<br /><em>Bright futures.</em></h1>
            <p>Find your direction, grow your confidence, and make a difference through learning built around your ambitions.</p>
            <div className="hero-actions"><Link className="button" to="/academics">Explore programs <ArrowRight size={16} /></Link><Link className="button button-outline" to="/about">Discover our college <ArrowDown size={15} /></Link></div>
            <div className="hero-footnote"><span className="gold-dot" /> A welcoming community for curious minds.</div>
          </div>
          <div className="hero-image-wrap">
            <img className="hero-image" src="https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&amp;fit=crop&amp;w=1200&amp;q=85" alt="College students studying and talking together on campus" loading="eager" />
            <div className="hero-stamp"><span>THE PLACE<br />TO BEGIN</span><Sparkles size={20} /></div>
            <div className="hero-caption"><span className="caption-icon"><GraduationCap size={19} /></span><span><strong>Find your next step</strong><small>Explore opportunities made for you</small></span><ArrowUpRight className="caption-arrow" size={17} /></div>
          </div>
        </div>
        <div className="hero-bottom container"><span>{college.city}</span><span className="hero-bottom-line" /><span>Curiosity takes you further</span></div>
      </section>

      <section className="intro-section section-pad">
        <div className="container intro-grid">
          <div><Eyebrow>A COMMUNITY THAT OPENS DOORS</Eyebrow><h2>Start with curiosity.<br /><em>Go anywhere.</em></h2></div>
          <div className="intro-text"><p>College is more than a qualification. It’s a community, a fresh perspective, and the confidence to take your ideas further.</p><Link className="underlined-link" to="/about">Get to know us <ArrowRight size={15} /></Link></div>
        </div>
        <div className="container metric-row"><div><strong>{college.established}</strong><span>Established</span></div><div><strong>Explore</strong><span>Programs for your next chapter</span></div><div><strong>Discover</strong><span>Campus life and opportunities</span></div><div><strong>Connect</strong><span>Meet your college community</span></div></div>
      </section>

      <section className="program-section section-pad" id="programs">
        <div className="container">
          <div className="section-heading"><div><Eyebrow>ACADEMICS</Eyebrow><h2>Make your curiosity<br />your <em>calling.</em></h2></div><Link className="underlined-link" to="/academics">Explore all programs <ArrowRight size={15} /></Link></div>
          <ProgramCards fallback={courses.slice(0, 3)} />
        </div>
      </section>

      <section className="campus-feature">
        <div className="container campus-grid">
          <div className="campus-image-wrap"><img src="https://images.unsplash.com/photo-1562774053-701939374585?auto=format&amp;fit=crop&amp;w=1100&amp;q=85" alt="University campus building framed by green trees" loading="lazy" /><div className="image-label"><Building2 size={15} /> A PLACE TO BELONG</div></div>
          <div className="campus-copy"><Eyebrow>CAMPUS & COMMUNITY</Eyebrow><h2>More room to<br /><em>become you.</em></h2><p>Find your people, try something new, and make memories that last beyond the classroom. Your college experience is yours to shape.</p><Link className="button button-light" to="/campus">Explore campus life <ArrowRight size={15} /></Link><div className="campus-icons"><span><Library size={17} /> Learning spaces</span><span><Users size={17} /> Student community</span></div></div>
        </div>
      </section>

      <section className="notice-section section-pad">
        <div className="container section-heading"><div><Eyebrow>STAY IN THE KNOW</Eyebrow><h2>News & <em>notices.</em></h2></div><Link className="underlined-link" to="/news">All news & events <ArrowRight size={15} /></Link></div>
        <PublicUpdates />
      </section>

      <section className="home-cta"><div className="container cta-inner"><div><Eyebrow>YOUR NEXT CHAPTER</Eyebrow><h2>Take the first step.</h2><p>Discover what’s possible. Get in touch to find out more about courses and admissions.</p></div><div className="cta-actions"><Link className="button button-gold" to="/admissions">Admissions information <ArrowRight size={15} /></Link><Link className="cta-contact" to="/contact">Talk to our team <ArrowUpRight size={15} /></Link></div></div></section>
    </main>
  </PageFrame>;
}

const pageInfo: Record<string, { eyebrow: string; title: string; intro: string }> = {
  about: { eyebrow: "GET TO KNOW US", title: "A college built for what comes next.", intro: "Discover our story, values, and the learning community you can help shape. Institutional history and leadership details will be added after official confirmation." },
  academics: { eyebrow: "LEARN WITH PURPOSE", title: "Find a program that moves you.", intro: "Explore areas of study and build a path around your interests. Program details, eligibility, and course materials require academic approval before publication." },
  admissions: { eyebrow: "YOUR NEXT STEP", title: "Your application starts here.", intro: "Tell us a little about yourself and our admissions team can help you find the right next step. This inquiry is not an official application." },
  faculty: { eyebrow: "OUR PEOPLE", title: "Meet our academic community.", intro: "Faculty biographies and qualifications will be published here once approved by the college." },
  campus: { eyebrow: "LIFE ON CAMPUS", title: "Make yourself at home.", intro: "Explore the spaces, facilities, and student experiences that make a campus a community. Facility details are pending institutional confirmation." },
  careers: { eyebrow: "CAREERS & PLACEMENTS", title: "Build your next opportunity.", intro: "Explore career guidance, internships, and employment resources. No placement rates or employer claims are published without verified data." },
  news: { eyebrow: "WHAT'S HAPPENING", title: "The latest from campus.", intro: "Official announcements, events, and academic notices will appear here as they are published." },
  policies: { eyebrow: "POLICIES & RESOURCES", title: "Information you can rely on.", intro: "Official policy documents require institutional approval before publication. Contact the college for current authoritative copies." },
};

function InfoPage({ page }: { page: keyof typeof pageInfo }) {
  const info = pageInfo[page];
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>{info.eyebrow}</Eyebrow><h1>{info.title}</h1><p>{info.intro}</p></div></section><section className="section-pad"><div className="container page-content">
    {page === "academics" && <ProgramCards fallback={courses} />}
    {page === "admissions" && <><AdmissionForm /><div className="admissions-info"><h2>Before you apply</h2><p>Deadlines, fees, eligibility, and required documents must be confirmed by the institution before use.</p><div className="faq-grid"><details><summary>When does the next application period open?</summary><p>Dates are pending official confirmation. Contact the admissions office for current information.</p></details><details><summary>What documents will I need?</summary><p>Document requirements depend on the verified program and applicant category. The official list has not been supplied yet.</p></details><details><summary>Where can I find tuition and fees?</summary><p>Fee schedules are not published until confirmed by the institution.</p></details></div></div></>}
    {page === "news" && <PublicUpdates />}
    {page === "about" && <div className="facts-grid"><Fact icon={<Compass />} title="Our vision" text="Institutional vision statement pending official confirmation." /><Fact icon={<ShieldCheck />} title="Our values" text="Verified institutional values will be published here after approval." /><Fact icon={<GraduationCap />} title="Affiliation" text={`${college.university}.`} /><Fact icon={<Landmark />} title="Accreditation" text={`${college.accreditation}.`} /></div>}
    {page === "faculty" && <FacultyDirectory />}
    {page === "campus" && <div className="facilities-grid">{[{ label: "Library", icon: Library }, { label: "Laboratories", icon: Microscope }, { label: "Computer facilities", icon: Building2 }, { label: "Sports facilities", icon: Compass }, { label: "Hostel", icon: Building2 }, { label: "Transportation", icon: Compass }, { label: "Cafeteria", icon: Building2 }, { label: "Auditorium & accessibility", icon: Users }].map(({ label, icon: Icon }) => <div className="facility-card" key={label}><Icon size={22} /><h3>{label}</h3><p>Facility details pending official institutional confirmation.</p></div>)}</div>}
    {page === "careers" && <EmptyState icon={<GraduationCap />} title="Career resources coming soon" text="Verified internship, employer, and career-support information will be added after review by the college." />}
    {page === "policies" && <div className="policy-list">{["Privacy policy — institutional approval required", "Website terms of use — institutional approval required", "Accessibility statement — review required", "Student safety and grievance information — official details required", "Mandatory disclosures — verified documents required"].map((item) => <div key={item}><ShieldCheck size={18} /><span>{item}</span><span className="pending-pill">Pending approval</span></div>)}</div>}
  </div></section></main></PageFrame>;
}

function Fact({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <article className="fact-card"><span>{icon}</span><h3>{title}</h3><p>{text}</p></article>;
}

function EmptyState({ icon, title, text }: { icon: ReactNode; title: string; text: string }) {
  return <div className="empty-state"><span>{icon}</span><h2>{title}</h2><p>{text}</p></div>;
}

function AdmissionForm() {
  const [status, setStatus] = useState<"idle" | "sent" | "error">("idle");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await api.contact({
        name: String(form.get("name") ?? ""),
        email: String(form.get("email") ?? ""),
        interest: String(form.get("interest") ?? ""),
        message: String(form.get("message") || "Admissions information request"),
      });
      setStatus("sent");
      setError("");
      formElement.reset();
    } catch (reason) {
      setStatus("error");
      setError(reason instanceof Error ? reason.message : "The inquiry could not be sent.");
    }
  }
  return <div className="form-layout"><div><Eyebrow>REQUEST INFORMATION</Eyebrow><h2>Let’s find your<br />next step.</h2><p>Complete this short inquiry and the admissions team can follow up. Do not send sensitive documents through this form.</p><p className="sample-label">Sample contact details are configured in src/config.ts and must be replaced before launch.</p></div><form className="contact-form" onSubmit={submit}>{status === "sent" && <div className="form-success" role="status"><Check size={17} />Your inquiry was received by the college.</div>}{status === "error" && <div className="form-error" role="alert">{error}</div>}<label htmlFor="full-name">Full name <span>*</span></label><input id="full-name" name="name" autoComplete="name" required maxLength={120} /><label htmlFor="email">Email address <span>*</span></label><input id="email" name="email" type="email" autoComplete="email" required maxLength={254} /><label htmlFor="interest">Area of interest</label><select id="interest" name="interest" defaultValue=""><option value="">Select an area</option>{courses.map((course) => <option key={course.name}>{course.name}</option>)}</select><label htmlFor="message">How can we help?</label><textarea id="message" name="message" rows={4} maxLength={2000} /><button className="button" type="submit">Send an inquiry <ArrowRight size={15} /></button><small>Submitting an inquiry does not create an official application.</small></form></div>;
}

function ContactPage() {
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>WE'RE HERE TO HELP</Eyebrow><h1>Let’s start a conversation.</h1><p>Reach out to ask about the college, programs, or admissions. Contact information below is sample data and must be verified.</p></div></section><section className="section-pad"><div className="container"><div className="contact-layout"><div className="contact-details"><Fact icon={<Mail />} title="Email" text={college.email} /><Fact icon={<Phone />} title="Phone" text={college.phone} /><Fact icon={<MapPin />} title="Address" text={college.address} /></div><AdmissionForm /></div>{college.mapEmbedUrl ? <iframe className="map-frame" src={college.mapEmbedUrl} title="College campus map" loading="lazy" referrerPolicy="no-referrer-when-downgrade" /> : <p className="sample-label map-pending">Map embed is not configured. Add a verified map URL to src/config.ts before publication.</p>}</div></section></main></PageFrame>;
}

function PortalPage({ admin = false }: { admin?: boolean }) {
  const [message, setMessage] = useState("");
  const navigate = useNavigate();
  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const token = await api.login(String(form.get("email")), String(form.get("password")));
      saveToken(token.access_token);
      const user = await api.me();
      if (admin && !user.roles.includes("admin")) {
        clearToken();
        throw new Error("This account does not have administrator access.");
      }
      navigate(user.roles.includes("admin") ? "/admin/dashboard" : user.roles.includes("faculty") ? "/portal/faculty" : user.roles.includes("student") ? "/portal/student" : "/portal");
    } catch (reason) {
      clearToken();
      setMessage(reason instanceof Error ? reason.message : "Sign in failed.");
    }
  }
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>{admin ? "ADMINISTRATION" : "STUDENT & APPLICANT PORTAL"}</Eyebrow><h1>{admin ? "Administrative sign in." : "Welcome back."}</h1><p>{admin ? "Administrator accounts must be provisioned by an authorized operator. Public self-registration cannot grant administrative permissions." : "Sign in to access your applicant or student workspace."}</p></div></section><section className="section-pad"><div className="container login-layout"><form className="contact-form login-form" onSubmit={signIn}><label htmlFor="login-email">Email address</label><input id="login-email" name="email" type="email" autoComplete="username" required maxLength={254} /><label htmlFor="login-password">Password</label><input id="login-password" name="password" type="password" autoComplete="current-password" required /><button className="button" type="submit">Sign in <ArrowRight size={15} /></button>{message && <p className="form-error" role="alert">{message}</p>}{!admin && <><Link className="underlined-link" to="/register">Create applicant account</Link><Link className="underlined-link" to="/forgot-password">Forgot your password?</Link><Link className="underlined-link" to="/resend-verification">Resend verification email</Link></>}</form><aside className="portal-aside"><CircleHelp size={24} /><h3>Need help?</h3><p>For account access assistance, please contact the college using the official contact details after they have been confirmed.</p><Link to="/contact">Contact the college <ArrowRight size={14} /></Link></aside></div></section></main></PageFrame>;
}

function RegisterPage() {
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  async function register(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.register(String(form.get("name")), String(form.get("email")), String(form.get("password")));
      setMessage("If this address can be registered, a verification email will be sent. Verify your email before signing in.");
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Account creation failed.");
    }
  }
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>APPLICANT ACCESS</Eyebrow><h1>Create an applicant account.</h1><p>Registration creates an applicant account only. Administrator accounts are provisioned separately by an authorized operator.</p></div></section><section className="section-pad"><div className="container login-layout"><form className="contact-form" onSubmit={register}>{message && <div className="form-success" role="status">{message}</div>}{error && <div className="form-error" role="alert">{error}</div>}<label htmlFor="register-name">Full name</label><input id="register-name" name="name" autoComplete="name" required minLength={2} maxLength={120} /><label htmlFor="register-email">Email address</label><input id="register-email" name="email" type="email" autoComplete="email" required maxLength={254} /><label htmlFor="register-password">Password (at least 12 characters)</label><input id="register-password" name="password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} /><button className="button" type="submit">Create applicant account <ArrowRight size={15} /></button></form></div></section></main></PageFrame>;
}

function VerifyEmailPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") ?? "";
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  async function verify() {
    try {
      const result = await api.verifyEmail(token);
      setStatus(result.message);
      setError("");
      navigate("/verify-email", { replace: true });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Email verification failed."); }
  }
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>ACCOUNT VERIFICATION</Eyebrow><h1>Verify your email address.</h1><p>Use the one-time link from your account email. Verification happens only after you confirm below.</p></div></section><section className="section-pad"><div className="container login-layout"><div className="contact-form">{status && <p className="form-success" role="status">{status}</p>}{error && <p className="form-error" role="alert">{error}</p>}{token ? <button className="button" onClick={verify}>Verify email <Check size={15} /></button> : <p className="form-error" role="alert">The verification link is missing its token.</p>}<Link className="underlined-link" to="/login">Return to sign in</Link></div></div></section></main></PageFrame>;
}

function RecoveryForm({ mode }: { mode: "request" | "resend" }) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const email = String(new FormData(form).get("email"));
    try {
      const result = mode === "request" ? await api.requestPasswordReset(email) : await api.resendVerification(email);
      setMessage(result.message);
      setError("");
      form.reset();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "The request could not be completed."); }
  }
  const verification = mode === "resend";
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>{verification ? "EMAIL VERIFICATION" : "ACCOUNT RECOVERY"}</Eyebrow><h1>{verification ? "Request a new verification email." : "Reset your password."}</h1><p>Enter your account email. The response is the same whether or not an eligible account exists.</p></div></section><section className="section-pad"><div className="container login-layout"><form className="contact-form" onSubmit={submit}>{message && <p className="form-success" role="status">{message}</p>}{error && <p className="form-error" role="alert">{error}</p>}<label htmlFor="recovery-email">Email address</label><input id="recovery-email" name="email" type="email" autoComplete="email" required maxLength={254} /><button className="button">{verification ? "Send verification email" : "Send password reset link"} <ArrowRight size={15} /></button><Link className="underlined-link" to="/login">Return to sign in</Link></form></div></section></main></PageFrame>;
}

function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") ?? "";
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const password = String(form.get("password"));
    if (password !== String(form.get("confirm"))) {
      setError("Passwords do not match.");
      return;
    }
    try {
      const result = await api.resetPassword(token, password);
      setMessage(result.message);
      setError("");
      formElement.reset();
      navigate("/reset-password", { replace: true });
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Password reset failed."); }
  }
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>ACCOUNT RECOVERY</Eyebrow><h1>Choose a new password.</h1><p>Password-reset links expire after 30 minutes and can be used once.</p></div></section><section className="section-pad"><div className="container login-layout"><form className="contact-form" onSubmit={submit}>{message && <p className="form-success" role="status">{message}</p>}{error && <p className="form-error" role="alert">{error}</p>}{!token && <p className="form-error" role="alert">The password-reset link is missing its token.</p>}<label htmlFor="new-password">New password (at least 12 characters)</label><input id="new-password" name="password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} /><label htmlFor="confirm-password">Confirm new password</label><input id="confirm-password" name="confirm" type="password" autoComplete="new-password" required minLength={12} maxLength={128} /><button className="button" disabled={!token}>Reset password <ArrowRight size={15} /></button><Link className="underlined-link" to="/login">Return to sign in</Link></form></div></section></main></PageFrame>;
}

function ApplicantDashboard() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  useEffect(() => {
    Promise.all([api.applications(), api.programs()]).then(([apps, items]) => {
      setApplications(apps);
      setPrograms(items);
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load your workspace."))
      .finally(() => setLoading(false));
  }, []);
  async function apply(programId: number) {
    try {
      const application = await api.createApplication(programId);
      setApplications((current) => [application, ...current]);
      setMessage(`Draft ${application.reference} created. Complete submission with the admissions office.`);
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Application could not be created."); }
  }
  async function submitApplication(id: number) {
    try {
      const submitted = await api.submitApplication(id);
      setApplications((current) => current.map((item) => item.id === id ? submitted : item));
      setMessage(`Application ${submitted.reference} submitted.`);
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Application could not be submitted."); }
  }
  async function uploadDocument(id: number, file: File | undefined) {
    if (!file) return;
    try {
      await api.uploadApplicationDocument(id, file);
      setMessage("Document uploaded to your draft application.");
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Document could not be uploaded."); }
  }
  function signOut() { clearToken(); navigate("/login"); }
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>YOUR WORKSPACE</Eyebrow><h1>Applicant dashboard.</h1><p>View your application references and access published program information. No academic results or attendance are displayed.</p></div></section><section className="section-pad"><div className="container dashboard"><div className="dashboard-heading"><h2>Your applications</h2><button className="button button-outline" onClick={signOut}>Sign out</button></div>{message && <div className="form-success" role="status">{message}</div>}{error && <div className="form-error" role="alert">{error}</div>}{loading ? <p className="loading-state" role="status" aria-live="polite">Loading your applications…</p> : applications.length ? <div className="application-list">{applications.map((application) => <article className="application-card" key={application.reference}><div><strong>{application.reference}</strong><span>Program ID {application.program_id} · {application.status}</span></div>{application.status === "draft" && <div className="application-actions"><label htmlFor={`doc-${application.id}`}>Upload PDF/JPEG/PNG (5 MB max)</label><input id={`doc-${application.id}`} type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" onChange={(event) => uploadDocument(application.id, event.currentTarget.files?.[0])} /><button className="button" onClick={() => submitApplication(application.id)}>Submit application <ArrowRight size={14} /></button></div>}<small>Started {new Date(application.created_at).toLocaleDateString()}</small></article>)}</div> : <p className="muted-copy">No applications have been started.</p>}<h2 className="dashboard-subhead">Published programs</h2>{loading ? <p className="loading-state" role="status" aria-live="polite">Loading published programs…</p> : programs.length ? <div className="course-grid">{programs.map((program) => <article className="course-card" key={program.id}><span className="card-kicker">{program.level}</span><h3>{program.name}</h3><p>{program.description}</p><button className="underlined-link" onClick={() => apply(program.id)}>Start an application <ArrowRight size={15} /></button></article>)}</div> : <p className="muted-copy">No published programs are available.</p>}</div></section></main></PageFrame>;
}

function AdminDashboard() {
  const [user, setUser] = useState<User | null>(null);
  const [apps, setApps] = useState<Application[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const navigate = useNavigate();
  useEffect(() => {
    Promise.all([api.me(), api.adminApplications()]).then(([currentUser, items]) => {
      if (!currentUser.roles.includes("admin")) throw new Error("This account does not have administrator access.");
      setUser(currentUser);
      setApps(items);
    }).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Could not load administration workspace.");
      clearToken();
    });
  }, []);
  async function updateStatus(id: number, status: string) {
    try {
      const updated = await api.setApplicationStatus(id, status);
      setApps((items) => items.map((item) => item.reference === updated.reference ? updated : item));
      setNotice(`Application ${updated.reference} updated.`);
      setError("");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Status update failed."); }
  }
  function signOut() { clearToken(); navigate("/admin"); }
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>ADMINISTRATION</Eyebrow><h1>Content & admissions.</h1><p>{user ? `Signed in as ${user.email}.` : "Loading administrator workspace…"}</p></div></section><section className="section-pad"><div className="container dashboard"><div className="dashboard-heading"><h2>Admission applications</h2><button className="button button-outline" onClick={signOut}>Sign out</button></div>{error && <div className="form-error" role="alert">{error}</div>}{notice && <div className="form-success" role="status">{notice}</div>}{apps.length ? <div className="table-wrap"><table><thead><tr><th>Reference</th><th>Program ID</th><th>Status</th><th>Action</th></tr></thead><tbody>{apps.map((application) => <tr key={application.reference}><td>{application.reference}</td><td>{application.program_id}</td><td>{application.status}</td><td><select aria-label={`Update status for ${application.reference}`} value={application.status} onChange={(event) => updateStatus(application.id, event.target.value)}><option value="draft">Draft</option><option value="submitted">Submitted</option><option value="under_review">Under review</option><option value="accepted">Accepted</option><option value="rejected">Rejected</option><option value="withdrawn">Withdrawn</option></select></td></tr>)}</tbody></table></div> : <p className="muted-copy">No applications are available, or you do not have administrator access.</p>}<AdminProgramForm onCreated={() => setNotice("Program created and published.")} onError={setError} /><AdminContentForms onCreated={setNotice} onError={setError} /><AdminUserManagement onError={setError} onNotice={setNotice} /></div></section></main></PageFrame>;
}

function AdminContentForms({ onCreated, onError }: { onCreated: (message: string) => void; onError: (message: string) => void }) {
  async function createNews(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    try {
      await api.createNews({
        title: String(values.get("news-title")),
        slug: String(values.get("news-slug")).trim().toLowerCase(),
        category: String(values.get("news-category")),
        body: String(values.get("news-body")),
        published: values.get("news-published") === "on",
      });
      form.reset();
      onCreated("News article saved.");
    } catch (reason) { onError(reason instanceof Error ? reason.message : "News article could not be saved."); }
  }
  async function createNotice(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    try {
      await api.createNotice({
        title: String(values.get("notice-title")),
        category: String(values.get("notice-category")),
        body: String(values.get("notice-body")),
        published: values.get("notice-published") === "on",
      });
      form.reset();
      onCreated("Notice saved.");
    } catch (reason) { onError(reason instanceof Error ? reason.message : "Notice could not be saved."); }
  }
  async function createEvent(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    try {
      await api.createEvent({
        title: String(values.get("event-title")),
        description: String(values.get("event-description")),
        venue: String(values.get("event-venue")),
        starts_at: new Date(String(values.get("event-date"))).toISOString(),
        published: values.get("event-published") === "on",
      });
      form.reset();
      onCreated("Event saved.");
    } catch (reason) { onError(reason instanceof Error ? reason.message : "Event could not be saved."); }
  }
  return <section><h2 className="dashboard-subhead">Publish news, notices, and events</h2><div className="admin-content-grid">
    <form className="contact-form admin-form" onSubmit={createNews}><h3>News article</h3><label htmlFor="news-title">Title</label><input id="news-title" name="news-title" required maxLength={200} /><label htmlFor="news-slug">URL slug</label><input id="news-slug" name="news-slug" pattern="[a-z0-9]+(-[a-z0-9]+)*" required maxLength={220} /><label htmlFor="news-category">Category</label><input id="news-category" name="news-category" defaultValue="News" maxLength={60} /><label htmlFor="news-body">Article</label><textarea id="news-body" name="news-body" required maxLength={50000} rows={4} /><label className="checkbox-label"><input name="news-published" type="checkbox" /> Publish now</label><button className="button">Save news</button></form>
    <form className="contact-form admin-form" onSubmit={createNotice}><h3>Notice</h3><label htmlFor="notice-title">Title</label><input id="notice-title" name="notice-title" required maxLength={200} /><label htmlFor="notice-category">Category</label><input id="notice-category" name="notice-category" defaultValue="General" maxLength={60} /><label htmlFor="notice-body">Notice details</label><textarea id="notice-body" name="notice-body" required maxLength={10000} rows={4} /><label className="checkbox-label"><input name="notice-published" type="checkbox" /> Publish now</label><button className="button">Save notice</button></form>
    <form className="contact-form admin-form" onSubmit={createEvent}><h3>Event</h3><label htmlFor="event-title">Title</label><input id="event-title" name="event-title" required maxLength={200} /><label htmlFor="event-venue">Venue</label><input id="event-venue" name="event-venue" maxLength={200} /><label htmlFor="event-date">Start date and time</label><input id="event-date" name="event-date" type="datetime-local" required /><label htmlFor="event-description">Details</label><textarea id="event-description" name="event-description" maxLength={10000} rows={4} /><label className="checkbox-label"><input name="event-published" type="checkbox" /> Publish now</label><button className="button">Save event</button></form>
  </div></section>;
}

function AdminUserManagement({ onError, onNotice }: { onError: (message: string) => void; onNotice: (message: string) => void }) {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [faculty, setFaculty] = useState<AdminFaculty[]>([]);
  const [roles, setRoles] = useState<Record<number, string>>({});
  const [studentNumbers, setStudentNumbers] = useState<Record<number, string>>({});
  useEffect(() => {
    Promise.all([api.adminUsers(), api.adminFaculty()]).then(([userItems, facultyItems]) => {
      setUsers(userItems);
      setFaculty(facultyItems);
    }).catch((reason: unknown) => onError(reason instanceof Error ? reason.message : "Could not load user administration."));
  }, [onError]);
  async function assign(user: AdminUser) {
    const role = roles[user.id] ?? user.roles[0] ?? "applicant";
    try {
      const updated = await api.assignUserRole(user.id, role, studentNumbers[user.id] ?? "");
      setUsers((current) => current.map((item) => item.id === updated.id ? updated : item));
      onNotice(`Role updated for ${updated.email}. Administrator assignment is disabled here.`);
      if (role === "faculty") setFaculty(await api.adminFaculty());
    } catch (reason) { onError(reason instanceof Error ? reason.message : "Role could not be updated."); }
  }
  async function approve(profile: AdminFaculty) {
    try {
      await api.approveFaculty(profile.id);
      setFaculty((items) => items.map((item) => item.id === profile.id ? { ...item, approved: true } : item));
      onNotice(`Approved the profile for ${profile.name}.`);
    } catch (reason) { onError(reason instanceof Error ? reason.message : "Faculty approval failed."); }
  }
  return <><h2 className="dashboard-subhead">Manage user roles</h2><p className="muted-copy">Only institution-authorized administrators should assign roles. Administrator roles can only be provisioned by the operator setup command.</p><div className="table-wrap"><table><thead><tr><th>User</th><th>Current role</th><th>Set role</th><th>Verified student number</th><th>Action</th></tr></thead><tbody>{users.map((item) => <tr key={item.id}><td>{item.full_name}<br />{item.email}</td><td>{item.roles.join(", ")}</td><td><select disabled={item.roles.includes("admin")} aria-label={`New role for ${item.email}`} value={item.roles.includes("admin") ? "applicant" : roles[item.id] ?? item.roles[0] ?? "applicant"} onChange={(event) => setRoles((current) => ({ ...current, [item.id]: event.target.value }))}><option value="applicant">Applicant</option><option value="student">Student</option><option value="faculty">Faculty</option></select></td><td><input disabled={item.roles.includes("admin")} aria-label={`Student number for ${item.email}`} value={studentNumbers[item.id] ?? ""} onChange={(event) => setStudentNumbers((current) => ({ ...current, [item.id]: event.target.value }))} /></td><td>{item.roles.includes("admin") ? "Operator-managed" : <button className="text-button" onClick={() => assign(item)}>Save</button>}</td></tr>)}</tbody></table></div><h3 className="dashboard-subhead">Faculty profile approvals</h3>{faculty.length ? <div className="table-wrap"><table><thead><tr><th>Name</th><th>Designation</th><th>Qualifications</th><th>Approval</th></tr></thead><tbody>{faculty.map((item) => <tr key={item.id}><td>{item.name}</td><td>{item.designation || "Not supplied"}</td><td>{item.qualifications || "Not supplied"}</td><td>{item.approved ? "Approved" : <button className="text-button" onClick={() => approve(item)}>Approve profile</button>}</td></tr>)}</tbody></table></div> : <p className="muted-copy">No faculty profiles are awaiting review.</p>}</>;
}

function RoleWorkspace({ requiredRole }: { requiredRole: "student" | "faculty" }) {
  const [error, setError] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const navigate = useNavigate();
  useEffect(() => {
    api.me().then((current) => {
      if (!current.roles.includes(requiredRole)) throw new Error("This account does not have access to this workspace.");
      setUser(current);
    }).catch((reason: unknown) => {
      setError(reason instanceof Error ? reason.message : "Could not verify access.");
    });
  }, [requiredRole]);
  return <PageFrame><main><section className="page-hero"><div className="container"><Eyebrow>{requiredRole === "student" ? "STUDENT PORTAL" : "FACULTY PORTAL"}</Eyebrow><h1>{requiredRole === "student" ? "Student workspace." : "Faculty workspace."}</h1><p>{user ? `Signed in as ${user.full_name}.` : error || "Verifying access…"}</p></div></section><section className="section-pad"><div className="container"><EmptyState icon={requiredRole === "student" ? <GraduationCap /> : <Users />} title={requiredRole === "student" ? "Student information is not connected" : "Faculty course tools are not configured"} text={requiredRole === "student" ? "This portal does not display attendance, grades, or results. Those require an authorized institutional source and approved workflows." : "Course assignments, learning materials, and student information require confirmed faculty workflows and institutional integrations."} /><button className="button" onClick={() => { clearToken(); navigate("/login"); }}>Sign out</button></div></section></main></PageFrame>;
}
function AdminProgramForm({ onCreated, onError }: { onCreated: () => void; onError: (message: string) => void }) {
  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      await api.createProgram({ name: String(form.get("name")), level: String(form.get("level")), description: String(form.get("description")), published: true });
      formElement.reset();
      onCreated();
    } catch (reason) { onError(reason instanceof Error ? reason.message : "Program could not be saved."); }
  }
  return <><h2 className="dashboard-subhead">Add an academic program</h2><form className="contact-form admin-form" onSubmit={create}><label htmlFor="program-name">Program name</label><input id="program-name" name="name" required maxLength={160} /><label htmlFor="program-level">Level</label><select id="program-level" name="level"><option>Undergraduate</option><option>Postgraduate</option><option>Doctoral</option><option>Other</option></select><label htmlFor="program-description">Description</label><textarea id="program-description" name="description" rows={3} maxLength={10000} /><button className="button">Publish program <ArrowRight size={15} /></button></form></>;
}

function NotFound() {
  return <PageFrame><main className="not-found"><div className="container"><Eyebrow>PAGE NOT FOUND</Eyebrow><h1>Let’s get you back on track.</h1><Link className="button" to="/">Return home <ArrowRight size={15} /></Link></div></main></PageFrame>;
}

export default function App() {
  return <>
  <PageMetadata />
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/about" element={<InfoPage page="about" />} />
    <Route path="/academics" element={<InfoPage page="academics" />} />
    <Route path="/admissions" element={<InfoPage page="admissions" />} />
    <Route path="/faculty" element={<InfoPage page="faculty" />} />
    <Route path="/campus" element={<InfoPage page="campus" />} />
    <Route path="/careers" element={<InfoPage page="careers" />} />
    <Route path="/news" element={<InfoPage page="news" />} />
    <Route path="/policies" element={<InfoPage page="policies" />} />
    <Route path="/contact" element={<ContactPage />} />
    <Route path="/login" element={<PortalPage />} />
    <Route path="/admin" element={<PortalPage admin />} />
    <Route path="/admin/dashboard" element={<AdminDashboard />} />
    <Route path="/portal" element={<ApplicantDashboard />} />
    <Route path="/portal/student" element={<RoleWorkspace requiredRole="student" />} />
    <Route path="/portal/faculty" element={<RoleWorkspace requiredRole="faculty" />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route path="/verify-email" element={<VerifyEmailPage />} />
    <Route path="/forgot-password" element={<RecoveryForm mode="request" />} />
    <Route path="/resend-verification" element={<RecoveryForm mode="resend" />} />
    <Route path="/reset-password" element={<ResetPasswordPage />} />
    <Route path="*" element={<NotFound />} />
  </Routes>
  </>;
}
