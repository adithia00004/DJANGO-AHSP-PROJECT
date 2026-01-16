# Roadmap Phase 2: Commercialization & Enterprise Features

**Status**: Planning
**Target**: Q2 2026

---

## 🚀 1. Monetization (SaaS Transformation)

Transform the internal tool into a profitable SaaS product.

### A. Landing Page (The Face)
- **Tech Stack**: Static HTML (Tailwind UI) or Django Template (HomePageView).
- **Sections**: 
  - Hero with strong CTA.
  - "How it works" video.
  - Pricing Table (Free, Pro, Enterprise).
  - Testimonials/Trust badges.

### B. Payment Integration (The Engine)
- **Gateway**: Midtrans (Recommended for Indonesia).
- **Features**:
  - Virtual Account (BCA, Mandiri, BRI).
  - QRIS (GoPay, OVO).
  - Auto-verification webhook.
- **Subscription Logic**:
  - Expiry date on UserProfile.
  - Auto-limit features based on plan.

### C. Pricing Tiers Strategy
| Feature | Free | Pro (Rp 99k/mo) | Enterprise |
|---------|------|-----------------|------------|
| Projects | 1 | Unlimited | Unlimited |
| Items/Project | Max 50 | Max 2000 | Unlimited |
| Export | PDF Watermarked | PDF/Excel Clean | Custom Kop Surat |
| Gantt | Basic | Interactive | Canvas Engine |
| Users | 1 | 1 | Multi-user Team |

---

## 🎨 2. UX & Performance (The Wow Factor)

### A. Canvas Gantt Chart (Enterprise Performance)
- **Problem**: DOM-based Gantt gets slow > 1000 items.
- **Solution**: Rewrite using HTML5 Canvas API.
- **Benefit**: Smooth 60fps scrolling for 10,000+ items.
- **Library**: Custom implementation or lightweight lib (e.g., Frappe Gantt hook).

### B. Real-time Collaboration (WebSocket)
- **Tech**: Django Channels + Redis.
- **Feature**: "User A is editing Row 5" lock indicator.
- **Benefit**: Prevent overwrite conflicts in teams.

---

## 🛡️ 3. Enterprise Security

### A. Audit Logs UI
- Visualize who edited what and when.
- Essential for corporate clients.

### B. Role-Based Access Control (RBAC)
- Roles: Owner, Estimator (Edit), Viewer (Read-only).
- Granular permission per project.

---

## 🧪 4. Testing & QA Automation

### A. End-to-End (E2E) Automation
- **Tool**: Cypress or Playwright.
- **Scenario**: Simulate full user journey (Login -> Create Project -> Add Item -> Export).
- **Benefit**: Catch UI regressions automatically.

---

## 🗓️ Recommended Timeline

| Month | Focus | Deliverable |
|-------|-------|-------------|
| **Month 1** | Landing Page & Free Tier Limit | Public Launch (Beta) |
| **Month 2** | Payment Integration | First Revenue |
| **Month 3** | Canvas Gantt Prototype | Pro Plan Launch |
| **Month 4** | WebSocket Collaboration | Enterprise Plan |
