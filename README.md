# Algorithmic Trading with Python
This is a repository of simple trading strategies I've implemented in Python. The main branch has the executable scripts and the Jupiter branch
has the Jupiter notebooks I used to make these scripts. These scripts are dependent on the IEX Cloud Stock API.

# How to Use
1. clone the repository and cd into it
2. create the virtual environment with ```python -m venv venv```
3. install dependencies with ```pip install -r requirements.txt ```. If the 'pip' command does not work, you may have to use 'pip3' instead
4. Create an IEX Cloud account and start a free trial (https://iexcloud.io/)
5. Get an API key and copy that key into the "secrets.py" file
6. run the scripts ```python [scriptName]``` or ```python3 [scriptName]```

After following these steps, you should have an Excel File with the outpute of whatever script you ran.
