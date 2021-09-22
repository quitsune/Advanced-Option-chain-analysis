import requests
import json
import pandas as pd
import xlwings as xw
from time import sleep
from datetime import datetime, time , timedelta
import os
import numpy as np

pd.set_option('display.width',1500)
pd.set_option('display.max_columns',75)
pd.set_option('display.max_rows',1500)

url_oc = "https://www.nseindia.com/option-chain"
url = f"https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, '
                         'like Gecko) '
                         'Chrome/80.0.3987.149 Safari/537.36',
           'accept-language': 'en,gu;q=0.9,hi;q=0.8', 'accept-encoding': 'gzip, deflate, br'}


expiry = "26-Aug-2021"
excel_file ="Option_Chain_Analysis.xlsx"
wb = xw.Book(excel_file)
sheet_oi_single = wb.sheets("OIData")
sht_live=wb.sheets("Data")
df_list =[]
mp_list =[]
oi_filename = os.path.join("Files","oi_data_records_{0}.json".format(datetime.now().strftime("%d%m%y")))
mp_filename = os.path.join("Files","mp_data_records_{0}.json".format(datetime.now().strftime("%d%m%y")))

def fetch_oi(df,mp_df):
  
    tries = 1
    max_retries = 1
    while tries <= max_retries:
        try:
            
            session = requests.Session()
            request = session.get(url_oc, headers=headers, timeout=5)
            cookies = dict(request.cookies)
            response = session.get(url, headers=headers, timeout=5, cookies=cookies)
            data_json = response.json()
            r = data_json
            print("hello")
            if expiry:
                ce_values = [data['CE'] for data in r['records']['data']if 'CE' in data and str(data['expiryDate']).lower() == str(expiry).lower()]
                pe_values = [data['PE'] for data in r['records']['data']if 'PE' in data and str(data['expiryDate']).lower() == str(expiry).lower()]
        
            else:
                ce_values = [data['CE'] for data in r['filtered']['data']if 'CE' in data]
                pe_values = [data['PE'] for data in r['filtered']['data']if 'PE' in data]
            ce_data = pd.DataFrame(ce_values)
            pe_data = pd.DataFrame(pe_values)
            ce_data = ce_data.sort_values(['strikePrice'])
            pe_data = pe_data.sort_values(['strikePrice'])
            sheet_oi_single.range("A2").options(index=False,headers=False).value = ce_data.drop(columns=['underlying','identifier','bidQty','bidprice','askQty','askPrice','expiryDate','totalBuyQuantity','totalBuyQuantity','totalTradedVolume','underlyingValue'], axis=1)[['openInterest','changeinOpenInterest','pchangeinOpenInterest','impliedVolatility','lastPrice','change','pChange','strikePrice']]
            sheet_oi_single.range("I2").options(index=False,headers=False).value = pe_data.drop(columns=['strikePrice','underlying','identifier','bidQty','bidprice','askQty','askPrice','expiryDate','totalBuyQuantity','totalBuyQuantity','totalTradedVolume','underlyingValue'], axis=1,)[['openInterest','changeinOpenInterest','pchangeinOpenInterest','impliedVolatility','lastPrice','change','pChange']]
            ce_data['type'] = 'CE'
            pe_data['type'] = 'PE'
            df1 = pd.concat([ce_data,pe_data])
            if len(df_list) > 0 :
                df1['Time'] = df_list[-1][0]['Time']
            if len(df_list) > 0 and df1.to_dict('records')== df_list[-1]:
                print("Duplicate data. Not recording")
                sleep(10)
                tries +=1
                continue
            df1['Time'] = datetime.now().strftime("%H:%M")

            pcr = pe_data['totalTradedVolume'].sum()/ce_data['totalTradedVolume'].sum()
            mp_dict = {datetime.now().strftime("%H: %M"): {'underlying' :df1['underlyingValue'].iloc[-1],
                                                        'MaxPain': wb.sheets("Dashboard").range("H8").value,
                                                        'pcr'  : pcr,
                                                        'call_decay': ce_data['change'].mean(),
                                                        'put_decay': pe_data['change'].mean() }}
            
            df3 = pd.DataFrame(mp_dict).transpose()
            mp_df = pd.concat([mp_df,df3])
            with open(mp_filename, "w") as files:
                files.write(json.dumps(mp_df.to_dict(), indent =4,sort_keys= True))
            wb.sheets['MPData'].range("A2").options(header = False).value = mp_df

            if not df.empty:
                df = df[['strikePrice', 'expiryDate', 'underlying', 'identifier', 'openInterest', 'changeinOpenInterest',
                        'pchangeinOpenInterest','totalTradedVolume', 'impliedVolatility', 'lastPrice', 'change',
                        'pChange',
                        'totalBuyQuantity', 'totalSellQuantity', 'bidQty','bidprice','askQty', 'askPrice',
                        'underlyingValue', 'type', 
                        'Time']]
                df1 = df1[['strikePrice', 'expiryDate', 'underlying', 'identifier', 'openInterest', 'changeinOpenInterest',
                        'pchangeinOpenInterest','totalTradedVolume', 'impliedVolatility', 'lastPrice', 'change',
                        'pChange',
                        'totalBuyQuantity', 'totalSellQuantity', 'bidQty','bidprice','askQty', 'askPrice',
                        'underlyingValue', 'type', 
                        'Time']]
            df  = pd.concat([df,df1])
            df_list.append(df1.to_dict('records'))
            with open(oi_filename, "w") as files:
                files.write(json.dumps(df_list, indent =4,sort_keys= True))
            return df, mp_df

        except Exception as error:
            print("Error {0}".format(error))
            tries +=1
            sleep(10)
            continue
    if tries>= max_retries:
        print("Max Retries exceeded. No new Data at time {0}".format(datetime.now()))
        return df, mp_df

def main():
   global df_list
   try :
       df_list = json.loads(open(oi_filename).read())
   except Exception as error:
       print("Error reading data. Error: {0}".format(error))
       df_list =[]
   if df_list:
       df = pd.DataFrame()
       for item in df_list:
           df = pd.concat([df, pd.DataFrame(item)])
   else:
       df = pd.DataFrame()
    
   try :
       mp_list = json.loads(open(mp_filename).read())
       mp_df = pd.DataFrame().from_dict(mp_list)
   except Exception as error:
       print("Error reading data. Error: {0}".format(error))
       mp_list =[]
       mp_df = pd.DataFrame()

   timeframe = 1
   while time(9,15) <= datetime.now().time() <= time(20,30) :

        timenow = datetime.now()
        check = True if timenow.minute/timeframe in list(np.arange(0.0, 60.0)) else False
        if check :
            nextscan = timenow + timedelta(minutes = timeframe)
            df, mp_df = fetch_oi(df,mp_df)
            if not df.empty:
                df['impliedVolatility'] = df['impliedVolatility'].replace(to_replace = 0, method = 'bfill').values
                df['identifier'] = df['strikePrice'].astype(str) + df['type']
                sht_live.range("A1").value= df
                wb.api.RefreshAll()
                waitsecs = int ((nextscan- datetime.now()).seconds)
                print("Wait for {0} seconds".format(waitsecs))
                sleep(waitsecs) if waitsecs > 0 else sleep(0)
            else:
                print("No data received")
                sleep(30)


if __name__ ==" __main__" :
   main()
   
main()