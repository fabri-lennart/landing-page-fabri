// ── HEADER SCROLL ──────────────────────────
const header = document.getElementById('site-header');
window.addEventListener('scroll', () => {
  header.classList.toggle('scrolled', window.scrollY > 20);
}, { passive: true });

// ── MOBILE MENU ────────────────────────────
const mobileBtn  = document.getElementById('mobile-toggle');
const mobileMenu = document.getElementById('mobile-menu');

mobileBtn.addEventListener('click', () => {
  const open = mobileMenu.classList.toggle('open');
  mobileBtn.innerHTML = open
    ? '<i class="fa-solid fa-xmark"></i>'
    : '<i class="fa-solid fa-bars"></i>';
});
document.querySelectorAll('.mob-link').forEach(l =>
  l.addEventListener('click', () => {
    mobileMenu.classList.remove('open');
    mobileBtn.innerHTML = '<i class="fa-solid fa-bars"></i>';
  })
);

// ── REVEAL ON SCROLL ───────────────────────
const revealObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.classList.add('in');
      revealObs.unobserve(e.target);
    }
  });
}, { threshold: 0.1 });
document.querySelectorAll('.reveal').forEach(el => revealObs.observe(el));

// ── LANGUAGE BARS ──────────────────────────
const langObs = new IntersectionObserver(entries => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      e.target.style.width = (parseFloat(e.target.dataset.w) * 100) + '%';
      langObs.unobserve(e.target);
    }
  });
}, { threshold: 0.3 });
document.querySelectorAll('.lang-fill').forEach(f => langObs.observe(f));

// ── STACK TABS ─────────────────────────────
const tabs   = document.querySelectorAll('.stack-tab');
const panels = document.querySelectorAll('.tab-panel');

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    panels.forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
  });
});

// ── ACTIVE NAV LINK ────────────────────────
const sections  = ['hero','about','stack','experience','contact'];
const navLinks  = document.querySelectorAll('.nav-links a');

window.addEventListener('scroll', () => {
  const y = window.scrollY + 100;
  sections.forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    if (y >= el.offsetTop && y < el.offsetTop + el.offsetHeight) {
      navLinks.forEach(a => a.classList.remove('active'));
      const a = document.querySelector(`.nav-links a[href="#${id}"]`);
      if (a) a.classList.add('active');
    }
  });
}, { passive: true });

// Init
header.classList.toggle('scrolled', window.scrollY > 20);
