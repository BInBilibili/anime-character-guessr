# tools/localize — 把 Bangumi 数据搬进仓库的抓取流水线

这些脚本用于生成本仓库随包分发的静态资源与数据：

- `client/public/chars/<shard>/<basename>.webp` — 角色立绘（宽 320px WebP）
- `client/public/covers/<shard>/<basename>.webp` — 作品封面（宽 120px WebP）
- `client/public/gamedata/*.json` — 游戏数据（含 `version.json`）
- `client/public/gamedata/indices.json` — 预设收藏目录

**前置**：Python 3.10+、`pip install requests pillow`，以及能访问 `api.bgm.tv` / `lain.bgm.tv` 的网络
（本机通常需要一个代理）。

## 环境变量

| 变量 | 含义 | 默认值 |
| --- | --- | --- |
| `ACG_REPO` | 仓库根目录（写入目标） | 本目录的上两级 |
| `ACG_WORK` | 抓取中间产物目录（raw JSONL，体积可达数百 MB，**不要提交**） | `tools/localize/_work` |
| `HTTPS_PROXY` | 抓取用代理，如 `http://127.0.0.1:7890` | 部分脚本回落到该默认值 |

## 执行顺序

```powershell
$env:ACG_REPO  = "D:\path\to\anime-character-guessr"
$env:ACG_WORK  = "D:\path\to\acg-work"
$env:HTTPS_PROXY = "http://127.0.0.1:7890"

python fetch_chars.py --workers 12        # 1. 角色详情 + 立绘（限流会失败，见第 2 步）
python retry_chars.py --workers 10 --rounds 5   # 2. 补抓限流失败项（幂等）
python fetch_data.py --phase chars        # 3. /subjects /persons
python fetch_data.py --phase subjects     # 4. /subjects/{id} 与 /subjects/{id}/characters
python patch_missing.py                   # 5. 补名单为空的作品（目录预设用）
python extract_covers.py                  # 6. 汇总封面 URL
python fetch_covers.py --workers 8        # 7. 下载封面
python fetch_indices.py                   # 8. 预设目录
python build_data.py                      # 9. 紧凑化 + version.json
```

## 注意事项（都是踩过的坑）

- **分片目录必须小写**：Windows 文件系统大小写不敏感、git `core.ignorecase=true` 只会记录首次创建的写法，
  而 GitHub Pages（Linux）大小写敏感 → 线上 404。脚本里统一 `shard = basename[-5:-3].lower()`。
- **不要用角色 id 命名图片**：图片 basename 与角色 id 不一定相同（例如角色 203 的图是 `277_crt_Y5fv`）。
- `fetch_chars.py` 并发过高（≥24）会触发限流，错误率可涨到 5%：用 `retry_chars.py` 收尾即可，失败是幂等的。
- 重新抓取后，把 `build_data.py` 里的 `DATA_CUTOFF` 改成新的抓取完成日 —— 首页显示的「数据快照日期」取自它。
- `build_data.py` 只读取 `ACG_WORK` 下的原始 JSONL，不联网；本地已有数据时可以单独重跑它（约 10 秒）。
- 生成的 `chars.json` / `subjects.json` 等文件被 git 跟踪；`_work`、`*.jsonl` 属于中间产物，不要提交。
