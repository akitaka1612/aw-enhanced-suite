# AW Enhanced Suite

Một lớp mở rộng chạy **trên ActivityWatch gốc** để có:

- dashboard đẹp hơn, dễ đọc hơn
- phân loại hoạt động theo category/subcategory
- so sánh ngày hiện tại với ngày trước và baseline 7 ngày
- generate **ảnh báo cáo PNG hằng ngày**
- generate **Markdown report**
- hỗ trợ tận dụng dữ liệu browser watcher nếu có cài extension

> Repo này **không fork / không bundle mã nguồn ActivityWatch gốc**.  
> Trên **Linux**, script có thể tải bản chính thức của ActivityWatch.  
> Trên **macOS / Windows**, nên cài ActivityWatch chính thức trước rồi mới chạy lớp enhanced này.

## 1) Tình trạng hỗ trợ nền tảng

- **Linux**: hỗ trợ tốt nhất, có thể cài gần như 1 lệnh
- **macOS**: dùng được, nhưng nên cài app ActivityWatch chính thức (`.dmg`) trước
- **Windows**: dùng được, nhưng nên cài ActivityWatch chính thức (`.exe installer`) trước

Enhanced dashboard/report layer là Python + HTTP local nên bản thân nó khá portable; phần khác biệt chủ yếu nằm ở **cách cài/chạy ActivityWatch base app** và **autostart**.

## 2) Quick start cho bạn bè

### Linux

```bash
git clone <repo-url>
cd aw-enhanced-suite
./scripts/install.sh
./scripts/open-dashboard.sh
```

### macOS

1. Cài ActivityWatch chính thức từ GitHub releases  
2. Mở app ActivityWatch ít nhất 1 lần để nó chạy ở `localhost:5600`
3. Chạy:

```bash
git clone <repo-url>
cd aw-enhanced-suite
python3 scripts/install.py --skip-base
python3 scripts/open-dashboard.py
```

### Windows

1. Cài ActivityWatch chính thức từ GitHub releases  
2. Mở app ActivityWatch ít nhất 1 lần
3. Mở PowerShell hoặc CMD:

```powershell
git clone <repo-url>
cd aw-enhanced-suite
py -3 scripts\install.py --skip-base
py -3 scripts\open-dashboard.py
```

Generate ảnh báo cáo:

```bash
./scripts/generate-report.sh
```

Windows:

```powershell
py -3 scripts\generate-report.py
```

Sau khi cài xong trên Linux có thể gọi nhanh bằng:

```bash
awx-dashboard
awx-report
```

## 3) Cấu trúc repo

- `enhanced/`: mã Python + HTML của dashboard nâng cao
- `scripts/install.py`: installer cross-platform cho lớp enhanced
- `scripts/install-base-activitywatch.sh`: tải bản Linux mới nhất của ActivityWatch từ GitHub release chính thức
- `scripts/open-dashboard.py`: đảm bảo base + enhanced đã chạy rồi mở giao diện
- `scripts/generate-report.py`: tạo file `.md` và `.png`
- `autostart/`, `systemd/`: template nếu muốn cài tự khởi động

## 4) Yêu cầu môi trường

Yêu cầu chung:

- Python 3.10+
- Git
- ActivityWatch base app

Khuyến nghị theo nền tảng:

- Linux: `curl`, `xclip` hoặc `wl-copy`, desktop session có tray
- macOS: `pbcopy` có sẵn
- Windows: `clip.exe` có sẵn, `py -3` hoặc Python launcher

Lưu ý cho ActivityWatch base app:

- Linux: docs chính thức nói tải **Linux `.zip`** rồi chạy `aw-qt`
- macOS: docs chính thức nói tải **`.dmg`** rồi kéo app vào Applications
- Windows: docs chính thức nói chạy **`.exe installer`**

## 5) Dữ liệu được lưu ở đâu?

- Dữ liệu ActivityWatch gốc: thường ở `~/.local/share/activitywatch`
- Binary ActivityWatch: mặc định cài vào `~/.local/opt/activitywatch`
- Ảnh + markdown report: mặc định ở `~/ActivityWatchReports`

## 6) Browser watcher (optional nhưng nên có)

Nếu cài browser extension `aw-watcher-web`, dashboard sẽ hiển thị domain/title tốt hơn.

Nếu không cài extension thì dashboard vẫn chạy, chỉ là phần website/domain sẽ kém chi tiết hơn.

## 7) Tự khởi động cùng máy

```bash
./scripts/install.sh --autostart
```

Lệnh này hiện chủ yếu dành cho **Linux/XDG autostart**.

Trên macOS hãy thêm app/script vào **Login Items**.  
Trên Windows hãy thêm shortcut/script vào **Startup** hoặc Task Scheduler.

## 8) Tuỳ biến

Bạn có thể copy `.env.example` thành `.env` rồi sửa các biến như:

- `AW_INSTALL_DIR`
- `AW_BASE_URL`
- `AW_ENHANCED_PORT`
- `AW_REPORTS_DIR`
- `AW_MACOS_APP`
- `AW_WINDOWS_EXE`

## 9) Push lên GitHub

Nếu đây là repo local mới:

```bash
git init
git add .
git commit -m "Initial AW enhanced suite"
git branch -M main
git remote add origin <github-repo-url>
git push -u origin main
```

## 10) Ghi chú quan trọng

- Dashboard enhanced đọc dữ liệu **live** từ ActivityWatch gốc trên port `5600`.
- Port mặc định của dashboard enhanced là `8712`.
- Đây là lớp mở rộng local-first, không upload dữ liệu đi đâu cả.
