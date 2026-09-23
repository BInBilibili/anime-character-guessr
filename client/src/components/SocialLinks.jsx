import '../styles/social.css';

const SOCIAL_TEXT = {
  zh: {
    difficultyHint: '太难了？调下难度',
    feedbackTitle: 'Bug/标签反馈',
    homeTitle: 'Home'
  },
  en: {
    difficultyHint: 'Too hard? Adjust difficulty',
    feedbackTitle: 'Feedback',
    homeTitle: 'Home'
  }
};

function SocialLinks({ onSettingsClick, onHelpClick, onFeedbackClick, showFeedbackInline = false, showSettings = true, locale = 'zh' }) {
  const text = SOCIAL_TEXT[locale] || SOCIAL_TEXT.zh;
  // 子路径部署（GitHub Pages /anime-character-guessr/）下不能用绝对路径 "/en"，
  // 否则会跳到域名根目录 404。
  const homeHref = `${import.meta.env.BASE_URL}${locale === 'en' ? 'en' : ''}`;

  return (
    <div className="social-links">
      {showSettings && (
        <>
          <div className="difficulty-hint">
            <span>{text.difficultyHint}</span>
            <div className="arrow"></div>
          </div>
          <button className="social-link settings-button" onClick={onSettingsClick}>
            <i className="fas fa-cog"></i>
          </button>
        </>
      )}
      <a href={homeHref} className="social-link" title={text.homeTitle}>
          <i className="fas fa-home"></i>
      </a>
      <button className="social-link help-button" onClick={onHelpClick}>
        <i className="fas fa-question-circle"></i>
      </button>

      {/* Inline feedback button for small screens; shown only when requested */}
      {showFeedbackInline && (
        <button
          className="social-link inline-feedback-button"
          title={text.feedbackTitle}
          onClick={onFeedbackClick}
        >
          <i className="fas fa-bug"></i>
        </button>
      )}

      <a href="https://bangumi.tv/user/725027" target="_blank" rel="noopener noreferrer" className="social-link">
        <img src={`${import.meta.env.BASE_URL}assets/bangumi-icon.png`} alt="Bangumi" className="bangumi-icon" />
      </a>
      <a href="https://github.com/kennylimz/anime-character-guessr" target="_blank" rel="noopener noreferrer" className="social-link">
        <i className="fab fa-github"></i>
      </a>
      <a href="https://space.bilibili.com/87983557" target="_blank" rel="noopener noreferrer" className="social-link">
        <i className="fa-brands fa-bilibili"></i>
      </a>
    </div>
  );
}

export default SocialLinks; 
