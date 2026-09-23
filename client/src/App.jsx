import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, Navigate } from 'react-router-dom';
import Home from './pages/Home';
import SinglePlayer from './pages/SinglePlayer';

const PAGE_TITLES = {
  zh: '二刺猿笑传之猜猜呗',
  en: 'Anime Character Guessr'
};

function AppRoutes() {
  const location = useLocation();

  useEffect(() => {
    const isEnglish = location.pathname === '/en' || new URLSearchParams(location.search).get('lang') === 'en';
    document.title = isEnglish ? PAGE_TITLES.en : PAGE_TITLES.zh;
  }, [location.pathname, location.search]);

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/en" element={<Home locale="en" />} />
      <Route path="/singleplayer" element={<SinglePlayer />} />
      {/* 每日挑战：复用单人模式的引擎，答案由日期种子决定 */}
      <Route path="/daily" element={<SinglePlayer daily />} />
      {/* 多人联机依赖自建游戏服务器，静态部署（GitHub Pages）不含后端，故整体下线并重定向回首页 */}
      <Route path="/multiplayer" element={<Navigate to="/" replace />} />
      <Route path="/multiplayer/:roomId" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <Router basename={import.meta.env.BASE_URL}>
      <AppRoutes />
    </Router>
  );
}

export default App;
