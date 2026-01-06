"""Enhanced UI template with confidence dashboard and tabbed interface"""

UI_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>BTC Trading Bot Dashboard - Macro-Aware</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            overflow-x: hidden;
        }

        .header {
            background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            position: sticky;
            top: 0;
            z-index: 100;
        }

        .header-content {
            max-width: 1600px;
            margin: 0 auto;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo h1 {
            font-size: 1.5em;
            background: linear-gradient(135deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .status-pill {
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            background: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }

        /* Confidence Dashboard */
        .confidence-dashboard {
            background: linear-gradient(135deg, #1e40af 0%, #7c3aed 100%);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 24px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
        }

        .overall-confidence {
            text-align: center;
            margin-bottom: 30px;
        }

        .confidence-score {
            font-size: 4em;
            font-weight: 700;
            margin: 10px 0;
            background: linear-gradient(135deg, #fbbf24, #f59e0b);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .confidence-label {
            font-size: 1.2em;
            opacity: 0.9;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        .confidence-breakdown {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-top: 20px;
        }

        .factor-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            padding: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }

        .factor-card:hover {
            background: rgba(255, 255, 255, 0.15);
            transform: translateY(-2px);
        }

        .factor-title {
            font-size: 0.85em;
            opacity: 0.8;
            margin-bottom: 8px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .factor-value {
            font-size: 1.8em;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .factor-bar {
            height: 6px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 3px;
            overflow: hidden;
        }

        .factor-bar-fill {
            height: 100%;
            transition: width 0.5s ease;
            border-radius: 3px;
        }

        .bar-green { background: linear-gradient(90deg, #22c55e, #16a34a); }
        .bar-yellow { background: linear-gradient(90deg, #f59e0b, #d97706); }
        .bar-red { background: linear-gradient(90deg, #ef4444, #dc2626); }
        .bar-blue { background: linear-gradient(90deg, #3b82f6, #2563eb); }

        /* Tabs */
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 24px;
            background: #1e293b;
            padding: 8px;
            border-radius: 12px;
            overflow-x: auto;
        }

        .tab {
            padding: 12px 24px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            white-space: nowrap;
            font-weight: 500;
            background: transparent;
            color: #94a3b8;
            border: none;
            font-size: 0.95em;
        }

        .tab:hover {
            background: rgba(148, 163, 184, 0.1);
            color: #cbd5e1;
        }

        .tab.active {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
        }

        .tab-content {
            display: none;
        }

        .tab-content.active {
            display: block;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* Cards */
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
        }

        .card {
            background: #1e293b;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.2);
            border: 1px solid #334155;
            transition: all 0.3s ease;
        }

        .card:hover {
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.3);
            border-color: #475569;
        }

        .card.wide {
            grid-column: span 2;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 12px;
            border-bottom: 2px solid #334155;
        }

        .card-title {
            font-size: 1.1em;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .data-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid rgba(51, 65, 85, 0.5);
        }

        .data-row:last-child {
            border-bottom: none;
        }

        .data-label {
            font-size: 0.9em;
            color: #94a3b8;
        }

        .data-value {
            font-weight: 600;
            font-size: 1em;
        }

        /* Badges & Pills */
        .badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .regime-RISK_ON {
            background: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }

        .regime-RISK_OFF {
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        .regime-DECOUPLED {
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .regime-CHOP {
            background: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .positive { color: #4ade80; }
        .negative { color: #f87171; }
        .neutral { color: #fbbf24; }

        .impact-HIGH {
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
        }

        .impact-MEDIUM {
            background: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
        }

        .impact-LOW {
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
        }

        /* Big Number Display */
        .big-number {
            font-size: 2.5em;
            font-weight: 700;
            margin: 10px 0;
            line-height: 1;
        }

        .big-number-label {
            font-size: 0.9em;
            color: #94a3b8;
            margin-bottom: 8px;
        }

        /* Status Indicator */
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
        }

        .status-online {
            background: #4ade80;
            box-shadow: 0 0 8px #4ade80;
        }

        .status-offline {
            background: #f87171;
        }

        /* Button */
        .btn {
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            border: none;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 500;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
        }

        .btn:active {
            transform: translateY(0);
        }

        /* News Item */
        .news-item {
            padding: 16px;
            background: rgba(51, 65, 85, 0.3);
            border-radius: 8px;
            margin-bottom: 12px;
            border-left: 3px solid #3b82f6;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .news-item:hover {
            background: rgba(51, 65, 85, 0.5);
            transform: translateX(4px);
            border-left-color: #60a5fa;
        }

        .news-title {
            font-size: 0.95em;
            line-height: 1.5;
            margin-bottom: 8px;
        }

        .news-meta {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            font-size: 0.8em;
        }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            z-index: 1000;
            overflow-y: auto;
            animation: fadeIn 0.2s ease;
        }

        .modal.active {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .modal-content {
            background: #1e293b;
            border-radius: 16px;
            max-width: 900px;
            width: 100%;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            animation: slideUp 0.3s ease;
        }

        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .modal-header {
            padding: 24px;
            border-bottom: 2px solid #334155;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 16px;
        }

        .modal-title {
            font-size: 1.4em;
            font-weight: 600;
            line-height: 1.4;
            flex: 1;
        }

        .modal-close {
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
            width: 36px;
            height: 36px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 1.2em;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.3s ease;
            flex-shrink: 0;
        }

        .modal-close:hover {
            background: rgba(239, 68, 68, 0.3);
            transform: rotate(90deg);
        }

        .modal-body {
            padding: 24px;
        }

        .modal-meta {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 20px;
            padding-bottom: 20px;
            border-bottom: 1px solid #334155;
        }

        .article-content {
            line-height: 1.8;
            font-size: 1.05em;
        }

        .article-content p {
            margin-bottom: 16px;
        }

        .article-content a {
            color: #60a5fa;
            text-decoration: none;
        }

        .article-content a:hover {
            text-decoration: underline;
        }

        .read-more-link {
            display: inline-block;
            margin-top: 20px;
            padding: 10px 20px;
            background: linear-gradient(135deg, #3b82f6, #2563eb);
            color: white;
            border-radius: 8px;
            text-decoration: none;
            transition: all 0.3s ease;
        }

        .read-more-link:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(59, 130, 246, 0.4);
        }

        /* Loading */
        .loading {
            text-align: center;
            padding: 40px;
            color: #64748b;
        }

        .spinner {
            border: 3px solid rgba(148, 163, 184, 0.2);
            border-top: 3px solid #3b82f6;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 16px;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Timeframe Analysis */
        .timeframe-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 16px;
        }

        .timeframe-card {
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 2px solid #334155;
            transition: all 0.3s ease;
        }

        .timeframe-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        }

        .timeframe-card.bullish {
            border-color: #22c55e;
            background: linear-gradient(135deg, rgba(34, 197, 94, 0.05) 0%, #1e293b 100%);
        }

        .timeframe-card.bearish {
            border-color: #ef4444;
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.05) 0%, #1e293b 100%);
        }

        .timeframe-card.neutral {
            border-color: #64748b;
            background: linear-gradient(135deg, rgba(100, 116, 139, 0.05) 0%, #1e293b 100%);
        }

        .timeframe-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 1px solid #334155;
        }

        .timeframe-name {
            font-size: 1.2em;
            font-weight: 700;
            color: #e2e8f0;
        }

        .bias-badge {
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.85em;
            font-weight: 700;
            text-transform: uppercase;
        }

        .bias-badge.bullish {
            background: rgba(34, 197, 94, 0.2);
            color: #4ade80;
            border: 1px solid rgba(34, 197, 94, 0.4);
        }

        .bias-badge.bearish {
            background: rgba(239, 68, 68, 0.2);
            color: #f87171;
            border: 1px solid rgba(239, 68, 68, 0.4);
        }

        .bias-badge.neutral {
            background: rgba(100, 116, 139, 0.2);
            color: #94a3b8;
            border: 1px solid rgba(100, 116, 139, 0.4);
        }

        .confidence-bar-container {
            background: rgba(51, 65, 85, 0.5);
            height: 8px;
            border-radius: 4px;
            overflow: hidden;
            margin: 12px 0;
        }

        .confidence-bar {
            height: 100%;
            transition: width 0.5s ease;
            border-radius: 4px;
        }

        .confidence-bar.bullish {
            background: linear-gradient(90deg, #22c55e, #16a34a);
        }

        .confidence-bar.bearish {
            background: linear-gradient(90deg, #ef4444, #dc2626);
        }

        .confidence-bar.neutral {
            background: linear-gradient(90deg, #64748b, #475569);
        }

        .confidence-text {
            font-size: 0.9em;
            color: #94a3b8;
            margin-bottom: 8px;
        }

        .timeframe-details {
            margin-top: 16px;
        }

        .detail-row {
            display: flex;
            justify-content: space-between;
            padding: 6px 0;
            font-size: 0.9em;
            color: #cbd5e1;
        }

        .detail-label {
            color: #94a3b8;
        }

        .factors-section {
            margin-top: 16px;
            padding-top: 16px;
            border-top: 1px solid #334155;
        }

        .factors-title {
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 8px;
            letter-spacing: 1px;
        }

        .factor-list {
            list-style: none;
            padding: 0;
            margin: 0;
        }

        .factor-item {
            padding: 4px 0 4px 16px;
            font-size: 0.85em;
            color: #cbd5e1;
            position: relative;
        }

        .factor-item:before {
            content: "•";
            position: absolute;
            left: 0;
            color: #3b82f6;
        }

        .factor-item.supporting:before {
            color: #22c55e;
        }

        .factor-item.conflicting:before {
            color: #ef4444;
        }

        .explanation {
            margin-top: 16px;
            padding: 12px;
            background: rgba(51, 65, 85, 0.3);
            border-radius: 8px;
            font-size: 0.9em;
            color: #cbd5e1;
            line-height: 1.6;
            border-left: 3px solid #3b82f6;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .card.wide {
                grid-column: span 1;
            }

            .confidence-score {
                font-size: 3em;
            }

            .tabs {
                flex-wrap: nowrap;
            }

            .timeframe-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <h1>🤖 Macro-Aware BTC Trading Bot</h1>
            </div>
            <div class="status-pill">
                <span class="status-dot status-online"></span>
                LIVE - All Modules Active
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Overall Confidence Dashboard -->
        <div class="confidence-dashboard">
            <div class="overall-confidence">
                <div class="confidence-label">Overall System Confidence</div>
                <div class="confidence-score" id="overall-confidence">--</div>
                <div class="confidence-label" id="confidence-status">Calculating...</div>
            </div>

            <div class="confidence-breakdown" id="confidence-breakdown">
                <!-- Factors will be injected here -->
            </div>
        </div>

        <!-- Tabs Navigation -->
        <div class="tabs">
            <button class="tab active" onclick="switchTab('overview')">📊 Overview</button>
            <button class="tab" onclick="switchTab('timeframes')">⏰ Timeframe Analysis</button>
            <button class="tab" onclick="switchTab('market')">📈 Market Data</button>
            <button class="tab" onclick="switchTab('macro')">💵 Macro Indicators</button>
            <button class="tab" onclick="switchTab('news')">📰 News & Sentiment</button>
            <button class="tab" onclick="switchTab('regime')">🎯 Regime Engine</button>
            <button class="tab" onclick="switchTab('trading')">⚡ Trading Signals</button>
            <button class="tab" onclick="switchTab('risk')">🛡️ Risk & Positions</button>
            <button class="tab" onclick="switchTab('system')">⚙️ System Status</button>
        </div>

        <!-- Tab Content: Overview -->
        <div id="tab-overview" class="tab-content active">
            <div class="grid">
                <div class="card wide">
                    <div class="card-header">
                        <div class="card-title">🎯 Current Regime State</div>
                    </div>
                    <div id="regime-overview"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">💵 DXY Index</div>
                    </div>
                    <div id="dxy-overview"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">₿ BTC Dominance</div>
                    </div>
                    <div id="btc-dom-overview"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📈 BTC Price</div>
                    </div>
                    <div id="btc-price-overview"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📰 Latest News</div>
                    </div>
                    <div id="news-overview"></div>
                </div>
            </div>
        </div>

        <!-- Tab Content: Timeframe Analysis -->
        <div id="tab-timeframes" class="tab-content">
            <div class="card wide">
                <div class="card-header">
                    <div class="card-title">⏰ Multi-Timeframe Bias Analysis</div>
                </div>
                <p style="margin-bottom: 20px; color: #94a3b8; font-size: 0.95em;">
                    Analysis of market bias across 15M, 1H, 4H, and Daily timeframes using technical indicators,
                    regime state, capital flow, and liquidity levels.
                </p>
                <div id="timeframe-analysis" class="timeframe-grid">
                    <!-- Timeframe cards will be injected here -->
                </div>
            </div>
        </div>

        <!-- Tab Content: Market Data -->
        <div id="tab-market" class="tab-content">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📈 Latest Trade</div>
                    </div>
                    <div id="latest-trade"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📊 Latest Kline (5m)</div>
                    </div>
                    <div id="latest-kline"></div>
                </div>

                <div class="card wide">
                    <div class="card-header">
                        <div class="card-title">📖 Order Book Summary</div>
                    </div>
                    <div id="orderbook-data"></div>
                </div>
            </div>
        </div>

        <!-- Tab Content: Macro Indicators -->
        <div id="tab-macro" class="tab-content">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">💵 DXY (US Dollar Index)</div>
                    </div>
                    <div id="dxy-detailed"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">₿ BTC Dominance</div>
                    </div>
                    <div id="btc-dom-detailed"></div>
                </div>

                <div class="card wide">
                    <div class="card-header">
                        <div class="card-title">📉 Trend Analysis</div>
                    </div>
                    <div id="trend-analysis"></div>
                </div>
            </div>
        </div>

        <!-- Tab Content: News & Sentiment -->
        <div id="tab-news" class="tab-content">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🎯 News Signals</div>
                    </div>
                    <div id="news-signals"></div>
                </div>

                <div class="card wide">
                    <div class="card-header">
                        <div class="card-title">📰 Latest Classified News</div>
                        <button class="btn" onclick="fetchNewsData()">Refresh</button>
                    </div>
                    <div id="news-list"></div>
                </div>
            </div>
        </div>

        <!-- Tab Content: Regime Engine -->
        <div id="tab-regime" class="tab-content">
            <div class="grid">
                <div class="card wide">
                    <div class="card-header">
                        <div class="card-title">🎯 Regime State Details</div>
                    </div>
                    <div id="regime-detailed"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📊 Contributions</div>
                    </div>
                    <div id="regime-contributions"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">⚙️ Permissions</div>
                    </div>
                    <div id="regime-permissions"></div>
                </div>
            </div>
        </div>

        <!-- Tab Content: Trading Signals -->
        <div id="tab-trading" class="tab-content">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">💰 Capital Flow</div>
                    </div>
                    <div id="capital-flow"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">💧 Liquidity Levels</div>
                    </div>
                    <div id="liquidity-levels"></div>
                </div>

                <div class="card wide">
                    <div class="card-header">
                        <div class="card-title">⚡ Execution Signal</div>
                    </div>
                    <div id="execution-signal"></div>
                </div>
            </div>
        </div>

        <!-- Tab Content: Risk & Positions -->
        <div id="tab-risk" class="tab-content">
            <div class="grid">
                <div class="card">
                    <div class="card-header">
                        <div class="card-title">🛡️ Risk Manager Status</div>
                    </div>
                    <div id="risk-status"></div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <div class="card-title">📊 Trade Manager</div>
                    </div>
                    <div id="trade-status"></div>
                </div>

                <div class="card wide">
                    <div class="card-header">
                        <div class="card-title">📈 Open Positions</div>
                    </div>
                    <div id="positions-list"></div>
                </div>
            </div>
        </div>

        <!-- Tab Content: System Status -->
        <div id="tab-system" class="tab-content">
            <div class="grid">
                <div class="card wide">
                    <div class="card-header">
                        <div class="card-title">⚙️ System Health</div>
                        <button class="btn" onclick="fetchData()">Refresh All</button>
                    </div>
                    <div id="system-health"></div>
                </div>
            </div>
        </div>
    </div>

    <!-- Article Modal -->
    <div id="article-modal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title" id="modal-article-title">Loading...</div>
                <button class="modal-close" onclick="closeArticleModal()">✕</button>
            </div>
            <div class="modal-body">
                <div class="modal-meta" id="modal-article-meta"></div>
                <div class="article-content" id="modal-article-content">
                    <div class="spinner"></div>
                    <div class="loading">Loading article...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentTab = 'overview';

        function switchTab(tabName) {
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {
                tab.classList.remove('active');
            });
            event.target.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            document.getElementById(`tab-${tabName}`).classList.add('active');

            currentTab = tabName;
        }

        function calculateOverallConfidence(data) {
            let factors = [];
            let totalWeight = 0;
            let weightedSum = 0;

            // Regime confidence (30% weight)
            if (data.regime && data.regime.confidence !== undefined) {
                const weight = 0.30;
                factors.push({
                    name: 'Regime Engine',
                    value: data.regime.confidence * 100,
                    weight: weight,
                    color: 'bar-blue'
                });
                weightedSum += data.regime.confidence * weight;
                totalWeight += weight;
            }

            // Market data availability (20% weight)
            if (data.bybit && data.bybit.latest_trade) {
                const weight = 0.20;
                const confidence = data.bybit.connected ? 1.0 : 0.0;
                factors.push({
                    name: 'Market Data',
                    value: confidence * 100,
                    weight: weight,
                    color: confidence > 0.8 ? 'bar-green' : 'bar-red'
                });
                weightedSum += confidence * weight;
                totalWeight += weight;
            }

            // Macro data availability (20% weight)
            let macroConfidence = 0;
            let macroCount = 0;
            if (data.macro) {
                if (data.macro.dxy) { macroConfidence += 1; macroCount++; }
                if (data.macro.btc_dominance) { macroConfidence += 1; macroCount++; }
            }
            if (macroCount > 0) {
                const weight = 0.20;
                const confidence = macroConfidence / macroCount;
                factors.push({
                    name: 'Macro Indicators',
                    value: confidence * 100,
                    weight: weight,
                    color: confidence > 0.8 ? 'bar-green' : confidence > 0.5 ? 'bar-yellow' : 'bar-red'
                });
                weightedSum += confidence * weight;
                totalWeight += weight;
            }

            // News availability (15% weight)
            if (data.news && data.news.signals) {
                const weight = 0.15;
                const confidence = data.news.signals.news_count > 0 ? 1.0 : 0.5;
                factors.push({
                    name: 'News & Sentiment',
                    value: confidence * 100,
                    weight: weight,
                    color: confidence > 0.8 ? 'bar-green' : 'bar-yellow'
                });
                weightedSum += confidence * weight;
                totalWeight += weight;
            }

            // Trading system readiness (15% weight)
            const weight = 0.15;
            const tradingConfidence = 0.9; // Assume high if system is running
            factors.push({
                name: 'Trading System',
                value: tradingConfidence * 100,
                weight: weight,
                color: 'bar-green'
            });
            weightedSum += tradingConfidence * weight;
            totalWeight += weight;

            const overallConfidence = totalWeight > 0 ? (weightedSum / totalWeight) * 100 : 0;

            return { overall: overallConfidence, factors: factors };
        }

        function updateConfidenceDashboard(data) {
            const { overall, factors } = calculateOverallConfidence(data);

            // Update overall confidence
            document.getElementById('overall-confidence').textContent = overall.toFixed(1) + '%';

            let status = 'Excellent';
            if (overall < 50) status = 'Poor';
            else if (overall < 70) status = 'Fair';
            else if (overall < 85) status = 'Good';

            document.getElementById('confidence-status').textContent = status;

            // Update breakdown
            const breakdown = document.getElementById('confidence-breakdown');
            breakdown.innerHTML = factors.map(factor => `
                <div class="factor-card">
                    <div class="factor-title">${factor.name}</div>
                    <div class="factor-value">${factor.value.toFixed(0)}%</div>
                    <div class="factor-bar">
                        <div class="factor-bar-fill ${factor.color}" style="width: ${factor.value}%"></div>
                    </div>
                </div>
            `).join('');
        }

        function getRegimeColor(state) {
            const colors = {
                'RISK_ON': 'positive',
                'RISK_OFF': 'negative',
                'DECOUPLED': 'neutral',
                'CHOP': 'neutral'
            };
            return colors[state] || 'neutral';
        }

        async function fetchData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();

                updateConfidenceDashboard(data);
                updateOverviewTab(data);
                updateMarketTab(data);
                updateMacroTab(data);
                updateRegimeTab(data);
                updateSystemTab(data);

            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }

        async function fetchNewsData() {
            try {
                const response = await fetch('/api/news/classified?limit=10');
                const news = await response.json();

                const newsList = document.getElementById('news-list');
                if (news && news.length > 0) {
                    // Store news data globally for modal access
                    window.newsData = news;

                    newsList.innerHTML = news.map((item, index) => `
                        <div class="news-item" onclick="openArticleModal(${index})" data-index="${index}">
                            <div class="news-title">${item.news_item.title}</div>
                            <div class="news-meta">
                                <span class="badge impact-${item.impact_level}">${item.impact_level}</span>
                                <span class="badge ${item.sentiment === 'POSITIVE' ? 'positive' : item.sentiment === 'NEGATIVE' ? 'negative' : 'neutral'}">
                                    ${item.sentiment} (${item.sentiment_score.toFixed(2)})
                                </span>
                                <span>Alignment: ${item.alignment}</span>
                                <span>Source: ${item.news_item.source}</span>
                            </div>
                        </div>
                    `).join('');
                } else {
                    newsList.innerHTML = '<div class="loading">No classified news available</div>';
                }
            } catch (error) {
                console.error('Error fetching news:', error);
            }
        }

        function openArticleModal(newsIndex) {
            console.log('Opening article modal for index:', newsIndex);

            if (!window.newsData) {
                console.error('No news data available');
                return;
            }

            const newsItem = window.newsData[newsIndex];
            if (!newsItem) {
                console.error('News item not found for index:', newsIndex);
                return;
            }

            console.log('News item:', newsItem);

            const modal = document.getElementById('article-modal');
            const title = document.getElementById('modal-article-title');
            const meta = document.getElementById('modal-article-meta');
            const content = document.getElementById('modal-article-content');

            // Set title
            title.textContent = newsItem.news_item.title;

            // Set meta info
            meta.innerHTML = `
                <span class="badge impact-${newsItem.impact_level}">${newsItem.impact_level}</span>
                <span class="badge ${newsItem.sentiment === 'POSITIVE' ? 'positive' : newsItem.sentiment === 'NEGATIVE' ? 'negative' : 'neutral'}">
                    ${newsItem.sentiment} (${newsItem.sentiment_score.toFixed(2)})
                </span>
                <span class="badge">Alignment: ${newsItem.alignment}</span>
                <span class="badge">Source: ${newsItem.news_item.source}</span>
                ${newsItem.news_item.published_at ? `<span class="badge">Published: ${new Date(newsItem.news_item.published_at).toLocaleString()}</span>` : ''}
            `;

            // Show loading state
            content.innerHTML = `
                <div class="spinner"></div>
                <div class="loading">Loading article content...</div>
            `;

            // Show modal
            modal.classList.add('active');

            // Fetch and display article content
            fetchArticleContent(newsItem);
        }

        async function fetchArticleContent(newsItem) {
            const content = document.getElementById('modal-article-content');

            try {
                // Display description if available
                let articleHtml = '';

                if (newsItem.news_item.description) {
                    articleHtml += `<p><strong>Summary:</strong> ${newsItem.news_item.description}</p>`;
                }

                if (newsItem.news_item.content) {
                    articleHtml += `<div>${newsItem.news_item.content}</div>`;
                } else {
                    articleHtml += `<p>Full article content is not available in the feed.</p>`;
                }

                // Add categories if available
                if (newsItem.categories && newsItem.categories.length > 0) {
                    articleHtml += `
                        <div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid #334155;">
                            <strong>Categories:</strong> ${newsItem.categories.map(cat => `<span class="badge">${cat}</span>`).join(' ')}
                        </div>
                    `;
                }

                // Add link to original article
                if (newsItem.news_item.link) {
                    articleHtml += `
                        <div style="margin-top: 24px; padding-top: 20px; border-top: 1px solid #334155; text-align: center;">
                            <a href="${newsItem.news_item.link}" target="_blank" class="read-more-link">
                                Read Full Article on ${newsItem.news_item.source} →
                            </a>
                        </div>
                    `;
                }

                content.innerHTML = articleHtml;

            } catch (error) {
                console.error('Error fetching article:', error);
                content.innerHTML = `
                    <p>Error loading article content.</p>
                    ${newsItem.news_item.link ? `
                        <a href="${newsItem.news_item.link}" target="_blank" class="read-more-link">
                            Read on ${newsItem.news_item.source} →
                        </a>
                    ` : ''}
                `;
            }
        }

        function closeArticleModal() {
            const modal = document.getElementById('article-modal');
            modal.classList.remove('active');
        }

        // Close modal when clicking outside content
        document.addEventListener('click', function(event) {
            const modal = document.getElementById('article-modal');
            if (event.target === modal) {
                closeArticleModal();
            }
        });

        // Close modal with Escape key
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                closeArticleModal();
            }
        });

        function updateOverviewTab(data) {
            // Regime overview
            if (data.regime) {
                const regime = data.regime;
                document.getElementById('regime-overview').innerHTML = `
                    <div style="text-align: center; margin: 20px 0;">
                        <span class="badge regime-${regime.state}" style="font-size: 1.2em; padding: 10px 20px;">
                            ${regime.state}
                        </span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Confidence</span>
                        <span class="data-value">${(regime.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Time in State</span>
                        <span class="data-value">${regime.time_in_state_formatted}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Trading Enabled</span>
                        <span class="data-value ${regime.permissions.trading_enabled ? 'positive' : 'negative'}">
                            ${regime.permissions.trading_enabled ? '✅ Yes' : '❌ No'}
                        </span>
                    </div>
                `;
            }

            // DXY overview
            if (data.macro && data.macro.dxy) {
                const dxy = data.macro.dxy;
                document.getElementById('dxy-overview').innerHTML = `
                    <div class="big-number-label">Current Value</div>
                    <div class="big-number">${parseFloat(dxy.value).toFixed(2)}</div>
                    ${dxy.change_percent ? `
                    <div class="data-row">
                        <span class="data-label">24h Change</span>
                        <span class="data-value ${dxy.change_percent > 0 ? 'positive' : 'negative'}">
                            ${dxy.change_percent > 0 ? '+' : ''}${parseFloat(dxy.change_percent).toFixed(2)}%
                        </span>
                    </div>
                    ` : ''}
                    <div class="data-row">
                        <span class="data-label">Source</span>
                        <span class="data-value">${dxy.source}</span>
                    </div>
                `;
            }

            // BTC Dominance overview
            if (data.macro && data.macro.btc_dominance) {
                const dom = data.macro.btc_dominance;
                document.getElementById('btc-dom-overview').innerHTML = `
                    <div class="big-number-label">Dominance</div>
                    <div class="big-number">${parseFloat(dom.value).toFixed(2)}%</div>
                    ${dom.change_percent ? `
                    <div class="data-row">
                        <span class="data-label">24h Change</span>
                        <span class="data-value ${dom.change_percent > 0 ? 'positive' : 'negative'}">
                            ${dom.change_percent > 0 ? '+' : ''}${parseFloat(dom.change_percent).toFixed(2)}%
                        </span>
                    </div>
                    ` : ''}
                `;
            }

            // BTC Price overview
            if (data.bybit && data.bybit.latest_trade) {
                const trade = data.bybit.latest_trade;
                document.getElementById('btc-price-overview').innerHTML = `
                    <div class="big-number-label">Current Price</div>
                    <div class="big-number">$${parseFloat(trade.price).toLocaleString()}</div>
                    <div class="data-row">
                        <span class="data-label">Last Side</span>
                        <span class="data-value ${trade.side === 'Buy' ? 'positive' : 'negative'}">${trade.side}</span>
                    </div>
                `;
            }

            // News overview
            if (data.news && data.news.latest) {
                const news = data.news.latest;
                document.getElementById('news-overview').innerHTML = `
                    <div class="news-item">
                        <div class="news-title">${news.title}</div>
                        <div class="news-meta">
                            <span>Source: ${news.source}</span>
                        </div>
                    </div>
                `;
            }
        }

        function updateMarketTab(data) {
            // Latest Trade
            if (data.bybit && data.bybit.latest_trade) {
                const trade = data.bybit.latest_trade;
                document.getElementById('latest-trade').innerHTML = `
                    <div class="big-number-label">Price</div>
                    <div class="big-number">$${parseFloat(trade.price).toLocaleString()}</div>
                    <div class="data-row">
                        <span class="data-label">Symbol</span>
                        <span class="data-value">${trade.symbol}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Side</span>
                        <span class="data-value ${trade.side === 'Buy' ? 'positive' : 'negative'}">${trade.side}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Quantity</span>
                        <span class="data-value">${parseFloat(trade.quantity).toFixed(4)}</span>
                    </div>
                `;
            }

            // Latest Kline
            if (data.bybit && data.bybit.latest_kline) {
                const kline = data.bybit.latest_kline;
                document.getElementById('latest-kline').innerHTML = `
                    <div class="data-row">
                        <span class="data-label">Open</span>
                        <span class="data-value">$${parseFloat(kline.open).toLocaleString()}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">High</span>
                        <span class="data-value positive">$${parseFloat(kline.high).toLocaleString()}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Low</span>
                        <span class="data-value negative">$${parseFloat(kline.low).toLocaleString()}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Close</span>
                        <span class="data-value">$${parseFloat(kline.close).toLocaleString()}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Volume</span>
                        <span class="data-value">${parseFloat(kline.volume).toFixed(2)}</span>
                    </div>
                `;
            }
        }

        function updateMacroTab(data) {
            // Detailed DXY
            if (data.macro && data.macro.dxy) {
                const dxy = data.macro.dxy;
                const trends = data.macro.trends?.dxy;
                document.getElementById('dxy-detailed').innerHTML = `
                    <div class="big-number">${parseFloat(dxy.value).toFixed(2)}</div>
                    <div class="data-row">
                        <span class="data-label">Change</span>
                        <span class="data-value ${dxy.change_percent > 0 ? 'positive' : 'negative'}">
                            ${dxy.change_percent ? (dxy.change_percent > 0 ? '+' : '') + parseFloat(dxy.change_percent).toFixed(2) + '%' : 'N/A'}
                        </span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Source</span>
                        <span class="data-value">${dxy.source}</span>
                    </div>
                    ${trends ? `
                    <div class="data-row">
                        <span class="data-label">Trend</span>
                        <span class="data-value">${trends.direction} (${trends.strength})</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Signal</span>
                        <span class="data-value ${getRegimeColor(trends.signal)}">${trends.signal}</span>
                    </div>
                    ` : ''}
                `;
            }

            // Detailed BTC Dominance
            if (data.macro && data.macro.btc_dominance) {
                const dom = data.macro.btc_dominance;
                const trends = data.macro.trends?.btc_dominance;
                document.getElementById('btc-dom-detailed').innerHTML = `
                    <div class="big-number">${parseFloat(dom.value).toFixed(2)}%</div>
                    <div class="data-row">
                        <span class="data-label">Change</span>
                        <span class="data-value ${dom.change_percent > 0 ? 'positive' : 'negative'}">
                            ${dom.change_percent ? (dom.change_percent > 0 ? '+' : '') + parseFloat(dom.change_percent).toFixed(2) + '%' : 'N/A'}
                        </span>
                    </div>
                    ${trends ? `
                    <div class="data-row">
                        <span class="data-label">Trend</span>
                        <span class="data-value">${trends.direction} (${trends.strength})</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Signal</span>
                        <span class="data-value ${getRegimeColor(trends.signal)}">${trends.signal}</span>
                    </div>
                    ` : ''}
                `;
            }

            // Trend Analysis
            if (data.macro && data.macro.trends) {
                const trends = data.macro.trends;
                document.getElementById('trend-analysis').innerHTML = `
                    <div class="data-row">
                        <span class="data-label">DXY Trend</span>
                        <span class="data-value">${trends.dxy?.direction || 'N/A'} (${trends.dxy?.strength || 'N/A'})</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">DXY Signal</span>
                        <span class="data-value ${getRegimeColor(trends.dxy?.signal)}">${trends.dxy?.signal || 'N/A'}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">BTC.D Trend</span>
                        <span class="data-value">${trends.btc_dominance?.direction || 'N/A'} (${trends.btc_dominance?.strength || 'N/A'})</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">BTC.D Signal</span>
                        <span class="data-value ${getRegimeColor(trends.btc_dominance?.signal)}">${trends.btc_dominance?.signal || 'N/A'}</span>
                    </div>
                `;
            }
        }

        function updateRegimeTab(data) {
            if (data.regime) {
                const regime = data.regime;

                // Detailed regime state
                document.getElementById('regime-detailed').innerHTML = `
                    <div style="text-align: center; margin-bottom: 24px;">
                        <span class="badge regime-${regime.state}" style="font-size: 1.3em; padding: 12px 24px;">
                            ${regime.state}
                        </span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Confidence</span>
                        <span class="data-value">${(regime.confidence * 100).toFixed(1)}%</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Time in State</span>
                        <span class="data-value">${regime.time_in_state_formatted}</span>
                    </div>
                `;

                // Contributions
                document.getElementById('regime-contributions').innerHTML = `
                    <div class="data-row">
                        <span class="data-label">DXY Contribution</span>
                        <span class="data-value">${(regime.dxy_contribution * 100).toFixed(1)}%</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">BTC.D Contribution</span>
                        <span class="data-value">${(regime.btc_dom_contribution * 100).toFixed(1)}%</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">News Contribution</span>
                        <span class="data-value">${(regime.news_contribution * 100).toFixed(1)}%</span>
                    </div>
                `;

                // Permissions
                const perms = regime.permissions;
                document.getElementById('regime-permissions').innerHTML = `
                    <div class="data-row">
                        <span class="data-label">Trading Enabled</span>
                        <span class="data-value ${perms.trading_enabled ? 'positive' : 'negative'}">
                            ${perms.trading_enabled ? '✅ Yes' : '❌ No'}
                        </span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Position Size</span>
                        <span class="data-value">${(perms.position_size_multiplier * 100).toFixed(0)}%</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Max Open Positions</span>
                        <span class="data-value">${perms.max_open_positions}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">Preferred Trades</span>
                        <span class="data-value">${perms.preferred_trades.join(', ') || 'None'}</span>
                    </div>
                `;
            }
        }

        function updateSystemTab(data) {
            document.getElementById('system-health').innerHTML = `
                <div class="data-row">
                    <span class="data-label">Bybit WebSocket</span>
                    <span class="data-value ${data.bybit?.connected ? 'positive' : 'negative'}">
                        <span class="status-dot ${data.bybit?.connected ? 'status-online' : 'status-offline'}"></span>
                        ${data.bybit?.connected ? 'Connected' : 'Disconnected'}
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">DXY Data</span>
                    <span class="data-value ${data.macro?.dxy ? 'positive' : 'negative'}">
                        ${data.macro?.dxy ? '✅ Available' : '❌ Unavailable'}
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">BTC Dominance</span>
                    <span class="data-value ${data.macro?.btc_dominance ? 'positive' : 'negative'}">
                        ${data.macro?.btc_dominance ? '✅ Available' : '❌ Unavailable'}
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">News Feed</span>
                    <span class="data-value ${data.news?.latest ? 'positive' : 'negative'}">
                        ${data.news?.latest ? '✅ Active' : '❌ Inactive'}
                    </span>
                </div>
                <div class="data-row">
                    <span class="data-label">Regime Engine</span>
                    <span class="data-value ${data.regime ? 'positive' : 'negative'}">
                        ${data.regime ? '✅ Running' : '❌ Stopped'}
                    </span>
                </div>
            `;
        }

        async function fetchTimeframeAnalysis() {
            try {
                const response = await fetch('/api/timeframe-analysis');
                const data = await response.json();

                if (data.error) {
                    console.error('Timeframe analysis error:', data.error);
                    document.getElementById('timeframe-analysis').innerHTML = `
                        <div class="loading">Error loading timeframe analysis: ${data.error}</div>
                    `;
                    return;
                }

                updateTimeframeAnalysis(data);
            } catch (error) {
                console.error('Error fetching timeframe analysis:', error);
                document.getElementById('timeframe-analysis').innerHTML = `
                    <div class="loading">Error loading timeframe analysis</div>
                `;
            }
        }

        function updateTimeframeAnalysis(data) {
            const container = document.getElementById('timeframe-analysis');

            // Order of timeframes to display
            const timeframeOrder = ['15M', '1H', '4H', 'Daily'];

            const html = timeframeOrder.map(tf => {
                const analysis = data[tf];
                if (!analysis) return '';

                const biasClass = analysis.bias.toLowerCase();
                const confidencePercent = (analysis.confidence * 100).toFixed(1);

                return `
                    <div class="timeframe-card ${biasClass}">
                        <div class="timeframe-header">
                            <div class="timeframe-name">${analysis.timeframe}</div>
                            <div class="bias-badge ${biasClass}">${analysis.bias}</div>
                        </div>

                        <div class="confidence-text">Confidence: ${confidencePercent}%</div>
                        <div class="confidence-bar-container">
                            <div class="confidence-bar ${biasClass}" style="width: ${confidencePercent}%"></div>
                        </div>

                        <div class="timeframe-details">
                            <div class="detail-row">
                                <span class="detail-label">Price</span>
                                <span>$${analysis.current_price.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Trend</span>
                                <span>${analysis.trend_direction} (${(analysis.trend_strength * 100).toFixed(0)}%)</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">MA Alignment</span>
                                <span>${analysis.ma_alignment.replace(/_/g, ' ')}</span>
                            </div>
                        </div>

                        ${analysis.supporting_factors && analysis.supporting_factors.length > 0 ? `
                        <div class="factors-section">
                            <div class="factors-title">✅ Supporting Factors</div>
                            <ul class="factor-list">
                                ${analysis.supporting_factors.slice(0, 3).map(factor => `
                                    <li class="factor-item supporting">${factor}</li>
                                `).join('')}
                            </ul>
                        </div>
                        ` : ''}

                        ${analysis.conflicting_factors && analysis.conflicting_factors.length > 0 ? `
                        <div class="factors-section">
                            <div class="factors-title">⚠️ Conflicting Factors</div>
                            <ul class="factor-list">
                                ${analysis.conflicting_factors.slice(0, 2).map(factor => `
                                    <li class="factor-item conflicting">${factor}</li>
                                `).join('')}
                            </ul>
                        </div>
                        ` : ''}

                        <div class="explanation">
                            ${analysis.explanation}
                        </div>
                    </div>
                `;
            }).join('');

            container.innerHTML = html || '<div class="loading">No timeframe analysis data available</div>';
        }

        // Initialize
        fetchData();
        fetchNewsData();
        fetchTimeframeAnalysis();
        setInterval(fetchData, 5000);
        setInterval(fetchNewsData, 30000);
        setInterval(fetchTimeframeAnalysis, 60000); // Update timeframe analysis every 60 seconds
    </script>
</body>
</html>
"""
