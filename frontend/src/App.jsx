import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  Menu, 
  Sparkles, 
  MoreHorizontal,
  Pin,
  Archive,
  Trash2,
  Folder,
  FileText,
  ChevronRight
} from 'lucide-react';
import Sidebar from './components/Sidebar';
import BrandLogo from './components/BrandLogo';
import ChatTab from './components/ChatTab';
import AuditTab from './components/AuditTab';
import RecommendTab from './components/RecommendTab';
import SettingsModal from './components/SettingsModal';
import ProfileModal from './components/ProfileModal';
import { apiUrl } from './api';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [studentProfile, setStudentProfile] = useState(null);
  const [auditData, setAuditData] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState(null);

  // Theme & Language Settings (persisted in localStorage)
  const [theme, setTheme] = useState(() => localStorage.getItem('hust_advisor_theme') || 'dark');
  const [language, setLanguage] = useState(() => localStorage.getItem('hust_advisor_lang') || 'vi');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [settingsTab, setSettingsTab] = useState('general');
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false);
  const [profileModalTab, setProfileModalTab] = useState('demo');

  // ChatGPT 3-Dots Menu & Pin / Archive States
  const [isChatMenuOpen, setIsChatMenuOpen] = useState(false);
  const [isChatPinned, setIsChatPinned] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);
  const chatMenuRef = useRef(null);

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 2500);
  };

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (chatMenuRef.current && !chatMenuRef.current.contains(e.target)) {
        setIsChatMenuOpen(false);
      }
    };
    if (isChatMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isChatMenuOpen]);

  useEffect(() => {
    fetchInitialData();
  }, []);

  // Update body class when theme changes
  useEffect(() => {
    localStorage.setItem('hust_advisor_theme', theme);
    if (theme === 'light') {
      document.body.classList.add('light-theme');
    } else {
      document.body.classList.remove('light-theme');
    }
  }, [theme]);

  // Persist language
  useEffect(() => {
    localStorage.setItem('hust_advisor_lang', language);
  }, [language]);

  const fetchInitialData = async () => {
    try {
      const [resProfile, resAudit] = await Promise.all([
        fetch(apiUrl('/api/student/profile')),
        fetch(apiUrl('/api/student/audit'))
      ]);

      if (resProfile.ok) {
        const data = await resProfile.json();
        setStudentProfile(data);
      }
      if (resAudit.ok) {
        const audit = await resAudit.json();
        setAuditData(audit);
      }
    } catch (err) {
      console.error('Lỗi kết nối Backend:', err);
    }
  };

  const [chatKey, setChatKey] = useState(0);

  const refreshConversations = async (studentId = studentProfile?.info?.student_id) => {
    if (!studentId) return;
    try {
      const res = await fetch(apiUrl('/api/conversations'), {
        headers: { 'X-Student-ID': studentId }
      });
      if (res.ok) {
        const data = await res.json();
        setConversations(data.conversations || []);
      }
    } catch (err) {
      console.error('Lỗi tải lịch sử hội thoại:', err);
    }
  };

  useEffect(() => {
    const studentId = studentProfile?.info?.student_id;
    if (!studentId) return;
    // Đổi hồ sơ thì không được hiển thị nhầm lịch sử của sinh viên trước.
    setActiveConversationId(null);
    setIsChatPinned(false);
    setConversations([]);
    setChatKey(prev => prev + 1);
    refreshConversations(studentId);
  }, [studentProfile?.info?.student_id]);

  const handleNewChat = () => {
    setActiveTab('chat');
    setActiveConversationId(null);
    setIsChatPinned(false);
    setChatKey(prev => prev + 1);
  };

  const handleSelectConversation = (conversationId) => {
    const conversation = conversations.find(item => item.id === conversationId);
    setActiveTab('chat');
    setActiveConversationId(conversationId);
    setIsChatPinned(Boolean(conversation?.is_pinned));
    setChatKey(prev => prev + 1);
  };

  const handleConversationCreated = (conversationId, studentId) => {
    setActiveConversationId(conversationId);
    refreshConversations(studentId);
  };

  const handleConversationAction = async (action) => {
    if (!activeConversationId) {
      showToast(language === 'vi' ? 'Chưa có đoạn chat để thao tác' : 'No active chat');
      return;
    }
    const studentId = studentProfile?.info?.student_id;
    const headers = {
      'Content-Type': 'application/json',
      ...(studentId ? { 'X-Student-ID': studentId } : {})
    };
    try {
      if (action === 'pin') {
        const nextPinned = !isChatPinned;
        const res = await fetch(apiUrl(`/api/conversations/${activeConversationId}`), {
          method: 'PATCH', headers, body: JSON.stringify({ is_pinned: nextPinned })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        setIsChatPinned(nextPinned);
        showToast(nextPinned ? (language === 'vi' ? 'Đã ghim đoạn chat' : 'Chat pinned') : (language === 'vi' ? 'Đã bỏ ghim đoạn chat' : 'Chat unpinned'));
      } else if (action === 'archive') {
        const res = await fetch(apiUrl(`/api/conversations/${activeConversationId}`), {
          method: 'PATCH', headers, body: JSON.stringify({ is_archived: true })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        handleNewChat();
        showToast(language === 'vi' ? 'Đã lưu trữ đoạn chat' : 'Chat archived');
      } else if (action === 'delete') {
        const res = await fetch(apiUrl(`/api/conversations/${activeConversationId}`), {
          method: 'DELETE', headers
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        handleNewChat();
        showToast(language === 'vi' ? 'Đã xóa đoạn chat' : 'Chat deleted');
      }
      refreshConversations(studentId);
    } catch (err) {
      console.error('Lỗi cập nhật đoạn chat:', err);
      showToast(language === 'vi' ? 'Không thể cập nhật đoạn chat' : 'Could not update chat');
    }
  };

  const handleOpenImport = () => {
    setProfileModalTab('import');
    setIsProfileModalOpen(true);
  };

  // Ổn định tham chiếu: SettingsModal gắn/gỡ listener Esc theo onClose.
  const handleCloseSettings = useCallback(() => setIsSettingsOpen(false), []);

  const handleOpenSettings = (tab = 'general') => {
    setSettingsTab(tab);
    setIsSettingsOpen(true);
  };

  const handleProfileUpdated = (data) => {
    if (data.profile) setStudentProfile(data.profile);
    if (data.audit) setAuditData(data.audit);
  };

  const handleOpenProfileModal = () => {
    setProfileModalTab('demo');
    setIsProfileModalOpen(true);
  };

  return (
    <div style={{ height: '100vh', display: 'flex', overflow: 'hidden', background: 'var(--bg-dark)' }}>
      {/* 1. ChatGPT-style Collapsible Left Sidebar */}
      <Sidebar 
        isOpen={isSidebarOpen}
        setIsOpen={setIsSidebarOpen}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        auditData={auditData}
        studentProfile={studentProfile}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onNewChat={handleNewChat}
        onSelectConversation={handleSelectConversation}
        onOpenSettings={handleOpenSettings}
        onOpenProfileModal={handleOpenProfileModal}
        onOpenImport={handleOpenImport}
        theme={theme}
        onToggleTheme={() => setTheme(current => (current === 'light' ? 'dark' : 'light'))}
        language={language}
      />

      {/* 2. Main Workspace */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        overflow: 'hidden',
        position: 'relative'
      }}>
        {/* Minimal ChatGPT-style Topbar */}
        <header style={{
          height: '44px',
          borderBottom: 'none',
          background: 'transparent',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 16px',
          zIndex: 30,
          flexShrink: 0
        }}>
          {/* Left: Sidebar Toggle (when closed) & Student Switcher Pill */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                title={language === 'vi' ? 'Mở thanh bên' : 'Open Sidebar'}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.color = 'var(--text-primary)';
                  e.currentTarget.style.background = 'var(--sidebar-hover)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.color = 'var(--text-secondary)';
                  e.currentTarget.style.background = 'transparent';
                }}
              >
                <Menu size={18} />
              </button>
            )}
            {!isSidebarOpen && <BrandLogo size={28} />}

          </div>

          {/* Right: ChatGPT 3-Dots Menu (...) with Pin, Archive, Delete */}
          <div style={{ display: 'flex', alignItems: 'center', position: 'relative' }} ref={chatMenuRef}>
            <button
              onClick={() => setIsChatMenuOpen(prev => !prev)}
              title={language === 'vi' ? 'Tùy chọn đoạn chat' : 'Chat options'}
              style={{
                width: '36px',
                height: '36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRadius: '8px',
                border: 'none',
                background: isChatMenuOpen ? 'var(--sidebar-hover)' : 'transparent',
                color: isChatMenuOpen ? 'var(--text-primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.color = 'var(--text-primary)';
                e.currentTarget.style.background = 'var(--sidebar-hover)';
              }}
              onMouseLeave={e => {
                if (!isChatMenuOpen) {
                  e.currentTarget.style.color = 'var(--text-secondary)';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <MoreHorizontal size={19} />
            </button>

            {/* ChatGPT-style Dropdown Menu */}
            {isChatMenuOpen && (
              <div style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                width: '235px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '14px',
                padding: '6px',
                boxShadow: 'var(--shadow-md)',
                backdropFilter: 'blur(20px)',
                zIndex: 100,
                display: 'flex',
                flexDirection: 'column',
                gap: '2px'
              }}>
                {/* 1. Xem các tệp trong đoạn chat */}
                <button
                  onClick={() => {
                    setIsChatMenuOpen(false);
                    handleOpenImport();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <FileText size={16} color="var(--text-muted)" />
                  <span>{language === 'vi' ? 'Xem các tệp trong đoạn chat' : 'View files in chat'}</span>
                </button>

                {/* 2. Ghim đoạn chat */}
                <button
                  onClick={() => {
                    setIsChatMenuOpen(false);
                    handleConversationAction('pin');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <Pin size={16} color={isChatPinned ? 'var(--brand-accent)' : 'var(--text-muted)'} />
                  <span>
                    {isChatPinned 
                      ? (language === 'vi' ? 'Bỏ ghim đoạn chat' : 'Unpin chat') 
                      : (language === 'vi' ? 'Ghim đoạn chat' : 'Pin chat')}
                  </span>
                </button>

                {/* 3. Lưu trữ */}
                <button
                  onClick={() => {
                    setIsChatMenuOpen(false);
                    handleConversationAction('archive');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <Archive size={16} color="var(--text-muted)" />
                  <span>{language === 'vi' ? 'Lưu trữ' : 'Archive'}</span>
                </button>

                {/* 4. Xóa */}
                <button
                  onClick={() => {
                    setIsChatMenuOpen(false);
                    handleConversationAction('delete');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--danger)',
                    fontSize: '0.85rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <Trash2 size={16} color="var(--danger)" />
                  <span>{language === 'vi' ? 'Xóa' : 'Delete'}</span>
                </button>

                <div style={{ height: '1px', background: 'var(--border-subtle)', margin: '4px 0' }} />

                {/* 5. Di chuyển sang dự án */}
                <button
                  onClick={() => {
                    setIsChatMenuOpen(false);
                    showToast(language === 'vi' ? 'Đã lưu vào Dự án tốt nghiệp' : 'Moved to Project');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '9px 12px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--text-primary)',
                    fontSize: '0.85rem',
                    fontWeight: '500',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                >
                  <Folder size={16} color="var(--text-muted)" />
                  <span>{language === 'vi' ? 'Di chuyển sang dự án' : 'Move to project'}</span>
                  <ChevronRight size={14} style={{ marginLeft: 'auto', color: 'var(--text-muted)' }} />
                </button>
              </div>
            )}
          </div>
        </header>

        {/* Apple Dynamic Island Toast Notification */}
        {toastMessage && (
          <div className="apple-dynamic-island">
            <Sparkles size={14} color="var(--success)" />
            <span>{toastMessage}</span>
          </div>
        )}

        {/* Content Workspace with Apple View Transition */}
        <main style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          <div key={activeTab} className="apple-view-transition" style={{ height: '100%' }}>
            {activeTab === 'chat' && (
              <ChatTab 
                key={chatKey}
                onNavigateTab={setActiveTab}
                studentProfile={studentProfile}
                studentId={studentProfile?.info?.student_id}
                conversationId={activeConversationId}
                onConversationCreated={handleConversationCreated}
                onConversationUpdated={() => refreshConversations()}
                onOpenImport={handleOpenImport}
                onOpenProfileModal={handleOpenProfileModal}
                onOpenAuthModal={handleOpenProfileModal}
                language={language}
              />
            )}

            {activeTab !== 'chat' && (
              <div style={{ 
                height: '100%', 
                overflowY: 'auto', 
                padding: '24px 28px',
                maxWidth: '1280px',
                margin: '0 auto'
              }}>
                {activeTab === 'audit' && (
                  <AuditTab 
                    auditData={auditData} 
                    onNavigateTab={setActiveTab}
                    onOpenImport={handleOpenImport}
                    onOpenProfileModal={handleOpenProfileModal}
                    onOpenAuthModal={handleOpenProfileModal}
                  />
                )}

                {activeTab === 'recommend' && (
                  <RecommendTab />
                )}
              </div>
            )}
          </div>
        </main>
      </div>

      {/* 3. Settings Dialog Modal */}
      <SettingsModal 
        isOpen={isSettingsOpen}
        onClose={handleCloseSettings}
        initialTab={settingsTab}
        theme={theme}
        setTheme={setTheme}
        language={language}
        setLanguage={setLanguage}
        studentProfile={studentProfile}
        auditData={auditData}
        onProfileUpdated={handleProfileUpdated}
        onSwitchProfile={() => {
          setIsSettingsOpen(false);
          handleOpenProfileModal();
        }}
        onShowToast={showToast}
      />

      {/* 4. Student Profile Switcher & Import Modal */}
      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
        currentStudentId={studentProfile?.info?.student_id}
        initialTab={profileModalTab}
        studentProfile={studentProfile}
        onProfileSwitched={(data) => {
          if (data.profile) setStudentProfile(data.profile);
          if (data.audit) setAuditData(data.audit);
        }}
        language={language}
      />
    </div>
  );
}
