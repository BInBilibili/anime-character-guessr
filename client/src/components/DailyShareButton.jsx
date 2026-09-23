import { useState } from 'react';

const SHARE_TEXT = {
  zh: { share: '复制成绩', copied: '已复制！', failed: '复制失败，请手动截图' },
  en: { share: 'Copy result', copied: 'Copied!', failed: 'Copy failed — screenshot instead' },
};

/** 每日挑战成绩分享按钮（无剧透 emoji 成绩卡） */
function DailyShareButton({ shareText, className = 'daily-bar-share', locale = 'zh' }) {
  const text = SHARE_TEXT[locale] || SHARE_TEXT.zh;
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(shareText);
      } else {
        const ta = document.createElement('textarea');
        ta.value = shareText;
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch (e) {
      console.error('复制成绩失败', e);
      alert(text.failed);
    }
  };

  return (
    <button type="button" className={className} onClick={handleCopy}>
      {copied ? text.copied : text.share}
    </button>
  );
}

export default DailyShareButton;
