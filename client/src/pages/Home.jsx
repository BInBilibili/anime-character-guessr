import { Link } from 'react-router-dom';
import { useState, useEffect } from 'react';
import '../styles/Home.css';
import WelcomePopup from '../components/WelcomePopup';
import { enableBgmAccelAfterBlock, getBgmApiUrl, hasBgmAccelUrl } from '../utils/bgmApi.js';
import { LOCAL_DATA_ENABLED } from '../data/localData.js';

const HOME_TEXT = {
  zh: {
    singleplayer: '单人',
    showAnnouncements: '公告/反馈公开',
    status: '服务状态',
    howToPlay: '玩法简介',
    repository: 'GitHub仓库',
    qqGroup: '加入QQ群',
    newToy: '作者的新玩具',
    description: '一个猜动漫/游戏角色的网站，建议使用桌面端浏览器游玩',
    inspiredBy: '灵感来源',
    dataSource: '数据来源',
    friendLinks: '其它二刺猿小游戏：',
    languageLabel: '语言',
    chinese: '中文',
    english: 'English'
  },
  en: {
    singleplayer: 'Singleplayer',
    showAnnouncements: 'Announcements/Feedback',
    dataSource: 'Data from',
    bangumi: 'Bangumi',
    tagTranslationNote: 'Some parts are not translated. Please use the translation feature of your browser.',
    languageLabel: 'Language',
    chinese: '中文',
    english: 'English'
  }
};

const Home = ({ locale = 'zh' }) => {
  const isEnglish = locale === 'en';
  const text = HOME_TEXT[locale] || HOME_TEXT.zh;
  // 欢迎/公告弹窗不再自动弹出（本地化版本无需 QQ群 / Issue 引导）。
  // 需要时仍可从底部「公告」按钮打开。
  const [showWelcomePopup, setShowWelcomePopup] = useState(false);

  useEffect(() => {
    // 本地数据模式：完全不访问 api.bgm.tv，无需探测加速
    if (LOCAL_DATA_ENABLED) return;
    // Only probe when accel is available and we are still on the official API
    if (!hasBgmAccelUrl()) return;
    const apiBaseUrl = getBgmApiUrl();
    if (!apiBaseUrl.startsWith('https://api.bgm.tv')) return;

    let mountTimeoutId;
    let nextAttemptTimeoutId;
    let fetchTimeoutId;
    let controller;
    let isAborted = false;

    const startTestWithRetry = (attempt = 0) => {
      if (isAborted) return;
      controller = new AbortController();
      fetchTimeoutId = setTimeout(() => controller.abort(), 5000);

      fetch(`https://api.bgm.tv/v0/characters/132476?t=${Date.now()}`, { 
        cache: 'no-store',
        signal: controller.signal
      })
        .then(() => {
          clearTimeout(fetchTimeoutId);
        })
        .catch(error => {
          clearTimeout(fetchTimeoutId);
          if (isAborted) return;

          const isConnectionClosed = 
            error?.name === 'AbortError' || 
            error?.message?.includes('Connection Closed') || 
            error?.code === 'ERR_CONNECTION_CLOSED' || 
            error?.code === 'ERR_CONNECTION_TIMED_OUT' ||
            String(error).includes('Connection Closed') || 
            String(error).includes('ERR_CONNECTION_CLOSED') || 
            String(error).includes('ERR_CONNECTION_TIMED_OUT') ||
            String(error).toLowerCase().includes('closed') ||
            String(error).toLowerCase().includes('timeout') ||
            String(error).toLowerCase().includes('timed out') ||
            String(error).toLowerCase().includes('failed to fetch');
          
          if (isConnectionClosed) {
            if (attempt < 3) {
              const waitTime = 1000 * Math.pow(2, attempt);
              nextAttemptTimeoutId = setTimeout(() => startTestWithRetry(attempt + 1), waitTime);
            } else {
              enableBgmAccelAfterBlock();
            }
          }
        });
    };

    mountTimeoutId = setTimeout(() => startTestWithRetry(0), 100);

    return () => {
      isAborted = true;
      clearTimeout(mountTimeoutId);
      clearTimeout(nextAttemptTimeoutId);
      clearTimeout(fetchTimeoutId);
      if (controller) controller.abort();
    };
  }, []);

  // 房间数轮询已移除：多人联机下线，静态部署没有游戏服务器。

  const handleCloseWelcomePopup = () => {
    setShowWelcomePopup(false);
  };

  if (isEnglish) {
    return (
      <div className="home-container home-container-en" lang="en" translate="no">
        <div className="language-switch" aria-label={text.languageLabel}>
          <Link to="/" className="language-option">{text.chinese}</Link>
          <Link to="/en" className="language-option active">{text.english}</Link>
        </div>

        <div className="center-block center-block-en">
          <div className="game-modes game-modes-en">
            <Link to="/singleplayer?lang=en" className="mode-button">
              <h2>{text.singleplayer}</h2>
            </Link>
          </div>
          <p className="home-data-source">
            {text.dataSource}{' '}
            <a href="https://bgm.tv/" target="_blank" rel="noopener noreferrer">
              {text.bangumi}
            </a>
          </p>
          <p className="home-tag-note">{text.tagTranslationNote}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="home-container" lang="zh-CN" translate="no">
      <div className="language-switch" aria-label={text.languageLabel}>
        <Link to="/" className="language-option active">{text.chinese}</Link>
        <Link to="/en" className="language-option">{text.english}</Link>
      </div>

      {showWelcomePopup && (
        <WelcomePopup onClose={handleCloseWelcomePopup} locale={locale} />
      )}

      <div className="center-block">
      <div className="game-modes">
        <Link to="/singleplayer" className="mode-button">
          <h2>{text.singleplayer}</h2>
        </Link>
      </div>
      </div>

      <div className="home-footer">
        <div className="button-group-grid">
          <a
            href="#"
            className="fotter-btn"
            onClick={e => { e.preventDefault(); setShowWelcomePopup(true); }}
          >
            <i className="fas fa-bullhorn" style={{marginRight: '8px'}}></i>{text.showAnnouncements}
          </a>
          <a
            href="https://status.baka.website/status/ccb"
            target="_blank"
            rel="noopener noreferrer"
            className="fotter-btn"
          >
            <i className="fas fa-server" style={{marginRight: '8px'}}></i>{text.status}
          </a>
          <a 
            href="https://www.bilibili.com/video/BV14CVRzUELs" 
            target="_blank" 
            rel="noopener noreferrer"
            className="fotter-btn"
          >
            <i className="fab fa-bilibili" style={{marginRight: '8px'}}></i>{text.howToPlay}
          </a>
          <a 
            href="https://github.com/kennylimz/anime-character-guessr" 
            target="_blank" 
            rel="noopener noreferrer"
            className="fotter-btn"
          >
            <i className="fab fa-github" style={{marginRight: '8px'}}></i>{text.repository}
          </a>
          <a 
            href="https://qm.qq.com/q/2sWbSsCwBu" 
            target="_blank" 
            rel="noopener noreferrer"
            className="fotter-btn"
          >
            <i className="fab fa-qq" style={{marginRight: '8px'}}></i>{text.qqGroup}
          </a>
          <a 
            href="https://www.bilibili.com/video/BV1MstxzgEhg/" 
            target="_blank" 
            rel="noopener noreferrer"
            className="fotter-btn"
          >
            <i className="fas fa-desktop" style={{marginRight: '8px'}}></i>{text.newToy}
          </a>
        </div>
        <p className="home-friend-links">
          {text.friendLinks}
          <a href="https://game.baka.website/" target="_blank" rel="noopener noreferrer"> BakaGame </a> &nbsp;
          <a href="https://anipeek.animaster.dpdns.org/" target="_blank" rel="noopener noreferrer"> 动漫高手一眼顶针 </a> &nbsp;
          <a href="https://decrypto.monight.dpdns.org/" target="_blank" rel="noopener noreferrer"> 动漫高手截码战 </a> &nbsp;
          <a href="https://bot.q.qq.com/s/uDo9xxV9Pq" target="_blank" rel="noopener noreferrer"> 抽抽Bot </a>
        </p>
        <p>
          {text.description}
          <br/>
          {text.inspiredBy}<a href="https://blast.tv/counter-strikle" target="_blank" rel="noopener noreferrer"> BLAST.tv </a> &nbsp;
          {text.dataSource}<a href="https://bgm.tv/" target="_blank" rel="noopener noreferrer"> Bangumi </a>
        </p>
      </div>
    </div>
  );
};

export default Home;
