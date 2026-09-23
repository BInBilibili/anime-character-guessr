import DailyShareButton from './DailyShareButton';

const DAILY_BAR_TEXT = {
  zh: {
    title: '每日挑战',
    samePuzzle: '今天的题目对所有人相同',
    played: '今日已完成',
    streakLabel: n => `连胜 ${n} 天`,
    bestLabel: n => `最高连胜 ${n} 天`,
    dateLabel: d => d,
  },
  en: {
    title: 'Daily Challenge',
    samePuzzle: 'Same puzzle for everyone today',
    played: 'Done today',
    streakLabel: n => `${n} day streak`,
    bestLabel: n => `Best streak ${n}`,
    dateLabel: d => d,
  },
};

/**
 * 每日挑战状态条：日期 / 连胜 / 成绩分享。
 * 成绩卡不含剧透（只有 6 列 emoji 网格 + 用时次数）。
 */
function DailyBar({ date, streak = 0, best = 0, playedToday = false, gameEnd = false, shareText = '', locale = 'zh' }) {
  const text = DAILY_BAR_TEXT[locale] || DAILY_BAR_TEXT.zh;

  return (
    <div className="daily-bar" lang={locale === 'en' ? 'en' : 'zh-CN'}>
      <span className="daily-bar-title">
        <i className="fas fa-calendar-day" aria-hidden="true"></i> {text.title}
      </span>
      <span className="daily-bar-date">{text.dateLabel(date)}</span>
      {streak > 0 ? (
        <span className="daily-bar-streak" title={text.bestLabel(best)}>
          🔥 {text.streakLabel(streak)}
        </span>
      ) : (
        best > 0 && <span className="daily-bar-best">{text.bestLabel(best)}</span>
      )}
      {gameEnd && shareText ? (
        <DailyShareButton shareText={shareText} locale={locale} />
      ) : (
        <span className="daily-bar-hint">{playedToday ? text.played : text.samePuzzle}</span>
      )}
    </div>
  );
}

export default DailyBar;
