import { isBgmAccelEnabled, toAccelBgmImageUrl } from './bgmApi.js';

const BGM_LAIN_MIRROR = import.meta.env.VITE_BGM_LAIN_URL || '';

/**
 * 将 lain.bgm.tv 域名替换为配置的镜像站地址或加速图床
 * @param {string} url - 原始图片 URL
 * @returns {string} - 替换后的 URL
 */
export function fixImageUrl(url) {
  if (!url) return url;
  if (BGM_LAIN_MIRROR) {
    return String(url).replace(/^https?:\/\/lain\.bgm\.tv/, BGM_LAIN_MIRROR);
  }
  if (isBgmAccelEnabled()) {
    return toAccelBgmImageUrl(url);
  }
  return url;
}

