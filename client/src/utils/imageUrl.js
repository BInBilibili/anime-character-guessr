import { isBgmAccelEnabled, toAccelBgmImageUrl } from './bgmApi.js';

const BGM_LAIN_MIRROR = import.meta.env.VITE_BGM_LAIN_URL || '';

// 所有角色图已固化进仓库（client/public/chars/**），默认走本地，不再请求 lain.bgm.tv。
// 设 VITE_LOCAL_CHARS=false 可退回旧的镜像/加速逻辑。
const USE_LOCAL_CHARS = import.meta.env.VITE_LOCAL_CHARS !== 'false';

const LAIN_RE = /^https?:\/\/lain\.bgm\.tv\//i;

/**
 * 由 lain.bgm.tv 图片 URL 推导仓库内本地文件路径。
 * https://lain.bgm.tv/r/400/pic/crt/l/7b/3a/1_crt_FEkJM.jpg  ->  chars/FE/1_crt_FEkJM.webp
 * 分片规则（与抓取脚本一致）：取 basename 倒数第 5~3 位这两个字符作为目录名。
 * @param {string} url
 * @returns {string|null}
 */
export function toLocalCharPath(url) {
  if (!url || !LAIN_RE.test(url)) return null;
  const path = String(url).split('?')[0];
  const file = path.substring(path.lastIndexOf('/') + 1);
  const base = file.replace(/\.[a-z0-9]+$/i, '');
  if (!base) return null;
  const raw = base.length >= 7 ? base.slice(-5, -3) : base.slice(0, 2);
  const shard = raw.replace(/[^0-9a-zA-Z]/g, '_').padEnd(2, '_').slice(0, 2).toLowerCase();
  return `chars/${shard}/${base}.webp`;
}

/**
 * 将 lain.bgm.tv 域名替换为仓库内本地图片路径、配置的镜像站地址或加速图床
 * @param {string} url - 原始图片 URL
 * @returns {string} - 替换后的 URL
 */
export function fixImageUrl(url) {
  if (!url) return url;

  if (USE_LOCAL_CHARS) {
    const local = toLocalCharPath(url);
    if (local) return `${import.meta.env.BASE_URL}${local}`;
  }

  if (BGM_LAIN_MIRROR) {
    return String(url).replace(/^https?:\/\/lain\.bgm\.tv/, BGM_LAIN_MIRROR);
  }
  if (isBgmAccelEnabled()) {
    return toAccelBgmImageUrl(url);
  }
  return url;
}
