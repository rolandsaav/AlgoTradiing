#!/usr/bin/env python
# coding: utf-8

# # Quantitative Value Strategy
# "Value investing" means investing in the stocks that are cheapest relative to common measures of business value (like earnings or assets).
# 
# For this project, we're going to build an investing strategy that selects the 50 stocks with the best value metrics. From there, we will calculate recommended trades for an equal-weight portfolio of these 50 stocks.
# 
# ## Library Imports
# The first thing we need to do is import the open-source software libraries that we'll be using in this tutorial.

# In[1]:


import numpy as np
import pandas as pd
import xlsxwriter
import requests
from scipy import stats
import math


# ## Importing Our List of Stocks & API Token
# As before, we'll need to import our list of stocks and our API token before proceeding. Make sure the .csv file is still in your working directory and import it with the following command:

# In[2]:


stocks = pd.read_csv('constituents.csv')


# ## Making Our First API Call
# It's now time to make the first version of our value screener!
# 
# We'll start by building a simple value screener that ranks securities based on a single metric (the price-to-earnings ratio).

# In[4]:


from secret import IEX_CLOUD_API_TOKEN
symbol = 'AAPL'
api_url = f'https://api.iex.cloud/v1/data/core/quote/{symbol}?token={IEX_CLOUD_API_TOKEN}'
data = requests.get(api_url).json()[0]


# ## Parsing Our API Call
# This API call has the metric we need - the price-to-earnings ratio.
# 
# Here is an example of how to parse the metric from our API call:

# In[5]:


ratio = data['peRatio']


# ## Executing A Batch API Call & Building Our DataFrame
# 
# Just like in our first project, it's now time to execute several batch API calls and add the information we need to our DataFrame.
# 
# We'll start by running the following code cell, which contains some code we already built last time that we can re-use for this project. More specifically, it contains a function called chunks that we can use to divide our list of securities into groups of 100.

# In[6]:


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

my_columns = ['Ticker', 'Price', 'Price-to-Earnings Ratio', 'Number of Shares to Buy']


# Now we need to create a blank DataFrame and add our data to the data frame one-by-one.

# In[27]:


dataframe = pd.DataFrame(columns=my_columns)
import time

for symbol_string in symbol_strings:
    batch_api_call_url = f'https://api.iex.cloud/v1/data/core/quote/{symbol_string}?token={IEX_CLOUD_API_TOKEN}'
    response = requests.get(batch_api_call_url)
    if (response.status_code != 200):
        print("Problem")
        break
    data = response.json()
    symbols = symbol_string.split(',')
    for i in range(len(symbols)):
        symbol = symbols[i]
        price = data[i]['latestPrice']
        peRatio = data[i]['peRatio']
        row = pd.DataFrame([[symbol, price, peRatio, 'N/A']],columns=my_columns)
        dataframe = pd.concat([dataframe, row], axis=0, ignore_index=True)
    time.sleep(0.2)
print('done')    
        
    


# ## Removing Glamour Stocks
# 
# The opposite of a "value stock" is a "glamour stock". 
# 
# Since the goal of this strategy is to identify the 50 best value stocks from our universe, our next step is to remove glamour stocks from the DataFrame.
# 
# We'll sort the DataFrame by the stocks' price-to-earnings ratio, and drop all stocks outside the top 50.

# In[28]:


dataframe.sort_values(ascending=True, by="Price-to-Earnings Ratio", inplace=True)
dataframe = dataframe[dataframe['Price-to-Earnings Ratio'] > 0]
dataframe.reset_index(inplace=True)
dataframe = dataframe[:50]
len(dataframe) 


# ## Calculating the Number of Shares to Buy
# We now need to calculate the number of shares we need to buy. 
# 
# To do this, we will use the `portfolio_input` function that we created in our momentum project.
# 
# I have included this function below.

# In[18]:


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


# Use the `portfolio_input` function to accept a `portfolio_size` variable from the user of this script.

# In[9]:





# You can now use the global `portfolio_size` variable to calculate the number of shares that our strategy should purchase.

# In[29]:


for row in dataframe.index:
    dataframe.loc[row, 'Number of Shares to Buy'] = math.floor(positionSize/dataframe.loc[row, 'Price'])



# ## Building a Better (and More Realistic) Value Strategy
# Every valuation metric has certain flaws.
# 
# For example, the price-to-earnings ratio doesn't work well with stocks with negative earnings.
# 
# Similarly, stocks that buyback their own shares are difficult to value using the price-to-book ratio.
# 
# Investors typically use a `composite` basket of valuation metrics to build robust quantitative value strategies. In this section, we will filter for stocks with the lowest percentiles on the following metrics:
# 
# * Price-to-earnings ratio
# * Price-to-book ratio
# * Price-to-sales ratio
# * Enterprise Value divided by Earnings Before Interest, Taxes, Depreciation, and Amortization (EV/EBITDA)
# * Enterprise Value divided by Gross Profit (EV/GP)
# 
# Some of these metrics aren't provided directly by the IEX Cloud API, and must be computed after pulling raw data. We'll start by calculating each data point from scratch.

# In[36]:


symbol = "AAPL"
quoteUrl = f"https://api.iex.cloud/v1/data/CORE/QUOTE/{symbol}?token={IEX_CLOUD_API_TOKEN}"
statsUrl = f"https://api.iex.cloud/v1/data/CORE/ADVANCED_STATS/{symbol}?token={IEX_CLOUD_API_TOKEN}"

quoteResponse = requests.get(quoteUrl)
statsResponse = requests.get(statsUrl)

if (quoteResponse.status_code != 200 or statsResponse.status_code != 200):
    print("Fail")

quoteData = quoteResponse.json()[0]
statsData = statsResponse.json()[0]

peRatio = quoteData['peRatio']
pbRatio = statsData['priceToBook']
psRatio = statsData['priceToSales']
enterpriseValue = statsData['enterpriseValue']
EBITDA = statsData['EBITDA']

evebitda = enterpriseValue/EBITDA

grossProfit = statsData['grossProfit']
evgp = enterpriseValue/grossProfit

print(peRatio)
print(pbRatio)
print(psRatio)
print(enterpriseValue)
print(EBITDA)
print(evebitda)
print(grossProfit)
print(evgp)


# Let's move on to building our DataFrame. You'll notice that I use the abbreviation `rv` often. It stands for `robust value`, which is what we'll call this sophisticated strategy moving forward.

# In[60]:


rv_columns = [
    'Ticker', 
    'Price', 
    'Number of Shares to Buy', 
    'Price-to-Earnings Ratio', 
    'PE Percentile', 
    'Price-to-Book Ratio', 
    'PB Percentile',
    'Price-to-Sales Ratio',
    'PS Percentile',
    'EV/EBITDA',
    'EV/EBITDA Percentile',
    'EV/GP',
    'EV/GP Percentile',
    'RV Score'
]

rvdf = pd.DataFrame(columns=rv_columns)


# In[61]:


for symbol_string in symbol_strings:
    quoteUrl = f"https://api.iex.cloud/v1/data/CORE/QUOTE/{symbol_string}?token={IEX_CLOUD_API_TOKEN}"
    statsUrl = f"https://api.iex.cloud/v1/data/CORE/ADVANCED_STATS/{symbol_string}?token={IEX_CLOUD_API_TOKEN}"
    
    quoteResponse = requests.get(quoteUrl)
    statsResponse = requests.get(statsUrl)
    
    if (quoteResponse.status_code != 200 or statsResponse.status_code != 200):
        print("Fail")
    
    quoteData = quoteResponse.json()
    statsData = statsResponse.json()
    symbols = symbol_string.split(',')
    for i in range(len(symbols)):
        if(len(quoteData[i]) == 0 or len(statsData[i]) == 0):
            continue
        symbol = symbols[i]   
        price = quoteData[i]['latestPrice']
        peRatio = quoteData[i]['peRatio']
        pbRatio = statsData[i]['priceToBook']
        psRatio = statsData[i]['priceToSales']
        enterpriseValue = statsData[i]['enterpriseValue']
        EBITDA = statsData[i]['EBITDA']

        evebitda = np.NaN
        if (enterpriseValue != None and EBITDA != None):
            evebitda = enterpriseValue/EBITDA
        else:
            print(f"Cannot calculate EV/EBITDA for {symbol}")
        
        grossProfit = statsData[i]['grossProfit']
        evgp = np.NaN
        if (grossProfit != None and enterpriseValue != None):
            evgp = enterpriseValue/grossProfit
        else:
            print(f"Cannot calculate EV/GP for {symbol}")
        row = pd.DataFrame([[symbol, price, 'N/A', peRatio, 'N/A', pbRatio, 'N/A', psRatio, 'N/A', evebitda, 'N/A', evgp, 'N/A', 'N/A']],columns=rv_columns)
        rvdf = pd.concat([rvdf, row], axis=0, ignore_index=True)
    time.sleep(0.4)
print('done')    


# ## Dealing With Missing Data in Our DataFrame
# 
# Our DataFrame contains some missing data because all of the metrics we require are not available through the API we're using. 
# 
# You can use pandas' `isnull` method to identify missing data:

# In[62]:




# Dealing with missing data is an important topic in data science.
# 
# There are two main approaches:
# 
# * Drop missing data from the data set (pandas' `dropna` method is useful here)
# * Replace missing data with a new value (pandas' `fillna` method is useful here)
# 
# In this tutorial, we will replace missing data with the average non-`NaN` data point from that column. 
# 
# Here is the code to do this:

# In[68]:


rvdf[rvdf.isnull().any(axis=1)]


# Now, if we run the statement from earlier to print rows that contain missing data, nothing should be returned:

# In[67]:


for column in ['Price-to-Earnings Ratio', 'Price-to-Book Ratio', 'Price-to-Sales Ratio', 'EV/EBITDA', 'EV/GP']:
    rvdf[column].fillna(rvdf[column].mean(), inplace=True)


# ## Calculating Value Percentiles
# 
# We now need to calculate value score percentiles for every stock in the universe. More specifically, we need to calculate percentile scores for the following metrics for every stock:
# 
# * Price-to-earnings ratio
# * Price-to-book ratio
# * Price-to-sales ratio
# * EV/EBITDA
# * EV/GP
# 
# Here's how we'll do this:

# In[72]:


metrics = {
    'Price-to-Earnings Ratio':'PE Percentile', 
    'Price-to-Book Ratio': 'PB Percentile',
    'Price-to-Sales Ratio': 'PS Percentile',
    'EV/EBITDA': 'EV/EBITDA Percentile',
    'EV/GP': 'EV/GP Percentile'
}
for metric in metrics.keys():
    for row in rvdf.index:
        value = rvdf.loc[row, metric]
        rvdf.loc[row, metrics[metric]] = stats.percentileofscore( rvdf[metric], value)/100



# ## Calculating the RV Score
# We'll now calculate our RV Score (which stands for Robust Value), which is the value score that we'll use to filter for stocks in this investing strategy.
# 
# The RV Score will be the arithmetic mean of the 4 percentile scores that we calculated in the last section.
# 
# To calculate arithmetic mean, we will use the mean function from Python's built-in statistics module.

# In[75]:


from statistics import mean

for row in rvdf.index:
    values = []
    for metric in metrics.keys():
        values.append(rvdf.loc[row, metrics[metric]])
    rvdf.loc[row, "RV Score"] = mean(values)



# ## Selecting the 50 Best Value Stocks¶
# 
# As before, we can identify the 50 best value stocks in our universe by sorting the DataFrame on the RV Score column and dropping all but the top 50 entries.

# In[79]:


rvdf.sort_values('RV Score', ascending = False, inplace=True)
rvdf = rvdf[:50]
rvdf.reset_index(drop = True, inplace = True)


# ## Calculating the Number of Shares to Buy
# We'll use the `portfolio_input` function that we created earlier to accept our portfolio size. Then we will use similar logic in a for loop to calculate the number of shares to buy for each stock in our investment universe.

# In[83]:


portfolioSize = getPortfolioSize()
positionSize = portfolioSize/len(rvdf.index)


# In[85]:


for row in rvdf.index:
    rvdf.loc[row, 'Number of Shares to Buy'] = math.floor(positionSize/rvdf.loc[row, 'Price'])


# ## Formatting Our Excel Output
# 
# We will be using the XlsxWriter library for Python to create nicely-formatted Excel files.
# 
# XlsxWriter is an excellent package and offers tons of customization. However, the tradeoff for this is that the library can seem very complicated to new users. Accordingly, this section will be fairly long because I want to do a good job of explaining how XlsxWriter works.

# In[87]:


writer = pd.ExcelWriter('value_strategy.xlsx', engine='xlsxwriter')
rvdf.to_excel(writer, sheet_name='Value Strategy', index = False)


# ## Creating the Formats We'll Need For Our .xlsx File
# You'll recall from our first project that formats include colors, fonts, and also symbols like % and $. We'll need four main formats for our Excel document:
# 
# * String format for tickers
# * \$XX.XX format for stock prices
# * \$XX,XXX format for market capitalization
# * Integer format for the number of shares to purchase
# * Float formats with 1 decimal for each valuation metric
# 
# Since we already built some formats in past sections of this course, I've included them below for you. Run this code cell before proceeding.

# In[88]:


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

float_template = writer.book.add_format(
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


# In[89]:


column_formats = {
                    'A': ['Ticker', string_template],
                    'B': ['Price', dollar_template],
                    'C': ['Number of Shares to Buy', integer_template],
                    'D': ['Price-to-Earnings Ratio', float_template],
                    'E': ['PE Percentile', percent_template],
                    'F': ['Price-to-Book Ratio', float_template],
                    'G': ['PB Percentile',percent_template],
                    'H': ['Price-to-Sales Ratio', float_template],
                    'I': ['PS Percentile', percent_template],
                    'J': ['EV/EBITDA', float_template],
                    'K': ['EV/EBITDA Percentile', percent_template],
                    'L': ['EV/GP', float_template],
                    'M': ['EV/GP Percentile', percent_template],
                    'N': ['RV Score', percent_template]
                 }

for column in column_formats.keys():
    writer.sheets['Value Strategy'].set_column(f'{column}:{column}', 25, column_formats[column][1])
    writer.sheets['Value Strategy'].write(f'{column}1', column_formats[column][0], column_formats[column][1])


# ## Saving Our Excel Output
# As before, saving our Excel output is very easy:

# In[90]:


writer.close()

