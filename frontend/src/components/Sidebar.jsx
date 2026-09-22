import React, { useState } from 'react';
import { 
  Plus, 
  Award, 
  CheckCircle2, 
  ChevronLeft, 
  Sparkles,
  Settings
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
  onOpenProfileModal,
  onOpenAuthModal,
  language = 'vi'
}) {
  const studentInfo = studentProfile?.info || {};
  const cpa = auditData?.cpa ?? 2.26;

  const toolItems = [
    { id: 'audit', label: language === 'vi' ? 'Tiến độ học tập & CPA' : 'Degree Audit & CPA', icon: Award },
    { id: 'recommend', label: language === 'vi' ? 'Gợi ý chọn môn' : 'Course Suggestions', icon: CheckCircle2 },
  ];

  return (
    <aside 
      style={{
        width: isOpen ? '260px' : '0px',
        minWidth: isOpen ? '260px' : '0px',
        transition: 'width 0.32s var(--ease-apple), min-width 0.32s var(--ease-apple)',
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
      <div style={{ padding: '16px 14px 12px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #c8102e, #990000)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: '900',
              fontSize: '0.88rem',
              color: '#fff',
              boxShadow: '0 2px 8px rgba(200, 16, 46, 0.4)'
            }}>
              BK
            </div>
            <div>
              <div style={{ fontSize: '0.92rem', fontWeight: '700', color: 'var(--text-primary)', letterSpacing: '-0.01em', lineHeight: 1.2 }}>
                HUST Advisor
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                Tư vấn học tập HUST
              </div>
            </div>
          </div>

          <button
            onClick={() => setIsOpen(false)}
            title="Thu gọn Sidebar"
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
            onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
          >
            <ChevronLeft size={18} />
          </button>
        </div>

        {/* New Chat Button */}
        <button
          onClick={onNewChat}
          className="apple-press"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '10px 14px',
            borderRadius: '10px',
            border: '1px solid var(--border-subtle)',
            background: 'var(--sidebar-newchat-bg)',
            color: 'var(--text-primary)',
            fontSize: '0.88rem',
            fontWeight: '600',
            cursor: 'pointer',
            width: '100%',
            boxShadow: 'var(--shadow-sm)'
          }}
          onMouseEnter={e => {
            e.currentTarget.style.background = 'var(--sidebar-hover)';
            e.currentTarget.style.borderColor = 'rgba(200, 16, 46, 0.3)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.background = 'var(--sidebar-newchat-bg)';
            e.currentTarget.style.borderColor = 'var(--border-subtle)';
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Plus size={16} color="#c8102e" />
            <span>Đoạn chat mới</span>
          </div>
          <Sparkles size={14} color="#38bdf8" />
        </button>
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
                    background: isActive ? 'rgba(200, 16, 46, 0.15)' : 'transparent',
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
                  <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                    <Icon size={16} color={isActive ? '#c8102e' : 'var(--text-muted)'} />
                    <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '170px' }}>
                      {item.label}
                    </span>
                  </div>
                  {item.badge && (
                    <span style={{ 
                      fontSize: '0.65rem', 
                      background: 'rgba(200, 16, 46, 0.15)', 
                      color: '#c8102e', 
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
            {conversations.length === 0 ? (
              <span style={{ padding: '7px 10px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                {language === 'vi' ? 'Chưa có đoạn chat đã lưu' : 'No saved chats yet'}
              </span>
            ) : conversations.map(conversation => (
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
            ))}
          </div>
        </div>

      </div>

      {/* Sidebar Footer: Student Profile Card */}
      <div style={{
        padding: '10px 12px',
        borderTop: '1px solid var(--border-subtle)',
        background: 'var(--sidebar-footer-bg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '6px'
      }}>
        {/* Clickable Profile Info (Avatar + Name + CPA) */}
        <div 
          onClick={onOpenProfileModal}
          title={language === 'vi' ? 'Nhấp để đổi hồ sơ sinh viên' : 'Click to switch student profile'}
          style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px', 
            overflow: 'hidden',
            cursor: 'pointer',
            flex: 1,
            padding: '5px 6px',
            borderRadius: '8px',
            transition: 'all 0.15s ease'
          }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--sidebar-hover)'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
        >
          {/* Avatar */}
          <div style={{
            width: '34px',
            height: '34px',
            borderRadius: '50%',
            background: studentInfo.avatar_gradient || 'linear-gradient(135deg, #6366f1, #38bdf8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: '700',
            fontSize: studentInfo.avatar_emoji ? '1.05rem' : '0.88rem',
            flexShrink: 0,
            overflow: 'hidden'
          }}>
            {studentInfo.avatar_url ? (
              <img src={studentInfo.avatar_url} alt="avatar" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            ) : (
              studentInfo.avatar_emoji || (studentInfo.student_name || 'H').charAt(0)
            )}
          </div>

          {/* 2 Lines: Dòng 1 tên, Dòng 2 CPA */}
          <div style={{ overflow: 'hidden', flex: 1, display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div style={{ 
              fontSize: '0.85rem', 
              fontWeight: '600', 
              color: 'var(--text-primary)', 
              whiteSpace: 'nowrap', 
              overflow: 'hidden', 
              textOverflow: 'ellipsis' 
            }}>
              {studentInfo.student_name || 'Nguyễn Văn Hiếu'}
            </div>
            <div style={{ 
              fontSize: '0.74rem', 
              color: 'var(--text-muted)',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}>
              <span>CPA:</span>
              <strong style={{ color: '#f59e0b', fontWeight: '600' }}>{cpa.toFixed(2)}</strong>
            </div>
          </div>
        </div>

        {/* Settings Button */}
        <button
          onClick={onOpenSettings}
          title={language === 'vi' ? 'Cài đặt' : 'Settings'}
          style={{
            background: 'transparent',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            padding: '7px',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.15s ease',
            flexShrink: 0
          }}
          onMouseEnter={e => {
            e.currentTarget.style.color = 'var(--text-primary)';
            e.currentTarget.style.background = 'var(--sidebar-hover)';
          }}
          onMouseLeave={e => {
            e.currentTarget.style.color = 'var(--text-muted)';
            e.currentTarget.style.background = 'transparent';
          }}
        >
          <Settings size={18} />
        </button>
      </div>
    </aside>
  );
}
