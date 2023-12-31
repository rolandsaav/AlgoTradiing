#!/usr/bin/env python
# coding: utf-8

# # Equal-Weight S&P 500 Index Fund
# 
# ## Introduction & Library Imports
# 
# The S&P 500 is the world's most popular stock market index. The largest fund that is benchmarked to this index is the SPDR® S&P 500® ETF Trust. It has more than US$250 billion of assets under management.
# 
# The goal of this section of the course is to create a Python script that will accept the value of your portfolio and tell you how many shares of each S&P 500 constituent you should purchase to get an equal-weight version of the index fund.
# 
# ## Library Imports
# 
# The first thing we need to do is import the open-source software libraries that we'll be using in this tutorial.

# In[1]:


import requests
import xlsxwriter
import math
import numpy as np
import pandas as pd
import time


# ## Importing Our List of Stocks
# 
# The next thing we need to do is import the constituents of the S&P 500.
# 
# These constituents change over time, so in an ideal world you would connect directly to the index provider (Standard & Poor's) and pull their real-time constituents on a regular basis.
# 
# Paying for access to the index provider's API is outside of the scope of this course. 
# 
# There's a static version of the S&P 500 constituents available here. [Click this link to download them now](https://drive.google.com/file/d/1ZJSpbY69DVckVZlO9cC6KkgfSufybcHN/view?usp=sharing). Move this file into the `starter-files` folder so it can be accessed by other files in that directory.
# 
# Now it's time to import these stocks to our Jupyter Notebook file.

# In[2]:


stocks = pd.read_csv('constituents.csv')


# ## Acquiring an API Token
# 
# Now it's time to import our IEX Cloud API token. This is the data provider that we will be using throughout this course.
# 
# API tokens (and other sensitive information) should be stored in a `secrets.py` file that doesn't get pushed to your local Git repository. We'll be using a sandbox API token in this course, which means that the data we'll use is randomly-generated and (more importantly) has no cost associated with it.
# 
# [Click here](http://nickmccullum.com/algorithmic-trading-python/secrets.py) to download your `secrets.py` file. Move the file into the same directory as this Jupyter Notebook before proceeding.

# In[3]:


from secret import IEX_CLOUD_API_TOKEN


# ## Making Our First API Call
# 
# Now it's time to structure our API calls to IEX cloud. 
# 
# We need the following information from the API:
# 
# * Market capitalization for each stock
# * Price of each stock
# 
# 

# In[4]:


symbol = 'AAPL'
api_url = f'https://api.iex.cloud/v1/data/core/quote/{symbol}?token={IEX_CLOUD_API_TOKEN}'
data = requests.get(api_url).json()[0]


# ## Parsing Our API Call
# 
# The API call that we executed in the last code block contains all of the information required to build our equal-weight S&P 500 strategy. 
# 
# With that said, the data isn't in a proper format yet. We need to parse it first.

# In[5]:


price = data['latestPrice']
market_cap = data['marketCap']


# ## Adding Our Stocks Data to a Pandas DataFrame
# 
# The next thing we need to do is add our stock's price and market capitalization to a pandas DataFrame. Think of a DataFrame like the Python version of a spreadsheet. It stores tabular data.

# In[6]:


my_columns = [ 'Ticker', 'Stock Price', 'Market Capitalization', 'Number of Shares to Buy']
final_dataframe = pd.DataFrame(columns = my_columns)
row = [symbol, price, market_cap, 0]
series = pd.Series(row , index=my_columns)
final_dataframe = pd.concat([final_dataframe, series.to_frame().T])



# In[7]:


testDf = pd.DataFrame([[0, 1, 2, 3]], columns=my_columns)
newDf = pd.DataFrame([[10, 12, 14, 15]], columns=my_columns)
newDf = pd.concat([testDf, newDf], axis=0, ignore_index=True)
newDf


# ## Looping Through The Tickers in Our List of Stocks
# 
# Using the same logic that we outlined above, we can pull data for all S&P 500 stocks and store their data in the DataFrame using a `for` loop.

# In[8]:


final_df = pd.DataFrame(columns = my_columns)
for stock in stocks['Ticker'][:10]:
    api_url = f'https://api.iex.cloud/v1/data/core/quote/{stock}?token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(api_url)
    if (data.status_code != 200):
        print(f"problem: status code: {data.status_code}")
        continue
    data = data.json()[0]
    price = data['latestPrice']
    market_cap = data['marketCap']
    newDf = pd.DataFrame([[stock, price, market_cap, 0]], columns=my_columns)
    final_df = pd.concat([final_df, newDf], axis=0, ignore_index=True)
    time.sleep(0.3)
    print(f"{stock} done")
print("done")


# In[64]:


final_df


# ## Using Batch API Calls to Improve Performance
# 
# Batch API calls are one of the easiest ways to improve the performance of your code.
# 
# This is because HTTP requests are typically one of the slowest components of a script.
# 
# Also, API providers will often give you discounted rates for using batch API calls since they are easier for the API provider to respond to.
# 
# IEX Cloud limits their batch API calls to 100 tickers per request. Still, this reduces the number of API calls we'll make in this section from 500 to 5 - huge improvement! In this section, we'll split our list of stocks into groups of 100 and then make a batch API call for each group.

# In[9]:


def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


# In[10]:


symbol_groups = list(chunks(stocks['Ticker'], 100))
symbol_strings = []
for i in range(0, len(symbol_groups)):
    symbol_strings.append(','.join(symbol_groups[i]))
    # print(symbol_strings[i])
final_df = pd.DataFrame(columns=my_columns)

for symbol_string in symbol_strings:
    batch_api_call_url = f'https://api.iex.cloud/v1/data/core/quote/{symbol_string}?token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    symbols = symbol_string.split(',')
    for i in range(len(symbols)):
        ticker = symbols[i]
        price = data[i]['latestPrice']
        market_cap = data[i]['marketCap']
        newDf = pd.DataFrame([[ticker, price, market_cap, 0]], columns=my_columns)
        final_df = pd.concat([final_df, newDf], axis=0, ignore_index=True)
    time.sleep(0.3)
        
final_df


# ## Calculating the Number of Shares to Buy
# 
# As you can see in the DataFrame above, we stil haven't calculated the number of shares of each stock to buy.
# 
# We'll do that next.

# In[3]:


class CheapPortfolioException(Exception):
    pass

def getPortfolioSize():
    val = 0
    while True:
        val = input("Enter the value of your portfolio: ")
        try:
            val = float(val)
            if val <= 0:
                raise CheapPortfolioException("That value is too small")
            return val
        except ValueError:
            print("That was not a number")
        except CheapPortfolioException:
            print("That number was too small")



# In[4]:


portfolio_value = getPortfolioSize()


# In[12]:


position_size = portfolio_value/len(final_df.index)

for i in range(0, len(final_df.index)):
    price = final_df.loc[i, 'Stock Price']
    shares = math.floor(position_size/price)
    final_df.loc[i, 'Number of Shares to Buy'] = shares
final_df


# ## Formatting Our Excel Output
# 
# We will be using the XlsxWriter library for Python to create nicely-formatted Excel files.
# 
# XlsxWriter is an excellent package and offers tons of customization. However, the tradeoff for this is that the library can seem very complicated to new users. Accordingly, this section will be fairly long because I want to do a good job of explaining how XlsxWriter works.
# 
# ### Initializing our XlsxWriter Object

# In[13]:


writer = pd.ExcelWriter('recommended trades.xlsx', engine= 'xlsxwriter')
final_df.to_excel(writer, 'Recommended Trades', index=False)


# ### Creating the Formats We'll Need For Our `.xlsx` File
# 
# Formats include colors, fonts, and also symbols like `%` and `$`. We'll need four main formats for our Excel document:
# * String format for tickers
# * \\$XX.XX format for stock prices
# * \\$XX,XXX format for market capitalization
# * Integer format for the number of shares to purchase

# In[14]:


background_color = "#0a0a23"
font_color = "#ffffff"

string_format = writer.book.add_format(
    {
        'font_color': font_color,
        'bg_color': background_color,
        'border': 1
    }
)

dollar_format = writer.book.add_format(
    {
        'font_color': font_color,
        'bg_color': background_color,
        'border': 1,
        'num_format': '$0.00'
    }
)

integer_format= writer.book.add_format(
    {
        'font_color': font_color,
        'bg_color': background_color,
        'border': 1,
        'num_format': 0
    }
)


# ### Applying the Formats to the Columns of Our `.xlsx` File
# 
# We can use the `set_column` method applied to the `writer.sheets['Recommended Trades']` object to apply formats to specific columns of our spreadsheets.
# 
# Here's an example:
# 
# ```python
# writer.sheets['Recommended Trades'].set_column('B:B', #This tells the method to apply the format to column B
#                      18, #This tells the method to apply a column width of 18 pixels
#                      string_template #This applies the format 'string_template' to the column
#                     )
# ```

# In[15]:


writer.sheets['Recommended Trades'].write('A1', 'Ticker', string_format)
writer.sheets['Recommended Trades'].write('B1', 'Stock Price', dollar_format)
writer.sheets['Recommended Trades'].write('C1', 'Market Capitalization', dollar_format)
writer.sheets['Recommended Trades'].write('D1', 'Number of Shares to Buy', integer_format)


# This code works, but it violates the software principle of "Don't Repeat Yourself". 
# 
# Let's simplify this by putting it in 2 loops:

# In[16]:


column_formats = {
    'A': ['Ticker', string_format],
    'B': ['Stock Price', dollar_format],
    'C': ['Market Capitalization', dollar_format],
    'D': ['Number of Shares to Buy', integer_format]
}
for column in column_formats.keys():
    writer.sheets['Recommended Trades'].set_column(f'{column}:{column}', 18, column_formats[column][1])



# ## Saving Our Excel Output
# 
# Saving our Excel file is very easy:

# In[17]:


writer.close()


# In[ ]:




