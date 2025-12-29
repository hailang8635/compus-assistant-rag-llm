(function () {
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function nowTime() {
    const d = new Date();
    const hh = String(d.getHours()).padStart(2, '0');
    const mm = String(d.getMinutes()).padStart(2, '0');
    return `${hh}:${mm}`;
  }

  function renderMarkdownToSafeHtml(md) {
    const text = String(md == null ? '' : md);
    if (!window.marked || !window.DOMPurify) {
      return escapeHtml(text).replace(/\n/g, '<br/>');
    }
    try {
      window.marked.setOptions({
        gfm: true,
        breaks: true,
        mangle: false,
        headerIds: false
      });
      const rawHtml = window.marked.parse(text);
      return window.DOMPurify.sanitize(rawHtml, { USE_PROFILES: { html: true } });
    } catch (e) {
      return escapeHtml(text).replace(/\n/g, '<br/>');
    }
  }

  function scrollToBottom() {
    const chat = document.getElementById('chat');
    if (!chat) return;
    chat.scrollTo({ top: chat.scrollHeight, behavior: 'smooth' });
  }

  function addMessage(role, text, meta) {
    const chatInner = document.getElementById('chatInner');
    const wrap = document.createElement('div');
    wrap.className = `msg ${role}`;

    const avatar = document.createElement('div');
    avatar.className = `avatar ${role === 'ai' ? 'ai' : 'user'}`;
    avatar.textContent = role === 'ai' ? 'AI' : '我';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    if (role === 'ai') {
      bubble.innerHTML = renderMarkdownToSafeHtml(text);
    } else {
      bubble.innerHTML = escapeHtml(String(text == null ? '' : text)).replace(/\n/g, '<br/>');
    }

    if (meta) {
      const small = document.createElement('span');
      small.className = 'small';
      small.textContent = meta;
      bubble.appendChild(small);
    }

    if (role === 'user') {
      wrap.appendChild(bubble);
      wrap.appendChild(avatar);
    } else {
      wrap.appendChild(avatar);
      wrap.appendChild(bubble);
    }

    chatInner.appendChild(wrap);
    scrollToBottom();
  }

  function addTyping() {
    const chatInner = document.getElementById('chatInner');
    const wrap = document.createElement('div');
    wrap.className = 'msg ai';
    wrap.id = 'typingRow';

    const avatar = document.createElement('div');
    avatar.className = 'avatar ai';
    avatar.textContent = 'AI';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';

    const typing = document.createElement('span');
    typing.className = 'typing';
    typing.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';

    bubble.appendChild(typing);
    wrap.appendChild(avatar);
    wrap.appendChild(bubble);
    chatInner.appendChild(wrap);
    scrollToBottom();
  }

  function removeTyping() {
    const row = document.getElementById('typingRow');
    if (row) row.remove();
  }

  function showModal(title, body) {
    document.getElementById('modalTitle').textContent = title;
    document.getElementById('modalBody').textContent = body;
    document.getElementById('modal').classList.add('show');
  }

  function hideModal() {
    document.getElementById('modal').classList.remove('show');
  }

  function setSending(sending) {
    document.getElementById('sendBtn').disabled = sending;
    document.getElementById('prompt').disabled = sending;
  }

  function normalizeMessage(msg) {
    return String(msg || '').replace(/\r\n/g, '\n').trim();
  }

  function autoGrowTextarea(el) {
    el.style.height = '0px';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  }

  async function send() {
    const textarea = document.getElementById('prompt');
    const msg = normalizeMessage(textarea.value);
    if (!msg) return;

    if (msg === '人工') {
      showModal('人工客服', '请联系百事通同学：zhangdreamer@126.com');
      textarea.value = '';
      autoGrowTextarea(textarea);
      textarea.focus();
      return;
    }

    addMessage('user', msg, `发送于 ${nowTime()}`);
    textarea.value = '';
    autoGrowTextarea(textarea);
    setSending(true);
    addTyping();

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      const data = await resp.json();
      removeTyping();

      if (data && data.type === 'human') {
        showModal('人工客服', data.answer || '请联系学长：zhangdreamer@126.com');
        return;
      }
      const answer = (data && data.answer) ? String(data.answer) : '（未获取到答案）';
      addMessage('ai', answer, `回答于 ${nowTime()}`);
    } catch (e) {
      removeTyping();
      addMessage('ai', `请求失败：${String(e)}`, `错误于 ${nowTime()}`);
    } finally {
      setSending(false);
      textarea.focus();
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    const textarea = document.getElementById('prompt');
    const sendBtn = document.getElementById('sendBtn');
    const newChatBtn = document.getElementById('newChatBtn');

    addMessage(
      'ai',
      '你好！我是**上海大学校园百事通**。\n\n' +
        '- 你可以问我：图书借阅与期限、医保报销、研究生学分、VPN等任意与在校生活有关的问题～\n' +
        '- 当问题与 `docs/*.md` 有关时，我会自动附带内容用于更准确回答\n\n' +
        '输入“人工”可获取人工联系方式。',
      '提示'
    );

    sendBtn.addEventListener('click', send);

    textarea.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        send();
      }
    });

    textarea.addEventListener('input', function () {
      autoGrowTextarea(textarea);
    });

    newChatBtn.addEventListener('click', function () {
      document.getElementById('chatInner').innerHTML = '';
      addMessage('ai', '新的对话已开始。你想咨询什么问题？', '提示');
      textarea.value = '';
      autoGrowTextarea(textarea);
      textarea.focus();
    });

    document.getElementById('modalClose').addEventListener('click', hideModal);
    document.getElementById('modalOk').addEventListener('click', hideModal);
    document.getElementById('modal').addEventListener('click', function (e) {
      if (e.target && e.target.id === 'modal') hideModal();
    });

    autoGrowTextarea(textarea);
    textarea.focus();
  });
})();


