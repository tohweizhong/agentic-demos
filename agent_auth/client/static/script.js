// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

$(function() {
  const $messagesContainer = $('#messages-container');
  const $userInput = $('#user-input');
  const $sendBtn = $('#send-btn');

  let currentSessionId = null;

  // ==========================================================================
  // agentic-demos change: 3LO flow view, step highlight, timings, loading
  // states, and a robust resume after consent.
  // ==========================================================================

  // Parties in the diagram, left to right.
  const FLOW_PARTIES = [
    {id: 'user', name: 'User', sub: '(browser)'},
    {id: 'client', name: 'Demo client', sub: '(Cloud Run + IAP)'},
    {id: 'agent', name: 'Agent', sub: '(Agent Runtime, SPIFFE ID)'},
    {id: 'am', name: 'Auth Manager', sub: '(agentidentity)'},
    {id: 'gh', name: 'GitHub', sub: '(consent + token)'},
    {id: 'mcp', name: 'GitHub MCP', sub: '(server)'},
  ];

  // The 12 steps of the flow. "from" and "to" are party IDs.
  const FLOW_STEPS = [
    {n: 1, from: 'user', to: 'client', text: 'User sends prompt (IAP login gives user ID)'},
    {n: 2, from: 'client', to: 'agent', text: 'Client calls agent stream_query'},
    {n: 3, from: 'agent', to: 'am', text: 'Agent asks Auth Manager for a token for this user (no token yet)'},
    {n: 4, from: 'agent', to: 'client', text: 'Agent returns adk_request_credential (consent URL + nonce)'},
    {n: 5, from: 'client', to: 'gh', text: 'Client opens popup to GitHub consent. Nonce kept in a cookie'},
    {n: 6, from: 'user', to: 'gh', text: 'User approves on github.com (password only on GitHub)'},
    {n: 7, from: 'gh', to: 'am', text: 'GitHub sends the code to the Auth Manager redirectUrl (not to the client)'},
    {n: 8, from: 'am', to: 'am', text: 'Auth Manager swaps code for token, stores it in its vault'},
    {n: 9, from: 'am', to: 'client', text: 'Browser goes to the client continue_uri /validateUserId'},
    {n: 10, from: 'client', to: 'am', text: 'Client calls credentials:finalize with validation state + nonce'},
    {n: 11, from: 'agent', to: 'mcp', text: 'Agent gets the token from Auth Manager and calls the GitHub MCP server'},
    {n: 12, from: 'agent', to: 'user', text: 'Answer streams back to the user'},
  ];

  const SVG_NS = 'http://www.w3.org/2000/svg';
  const svgEl = (tag, attrs, text) => {
    const el = document.createElementNS(SVG_NS, tag);
    Object.entries(attrs || {}).forEach(([k, v]) => el.setAttribute(k, v));
    if (text !== undefined) el.textContent = text;
    return el;
  };

  // Draws the flow as an inline SVG sequence diagram, and the text list.
  const buildFlowDiagram = () => {
    const colW = 160;
    const left = 80;
    const top = 70;
    const rowH = 40;
    const width = left * 2 + colW * (FLOW_PARTIES.length - 1);
    const height = top + rowH * FLOW_STEPS.length + 40;
    const x = {};
    FLOW_PARTIES.forEach((p, i) => { x[p.id] = left + i * colW; });

    const svg = svgEl('svg', {
      viewBox: `0 0 ${width} ${height}`, role: 'img',
      'aria-labelledby': 'flow-title flow-desc', class: 'flow-svg'});
    svg.appendChild(svgEl('title', {id: 'flow-title'}, '3LO flow diagram'));
    svg.appendChild(svgEl('desc', {id: 'flow-desc'},
        'Sequence diagram with six parties and twelve numbered steps. ' +
        'The list under the diagram has the same steps as text.'));
    const defs = svgEl('defs');
    ['normal', 'active'].forEach((kind) => {
      const marker = svgEl('marker', {
        id: `arrow-${kind}`, viewBox: '0 0 10 10', refX: '9', refY: '5',
        markerWidth: '7', markerHeight: '7', orient: 'auto-start-reverse'});
      marker.appendChild(svgEl('path', {d: 'M0,0 L10,5 L0,10 z', class: `arrow-head-${kind}`}));
      defs.appendChild(marker);
    });
    svg.appendChild(defs);

    FLOW_PARTIES.forEach((p) => {
      svg.appendChild(svgEl('line', {
        x1: x[p.id], y1: top - 10, x2: x[p.id], y2: height - 10, class: 'lifeline'}));
      svg.appendChild(svgEl('rect', {
        x: x[p.id] - 70, y: 6, width: 140, height: 46, rx: 8, class: 'party-box'}));
      svg.appendChild(svgEl('text', {x: x[p.id], y: 25, class: 'party-name'}, p.name));
      svg.appendChild(svgEl('text', {x: x[p.id], y: 42, class: 'party-sub'}, p.sub));
    });

    FLOW_STEPS.forEach((s, i) => {
      const y = top + rowH * i + 20;
      const g = svgEl('g', {class: 'flow-step', id: `flow-step-${s.n}`});
      if (s.from === s.to) {
        const x0 = x[s.from];
        g.appendChild(svgEl('path', {
          d: `M${x0},${y - 8} h40 v16 h-38`, class: 'step-line', fill: 'none',
          'marker-end': 'url(#arrow-normal)'}));
        g.appendChild(svgEl('text', {x: x0 + 48, y: y + 4, class: 'step-label', 'text-anchor': 'start'},
            `${s.n}. ${s.text}`));
      } else {
        const x1 = x[s.from];
        const x2 = x[s.to];
        const dir = x2 > x1 ? 1 : -1;
        g.appendChild(svgEl('line', {
          x1: x1 + dir * 4, y1: y, x2: x2 - dir * 4, y2: y, class: 'step-line',
          'marker-end': 'url(#arrow-normal)'}));
        const midX = (x1 + x2) / 2;
        g.appendChild(svgEl('text', {x: midX, y: y - 6, class: 'step-label'},
            `${s.n}. ${s.text}`));
      }
      // Text marker, so that the highlight does not depend on color only.
      g.appendChild(svgEl('text', {x: 8, y: y + 4, class: 'step-now', 'text-anchor': 'start'}, 'NOW'));
      svg.appendChild(g);
    });

    $('#flow-diagram').empty().append(svg);

    const $list = $('#flow-steps').empty();
    FLOW_STEPS.forEach((s) => {
      $list.append($('<li>').attr('id', `flow-item-${s.n}`).attr('value', s.n).text(s.text));
    });
  };

  const STEP_NAMES = {
    '1,2': 'Prompt sent',
    '4,5': 'Consent request received',
    '6': 'Waiting for approval on GitHub',
    '7,8,9,10': 'GitHub redirect, token stored, finalize',
    '11': 'Agent calls GitHub with the token',
    '12': 'Answer received',
  };
  let currentSteps = [];

  // Highlights the given step numbers in the diagram and the list.
  const setStep = (steps, label) => {
    currentSteps = steps;
    $('.flow-step').removeClass('active');
    $('#flow-steps li').removeAttr('aria-current').removeClass('active');
    steps.forEach((n) => {
      $(`#flow-step-${n}`).addClass('active');
      $(`#flow-item-${n}`).attr('aria-current', 'step').addClass('active');
    });
    const name = label || STEP_NAMES[steps.join(',')] || '';
    $('#step-chip').text(steps.length ?
        `3LO step ${steps.join('-')}: ${name}` : `3LO step: ${label || 'none'}`);
  };

  // ---- Timings of the last run. Browser memory only. ----
  const TIMING_EVENTS = [
    {key: 'send', label: 'Steps 1-2: prompt sent'},
    {key: 'credential', label: 'Steps 3-4: consent request received'},
    {key: 'popup', label: 'Steps 5-6: popup opened'},
    {key: 'validated', label: 'Steps 7-10: GitHub redirect, token stored, finalize'},
    {key: 'resume', label: 'Step 11: resume sent to the agent'},
    {key: 'firstText', label: 'Step 12: first answer text'},
    {key: 'lastText', label: 'Step 12: last answer text'},
  ];
  let timings = {};

  const fmtLocal = (ms) => {
    const d = new Date(ms);
    const t = d.toLocaleTimeString('en-GB', {hour12: false});
    const zonePart = new Intl.DateTimeFormat(undefined, {timeZoneName: 'short'})
        .formatToParts(d).find((p) => p.type === 'timeZoneName');
    return `${t}${zonePart ? ' ' + zonePart.value : ''}`;
  };

  const renderTimings = () => {
    const $body = $('#timings-body').empty();
    let prev = null;
    let first = null;
    let last = null;
    TIMING_EVENTS.forEach((e) => {
      const t = timings[e.key];
      if (t === undefined) return;
      if (first === null) first = t;
      last = t;
      const delta = prev === null ? '-' : ((t - prev) / 1000).toFixed(1);
      $body.append($('<tr>')
          .append($('<td>').text(e.label))
          .append($('<td>').text(fmtLocal(t)))
          .append($('<td>').text(delta)));
      prev = t;
    });
    if (first === null) {
      $body.append($('<tr>').append($('<td>').attr('colspan', 3)
          .text('No run yet. Send a message in the Playground.')));
    } else {
      $body.append($('<tr>').addClass('timings-total')
          .append($('<td>').text('Total'))
          .append($('<td>').text(''))
          .append($('<td>').text(((last - first) / 1000).toFixed(1))));
    }
  };

  const markTiming = (key, overwrite = false) => {
    if (overwrite || timings[key] === undefined) {
      timings[key] = Date.now();
      renderTimings();
    }
  };


  // ---- Markdown rendering of agent answers. ----
  // The model text is never trusted as HTML. marked escapes raw HTML in the
  // text, and DOMPurify sanitizes the result. Links open in a new tab.
  const escapeHtml = (t) => String(t)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  if (window.marked) {
    window.marked.use({
      gfm: true,
      breaks: true,
      renderer: {
        html(token) {
          return escapeHtml(token.raw !== undefined ? token.raw : token.text);
        },
      },
    });
  }
  if (window.DOMPurify) {
    window.DOMPurify.addHook('afterSanitizeAttributes', (node) => {
      if (node.tagName === 'A') {
        node.setAttribute('target', '_blank');
        node.setAttribute('rel', 'noopener noreferrer');
      }
    });
  }
  const renderMarkdown = (text) => {
    if (!window.marked || !window.DOMPurify) return null;
    return window.DOMPurify.sanitize(window.marked.parse(text), {
      FORBID_TAGS: ['style', 'form', 'input', 'iframe', 'img'],
      FORBID_ATTR: ['style'],
    });
  };
  // While the stream runs, answers show as plain text. When the stream ends,
  // this function renders each answer as Markdown, once.
  const finalizeAnswers = ($container) => {
    $container.find('.answer-text[data-md-pending="1"]').each(function() {
      const html = renderMarkdown($(this).data('raw') || '');
      if (html !== null) {
        this.innerHTML = html;
        $(this).addClass('markdown');
      }
      $(this).attr('data-md-pending', '0');
    });
  };
  const appendAnswer = ($container, text) => {
    $container.append($('<div>').addClass('answer-text')
        .attr('data-md-pending', '1').data('raw', text).text(text));
  };

  // ---- Loading states in the chat. ----
  const waitTimers = new Set();
  const clearWaits = () => {
    waitTimers.forEach((t) => clearTimeout(t));
    waitTimers.clear();
    $('.wait-indicator').remove();
  };
  const showWait = ($container, kind, text) => {
    const $w = $('<div>').addClass('wait-indicator')
                   .attr({'role': 'status', 'aria-live': 'polite'});
    if (kind === 'dots') {
      $w.append($('<span>').addClass('typing-dots').attr('aria-hidden', 'true')
          .append('<span></span><span></span><span></span>'));
    } else {
      $w.append($('<span>').addClass('material-symbols-outlined icon-spin')
          .attr('aria-hidden', 'true').text('sync'));
    }
    $w.append($('<span>').addClass('wait-text').text(text));
    $container.append($w);
    const timer = setTimeout(() => {
      $w.append($('<div>').addClass('wait-hint')
          .text('This can take up to 2 minutes on the first run.'));
      waitTimers.delete(timer);
    }, 30000);
    waitTimers.add(timer);
    $messagesContainer.scrollTop($messagesContainer.prop('scrollHeight'));
    return $w;
  };
  // Changes the text of the last loading state, or adds one.
  const setWaitText = ($container, text) => {
    const $t = $container.find('.wait-indicator .wait-text').last();
    if ($t.length) {
      $t.text(text);
    } else {
      showWait($container, 'dots', text);
    }
  };

  // ---- Resume after consent, exactly once. ----
  // The resume starts when the first of these signals arrives:
  // - a message from the /validateUserId page (BroadcastChannel,
  //   window.postMessage, or a localStorage "storage" event),
  // - the popup window is closed.
  let pendingAuth = null;
  // Each chat request gets a number. Only the latest request clears the
  // loading states when its stream ends.
  let latestRequestId = 0;

  const completeAuth = (source) => {
    if (!pendingAuth || pendingAuth.done) return;
    pendingAuth.done = true;
    clearInterval(pendingAuth.timer);
    const resume = pendingAuth.resume;
    pendingAuth = null;
    console.log(`Consent complete (signal: ${source}). Resuming once.`);
    resume();
  };

  const isAuthMessage = (data) => data && data.type === 'agent-auth-complete';
  try {
    const channel = new BroadcastChannel('agent-auth');
    channel.onmessage = (e) => { if (isAuthMessage(e.data)) completeAuth('broadcast'); };
  } catch (e) {
    console.warn('BroadcastChannel is not available.');
  }
  window.addEventListener('message', (e) => {
    if (e.origin === window.location.origin && isAuthMessage(e.data)) {
      completeAuth('postMessage');
    }
  });
  window.addEventListener('storage', (e) => {
    if (e.key === 'agent-auth-complete') completeAuth('storage');
  });

  // ---- Presentation mode (track playground_layout_20261108). ----
  // The button folds the configuration panel to a thin bar. The browser
  // remembers the choice.
  const PRESENTATION_KEY = 'agentAuthPresentation';

  /**
   * Folds or unfolds the configuration panel.
   * @param {boolean} folded True to fold the panel.
   */
  const setPresentationMode = (folded) => {
    const label = folded ? 'Unfold the configuration panel' :
        'Fold the configuration panel (presentation mode)';
    $('#settings-sidebar').toggleClass('folded', folded);
    $('#presentation-toggle').attr({
      'aria-expanded': String(!folded),
      'aria-label': label,
      'title': label,
    });
    $('#presentation-toggle .material-symbols-outlined')
        .text(folded ? 'left_panel_open' : 'left_panel_close');
    localStorage.setItem(PRESENTATION_KEY, folded ? '1' : '0');
  };
  setPresentationMode(localStorage.getItem(PRESENTATION_KEY) === '1');
  $('#presentation-toggle').on('click', () => {
    setPresentationMode(!$('#settings-sidebar').hasClass('folded'));
  });

  // ---- Step mode (track step_mode_3lo_20261108). ----
  // With Step mode on, the backend runs at full speed. The page keeps the
  // agent events in a queue, and the answer stays hidden until step 12.
  const STEP_MODE_KEY = 'agentAuthStepMode';
  const $stepSwitch = $('#step-mode-switch');
  $stepSwitch.prop('checked', localStorage.getItem(STEP_MODE_KEY) === '1');
  $stepSwitch.on('change', function() {
    localStorage.setItem(STEP_MODE_KEY, this.checked ? '1' : '0');
  });

  /** @return {boolean} True when the Step mode switch is on. */
  const isStepMode = () => $stepSwitch.prop('checked') === true;

  /** The Step mode run of the current prompt, or null. */
  let activeStepRun = null;

  /** Shows the queue length on the body element, for tests and debugging. */
  const setQueueCount = (n) => {
    document.body.dataset.stepQueue = String(n);
  };

  /**
   * Creates the state of one Step mode run.
   * @param {!jQuery} $bubble The hidden agent bubble of this run.
   * @return {!Object} The run state.
   */
  const createStepRun = ($bubble) => {
    const run = {
      $bubble: $bubble,
      events: 0,
      // 'consent' when Auth Manager asks for consent, 'token' when the token
      // is already stored.
      path: null,
      credential: null,
      credentialAt: null,
      consentDone: false,
      resumeStarted: false,
      answerReady: false,
      failed: false,
      sessionId: null,
      times: {},
    };
    run.onEvent = (data) => {
      run.events += 1;
      setQueueCount(run.events);
      // A tool call alone does not show the path: the tool can still ask
      // for consent. A tool result or answer text without a consent request
      // shows that Auth Manager already has the token.
      const parts = (data.content && data.content.parts) || [];
      const toolRanOrText = parts.some((p) => p.text ||
          p.function_response || p.functionResponse) || Boolean(data.text);
      if (!run.path && toolRanOrText) {
        run.path = 'token';
        run.times.agent = Date.now();
      }
      run.notify();
    };
    run.onCredential = (data) => {
      run.path = 'consent';
      run.credential = data;
      run.credentialAt = Date.now();
      run.times.agent = run.times.agent || run.credentialAt;
      run.notify();
    };
    run.onStreamEnd = () => {
      if (run.$bubble.find('.answer-text').length) {
        run.answerReady = true;
        run.times.answer = Date.now();
        if (!run.path) {
          run.path = 'token';
          run.times.agent = run.times.agent || run.times.answer;
        }
      }
      run.notify();
    };
    run.onError = () => {
      run.failed = true;
      run.$bubble.find('.wait-indicator').remove();
      $messagesContainer.append(run.$bubble);
      run.notify();
    };
    run.times.send = Date.now();
    run.shown = 0;
    run.popupOpened = false;
    run.expired = false;
    run.notify = () => updateNextButton(run);
    return run;
  };

  // ---- Step cards (Step mode). One table holds the text of each step. ----
  const STEP_CARDS = {
    1: {title: 'You send the prompt',
      text: 'The demo client gets your prompt. IAP gives your user ID.',
      who: 'You and the demo client.',
      what: 'Your browser sends the prompt. IAP adds your verified email.',
      data: 'The prompt text and your user ID (email).',
      hidden: 'No secret moves in this step.', time: 'send'},
    2: {title: 'The client calls the agent',
      text: 'The client sends the prompt to the agent on Agent Runtime.',
      who: 'The demo client and the agent.',
      what: 'The client calls stream_query on the agent.',
      data: 'The prompt, your user ID, and the session ID.',
      hidden: 'The client has no GitHub token.', time: 'send'},
    3: {title: 'The agent asks Auth Manager for a token', server: true,
      text: 'The agent uses its own identity to ask for a GitHub token for you.',
      who: 'The agent and Auth Manager.',
      what: 'The agent asks for the token of your user ID.',
      data: 'Your user ID and the auth provider name.',
      hidden: 'The agent identity credentials stay in Google Cloud.',
      time: 'agent'},
    4: {title: 'Auth Manager asks for consent',
      text: 'There is no token yet. The agent sends a consent request to the client.',
      who: 'The agent and the demo client.',
      what: 'The agent returns adk_request_credential.',
      data: 'A consent URL and a nonce. The client keeps the nonce in a cookie.',
      hidden: 'No token exists yet.', time: 'credential'},
    5: {title: 'The client opens the GitHub window',
      text: 'The client opens GitHub in a new window.',
      who: 'The demo client and your browser.',
      what: 'The browser opens the consent URL on github.com.',
      data: 'The consent URL. The nonce stays in a cookie.',
      hidden: 'The client never sees your GitHub password.', time: 'popup'},
    6: {title: 'You approve on GitHub',
      text: 'You sign in on github.com and approve the app.',
      who: 'You and GitHub.',
      what: 'GitHub asks you to approve the OAuth app.',
      data: 'Your GitHub password goes only to GitHub.',
      hidden: 'Google, the client, and the agent never see your password.',
      time: 'consent'},
    7: {title: 'GitHub sends the code to Auth Manager', server: true,
      text: 'GitHub sends an authorization code to the Auth Manager redirect URL.',
      who: 'GitHub and Auth Manager.',
      what: 'The code goes to Auth Manager, not to the client.',
      data: 'The authorization code.',
      hidden: 'The client never sees the code.', time: 'consent'},
    8: {title: 'Auth Manager stores the token', server: true,
      text: 'Auth Manager swaps the code for a token, and stores it in its vault.',
      who: 'Auth Manager and GitHub.',
      what: 'Auth Manager gets the token from GitHub.',
      data: 'The token goes into the Auth Manager vault.',
      hidden: 'The token stays in the vault.', time: 'consent'},
    9: {title: 'The browser returns to the client',
      text: 'Auth Manager sends your browser to the client page /validateUserId.',
      who: 'Auth Manager, your browser, and the demo client.',
      what: 'The browser opens the client continue URL.',
      data: 'A validation state in the URL.',
      hidden: 'The URL holds no token.', time: 'consent'},
    10: {title: 'The client finalizes the consent',
      text: 'The client calls credentials:finalize with the validation state and the nonce.',
      who: 'The demo client and Auth Manager.',
      what: 'Auth Manager checks that the same user started and finished the consent.',
      data: 'The validation state and the nonce.',
      hidden: 'The client gets no token.', time: 'consent'},
    11: {title: 'The agent calls GitHub',
      text: 'The agent gets the token from Auth Manager and calls the GitHub MCP server.',
      who: 'The agent, Auth Manager, and the GitHub MCP server.',
      what: 'The agent calls the GitHub tools with your token.',
      data: 'The token goes from Auth Manager to the agent and to GitHub.',
      hidden: 'The token never goes to your browser.', time: 'resume'},
    12: {title: 'The answer comes back',
      text: 'The agent sends the answer to the client, and the client shows it.',
      who: 'The agent, the demo client, and you.',
      what: 'The answer streams back to the chat.',
      data: 'The answer text.',
      hidden: 'The answer holds no token.', time: 'answer'},
  };
  const SKIPPED_TEXT = 'Skipped: token already stored.';
  const CONSENT_EXPIRY_DEFAULT_MS = 10 * 60 * 1000;

  /** @return {number} The time after which a consent request can expire. */
  const consentExpiryMs = () => window.STEP_MODE_CONSENT_EXPIRY_MS ||
      CONSENT_EXPIRY_DEFAULT_MS;

  /** Shows only the start of a nonce. */
  const maskNonce = (nonce) => (nonce ? `${String(nonce).slice(0, 4)}...` : '-');

  /**
   * Tells if the data for a step is ready.
   * @param {!Object} run The Step mode run.
   * @param {number} n The step number.
   * @return {?string} null when the step is ready, else a wait message.
   */
  const stepWaitReason = (run, n) => {
    if (n <= 2) {
      return null;
    }
    if (!run.path) {
      return 'Waiting for the agent...';
    }
    if (run.path === 'token') {
      if (n === 12 && !run.answerReady) {
        return 'Waiting for the answer...';
      }
      return null;
    }
    if (n <= 5) {
      return null;
    }
    if (n === 6) {
      return run.popupOpened ? null : 'Open the GitHub window first.';
    }
    if (n <= 10) {
      return run.consentDone ? null :
          'Waiting for your approval in the GitHub window...';
    }
    if (n === 11) {
      return run.resumeStarted ? null : 'Waiting for the agent...';
    }
    return run.answerReady ? null : 'Waiting for the answer...';
  };

  /** Enables or disables the Next step button of the newest card. */
  const updateNextButton = (run) => {
    if (run !== activeStepRun || !run.$newest) {
      return;
    }
    const $next = run.$newest.find('.step-next');
    const $wait = run.$newest.find('.step-wait');
    if (run.failed) {
      $next.remove();
      $wait.text('Stopped on an error. See the message below.');
      return;
    }
    if (!$next.length) {
      return;
    }
    const reason = stepWaitReason(run, run.shown + 1);
    $next.prop('disabled', reason !== null);
    $wait.text(reason || '');
  };

  /**
   * Adds the card of step n to the chat.
   * @param {!Object} run The Step mode run.
   * @param {number} n The step number.
   * @param {?Object=} override Text that replaces the normal card text.
   */
  const showStepCard = (run, n, override = null) => {
    const info = STEP_CARDS[n];
    const skipped = run.path === 'token' && n >= 4 && n <= 10;
    run.shown = n;
    if (run.$newest) {
      run.$newest.find('.step-next').remove();
      run.$newest.find('.step-wait').remove();
    }
    const titleId = `step-card-title-${n}-${Date.now()}`;
    const $card = $('<section>').addClass('step-card')
        .toggleClass('skipped', skipped)
        .attr({'role': 'group', 'aria-labelledby': titleId, 'tabindex': '-1'});
    $card.append($('<div>').addClass('step-number').text(`Step ${n} of 12`));
    const title = override ? override.title : info.title;
    $card.append($('<div>').addClass('step-title').attr('id', titleId).text(title));
    $card.append($('<p>').addClass('step-text').text(
        override ? override.text : (skipped ? SKIPPED_TEXT : info.text)));
    if (!override) {
      const $details = $('<details>').addClass('step-details');
      $details.append($('<summary>').text('Details'));
      const time = run.times[info.time];
      const rows = [
        ['Who acts', info.who],
        ['What happens', skipped ?
            'Nothing. Auth Manager already has a token for you.' : info.what],
        ['What data moves', info.data],
        ['What stays hidden', info.hidden],
        ['Where it runs', info.server ? 'Runs on the server. Your browser does not see this step.' :
            'Your browser sees this step.'],
        ['Time (this run)', time ? fmtLocal(time) : '-'],
        ['Session ID (this run)', currentSessionId || '-'],
      ];
      if (n === 4 || n === 5) {
        rows.push(['Nonce (masked)', maskNonce(run.credential && run.credential.consent_nonce)]);
      }
      const $dl = $('<dl>');
      rows.forEach(([k, v]) => {
        $dl.append($('<dt>').text(k)).append($('<dd>').text(v));
      });
      $details.append($dl);
      $card.append($details);
    }
    if (n < 12 && !(override && override.final)) {
      const $next = $('<button>').attr('type', 'button').addClass('step-next')
          .attr('aria-label', `Next step: step ${n + 1} of 12`).text('Next step');
      $next.on('click', () => onNextStep(run));
      $card.append($next);
      $card.append($('<span>').addClass('step-wait').attr('aria-live', 'polite'));
    }
    $messagesContainer.append($card);
    run.$newest = $card;
    setStep([n], skipped ? 'skipped, token already stored' : title);
    updateNextButton(run);
    const $focus = $card.find('.step-next:not(:disabled)');
    ($focus.length ? $focus : $card).trigger('focus');
    $messagesContainer.scrollTop($messagesContainer.prop('scrollHeight'));
  };

  /** Opens the GitHub consent window from the step 5 click. */
  const openConsentWindow = (run) => {
    const thisAuth = pendingAuth;
    const popup = window.open(run.credential.popup_auth_uri, '_blank');
    run.popupOpened = true;
    run.times.popup = Date.now();
    markTiming('popup');
    if (popup && thisAuth) {
      thisAuth.timer = setInterval(() => {
        if (popup.closed && pendingAuth === thisAuth) {
          completeAuth('popup closed');
        }
      }, 500);
    }
  };

  /** Handles a click on Next step. */
  const onNextStep = (run) => {
    if (run !== activeStepRun) {
      return;
    }
    const n = run.shown + 1;
    if (n > 12 || stepWaitReason(run, n) !== null) {
      return;
    }
    if (n === 5 && run.path === 'consent') {
      if (Date.now() - run.credentialAt > consentExpiryMs()) {
        run.expired = true;
        pendingAuth = null;
        showStepCard(run, 5, {
          title: 'The consent request expired',
          text: 'The consent request expired during the pause. ' +
              'Send the prompt again.',
          final: true,
        });
        return;
      }
      openConsentWindow(run);
    }
    showStepCard(run, n);
    if (n === 12) {
      run.$bubble.find('.wait-indicator').remove();
      $messagesContainer.append(run.$bubble);
      $messagesContainer.scrollTop($messagesContainer.prop('scrollHeight'));
    }
  };

  // F10: the right arrow key or Enter clicks Next step.
  $(document).on('keydown', (e) => {
    if (!activeStepRun || (e.key !== 'ArrowRight' && e.key !== 'Enter')) {
      return;
    }
    const tag = (e.target.tagName || '').toLowerCase();
    if (['input', 'textarea', 'select'].includes(tag) || e.target.isContentEditable) {
      return;
    }
    // Enter on a button already clicks that button.
    if (e.key === 'Enter' && (tag === 'button' || tag === 'summary' || tag === 'a' ||
        tag.startsWith('md-'))) {
      return;
    }
    const $next = $('#messages-container .step-card .step-next').last();
    if ($next.length && !$next.prop('disabled')) {
      e.preventDefault();
      $next.trigger('click');
    }
  });

  // ---- Tabs. ----
  const selectTab = (which) => {
    const isHow = which === 'how';
    $('#tab-play').attr({'aria-selected': String(!isHow), 'tabindex': isHow ? '-1' : '0'});
    $('#tab-how').attr({'aria-selected': String(isHow), 'tabindex': isHow ? '0' : '-1'});
    $('#how-panel').prop('hidden', !isHow);
    $('#playground-panel').prop('hidden', isHow);
  };
  $('#tab-play').on('click', () => selectTab('play'));
  $('#tab-how').on('click', () => selectTab('how'));
  $('.tabs').on('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
      const toHow = $('#tab-play').attr('aria-selected') === 'true';
      selectTab(toHow ? 'how' : 'play');
      $(toHow ? '#tab-how' : '#tab-play').trigger('focus');
    }
  });
  $('#open-demo-controls').on('click', (e) => {
    e.preventDefault();
    const details = document.getElementById('demo-controls');
    if (details) {
      details.open = true;
      details.scrollIntoView({behavior: 'smooth'});
      $('#demo-reset-btn').trigger('focus');
    }
  });
  // New conversation: clear the chat, the step chip, and the timings. The
  // next message starts a new agent session. This does not remove the GitHub
  // token that Auth Manager stores.
  $('#new-conversation').on('click', () => {
    clearWaits();
    pendingAuth = null;
    activeStepRun = null;
    setQueueCount(0);
    $('.step-card').remove();
    latestRequestId++;
    currentSessionId = null;
    document.cookie =
        'session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=lax';
    resetChatFeed();
    appendMessage('New conversation started.', 'system-message');
    timings = {};
    renderTimings();
    setStep([]);
    updateAgentInfoPane();
  });

  $('#clear-timings').on('click', () => {
    timings = {};
    renderTimings();
  });

  buildFlowDiagram();
  renderTimings();

  /**
   * Updates the active agent profile information panel in the sidebar
   * based on the currently selected agent mode, local or remote parameters.
   */
  const updateAgentInfoPane = () => {
    const isLocal = ($('#agent-type-select').val() || 'remote') === 'local';
    const userId = $('#user-id').val() || 'default_user_id';

    if (isLocal) {
      const localAgent = $('#local-agent').val() || $('#local-agent-select').val();
      $('#info-agent-mode').text('Local Agent');
      $('#info-local-agent').text(localAgent || '-');
    } else {
      const projectId = $('#project-id').val();
      const location = $('#location').val();
      const agentId = $('#agent-id').val() || $('#agent-select').val();

      $('#info-agent-mode').text('Remote Vertex AI');
      $('#info-project-id').text(projectId || '-');
      $('#info-location').text(location || '-');
      $('#info-agent-id').text(agentId || '-');
    }

    $('#info-row-local-agent').toggle(isLocal);
    $('#info-row-project-id, #info-row-location, #info-row-agent-id').toggle(!isLocal);
    $('#info-session-id').text(currentSessionId || 'No active session');
    $('#info-user-id').text(userId);
  };

  /**
   * Resets the message history container to display the initial greeting
   * and instructions for the user.
   */
  const resetChatFeed = () => {
    $messagesContainer.html(`
            <div class="message system-message">
                <div class="message-content">
                    Hi! I am your AI Assistant. Configure your target agent in the panel on the left, and type a query below to load the sandbox stream.
                </div>
            </div>
        `);
  };

  const onAgentConfigChange = () => {
    currentSessionId = null;
    resetChatFeed();
    updateAgentInfoPane();
  };

  /**
   * Asynchronously fetches the list of available local agents from the backend
   * API and populates the local agent selection dropdown.
   */
  function loadLocalAgents(showAlert = false) {
    const $localSelect = $('#local-agent-select');

    $.getJSON('/list_local_agents')
        .done(data => {
          if (data.error) {
            if (showAlert) alert(`Local Agent Error: ${data.error}`);
            console.error(`Local agent fetch error: ${data.error}`);
          } else if (data.agents) {
            $localSelect.html('<md-select-option value=""><div slot="headline">Select an agent...</div></md-select-option>');
            data.agents.forEach(agent => {
              $localSelect.append(
                  $('<md-select-option>').val(agent.id).append(
                      $('<div>').attr('slot', 'headline').text(`${agent.name} (${agent.id}.py)`)
                  )
              );
            });

            const currentLocalAgent = $('#local-agent').val();
            if (currentLocalAgent) {
              $localSelect.val(currentLocalAgent);
            } else if (data.agents.length > 0) {
              $localSelect.val(data.agents[0].id);
              $('#local-agent').val(data.agents[0].id);
            }
            updateAgentInfoPane();
          }
        })
        .fail((jqXHR, textStatus, errorThrown) => {
          console.error('Failed to load local agents:', errorThrown);
          if (showAlert) alert('Failed to communicate with local agent directory.');
        });
  }

  /**
   * Asynchronously fetches the list of available remote agents from the backend
   * API and populates the remote agent selection dropdown.
   */
  function loadRemoteAgents(showAlert = false) {
    const projectId = ($('#project-id').val() || '').trim();
    const location = ($('#location').val() || '').trim();

    updateAgentInfoPane();

    if (!projectId || !location) {
      if (showAlert) alert('Please configure both Project ID and Location first.');
      return;
    }

    const $loadAgentsBtn = $('#load-agents-btn');
    const $agentSelect = $('#agent-select');

    $loadAgentsBtn.prop('disabled', true).html('<span class="material-symbols-outlined icon-spin" slot="icon">sync</span> Loading...');

    $.getJSON('/list_agents', { project_id: projectId, location: location })
        .done(data => {
          if (data.error) {
            if (showAlert) alert(`GCP Error: ${data.error}`);
            console.error(`Remote agent fetch error: ${data.error}`);
          } else if (data.agents) {
            $agentSelect.html('<md-select-option value=""><div slot="headline">Select an engine...</div></md-select-option>');
            data.agents.forEach(agent => {
              $agentSelect.append(
                  $('<md-select-option>').val(agent.id).append(
                      $('<div>').attr('slot', 'headline').text(`${agent.name} (${agent.id})`)
                  )
              );
            });

            const currentAgentId = $('#agent-id').val();
            if (currentAgentId) {
              $agentSelect.val(currentAgentId);
            }
            updateAgentInfoPane();
          }
        })
        .fail((jqXHR, textStatus, errorThrown) => {
          console.error('Failed to load remote agents:', errorThrown);
          if (showAlert) alert('Failed to communicate with GCP reasoning engines.');
        })
        .always(() => {
          $loadAgentsBtn.prop('disabled', false).html('<span class="material-symbols-outlined" slot="icon">sync</span> Load Remote Agents');
        });
  }

  $('#agent-type-select').on('change', function() {
    const isLocal = $(this).val() === 'local';
    $('#local-settings').toggle(isLocal);
    $('#remote-settings').toggle(!isLocal);
    if (isLocal) loadLocalAgents();
    onAgentConfigChange();
  });

  $('#local-agent-select').on('change', function() {
    $('#local-agent').val($(this).val());
    onAgentConfigChange();
  });

  $('#agent-select').on('change', function() {
    $('#agent-id').val($(this).val());
    onAgentConfigChange();
  });

  /**
   * Initializes default configuration values on fresh page loads
   * and updates the active agent profile panel accordingly.
   */
  const loadSettings = () => {
    const agentType = 'remote';
    const projectId = '';
    const location = '';
    const agentId = '';
    const userId = 'default_user_id';

    $('#agent-type-select').val(agentType);
    $('#project-id').val(projectId);
    $('#location').val(location);
    $('#agent-id').val(agentId);
    $('#user-id').val(userId);

    loadLocalAgents();
    updateAgentInfoPane();

    // agentic-demos change: fill the Project ID and Location dropdowns from
    // the server config, and select the server defaults.
    const fillSelect = ($select, values, selected) => {
      $select.empty();
      values.forEach((v) => {
        const $opt = $('<md-select-option>').attr('value', v).append(
            $('<div>').attr('slot', 'headline').text(v));
        if (v === selected) $opt.attr('selected', '');
        $select.append($opt);
      });
      // The options register asynchronously. Set the value after that.
      setTimeout(() => {
        $select.val(selected);
        updateAgentInfoPane();
      }, 0);
    };
    $.getJSON('/config').done((cfg) => {
      fillSelect($('#project-id'), cfg.projects || [], cfg.default_project);
      fillSelect($('#location'), cfg.locations || [], cfg.default_location);
    });
    $('#project-id, #location').on('change', () => updateAgentInfoPane());

    // agentic-demos change: behind IAP, the server takes the user ID from
    // the IAP login. Show that user ID, and lock the field.
    $.getJSON('/whoami').done((who) => {
      if (who && who.iap) {
        $('#user-id').val(who.user_id).prop('disabled', true);
        updateAgentInfoPane();
      }
    });
  };

  // Apply configs to active session
  $('#save-settings').on('click', () => {
    const agentType = $('#agent-type-select').val();
    if (agentType === 'remote') {
      const selectVal = $('#agent-select').val();
      if (selectVal) {
        $('#agent-id').val(selectVal);
      }
    } else {
      const selectVal = $('#local-agent-select').val();
      if (selectVal) {
        $('#local-agent').val(selectVal);
      }
    }

    currentSessionId = null;
    document.cookie =
        'session_id=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; samesite=lax';

    resetChatFeed();
    updateAgentInfoPane();
    alert('Settings applied and session reset successfully!');
  });

  $('#load-agents-btn').on('click', () => loadRemoteAgents(true));

  // agentic-demos change: Demo controls panel. DEMO ONLY.
  // The server acts only for the IAP user. The page sends no user ID.
  const showDemoResult = (data, httpStatus, note) => {
    const lines = [];
    if (data.command) lines.push(`$ ${data.command}`);
    if (data.http) lines.push(`# ${data.http}`);
    lines.push(`# HTTP status: ${data.status !== undefined ? data.status : httpStatus}`);
    if (note) lines.push(`# ${note}`);
    lines.push(JSON.stringify(data.response !== undefined ? data.response : data, null, 2));
    $('#demo-output').text(lines.join('\n'));
  };

  const shortName = (value) => (value ? String(value).split('/').pop() : '');

  // Shows an API time (UTC) in the browser local time with the zone, and
  // the UTC time. Example: "08 Nov 2026 15:00 SGT (07:00 UTC)".
  const formatTime = (iso) => {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const local = d.toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit',
      minute: '2-digit', hour12: false}).replace(',', '');
    // The zone name comes from the browser language, for example "SGT" for
    // en-SG or "GMT+8" for en-US.
    const zonePart = new Intl.DateTimeFormat(undefined, {timeZoneName: 'short'})
        .formatToParts(d).find((p) => p.type === 'timeZoneName');
    const zone = zonePart ? ` ${zonePart.value}` : '';
    const utc = d.toLocaleString('en-GB', {
      hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC'});
    return `${local}${zone} (${utc} UTC)`;
  };

  const showSummaryTable = (summaries) => {
    const $table = $('<table>');
    const columns = ['userId', 'workloadId', 'authProvider', 'scopes',
                     'firstAccessTime', 'lastAccessTime'];
    const $head = $('<tr>');
    columns.forEach((c) => $head.append($('<th>').text(c)));
    $table.append($head);
    summaries.forEach((s) => {
      const $row = $('<tr>');
      $row.append($('<td>').text(s.userId || ''));
      $row.append($('<td>').text(shortName(s.workloadId)));
      $row.append($('<td>').text(shortName(s.authProvider)));
      $row.append($('<td>').text((s.scopes || []).join(' ')));
      $row.append($('<td>').text(formatTime(s.firstAccessTime)));
      $row.append($('<td>').text(formatTime(s.lastAccessTime)));
      $table.append($row);
    });
    $('#demo-table').empty().append($table);
  };

  const callDemo = async (method, url, note) => {
    $('#demo-output').text(`$ (running ${method} ${url})`);
    try {
      const resp = await fetch(url, {method: method});
      const data = await resp.json();
      showDemoResult(data, resp.status, note);
      return data;
    } catch (e) {
      $('#demo-output').text(`# Error: ${e}`);
      return null;
    }
  };

  $.getJSON('/demo/config').done((cfg) => {
    if (cfg && cfg.github_app_url) {
      $('#demo-github-link').attr('href', cfg.github_app_url);
    }
  });

  $('#demo-reset-btn').on('click', async () => {
    const userId = $('#user-id').val();
    if (!confirm(`Reset the Auth Manager consent for ${userId}? ` +
                 'The agent will ask for consent again.')) {
      return;
    }
    $('#demo-table').empty();
    await callDemo('POST', '/demo/reset-consent');
  });

  $('#demo-summary-btn').on('click', async () => {
    $('#demo-table').empty();
    const data = await callDemo('GET', '/demo/access-summaries',
        'Times in the API are UTC. The table shows local time.');
    const summaries = data && data.response && data.response.accessSummaries;
    if (summaries) showSummaryTable(summaries);
  });

  // Initialize
  loadSettings();

  // Handle send button states on user inputs
  $userInput.on('input', function() {
    $sendBtn.prop('disabled', $(this).val().trim() === '');
  });

  $userInput.on('keydown', function(e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      sendMessage();
    }
  });

  $sendBtn.on('click', sendMessage);

  /**
   * Handles the user message submission workflow, disabling input controls
   * during processing, appending the user's message to the chat container, and
   * initiating the backend streaming request.
   */
  async function sendMessage() {
    const text = $userInput.val().trim();
    if (!text) return;

    $userInput.val('');
    $sendBtn.prop('disabled', true);

    appendMessage(text, 'user-message');
    await executeChatRequest(text, false, null, null, null);
  }

  /**
   * Executes a POST request to the /chat API endpoint and processes the
   * Server-Sent Events (SSE) stream. Handles agent messages, tool execution
   * progress, and OAuth popup authentication resumes.
   *
   * @param {?string} text - The user query or prompt to send to the agent.
   * @param {?boolean} isAuthResume - Indicates whether the request is resuming
   *     from an OAuth popup authentication flow.
   * @param {?string|null} authRequestId - The function call ID associated with
   *     the credentials request.
   * @param {?object|null} authConfig - The authentication configuration
   *     parameters returned by the agent tool.
   * @param {?HTMLElement|null=} existingAgentMessageDiv - An existing message
   *     container element to append streaming responses into.
   */
  async function executeChatRequest(
      text, isAuthResume, authRequestId, authConfig,
      existingAgentMessageDiv = null) {
    let $agentMessageDiv;
    let $contentDiv;
    let isFirstEvent = true;

    if (existingAgentMessageDiv) {
      $agentMessageDiv = $(existingAgentMessageDiv);
      $contentDiv = $agentMessageDiv.find('.message-content');
      isFirstEvent = false;
    } else if (isStepMode()) {
      // agentic-demos change: Step mode keeps the agent bubble hidden (not
      // in the page) until step 12.
      $agentMessageDiv = $('<div>').addClass('message agent-message')
          .append($('<div>').addClass('message-content'));
      $contentDiv = $agentMessageDiv.find('.message-content');
      activeStepRun = createStepRun($agentMessageDiv);
      setQueueCount(0);
      showStepCard(activeStepRun, 1);
    } else {
      activeStepRun = null;
      $agentMessageDiv = appendMessage('', 'agent-message');
      $contentDiv = $agentMessageDiv.find('.message-content');
    }
    // The Step mode run that owns this bubble, or null.
    const stepRun = (activeStepRun &&
        activeStepRun.$bubble[0] === $agentMessageDiv[0]) ? activeStepRun : null;
    // In Step mode, the step cards control the step chip and the waits.
    const liveStep = (steps, label) => {
      if (!stepRun) {
        setStep(steps, label);
      }
    };
    const liveWait = (kind, waitText) => {
      if (!stepRun) {
        showWait($contentDiv, kind, waitText);
      }
    };

    // agentic-demos change: loading state, step highlight, and timing.
    const requestId = ++latestRequestId;
    if (!isAuthResume) {
      clearWaits();
      pendingAuth = null;
      timings = {};
      markTiming('send');
      liveStep([1, 2]);
      liveWait('dots', 'The agent is working...');
    }

    const agentType = $('#agent-type-select').val() || 'remote';
    const localAgent = $('#local-agent').val() || $('#local-agent-select').val() || '';
    const projectId = $('#project-id').val() || '';
    const location = $('#location').val() || '';
    const agentId = $('#agent-id').val() || $('#agent-select').val() || '';
    const userId = $('#user-id').val() || 'default_user_id';

    const formatAgentText = (inputVal) => {
      if (typeof inputVal !== 'string') return inputVal;
      return inputVal.replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;')
          .replace(/'/g, '&#039;')
          .replace(/\n/g, '<br>');
    };

    try {
      const requestBody = {
        message: text || '',
        agent_type: agentType,
        local_agent: localAgent,
        project_id: projectId,
        location: location,
        agent_id: agentId,
        user_id: userId,
        is_auth_resume: isAuthResume,
        auth_request_function_call_id: authRequestId,
        auth_config: authConfig
      };

      if (currentSessionId) {
        requestBody.session_id = currentSessionId;
      }

      const response = await fetch('/chat', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        let errorDetail = '';
        try {
          const errData = await response.json();
          errorDetail = errData.detail ? JSON.stringify(errData.detail) :
                                         JSON.stringify(errData);
        } catch (e) {
          try {
            errorDetail = await response.text();
          } catch (t) {
            errorDetail = `Status ${response.status}`;
          }
        }
        throw new Error(`HTTP connection error (Status ${response.status}): ${
            errorDetail}`);
      }

      if (isAuthResume) {
        markTiming('resume');
        // Show steps 7-10 for a short time before step 11.
        setTimeout(() => {
          if (currentSteps.join(',') === '7,8,9,10') liveStep([11]);
        }, 1200);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const {value, done} = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, {stream: true});
        while (true) {
          const eventEnd = buffer.indexOf('\n\n');
          if (eventEnd === -1) break;

          const event = buffer.substring(0, eventEnd);
          buffer = buffer.substring(eventEnd + 2);

          if (event.startsWith('data: ')) {
            const dataStr = event.substring(6);
            try {
              const data = JSON.parse(dataStr);

              if (data.session_id) {
                currentSessionId = data.session_id;
                document.cookie =
                    `session_id=${currentSessionId}; path=/; samesite=lax`;
                updateAgentInfoPane();
                continue;
              }

              // agentic-demos change: do not empty the bubble here. The
              // loading state stays until there is text or a status line.
              isFirstEvent = false;
              if (stepRun && !data.popup_auth_uri) {
                stepRun.onEvent(data);
              }

              if (data.popup_auth_uri) {
                if (data.consent_nonce) {
                  document.cookie = `consent_nonce=${
                      data.consent_nonce}; path=/; samesite=lax`;
                }
                const currentUserId = $('#user-id').val();
                document.cookie =
                    `consent_user_id=${currentUserId}; path=/; samesite=lax`;
                // agentic-demos change: resume exactly once, on the first
                // completion signal (see completeAuth), or when the popup
                // closes.
                clearWaits();
                markTiming('credential');
                liveStep([4, 5]);
                pendingAuth = {
                  done: false,
                  timer: null,
                  resume: () => {
                    clearWaits();
                    markTiming('validated');
                    if (stepRun) {
                      // Step mode: resume at once, in the background.
                      stepRun.consentDone = true;
                      stepRun.resumeStarted = true;
                      stepRun.times.consent = Date.now();
                      stepRun.notify();
                    } else {
                      setStep([7, 8, 9, 10]);
                      $contentDiv.append(
                          '<br><em>Authentication complete. Resuming session...</em><br>');
                      showWait($contentDiv, 'spinner', 'Getting your data from GitHub...');
                    }
                    executeChatRequest(
                        '', true, data.auth_request_function_call_id,
                        data.auth_config, $agentMessageDiv[0]);
                  },
                };
                if (stepRun) {
                  // Step mode: the step 5 card opens the GitHub window.
                  stepRun.onCredential(data);
                  continue;
                }
                const thisAuth = pendingAuth;
                const popup = window.open(data.popup_auth_uri, '_blank');
                if (popup) {
                  markTiming('popup');
                  setTimeout(() => {
                    if (pendingAuth === thisAuth) setStep([6]);
                  }, 1500);
                  thisAuth.timer = setInterval(() => {
                    if (popup.closed && pendingAuth === thisAuth) {
                      completeAuth('popup closed');
                    }
                  }, 500);
                }
                $contentDiv.append(
                    `<span>Please log in to complete authorization in the popup. <a href="${
                        data.popup_auth_uri}" target="_blank">Open login window manually.</a></span>`);
                showWait($contentDiv, 'spinner',
                         'Waiting for your approval in the GitHub window...');
              }

              const errorMsg = data.error || data.error_message ||
                  data.errorMessage || data.error_code || data.errorCode;
              if (errorMsg) {
                clearWaits();
                pendingAuth = null;
                liveStep([], 'stopped on an error');
                const $err = $('<div>')
                                 .addClass('error-header')
                                 .text(`Error: ${errorMsg}`);
                $contentDiv.append($err);

                if (data.traceback) {
                  const $pre = $('<pre>')
                                   .addClass('error-traceback')
                                   .text(data.traceback);
                  $contentDiv.append($pre);
                }
                $agentMessageDiv.addClass('error-message');
                if (stepRun) {
                  stepRun.onError();
                }
              } else if (data.content && data.content.parts) {
                data.content.parts.forEach(part => {
                  const fc = part.function_call || part.functionCall;
                  if (fc && fc.name && fc.name !== 'adk_request_credential' &&
                      !data.popup_auth_uri) {
                    if (!stepRun) {
                      setWaitText($contentDiv, `The agent is calling a tool: ${fc.name}...`);
                    }
                  }
                  if (part.text) {
                    clearWaits();
                    markTiming('firstText');
                    markTiming('lastText', true);
                    liveStep([12]);
                    appendAnswer($contentDiv, part.text);
                  }
                });
              } else if (data.text) {
                clearWaits();
                appendAnswer($contentDiv, data.text);
              } else if (typeof data === 'string') {
                clearWaits();
                appendAnswer($contentDiv, data);
              }

              $messagesContainer.scrollTop(
                  $messagesContainer.prop('scrollHeight'));
            } catch (err) {
              console.error('Error parsing JSON event chunk:', dataStr, err);
            }
          }
        }
      }
      // agentic-demos change: the stream ended. Keep the consent spinner
      // only while the consent is pending.
      if (!pendingAuth && requestId === latestRequestId) clearWaits();
      finalizeAnswers($contentDiv);
      if (stepRun) {
        // Step mode: the bubble stays hidden until step 12.
        stepRun.onStreamEnd();
        return;
      }
      // Never leave an empty bubble.
      const $visible = $contentDiv.clone();
      $visible.find('.wait-indicator').remove();
      if (!$visible.text().trim() && !$contentDiv.find('.wait-indicator').length) {
        $agentMessageDiv.remove();
      }
    } catch (error) {
      console.error('Error during query stream processing:', error);
      clearWaits();
      pendingAuth = null;
      liveStep([], 'stopped on an error');
      finalizeAnswers($contentDiv);
      $contentDiv.append(
          $('<div>')
              .addClass('error-header')
              .text(`Network / connection error: ${error.message}`));
      $agentMessageDiv.addClass('error-message');
      if (stepRun) {
        stepRun.onError();
      }
      $messagesContainer.scrollTop($messagesContainer.prop('scrollHeight'));
    }
  }

  /**
   * Helper utility to create and append a new message container element (user,
   * agent, or system) to the chat history DOM, automatically scrolling the view
   * to the latest message.
   *
   * @param {string} text - The HTML or plaintext content of the message.
   * @param {string} type - The CSS class defining the message type (e.g.,
   *     'user-message', 'agent-message').
   * @returns {!jQuery} The jQuery wrapper representing the newly created message
   *     element.
   */
  function appendMessage(text, type) {
    const $messageDiv = $('<div>').addClass(`message ${type}`);
    const $contentDiv = $('<div>')
                            .addClass('message-content')
                            .html(text ? text.replace(/\n/g, '<br>') : '');

    $messageDiv.append($contentDiv);
    $messagesContainer.append($messageDiv);
    $messagesContainer.scrollTop($messagesContainer.prop('scrollHeight'));
    return $messageDiv;
  }
});
