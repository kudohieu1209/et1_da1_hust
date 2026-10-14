import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  Copy, 
  Check, 
  Plus, 
  BookOpen,
  Mic,
  MicOff,
  ThumbsUp,
  ThumbsDown,
  RotateCcw
} from 'lucide-react';
import { API_BASE_URL, apiUrl } from '../api';
import BrandLogo from './BrandLogo';
import StudentWelcome from './StudentWelcome';

export default function ChatTab({ 
  onOpenImport,
  studentProfile,
  studentId,
  conversationId,
  onConversationCreated,
  onConversationUpdated,
  language = 'vi'
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef(null);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;
  const recognitionRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-resize textarea dynamically based on content (up to 160px)
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = '36px';
      if (input) {
        const scrollH = textareaRef.current.scrollHeight;
        if (scrollH > 36) {
          textareaRef.current.style.height = `${Math.min(scrollH, 160)}px`;
        }
      }
    }
  }, [input]);

  // Load the selected conversation from SQLite. A new chat has no ID until
  // its first message is accepted by the backend.
  useEffect(() => {
    let cancelled = false;
    if (!conversationId) {
      setMessages([]);
      return undefined;
    }

    setLoading(true);
    fetch(apiUrl(`/api/conversations/${conversationId}`), {
      headers: studentId ? { 'X-Student-ID': studentId } : {}
    })
      .then(res => res.ok ? res.json() : Promise.reject(new Error(`HTTP ${res.status}`)))
      .then(data => {
        if (cancelled) return;
        setMessages((data.messages || []).map(message => ({
          role: message.role,
          content: message.content,
          suggested_actions: message.suggested_actions || [],
          data_context: message.data_context,
          sources: message.sources || [],
          model_used: message.model_used
        })));
      })
      .catch(err => {
        if (!cancelled) {
          console.error('Lỗi tải đoạn chat:', err);
          setMessages([]);
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [conversationId, studentId]);

  const toggleListening = () => {
    if (isListening) {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
      setIsListening(false);
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert(language === 'vi' 
        ? 'Trình duyệt của bạn chưa hỗ trợ nhận diện giọng nói (Web Speech API). Vui lòng thử trên Google Chrome hoặc Edge.' 
        : 'Your browser does not support Web Speech API. Please try on Google Chrome or Microsoft Edge.');
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = language === 'vi' ? 'vi-VN' : 'en-US';
      recognition.continuous = false;
      recognition.interimResults = true;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(result => result[0].transcript)
          .join('');
        setInput(transcript);
      };

      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err) {
      console.error('Lỗi khởi tạo Microphone:', err);
      setIsListening(false);
    }
  };



  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const handleSend = async (textToSend) => {
    const query = typeof textToSend === 'string' ? textToSend.trim() : input.trim();
    if (!query || loading) return;

    // Guaranteed instant functional state update: Appends user question bubble immediately
    const userMsg = { role: 'user', content: query };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = '36px';
    }
    setLoading(true);

    try {
      const historyToSend = [...messagesRef.current, userMsg].slice(-6);
      const res = await fetch(apiUrl('/api/chat'), {
        method: 'POST',
        // The demo auth layer identifies the active profile by MSSV. This
        // header also scopes conversation history on the backend.
        headers: {
          'Content-Type': 'application/json',
          ...(studentId ? { 'X-Student-ID': studentId } : {})
        },
        body: JSON.stringify({
          message: query,
          history: historyToSend,
          conversation_id: conversationId || null
        })
      });

      if (!res.ok) {
        throw new Error(`HTTP error: ${res.status}`);
      }

      const data = await res.json();
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: data.reply,
          suggested_actions: data.suggested_actions,
          data_context: data.data_context,
          sources: data.sources || [],
          model_used: data.model_used
        }
      ]);
      if (data.conversation_id && !conversationId && onConversationCreated) {
        onConversationCreated(data.conversation_id, studentId);
      } else if (onConversationUpdated) {
        onConversationUpdated();
      }
    } catch (err) {
      console.error('Chat error:', err);
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          content: `❌ Không thể kết nối tới Backend server (${API_BASE_URL}). Bạn vui lòng kiểm tra xem server FastAPI đang chạy nhé!`,
          suggested_actions: ["Thử lại", "Kiểm tra kết nối"]
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Helper to parse inline Markdown (bold, code, italic)
  const parseInlineTokens = (rawText) => {
    if (!rawText) return null;
    const regex = /(\*\*.*?\*\*|`.*?`|\*.*?\*)/g;
    const tokens = rawText.split(regex);

    return tokens.map((token, idx) => {
      if (!token) return null;
      if (token.startsWith('**') && token.endsWith('**') && token.length >= 4) {
        return (
          <strong key={idx} style={{ color: 'var(--text-primary)', fontWeight: '700' }}>
            {token.slice(2, -2)}
          </strong>
        );
      }
      if (token.startsWith('`') && token.endsWith('`') && token.length >= 2) {
        return (
          <code key={idx} style={{
            background: 'rgba(213, 19, 42, 0.12)',
            padding: '2px 6px',
            borderRadius: '4px',
            color: 'var(--brand-accent)',
            fontSize: '0.88em',
            fontFamily: 'monospace',
            border: '1px solid rgba(213, 19, 42, 0.2)'
          }}>
            {token.slice(1, -1)}
          </code>
        );
      }
      if (token.startsWith('*') && token.endsWith('*') && token.length >= 2 && !token.startsWith('**')) {
        return (
          <em key={idx} style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>
            {token.slice(1, -1)}
          </em>
        );
      }
      return token;
    });
  };

  // Render text with Markdown bold, code, lists, and headings
  const renderFormattedText = (text) => {
    if (!text) return null;
    const lines = text.split('\n');

    return lines.map((rawLine, i) => {
      // 1. Blank line
      if (!rawLine.trim()) {
        return <div key={i} style={{ height: '8px' }} />;
      }

      // 2. Headings
      if (rawLine.startsWith('### ')) {
        return (
          <h4 key={i} style={{ 
            margin: '14px 0 8px', 
            fontSize: '1.05rem', 
            color: 'var(--text-primary)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}>
            {parseInlineTokens(rawLine.slice(4))}
          </h4>
        );
      }
      if (rawLine.startsWith('#### ')) {
        return (
          <h5 key={i} style={{ margin: '10px 0 4px', fontSize: '0.95rem', color: 'var(--text-secondary)' }}>
            {parseInlineTokens(rawLine.slice(5))}
          </h5>
        );
      }

      // 3. Sub-level list items (indented by 2+ spaces or tabs: '  - ', '  * ', '  • ', '  + ')
      const subBulletMatch = rawLine.match(/^\s{2,}[-*•+]\s+(.*)$/);
      if (subBulletMatch) {
        return (
          <div key={i} style={{ 
            display: 'flex', 
            gap: '8px', 
            margin: '3px 0 3px 24px', 
            alignItems: 'baseline', 
            lineHeight: '1.5' 
          }}>
            <span style={{ color: 'var(--brand-accent)', fontWeight: 'bold', fontSize: '0.9em', flexShrink: 0 }}>–</span>
            <div style={{ color: 'var(--text-secondary)', flex: 1 }}>{parseInlineTokens(subBulletMatch[1])}</div>
          </div>
        );
      }

      // 4. Root-level bullet items ('- ', '* ', '• ')
      const rootBulletMatch = rawLine.match(/^[-*•]\s+(.*)$/);
      if (rootBulletMatch) {
        return (
          <div key={i} style={{ 
            display: 'flex', 
            gap: '8px', 
            margin: '4px 0 4px 10px', 
            alignItems: 'baseline', 
            lineHeight: '1.55' 
          }}>
            <span style={{ color: 'var(--brand-accent)', fontWeight: 'bold', fontSize: '1.1em', lineHeight: 1, flexShrink: 0 }}>•</span>
            <div style={{ color: 'var(--text-primary)', flex: 1 }}>{parseInlineTokens(rootBulletMatch[1])}</div>
          </div>
        );
      }

      // 5. Numbered list items ('1. ', '2. ', etc.)
      const numMatch = rawLine.match(/^(\s*)(\d+)\.\s+(.*)$/);
      if (numMatch) {
        const isIndented = numMatch[1].length >= 2;
        return (
          <div key={i} style={{ 
            display: 'flex', 
            gap: '8px', 
            margin: `4px 0 4px ${isIndented ? '24px' : '10px'}`, 
            alignItems: 'baseline', 
            lineHeight: '1.55' 
          }}>
            <span style={{ color: 'var(--brand-accent)', fontWeight: '700', minWidth: '18px', flexShrink: 0 }}>{numMatch[2]}.</span>
            <div style={{ color: 'var(--text-primary)', flex: 1 }}>{parseInlineTokens(numMatch[3])}</div>
          </div>
        );
      }

      // 6. Normal paragraph
      return (
        <p key={i} style={{ margin: '4px 0', lineHeight: '1.6', color: 'var(--text-primary)' }}>
          {parseInlineTokens(rawLine)}
        </p>
      );
    });
  };

  const hasChatStarted = messages.length > 0;

  const suggestionItems = [
    {
      id: 'thesis',
      emoji: '🎓',
      text: language === 'vi' ? 'Kiểm tra điều kiện nhận Đồ án tốt nghiệp tại HUST' : 'Check graduation thesis criteria at HUST',
      query: language === 'vi'
        ? 'Điều kiện để được nhận Đồ án tốt nghiệp tại HUST là gì? Em cần chuẩn bị những gì?'
        : 'What are the requirements for Graduation Thesis and degree completion at HUST?'
    },
    {
      id: 'cpa',
      emoji: '📈',
      text: language === 'vi' ? 'Kế hoạch cải thiện CPA lên bằng Khá (≥ 2.50)' : 'CPA improvement plan to reach Good standing (≥ 2.50)',
      query: language === 'vi'
        ? 'CPA hiện tại của em đang là 2.26. Em cần làm gì và học cải thiện những môn nào để kéo CPA lên bằng Khá?'
        : 'My current CPA is 2.26. Which courses should I retake to raise my CPA to Good standing?'
    },
    {
      id: 'warning',
      emoji: '⚠️',
      text: language === 'vi' ? 'Quy chế Cảnh báo học tập mức 1 & mức 2 của HUST' : 'HUST Academic Warning Level 1 & 2 regulations',
      query: language === 'vi'
        ? 'Quy chế cảnh báo học tập mức 1 và mức 2 của Đại học Bách Khoa Hà Nội quy định như thế nào?'
        : 'What are the rules and credit limits for Academic Warning Level 1 and 2 at HUST?'
    },
    {
      id: 'enroll',
      emoji: '📅',
      text: language === 'vi' ? 'Gợi ý danh sách môn nên đăng ký trong kỳ tới' : 'Course registration suggestions for next term',
      query: language === 'vi'
        ? 'Gợi ý cho em danh sách các môn nên đăng ký trong kỳ tới dựa trên tiến độ học tập hiện tại'
        : 'Which courses should I register for next semester based on my current progress?'
    }
  ];

  const renderInputCapsule = (isCentered = false) => (
    <div style={{
      display: 'flex',
      alignItems: 'flex-end',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-subtle)',
      borderRadius: '26px',
      padding: '8px 10px 8px 12px',
      boxShadow: isCentered ? '0 4px 24px rgba(0, 0, 0, 0.06)' : 'var(--shadow-md)',
      backdropFilter: 'blur(20px)',
      transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
      width: '100%',
      boxSizing: 'border-box'
    }}>
      {/* Attachment Button (+) like ChatGPT */}
      <button
        type="button"
        onClick={onOpenImport}
        title={language === 'vi' ? 'Dán / Nhập bảng điểm CTT Bách Khoa' : 'Attach / Paste HUST CTT Transcript'}
        style={{
          width: '36px',
          height: '36px',
          minWidth: '36px',
          minHeight: '36px',
          background: 'transparent',
          border: 'none',
          color: 'var(--text-muted)',
          cursor: 'pointer',
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: 0,
          marginRight: '4px',
          flexShrink: 0,
          transition: 'color 0.15s ease'
        }}
        onMouseEnter={e => e.currentTarget.style.color = 'var(--text-primary)'}
        onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}
      >
        <Plus size={19} />
      </button>

      {/* Auto-expanding Textarea (up to 160px height) */}
      <textarea
        ref={textareaRef}
        rows={1}
        autoFocus={isCentered}
        value={input}
        onChange={e => {
          setInput(e.target.value);
          e.target.style.height = '36px';
          const scrollH = e.target.scrollHeight;
          if (scrollH > 36) {
            e.target.style.height = `${Math.min(scrollH, 160)}px`;
          }
        }}
        onKeyDown={handleKeyDown}
        placeholder={isListening 
          ? (language === 'vi' ? 'Đang lắng nghe... Hãy nói câu hỏi của bạn' : 'Listening... Speak now') 
          : (language === 'vi' ? 'Hỏi bất cứ điều gì' : 'Ask anything')}
        style={{
          flex: 1,
          background: 'transparent',
          border: 'none',
          color: isListening ? 'var(--brand-accent)' : 'var(--text-primary)',
          fontWeight: isListening ? '600' : 'normal',
          fontSize: '0.96rem',
          outline: 'none',
          fontFamily: 'inherit',
          resize: 'none',
          lineHeight: '20px',
          height: '36px',
          minHeight: '36px',
          maxHeight: '160px',
          boxSizing: 'border-box',
          overflowY: (textareaRef.current && textareaRef.current.scrollHeight > 160) ? 'auto' : 'hidden',
          padding: '8px 4px',
          margin: '0 8px 0 2px',
          display: 'block'
        }}
      />

      {/* Microphone Voice Button (ChatGPT/Gemini Style) */}
      <button
        onClick={toggleListening}
        type="button"
        title={isListening 
          ? (language === 'vi' ? 'Dừng ghi âm' : 'Stop recording') 
          : (language === 'vi' ? 'Dùng Giọng nói' : 'Voice input')}
        style={{
          width: '36px',
          height: '36px',
          minWidth: '36px',
          minHeight: '36px',
          borderRadius: '50%',
          background: isListening ? 'var(--hust-red)' : 'transparent',
          color: isListening ? '#fff' : 'var(--text-muted)',
          border: isListening ? '1px solid var(--hust-red)' : 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
          flexShrink: 0,
          margin: 0,
          marginRight: '6px',
          boxShadow: isListening ? '0 0 12px rgba(213, 19, 42, 0.6)' : 'none'
        }}
        onMouseEnter={e => {
          if (!isListening) {
            e.currentTarget.style.color = 'var(--text-primary)';
            e.currentTarget.style.background = 'var(--sidebar-hover)';
          }
        }}
        onMouseLeave={e => {
          if (!isListening) {
            e.currentTarget.style.color = 'var(--text-muted)';
            e.currentTarget.style.background = 'transparent';
          }
        }}
      >
        {isListening ? <MicOff size={17} /> : <Mic size={17} />}
      </button>

      {/* Circular Send Button */}
      <button
        onClick={() => handleSend()}
        disabled={!input.trim() || loading}
        type="button"
        title={language === 'vi' ? 'Gửi tin nhắn (Enter)' : 'Send message (Enter)'}
        style={{
          width: '36px',
          height: '36px',
          minWidth: '36px',
          minHeight: '36px',
          borderRadius: '50%',
          background: input.trim() ? 'var(--hust-red)' : 'var(--sidebar-hover)',
          color: input.trim() ? '#fff' : 'var(--text-muted)',
          border: 'none',
          cursor: input.trim() && !loading ? 'pointer' : 'default',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transition: 'all 0.2s ease',
          flexShrink: 0,
          margin: 0,
          boxShadow: input.trim() ? '0 2px 10px rgba(213, 19, 42, 0.4)' : 'none'
        }}
      >
        <Send size={15} />
      </button>
    </div>
  );

  // 🌟 ChatGPT Empty State: Title, Input Capsule, and 4 Suggestion Cards
  if (!hasChatStarted) {
    return (
      <div style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'safe center',
        padding: '24px 20px',
        minHeight: 0,
        overflowY: 'auto',
        position: 'relative',
        background: 'transparent'
      }}>
        <div style={{
          maxWidth: '780px',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '20px',
          flexShrink: 0
        }}>
          {/* Header Title */}
          <StudentWelcome language={language} />
          <h1 style={{
            fontSize: '1.9rem',
            fontWeight: '600',
            color: 'var(--text-primary)',
            letterSpacing: '-0.02em',
            margin: '0 0 2px 0',
            textAlign: 'center'
          }}>
            {language === 'vi' ? 'Chúng ta nên bắt đầu từ đâu?' : 'Where should we start?'}
          </h1>

          {/* Centered Input Capsule */}
          <div style={{ width: '100%' }}>
            {renderInputCapsule(true)}
          </div>

          {/* Compact Suggestion Row / List (ChatGPT Minimal Style) */}
          <div style={{
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-start',
            gap: '2px',
            marginTop: '2px',
            padding: '0 6px'
          }}>
            {suggestionItems.map(item => (
              <button
                key={item.id}
                onClick={() => !loading && handleSend(item.query)}
                className="apple-press"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '7px 12px',
                  borderRadius: '10px',
                  border: 'none',
                  background: 'transparent',
                  color: 'var(--text-muted)',
                  fontSize: '0.88rem',
                  cursor: loading ? 'default' : 'pointer',
                  textAlign: 'left',
                  width: '100%',
                  transition: 'all 0.15s ease'
                }}
                onMouseEnter={e => {
                  if (!loading) {
                    e.currentTarget.style.background = 'var(--sidebar-hover)';
                    e.currentTarget.style.color = 'var(--text-primary)';
                  }
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = 'transparent';
                  e.currentTarget.style.color = 'var(--text-muted)';
                }}
              >
                <span style={{ fontSize: '0.96rem', flexShrink: 0, lineHeight: 1 }}>{item.emoji}</span>
                <span style={{
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap'
                }}>
                  {item.text}
                </span>
              </button>
            ))}
          </div>

        </div>
      </div>
    );
  }

  // 🌟 Active Chat View (Messages Stream + Bottom Docked Capsule)
  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      position: 'relative',
      background: 'transparent'
    }}>
      {/* Messages Scroll Area */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px 20px 140px',
        display: 'flex',
        flexDirection: 'column'
      }}>
        <div style={{ maxWidth: '820px', width: '100%', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* Chat Message Stream */}
          {messages.map((msg, index) => {
            const isUser = msg.role === 'user';
            
            if (isUser) {
              return (
                <div 
                  key={index} 
                  className="apple-bubble-user"
                  style={{
                    display: 'flex',
                    justifyContent: 'flex-end',
                    width: '100%',
                    margin: '6px 0 12px 0'
                  }}
                >
                  <div style={{
                    maxWidth: '80%',
                    padding: '12px 20px',
                    borderRadius: '20px',
                    background: 'var(--chat-user-bubble)',
                    border: '1px solid var(--chat-user-bubble-border)',
                    color: 'var(--text-primary)',
                    fontSize: '0.96rem',
                    fontWeight: '500',
                    lineHeight: '1.55',
                    wordBreak: 'break-word',
                    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)'
                  }}>
                    {msg.content}
                  </div>
                </div>
              );
            }

            // 🌟 AI Assistant Response: Apple-style fluid entrance
            return (
              <div 
                key={index} 
                className="apple-bubble-ai"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'flex-start',
                  width: '100%',
                  margin: '6px 0 18px 0'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
                  <BrandLogo size={32} decorative />
                  <span style={{ fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-secondary)' }}>
                    HUST Advisor
                  </span>
                </div>
                {/* AI Text Content */}
                <div style={{
                  width: '100%',
                  color: 'var(--text-primary)',
                  fontSize: '0.95rem',
                  lineHeight: '1.65',
                  wordBreak: 'break-word'
                }}>
                  {renderFormattedText(msg.content)}

                  {/* RAG Document Sources Badge */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div style={{
                      marginTop: '14px',
                      paddingTop: '10px',
                      borderTop: '1px dashed var(--border-subtle)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px'
                    }}>
                      <div style={{ 
                        display: 'flex', 
                        alignItems: 'center', 
                        gap: '6px', 
                        color: 'var(--brand-accent)',
                        fontSize: '0.78rem', 
                        fontWeight: '700' 
                      }}>
                        <BookOpen size={13} />
                        <span>{language === 'vi' ? 'Nguồn tài liệu trích dẫn:' : 'Cited Documents:'}</span>
                        {msg.model_used && (
                          <span style={{
                            marginLeft: 'auto',
                            fontSize: '0.7rem',
                            color: 'var(--text-muted)',
                            background: 'var(--sidebar-hover)',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontFamily: 'monospace'
                          }}>
                            {msg.model_used}
                          </span>
                        )}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {msg.sources.map((s, idx) => {
                          const rawName = s.source || s.title || 'Quy chế HUST';
                          const cleanName = String(rawName).replace(/\.(md|txt|pdf)$/i, '').replace(/_/g, ' ');
                          return (
                            <span 
                              key={idx} 
                              title={s.title || cleanName}
                              style={{
                                fontSize: '0.74rem',
                                background: 'rgba(213, 19, 42, 0.08)',
                                color: 'var(--text-secondary)',
                                border: '1px solid rgba(213, 19, 42, 0.2)',
                                padding: '3px 8px',
                                borderRadius: '6px',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                            >
                              📜 {cleanName}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>

                {/* ChatGPT-style Action Row (Copy, Thumbs, Retry) */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  marginTop: '10px',
                  color: 'var(--text-muted)'
                }}>
                  <button
                    onClick={() => copyToClipboard(msg.content, index)}
                    title={language === 'vi' ? 'Sao chép' : 'Copy'}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '6px',
                      borderRadius: '6px',
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
                      e.currentTarget.style.color = 'var(--text-muted)';
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    {copiedIndex === index ? <Check size={15} color="var(--success)" /> : <Copy size={15} />}
                  </button>

                  <button
                    title={language === 'vi' ? 'Phản hồi tốt' : 'Good response'}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '6px',
                      borderRadius: '6px',
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
                      e.currentTarget.style.color = 'var(--text-muted)';
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <ThumbsUp size={15} />
                  </button>

                  <button
                    title={language === 'vi' ? 'Phản hồi chưa tốt' : 'Bad response'}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '6px',
                      borderRadius: '6px',
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
                      e.currentTarget.style.color = 'var(--text-muted)';
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <ThumbsDown size={15} />
                  </button>

                  <button
                    onClick={() => {
                      const prevUserMsg = messagesRef.current.slice(0, index).reverse().find(m => m.role === 'user');
                      if (prevUserMsg) handleSend(prevUserMsg.content);
                    }}
                    title={language === 'vi' ? 'Tạo lại câu trả lời' : 'Regenerate'}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '6px',
                      borderRadius: '6px',
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
                      e.currentTarget.style.color = 'var(--text-muted)';
                      e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    <RotateCcw size={15} />
                  </button>
                </div>

                {/* Suggestion Chips */}
                {msg.suggested_actions && msg.suggested_actions.length > 0 && (
                  <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '8px',
                    marginTop: '10px'
                  }}>
                    {msg.suggested_actions.map((act, i) => (
                      <button
                        key={i}
                        className="apple-chip"
                        onClick={() => handleSend(act)}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '6px 14px',
                          borderRadius: '16px',
                          border: '1px solid var(--border-subtle)',
                          background: 'var(--bg-card)',
                          color: 'var(--text-secondary)',
                          fontSize: '0.8rem',
                          cursor: 'pointer'
                        }}
                        onMouseEnter={e => {
                          e.currentTarget.style.background = 'var(--sidebar-hover)';
                          e.currentTarget.style.color = 'var(--text-primary)';
                        }}
                        onMouseLeave={e => {
                          e.currentTarget.style.background = 'var(--bg-card)';
                          e.currentTarget.style.color = 'var(--text-secondary)';
                        }}
                      >
                        <Sparkles size={12} color="var(--brand-accent)" />
                        <span>{act}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            );
          })}

          {/* Loading Indicator with Apple Siri Fluid Wave */}
          {loading && (
            <div className="apple-bubble-ai" style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' }}>
              <BrandLogo size={32} />
              <div style={{
                padding: '10px 18px',
                borderRadius: '20px',
                background: 'var(--bg-card)',
                backdropFilter: 'blur(20px)',
                border: '1px solid var(--border-subtle)',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                color: 'var(--text-secondary)',
                fontSize: '0.85rem',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.2)'
              }}>
                <div className="apple-siri-indicator">
                  <span className="apple-siri-dot" />
                  <span className="apple-siri-dot" />
                  <span className="apple-siri-dot" />
                </div>
                <span style={{ fontWeight: '500' }}>
                  {language === 'vi' 
                    ? 'AI đang đối chiếu CTĐT & quy chế Bách Khoa...' 
                    : 'AI is evaluating HUST regulations and student transcript...'}
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Floating ChatGPT / Gemini Input Capsule */}
      <div style={{
        position: 'absolute',
        bottom: 0,
        left: 0,
        right: 0,
        background: 'linear-gradient(to top, var(--bg-dark) 70%, transparent 100%)',
        padding: '16px 20px 18px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        zIndex: 20
      }}>
        <div style={{ maxWidth: '820px', width: '100%', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {renderInputCapsule(false)}

          <div style={{
            textAlign: 'center',
            fontSize: '0.72rem',
            color: 'var(--text-muted)',
            letterSpacing: '0.01em'
          }}>
            {language === 'vi' 
              ? 'HUST Advisor có thể đưa ra câu trả lời cần kiểm chứng. Hãy đối chiếu với trang đào tạo CTT Bách Khoa.' 
              : 'HUST Advisor may make mistakes. Verify important information with HUST CTT portal.'}
          </div>
        </div>
      </div>
    </div>
  );
}
