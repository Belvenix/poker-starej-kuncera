// ============================================================
// Poker Starej Kuncery - Game Client
// ============================================================
(function () {
    'use strict';

    // ---------- CONSTANTS ----------

    const RANK_LABELS = {
        7: '7', 8: '8', 9: '9', 10: '10',
        11: 'J', 12: 'Q', 13: 'K', 14: 'A'
    };

    const RANK_NAMES = {
        7: '7', 8: '8', 9: '9', 10: '10',
        11: 'Walet', 12: 'Dama', 13: 'Krol', 14: 'As'
    };

    const SUIT_SYMBOLS = { 0: '\u2663', 1: '\u2666', 2: '\u2665', 3: '\u2660' };
    const SUIT_NAMES   = { 0: 'Trefl', 1: 'Karo', 2: 'Kier', 3: 'Pik' };
    const SUIT_CLASSES  = { 0: 'suit-clubs', 1: 'suit-diamonds', 2: 'suit-hearts', 3: 'suit-spades' };

    const FIGURE_TYPES = [
        'high_card', 'pair', 'two_pairs', 'straight',
        'three_of_kind', 'full_house', 'flush',
        'four_of_kind', 'straight_flush'
    ];

    const FIGURE_LABELS = {
        high_card: 'Wysoka karta',
        pair: 'Para',
        two_pairs: 'Dwie pary',
        straight: 'Strit',
        three_of_kind: 'Trojka',
        full_house: 'Full',
        flush: 'Kolor',
        four_of_kind: 'Kareta',
        straight_flush: 'Poker'
    };

    const ALL_RANKS = [7, 8, 9, 10, 11, 12, 13, 14];

    // ---------- STATE ----------

    let ws = null;
    let reconnectTimer = null;
    let reconnectDelay = 1000;
    let roomCode = null;
    let playerName = null;
    let isCreator = false;
    let gameState = null;
    let historyOpen = false;

    // ---------- DOM REFS ----------

    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => document.querySelectorAll(sel);

    const lobbyScreen     = $('#lobby-screen');
    const gameScreen       = $('#game-screen');
    const lobbyForms       = $('#lobby-forms');
    const lobbyRoom        = $('#lobby-room');
    const lobbyError       = $('#lobby-error');
    const lobbyPlayerList  = $('#lobby-player-list');
    const roomCodeValue    = $('#room-code-value');
    const btnStartGame     = $('#btn-start-game');
    const lobbyWaiting     = $('#lobby-waiting');

    const playersStrip     = $('#players-strip');
    const declarationText  = $('#declaration-text');
    const declarationBy    = $('#declaration-by');
    const playerHand       = $('#player-hand');
    const roundInfo        = $('#round-info');

    const btnRaise         = $('#btn-raise');
    const btnMasq          = $('#btn-masq');
    const btnCheck         = $('#btn-check');
    const btnMate          = $('#btn-mate');

    const confirmOverlay   = $('#confirm-overlay');
    const confirmText      = $('#confirm-text');
    const confirmYes       = $('#confirm-yes');
    const confirmNo        = $('#confirm-no');

    const figurePicker     = $('#figure-picker');
    const pickerContent    = $('#picker-content');

    const historyPanel     = $('#history-panel');
    const historyList      = $('#history-list');

    const toastEl          = $('#toast');
    const resultOverlay    = $('#round-result-overlay');
    const resultTitle      = $('#result-title');
    const resultDesc       = $('#result-description');
    const resultCards      = $('#result-cards');

    const gameOverOverlay  = $('#game-over-overlay');
    const gameOverText     = $('#game-over-text');

    // ---------- HELPERS ----------

    function show(el) { el.classList.remove('hidden'); }
    function hide(el) { el.classList.add('hidden'); }
    function toggle(el) { el.classList.toggle('hidden'); }

    function showToast(msg, duration) {
        duration = duration || 3000;
        toastEl.textContent = msg;
        toastEl.classList.remove('hidden', 'toast-out');
        clearTimeout(toastEl._timer);
        toastEl._timer = setTimeout(function () {
            toastEl.classList.add('toast-out');
            setTimeout(function () { hide(toastEl); }, 300);
        }, duration);
    }

    function showError(msg) {
        lobbyError.textContent = msg;
        show(lobbyError);
        setTimeout(function () { hide(lobbyError); }, 5000);
    }

    function rankName(r) { return RANK_NAMES[r] || String(r); }
    function suitName(s) { return SUIT_NAMES[s] || String(s); }
    function suitSym(s)  { return SUIT_SYMBOLS[s] || '?'; }

    function figureName(fig) {
        if (!fig) return '-';
        var label = FIGURE_LABELS[fig.type] || fig.type;
        var p = fig.params || [];
        switch (fig.type) {
            case 'high_card':      return label + ' ' + rankName(p[0]);
            case 'pair':           return label + ' ' + rankName(p[0]);
            case 'two_pairs':      return label + ': ' + rankName(p[0]) + ' i ' + rankName(p[1]);
            case 'straight':       return label + ' od ' + rankName(p[0]);
            case 'three_of_kind':  return label + ' ' + rankName(p[0]);
            case 'full_house':     return label + ': ' + rankName(p[0]) + ' po ' + rankName(p[1]);
            case 'flush':          return label + ' ' + suitName(p[0]) + ' ' + suitSym(p[0]);
            case 'four_of_kind':   return label + ' ' + rankName(p[0]);
            case 'straight_flush':  return label + ' od ' + rankName(p[0]) + ' ' + suitName(p[1]) + ' ' + suitSym(p[1]);
            default:               return label;
        }
    }

    // ---------- CARD RENDERING ----------

    function createCardEl(card, animate) {
        var el = document.createElement('div');
        var suitClass = SUIT_CLASSES[card.suit] || '';
        el.className = 'card ' + suitClass + (animate ? ' card-reveal' : '');
        el.innerHTML =
            '<span class="card-tl"><span>' + RANK_LABELS[card.rank] + '</span><span>' + suitSym(card.suit) + '</span></span>' +
            '<span class="card-rank">' + RANK_LABELS[card.rank] + '</span>' +
            '<span class="card-suit">' + suitSym(card.suit) + '</span>' +
            '<span class="card-br"><span>' + RANK_LABELS[card.rank] + '</span><span>' + suitSym(card.suit) + '</span></span>';
        return el;
    }

    // ---------- WEBSOCKET ----------

    function connectWS() {
        if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
            return;
        }

        var proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        var url = proto + '//' + location.host + '/ws/' + encodeURIComponent(roomCode) + '/' + encodeURIComponent(playerName);

        ws = new WebSocket(url);

        ws.onopen = function () {
            reconnectDelay = 1000;
            showToast('Polaczono!', 1500);
        };

        ws.onmessage = function (evt) {
            var msg;
            try { msg = JSON.parse(evt.data); } catch (e) { return; }
            handleMessage(msg);
        };

        ws.onclose = function () {
            scheduleReconnect();
        };

        ws.onerror = function () {
            // onclose will fire after onerror
        };
    }

    function scheduleReconnect() {
        if (reconnectTimer) return;
        showToast('Rozlaczono. Ponowne laczenie...', 4000);
        reconnectTimer = setTimeout(function () {
            reconnectTimer = null;
            reconnectDelay = Math.min(reconnectDelay * 1.5, 10000);
            connectWS();
        }, reconnectDelay);
    }

    function send(obj) {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(obj));
        }
    }

    // ---------- MESSAGE HANDLERS ----------

    function handleMessage(msg) {
        switch (msg.type) {
            case 'state':
                gameState = msg;
                if (msg.phase === 'lobby') {
                    renderLobbyPlayers(msg);
                } else {
                    switchToGame();
                    renderGame(msg);
                }
                break;

            case 'round_result':
                if (msg.event === 'check' || msg.event === 'mate') {
                    showRoundResult(msg);
                }
                break;

            case 'error':
                showToast(msg.message || 'Blad!', 4000);
                break;

            case 'game_over':
                showGameOver(msg);
                break;

            case 'player_joined':
                showToast(msg.name + ' dolaczyl/a!', 2000);
                if (msg.players) renderLobbyPlayerList(msg.players);
                break;

            case 'player_left':
                showToast(msg.name + ' opuscil/a gre.', 2000);
                if (msg.players) renderLobbyPlayerList(msg.players);
                break;

            default:
                break;
        }
    }

    // ---------- LOBBY ----------

    function renderLobbyPlayers(state) {
        var players = state.players || [];
        renderLobbyPlayerList(players);
    }

    function renderLobbyPlayerList(players) {
        lobbyPlayerList.innerHTML = '';
        players.forEach(function (p) {
            var li = document.createElement('li');
            li.textContent = p.name;
            lobbyPlayerList.appendChild(li);
        });

        // Show start button only for creator
        if (isCreator && players.length >= 2) {
            show(btnStartGame);
            hide(lobbyWaiting);
        } else if (isCreator) {
            hide(btnStartGame);
            show(lobbyWaiting);
            lobbyWaiting.textContent = 'Potrzeba min. 2 graczy...';
        } else {
            hide(btnStartGame);
            show(lobbyWaiting);
            lobbyWaiting.textContent = 'Czekanie na start...';
        }
    }

    function enterRoom(code, name, creator) {
        roomCode = code.toUpperCase();
        playerName = name;
        isCreator = creator;

        roomCodeValue.textContent = roomCode;
        hide(lobbyForms);
        show(lobbyRoom);
        hide(lobbyError);

        connectWS();
    }

    // ---------- GAME RENDERING ----------

    function switchToGame() {
        lobbyScreen.classList.remove('active');
        gameScreen.classList.add('active');
    }

    function renderGame(state) {
        var round = state.round || {};

        // Round info
        roundInfo.textContent = state.phase === 'DECLARING' ? 'Deklarowanie' : (state.phase || '');

        // Players strip
        renderPlayers(state);

        // Declaration (last_figure is a string description from the engine)
        if (round.last_figure) {
            declarationText.textContent = round.last_figure;
            declarationBy.textContent = round.last_declarer ? ('- ' + round.last_declarer) : '';
        } else {
            declarationText.textContent = 'Brak (pierwsza deklaracja)';
            declarationBy.textContent = '';
        }

        // Hand - extract from players array
        var myHand = [];
        (state.players || []).forEach(function (p) {
            if (p.id === state.your_id && p.hand) {
                myHand = p.hand;
            }
        });
        renderHand(myHand);

        // Actions
        var isMyTurn = round.is_your_turn || false;
        var hasDeclaration = !!round.last_figure;

        btnRaise.disabled  = !isMyTurn;
        btnRaise.textContent = hasDeclaration ? 'Podbij' : 'Zacznij';
        btnCheck.disabled  = !isMyTurn || !hasDeclaration;
        btnMate.disabled   = !isMyTurn || !hasDeclaration;

        // Masquerade: only when current figure is a full house with pair > trio
        if (isMyTurn && canMasquerade()) {
            show(btnMasq);
            btnMasq.disabled = false;
        } else {
            hide(btnMasq);
            btnMasq.disabled = true;
        }

        // History
        renderHistory(round.history || []);
    }

    function renderPlayers(state) {
        var round = state.round || {};
        playersStrip.innerHTML = '';
        (state.players || []).forEach(function (p) {
            var chip = document.createElement('div');
            chip.className = 'player-chip';
            if (p.id === round.current_player_id) chip.classList.add('current-turn');
            if (p.id === state.your_id) chip.classList.add('is-you');
            if (!p.alive) chip.classList.add('eliminated');

            var nameSpan = document.createElement('span');
            nameSpan.className = 'player-chip-name';
            nameSpan.textContent = p.name + (p.id === state.your_id ? ' (Ty)' : '');

            var cardsDiv = document.createElement('div');
            cardsDiv.className = 'player-chip-cards';
            for (var i = 0; i < (p.card_count || 0); i++) {
                var dot = document.createElement('span');
                dot.className = 'card-dot';
                cardsDiv.appendChild(dot);
            }
            if (p.card_count === 0 && p.alive) {
                cardsDiv.textContent = '0 kart';
            }

            chip.appendChild(nameSpan);
            chip.appendChild(cardsDiv);
            playersStrip.appendChild(chip);
        });
    }

    function renderHand(cards) {
        playerHand.innerHTML = '';
        cards.forEach(function (c) {
            playerHand.appendChild(createCardEl(c, false));
        });
        if (cards.length === 0) {
            var empty = document.createElement('span');
            empty.style.color = 'var(--white-dim)';
            empty.style.fontSize = '0.9rem';
            empty.textContent = 'Brak kart';
            playerHand.appendChild(empty);
        }
    }

    function renderHistory(history) {
        historyList.innerHTML = '';
        history.forEach(function (h) {
            var li = document.createElement('li');
            var desc = h.action;
            if (h.action === 'raise') {
                desc = h.figure || 'Podbicie';
            } else if (h.action === 'check') {
                desc = 'Sprawdzenie' + (h.target ? ' -> ' + h.target : '');
            } else if (h.action === 'mate') {
                desc = 'Mat' + (h.success ? ' (udany!)' : ' (nieudany)');
            }
            li.innerHTML = '<span class="history-player">' + escapeHtml(h.player) + ':</span> ' + escapeHtml(desc);
            historyList.appendChild(li);
        });
    }

    function escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // ---------- ROUND RESULT ----------

    function showRoundResult(msg) {
        var event = msg.event || msg.action || '';
        resultTitle.textContent = event === 'check' ? 'Sprawdzenie!' : 'Mat!';

        // Build description
        var desc = '';
        if (event === 'check') {
            desc = msg.player + ' sprawdza ' + msg.target + ': ' + (msg.figure || '');
            desc += msg.figure_exists ? ' - figura istnieje!' : ' - figura nie istnieje!';
            desc += ' Przegrywa: ' + (msg.loser || '?');
        } else if (event === 'mate') {
            desc = msg.player + ' gra mata na: ' + (msg.figure || '');
            if (msg.success) {
                desc += ' - udany! (-1 karta)';
            } else if (msg.mate_fail_reason === 'not_found') {
                desc += ' - nieudany! Figura nie istnieje! (+1 karta)';
            } else if (msg.mate_fail_reason === 'higher_exists') {
                desc += ' - nieudany! Istnieje wyzsza: ' + (msg.highest_figure || '?') + ' (+1 karta)';
            } else {
                desc += ' - nieudany! (+1 karta)';
            }
        }
        if (msg.eliminated) desc += '\n' + msg.eliminated + ' odpada z gry!';
        resultDesc.textContent = desc;

        resultCards.innerHTML = '';
        if (msg.cards_revealed && msg.cards_revealed.length) {
            var row = document.createElement('div');
            row.className = 'result-cards-row';
            msg.cards_revealed.forEach(function (c) {
                row.appendChild(createCardEl(c, true));
            });
            resultCards.appendChild(row);
        }

        show(resultOverlay);
    }

    function showGameOver(msg) {
        var winnerName = msg.winner || 'Ktos';
        // Try to find winner name from game state
        if (gameState && gameState.players) {
            gameState.players.forEach(function (p) {
                if (p.id === msg.winner) winnerName = p.name;
            });
        }
        gameOverText.textContent = winnerName + ' wygrywa!';
        show(gameOverOverlay);
    }

    // ---------- CONFIRMATION ----------

    function showConfirm(text, onYes) {
        confirmText.textContent = text;
        show(confirmOverlay);

        var yesHandler, noHandler;
        yesHandler = function () {
            hide(confirmOverlay);
            confirmYes.removeEventListener('click', yesHandler);
            confirmNo.removeEventListener('click', noHandler);
            onYes();
        };
        noHandler = function () {
            hide(confirmOverlay);
            confirmYes.removeEventListener('click', yesHandler);
            confirmNo.removeEventListener('click', noHandler);
        };
        confirmYes.addEventListener('click', yesHandler);
        confirmNo.addEventListener('click', noHandler);
    }

    // ---------- FIGURE PICKER ----------

    // Figure ordering index for comparison
    function figureTypeIndex(t) {
        return FIGURE_TYPES.indexOf(t);
    }

    // Check if a proposed figure is higher than current last_figure
    function isHigherFigure(proposed, current) {
        if (!current) return true;
        var pi = figureTypeIndex(proposed.type);
        var ci = figureTypeIndex(current.type);
        if (pi > ci) return true;
        if (pi < ci) return false;
        // Same type: compare params lexicographically
        var pp = proposed.params;
        var cp = current.params;
        for (var i = 0; i < pp.length && i < cp.length; i++) {
            if (pp[i] > cp[i]) return true;
            if (pp[i] < cp[i]) return false;
        }
        return false;
    }

    // Get available ranks based on min_rank from state
    function getAvailableRanks() {
        var minRank = 9;
        if (gameState && gameState.config) minRank = gameState.config.min_rank || 9;
        return ALL_RANKS.filter(function (r) { return r >= minRank; });
    }

    function openFigurePicker() {
        show(figurePicker);
        showPickerTypeList();
    }

    function closeFigurePicker() {
        hide(figurePicker);
    }

    function getCurrentFigureRaw() {
        if (!gameState || !gameState.round) return null;
        return gameState.round.last_figure_raw || null;
    }

    function showPickerTypeList() {
        var current = getCurrentFigureRaw();
        var currentIdx = current ? figureTypeIndex(current.type) : -1;

        var html = '<div class="picker-type-list">';
        FIGURE_TYPES.forEach(function (ft, idx) {
            // Allow same type (might have higher params) or higher types
            var disabled = idx < currentIdx ? ' disabled' : '';
            html += '<button class="picker-type-btn" data-type="' + ft + '"' + disabled + '>' +
                FIGURE_LABELS[ft] +
                '<span class="arrow">&rsaquo;</span></button>';
        });
        html += '</div>';
        pickerContent.innerHTML = html;

        pickerContent.querySelectorAll('.picker-type-btn').forEach(function (btn) {
            btn.addEventListener('click', function () {
                if (btn.disabled) return;
                showPickerParams(btn.dataset.type);
            });
        });
    }

    function showPickerParams(figType) {
        var ranks = getAvailableRanks();
        var current = getCurrentFigureRaw();
        var html = '<button class="picker-back-btn" id="picker-back">&larr; Wstecz</button>';
        html += '<h4 style="color:var(--gold);margin-bottom:12px;">' + FIGURE_LABELS[figType] + '</h4>';

        switch (figType) {
            case 'high_card':
            case 'pair':
            case 'three_of_kind':
            case 'four_of_kind':
                html += '<div class="picker-param-section"><h4>Wybierz rang:</h4>';
                html += '<div class="picker-param-grid">';
                ranks.forEach(function (r) {
                    var fig = { type: figType, params: [r] };
                    var dis = !isHigherFigure(fig, current) ? ' disabled' : '';
                    html += '<button class="picker-param-btn" data-rank="' + r + '"' + dis + '>' + rankName(r) + '</button>';
                });
                html += '</div></div>';
                pickerContent.innerHTML = html;
                pickerContent.querySelectorAll('.picker-param-btn[data-rank]').forEach(function (btn) {
                    btn.addEventListener('click', function () {
                        if (btn.disabled) return;
                        var rank = parseInt(btn.dataset.rank);
                        sendRaise({ type: figType, params: [rank] });
                    });
                });
                break;

            case 'two_pairs':
                html += buildTwoPairsUI(ranks, current, figType);
                pickerContent.innerHTML = html;
                setupTwoPairsHandlers(ranks, current, figType);
                break;

            case 'straight':
                html += '<div class="picker-param-section"><h4>Strit od:</h4>';
                html += '<div class="picker-param-grid">';
                ranks.forEach(function (r) {
                    // Straight needs 5 consecutive - check if start_rank + 4 exists
                    if (r + 4 > 14) return;
                    var fig = { type: figType, params: [r] };
                    var dis = !isHigherFigure(fig, current) ? ' disabled' : '';
                    html += '<button class="picker-param-btn" data-rank="' + r + '"' + dis + '>' + rankName(r) + '-' + rankName(r + 4) + '</button>';
                });
                html += '</div></div>';
                pickerContent.innerHTML = html;
                pickerContent.querySelectorAll('.picker-param-btn[data-rank]').forEach(function (btn) {
                    btn.addEventListener('click', function () {
                        if (btn.disabled) return;
                        sendRaise({ type: figType, params: [parseInt(btn.dataset.rank)] });
                    });
                });
                break;

            case 'full_house':
                html += buildFullHouseUI(ranks, current, figType);
                pickerContent.innerHTML = html;
                setupFullHouseHandlers(ranks, current, figType);
                break;

            case 'flush':
                html += '<div class="picker-param-section"><h4>Wybierz kolor:</h4>';
                html += '<div class="picker-param-grid">';
                [0, 1, 2, 3].forEach(function (s) {
                    var fig = { type: figType, params: [s] };
                    var dis = !isHigherFigure(fig, current) ? ' disabled' : '';
                    html += '<button class="picker-param-btn" data-suit="' + s + '"' + dis + '>' + suitSym(s) + ' ' + suitName(s) + '</button>';
                });
                html += '</div></div>';
                pickerContent.innerHTML = html;
                pickerContent.querySelectorAll('.picker-param-btn[data-suit]').forEach(function (btn) {
                    btn.addEventListener('click', function () {
                        if (btn.disabled) return;
                        sendRaise({ type: figType, params: [parseInt(btn.dataset.suit)] });
                    });
                });
                break;

            case 'straight_flush':
                html += buildStraightFlushUI(ranks, current, figType);
                pickerContent.innerHTML = html;
                setupStraightFlushHandlers(ranks, current, figType);
                break;

            default:
                html += '<p>Nieobslugiwany typ</p>';
                pickerContent.innerHTML = html;
                break;
        }

        // Back button
        var backBtn = pickerContent.querySelector('#picker-back');
        if (backBtn) {
            backBtn.addEventListener('click', showPickerTypeList);
        }
    }

    // --- Two pairs: pick high rank, then low rank ---
    function buildTwoPairsUI(ranks, current, figType) {
        var html = '<div class="picker-param-section" id="tp-step1"><h4>Wyzsza para:</h4>';
        html += '<div class="picker-param-grid">';
        ranks.forEach(function (r) {
            html += '<button class="picker-param-btn tp-high" data-rank="' + r + '">' + rankName(r) + '</button>';
        });
        html += '</div></div>';
        html += '<div class="picker-param-section hidden" id="tp-step2"><h4>Nizsza para:</h4>';
        html += '<div class="picker-param-grid" id="tp-low-grid"></div></div>';
        return html;
    }

    function setupTwoPairsHandlers(ranks, current, figType) {
        var step2 = pickerContent.querySelector('#tp-step2');
        var lowGrid = pickerContent.querySelector('#tp-low-grid');
        pickerContent.querySelectorAll('.tp-high').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var high = parseInt(btn.dataset.rank);
                // Highlight selection
                pickerContent.querySelectorAll('.tp-high').forEach(function (b) { b.classList.remove('selected'); });
                btn.classList.add('selected');
                // Build low rank options
                lowGrid.innerHTML = '';
                ranks.forEach(function (r) {
                    if (r >= high) return; // low must be less than high
                    var fig = { type: figType, params: [high, r] };
                    var dis = !isHigherFigure(fig, current) ? ' disabled' : '';
                    var lowBtn = document.createElement('button');
                    lowBtn.className = 'picker-param-btn';
                    lowBtn.dataset.rank = r;
                    lowBtn.textContent = rankName(r);
                    if (!isHigherFigure(fig, current)) lowBtn.disabled = true;
                    lowBtn.addEventListener('click', function () {
                        if (lowBtn.disabled) return;
                        sendRaise({ type: figType, params: [high, parseInt(lowBtn.dataset.rank)] });
                    });
                    lowGrid.appendChild(lowBtn);
                });
                show(step2);
            });
        });
    }

    // --- Full house: pick three rank, then pair rank ---
    function buildFullHouseUI(ranks, current, figType) {
        var html = '<div class="picker-param-section" id="fh-step1"><h4>Trojka:</h4>';
        html += '<div class="picker-param-grid">';
        ranks.forEach(function (r) {
            html += '<button class="picker-param-btn fh-three" data-rank="' + r + '">' + rankName(r) + '</button>';
        });
        html += '</div></div>';
        html += '<div class="picker-param-section hidden" id="fh-step2"><h4>Para:</h4>';
        html += '<div class="picker-param-grid" id="fh-pair-grid"></div></div>';
        return html;
    }

    function setupFullHouseHandlers(ranks, current, figType) {
        var step2 = pickerContent.querySelector('#fh-step2');
        var pairGrid = pickerContent.querySelector('#fh-pair-grid');
        pickerContent.querySelectorAll('.fh-three').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var three = parseInt(btn.dataset.rank);
                pickerContent.querySelectorAll('.fh-three').forEach(function (b) { b.classList.remove('selected'); });
                btn.classList.add('selected');
                pairGrid.innerHTML = '';
                ranks.forEach(function (r) {
                    if (r === three) return;
                    var fig = { type: figType, params: [three, r] };
                    var pBtn = document.createElement('button');
                    pBtn.className = 'picker-param-btn';
                    pBtn.dataset.rank = r;
                    pBtn.textContent = rankName(r);
                    if (!isHigherFigure(fig, current)) pBtn.disabled = true;
                    pBtn.addEventListener('click', function () {
                        if (pBtn.disabled) return;
                        sendRaise({ type: figType, params: [three, parseInt(pBtn.dataset.rank)] });
                    });
                    pairGrid.appendChild(pBtn);
                });
                show(step2);
            });
        });
    }

    // --- Straight flush: pick start rank, then suit ---
    function buildStraightFlushUI(ranks, current, figType) {
        var html = '<div class="picker-param-section" id="sf-step1"><h4>Strit od:</h4>';
        html += '<div class="picker-param-grid">';
        ranks.forEach(function (r) {
            if (r + 4 > 14) return;
            html += '<button class="picker-param-btn sf-start" data-rank="' + r + '">' + rankName(r) + '-' + rankName(r + 4) + '</button>';
        });
        html += '</div></div>';
        html += '<div class="picker-param-section hidden" id="sf-step2"><h4>Kolor:</h4>';
        html += '<div class="picker-param-grid" id="sf-suit-grid"></div></div>';
        return html;
    }

    function setupStraightFlushHandlers(ranks, current, figType) {
        var step2 = pickerContent.querySelector('#sf-step2');
        var suitGrid = pickerContent.querySelector('#sf-suit-grid');
        pickerContent.querySelectorAll('.sf-start').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var start = parseInt(btn.dataset.rank);
                pickerContent.querySelectorAll('.sf-start').forEach(function (b) { b.classList.remove('selected'); });
                btn.classList.add('selected');
                suitGrid.innerHTML = '';
                [0, 1, 2, 3].forEach(function (s) {
                    var fig = { type: figType, params: [start, s] };
                    var sBtn = document.createElement('button');
                    sBtn.className = 'picker-param-btn';
                    sBtn.dataset.suit = s;
                    sBtn.textContent = suitSym(s) + ' ' + suitName(s);
                    if (!isHigherFigure(fig, current)) sBtn.disabled = true;
                    sBtn.addEventListener('click', function () {
                        if (sBtn.disabled) return;
                        sendRaise({ type: figType, params: [start, parseInt(sBtn.dataset.suit)] });
                    });
                    suitGrid.appendChild(sBtn);
                });
                show(step2);
            });
        });
    }

    function sendRaise(figure) {
        send({ type: 'raise', figure: figure });
        closeFigurePicker();
    }

    // --- Masquerade: one-click swap of current full house ---
    function canMasquerade() {
        var fig = getCurrentFigureRaw();
        if (!fig || fig.type !== 'full_house') return false;
        // pair_rank (params[1]) must be higher than three_rank (params[0])
        // so the swap produces a higher figure
        return fig.params[1] > fig.params[0];
    }

    function doMasquerade() {
        var fig = getCurrentFigureRaw();
        if (!fig) return;
        // Swap: declared trio = old pair rank, declared pair = old trio rank
        send({
            type: 'raise',
            figure: {
                type: 'full_house',
                params: [fig.params[1], fig.params[0]],
                masquerade: true
            }
        });
    }

    // ---------- EVENT BINDINGS ----------

    // Lobby: create room
    $('#btn-create-room').addEventListener('click', function () {
        var name = $('#player-name').value.trim();
        if (!name) { showError('Wpisz swoje imie!'); return; }
        fetch('/api/rooms', { method: 'POST' })
            .then(function (res) { return res.json(); })
            .then(function (data) {
                if (data.code) {
                    enterRoom(data.code, name, true);
                } else {
                    showError(data.error || 'Nie udalo sie stworzyc pokoju');
                }
            })
            .catch(function () { showError('Blad polaczenia z serwerem'); });
    });

    // Lobby: join room
    $('#btn-join-room').addEventListener('click', function () {
        var name = $('#player-name').value.trim();
        var code = $('#room-code-input').value.trim().toUpperCase();
        if (!name) { showError('Wpisz swoje imie!'); return; }
        if (!code || code.length < 3) { showError('Wpisz kod pokoju!'); return; }
        enterRoom(code, name, false);
    });

    // Lobby: copy code
    $('#btn-copy-code').addEventListener('click', function () {
        if (navigator.clipboard && roomCode) {
            navigator.clipboard.writeText(roomCode).then(function () {
                showToast('Skopiowano!', 1500);
            });
        }
    });

    // Lobby: start game
    btnStartGame.addEventListener('click', function () {
        send({ type: 'start' });
    });

    // Game: raise
    btnRaise.addEventListener('click', function () {
        if (btnRaise.disabled) return;
        openFigurePicker();
    });

    // Game: masquerade (single click, auto-swaps current full house)
    btnMasq.addEventListener('click', function () {
        if (btnMasq.disabled) return;
        showConfirm('Maszkarada?', function () {
            doMasquerade();
        });
    });

    // Game: check (with confirmation)
    btnCheck.addEventListener('click', function () {
        if (btnCheck.disabled) return;
        showConfirm('Na pewno chcesz sprawdzic?', function () {
            send({ type: 'check' });
        });
    });

    // Game: mate (with confirmation)
    btnMate.addEventListener('click', function () {
        if (btnMate.disabled) return;
        showConfirm('Na pewno chcesz zagrac mata?', function () {
            send({ type: 'mate' });
        });
    });

    // Picker: close
    $('#picker-close').addEventListener('click', closeFigurePicker);
    figurePicker.querySelector('.picker-backdrop').addEventListener('click', closeFigurePicker);

    // History toggle
    $('#btn-history-toggle').addEventListener('click', function () {
        historyOpen = !historyOpen;
        if (historyOpen) show(historyPanel); else hide(historyPanel);
    });

    $('#btn-history-close').addEventListener('click', function () {
        historyOpen = false;
        hide(historyPanel);
    });

    // Round result dismiss
    $('#result-dismiss').addEventListener('click', function () {
        hide(resultOverlay);
    });

    // Game over: back to lobby
    $('#btn-back-lobby').addEventListener('click', function () {
        hide(gameOverOverlay);
        gameScreen.classList.remove('active');
        lobbyScreen.classList.add('active');
        show(lobbyForms);
        hide(lobbyRoom);
        if (ws) { ws.close(); ws = null; }
        roomCode = null;
        playerName = null;
        gameState = null;
    });

    // ---------- UTILITY ----------

    function generateCode() {
        var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
        var code = '';
        for (var i = 0; i < 6; i++) {
            code += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return code;
    }

    // Handle visibility change for reconnect on phone wake
    document.addEventListener('visibilitychange', function () {
        if (!document.hidden && roomCode && (!ws || ws.readyState !== WebSocket.OPEN)) {
            connectWS();
        }
    });

})();
