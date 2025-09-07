# Project: Google Trends Analysis Tool

## Role Definition
This project is designed to analyze and visualize Google Trends data. The assistant should help with:
- Setting up Python environment for data analysis
- Implementing Google Trends API integration
- Creating data visualization components
- Building analysis workflows
- Ensuring code quality and testing

## Project Guidelines

### Environment Setup
- Always use a virtual environment for Python dependencies
- Python version: 3.8+
- Main dependencies: pytrends, pandas, matplotlib, seaborn

### Code Standards
- Follow PEP 8 style guidelines
- Use type hints where applicable
- Write docstrings for all functions and classes
- Implement proper error handling

### Testing
- Write unit tests for core functionality
- Use pytest as the testing framework
- Maintain test coverage above 80%

### Commands
- Create virtual environment: `python3 -m venv venv`
- Activate virtual environment: `source venv/bin/activate` (Unix/macOS) or `venv\Scripts\activate` (Windows)
- Install dependencies: `pip3 install -r requirements.txt`
- Run tests: `pytest`
- Lint code: `flake8`
- Run main scraper: `python3 trends_trending_now.py --geo="Country Name"`
- Run simple Chinese output: `python3 simple_trends.py "Country Name"`

### Important Notes
- Always use `python3` and `pip3` commands explicitly to ensure Python 3 is used
- The system may have both Python 2 and Python 3 installed, so explicit version is required

## Project Structure
```
google_trend_claude/
├── venv/                 # Virtual environment
├── src/                  # Source code
├── tests/                # Test files
├── data/                 # Data files
├── notebooks/            # Jupyter notebooks
├── requirements.txt      # Python dependencies
├── README.md            # Project documentation
└── CLAUDE.md            # This file
```