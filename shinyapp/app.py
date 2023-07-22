import sqlite3
import pandas as pd
from pathlib import Path
from shiny import App, render, ui, reactive
from htmltools import css
from matplotlib import pyplot as plt
import seaborn as sns


### Create DB ##########################################################

conn = sqlite3.connect('Portfolio_Tracker72')
c = conn.cursor()
infile = Path(__file__).parent / "Stocks_Dataset.csv"
df = pd.read_csv(infile)
df.to_sql('stock_data_raw',conn,if_exists='replace',index=False)

## Stock
c.execute('''create table stock (
  ID integer primary key autoincrement not null,
  tickersymbol varchar(10),
  companyname varchar(100)
)''')
c.execute('''insert into stock (tickersymbol,companyname)
select distinct symbol,company from stock_data_raw
''')
# colnames=[x[0] for x in c.description]
stock_df = pd.DataFrame(c.fetchall(),columns=['ID','tickersymbol','companyname'])

## StockFact
c.execute('''create table stockfact (
  stockid integer not null,
  date_time datetime,
  stockprice decimal(6,2),
  foreign key (stockid) references stock(id)
)''')
c.execute('''insert into stockfact(stockid,date_time,stockprice)
select distinct a.id,b.date,b.close_last from stock as a left join stock_data_raw as b on a.tickersymbol=b.symbol
''')
#colnames=[x[0] for x in c.description]
stockfact_df = pd.DataFrame(c.fetchall(),columns=['stockid','date_time','stockprice'])

## User
c.execute('''create table user (
  ID integer primary key autoincrement not null,
  FirstName char(50) not null,
  LastName char(50) not null,
  Email varchar(100) not null check(email like '%@%'),
  password varchar(50) not null
)''')
c.execute('''insert into user (FirstName,LastName,Email,password) values
('Lee','Johnson','lj@yahoo.com','ABC123')
  '''
)
#colnames=[x[0] for x in c.description]
user_df = pd.DataFrame(c.fetchall(),columns=['ID','FirstName','LastName','Email','password'])

## Portfolio
c.execute('''create table portfolio (
  ID integer primary key autoincrement not null,
  userid integer not null,
  foreign key (userid) references user(id)
)''')
c.execute('''insert into portfolio(userid)
select distinct id from user''')
#colnames=[x[0] for x in c.description]
portfolio_df = pd.DataFrame(c.fetchall(),columns=['ID','userid'])

## Stock Portfolio
c.execute('''create table stockportfolio (
  portfolioid integer not null,
  stockid integer not null,
  shares integer,
  foreign key (portfolioid) references portfolio (id),
  foreign key (stockid) references stock(id)
)''')
c.execute('''insert into stockportfolio (portfolioid,stockid,shares)
select distinct a.id,b.id,1 from portfolio as a cross join stock as b where tickersymbol in ('INFY','JKS')
''')
#colnames=[x[0] for x in c.description]
stockportfolio_df = pd.DataFrame(c.fetchall(),columns=['portfolioid','stockid','shares'])

c.execute('''select distinct e.tickersymbol,companyname,shares from user as a
          inner join portfolio as b on a.id=b.userid
          inner join stockportfolio as c on b.id=c.portfolioid
          inner join stockfact as d on c.stockid=d.stockid
          inner join stock as e on d.stockid=e.id and c.stockid=e.id
          
''')
colnames=[x[0] for x in c.description]
port_df = pd.DataFrame(c.fetchall(),columns=colnames)

c.execute('''select tickersymbol, date_time, stockprice from stock as a
          inner join stockfact as b on a.id=b.stockid
''')
colnames=[x[0] for x in c.description]
dropdown_df = pd.DataFrame(c.fetchall(),columns=colnames)

########################################################################


# START OF TEMP DATA until connected to database
#temp dropdown options
#choices = ['AAPL', 'TMUS', 'IBM', 'SIX']
choices = dropdown_df['tickersymbol'].tolist()

#temp current portfolio
#current_port = [['SWI', 52.34, 20], ['IBM', 108.43, 10], ['COST', 25.79, 40]]
#port_df = pd.DataFrame(current_port, columns=['Symbol', 'Price', 'Share Count'])


#temp line charts
# dropdown_trend = [[1, 52.34], [2, 63.29], [3, 66.80], [4, 63.41],
#                   [5, 55.76], [6, 43.86], [7, 52], [8, 70.98], 
#                   [9, 74], [10, 80.88], [11, 95.21], [12, 66.80]]
# dropdown_df = pd.DataFrame(dropdown_trend, columns=['Month', 'Price'])

# port_trend = [[1, 2000], [2, 6000], [3, 12000], [4, 26000],
#                   [5, 20000], [6, 17000], [7, 19000], [8, 2000], 
#                   [9, 10000], [10, 8000], [11, 6000], [12, 6000]]
#port_trend_df = pd.DataFrame(port_trend, columns=['Month', 'Total'])
# END OF TEMP DATA


#UI
app_ui = ui.page_fluid(
        ui.tags.style(
        """
        .app-col {
            background-color: #eee;
        }
        """),
    ui.h2("My Portfolio Tracker",class_='app-col'), # header
    ui.h4("Current Portfolio"),  # header
    ui.output_table("current_portfolio"), # user current portfolio table 
    ui.div(ui.row( 
        ui.column(4,ui.input_selectize("x1","Select Stock" ,choices)),  #Stock Dropdown
        ui.column(4,ui.input_numeric("x", "Stock Count", value=0)),   #stock count
        ui.column(4,ui.p(ui.input_action_button("x4", "Save Results", class_="btn-success"))),
        style=css(align_items="center" )
    ),
ui.row(class_='app-col'),
    ui.row(
        ui.column(4,ui.p(ui.input_action_button("x2", "Buy", class_="btn-primary"))),  #stock add button
        ui.column(4,ui.p(ui.input_action_button("x3", "Sell", class_="btn-primary"))), #stock drop button
        ui.column(4,ui.p(ui.input_action_button("x5", "Update", class_="btn-primary")))  #shares update button
    ),class_='app-col'),
    
    ui.row(
        ui.column(6,ui.output_plot("Stock_Dropdown_Trend")),  #plot 1
        ui.column(6,ui.output_plot("Portfolio_Trend"))        #plot 2
    ),
)

curr_stocks=port_df['tickersymbol'].tolist()
port_trend_df=dropdown_df.loc[dropdown_df['tickersymbol'].isin(curr_stocks)]


# SERVER
def server(input, output, session):

    @output
    @render.table
    def current_portfolio():
        input.x4()
        with reactive.isolate():
            if input.x3():
                #drop_row = port_df[port_df['tickersymbol']==input.x1()].index
                #port_df2=port_df.drop(drop_row)
                params=[input.x1()]
                c.execute('''delete from stockportfolio where stockid = (select distinct id from stock where tickersymbol=?)''',params)
                c.execute('''select distinct e.tickersymbol,companyname,shares from user as a
                  inner join portfolio as b on a.id=b.userid
                  inner join stockportfolio as c on b.id=c.portfolioid
                  inner join stockfact as d on c.stockid=d.stockid
                  inner join stock as e on d.stockid=e.id and c.stockid=e.id''')
                colnames=[x[0] for x in c.description]
                port_df = pd.DataFrame(c.fetchall(),columns=colnames)
                # return port_df
    
            elif input.x2():
                # new_row=pd.DataFrame({'tickersymbol':input.x1(),'shares':input.x()},index=[0])
                # port_df3=port_df.append(new_row)
                params=[input.x(),input.x1()]
                c.execute('''insert into stockportfolio(portfolioid,stockid,shares)
                select 1,b.id,? from stock as b where b.tickersymbol = ?''',params)
                c.execute('''select distinct e.tickersymbol,companyname,shares from user as a
                  inner join portfolio as b on a.id=b.userid
                  inner join stockportfolio as c on b.id=c.portfolioid
                  inner join stockfact as d on c.stockid=d.stockid
                  inner join stock as e on d.stockid=e.id and c.stockid=e.id''')
                colnames=[x[0] for x in c.description]
                port_df = pd.DataFrame(c.fetchall(),columns=colnames)
                # return port_df 

            elif input.x5():
                params=[input.x(),input.x1()]
                c.execute('''update stockportfolio
                set shares = ?  where stockid = (select distinct id from stock where tickersymbol= ?)''',params)
                c.execute('''select distinct e.tickersymbol,companyname,shares from user as a
                  inner join portfolio as b on a.id=b.userid
                  inner join stockportfolio as c on b.id=c.portfolioid
                  inner join stockfact as d on c.stockid=d.stockid
                  inner join stock as e on d.stockid=e.id and c.stockid=e.id''')
                colnames=[x[0] for x in c.description]
                port_df = pd.DataFrame(c.fetchall(),columns=colnames)
                # return port_df 
            else:
                c.execute('''select distinct e.tickersymbol,companyname,shares from user as a
                  inner join portfolio as b on a.id=b.userid
                  inner join stockportfolio as c on b.id=c.portfolioid
                  inner join stockfact as d on c.stockid=d.stockid
                  inner join stock as e on d.stockid=e.id and c.stockid=e.id''')
                colnames=[x[0] for x in c.description]
                port_df = pd.DataFrame(c.fetchall(),columns=colnames)
                # return port_df 
        return port_df
        
    @output
    @render.plot
    def Stock_Dropdown_Trend():
        # Convert the date_time column to datetime type
        dropdown_df['date_time'] = pd.to_datetime(dropdown_df['date_time'])
        dropdown_df2=dropdown_df.loc[dropdown_df['tickersymbol']==input.x1()]
        # Create monthly bins and calculate the avg of stock prices for each month
        dropdown_df3= dropdown_df2.groupby(pd.Grouper(key='date_time', freq='M')).mean()
        plt.plot(dropdown_df3.index, dropdown_df3['stockprice'])
        plt.xlabel("Date")
        plt.ylabel("Average Price")
        return plt.title('Stock Dropdown Visual')    #display plot 1
        
        
    @output
    @render.plot
    def Portfolio_Trend():
        input.x4()
        with reactive.isolate():
            c.execute('''select tickersymbol, date_time, stockprice from stock as a
              inner join stockfact as b on a.id=b.stockid
            ''')
            colnames=[x[0] for x in c.description]
            dropdown_df = pd.DataFrame(c.fetchall(),columns=colnames)
            c.execute('''select distinct e.tickersymbol,companyname,shares from user as a
              inner join portfolio as b on a.id=b.userid
              inner join stockportfolio as c on b.id=c.portfolioid
              inner join stockfact as d on c.stockid=d.stockid
              inner join stock as e on d.stockid=e.id and c.stockid=e.id''')
            colnames=[x[0] for x in c.description]
            port_df = pd.DataFrame(c.fetchall(),columns=colnames)
            curr_stocks=port_df['tickersymbol'].tolist()
            print(curr_stocks)
            port_trend_df=dropdown_df.loc[dropdown_df['tickersymbol'].isin(curr_stocks)]
            
            # Convert the date_time column to pandas Timestamp object
            port_trend_df.loc[:, 'date_time'] = port_trend_df['date_time'].apply(pd.Timestamp)
            # Extract the year from the date_time column
            port_trend_df.loc[:, 'year'] = port_trend_df['date_time'].dt.year
            # Create yearly bins and calculate the average stock prices for each year
            port_trend_df2 = port_trend_df.groupby(['year', 'tickersymbol'])['stockprice'].mean().unstack()
            # Plot the stacked column chart
            port_trend_df2.plot(kind='bar', stacked=True)
            plt.xlabel("Date")
            plt.ylabel("Average Price")
            plt.legend(title='Stock')
            return plt.title('Portfolio Trend')

app=App(app_ui,server)