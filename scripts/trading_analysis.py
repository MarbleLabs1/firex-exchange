import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import talib as ta
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TradingAnalyzer:
    """Class to analyze trading data and generate signals"""
    
    def __init__(self, data=None):
        """Initialize with historical price data or load sample data"""
        self.data = data if data is not None else self.generate_sample_data()
        
    def generate_sample_data(self, days=180):
        """Generate sample OHLCV data for testing"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Generate random price data with a trend
        np.random.seed(42)  # for reproducibility
        base_price = 100
        trend = np.linspace(0, 20, len(date_range)) + np.random.normal(0, 5, len(date_range))
        close_prices = base_price + np.cumsum(np.random.normal(0, 2, len(date_range))) + trend
        
        # Generate OHLCV data
        data = []
        for i, date in enumerate(date_range):
            close = close_prices[i]
            # Random variations for open, high, low
            open_price = close + np.random.normal(0, 1)
            high = max(open_price, close) + abs(np.random.normal(0, 1))
            low = min(open_price, close) - abs(np.random.normal(0, 1))
            volume = np.random.normal(1000000, 500000) * (1 + abs(close - open_price) / 10)
            
            data.append({
                'date': date,
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        return pd.DataFrame(data)
    
    def calculate_indicators(self):
        """Calculate technical indicators on the price data"""
        df = self.data.copy()
        
        # Basic indicators
        df['sma_20'] = ta.SMA(df['close'].values, timeperiod=20)
        df['sma_50'] = ta.SMA(df['close'].values, timeperiod=50)
        df['sma_200'] = ta.SMA(df['close'].values, timeperiod=200)
        
        # Bollinger Bands
        upperband, middleband, lowerband = ta.BBANDS(
            df['close'].values, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
        df['bb_upper'] = upperband
        df['bb_middle'] = middleband
        df['bb_lower'] = lowerband
        
        # RSI
        df['rsi'] = ta.RSI(df['close'].values, timeperiod=14)
        
        # MACD
        macd, macdsignal, macdhist = ta.MACD(
            df['close'].values, fastperiod=12, slowperiod=26, signalperiod=9)
        df['macd'] = macd
        df['macd_signal'] = macdsignal
        df['macd_hist'] = macdhist
        
        # Stochastic
        slowk, slowd = ta.STOCH(
            df['high'].values, df['low'].values, df['close'].values,
            fastk_period=5, slowk_period=3, slowk_matype=0, slowd_period=3, slowd_matype=0)
        df['stoch_k'] = slowk
        df['stoch_d'] = slowd
        
        # ATR - Average True Range (volatility)
        df['atr'] = ta.ATR(df['high'].values, df['low'].values, df['close'].values, timeperiod=14)
        
        # OBV - On Balance Volume
        df['obv'] = ta.OBV(df['close'].values, df['volume'].values)
        
        return df
    
    def generate_trading_signals(self):
        """Generate trading signals based on indicators"""
        df = self.calculate_indicators()
        
        # Initialize signal column
        df['signal'] = 0  # 0: no signal, 1: buy, -1: sell
        
        # SMA crossover strategy
        df['sma_cross'] = 0
        df.loc[df['sma_20'] > df['sma_50'], 'sma_cross'] = 1
        df.loc[df['sma_20'] < df['sma_50'], 'sma_cross'] = -1
        
        # RSI strategy
        df['rsi_signal'] = 0
        df.loc[df['rsi'] < 30, 'rsi_signal'] = 1  # oversold -> buy
        df.loc[df['rsi'] > 70, 'rsi_signal'] = -1  # overbought -> sell
        
        # MACD strategy
        df['macd_signal_line'] = 0
        df.loc[df['macd'] > df['macd_signal'], 'macd_signal_line'] = 1
        df.loc[df['macd'] < df['macd_signal'], 'macd_signal_line'] = -1
        
        # Bollinger Bands strategy
        df['bb_signal'] = 0
        df.loc[df['close'] < df['bb_lower'], 'bb_signal'] = 1  # price below lower band -> buy
        df.loc[df['close'] > df['bb_upper'], 'bb_signal'] = -1  # price above upper band -> sell
        
        # Combine signals (simple version)
        # Generate a buy signal if at least 2 indicators suggest buying
        # Generate a sell signal if at least 2 indicators suggest selling
        df['buy_count'] = (df['sma_cross'] == 1).astype(int) + \
                          (df['rsi_signal'] == 1).astype(int) + \
                          (df['macd_signal_line'] == 1).astype(int) + \
                          (df['bb_signal'] == 1).astype(int)
        
        df['sell_count'] = (df['sma_cross'] == -1).astype(int) + \
                           (df['rsi_signal'] == -1).astype(int) + \
                           (df['macd_signal_line'] == -1).astype(int) + \
                           (df['bb_signal'] == -1).astype(int)
        
        # Generate final signals
        df.loc[df['buy_count'] >= 2, 'signal'] = 1
        df.loc[df['sell_count'] >= 2, 'signal'] = -1
        
        return df
    
    def plot_analysis(self):
        """Create an advanced plotly visualization of the price and indicators"""
        df = self.generate_trading_signals()
        
        # Create figure with secondary y-axis
        fig = make_subplots(rows=4, cols=1, 
                           shared_xaxes=True,
                           vertical_spacing=0.02,
                           row_heights=[0.5, 0.15, 0.15, 0.2],
                           subplot_titles=("Price and Indicators", "RSI", "MACD", "Volume"))
        
        # Add candlestick trace
        fig.add_trace(go.Candlestick(x=df['date'],
                                    open=df['open'], high=df['high'],
                                    low=df['low'], close=df['close'],
                                    name='Price'), row=1, col=1)
        
        # Add moving averages
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_20'], name='SMA 20', line=dict(color='blue')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_50'], name='SMA 50', line=dict(color='orange')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['sma_200'], name='SMA 200', line=dict(color='red')), row=1, col=1)
        
        # Add Bollinger Bands
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_upper'], name='BB Upper', line=dict(color='rgba(0,128,0,0.3)')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_middle'], name='BB Middle', line=dict(color='rgba(0,128,0,0.3)')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['bb_lower'], name='BB Lower', line=dict(color='rgba(0,128,0,0.3)')), row=1, col=1)
        
        # Add buy signals
        buy_signals = df[df['signal'] == 1]
        fig.add_trace(go.Scatter(x=buy_signals['date'], y=buy_signals['low'] * 0.99, 
                                mode='markers', marker=dict(symbol='triangle-up', size=10, color='green'),
                                name='Buy Signal'), row=1, col=1)
        
        # Add sell signals
        sell_signals = df[df['signal'] == -1]
        fig.add_trace(go.Scatter(x=sell_signals['date'], y=sell_signals['high'] * 1.01, 
                                mode='markers', marker=dict(symbol='triangle-down', size=10, color='red'),
                                name='Sell Signal'), row=1, col=1)
        
        # Add RSI
        fig.add_trace(go.Scatter(x=df['date'], y=df['rsi'], name='RSI', line=dict(color='purple')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=[70] * len(df), name='Overbought', line=dict(color='red', dash='dash')), row=2, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=[30] * len(df), name='Oversold', line=dict(color='green', dash='dash')), row=2, col=1)
        
        # Add MACD
        fig.add_trace(go.Scatter(x=df['date'], y=df['macd'], name='MACD', line=dict(color='blue')), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['date'], y=df['macd_signal'], name='Signal', line=dict(color='red')), row=3, col=1)
        
        # Add MACD histogram
        colors = ['green' if val >= 0 else 'red' for val in df['macd_hist']]
        fig.add_trace(go.Bar(x=df['date'], y=df['macd_hist'], name='Histogram', marker=dict(color=colors)), row=3, col=1)
        
        # Add volume
        fig.add_trace(go.Bar(x=df['date'], y=df['volume'], name='Volume', marker=dict(color='blue')), row=4, col=1)
        
        # Update layout
        fig.update_layout(title='Advanced Technical Analysis',
                          xaxis_title='Date',
                          yaxis_title='Price',
                          height=1200,
                          width=1200,
                          showlegend=False,
                          template='plotly_dark')
        
        # Update y-axis labels
        fig.update_yaxes(title_text="Price", row=1, col=1)
        fig.update_yaxes(title_text="RSI", row=2, col=1)
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        fig.update_yaxes(title_text="Volume", row=4, col=1)
        
        # Update layout for subplots
        fig.update_xaxes(rangeslider_visible=False)
        fig.update_xaxes(title_text="Date", row=4, col=1)
        
        # Remove rangesliders
        fig.update_layout(xaxis_rangeslider_visible=False,
                          xaxis2_rangeslider_visible=False,
                          xaxis3_rangeslider_visible=False,
                          xaxis4_rangeslider_visible=False)
        
        return fig
    
    def pattern_recognition(self):
        """Identify candlestick patterns in the price data"""
        df = self.data.copy()
        
        # Candlestick pattern recognition using TA-Lib
        pattern_functions = [
            ("Hammer", ta.CDLHAMMER),
            ("Inverted Hammer", ta.CDLINVERTEDHAMMER),
            ("Engulfing", ta.CDLENGULFING),
            ("Morning Star", ta.CDLMORNINGSTAR),
            ("Evening Star", ta.CDLEVENINGSTAR),
            ("Hanging Man", ta.CDLHANGINGMAN),
            ("Shooting Star", ta.CDLSHOOTINGSTAR),
            ("Doji", ta.CDLDOJI),
            ("Harami", ta.CDLHARAMI),
            ("Three White Soldiers", ta.CDL3WHITESOLDIERS),
            ("Three Black Crows", ta.CDL3BLACKCROWS)
        ]
        
        # Apply pattern recognition
        for pattern_name, pattern_func in pattern_functions:
            df[pattern_name] = pattern_func(df['open'].values, df['high'].values, 
                                           df['low'].values, df['close'].values)
        
        return df
    
    def market_regime_detection(self):
        """Detect market regimes using K-means clustering"""
        df = self.calculate_indicators()
        
        # Features for clustering
        features = ['close', 'rsi', 'macd', 'atr']
        df_features = df[features].dropna()
        
        # Standardize the features
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(df_features)
        
        # Apply K-means clustering (3 regimes: bullish, bearish, sideways)
        kmeans = KMeans(n_clusters=3, random_state=42)
        df_features['regime'] = kmeans.fit_predict(scaled_features)
        
        # Map the regimes back to the original dataframe
        regime_mapping = df_features['regime']
        df.loc[regime_mapping.index, 'regime'] = regime_mapping
        
        # Analyze characteristics of each regime
        regime_stats = df.groupby('regime')[['close', 'rsi', 'macd', 'atr']].mean()
        
        # Label regimes based on characteristics
        highest_close_regime = regime_stats['close'].idxmax()
        lowest_close_regime = regime_stats['close'].idxmin()
        middle_regime = set([0, 1, 2]) - set([highest_close_regime, lowest_close_regime])
        middle_regime = list(middle_regime)[0]
        
        regime_labels = {}
        regime_labels[highest_close_regime] = 'Bullish'
        regime_labels[lowest_close_regime] = 'Bearish'
        regime_labels[middle_regime] = 'Sideways'
        
        df['regime_label'] = df['regime'].map(regime_labels)
        
        return df
    
    def plot_regimes(self):
        """Plot price with market regime overlay"""
        df = self.market_regime_detection()
        
        # Create figure
        fig = go.Figure()
        
        # Add candlestick trace
        fig.add_trace(go.Candlestick(x=df['date'],
                                    open=df['open'], high=df['high'],
                                    low=df['low'], close=df['close'],
                                    name='Price'))
        
        # Color regions by regime
        regimes = df['regime_label'].dropna().unique()
        for regime in regimes:
            regime_df = df[df['regime_label'] == regime]
            if regime_df.empty:
                continue
                
            color_map = {'Bullish': 'rgba(0, 255, 0, 0.1)', 
                         'Bearish': 'rgba(255, 0, 0, 0.1)', 
                         'Sideways': 'rgba(255, 255, 0, 0.1)'}
            
            # Create shaded regions for each continuous period of the regime
            date_groups = []
            current_group = []
            
            # Group consecutive dates with the same regime
            for date in regime_df['date'].sort_values():
                if not current_group or (date - current_group[-1]).days <= 2:  # Allow 1 day gap
                    current_group.append(date)
                else:
                    date_groups.append(current_group)
                    current_group = [date]
            
            if current_group:
                date_groups.append(current_group)
            
            # Add shaded areas for each group
            for group in date_groups:
                start_date = min(group)
                end_date = max(group)
                
                fig.add_vrect(
                    x0=start_date, x1=end_date,
                    fillcolor=color_map[regime],
                    opacity=0.5,
                    layer="below",
                    line_width=0,
                )
        
        # Update layout
        fig.update_layout(title='Market Regimes Analysis',
                          xaxis_title='Date',
                          yaxis_title='Price',
                          height=600,
                          template='plotly_dark',
                          showlegend=True)
        
        # Add annotations for regime types
        fig.add_annotation(x=0.05, y=0.95, xref="paper", yref="paper",
                           text="Green: Bullish, Red: Bearish, Yellow: Sideways",
                           showarrow=False, font=dict(color="white"))
        
        return fig
    
    def calculate_optimal_portfolio(self, assets=['ETH', 'BTC', 'SOL', 'AVAX'], lookback_period=90):
        """Calculate optimal portfolio allocation using modern portfolio theory"""
        # In a real implementation, this would use actual price data for each asset
        # For demo purposes, we'll generate correlated price series
        
        # Generate sample returns for each asset
        np.random.seed(42)
        n_observations = lookback_period
        n_assets = len(assets)
        
        # Create a correlation matrix (realistic correlations between crypto assets)
        # Crypto assets tend to be highly correlated
        corr_matrix = np.array([[1.0, 0.8, 0.7, 0.65],
                                [0.8, 1.0, 0.6, 0.55],
                                [0.7, 0.6, 1.0, 0.7],
                                [0.65, 0.55, 0.7, 1.0]])
        
        # Create mean returns and standard deviations for assets
        mean_returns = np.array([0.0010, 0.0008, 0.0015, 0.0012])  # daily returns
        volatilities = np.array([0.03, 0.025, 0.045, 0.04])        # daily volatility
        
        # Generate random returns
        L = np.linalg.cholesky(corr_matrix)
        uncorrelated_returns = np.random.normal(size=(n_observations, n_assets))
        correlated_returns = uncorrelated_returns @ L.T
        
        # Scale returns to match the target mean and volatility
        for i in range(n_assets):
            correlated_returns[:, i] = mean_returns[i] + volatilities[i] * correlated_returns[:, i]
        
        # Create a DataFrame of returns
        dates = pd.date_range(end=pd.Timestamp.now(), periods=n_observations)
        returns_df = pd.DataFrame(correlated_returns, index=dates, columns=assets)
        
        # Calculate mean returns and covariance matrix
        mean_returns = returns_df.mean()
        cov_matrix = returns_df.cov()
        
        # Generate random portfolios
        num_portfolios = 10000
        results = np.zeros((3, num_portfolios))
        weights_record = []
        
        for i in range(num_portfolios):
            weights = np.random.random(n_assets)
            weights /= np.sum(weights)
            weights_record.append(weights)
            
            # Portfolio return
            portfolio_return = np.sum(mean_returns * weights) * 252  # annualized
            
            # Portfolio volatility
            portfolio_std_dev = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights))) * np.sqrt(252)  # annualized
            
            # Sharpe ratio (assuming risk-free rate of 0.01)
            results[0, i] = portfolio_return
            results[1, i] = portfolio_std_dev
            results[2, i] = (portfolio_return - 0.01) / portfolio_std_dev
        
        # Find the portfolio with the maximum Sharpe ratio
        max_sharpe_idx = np.argmax(results[2])
        optimal_weights = weights_record[max_sharpe_idx]
        
        # Minimum volatility portfolio
        min_vol_idx = np.argmin(results[1])
        min_vol_weights = weights_record[min_vol_idx]
        
        # Return results
        optimal_portfolio = {
            'max_sharpe': {
                'weights': dict(zip(assets, optimal_weights)),
                'return': results[0, max_sharpe_idx],
                'volatility': results[1, max_sharpe_idx],
                'sharpe_ratio': results[2, max_sharpe_idx]
            },
            'min_volatility': {
                'weights': dict(zip(assets, min_vol_weights)),
                'return': results[0, min_vol_idx],
                'volatility': results[1, min_vol_idx],
                'sharpe_ratio': results[2, min_vol_idx]
            },
            'efficient_frontier': {
                'returns': results[0],
                'volatilities': results[1],
                'sharpe_ratios': results[2]
            }
        }
        
        return optimal_portfolio
    
    def plot_efficient_frontier(self):
        """Plot the efficient frontier for portfolio optimization"""
        portfolio = self.calculate_optimal_portfolio()
        
        # Extract data
        returns = portfolio['efficient_frontier']['returns']
        volatilities = portfolio['efficient_frontier']['volatilities']
        sharpe_ratios = portfolio['efficient_frontier']['sharpe_ratios']
        max_sharpe_return = portfolio['max_sharpe']['return']
        max_sharpe_vol = portfolio['max_sharpe']['volatility']
        min_vol_return = portfolio['min_volatility']['return']
        min_vol_vol = portfolio['min_volatility']['volatility']
        
        # Create figure
        fig = go.Figure()
        
        # Add scatter plot of all portfolios
        fig.add_trace(go.Scatter(
            x=volatilities,
            y=returns,
            mode='markers',
            marker=dict(
                size=5,
                color=sharpe_ratios,
                colorscale='Viridis',
                colorbar=dict(title='Sharpe Ratio'),
                line=dict(width=1)
            ),
            name='Portfolios'
        ))
        
        # Add maximum Sharpe ratio portfolio
        fig.add_trace(go.Scatter(
            x=[max_sharpe_vol],
            y=[max_sharpe_return],
            mode='markers',
            marker=dict(
                size=15,
                color='red',
                symbol='star'
            ),
            name='Max Sharpe Ratio'
        ))
        
        # Add minimum volatility portfolio
        fig.add_trace(go.Scatter(
            x=[min_vol_vol],
            y=[min_vol_return],
            mode='markers',
            marker=dict(
                size=15,
                color='green',
                symbol='star'
            ),
            name='Min Volatility'
        ))
        
        # Update layout
        fig.update_layout(
            title='Efficient Frontier',
            xaxis=dict(title='Annualized Volatility'),
            yaxis=dict(title='Annualized Return'),
            height=600,
            width=800,
            template='plotly_dark',
            legend=dict(x=0.02, y=0.98)
        )
        
        return fig

# Demo function to show capabilities
def run_demo():
    analyzer = TradingAnalyzer()
    
    # Generate trading signals
    signals_df = analyzer.generate_trading_signals()
    print(f"Generated {len(signals_df[signals_df['signal'] == 1])} buy signals and {len(signals_df[signals_df['signal'] == -1])} sell signals")
    
    # Detect patterns
    patterns_df = analyzer.pattern_recognition()
    print("\nCandlestick patterns detected:")
    for pattern in patterns_df.columns[6:]:  # skip date, ohlcv columns
        pattern_count = len(patterns_df[patterns_df[pattern] != 0])
        if pattern_count > 0:
            print(f"{pattern}: {pattern_count} instances")
    
    # Market regimes
    regimes_df = analyzer.market_regime_detection()
    regime_counts = regimes_df['regime_label'].value_counts()
    print("\nMarket regimes detected:")
    for regime, count in regime_counts.items():
        print(f"{regime}: {count} days")
    
    # Portfolio optimization
    portfolio = analyzer.calculate_optimal_portfolio()
    print("\nOptimal portfolio allocation (Max Sharpe):")
    for asset, weight in portfolio['max_sharpe']['weights'].items():
        print(f"{asset}: {weight:.2%}")
    print(f"Expected annual return: {portfolio['max_sharpe']['return']:.2%}")
    print(f"Expected annual volatility: {portfolio['max_sharpe']['volatility']:.2%}")
    print(f"Sharpe ratio: {portfolio['max_sharpe']['sharpe_ratio']:.2f}")
    
    # Save plots for analysis
    technical_plot = analyzer.plot_analysis()
    technical_plot.write_html("analysis_charts/technical_analysis.html")
    
    regimes_plot = analyzer.plot_regimes()
    regimes_plot.write_html("analysis_charts/market_regimes.html")
    
    portfolio_plot = analyzer.plot_efficient_frontier()
    portfolio_plot.write_html("analysis_charts/efficient_frontier.html")
    
    print("\nAnalysis complete! Charts saved to 'analysis_charts' directory.")

if __name__ == "__main__":
    # Create output directory if it doesn't exist
    os.makedirs("analysis_charts", exist_ok=True)
    run_demo()

