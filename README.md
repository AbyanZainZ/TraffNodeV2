# 🌐 TraffNode V2 — Dual-Engine Hybrid Passive Income Engine

> **VPS Multi-Proxy & Surfshark VPN Simultaneous Bandwidth Monetization Harvester**  
> *Port Dashboard: `8888` (Berdiri sendiri & terpisah total dari ProxyChain di port `8080`)*

TraffNode V2 adalah sistem orkestrasi otomasi server yang ditingkatkan untuk menjalankan ratusan instance **TraffMonetizer** secara **simultan (bersamaan)** 24/7 di satu VPS Linux. Sistem ini menggabungkan dua sumber koneksi secara berdampingan tanpa saling menimpa (*non-destructive dual-pool*).

---

## 🚀 Apa yang Baru di TraffNode V2?

1. **Dual-Pool Simultaneous Concurrency**:
   - Dapat menjalankan **Surfshark WireGuard VPN** dan **Custom Proxy (Public/Private)** secara bersamaan 100%.
   - Menyimpan custom proxy tidak akan menghapus node Surfshark, dan men-generate node Surfshark tidak akan menghapus custom proxy.
2. **Koleksi 925 IP Fisik Unik Surfshark**:
   - Database server diperbarui menjadi **925 server fisik WireGuard unik** (bukan sekadar 142 domain round-robin) dengan zero duplicate IP penalty.
   - Filter wilayah presisi: Global (925), United States (215), Negara Premium, Asia Pasifik, dan Eropa.
3. **Format Custom Proxy Lengkap & Auto-Detect**:
   - Mendukung format privat `host:port:user:pass` (seperti `191.96.254.138:6185:windowsproxy001:win012345`), `user:pass@host:port`, `socks5://...`, dan `http://...`.
   - Melakukan deteksi protokol otomatis HTTP CONNECT dan SOCKS5 handshake saat pengecekan kesehatan proxy.
4. **Kontrol Selektif & Master Control**:
   - `🚀 START ALL WORKERS (Total SS + PX)`
   - `▶ Start Surfshark Saja`
   - `▶ Start Custom Proxy Saja`
   - `🛑 Stop All`, `🛑 Stop SS`, `🛑 Stop PX`, `🔄 Restart All`
   - `🗑️ Bersihkan SS Pool` dan `🗑️ Bersihkan Proxy Pool`
5. **Anti-Lag Staggered Pacing (Smooth CPU & RAM Protection)**:
   - Mekanisme start bertahap asinkron dengan jeda jeda 0.6 detik antar proses.
   - Mencegah lonjakan CPU/IO VPS saat menjalankan puluhan/ratusan worker sekaligus, sehingga VPS tidak freeze/lagging.
   - Status transisi `STARTING` (badge kuning berdenyut) menuju `RUNNING` (hijau) secara real-time.
   - Pembatalan instan saat menekan Stop All jika proses start masih berjalan.
6. **Antislop Cyber UI**:
   - Memenuhi standar rasio kontras WCAG AA (≥ 4.5:1).
   - Filter pill cepat pada tabel monitoring: *Semua*, *Surfshark Saja*, *Custom Proxy Saja*, *Running*, *Offline/Error*.
   - Zero Dead Controls: semua tombol memiliki loading state, modal log interaktif, dan toast responsif.

---

## ☁️ Cara Deploy ke VPS Linux (1 Perintah)

Jalankan perintah berikut di terminal SSH VPS Anda:

```bash
git clone https://github.com/AbyanZainZ/TraffNodeV2.git /opt/traffnode && cd /opt/traffnode && sudo bash deploy_vps.sh
```

Atau jika file sudah berada di VPS:
```bash
sudo bash deploy_vps.sh
```

Buka browser Anda di:  
👉 **`http://IP_VPS:8888`**

---

## 💻 Cara Menjalankan di Localhost Windows

1. Jalankan launcher:
   ```cmd
   run_localhost.bat
   ```
2. Buka browser di:
   👉 **`http://127.0.0.1:8888`**
