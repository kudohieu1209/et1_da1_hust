import React from 'react';

/**
 * Ảnh đại diện tròn: ảnh tải lên > emoji > chữ cái đầu trên nền gradient.
 * @param {{ avatar: { url: string, emoji: string, gradient: string }, initial: string, size?: number }} props
 */
export default function Avatar({ avatar, initial, size = 32 }) {
  const content = avatar.url ? (
    <img src={avatar.url} alt="" className="account-avatar__img" />
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
        fontSize: Math.round(size * (avatar.emoji ? 0.5 : 0.42)),
        background: avatar.url ? 'var(--bg-card)' : avatar.gradient,
      }}
    >
      {content}
    </span>
  );
}
