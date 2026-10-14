import React, { useEffect, useRef, useState } from 'react';
import { Info, Moon, SlidersHorizontal, Sun, UserRound, X } from 'lucide-react';
import AboutPanel from './account/AboutPanel';
import ProfileSettings from './account/ProfileSettings';
import './account/account.css';

const TABS = [
  { id: 'general', vi: 'Chung', en: 'General', icon: SlidersHorizontal },
  { id: 'profile', vi: 'Hồ sơ', en: 'Profile', icon: UserRound },
  { id: 'about', vi: 'Giới thiệu', en: 'About', icon: Info },
];

function Segmented({ label, value, options, onChange }) {
  return (
    <div className="settings-segment" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          onClick={() => onChange(option.value)}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  );
}

/**
 * Hộp thoại Cài đặt: Chung (giao diện, ngôn ngữ), Hồ sơ (tên + ảnh đại diện)
 * và Giới thiệu (số liệu hệ thống lấy từ backend).
 */
export default function SettingsModal({
  isOpen,
  onClose,
  initialTab = 'general',
  theme,
  setTheme,
  language,
  setLanguage,
  studentProfile,
  auditData,
  onProfileUpdated,
  onSwitchProfile,
  onShowToast,
}) {
  const t = (vi, en) => (language === 'vi' ? vi : en);
  const [activeTab, setActiveTab] = useState(initialTab);
  const dialogRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    setActiveTab(initialTab);
    const previouslyFocused = document.activeElement;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKeyDown);
    // Đưa focus vào hộp thoại để Esc/Tab hoạt động ngay khi mở.
    requestAnimationFrame(() => dialogRef.current?.querySelector('[aria-selected="true"]')?.focus());
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      if (previouslyFocused instanceof HTMLElement) previouslyFocused.focus();
    };
  }, [isOpen, initialTab, onClose]);

  if (!isOpen) return null;

  const handleTabKeyDown = (event) => {
    const index = TABS.findIndex((tab) => tab.id === activeTab);
    const step = { ArrowDown: 1, ArrowRight: 1, ArrowUp: -1, ArrowLeft: -1 }[event.key];
    if (!step) return;
    event.preventDefault();
    const next = TABS[(index + step + TABS.length) % TABS.length];
    setActiveTab(next.id);
    dialogRef.current?.querySelector(`#settings-tab-${next.id}`)?.focus();
  };

  return (
    <div className="apple-modal-backdrop" onClick={onClose}>
      <div
        ref={dialogRef}
        className="apple-modal-window settings-window"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        onClick={(event) => event.stopPropagation()}
      >
        <header className="settings-header">
          <h2 id="settings-title">{t('Cài đặt', 'Settings')}</h2>
          <button type="button" className="settings-close" onClick={onClose} aria-label={t('Đóng', 'Close')}>
            <X size={18} />
          </button>
        </header>

        <div className="settings-body">
          <nav className="settings-tabs" role="tablist" aria-orientation="vertical" onKeyDown={handleTabKeyDown}>
            {TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = tab.id === activeTab;
              return (
                <button
                  key={tab.id}
                  id={`settings-tab-${tab.id}`}
                  type="button"
                  role="tab"
                  aria-selected={isActive}
                  aria-controls="settings-panel"
                  tabIndex={isActive ? 0 : -1}
                  className="settings-tab"
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon size={16} aria-hidden="true" />
                  {t(tab.vi, tab.en)}
                </button>
              );
            })}
          </nav>

          <div
            id="settings-panel"
            className="settings-panel"
            role="tabpanel"
            aria-labelledby={`settings-tab-${activeTab}`}
          >
            {activeTab === 'general' && (
              <>
                <section className="settings-section">
                  <h3>{t('Giao diện', 'Appearance')}</h3>
                  <p className="settings-hint">{t('Lưu trên trình duyệt này.', 'Saved in this browser.')}</p>
                  <Segmented
                    label={t('Giao diện', 'Appearance')}
                    value={theme}
                    onChange={setTheme}
                    options={[
                      { value: 'light', label: t('Sáng', 'Light'), icon: <Sun size={15} aria-hidden="true" /> },
                      { value: 'dark', label: t('Tối', 'Dark'), icon: <Moon size={15} aria-hidden="true" /> },
                    ]}
                  />
                </section>
                <section className="settings-section">
                  <h3>{t('Ngôn ngữ', 'Language')}</h3>
                  <p className="settings-hint">
                    {t('Chỉ áp dụng cho giao diện; câu trả lời của trợ lý hiện bằng tiếng Việt.', 'Interface only; the assistant currently answers in Vietnamese.')}
                  </p>
                  <Segmented
                    label={t('Ngôn ngữ', 'Language')}
                    value={language}
                    onChange={setLanguage}
                    options={[
                      { value: 'vi', label: 'Tiếng Việt' },
                      { value: 'en', label: 'English' },
                    ]}
                  />
                </section>
              </>
            )}

            {activeTab === 'profile' && (
              <ProfileSettings
                studentProfile={studentProfile}
                auditData={auditData}
                language={language}
                onProfileUpdated={onProfileUpdated}
                onSwitchProfile={onSwitchProfile}
                onShowToast={onShowToast}
              />
            )}

            {activeTab === 'about' && <AboutPanel language={language} />}
          </div>
        </div>
      </div>
    </div>
  );
}
