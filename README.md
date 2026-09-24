[中文](README.md) | [English](README.en.md)

> **本仓库是 [kennylimz/anime-character-guessr](https://github.com/kennylimz/anime-character-guessr) 的「纯静态离线化」分支。**
> 玩法与原版一致，但把**全部游戏数据、角色立绘、作品封面**都搬进了仓库，运行时不请求任何外部接口，
> 直接部署在 GitHub Pages 上即可游玩。
>
> 🎮 在线地址：**https://binbilibili.github.io/anime-character-guessr/** （建议桌面端浏览器）

## 📊 数据快照

| 项目 | 值 |
| --- | --- |
| 数据来源 | [Bangumi](https://bgm.tv/)（`api.bgm.tv` / 图片 CDN `lain.bgm.tv`） |
| 快照日期 | **2026-09-23**（抓取完成日，UTC+8；首页会显示该日期） |
| 角色 | **32,311** 个（其中 32,306 个有立绘） |
| 作品库 | **19,636** 部（可玩 17,778 部；默认预设「动画 2016–2026」为 3,302 部） |
| 角色标签 | 32,709 个角色 / 421 个唯一标签（`client/src/data/id_tags.js`，沿用上游） |
| 运行时外部请求 | **0** |

> ⚠️ 由于数据是快照，**新番新角色不会自动出现**；重新抓取见下方《数据重建流水线》。

## 🆕 本站相对上游的改动汇总

### 一、部署与可玩性（让它能在静态托管上真玩）

| 改动 | 说明 |
| --- | --- |
| GitHub Pages 工作流 | 新增 `.github/workflows/deploy-pages.yml`：build → `dist/404.html`（SPA 回退）→ `upload-pages-artifact` → `deploy-pages` |
| 子路径支持 | `client/src/App.jsx` 的 `<Router basename={import.meta.env.BASE_URL}>`；硬编码 `/assets/...` 全部改为 `import.meta.env.BASE_URL`（`WelcomePopup.jsx`、`announcements.js` 等），否则子路径下白屏/404 |
| 无后端降级 | `VITE_DISABLE_BACKEND=true` 时不请求游戏服务器：首页房间数轮询、反馈栏、`addedSubjects` 上报全部跳过 |
| CI 依赖 | workflow 用 `npm install` 而非 `npm ci`（上游 `client/package-lock.json` 与 `package.json` 不同步，`npm ci` 会报 `EUSAGE`） |

### 二、资源与数据本地化（全程只用仓库数据）

| 资源 | 规模 | 位置 |
| --- | --- | --- |
| 角色立绘 | **32,306** 张 WebP（宽 320px / q82），**304.6 MB** | `client/public/chars/<shard>/<basename>.webp` |
| 作品封面 | **19,598** 张 WebP（宽 120px / q80），**67.0 MB** | `client/public/covers/<shard>/<basename>.webp` |
| 游戏数据 | 8 个文件，**31.57 MB** | `client/public/gamedata/*.json` |
| Font Awesome 6.0.0 | 1 CSS + 4 woff2，约 350 KB | `client/public/vendor/fontawesome/` |
| Bangumi 图标 | 1 PNG，9.4 KB | `client/public/assets/bangumi-icon.png` |

- 新增本地数据层 `client/src/data/localData.js`：`bangumi.js` 的角色/作品/声优/标签/搜索全部改为读本地 JSON（`loadLocalData()` 一次性并发加载）。
- 实测线上页面：**116 个请求全部来自本站，0 个外部 hostname，0 个 Bangumi API 调用**。
- 原站的统计上报、反馈栏、排行榜依赖服务端，静态版一并跳过。

### 三、功能改动

- **每日挑战（新增）**：「单人」旁边的第二个模式。答案由日期确定性生成（域 = 本地已有立绘且热度 ≥ 300 的 673 个角色，`mulberry32(dayIndex × 2654435761) % 673`），**不需要任何预生成文件**，全服同题；连胜/完成状态只写 `localStorage`，无需登录；结算弹窗内可一键复制成绩（`🟩🟨⬜` 格子）。
- **「使用目录」本地实现**：原版本地模式会忽略 `useIndex` 静默随机出题；现在按目录内作品均匀抽题（不叠加类型/年份过滤），内置 4 个预设目录（`client/public/gamedata/indices.json`）。
- **多人联机下线**：静态托管没有游戏服务器，移除首页入口与 `/multiplayer` 路由（跳回首页），`Multiplayer.jsx` 变为死代码但保留在仓库。
- **欢迎/QQ 群弹窗不再自动弹出**（仍可从底部「公告」按钮打开）。
- **移除「启用 BGM 加速」开关**（本地数据模式不需要）。
- **补齐 2 部预设目录作品的角色名单**：`18011 英雄联盟`、`504678 摇滚乃是淑女的爱好`（原抓取批次失败导致无名单，抽到即无解）。
- 头像裁切：所有方形头像框加 `object-position: center top`（Bangumi 方形图是头部取景，本地图是竖版，居中裁会切到躯干）。

### 四、踩过的坑（上游/未来维护者值得一看）

1. **GitHub Pages 大小写敏感**：本地图片分片目录名保留原名大小写，在 Windows（不敏感）+ `core.ignorecase=true` 下只记录了首次创建的写法 → 线上约 45% 头像 404。修复：分片目录一律小写 + `git config core.ignorecase false` 重新入库。
2. **静态资源缓存**：GitHub Pages 的 CDN（Fastly）**忽略 `If-None-Match`**，`no-cache` 会导致每次加载重下 31 MB。改为 `version.json`（约 300 B，`no-cache`）发布数据 hash，数据文件用 `?v=<hash>` + `force-cache`：数据不变时二次加载 **0 字节回源**。
3. **`npm ci` 在上游会失败**：lockfile 缺 `@emnapi/core` 等条目且版本不一致。
4. **Windows bsdtar 解压非 ASCII 文件名失败**（控制台代码页 936），改用 Python `tarfile` 解包。
5. **PowerShell 脚本不要内嵌中文路径**：文件以 UTF-8 无 BOM 保存时被按 GBK 解码，`& : The term ... is not recognized`，且 `$ErrorActionPreference='Continue'` 会让 exit code 仍为 0（静默失败）。

## 🧰 数据重建流水线

抓取脚本都在 `tools/localize/`，路径由环境变量指定，可重复运行（全部支持断点续传）。
**注意**：需要能访问 Bangumi 的网络（本机需要一个可用代理，见 `HTTPS_PROXY`）。

```powershell
$env:ACG_REPO  = "<仓库路径>"
$env:ACG_WORK  = "<临时工作目录>，存放 raw JSONL，见下"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"   # 按需
```

| 顺序 | 脚本 | 作用 |
| --- | --- | --- |
| 1 | `fetch_chars.py` | 读 `id_tags.js` 的角色 id → `/v0/characters/{id}` + 立绘转 WebP（320px/q82）→ `chars/<shard>/`、`chars_data.jsonl` |
| 2 | `retry_chars.py` | 补抓限流失败的角色（指数退避 + 抖动，幂等） |
| 3 | `fetch_data.py --phase chars` → `--phase subjects` | `/characters/{id}/subjects`、`/persons`、`/subjects/{id}`、`/subjects/{id}/characters` → `data/*.jsonl` |
| 4 | `patch_missing.py` | 补抓 `subj_chars` 为空的目录作品（如 `18011` / `504678`） |
| 5 | `extract_covers.py` | 从原始抓取结果提取封面 URL（`covers_urls.json`） |
| 6 | `fetch_covers.py` | 下载封面转 WebP（120px/q80）→ `covers/<shard>/` |
| 7 | `fetch_indices.py` | 抓预设收藏目录 → `gamedata/indices.json` |
| 8 | `build_data.py` | 紧凑化 → `gamedata/*.json` + `version.json`（含 `cutoff` 快照日期） |

> 重新抓取后请修改 `tools/localize/build_data.py` 里的 `DATA_CUTOFF`，首页显示的「数据快照日期」取自它。

<details>
<summary>本地数据文件格式</summary>

| 文件 | 结构 |
| --- | --- |
| `chars.json` | `{ cid: [name, nameCn, nameEn, gender, popularity, "shard/base", summary] }` |
| `char_subj.json` | `{ cid: [[subjectId, "主角"\|"配角", type], ...] }` |
| `char_pers.json` | `{ cid: [vaName, ...] }` |
| `subjects.json` | `{ sid: [name, nameCn, date, type, locked, score, total, metaTags[], "shard/base"\|""] }` |
| `subj_tags.json` | `{ sid: [["tag", count], ...] }` |
| `subj_chars.json` | `{ sid: [[cid, "主角"\|"配角"], ...] }` |
| `search.json` | `[ [cid, name, nameCn, nameEn, aliases[]], ... ]`（按热度降序） |
| `indices.json` | `{ indexId: { title, sids: [subjectId, ...] } }` |
| `version.json` | `{ v, cutoff, chars, subjects }`（版本戳 + 快照日期 + 规模） |

</details>

## 🚀 部署（GitHub Pages）

1. 仓库 Settings → Pages → Source 选 **GitHub Actions**。
2. push 到 `main` 即自动构建部署（`.github/workflows/deploy-pages.yml`）。
   - 环境变量：`VITE_DISABLE_BACKEND=true`、`VITE_AES_SECRET=my-secret-key`、`VITE_BGM_API_URL=https://api.bgm.tv`
   - 构建命令：`npm run build -- --base=/<仓库名>/`
3. 站点体积约 404 MB（角色立绘 304.6 + 封面 67 + 数据 31.6），仓库约 434 MB。
   GitHub Pages 站点上限 **1 GB（硬性）**、仓库建议 < 1 GB，目前都在限内，但**再加大量图片前请先看这条**。

## ⚠️ 已知限制

- **多人联机不可用**：静态托管没有游戏服务器（也是本分支有意取舍）。
- **数据是 2026-09-23 的快照**，新番新角色不会自动更新。
- **首次进入需下载约 12 MB** 数据（之后走浏览器缓存，0 字节回源）。
- 立绘是 Bangumi 原图压缩后的 320px WebP，**画质与原站有差异**；个别角色 Bangumi 本身没有图（约 1.5%）。
- 搜索建议的头像框沿用原站 40×40 方形设计，与竖版立绘的裁切效果略有出入。

## 📖 简介
二次元笑传之猜猜呗，快来弗/灯一把吧！

- 一个猜动漫角色的游戏, 建议使用桌面端浏览器游玩。
- 灵感来源 [BLAST.tv](https://blast.tv/counter-strikle), 数据来源 [Bangumi](https://bgm.tv/)。
- [国内备用网址](https://ccb.baka.website)
- 上游作者游玩群：467740403 / 开发交流群：894333602

## 📦 运行教程

### 1. 本地 npm 运行（完整版，含服务端）

分别在 `client` 和 `server` 目录下执行以下命令：
```
npm install
npm run dev
```

### 2. 只跑静态前端（本分支用法）

```
cd client
npm install
npm run dev -- --base=/anime-character-guessr/
```
生产构建：
```
npm run build -- --base=/anime-character-guessr/
```
（如需回退到在线 Bangumi API，设 `VITE_LOCAL_DATA=false`。）

### 3. docker 运行（上游完整版）

在根目录下新建env文件
```env
DOMAIN_NAME=http://[你的 IP]

MONGODB_URI=mongodb://mongo:27017/tags

CLIENT_INTERNAL_PORT=80
SERVER_INTERNAL_PORT=3000
NGINX_EXTERNAL_PORT=80

AES_SECRET=YourSuperSecretKeyChangeMe

SERVER_URL=http://[你的 IP]:3000
```
使用项目中的 `docker-compose` 文件一键运行：
```
docker-compose up --build
```
删除容器：
```
docker-compose down
```

## 🎮 游戏玩法

- 猜一个神秘动漫角色。搜索角色，然后做出猜测。
- 每次猜测后，你会获得你猜的角色的信息。
- 绿色高亮：正确或非常接近；黄色高亮：有点接近。
- "↑"：应该往高了猜；"↓"：应该往低了猜
- **每日挑战**：每天一道全服同题，最多 10 次机会，连胜记录存在本地。

## ✨ 贡献标签

- 提交外部标签PR的时候请注意！
- 素材文件分好文件夹，放到client/public/assets下。
- 标签数据可以直接放到client/public/data/extra_tags下，作者会看一下再导入。
- 本地测试新标签加载不出来？看一看有没有把条目ID放进./client/data的extra_tag_subjects.js里。

## 🙏 致谢

- 上游项目：[kennylimz/anime-character-guessr](https://github.com/kennylimz/anime-character-guessr)
- 英化项目：[vertiKarl/anime-character-guessr-english](https://github.com/vertiKarl/anime-character-guessr-english)
- 数据与图片：[Bangumi 番组计划](https://bgm.tv/)
