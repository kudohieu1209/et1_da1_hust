import React, { useState, useEffect } from 'react';
import BrandLogo from './BrandLogo';
import AccountMenu from './account/AccountMenu';
import { 
  Plus, 
  Award, 
  CheckCircle2, 
  PanelLeft,
  PanelLeftClose,
  Search,
  X
} from 'lucide-react';

export default function Sidebar({ 
  isOpen, 
  setIsOpen, 
  activeTab, 
  setActiveTab, 
  auditData, 
  studentProfile,
  conversations = [],
  activeConversationId,
  onNewChat,
  onSelectConversation,
  onOpenSettings,
  onLogout,
  onOpenImport,
  language = 'vi'
}) {

  // Resizable sidebar width (persisted in localStorage)
  const [width, setWidth] = useState(() => {
    const saved = localStorage.getItem('hust_advisor_sidebar_width');
    const parsed = parseInt(saved, 10);
    return !isNaN(parsed) && parsed >= 220 && parsed <= 500 ? parsed : 260;
  });
  const [isResizing, setIsResizing] = useState(false);
  const [isCollapseHovered, setIsCollapseHovered] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    if (!isResizing) return;

    const handleMouseMove = (e) => {
      const newWidth = Math.min(Math.max(e.clientX, 220), 500);
      setWidth(newWidth);
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      localStorage.setItem('hust_advisor_sidebar_width', width);
    };

    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
  }, [isResizing, width]);

  const startResizing = (e) => {
    e.preventDefault();
    setIsResizing(true);
  };

  const handleDoubleClick = () => {
    setWidth(260);
    localStorage.setItem('hust_advisor_sidebar_width', 260);
  };

  const toolItems = [
    { id: 'audit', label: language === 'vi' ? 'Tiến độ học tập & CPA' : 'Degree Audit & CPA', icon: Award },
    { id: 'recommend', label: language === 'vi' ? 'Gợi ý chọn môn' : 'Course Suggestions', icon: CheckCircle2 },
  ];

  return (
    <aside 
      style={{
        width: isOpen ? `${width}px` : '0px',
        minWidth: isOpen ? `${width}px` : '0px',
        transition: isResizing ? 'none' : 'width 0.32s var(--ease-apple), min-width 0.32s var(--ease-apple)',
        height: '100vh',
        background: 'var(--sidebar-bg)',
        borderRight: isOpen ? '1px solid var(--border-subtle)' : 'none',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        position: 'relative',
        zIndex: 50,
        flexShrink: 0
      }}
    >
      {/* Sidebar Header: Logo & New Chat */}
      <div style={{ padding: '14px 12px 10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <button
            type="button"
            onClick={onNewChat}
            className="apple-press"
            title={language === 'vi' ? 'Cuộc trò chuyện mới' : 'New chat'}
            style={{ 
              background: 'transparent',
              border: 'none',
              padding: '4px 6px',
              marginLeft: '-4px',
              borderRadius: '8px',
              display: 'flex', 
              alignItems: 'center', 
              gap: '8px',
              cursor: 'pointer',
              textAlign: 'left',
              transition: 'background 0.15s ease'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <BrandLogo size={24} decorative />
            <span style={{ 
              fontSize: '1rem', 
              fontWeight: '600', 
              color: 'var(--text-primary)', 
              letterSpacing: '-0.01em',
              lineHeight: 1
            }}>
              HUST Advisor
            </span>
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: '2px' }}>
            <button
              type="button"
              onClick={() => {
                setIsSearchOpen(prev => !prev);
                if (isSearchOpen) setSearchQuery('');
              }}
              title={language === 'vi' ? 'Tìm kiếm' : 'Search'}
              style={{
                background: isSearchOpen ? 'var(--sidebar-hover)' : 'transparent',
                border: 'none',
                color: isSearchOpen ? 'var(--text-primary)' : 'var(--text-muted)',
                cursor: 'pointer',
                width: '32px',
                height: '32px',
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
                if (!isSearchOpen) {
                  e.currentTarget.style.color = 'var(--text-muted)';
                  e.currentTarget.style.background = 'transparent';
                }
              }}
            >
              <Search size={18} />
            </button>

            <button
              type="button"
              onClick={() => {
                setIsCollapseHovered(false);
                setIsOpen(false);
              }}
              title={language === 'vi' ? 'Thu gọn thanh bên' : 'Collapse sidebar'}
              style={{
                background: isCollapseHovered ? 'var(--sidebar-hover)' : 'transparent',
                border: 'none',
                color: isCollapseHovered ? 'var(--text-primary)' : 'var(--text-muted)',
                cursor: 'pointer',
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.15s ease'
              }}
              onMouseEnter={() => setIsCollapseHovered(true)}
              onMouseLeave={() => setIsCollapseHovered(false)}
            >
              {isCollapseHovered ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
            </button>
          </div>
        </div>

        {isSearchOpen && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 10px',
            borderRadius: '8px',
            background: 'var(--sidebar-hover)',
            border: '1px solid var(--border-subtle)',
            marginTop: '2px'
          }}>
            <Search size={14} color="var(--text-muted)" style={{ flexShrink: 0 }} />
            <input
              type="text"
              autoFocus
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder={language === 'vi' ? 'Tìm cuộc trò chuyện…' : 'Search chats…'}
              style={{
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: 'var(--text-primary)',
                fontSize: '0.82rem',
                width: '100%'
              }}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '2px',
                  display: 'flex',
                  alignItems: 'center',
                  color: 'var(--text-muted)'
                }}
              >
                <X size={14} />
              </button>
            )}
          </div>
        )}

        {/* New Chat Button - Synchronized with Tool Items */}
        {(() => {
          const isNewChatActive = activeTab === 'chat' && !activeConversationId;
          return (
            <button
              onClick={onNewChat}
              className="apple-press"
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '8px 10px',
                borderRadius: '8px',
                border: 'none',
                background: isNewChatActive ? 'rgba(213, 19, 42, 0.15)' : 'transparent',
                color: isNewChatActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontWeight: isNewChatActive ? '700' : '500',
                fontSize: '0.84rem',
                cursor: 'pointer',
                textAlign: 'left',
                width: '100%',
                transition: 'background 0.15s ease, color 0.15s ease'
              }}
              onMouseEnter={e => {
                if (!isNewChatActive) {
                  e.currentTarget.style.background = 'var(--sidebar-hover)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }
              }}
              onMouseLeave={e => {
                if (!isNewChatActive) {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '9px', minWidth: 0, flex: 1 }}>
                <Plus size={16} color="var(--brand-accent)" style={{ flexShrink: 0 }} />
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flex: 1 }}>
                  {language === 'vi' ? 'Cuộc trò chuyện mới' : 'New chat'}
                </span>
              </div>
            </button>
          );
        })()}
      </div>

      {/* Middle Scrollable Section: Tools & Conversation History */}
      <div style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '8px 12px', 
        display: 'flex', 
        flexDirection: 'column', 
        gap: '18px' 
      }}>
        {/* Navigation Tools */}
        <div>
          <div style={{ 
            fontSize: '0.72rem', 
            fontWeight: '700', 
            color: 'var(--text-muted)', 
            textTransform: 'uppercase', 
            padding: '0 8px 6px',
            letterSpacing: '0.05em'
          }}>
            Công cụ học tập
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '3px' }}>
            {toolItems.map(item => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className="apple-press"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    borderRadius: '8px',
                    border: 'none',
                    background: isActive ? 'rgba(213, 19, 42, 0.15)' : 'transparent',
                    color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                    fontWeight: isActive ? '700' : '500',
                    fontSize: '0.84rem',
                    cursor: 'pointer',
                    textAlign: 'left',
                    width: '100%'
                  }}
                  onMouseEnter={e => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'var(--sidebar-hover)';
                      e.currentTarget.style.color = 'var(--text-primary)';
                    }
                  }}
                  onMouseLeave={e => {
                    if (!isActive) {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text-secondary)';
                    }
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '9px', minWidth: 0, flex: 1 }}>
                    <Icon size={16} color={isActive ? 'var(--brand-accent)' : 'var(--text-muted)'} style={{ flexShrink: 0 }} />
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', flex: 1 }}>
                      {item.label}
                    </span>
                  </div>
                  {item.badge && (
                    <span style={{ 
                      fontSize: '0.65rem', 
                      background: 'rgba(213, 19, 42, 0.15)',
                      color: 'var(--brand-accent)',
                      padding: '2px 6px', 
                      borderRadius: '4px',
                      fontWeight: '700'
                    }}>
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Persistent conversation history */}
        <div>
          <div style={{ 
            fontSize: '0.74rem', 
            fontWeight: '600', 
            color: 'var(--text-muted)', 
            padding: '4px 10px 6px',
            letterSpacing: '0.01em'
          }}>
            {language === 'vi' ? 'Gần đây' : 'Recent'}
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {(() => {
              const displayList = searchQuery.trim()
                ? conversations.filter(c => (c.title || '').toLowerCase().includes(searchQuery.toLowerCase()))
                : conversations;

              if (displayList.length === 0) {
                return (
                  <span style={{ padding: '7px 10px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    {searchQuery.trim()
                      ? (language === 'vi' ? 'Không tìm thấy cuộc trò chuyện' : 'No matching chats found')
                      : (language === 'vi' ? 'Chưa có đoạn chat đã lưu' : 'No saved chats yet')}
                  </span>
                );
              }

              return displayList.map(conversation => (
              <button
                key={conversation.id}
                className="apple-press"
                onClick={() => onSelectConversation(conversation.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '7px 10px',
                  borderRadius: '8px',
                  border: 'none',
                  background: activeConversationId === conversation.id ? 'var(--sidebar-hover)' : 'transparent',
                  color: activeConversationId === conversation.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                  fontSize: '0.84rem',
                  cursor: 'pointer',
                  textAlign: 'left',
                  width: '100%',
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = 'var(--sidebar-hover)';
                  e.currentTarget.style.color = 'var(--text-primary)';
                }}
                onMouseLeave={e => {
                  if (activeConversationId !== conversation.id) e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = activeConversationId === conversation.id ? 'var(--text-primary)' : 'var(--text-secondary)';
                }}
              >
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {conversation.is_pinned ? '📌 ' : ''}{conversation.title}
                </span>
              </button>
              ));
            })()}
          </div>
        </div>

      </div>

      <AccountMenu
        studentProfile={studentProfile}
        auditData={auditData}
        onLogout={onLogout}
        onImportTranscript={onOpenImport}
        onOpenSettings={onOpenSettings}
        language={language}
      />

      {/* Draggable Resize Handle on right edge */}
      {isOpen && (
        <div
          onMouseDown={startResizing}
          onDoubleClick={handleDoubleClick}
          title={language === 'vi' ? 'Kéo để chỉnh độ rộng thanh bên (Nhấp đúp để đặt lại)' : 'Drag to resize sidebar (Double-click to reset)'}
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            width: '5px',
            height: '100%',
            cursor: 'col-resize',
            zIndex: 100,
            userSelect: 'none',
            background: isResizing ? 'var(--brand-accent, #c8102e)' : 'transparent',
            transition: 'background 0.15s ease'
          }}
          onMouseEnter={e => {
            if (!isResizing) e.currentTarget.style.background = 'rgba(200, 16, 46, 0.4)';
          }}
          onMouseLeave={e => {
            if (!isResizing) e.currentTarget.style.background = 'transparent';
          }}
        />
      )}
    </aside>
  );
}
