#!/usr/bin/env python
# coding: utf-8

# # Quantitative Momentum Strategy
# 
# "Momentum investing" means investing in the stocks that have increased in price the most.
# 
# For this project, we're going to build an investing strategy that selects the 50 stocks with the highest price momentum. From there, we will calculate recommended trades for an equal-weight portfolio of these 50 stocks.
# 
# 
# ## Library Imports
# 
# The first thing we need to do is import the open-source software libraries that we'll be using

# In[88]:


import numpy as np
import pandas as pd
import requests
import math
from scipy import stats
import xlsxwriter
import time


# ## Importing Our List of Stocks
# 
# As before, we'll need to import our list of stocks and our API token before proceeding. 

# In[89]:


stocks = pd.read_csv('constituents.csv')
from secret import IEX_CLOUD_API_TOKEN


# ## Making Our First API Call
# 
# It's now time to make the first version of our momentum screener!
# 
# We need to get one-year price returns for each stock in the universe. Here's how.

# In[12]:


symbol = "AAPL"
api_url = f'https://api.iex.cloud/v1/data/core/advanced_stats/{symbol}?token={IEX_CLOUD_API_TOKEN}'
data = requests.get(api_url).json()[0]


# ## Parsing Our API Call
# 
# This API call has all the information we need. We can parse it using the same square-bracket notation as in the first project of this course. Here is an example.

# In[13]:


data['year1ChangePercent']


# ## Executing A Batch API Call & Building Our DataFrame
# 
# Just like in our first project, it's now time to execute several batch API calls and add the information we need to our DataFrame.
# 
# We'll start by running the following code cell, which contains some code we already built last time that we can re-use for this project. More specifically, it contains a function called `chunks` that we can use to divide our list of securities into groups of 100.

# In[14]:


# Function sourced from 
# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]   
        
symbol_groups = list(chunks(stocks['Ticker'], 100))
symbol_strings = []
for i in range(0, len(symbol_groups)):
    symbol_strings.append(','.join(symbol_groups[i]))
#     print(symbol_strings[i])

my_columns = ['Ticker', 'Price', 'One-Year Price Return', 'Number of Shares to Buy']


# Now we need to create a blank DataFrame and add our data to the data frame one-by-one.

# In[24]:


dataframe = pd.DataFrame(columns = my_columns)

for symbol_string in symbol_strings:
    url = f'https://api.iex.cloud/v1/data/core/advanced_stats/{symbol_string}?token={IEX_CLOUD_API_TOKEN}'
    quoteUrl = f'https://api.iex.cloud/v1/data/core/quote/{symbol_string}?token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(url).json()
    quoteData = requests.get(quoteUrl).json()
    symbols = symbol_string.split(',')
    for i in range(len(symbols)):
        name = symbols[i]
        price = quoteData[i]['latestPrice']
        oneYearChange = data[i]['year1ChangePercent']
        row = pd.DataFrame([[name, price, oneYearChange, 'N/A']], columns=my_columns)
        dataframe = pd.concat([dataframe, row], axis=0, ignore_index=True)
    time.sleep(0.4)



# ## Removing Low-Momentum Stocks
# 
# The investment strategy that we're building seeks to identify the 50 highest-momentum stocks in the S&P 500.
# 
# Because of this, the next thing we need to do is remove all the stocks in our DataFrame that fall below this momentum threshold. We'll sort the DataFrame by the stocks' one-year price return, and drop all stocks outside the top 50.
# 

# In[28]:


dataframe.sort_values('One-Year Price Return', ascending = False, inplace=True)
dataframe = dataframe[:50]
dataframe.reset_index(inplace=True)


# ## Calculating the Number of Shares to Buy
# 
# Just like in the last project, we now need to calculate the number of shares we need to buy. The one change we're going to make is wrapping this functionality inside a function, since we'll be using it again later in this Jupyter Notebook.
# 
# Since we've already done most of the work on this, try to complete the following two code cells without watching me do it first!

# In[32]:


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

portfolioSize = getPortfolioSize()
positionSize = portfolioSize/len(dataframe.index)


# In[33]:


for i in range(len(dataframe)):
    dataframe.loc[i, "Number of Shares to Buy"] = math.floor(positionSize/dataframe.loc[i, 'Price'])



# ## Building a Better (and More Realistic) Momentum Strategy
# 
# Real-world quantitative investment firms differentiate between "high quality" and "low quality" momentum stocks:
# 
# * High-quality momentum stocks show "slow and steady" outperformance over long periods of time
# * Low-quality momentum stocks might not show any momentum for a long time, and then surge upwards.
# 
# The reason why high-quality momentum stocks are preferred is because low-quality momentum can often be cause by short-term news that is unlikely to be repeated in the future (such as an FDA approval for a biotechnology company).
# 
# To identify high-quality momentum, we're going to build a strategy that selects stocks from the highest percentiles of: 
# 
# * 1-month price returns
# * 3-month price returns
# * 6-month price returns
# * 1-year price returns
# 
# Let's start by building our DataFrame. You'll notice that I use the abbreviation `hqm` often. It stands for `high-quality momentum`.

# In[131]:


hqmColumns = [
    'Ticker',
    'Price',
    'Number of Shares to Buy',
    'One-Year Price Return',
    'One-Year Return Percentile',
    'Six-Month Price Return',
    'Six-Month Return Percentile',
    'Three-Month Price Return',
    'Three-Month Return Percentile',
    'One-Month Price Return',
    'One-Month Return Percentile',
    'HQM Score'
]
hqmDataframe = pd.DataFrame(columns=hqmColumns)

for symbol_string in symbol_strings:
    url = f'https://api.iex.cloud/v1/data/core/advanced_stats/{symbol_string}?token={IEX_CLOUD_API_TOKEN}'
    quoteUrl = f'https://api.iex.cloud/v1/data/core/quote/{symbol_string}?token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(url).json()
    quoteData = requests.get(quoteUrl).json()
    symbols = symbol_string.split(',')
    for i in range(len(symbols)):
        name = symbols[i]
        price = quoteData[i]['latestPrice']
        oneYearChange = data[i]['year1ChangePercent']
        sixMonthChange = data[i]['month6ChangePercent']
        threeMonthChange = data[i]['month3ChangePercent']
        oneMonthChange = data[i]['month1ChangePercent']
        row = pd.DataFrame([[name, price, 'N/A', oneYearChange, 'N/A', sixMonthChange, 'N/A', threeMonthChange, 'N/A', oneMonthChange, 'N/A', 'N/A']], columns=hqmColumns)
        hqmDataframe = pd.concat([hqmDataframe, row], axis=0, ignore_index=True)
    time.sleep(0.4)


# ## Calculating Momentum Percentiles
# 
# We now need to calculate momentum percentile scores for every stock in the universe. More specifically, we need to calculate percentile scores for the following metrics for every stock:
# 
# * `One-Year Price Return`
# * `Six-Month Price Return`
# * `Three-Month Price Return`
# * `One-Month Price Return`
# 
# Here's how we'll do this:

# In[132]:


timePeriods = ['One-Year', 'Six-Month', 'Three-Month', 'One-Month']

for row in hqmDataframe.index:
    for period in timePeriods:
        columnString = f'{period} Price Return'
        percentile = stats.percentileofscore(hqmDataframe[columnString][~np.isnan(hqmDataframe[columnString])], hqmDataframe.loc[row, columnString])/100
        hqmDataframe.loc[row, f'{period} Return Percentile'] = percentile



# ## Calculating the HQM Score
# 
# We'll now calculate our `HQM Score`, which is the high-quality momentum score that we'll use to filter for stocks in this investing strategy.
# 
# The `HQM Score` will be the arithmetic mean of the 4 momentum percentile scores that we calculated in the last section.
# 
# To calculate arithmetic mean, we will use the `mean` function from Python's built-in `statistics` module.

# In[133]:


from statistics import mean

for row in hqmDataframe.index:
    momentumPercentiles = []
    for period in timePeriods:
        momentumPercentiles.append(hqmDataframe.loc[row, f'{period} Return Percentile'])
    hqmDataframe.loc[row, "HQM Score"] = mean(momentumPercentiles)
    


# ## Selecting the 50 Best Momentum Stocks
# 
# As before, we can identify the 50 best momentum stocks in our universe by sorting the DataFrame on the `HQM Score` column and dropping all but the top 50 entries.

# In[134]:


hqmDataframe.sort_values("HQM Score", ascending=False, inplace=True)
hqmDataframe = hqmDataframe[:50]


# ## Calculating the Number of Shares to Buy
# 
# We'll use the `portfolio_input` function that we created earlier to accept our portfolio size. Then we will use similar logic in a `for` loop to calculate the number of shares to buy for each stock in our investment universe.

# In[94]:


portfolioSize = getPortfolioSize()


# In[135]:


positionSize = portfolioSize/len(hqmDataframe.index)
for i in hqmDataframe.index:
    hqmDataframe.loc[i, "Number of Shares to Buy"] = math.floor(positionSize/hqmDataframe.loc[i, "Price"])



# ## Formatting Our Excel Output
# 
# We will be using the XlsxWriter library for Python to create nicely-formatted Excel files.
# 
# XlsxWriter is an excellent package and offers tons of customization. However, the tradeoff for this is that the library can seem very complicated to new users. Accordingly, this section will be fairly long because I want to do a good job of explaining how XlsxWriter works.

# In[136]:


writer = pd.ExcelWriter('momentum_strategy.xlsx', engine='xlsxwriter')
hqmDataframe.to_excel(writer, "Momentum Strategy", index=False)


# ## Creating the Formats We'll Need For Our .xlsx File
# 
# You'll recall from our first project that formats include colors, fonts, and also symbols like % and $. We'll need four main formats for our Excel document:
# 
# * String format for tickers
# * \$XX.XX format for stock prices
# * \$XX,XXX format for market capitalization
# * Integer format for the number of shares to purchase
# 
# Since we already built our formats in the last section of this course, I've included them below for you. Run this code cell before proceeding.

# In[137]:


background_color = '#0a0a23'
font_color = '#ffffff'

string_template = writer.book.add_format(
        {
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

dollar_template = writer.book.add_format(
        {
            'num_format':'$0.00',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

integer_template = writer.book.add_format(
        {
            'num_format':'0',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

percent_template = writer.book.add_format(
        {
            'num_format':'0.0%',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )


# In[139]:


columnFormats = {
    'A': ['Ticker', string_template],
    'B': ['Price', dollar_template],
    'C': ['Number of Shares to Buy', integer_template],
    'D': ['One-Year Price Return', percent_template],
    'E': ['One-Year Return Percentile', percent_template],
    'F': ['Six-Month Price Return', percent_template],
    'G': ['Six-Month Return Percentile', percent_template],
    'H': ['Three-Month Price Return', percent_template],
    'I': ['Three-Month Return Percentile', percent_template],
    'J': ['One-Month Price Return', percent_template],
    'K': ['One-Month Return Percentile', percent_template],
    'L': ['HQM Score', percent_template]
}

for column in columnFormats.keys():
    writer.sheets["Momentum Strategy"].set_column( f"{column}:{column}", 25, columnFormats[column][1])
    writer.sheets["Momentum Strategy"].write(f"{column}1", columnFormats[column][0], columnFormats[column][1])


# ## Saving Our Excel Output
# 
# As before, saving our Excel output is very easy:

# In[140]:


writer.close()


# In[ ]:




