# ACUSEEK — 40-Camera Hikvision Server & Hardware Shopping List 🇪🇬

> **Target:** 40 Hikvision CCTV cameras · 2 LPR gates · 1x Mid-Range AI Server
> **Print this document and take it to your vendor. Every part has exact model numbers for easy searching.**
> **Prices are approximate for the Egypt market (2025). Fluctuate with USD/EGP exchange.**
> Check: **Sigma Computer**, **Delta Computer**, **Computer Mall (Bab El Louk)**, **Amazon.eg**, **Noon.com.eg**, **Techno 360**, **EGYPT PC**.

---

## 1. Server Components (Option 1: AMD ECC — Recommended)

> **Why AMD ECC?** Native support for **Unbuffered ECC DDR4 RAM** on standard motherboards → prevents silent data corruption on a 24/7 database server. Lower cost and power draw than the Intel alternative.

| # | Component | Exact Model to Search | Notes |
|---|---|---|---|
| 1 | **CPU** | **AMD Ryzen 9 5900X** (12C/24T, 3.7–4.8 GHz) | Best price-to-performance for AI inference. Widely available in Egypt. |
| 2 | **Motherboard** | **ASUS Pro WS X570-ACE** or **MSI X570-A PRO** | Workstation-class, **ECC Unbuffered RAM support**, PCIe 4.0 x16 for GPU |
| 3 | **RAM** | **4× Kingston KSM32ED8/16ME** (16GB DDR4-3200 ECC Unbuffered) | **Total 64 GB ECC.** Error-correcting for 24/7 reliability |
| 4 | **RAM Alt** | **4× Samsung M391A2G43BB2-CWE** (16GB DDR4-3200 ECC) | Same spec, different brand |
| 5 | **GPU** | **NVIDIA RTX 3060 12GB** Dual-Fan (MSI Ventus / ASUS Dual / Gigabyte Eagle / EVGA) | 12GB VRAM fits all 3 AI models simultaneously (see below) |
| 6 | **Boot SSD** | **Samsung 980 PRO 1TB NVMe M.2** or **WD Black SN850X** | OS + Docker images + PostgreSQL + pgvector DB |
| 7 | **Data HDD ×2** | **2× Seagate IronWolf 4TB** (ST4000VN006) | RAID-1 mirror for image/video storage (MinIO) |
| 8 | **PSU** | **Seasonic Focus GX-750** (750W 80+ Gold) or **Corsair RM750x** | Gold-rated, 10-year warranty, 1× 8-pin PCIe power for GPU |
| 9 | **CPU Cooler** | **Noctua NH-D15** or **be quiet! Dark Rock Pro 4** | 24/7 operation needs reliable cooling |
| 10 | **Case** | **Fractal Design Define 7** or **be quiet! Pure Base 500DX** | Airflow + dust filters + room for HDD bays |

> [!IMPORTANT]
> **Must be ECC (Error-Correcting)**. Search: `"DDR4 ECC Unbuffered UDIMM 16GB 3200"`. Regular gaming RAM risks silent data corruption on a 24/7 database server.
>
> **Why 12GB VRAM?** Our models loaded together: InsightFace ~2GB + OpenCLIP ~2GB + YOLOv8 ~1GB + PyTorch/ONNX overhead ~2GB = ~7GB → comfortable headroom.

---

## 2. Cameras (Hikvision — 40 Total)

### Breakdown by Zone
| Location | Qty | Camera Type |
|---|---|---|
| **Gate 1 — LPR** | 2 | Hikvision LPR ANPR Bullet |
| **Gate 2 — LPR** | 2 | Hikvision LPR ANPR Bullet |
| **Gate 1 — Overview / Face** | 2 | Hikvision Full-Color Fixed Bullet |
| **Gate 2 — Overview / Face** | 2 | Hikvision Full-Color Fixed Bullet |
| **Restricted Zones** (8 zones × 2) | 16 | Hikvision DS-2CD2646G2-IZS + DS-2CD2186G2-IS |
| **Production / Open Areas** | 14 | Hikvision DS-2CD2043G2-I + DS-2CD2047G2-LU |
| **Perimeter / Exterior** | 2 | Hikvision DS-2CD2T46G2-4I (long-range) |
| **Total** | **40** | |

### Hikvision Camera Models (Exact Part Numbers)

| # | Model | Type | Spec / Notes | Qty | Est. EGP/ea |
|---|---|---|---|---|---|
| 1 | **DS-2CD7A46G0-IZHS** | **LPR / ANPR** (Bullet) | 4MP, 8mm-80mm vari-focal, **built-in LPR/ANPR detection**, H.265, 2-way | 4 | ~9,000 |
| 2 | **DS-2CD2686G2-IZS** | **4K Full-Color** (Bullet) | 4K/8MP, AcuSense, Active Deterrence, IR + white light (gate face/overview) | 4 | ~7,500 |
| 3 | **DS-2CD2646G2-IZS** | **8MP DarkFighter** (Bullet) | 4K, AcuSense, H.265+, 2.8–12mm motorized, **restricted zones** | 8 | ~6,500 |
| 4 | **DS-2CD2186G2-IS** | **8MP DarkFighter** (Dome) | 4K, AcuSense, IR, indoor ceiling — **restricted zones / production** | 8 | ~6,000 |
| 5 | **DS-2CD2043G2-I** | **4MP AcuSense** (Bullet) | 4MP, H.265+, IR 30m, cost-effective **open areas** | 10 | ~3,800 |
| 6 | **DS-2CD2047G2-LU** | **4MP Full-Color 180°** (Bullet) | 4MP, white light, 180° wide view — **loading docks / production** | 6 | ~4,500 |
| 7 | **DS-2CD2T46G2-4I** | **4MP Long-Range IR** (Bullet) | 4MP, IR up to 120m — **perimeter / exterior** | 2 | ~5,000 |

> **LPR (ANPR) Cameras (4 units)** — Critical: These are **different** from normal cameras. They combine the image sensor + on-board LPR engine. When a plate is detected they send an **ISAPI/HTTP event** to our server (`http://192.168.10.50:8001/api/v1/lpr-event`), which triggers our gate barrier logic. Models: `DS-2CD7A46G0-IZHS` or newer `DS-2CD7A46G0-IZHS/B`.
>
> **Hikvision alternatives** — The newer **AcuSense / DeepinView** series is fully compatible. Confirm any camera supports **ISAPI** and **RTSP** and on-board ANPR HTTP push.

### Camera Power Requirements
All 40 cameras are **PoE (Power over Ethernet)** — they receive power + data over a single CAT6A cable. This means we need PoE switches (see Network section). No power adapters needed per camera.

---

## 3. Network Equipment & Power Backup

| # | Component | Exact Model | Qty | Est. EGP/ea | Total EGP |
|---|---|---|---|---|---|
| 1 | **PoE+ Switch 24-Port** | **Hikvision DS-3E1526P-EI/M** or **TP-Link TL-SG1024PE** (24-port Gigabit PoE+, 250W+) | 2 | ~9,500 | 19,000 |
| 2 | **PoE+ Switch 8-Port** (spare / future) | TP-Link TL-SG108PE | 2 | ~2,200 | 4,400 |
| 3 | **Patch Panel 24-Port** | CAT6A Shielded | 2 | ~1,600 | 3,200 |
| 4 | **CAT6A Cable** | 305m box, 100% solid bare copper, outdoor rated | 4 | ~4,200 | 16,800 |
| 5 | **Network Rack** | 12U Wall-Mount / Floor + cable management | 1 | ~4,500 | 4,500 |
| 6 | **10GbE NIC** (server) | Intel X540-T1 (10GBase-T) | 1 | ~3,000 | 3,000 |
| 7 | **UPS** | **APC Smart-UPS 2200VA (SMT2200I)** pure sine wave | 1 | ~16,000 | 16,000 |
| | | **Network & Power Subtotal** | | | **~66,900 EGP** |

> [!IMPORTANT]
> **Use CAT6A solid bare-copper.** Do not use CCA (copper-clad aluminum) — fails in Egypt's heat/dust and breaks PoE.
> **UPS must be pure sine wave** (not simulated/stepped) to protect the server PSU during factory power fluctuations.
> **48 PoE ports total** = covers 40 cameras + 8 spare for NVR uplinks or Wi-Fi APs.

---

## 4. Complete Cost Summary (Server + Cameras + Network)

| Category | Est. Cost (EGP) |
|---|---|
| Server Build (AMD ECC, 64GB ECC, RTX 3060, 2×4TB) | ~79,600 |
| 40× Hikvision Cameras (LPR + DarkFighter + AcuSense) | ~210,000 |
| Network & Power (switches, cable, rack, UPS, 10GbE) | ~66,900 |
| **GRAND TOTAL ESTIMATE** | **~356,500 EGP** |

> [!NOTE]
> This is a **mid-range budget** estimate. Actual quote varies by vendor & USD/EGP rate. Camera prices dominate — negotiate with **El Maghraby Group** (Hikvision distributor) for bulk pricing on 40 units. CCTV installation labor not included.

---

## 5. Power Consumption Estimate

| Component | Typical (W) | Peak (W) |
|---|---|---|
| Server (CPU 5900X + GPU RTX 3060 + 64GB ECC + 3 drives) | 285 | 407 |
| PoE Switches (2× 24-port handling 40 cameras) | 350 | 550 |
| Cameras (40 × ~7W PoE avg) | 280 | 320 |
| **Entire System** | **~915 W** | **~1,277 W** |

> UPS runtime at ~915W: APC Smart-UPS 2200VA ≈ **25–35 min**. Enough for graceful shutdown during outages.

---

## 6. Software Stack (All FREE & Open-Source)

### Host
| Component | Version |
|---|---|
| Ubuntu Server | 22.04 LTS |
| Docker Engine | 27.x |
| Docker Compose | v2.x |
| NVIDIA Driver | >= 535 |
| NVIDIA Container Toolkit | latest |

### Docker Services
| Service | Image |
|---|---|
| PostgreSQL + pgvector | `pgvector/pgvector:pg16` |
| Redis | `redis:7-alpine` |
| MinIO | `minio/minio:latest` |
| Mosquitto MQTT | `eclipse-mosquitto:2` |
| Nginx | `nginx:alpine` |
| Cloudflared | `cloudflare/cloudflared:latest` |
| API (our code) | FastAPI + SQLAlchemy + Celery |
| AI Engine (our code) | NVIDIA CUDA 12.1 + ONNX Runtime GPU |
| LPR Listener (our code) | Python (ISAPI digest auth) |
| Stream Processor (our code) | OpenCV/PyAV (RTSP sampling) |
| Dashboard (our code) | FastAPI + Jinja2 + HTMX |

### AI Models (Auto-Downloaded ~710 MB total)
| Model | Size | Purpose |
|---|---|---|
| InsightFace `buffalo_l` | ~320 MB | Face detection + recognition (512-d) |
| OpenCLIP `ViT-B-32` | ~340 MB | Text-to-image search embeddings (512-d) |
| YOLOv8 `yolov8m.pt` | ~50 MB | Person / vehicle / intrusion detection |

---

## 7. Where to Buy in Egypt 🇪🇬

### Computer Parts
| Store | Website | Best For |
|---|---|---|
| Sigma Computer | sigma-computer.com | GPUs, SSDs, RAM |
| Delta Computer | delta-comp.com | Full builds |
| Computer Mall | Bab El Louk, Cairo (in-person) | Parts |
| Amazon.eg | amazon.eg | HDDs, cables, peripherals |
| Noon | noon.com/egypt | General |
| Techno 360 | techno360-eg.com | Gaming/WS parts |

### Cameras & Network (Hikvision)
| Store | Website | Notes |
|---|---|---|
| El Maghraby Group | elmaghrabygroup.com | Hikvision LPR/deepinview specialist |
| Magdy Group | Enterprise CCTV | Hikvision distributor (bulk) |
| HikSafety / Security Egypt | — | Hikvision ANPR stockists |
| Techno Vision | — | Cairo CCTV dealer |

### Workstations / Servers
| Store | Website | Notes |
|---|---|---|
| Trivera Egypt | trivera.com.eg | Dell Precision / HP Z |
| Elite Technology | Enterprise | Quotes on request |
| Dell Egypt | dell.com/eg | Direct |

---

## 8. Quick Checklist Before Buying ✅

- [ ] Confirm **motherboard supports ECC Unbuffered RAM** (X570 does)
- [ ] Confirm **GPU is dual-fan** (not single-fan ITX)
- [ ] Confirm **case fits full-length GPU** (RTX 3060 ≈ 240mm)
- [ ] Confirm **PSU has 1× 8-pin PCIe** for GPU
- [ ] Confirm **UPS is pure sine wave**
- [ ] Buy **2× identical 4TB HDDs** for RAID-1
- [ ] Confirm all **40 cameras support ISAPI + RTSP + PoE**
- [ ] Confirm **LPR cameras are true on-board ANPR models** (DS-2CD7A46G0-IZHS)
- [ ] Buy **CAT6A solid bare copper** (never CCA)
- [ ] Confirm camera seller provides **bulk discount** for 40 units
- [ ] Server room has **AC** (max 25°C ambient)
- [ ] Stable internet ≥ **10 Mbps upload** for Cloudflare tunnel
