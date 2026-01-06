"""Enhanced UI template with regime and news classification"""

UI_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>BTC Trading Bot Dashboard - Macro-Aware</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
        }
        .container {
            max-width: 1600px;
            margin: 0 auto;
        }
        h1 {
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            opacity: 0.9;
            margin-bottom: 30px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }
        .card.featured {
            grid-column: span 2;
            background: rgba(255, 255, 255, 0.15);
        }
        .card h2 {
            margin-top: 0;
            font-size: 1.2em;
            border-bottom: 2px solid rgba(255, 255, 255, 0.3);
            padding-bottom: 10px;
        }
        .data-item {
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        .data-label {
            font-weight: bold;
        }
        .data-value {
            text-align: right;
        }
        .positive {
            color: #4ade80;
        }
        .negative {
            color: #f87171;
        }
        .neutral {
            color: #fbbf24;
        }
        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-online {
            background: #4ade80;
            box-shadow: 0 0 10px #4ade80;
        }
        .status-offline {
            background: #f87171;
        }
        .regime-badge {
            display: inline-block;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            margin: 5px 5px 5px 0;
        }
        .regime-RISK_ON {
            background: #4ade80;
            color: #065f46;
        }
        .regime-RISK_OFF {
            background: #f87171;
            color: #7f1d1d;
        }
        .regime-DECOUPLED {
            background: #60a5fa;
            color: #1e3a8a;
        }
        .regime-CHOP {
            background: #fbbf24;
            color: #78350f;
        }
        .confidence-bar {
            width: 100%;
            height: 8px;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }
        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #4ade80, #60a5fa);
            transition: width 0.3s;
        }
        button {
            background: rgba(255, 255, 255, 0.2);
            border: 1px solid rgba(255, 255, 255, 0.3);
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            margin-top: 10px;
        }
        button:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        .tag {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.75em;
            margin: 2px;
            background: rgba(255, 255, 255, 0.2);
        }
        .impact-HIGH {
            background: #f87171;
        }
        .impact-MEDIUM {
            background: #fbbf24;
        }
        .impact-LOW {
            background: #60a5fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Macro-Aware BTC Trading Bot</h1>
        <div class="subtitle">Module 1-4 Active: Config, Data Ingestion, News Classification & Regime Engine</div>

        <!-- Regime State (Featured) -->
        <div class="grid">
            <div class="card featured">
                <h2>📊 Current Regime State</h2>
                <div id="regime-state"></div>
            </div>
        </div>

        <!-- Main Grid -->
        <div class="grid">
            <div class="card">
                <h2><span class="status-indicator status-online"></span>System Status</h2>
                <div id="system-status"></div>
                <button onclick="refreshData()">Refresh Data</button>
            </div>

            <div class="card">
                <h2>📈 Latest Trade</h2>
                <div id="latest-trade"></div>
            </div>

            <div class="card">
                <h2>📊 Latest Kline (5m)</h2>
                <div id="latest-kline"></div>
            </div>

            <div class="card">
                <h2>💵 DXY (US Dollar Index)</h2>
                <div id="dxy-data"></div>
            </div>

            <div class="card">
                <h2>₿ BTC Dominance</h2>
                <div id="btc-dom-data"></div>
            </div>

            <div class="card">
                <h2>📰 Latest News & Classification</h2>
                <div id="news-data"></div>
            </div>

            <div class="card">
                <h2>📉 Trend Analysis</h2>
                <div id="trend-data"></div>
            </div>

            <div class="card">
                <h2>🎯 News Signals</h2>
                <div id="news-signals"></div>
            </div>
        </div>
    </div>

    <script>
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

                // Regime State
                if (data.regime) {
                    const regime = data.regime;
                    const permissions = regime.permissions;
                    document.getElementById('regime-state').innerHTML = `
                        <div style="text-align: center; margin: 20px 0;">
                            <span class="regime-badge regime-${regime.state}">${regime.state}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Confidence</span>
                            <span class="data-value">${(regime.confidence * 100).toFixed(1)}%</span>
                        </div>
                        <div class="confidence-bar">
                            <div class="confidence-fill" style="width: ${regime.confidence * 100}%"></div>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Time in State</span>
                            <span class="data-value">${regime.time_in_state_formatted}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Trading Enabled</span>
                            <span class="data-value ${permissions.trading_enabled ? 'positive' : 'negative'}">
                                ${permissions.trading_enabled ? '✅ Yes' : '❌ No'}
                            </span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Position Size Multiplier</span>
                            <span class="data-value">${(permissions.position_size_multiplier * 100).toFixed(0)}%</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Preferred Trades</span>
                            <span class="data-value">${permissions.preferred_trades.join(', ') || 'None'}</span>
                        </div>
                    `;
                } else {
                    document.getElementById('regime-state').innerHTML = '<p>Calculating regime...</p>';
                }

                // System Status
                document.getElementById('system-status').innerHTML = `
                    <div class="data-item">
                        <span class="data-label">Bybit WS</span>
                        <span class="data-value">${data.bybit.connected ? '✅ Connected' : '❌ Disconnected'}</span>
                    </div>
                `;

                // Latest Trade
                if (data.bybit.latest_trade) {
                    const trade = data.bybit.latest_trade;
                    document.getElementById('latest-trade').innerHTML = `
                        <div class="data-item">
                            <span class="data-label">Symbol</span>
                            <span class="data-value">${trade.symbol}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Price</span>
                            <span class="data-value">$${parseFloat(trade.price).toFixed(2)}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Quantity</span>
                            <span class="data-value">${parseFloat(trade.quantity).toFixed(4)}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Side</span>
                            <span class="data-value ${trade.side === 'Buy' ? 'positive' : 'negative'}">${trade.side}</span>
                        </div>
                    `;
                }

                // Latest Kline
                if (data.bybit.latest_kline) {
                    const kline = data.bybit.latest_kline;
                    document.getElementById('latest-kline').innerHTML = `
                        <div class="data-item">
                            <span class="data-label">Open</span>
                            <span class="data-value">$${parseFloat(kline.open).toFixed(2)}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">High</span>
                            <span class="data-value positive">$${parseFloat(kline.high).toFixed(2)}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Low</span>
                            <span class="data-value negative">$${parseFloat(kline.low).toFixed(2)}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Close</span>
                            <span class="data-value">$${parseFloat(kline.close).toFixed(2)}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Volume</span>
                            <span class="data-value">${parseFloat(kline.volume).toFixed(2)}</span>
                        </div>
                    `;
                }

                // DXY
                if (data.macro.dxy) {
                    const dxy = data.macro.dxy;
                    const trends = data.macro.trends?.dxy;
                    document.getElementById('dxy-data').innerHTML = `
                        <div class="data-item">
                            <span class="data-label">Value</span>
                            <span class="data-value">${parseFloat(dxy.value).toFixed(2)}</span>
                        </div>
                        ${dxy.change_percent ? `
                        <div class="data-item">
                            <span class="data-label">Change</span>
                            <span class="data-value ${dxy.change_percent > 0 ? 'positive' : 'negative'}">
                                ${dxy.change_percent > 0 ? '+' : ''}${parseFloat(dxy.change_percent).toFixed(2)}%
                            </span>
                        </div>
                        ` : ''}
                        ${trends ? `
                        <div class="data-item">
                            <span class="data-label">Trend</span>
                            <span class="data-value">${trends.direction} (${trends.strength})</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Signal</span>
                            <span class="data-value ${getRegimeColor(trends.signal)}">${trends.signal}</span>
                        </div>
                        ` : ''}
                    `;
                } else {
                    document.getElementById('dxy-data').innerHTML = '<p>Loading...</p>';
                }

                // BTC Dominance
                if (data.macro.btc_dominance) {
                    const dom = data.macro.btc_dominance;
                    const trends = data.macro.trends?.btc_dominance;
                    document.getElementById('btc-dom-data').innerHTML = `
                        <div class="data-item">
                            <span class="data-label">Dominance</span>
                            <span class="data-value">${parseFloat(dom.value).toFixed(2)}%</span>
                        </div>
                        ${dom.change_percent ? `
                        <div class="data-item">
                            <span class="data-label">Change</span>
                            <span class="data-value ${dom.change_percent > 0 ? 'positive' : 'negative'}">
                                ${dom.change_percent > 0 ? '+' : ''}${parseFloat(dom.change_percent).toFixed(2)}%
                            </span>
                        </div>
                        ` : ''}
                        ${trends ? `
                        <div class="data-item">
                            <span class="data-label">Trend</span>
                            <span class="data-value">${trends.direction} (${trends.strength})</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Signal</span>
                            <span class="data-value ${getRegimeColor(trends.signal)}">${trends.signal}</span>
                        </div>
                        ` : ''}
                    `;
                } else {
                    document.getElementById('btc-dom-data').innerHTML = '<p>Loading...</p>';
                }

                // News with Classification
                if (data.news.latest) {
                    const news = data.news.latest;
                    document.getElementById('news-data').innerHTML = `
                        <div class="data-item">
                            <span class="data-label">Source</span>
                            <span class="data-value">${news.source}</span>
                        </div>
                        ${news.impact_level ? `
                        <div class="data-item">
                            <span class="data-label">Impact</span>
                            <span class="data-value"><span class="tag impact-${news.impact_level}">${news.impact_level}</span></span>
                        </div>
                        ` : ''}
                        ${news.sentiment_score !== null ? `
                        <div class="data-item">
                            <span class="data-label">Sentiment</span>
                            <span class="data-value ${news.sentiment_score > 0 ? 'positive' : news.sentiment_score < 0 ? 'negative' : 'neutral'}">
                                ${news.sentiment_score > 0 ? '😊' : news.sentiment_score < 0 ? '😟' : '😐'} ${news.sentiment_score.toFixed(2)}
                            </span>
                        </div>
                        ` : ''}
                        <p style="margin-top: 10px; line-height: 1.5; font-size: 0.9em;">${news.title}</p>
                    `;
                } else {
                    document.getElementById('news-data').innerHTML = '<p>No news available</p>';
                }

                // Trend Analysis
                if (data.macro.trends) {
                    const trends = data.macro.trends;
                    document.getElementById('trend-data').innerHTML = `
                        <div class="data-item">
                            <span class="data-label">DXY Trend</span>
                            <span class="data-value">${trends.dxy.direction || 'N/A'}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">BTC.D Trend</span>
                            <span class="data-value">${trends.btc_dominance.direction || 'N/A'}</span>
                        </div>
                    `;
                } else {
                    document.getElementById('trend-data').innerHTML = '<p>Calculating trends...</p>';
                }

                // News Signals
                if (data.news.signals) {
                    const signals = data.news.signals;
                    document.getElementById('news-signals').innerHTML = `
                        <div class="data-item">
                            <span class="data-label">Active News</span>
                            <span class="data-value">${signals.news_count}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Risk Signal</span>
                            <span class="data-value ${getRegimeColor(signals.risk_signal)}">${signals.risk_signal}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">Alignment</span>
                            <span class="data-value">${signals.alignment}</span>
                        </div>
                        <div class="data-item">
                            <span class="data-label">High Impact</span>
                            <span class="data-value ${signals.high_impact_count > 0 ? 'negative' : ''}">
                                ${signals.high_impact_count}
                            </span>
                        </div>
                    `;
                } else {
                    document.getElementById('news-signals').innerHTML = '<p>No signals available</p>';
                }

            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }

        function refreshData() {
            fetchData();
        }

        fetchData();
        setInterval(fetchData, 5000);
    </script>
</body>
</html>
"""
