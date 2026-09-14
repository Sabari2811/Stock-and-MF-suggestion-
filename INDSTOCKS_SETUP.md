# INDstocks / INDmoney market-data setup

Do not put an access token in GitHub, source files, screenshots, or Streamlit code. The application reads it from the local `INDSTOCKS_TOKEN` environment variable.

## Windows PowerShell

For the current terminal session:

```powershell
$env:INDSTOCKS_TOKEN = "PASTE_YOUR_NEW_TOKEN_HERE"
streamlit run streamlit_app.py
```

The dashboard will automatically use the INDstocks provider when `INDSTOCKS_TOKEN` is present. Without it, the dashboard falls back to Yahoo Finance research data.

INDstocks market data uses the access token in the `Authorization` header. The application resolves NSE/BSE equity symbols through the INDstocks instruments master and requests historical OHLCV from the INDstocks historical-data API.
