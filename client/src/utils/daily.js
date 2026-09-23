/**
 * 每日挑战（Daily Challenge）
 * ------------------------------------------------------------------
 * 题目「完全由日期种子生成」，不依赖任何预生成的答案表：
 *
 *   dayIndex = floor((now + 8h) / 24h)          // 固定 UTC+8，全球同一时刻换题
 *   cid      = 候选域[ mulberry32(dayIndex × 2654435761) % 候选域.length ]
 *
 * 候选域由 localData.dailyPoolIds() 现算：id_tags 的 id ∩ 本地有资料的角色 ∩ 热度门槛，
 * 排序键固定为 cid 升序 —— 顺序因此是稳定的，只有数据更新才会改变成员。
 * 所有人加载的是同一份带版本戳的 gamedata + 同一个种子 → 任何时候打开都是同一道题。
 *
 * 连胜只写 localStorage，不需要账号，服务端零参与。
 */

const TZ_OFFSET_MS = 8 * 60 * 60 * 1000; // UTC+8：中国无夏令时，偏移恒定
const DAY_MS = 24 * 60 * 60 * 1000;

/** 热度门槛。>=300 约有 673 个角色 → 约 1.8 年不重复（实测见 daily_sample.txt） */
export const DAILY_POPULARITY_MIN = 300;
export const DAILY_MAX_ATTEMPTS = 10;
const STORAGE_KEY = 'acg-daily-v1';

/** 当天序号（UTC+8 的日历天） */
export function dayIndexOf(now = Date.now()) {
  return Math.floor((now + TZ_OFFSET_MS) / DAY_MS);
}

/** dayIndex -> "2026-09-23" */
export function dateStringOf(dayIndex) {
  return new Date(dayIndex * DAY_MS - TZ_OFFSET_MS).toISOString().slice(0, 10);
}

/** mulberry32：纯 32 位整数运算，跨浏览器/跨平台逐位一致（JS 的 Math.imul 是精确的） */
export function nextU32(seed) {
  let a = (seed + 0x6d2b79f5) | 0;
  let t = Math.imul(a ^ (a >>> 15), 1 | a);
  t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
  return (t ^ (t >>> 14)) >>> 0;
}

/**
 * 从候选域里按种子取一个 id。
 * @param {number[]} domain 必须是稳定顺序的数组（dailyPoolIds 已按 cid 升序）
 * @param {number} dayIndex
 */
export function pickFromDomain(domain, dayIndex) {
  if (!domain || !domain.length) return null;
  const seed = Math.imul(dayIndex, 2654435761);
  return domain[nextU32(seed) % domain.length];
}

/**
 * 每日挑战的冻结设置。
 * 必须冻结，因为 generateFeedback() 的输出依赖 metaTags / commonTags 等字段 ——
 * 否则每个人的反馈表都不一样，成绩就没法互相比较。
 */
export const DAILY_SETTINGS = {
  startYear: 1970,
  endYear: new Date().getFullYear(),
  useSubjectPerYear: false,
  topNSubjects: 50,
  metaTags: ['', '', ''], // 动画
  useIndex: false,
  indexId: null,
  addedSubjects: [],
  mainCharacterOnly: false,
  characterNum: 6,
  maxAttempts: DAILY_MAX_ATTEMPTS,
  useHints: [],
  useImageHint: 0,
  timeLimit: null,
  subjectSearch: true,
  characterTagNum: 4,
  subjectTagNum: 4,
  commonTags: true,
};

const EMPTY_PROGRESS = { day: null, won: false, attempts: 0, streak: 0, best: 0 };

export function loadDailyProgress() {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return { ...EMPTY_PROGRESS };
    const p = JSON.parse(raw);
    return {
      day: typeof p.day === 'number' ? p.day : null,
      won: Boolean(p.won),
      attempts: Number(p.attempts) || 0,
      streak: Number(p.streak) || 0,
      best: Number(p.best) || 0,
    };
  } catch {
    return { ...EMPTY_PROGRESS };
  }
}

/** 当前连胜：只有「今天玩过」或「昨天玩过」才延续，否则显示为 0（存储不动，等下次记录时复位） */
export function currentStreak(p = loadDailyProgress(), day = dayIndexOf()) {
  if (!p || p.day === null || p.day === undefined) return 0;
  if (p.day !== day && p.day !== day - 1) return 0;
  return p.won ? p.streak || 0 : 0;
}

/**
 * 记录成绩。同一天只记一次（重玩不算），返回新的进度记录。
 * @param {{day:number, won:boolean, attempts:number}} result
 */
export function recordDailyResult({ day, won, attempts }) {
  const prev = loadDailyProgress();
  if (prev.day === day) return prev; // 今天已记录过
  const continues = prev.day === day - 1 && prev.won;
  const streak = won ? (continues ? prev.streak + 1 : 1) : 0;
  const next = {
    day,
    won: Boolean(won),
    attempts: Number(attempts) || 0,
    streak,
    best: Math.max(prev.best || 0, streak),
  };
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  } catch {
    /* 隐私模式等场景写入失败，忽略 */
  }
  return next;
}

// '=' / 'yes' = 完全一致；方向箭头 = 接近；其余 = 不一致
const CELL = { '=': '🟩', yes: '🟩', '++': '🟨', '--': '🟨', '+': '🟨', '-': '🟨' };
const emoji = (fb) => CELL[fb] || '⬜';

/**
 * 无剧透成绩卡（6 列：性别 / 热度 / 评分 / 作品数 / 最晚 / 最早）
 * @param {{day:number, won:boolean, attempts:number, rows:Array, streak:number, url?:string}} o
 */
export function dailyShareText({ day, won, attempts, rows = [], streak = 0, url = '' }) {
  const head = `动漫角色猜猜呗 · 每日挑战 ${dateStringOf(day)}`;
  const result = won ? `✅ 第 ${attempts}/${DAILY_MAX_ATTEMPTS} 次猜中` : `❌ 未猜出`;
  const grid = rows
    .map(r =>
      [
        r.genderFeedback,
        r.popularityFeedback,
        r.ratingFeedback,
        r.appearancesCountFeedback,
        r.latestAppearanceFeedback,
        r.earliestAppearanceFeedback,
      ]
        .map(emoji)
        .join('')
    )
    .join('\n');
  const streakLine = streak > 0 ? `🔥 连胜 ${streak} 天` : '';
  return [head, result, '', grid, '', streakLine, url].filter(s => s !== '').join('\n');
}
