/**
 * 本地数据层
 * ------------------------------------------------------------------
 * 「全程只用 GitHub 仓库数据」模式的唯一数据入口。
 * 所有游戏数据来自仓库内静态文件 client/public/gamedata/*.json，
 * 运行时不请求 api.bgm.tv / lain.bgm.tv。
 *
 * 由 scripts 抓取并紧凑化生成（见 build_data.py）：
 *   chars.json      { cid: [name, nameCn, nameEn, gender, popularity, "shard/base", summary] }
 *   char_subj.json  { cid: [[subjectId, "主角"|"配角", type], ...] }
 *   char_pers.json  { cid: [vaName, ...] }
 *   subjects.json   { sid: [name, nameCn, date, type, locked, score, total, metaTags[], "shard/base"|""] }
 *                   （末项为 covers/ 下的封面路径，空串表示未收录封面）
 *   subj_tags.json  { sid: [["tag", count], ...] }
 *   subj_chars.json { sid: [[cid, "主角"|"配角"], ...] }
 *   search.json     [ [cid, name, nameCn, nameEn, aliases[]], ... ]  按 popularity 降序
 *                   （无 popularity 字段；顺序本身即热度序）
 */

const BASE = import.meta.env.BASE_URL || '/';
const DATA_BASE = `${BASE}gamedata/`;

/** 设 VITE_LOCAL_DATA=false 可整体回退到在线 Bangumi API */
export const LOCAL_DATA_ENABLED = import.meta.env.VITE_LOCAL_DATA !== 'false';

const FILES = ['chars', 'char_subj', 'char_pers', 'subjects', 'subj_tags', 'subj_chars', 'search'];

let _data = null;
let _promise = null;

export function localDataReady() {
  return _data !== null;
}

/**
 * 加载全部本地数据（只加载一次，重复调用共享同一个 Promise）
 * @param {(ratio:number, file:string)=>void} [onProgress]
 */
export function loadLocalData(onProgress) {
  if (_data) return Promise.resolve(_data);
  if (_promise) return _promise;
  _promise = (async () => {
    const out = {};
    for (let i = 0; i < FILES.length; i++) {
      const name = FILES[i];
      // 'no-cache' = always revalidate (ETag → 304 when unchanged, so it stays cheap).
      // 'force-cache' served a stale copy of these unversioned JSON URLs forever,
      // which made new data (e.g. subject covers) never show up without a hard refresh.
      const res = await fetch(`${DATA_BASE}${name}.json`, { cache: 'no-cache' });
      if (!res.ok) {
        _promise = null;
        throw new Error(`本地数据加载失败：${name}.json (HTTP ${res.status})`);
      }
      out[name] = await res.json();
      if (onProgress) onProgress((i + 1) / FILES.length, name);
    }
    _data = out;
    return out;
  })();
  return _promise;
}

function D() {
  if (!_data) throw new Error('本地数据尚未加载，请先 await loadLocalData()');
  return _data;
}

// ---------- 角色 ----------
export function localChar(id) {
  return D().chars[String(id)] || null;
}

export function localCharSubjects(id) {
  return D().char_subj[String(id)] || [];
}

export function localCharPersons(id) {
  return D().char_pers[String(id)] || [];
}

// ---------- 作品 ----------
export function localSubject(id) {
  return D().subjects[String(id)] || null;
}

export function localSubjectTags(id) {
  return D().subj_tags[String(id)] || [];
}

export function localSubjectChars(id) {
  return D().subj_chars[String(id)] || [];
}

// ---------- 图片 ----------
/** img 形如 "z1/2_crt_z1V9r"（chars/ 下的相对路径，无扩展名） */
export function localImageUrl(img) {
  if (!img) return '';
  // shard 目录统一小写：git 在 Windows 上只记录了首次出现的大小写，
  // 而 GitHub Pages 是大小写敏感的 Linux，混用会导致 404。
  // basename 必须保持原样（对应 Bangumi 的文件名）。
  const i = img.indexOf('/');
  const path = i === -1 ? img : img.slice(0, i).toLowerCase() + img.slice(i);
  return `${BASE}chars/${path}.webp`;
}

/**
 * 作品封面。cover 形如 "q2/347533_HF5CX"（covers/ 下的相对路径，无扩展名）。
 * shard 小写规则与角色图一致（Windows 大小写不敏感 vs Pages 敏感）。
 */
export function localSubjectImage(cover) {
  if (!cover) return '';
  const i = cover.indexOf('/');
  const path = i === -1 ? cover : cover.slice(0, i).toLowerCase() + cover.slice(i);
  return `${BASE}covers/${path}.webp`;
}

// ---------- 随机选题 ----------
const poolCache = new Map();

/**
 * 按「类型 + 年份」筛出作品池，按评分人数（热度代理）降序缓存。
 * 与原在线逻辑 POST /v0/search/subjects {sort:"heat"} 的 topN 语义对应。
 */
function buildPool(types, startYear, endYear) {
  const key = `${types.join(',')}|${startYear}|${endYear}`;
  if (poolCache.has(key)) return poolCache.get(key);
  const d = D();
  const pool = [];
  for (const sid in d.subjects) {
    const s = d.subjects[sid];
    const type = s[3];
    if (!types.includes(type)) continue;
    if (s[4]) continue; // locked
    // 必须有角色名单（且名单里至少有一个本地有图的角色），否则开局会白白重试
    const roster = d.subj_chars[sid];
    if (!roster || !roster.length) continue;
    const date = s[2] || '';
    const y = date ? parseInt(date.slice(0, 4), 10) : NaN;
    if (!Number.isFinite(y) || y < startYear || y > endYear) continue;
    pool.push([sid, s[6] || 0]); // rating total 作热度
  }
  pool.sort((a, b) => b[1] - a[1]);
  const ids = pool.map(p => p[0]);
  poolCache.set(key, ids);
  return ids;
}

/**
 * 从本地池随机选一个作品 id
 * @param {{types:number[], startYear:number, endYear:number, topN:number}} opts
 * @returns {string|null}
 */
export function pickRandomSubjectId({ types = [2], startYear = 1970, endYear = 2100, topN = 50 } = {}) {
  const ids = buildPool(types, startYear, endYear);
  if (!ids.length) return null;
  const n = Math.max(1, Math.min(topN, ids.length));
  return ids[Math.floor(Math.random() * n)];
}

// ---------- 搜索 ----------
/**
 * 本地角色搜索（替代 POST /v0/search/characters）
 * search.json 已按热度降序，命中结果天然按热度排序。
 * @returns {{rows:Array, hasMore:boolean}}
 */
export function searchLocalCharacters(keyword, limit = 10, offset = 0) {
  const kw = String(keyword || '').trim().toLowerCase();
  if (!kw) return { rows: [], hasMore: false };
  const idx = D().search;
  const hits = [];
  for (let i = 0; i < idx.length; i++) {
    const row = idx[i];
    const name = row[1] || '';
    const nameCn = row[2] || '';
    const nameEn = row[3] || '';
    if (
      name.toLowerCase().includes(kw) ||
      nameCn.toLowerCase().includes(kw) ||
      nameEn.toLowerCase().includes(kw)
    ) {
      hits.push(row);
      continue;
    }
    const aliases = row[4];
    if (aliases && aliases.length) {
      for (let j = 0; j < aliases.length; j++) {
        if (String(aliases[j]).toLowerCase().includes(kw)) {
          hits.push(row);
          break;
        }
      }
    }
  }
  return {
    rows: hits.slice(offset, offset + limit),
    hasMore: hits.length > offset + limit,
  };
}

/** 本地作品搜索（替代 POST /v0/search/subjects），按评分人数降序 */
export function searchLocalSubjects(keyword, limit = 50) {
  const kw = String(keyword || '').trim().toLowerCase();
  if (!kw) return [];
  const d = D();
  const hits = [];
  for (const sid in d.subjects) {
    const s = d.subjects[sid];
    const name = s[0] || '';
    const nameCn = s[1] || '';
    if (name.toLowerCase().includes(kw) || nameCn.toLowerCase().includes(kw)) {
      hits.push([sid, s[0], s[1], s[2], s[3], s[4], s[5], s[6], s[8] || '']);
    }
  }
  hits.sort((a, b) => (b[7] || 0) - (a[7] || 0));
  return hits.slice(0, limit);
}

/** 数据概览，便于调试与「数据版本」展示 */
export function localDataStats() {
  const d = D();
  return {
    characters: Object.keys(d.chars).length,
    subjects: Object.keys(d.subjects).length,
    searchRows: Array.isArray(d.search) ? d.search.length : 0,
  };
}
