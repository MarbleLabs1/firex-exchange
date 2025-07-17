# Solana DEX Frontend

This is the frontend interface for the Solana DEX application. It provides a modern, user-friendly interface for trading, analytics, and market-making operations.

## Features

- **Trading Interface**
  - Real-time order book display
  - Recent trades feed
  - Limit and market order placement
  - Multiple market support

- **Analytics Dashboard**
  - Market metrics and statistics
  - Price and volume charts
  - Historical data analysis

- **Market Making Controls**
  - Automated market making strategy
  - Customizable parameters
  - Real-time strategy status

## Installation

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the application:
   ```bash
   python main_window.py
   ```

## Dependencies

- PyQt6: GUI framework
- Plotly: Interactive charts
- Pandas: Data manipulation
- NumPy: Numerical computations

## Development

The frontend is built using PyQt6 and follows a modular design pattern. The main components are:

- `main_window.py`: Main application window and UI setup
- `styles.qss`: Application stylesheet
- `resources/`: Icons and other resources

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 