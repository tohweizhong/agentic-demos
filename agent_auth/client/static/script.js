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
    } else {
      $agentMessageDiv = appendMessage(
          '<div class="agent-loader"><span class="material-symbols-outlined icon-spin">sync</span> Thinking...</div>',
          'agent-message');
      $contentDiv = $agentMessageDiv.find('.message-content');
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

              if (isFirstEvent) {
                $contentDiv.empty();
                isFirstEvent = false;
              }

              if (data.popup_auth_uri) {
                if (data.consent_nonce) {
                  document.cookie = `consent_nonce=${
                      data.consent_nonce}; path=/; samesite=lax`;
                }
                const currentUserId = $('#user-id').val();
                document.cookie =
                    `consent_user_id=${currentUserId}; path=/; samesite=lax`;
                const popup = window.open(data.popup_auth_uri, '_blank');
                if (popup) {
                  const timer = setInterval(() => {
                    if (popup.closed) {
                      clearInterval(timer);
                      $contentDiv.append(
                          '<br><em>Authentication complete. Resuming session...</em><br>');
                      $messagesContainer.scrollTop(
                          $messagesContainer.prop('scrollHeight'));
                      executeChatRequest(
                          '', true, data.auth_request_function_call_id,
                          data.auth_config, $agentMessageDiv[0]);
                    }
                  }, 500);
                }
                $contentDiv.append(
                    `<span>Please log in to complete authorization in the popup. <a href="${
                        data.popup_auth_uri}" target="_blank">Open login window manually.</a></span>`);
              }

              const errorMsg = data.error || data.error_message ||
                  data.errorMessage || data.error_code || data.errorCode;
              if (errorMsg) {
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
              } else if (data.content && data.content.parts) {
                data.content.parts.forEach(part => {
                  if (part.text) {
                    $contentDiv.append(
                        $('<div>').html(formatAgentText(part.text)));
                  }
                });
              } else if (data.text) {
                $contentDiv.append($('<div>').html(formatAgentText(data.text)));
              } else if (typeof data === 'string') {
                $contentDiv.append($('<div>').html(formatAgentText(data)));
              }

              $messagesContainer.scrollTop(
                  $messagesContainer.prop('scrollHeight'));
            } catch (err) {
              console.error('Error parsing JSON event chunk:', dataStr, err);
            }
          }
        }
      }
    } catch (error) {
      console.error('Error during query stream processing:', error);
      if (isFirstEvent) {
        $contentDiv.empty();
      }
      $contentDiv.append(
          $('<div>')
              .addClass('error-header')
              .text(`Network / connection error: ${error.message}`));
      $agentMessageDiv.addClass('error-message');
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
