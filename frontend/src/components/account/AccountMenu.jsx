import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ChevronsUpDown, Info, Moon, Settings, Sun, Upload, Users } from 'lucide-react';
import Avatar from './Avatar';
import { buildStudentSummary, formatCpa, programLabel } from './studentSummary';
import './account.css';

const MENU_MIN_WIDTH_PX = 300;
const MENU_GAP_PX = 6;

/**
 * Khối tài khoản cuối sidebar: bấm để mở menu thao tác về hồ sơ, giao diện
 * và cài đặt (một lối vào duy nhất thay cho tên + nút bánh răng riêng).
 */
export default function AccountMenu({
  studentProfile,
  auditData,
  theme,
  onToggleTheme,
  onSwitchProfile,
  onImportTranscript,
  onOpenSettings,
  language = 'vi',
}) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState(null);
  const rootRef = useRef(null);
  const triggerRef = useRef(null);
  const menuRef = useRef(null);
  const menuId = useId();
  const summary = buildStudentSummary(studentProfile, auditData);
  const program = programLabel(summary);
  const isLoading = !studentProfile;

  const close = useCallback((restoreFocus = true) => {
    setIsOpen(false);
    if (restoreFocus) triggerRef.current?.focus();
  }, []);

  const menuItems = () => Array.from(menuRef.current?.querySelectorAll('[role="menuitem"]') ?? []);

  // Menu render qua portal (sidebar có overflow: hidden và có thể hẹp) nên
  // tự neo vào cạnh trên của nút, rộng tối thiểu MENU_MIN_WIDTH.
  useLayoutEffect(() => {
    if (!isOpen) return undefined;
    const place = () => {
      const rect = triggerRef.current?.getBoundingClientRect();
      if (!rect) return;
      setPosition({
        left: rect.left,
        bottom: window.innerHeight - rect.top + MENU_GAP_PX,
        width: Math.max(rect.width, MENU_MIN_WIDTH_PX),
      });
    };
    place();
    window.addEventListener('resize', place);
    return () => window.removeEventListener('resize', place);
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !position) return undefined;
    menuItems()[0]?.focus();
    const handlePointerDown = (event) => {
      const inside = rootRef.current?.contains(event.target) || menuRef.current?.contains(event.target);
      if (!inside) close(false);
    };
    document.addEventListener('mousedown', handlePointerDown);
    return () => document.removeEventListener('mousedown', handlePointerDown);
  }, [isOpen, position, close]);

  const handleMenuKeyDown = (event) => {
    const items = menuItems();
    const index = items.indexOf(document.activeElement);
    const focusAt = (next) => items[(next + items.length) % items.length]?.focus();
    switch (event.key) {
      case 'Escape':
        event.preventDefault();
        close();
        break;
      case 'ArrowDown':
        event.preventDefault();
        focusAt(index + 1);
        break;
      case 'ArrowUp':
        event.preventDefault();
        focusAt(index - 1);
        break;
      case 'Home':
        event.preventDefault();
        focusAt(0);
        break;
      case 'End':
        event.preventDefault();
        focusAt(items.length - 1);
        break;
      case 'Tab':
        close(false);
        break;
      default:
    }
  };

  const handleTriggerKeyDown = (event) => {
    if (event.key === 'ArrowUp' || event.key === 'ArrowDown') {
      event.preventDefault();
      setIsOpen(true);
    }
  };

  const run = (action, keepOpen = false) => () => {
    if (!keepOpen) close(false);
    action?.();
  };

  const isDark = theme !== 'light';
  const subtitle = [program, summary.cpa !== null ? `CPA ${formatCpa(summary.cpa)}` : null]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="account" ref={rootRef}>
      {isOpen && position && createPortal(
        <div
          ref={menuRef}
          id={menuId}
          role="menu"
          aria-label={t('Tài khoản', 'Account')}
          className="account-menu"
          style={position}
          onKeyDown={handleMenuKeyDown}
        >
          <div className="account-menu__header">
            <Avatar avatar={summary.avatar} initial={summary.initial} size={40} />
            <div className="account-menu__identity">
              <div className="account-menu__name">{summary.name || t('Chưa có hồ sơ', 'No profile')}</div>
              <div className="account-menu__meta">
                {[summary.studentId && `MSSV ${summary.studentId}`, summary.className].filter(Boolean).join(' · ')}
              </div>
            </div>
          </div>

          <dl className="account-menu__stats">
            <div title={summary.programName}>
              <dt>{t('CTĐT', 'Program')}</dt>
              <dd>
                {summary.programCode || '—'}
                {summary.curriculumVersion && <small>{t('Bản', 'Version')} {summary.curriculumVersion}</small>}
              </dd>
            </div>
            <div>
              <dt>CPA</dt>
              <dd>
                {formatCpa(summary.cpa)}
                {summary.rank && <small>{summary.rank}</small>}
              </dd>
            </div>
            <div>
              <dt>{t('Tín chỉ', 'Credits')}</dt>
              <dd>
                {summary.creditsText ? summary.creditsText.replace(' TC', '') : '—'}
                {summary.completion !== null && <small>{Math.round(summary.completion)}%</small>}
              </dd>
            </div>
          </dl>
          {summary.warningLevel > 0 && (
            <div className="account-menu__warning" role="note">
              {t(`Đang bị cảnh báo học tập mức ${summary.warningLevel}`, `Academic warning level ${summary.warningLevel}`)}
              {summary.warningText ? ` · ${summary.warningText}` : ''}
            </div>
          )}

          <div className="account-menu__divider" role="separator" />

          <button type="button" role="menuitem" className="account-menu__item" onClick={run(onSwitchProfile)}>
            <Users size={16} aria-hidden="true" />
            <span>{t('Đổi hồ sơ sinh viên', 'Switch student profile')}</span>
          </button>
          <button type="button" role="menuitem" className="account-menu__item" onClick={run(onImportTranscript)}>
            <Upload size={16} aria-hidden="true" />
            <span>{t('Nhập bảng điểm từ CTT', 'Import transcript from CTT')}</span>
          </button>

          <div className="account-menu__divider" role="separator" />

          <button type="button" role="menuitem" className="account-menu__item" onClick={run(onToggleTheme, true)}>
            {isDark ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
            <span>{isDark ? t('Chuyển sang giao diện sáng', 'Switch to light theme') : t('Chuyển sang giao diện tối', 'Switch to dark theme')}</span>
          </button>
          <button type="button" role="menuitem" className="account-menu__item" onClick={run(() => onOpenSettings('general'))}>
            <Settings size={16} aria-hidden="true" />
            <span>{t('Cài đặt', 'Settings')}</span>
          </button>
          <button type="button" role="menuitem" className="account-menu__item" onClick={run(() => onOpenSettings('about'))}>
            <Info size={16} aria-hidden="true" />
            <span>{t('Giới thiệu hệ thống', 'About this system')}</span>
          </button>
        </div>,
        document.body,
      )}

      <button
        ref={triggerRef}
        type="button"
        className="account-trigger"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        aria-controls={isOpen ? menuId : undefined}
        onClick={() => setIsOpen((open) => !open)}
        onKeyDown={handleTriggerKeyDown}
      >
        <Avatar avatar={summary.avatar} initial={summary.initial} size={34} />
        <span className="account-trigger__text">
          <span className="account-trigger__name">
            {isLoading ? t('Đang tải hồ sơ…', 'Loading profile…') : summary.name || t('Chọn hồ sơ', 'Choose a profile')}
          </span>
          {subtitle && (
            <span className={`account-trigger__sub${summary.warningLevel > 0 ? ' is-warning' : ''}`}>{subtitle}</span>
          )}
        </span>
        <ChevronsUpDown size={16} className="account-trigger__chevron" aria-hidden="true" />
      </button>
    </div>
  );
}
