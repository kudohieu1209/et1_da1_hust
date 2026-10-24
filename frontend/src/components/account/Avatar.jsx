import React, { useState } from 'react';
import { DEFAULT_AVATAR_GRADIENT } from './studentSummary';

/**
 * Ảnh tải lên > emoji > chữ viết tắt tên; mặc định nền kem, chữ đỏ.
 * @param {{ avatar: { url: string, emoji: string, gradient: string }, initial: string, size?: number }} props
 */
export default function Avatar({ avatar = {}, initial = '?', size = 32 }) {
  const [failedUrl, setFailedUrl] = useState(null);
  const hasImage = avatar.url && avatar.url !== failedUrl;
  const gradient = avatar.gradient || DEFAULT_AVATAR_GRADIENT;
  const content = hasImage ? (
    <img src={avatar.url} alt="" className="account-avatar__img" onError={() => setFailedUrl(avatar.url)} />
  ) : (
    avatar.emoji || initial
  );

  return (
    <span
      className="account-avatar"
      aria-hidden="true"
      style={{
        width: size,
        height: size,
        fontSize: Math.round(size * (avatar.emoji ? 0.5 : initial.length > 1 ? 0.33 : 0.42)),
        background: hasImage ? 'var(--bg-card)' : gradient,
        color: gradient === DEFAULT_AVATAR_GRADIENT ? '#b81227' : '#fff',
      }}
    >
      {content}
    </span>
  );
}
