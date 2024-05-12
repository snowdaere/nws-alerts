# NWS-alerts
nws-alerts is an aggregator for National Weather Service alerts. It is a TUI application written in python and urwid.

# Installation
This application is linux only. To install, simply clone the repository and install the requirements:
```
git clone https://github.com/snowdaere/nws-alerts && cd nws-alerts
pip install -r requirements.txt
```

# Use
To run:
```
python3 main.py
```
Or you can make it executable with chmod and run it more compactly:
```
chmod +x main.py
./main.py
```

# Configuration
Configuration information can be found and changed by editing the variables in main.py. You can request certain types of alerts from certain
states, modify what is displayed, colors, and more.
